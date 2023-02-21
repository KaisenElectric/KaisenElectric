from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    internal_cost = fields.Float(string="Internal Cost", compute="_compute_internal_cost")
    sale_order_line_id = fields.Many2one(comodel_name="sale.order.line", string="Sale Order Line")

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, company_id, values,
                                                      po):
        """
        OVERRIDE
        Added intecialization of fields product_packaging_id and price_unit when po line created
        """
        res = super()._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, company_id,
                                                                    values, po)
        if values.get("product_packaging_id"):
            res["product_packaging_id"] = values.get("product_packaging_id").id
        if values.get("move_dest_ids"):
            sale_line_id = values.get("move_dest_ids").sale_line_id
            price_unit = sale_line_id.price_unit
            if sale_line_id.order_id.currency_id != po.currency_id:
                price_unit = sale_line_id.order_id.currency_id._convert(from_amount=price_unit,
                                                                        to_currency=po.currency_id,
                                                                        company=po.company_id, date=fields.Date.today(),
                                                                        round=False)
            res["price_unit"] = price_unit
        return res

    def _prepare_stock_moves(self, picking):
        """
        OVERRIDE
        Added intecialization of fields product_packaging_id and price_unit when po line created
        """
        results = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        for result in results:
            result["product_packaging_id"] = self.product_packaging_id.id
            result["price_unit"] = self.move_dest_ids.sale_line_id.price_unit
        return results

    def _find_candidate(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        """
        OVERRIDE
        Added fields product_packaging_id and price_unit when select candidates for the merger
        """
        lines = self.filtered(
            lambda po_line: po_line.product_packaging_id.id == values['product_packaging_id'].id) if values.get(
            'product_packaging_id') else self
        if values.get("move_dest_ids"):
            sale_line_id = values.get("move_dest_ids").move_dest_ids.sale_line_id
            lines = lines.filtered(
                lambda po_line_id: po_line_id.price_unit == sale_line_id.order_id.currency_id._convert(
                    from_amount=sale_line_id.price_unit,
                    to_currency=po_line_id.order_id.currency_id,
                    company=po_line_id.order_id.company_id, date=fields.Date.today(),
                    round=False))
        return super(PurchaseOrderLine, lines)._find_candidate(product_id, product_qty, product_uom, location_id, name,
                                                               origin, company_id, values)

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, company_id, values,
                                                      po):
        """
        OVERRIDE
        Added fields product_packaging_id and price_unit when select candidates for the merger
        """
        res = super()._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, company_id,
                                                                    values, po)
        res['product_packaging_id'] = values.get('product_packaging_id').id if values.get(
            'product_packaging_id') else False
        if values.get("move_dest_ids"):
            sale_line_id = values.get("move_dest_ids").sale_line_id
            price_unit = sale_line_id.price_unit
            if sale_line_id.order_id.currency_id != po.currency_id:
                price_unit = sale_line_id.order_id.currency_id._convert(from_amount=price_unit,
                                                                        to_currency=po.currency_id,
                                                                        company=po.company_id, date=fields.Date.today(),
                                                                        round=False)
            res["price_unit"] = price_unit
        return res

    @api.depends("order_id", "order_id.partner_id", "sale_order_line_id", "sale_order_line_id.purchase_price")
    def _compute_internal_cost(self):
        """Computes internal_cost by partner_id and purchase_price in linked sale order line."""
        for record_id in self:
            if record_id.order_id.partner_id in self.env.company.parent_ids.mapped("partner_id"):
                record_id.internal_cost = record_id.sudo().sale_order_line_id.purchase_price
            else:
                record_id.internal_cost = 0
