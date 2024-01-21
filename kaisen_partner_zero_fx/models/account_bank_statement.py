from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_is_zero


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def _get_account_amount(self, ids_account):
        return self.env['account.move.line'].read_group(
            domain=[
                ('account_id', 'in', ids_account),
                ('parent_state', '=', 'posted'),
            ],
            fields=['account_id', 'amount_currency:sum(amount_currency)', 'amount:sum(balance)'],
            groupby=['account_id'],
        )

    def button_post(self):
        super().button_post()
        zero_statement_ids = self.filtered(lambda s:
            float_is_zero(s.balance_end_real, precision_digits=s.journal_id.currency_id.decimal_places)
            and s.journal_type in ('bank', 'cash') and s.journal_id.currency_id != s.company_id.currency_id
        )

        lines = []
        if zero_statement_ids:
            lines = self._get_account_amount(zero_statement_ids.journal_id.default_account_id.ids)

        zero_statement_line_by_account = defaultdict(self.env['account.bank.statement.line'].browse)
        for line_id in zero_statement_ids.line_ids:
            zero_statement_line_by_account[line_id.journal_id.default_account_id.id] |= line_id

        move_vals_list = []
        for line in lines:
            if line.get('amount_currency') != 0 or line['amount'] == 0:
                continue
            statement_line_id = zero_statement_line_by_account[line['account_id'][0]][:1]
            if not statement_line_id:
                continue
            move_vals = statement_line_id.move_id._prepare_move_vals_partner_zero_fx(
                line['account_id'][0],
                line['amount'],
                with_partner=False,
            )
            move_vals_list.append(move_vals)

        if move_vals_list:
            move_ids = self.env['account.move'].create(move_vals_list)
            move_ids._post()

    def button_reopen(self):
        statement_ids = self.filtered(lambda s:
            s.journal_type in ('bank', 'cash')
            and s.journal_id.currency_id != s.company_id.currency_id
        )
        account_ids = statement_ids.journal_id.default_account_id
        if not account_ids:
            return super().button_reopen()

        date = min(statement_ids.line_ids.mapped('date'))

        move_ids = self.env['account.move.line'].search([
            ('move_id.is_partner_zero_fx_entry', '=', True),
            ('account_id', 'in', account_ids.ids),
            ('move_id.date', '>=', date),
            ('parent_state', '=', 'posted'),
            ('move_id.reversed_entry_id', '=', False),
        ]).move_id

        super().button_reopen()

        for move_id in move_ids:
            default_values = {
                'ref': _('Reversal of: %s', move_id.name),
                'date': move_id.date,
                'invoice_date_due': move_id.date,
                'invoice_date': False,
                'journal_id': move_id.journal_id.id,
                'invoice_payment_term_id': None,
                'invoice_user_id': False,
                'auto_post': 'no',
            }
            reversed_move_id = move_id._reverse_moves([default_values])
            move_id.is_partner_zero_fx_entry = False
            move_id.message_post(body=_('This entry has been %s', reversed_move_id._get_html_link(title=_("reversed"))))
            reversed_move_id._post()
