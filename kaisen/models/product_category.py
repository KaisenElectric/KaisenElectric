from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_cost_method = fields.Selection(selection_add=[("fifowh", "First In First Out by Warehouse (FIFO)")],
                                                           ondelete={"fifowh": "set default"})
