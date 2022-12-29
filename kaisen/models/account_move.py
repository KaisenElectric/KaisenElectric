from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("name", "highest_name")
    def _onchange_name_warning(self):
        super()._onchange_name_warning()
