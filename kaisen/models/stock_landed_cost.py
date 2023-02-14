from odoo import models, fields, _


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    name = fields.Char(readonly=False)
