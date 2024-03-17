from odoo import api, fields, models


class KaisenScheduleFxAdjustmentLog(models.Model):
    _name = 'kaisen.schedule.fx.adjustment.log'
    _description = 'Log Schedule of Currency Adjustment Automation'
    _order = 'id desc'

    name = fields.Char(
        string='Description',
    )

    schedule_id = fields.Many2one(
        'kaisen.schedule.fx.adjustment',
        string='Cause by',
    )

    move_id = fields.Many2one(
        'account.move',
        string='FX Entry',
    )

    reverse_move_id = fields.Many2one(
        'account.move',
        string='Reverse FX Entry',
    )

    @staticmethod
    def open_record(res_id):
        return {
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': res_id,
            'type': 'ir.actions.act_window',
        }

    def open_move_id(self):
        if not self.move_id:
            return None
        return self.open_record(self.move_id.id)

    def open_reverse_move_id(self):
        if not self.reverse_move_id:
            return None
        return self.open_record(self.reverse_move_id.id)
