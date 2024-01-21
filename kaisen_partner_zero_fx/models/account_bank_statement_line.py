import logging
from odoo import models


_logger = logging.getLogger(__name__)

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def reconcile(self, lines_vals_list, to_check=False, allow_partial=False):
        super().reconcile(lines_vals_list, to_check, allow_partial)
        if self.move_id.currency_id == self.move_id.company_id.currency_id:
            return None
        journal_id = self.move_id.journal_id
        account_ids = journal_id.default_account_id | journal_id.suspense_account_id
        line_ids = self.move_id.line_ids.filtered(lambda l: l.account_id not in account_ids)
        lines = self.env['account.move.line'].read_group(
            domain=[
                ('account_id', 'in', line_ids.account_id.ids),
                ('partner_id', '=', self.move_id.partner_id.id),
                ('parent_state', '=', 'posted'),
            ],
            fields=['account_id', 'amount_currency:sum(amount_currency)', 'amount:sum(balance)'],
            groupby=['account_id'],
        )
        move_vals_list = []
        for line in lines:
            if line.get('amount_currency') != 0 or line['amount'] == 0:
                continue
            move_vals = self.move_id._prepare_move_vals_partner_zero_fx(line['account_id'][0], line['amount'])
            move_vals_list.append(move_vals)

        if move_vals_list:
            move_ids = self.move_id.create(move_vals_list)
            move_ids._post()
