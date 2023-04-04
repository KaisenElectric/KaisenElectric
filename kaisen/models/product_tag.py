from random import randint

from odoo import models, fields


class ProductTag(models.Model):
    _name = "product.tag"
    _description = "Product Tag"

    def _get_default_color(self):
        """
        This function returns a random integer between 1 and 11
        """
        return randint(1, 11)

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    color = fields.Integer(
        string="Color",
        default=_get_default_color,
    )

    _sql_constraints = [
        ("name_uniq", "unique (name)", "Tag name already exists !"),
    ]
