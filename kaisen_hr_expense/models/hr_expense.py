from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"
    
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner"
    )
