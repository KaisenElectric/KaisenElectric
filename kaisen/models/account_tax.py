from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    notes_for_printing = fields.Text(string="Notes for Printing Forms")
    description = fields.Char(translate=True)
