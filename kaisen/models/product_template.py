from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    tag_ids = fields.Many2many(
        comodel_name="product.tag",
        string="Tags",
    )
