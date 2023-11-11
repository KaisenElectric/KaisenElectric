from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    message_main_attachment_hash = fields.Char(string="Hash of main attachment")
