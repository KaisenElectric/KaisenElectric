from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    comments = fields.Char(string="Comments")
