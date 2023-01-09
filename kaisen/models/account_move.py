from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("name", "highest_name")
    def _onchange_name_warning(self):
        """
        OVERRIDE
        Does not return a warning.
        """
        super()._onchange_name_warning()
