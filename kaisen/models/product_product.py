from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    tag_ids = fields.Many2many(
        comodel_name="product.tag",
        related="product_tmpl_id.tag_ids",
    )
