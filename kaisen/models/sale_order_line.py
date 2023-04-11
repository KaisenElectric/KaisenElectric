from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    purchase_order_line_ids = fields.One2many(
        comodel_name="purchase.order.line",
        inverse_name="sale_order_line_id",
        string="Sale Order Lines",
    )
