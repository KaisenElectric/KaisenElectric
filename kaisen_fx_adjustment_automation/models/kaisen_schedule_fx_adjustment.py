import hashlib
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class KaisenScheduleFxAdjustment(models.Model):
    _name = 'kaisen.schedule.fx.adjustment'
    _description = 'Schedule of Currency Adjustment Automation'

    name = fields.Char(
        string='Name'
    )

    apply_company_ids = fields.Many2many(
        'res.company',
        string='Apply to companies',
    )

    apply_company_hash = fields.Char(
        string='List Company Hash',
        compute='_compute_apply_company_hash',
        store=True,
    )

    date_start = fields.Date(
        string='Date Start',
        inverse='_inverse_date_start',
    )

    date_end = fields.Date(
        string='Date End',
        inverse='_inverse_date_end',
    )

    interval_number = fields.Integer(
        string='Execute Every',
        default=1,
        help="Repeat every x.",
        inverse='_inverse_interval',
    )

    interval_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string='Interval Unit', default='months', inverse='_inverse_interval')

    next_call = fields.Date(
        string='Next Execution Date',
        help="Next planned execution date.",
        readonly=True,
    )

    last_call = fields.Date(
        string='Last Execution Date',
        readonly=True,
    )

    @api.depends('apply_company_ids')
    def _compute_apply_company_hash(self):
        for rec in self:
            if not rec.apply_company_ids:
                rec.apply_company_hash = hashlib.sha256('None'.encode('utf-8')).hexdigest()
            else:
                rec.apply_company_hash = hashlib.sha256(','.join(map(str, sorted(rec.apply_company_ids.ids))).encode('utf-8')).hexdigest()

    def _inverse_date_start(self):
        for rec in self:
            if rec.date_start < fields.Date.today():
                raise ValidationError("Start date cannot be in the past")
            if rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError("The end date cannot be earlier than the start date")
            else:
                rec.next_call = rec.get_next_call(rec.date_start)

    def _inverse_date_end(self):
        for rec in self:
            if not rec.date_end:
                rec._inverse_interval()
                continue
            if rec.date_end < fields.Date.today():
                raise ValidationError("End date cannot be in the past")
            if rec.date_start > rec.date_end:
                raise ValidationError("The end date cannot be earlier than the start date")
            if rec.next_call and rec.next_call > rec.date_end:
                rec.next_call = False

    def _inverse_interval(self):
        for rec in self:
            if rec.last_call:
                rec.next_call = rec.get_next_call(rec.last_call)
            else:
                rec.next_call = rec.get_next_call(rec.date_start)

    def get_next_call(self, date, exclude_current=True):
        self.ensure_one()
        if not date:
            return False
        domain = [('apply_company_hash', '=', self.apply_company_hash)]
        if exclude_current:
            domain.append(('id', '!=', self.id))
        exists = set(self.search(domain).mapped('next_call'))
        now = fields.Date.today()
        result = date
        while result in exists or result < now:
            result = result + relativedelta(**{self.interval_type: self.interval_number})
            if self.date_end and result > self.date_end:
                return False
        return result

    def _prepare_move_vals_partner_fx(self, company_id, date, data):
        move_lines = []
        income_currency_fx_account_id = company_id.income_currency_exchange_account_id
        expense_currency_fx_account_id = company_id.expense_currency_exchange_account_id
        for row in data:
            currency_id = self.env['res.currency'].browse(row.get('currency_id'))
            amount = row.get('amount', 0)
            move_lines.append((0, 0, {
                'name': _('Currency Exchange Difference {for_cur}').format(
                    for_cur=currency_id.display_name,
                ),
                'partner_id': row.get('partner_id', False),
                'debit': -amount if amount < 0 else 0,
                'credit': amount if amount > 0 else 0,
                'amount_currency': 0,
                'currency_id': currency_id.id,
                'account_id': row.get('account_id'),
            }))
            move_lines.append((0, 0, {
                'name': (
                    _('Foreign Exchange Losses for {for_cur}') if amount > 0 else _('Foreign Exchange Income for {for_cur}')).format(
                    for_cur=currency_id.display_name,
                ),
                'partner_id': row.get('partner_id', False),
                'debit': amount if amount > 0 else 0,
                'credit': -amount if amount < 0 else 0,
                'amount_currency': 0,
                'currency_id': currency_id.id,
                'account_id': expense_currency_fx_account_id.id if amount > 0 else income_currency_fx_account_id.id,
            }))
        move_vals = {
            'ref': _('Foreign currencies adjustment entry as of %s', date.strftime('%d-%m-%Y')),
            'journal_id': company_id.currency_exchange_journal_id.id,
            'date': date,
            'line_ids': move_lines,
        }
        return move_vals

    def _get_receivable_payable_rows(self, date, company_id):
        self.env.cr.execute("""
            SELECT d.*, cr.rate, amount_residual_currency / cr.rate - amount_residual AS amount FROM (
            SELECT aml.partner_id, aml.account_id, aml.currency_id, aml.company_id, sum(aml.amount_residual_currency) AS amount_residual_currency, sum(amount_residual) AS amount_residual
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id 
            JOIN res_company c ON aml.company_id = c.id
            WHERE aa.internal_type IN ('receivable', 'payable')
            AND aml.parent_state = 'posted'
            AND c.currency_id <> aml.currency_id 
            AND aml.date <= %(date)s
            AND aml.reconciled IS NOT TRUE
            GROUP BY aml.account_id, aml.partner_id, aml.currency_id, aml.company_id
            ) d
            JOIN (
                SELECT "date", currency_id, company_id, rate
                FROM (
                SELECT "name" AS "date", currency_id, company_id, rate, LAG(id) OVER (PARTITION BY currency_id, company_id ORDER BY "name" DESC) AS prev
                FROM res_currency_rate cr
                WHERE "name" <= %(date)s
                ORDER BY "name" DESC 
                ) d WHERE prev IS NULL
            ) cr ON cr.currency_id = d.currency_id AND cr.company_id = d.company_id
            WHERE d.amount_residual_currency <> 0 AND d.company_id = %(company)s
        """, {'date': date, 'company': company_id.id})
        return self.env.cr.dictfetchall()

    def _get_bank_cash_rows(self, date, company_id):
        self.env.cr.execute("""
            SELECT d.*, cr.rate, amount_residual_currency / cr.rate - amount_residual AS amount FROM (
            SELECT aml.account_id, aml.currency_id, aml.company_id, sum(aml.amount_residual_currency) AS amount_residual_currency, sum(amount_residual) AS amount_residual
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id 
            JOIN res_company c ON aml.company_id = c.id
            WHERE aa.internal_type = 'liquidity'
            AND aml.parent_state = 'posted'
            AND c.currency_id <> aml.currency_id 
            AND aml.date <= %(date)s
            AND aml.reconciled IS NOT TRUE
            GROUP BY aml.account_id, aml.currency_id, aml.company_id
            ) d
            JOIN (
                SELECT "date", currency_id, company_id, rate
                FROM (
                SELECT "name" AS "date", currency_id, company_id, rate, LAG(id) OVER (PARTITION BY currency_id, company_id ORDER BY "name" DESC) AS prev
                FROM res_currency_rate cr
                WHERE "name" <= %(date)s
                ORDER BY "name" DESC 
                ) d WHERE prev IS NULL
            ) cr ON cr.currency_id = d.currency_id AND cr.company_id = d.company_id
            WHERE d.amount_residual_currency <> 0 AND d.company_id = %(company)s
        """, {'date': date, 'company': company_id.id})
        return self.env.cr.dictfetchall()

    def register_log(self, move_id, reverse_move_id):
        self.env['kaisen.schedule.fx.adjustment.log'].sudo().create({
            'name': _('Entry was created successful'),
            'schedule_id': self.id,
            'move_id': move_id.id,
            'reverse_move_id': reverse_move_id.id,
        })

    def register_log_message(self, message):
        self.env['kaisen.schedule.fx.adjustment.log'].sudo().create({
            'name': message,
            'schedule_id': self.id,
        })

    def _cron(self):
        now = fields.Date.today()
        tasks = self.search([('next_call', '<=', now)], order='next_call')
        all_company_ids = self.env['res.company']
        processed_company = set()
        date_shift = int(self.env['ir.config_parameter'].sudo().set_param('kaisen_fx_adjustment_automation.date_shift', 0))
        for task in tasks:
            if task.next_call < now:
                task.register_log_message(_('Entry was not created. Planed date is %s, now is %s') % (task.next_call, now))
                task.next_call = task.get_next_call(task.last_call or task.date_start)
                continue
            if date_shift:
                date = task.next_call - relativedelta(days=date_shift+1)
                reverse_date = task.next_call - relativedelta(days=date_shift)
            else:
                date = task.next_call - relativedelta(days=1)
                reverse_date = task.next_call
            if not task.apply_company_ids and not all_company_ids:
                all_company_ids = all_company_ids.search([])
            for company_id in task.apply_company_ids or all_company_ids:
                if company_id.id in processed_company:
                    continue

                rows = self._get_receivable_payable_rows(date, company_id)
                rows.extend(self._get_bank_cash_rows(date, company_id))
                move_vals = self._prepare_move_vals_partner_fx(company_id, date, rows)
                move_id = self.env['account.move'].with_company(company_id).create(move_vals)
                move_id._post()

                default_values = {
                    'ref': _('Reversal of: %s', move_id.name),
                    'date': reverse_date,
                    'invoice_date_due': reverse_date,
                    'invoice_date': False,
                    'journal_id': move_id.journal_id.id,
                    'invoice_payment_term_id': None,
                    'invoice_user_id': False,
                    'auto_post': 'no',
                }
                reversed_move_id = move_id._reverse_moves([default_values])
                move_id.message_post(body=_('This entry has been %s', reversed_move_id._get_html_link(title=_("reversed"))))
                reversed_move_id._post()
                task.register_log(move_id, reversed_move_id)

                processed_company.add(company_id.id)

            task.last_call = now
            task.next_call = task.get_next_call(now, exclude_current=False)
