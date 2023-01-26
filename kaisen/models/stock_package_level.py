from odoo import models, fields


class StockPackageLevel(models.Model):
    _inherit = "stock.package_level"

    company_id = fields.Many2one(comodel_name="res.company", string="Company", required=False)
