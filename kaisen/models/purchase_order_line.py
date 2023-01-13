from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    internal_cost = fields.Float(string="Internal Cost", currency_field="currency_id", compute="_compute_internal_cost")
    sale_order_line_id = fields.Many2one(comodel_name="sale.order.line", string="Sale Order Line")

    @api.depends("order_id", "order_id.partner_id", "sale_order_line_id", "sale_order_line_id.purchase_price")
    def _compute_internal_cost(self):
        """Computes internal_cost by partner_id and purchase_price in linked sale order line."""
        for record_id in self:
            if record_id.order_id.partner_id in self.env.company.parent_ids.mapped("partner_id"):
                record_id.internal_cost = record_id.sudo().sale_order_line_id.purchase_price
            else:
                record_id.internal_cost = 0
