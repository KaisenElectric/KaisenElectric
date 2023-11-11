from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    property_recipient_bank_id = fields.Many2one(
        "res.partner.bank",
        string="Recipient bank",
        company_dependent=True,
    )
