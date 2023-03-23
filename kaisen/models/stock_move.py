from odoo import models, fields, _, api
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    product_packaging_qty = fields.Float(string="Packaging Quantity", compute="_compute_product_packaging_qty")

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        move_line_values = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        if not move_line_values.get("package_id"):
            # move_line_values["package_id"] = self.product_packaging_id.stock_quant_package_id.id
            move_line_values["result_package_id"] = self.product_packaging_id.stock_quant_package_id.id
        return move_line_values

    @api.depends("product_packaging_id", "quantity_done", "forecast_availability", "product_qty")
    def _compute_product_packaging_qty(self):
        """Computes product_packaging_qty by qty in packaging and product qty"""
        for record_id in self:
            product_packaging_qty = 0
            if record_id.product_packaging_id.qty:
                packaging_uom_id = record_id.product_packaging_id.product_uom_id
                if record_id.picking_id.picking_type_id.code == "incoming" and record_id.quantity_done:
                    product_packaging_qty = float_round(
                        record_id.quantity_done / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding,
                    )
                elif record_id.picking_id.picking_type_id.code == "outgoing" and record_id.forecast_availability:
                    product_packaging_qty = float_round(
                        record_id.forecast_availability / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding,
                    )
                elif record_id.picking_id.picking_type_id.code == "outgoing" and record_id.quantity_done:
                    product_packaging_qty = float_round(
                        record_id.quantity_done / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding,
                    )
                else:
                    product_packaging_qty = float_round(
                        record_id.product_qty / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding,
                    )
            record_id.product_packaging_qty = abs(product_packaging_qty)

    def get_logismart_product_code(self):
        """Returns logismart_product_code by product and packaging"""
        self.ensure_one()
        logismart_product_code = None
        if self.picking_id.is_packing_operation:
            if not self.move_line_ids[:1].package_id:
                raise UserError(f"Source Package field is not filled for {self.product_id.name}")
            if not self.move_line_ids[:1].result_package_id:
                raise UserError(f"Destination Package field is not filled for {self.product_id.name}")
            if self.env.context.get("is_internal_arrival"):
                logismart_product_code = self.move_line_ids[:1].result_package_id.product_packaging_id.logismart_product_code
            elif self.env.context.get("is_internal_order"):
                logismart_product_code = self.move_line_ids[:1].package_id.product_packaging_id.logismart_product_code
        else:
            if not self.product_packaging_id:
                raise UserError(f"Packaging field is not filled for {self.product_id.name}")
            logismart_product_code = self.product_id.packaging_ids.filtered(lambda x: x == self.product_packaging_id)[
                :1
            ].logismart_product_code
        if not logismart_product_code:
            raise UserError(f"Logismart product code field is not filled in {self.product_id.name}")
        return logismart_product_code

    def _get_price_unit(self):
        """
        OVERRIDE
        Returns the unit price for the move.
        """
        self.ensure_one()
        line_id = self.purchase_line_id
        order_id = line_id.order_id
        if line_id.internal_cost:
            return order_id.currency_id._convert(
                line_id.internal_cost, order_id.company_id.currency_id, order_id.company_id,
                fields.Date.context_today(self),
                round=False)
        return super()._get_price_unit()

    @api.model
    def _get_valued_types(self):
        result = super()._get_valued_types()
        result.append("warehouse_moving")
        return result

    def _get_warehouse_moving_move_lines(self):
        """ Returns the `stock.move.line` records of `self` considered as moving between warehouses. It is done thanks
        to the `_should_be_valued` method of their source and destionation location and different warehouse of their
        source and destionation location.

        :returns: a subset of `self` containing the outgoing records
        :rtype: recordset
        """
        res = self.env["stock.move.line"]
        for move_line in self.move_line_ids:
            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id:
                continue
            if move_line.location_id._should_be_valued() and move_line.location_dest_id._should_be_valued()\
                    and move_line.location_id.warehouse_id != move_line.location_dest_id.warehouse_id:
                res |= move_line
        return res

    def _is_warehouse_moving(self):
        """Check if the move should be considered as moving between warehouses so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is leaving the company else False
        :rtype: bool
        """
        self.ensure_one()
        if self._get_warehouse_moving_move_lines():
            return True
        return False

    def _create_warehouse_moving_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_warehouse_moving_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done,
                                                                                     move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            if move.location_id.warehouse_id and move.product_id.cost_method == "fifowh":
                warehouse_id = move.location_id.warehouse_id
            else:
                continue
            svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id, warehouse_id)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals["description"] = "Correction of %s (modification of past move)" % move.picking_id.name or move.name
            svl_vals["description"] += svl_vals.pop("rounding_adjustment", "")
            svl_vals_list.append(svl_vals)

            unit_cost = svl_vals["unit_cost"]
            svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update({"warehouse_id": move.location_dest_id.warehouse_id.id})
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals["description"] = "Correction of %s (modification of past move)" % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def product_price_update_before_done(self, forced_qty=None):
        super().product_price_update_before_done(forced_qty)
        # adapt standard price on incomming moves if the product cost_method is 'fifowh'
        for move in self.filtered(lambda move:
                                  move.with_company(move.company_id).product_id.cost_method == "fifowh"
                                  and float_is_zero(move.product_id.sudo().quantity_svl, precision_rounding=move.product_id.uom_id.rounding)):
            move.product_id.with_company(move.company_id.id).sudo().write({"standard_price": move._get_price_unit()})

    def _action_assign(self):
        for move_id in self:
            if not move_id.package_level_id and  move_id.product_packaging_id.stock_quant_package_id\
                and not move_id.location_id.should_bypass_reservation():
                move_id.package_level_id = self.env["stock.package_level"].create({
                    "package_id": move_id.product_packaging_id.stock_quant_package_id.id,
                })

        return super()._action_assign()
