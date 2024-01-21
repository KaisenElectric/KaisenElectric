from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_partner_zero_fx_entry = fields.Boolean(
        string='Automatically generated partner zero FX entry',
        readonly=True,
        default=False,
        copy=False,
    )

    def _prepare_move_vals_partner_zero_fx(self, id_account, amount, with_partner=True):
        self.ensure_one()
        move_lines = []
        income_currency_fx_account_id = self.company_id.income_currency_exchange_account_id
        expense_currency_fx_account_id = self.company_id.expense_currency_exchange_account_id
        move_lines.append((0, 0, {
            'name': _('Currency Exchange Difference {for_cur}').format(
                for_cur=self.currency_id.display_name,
            ),
            'partner_id': with_partner and self.partner_id.id,
            'debit': -amount if amount < 0 else 0,
            'credit': amount if amount > 0 else 0,
            'amount_currency': 0,
            'currency_id': self.currency_id.id,
            'account_id': id_account,
        }))
        move_lines.append((0, 0, {
            'name': (
                _('Foreign Exchange Losses for {for_cur}') if amount > 0 else _('Foreign Exchange Income for {for_cur}')).format(
                for_cur=self.currency_id.display_name,
            ),
            'partner_id': with_partner and self.partner_id.id,
            'debit': amount if amount > 0 else 0,
            'credit': -amount if amount < 0 else 0,
            'amount_currency': 0,
            'currency_id': self.currency_id.id,
            'account_id': expense_currency_fx_account_id.id if amount > 0 else income_currency_fx_account_id.id,
        }))
        move_vals = {
            'ref': _('Foreign currencies adjustment entry as of %s', self.date.strftime('%d-%m-%Y')),
            'journal_id': self.company_id.currency_exchange_journal_id.id,
            'date': self.date,
            'is_partner_zero_fx_entry': True,
            'line_ids': move_lines,
        }
        return move_vals
