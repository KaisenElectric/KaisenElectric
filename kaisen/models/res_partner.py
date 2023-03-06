from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    registry_number = fields.Char(string="Registry Number")
