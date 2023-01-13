from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    parent_ids = fields.Many2many(
        comodel_name="res.company",
        name="Parent companies",
        relation="parent_companies_rel",
        column1="child_id",
        column2="parent_id",
    )
