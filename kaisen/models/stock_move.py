from odoo import models, fields, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
from odoo.tools.misc import OrderedSet
from odoo.tools.float_utils import float_compare, float_is_zero
from collections import defaultdict


class StockMove(models.Model):
    _inherit = "stock.move"

    product_packaging_qty = fields.Float(string="Packaging Quantity", compute="_compute_product_packaging_qty")

    def _action_done(self, cancel_backorder=False):
        """
        OVERRIDE
        Changed the check for a unique location
        """
        # Init a dict that will group the moves by valuation type, according to `move._is_valued_type`.
        valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
        for move in self:
            if float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding):
                continue
            for valued_type in self._get_valued_types():
                if getattr(move, '_is_%s' % valued_type)():
                    valued_moves[valued_type] |= move

        # AVCO application
        valued_moves['in'].product_price_update_before_done()

        res = self._second_action_done(cancel_backorder=cancel_backorder)

        # '_action_done' might have created an extra move to be valued
        for move in res - self:
            for valued_type in self._get_valued_types():
                if getattr(move, '_is_%s' % valued_type)():
                    valued_moves[valued_type] |= move

        stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
        # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
        for valued_type in self._get_valued_types():
            todo_valued_moves = valued_moves[valued_type]
            if todo_valued_moves:
                todo_valued_moves._sanity_check_for_valuation()
                stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()

        stock_valuation_layers._validate_accounting_entries()
        stock_valuation_layers._validate_analytic_accounting_entries()

        stock_valuation_layers._check_company()

        # For every in move, run the vacuum for the linked product.
        products_to_vacuum = valued_moves['in'].mapped('product_id')
        company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[
            0] or self.env.company
        for product_to_vacuum in products_to_vacuum:
            product_to_vacuum._run_fifo_vacuum(company)

        return res

    def _second_action_done(self, cancel_backorder=False):
        """
        OVERRIDE
        Original method name: _action_done
        Changed the check for a unique location
        """
        self.filtered(lambda move: move.state == 'draft')._action_confirm()  # MRP allows scrapping draft moves
        moves = self.exists().filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_ids_todo = OrderedSet()

        # Cancel moves where necessary ; we should do it before creating the extra moves because
        # this operation could trigger a merge of moves.
        for move in moves:
            if move.quantity_done <= 0 and not move.is_inventory:
                if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0 or cancel_backorder:
                    move._action_cancel()

        # Create extra moves where necessary
        for move in moves:
            if move.state == 'cancel' or (move.quantity_done <= 0 and not move.is_inventory):
                continue

            moves_ids_todo |= move._create_extra_move().ids

        moves_todo = self.browse(moves_ids_todo)
        moves_todo._check_company()
        # Split moves where necessary and move quants
        backorder_moves_vals = []
        for move in moves_todo:
            # To know whether we need to create a backorder or not, round to the general product's
            # decimal precision and not the product's UOM.
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
                # Need to do some kind of conversion here
                qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done, move.product_id.uom_id, rounding_method='HALF-UP')
                new_move_vals = move._split(qty_split)
                backorder_moves_vals += new_move_vals
        backorder_moves = self.env['stock.move'].create(backorder_moves_vals)
        # The backorder moves are not yet in their own picking. We do not want to check entire packs for those
        # ones as it could messed up the result_package_id of the moves being currently validated
        backorder_moves.with_context(bypass_entire_pack=True)._action_confirm(merge=False)
        if cancel_backorder:
            backorder_moves.with_context(moves_todo=moves_todo)._action_cancel()
        moves_todo.mapped('move_line_ids').sorted()._action_done()
        # Check the consistency of the result packages; there should be an unique location across
        # the contained quants.
        for result_package in moves_todo\
                .mapped('move_line_ids.result_package_id')\
                .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1 and not p.product_packaging_id):
            if len(result_package.quant_ids.filtered(lambda q: not float_is_zero(abs(q.quantity) + abs(q.reserved_quantity), precision_rounding=q.product_uom_id.rounding)).mapped('location_id')) > 1:
                raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
        picking = moves_todo.mapped('picking_id')
        moves_todo.write({'state': 'done', 'date': fields.Datetime.now()})

        new_push_moves = moves_todo.filtered(lambda m: m.picking_id.immediate_transfer)._push_apply()
        if new_push_moves:
            new_push_moves._action_confirm()
        move_dests_per_company = defaultdict(lambda: self.env['stock.move'])
        for move_dest in moves_todo.move_dest_ids:
            move_dests_per_company[move_dest.company_id.id] |= move_dest
        for company_id, move_dests in move_dests_per_company.items():
            move_dests.sudo().with_company(company_id)._action_assign()

        # We don't want to create back order for scrap moves
        # Replace by a kwarg in master
        if self.env.context.get('is_scrap'):
            return moves_todo

        if picking and not cancel_backorder:
            backorder = picking._create_backorder()
            if any([m.state == 'assigned' for m in backorder.move_lines]):
               backorder._check_entire_pack()
        return moves_todo

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        move_line_values = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        if not move_line_values.get("package_id"):
            # move_line_values["package_id"] = self.product_packaging_id.stock_quant_package_id.id
            move_line_values["result_package_id"] = self.product_packaging_id.stock_quant_package_id.id
        return move_line_values

    def _compute_product_packaging_qty(self):
        """Computes product_packaging_qty by qty in packaging and product qty"""
        for record_id in self:
            product_packaging_qty = 0
            if record_id.product_packaging_id.qty:
                packaging_uom_id = record_id.product_packaging_id.product_uom_id
                if record_id.picking_id.picking_type_id.code == "incoming" and record_id.quantity_done:
                    product_packaging_qty = float_round(
                        record_id.quantity_done / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding or 0.01,
                    )
                elif record_id.picking_id.picking_type_id.code == "outgoing" and record_id.forecast_availability:
                    product_packaging_qty = float_round(
                        record_id.forecast_availability / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding or 0.01,
                    )
                elif record_id.picking_id.picking_type_id.code == "outgoing" and record_id.quantity_done:
                    product_packaging_qty = float_round(
                        record_id.quantity_done / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding or 0.01,
                    )
                else:
                    product_packaging_qty = float_round(
                        record_id.product_qty / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding or 0.01,
                    )
            record_id.product_packaging_qty = abs(product_packaging_qty)

    def get_logismart_product_code(self):
        """Returns logismart_product_code by product and packaging"""
        self.ensure_one()
        if not self.product_packaging_id:
            raise UserError(f"Packaging field is not filled in for {self.product_id.name}")
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
        if self.purchase_line_id.internal_cost:
            return self.purchase_line_id.internal_cost
        return super()._get_price_unit()
