from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    kaisen_fx_adjustment_automation_date_shift = fields.Integer(
        string='Date shift',
        default=0,
        config_parameter='kaisen_fx_adjustment_automation.date_shift',
    )
