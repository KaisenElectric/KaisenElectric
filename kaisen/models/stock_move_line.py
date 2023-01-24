from odoo import models, fields


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    product_packaging_id = fields.Many2one(
        comodel_name="product.packaging", sting="Packaging", related="move_id.product_packaging_id"
    )
    result_package_id = fields.Many2one(
        string="Destination Package",
        domain="['|', ('product_packaging_id', '=', False), ('product_packaging_id', '=', product_packaging_id)]",
    )
