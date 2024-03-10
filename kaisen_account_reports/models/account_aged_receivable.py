from odoo import models, api, fields, _


class ReportAccountAgedReceivable(models.Model):
    _inherit = "account.aged.receivable"

    filter_group_by_saleperson = False
    filter_saleperson = True

    saleperson_id = fields.Many2one('res.users')
    saleperson_name = fields.Char(group_operator='max')

    @api.model
    def _get_sql(self):
        options = self.env.context['report_options']

        query = ("""
            SELECT
                {move_line_fields},
                account_move_line.amount_currency as amount_currency,
                account_move_line.partner_id AS partner_id,
                partner.name AS partner_name,
                sales.user_id AS saleperson_id,
                sales.name AS saleperson_name,
                COALESCE(trust_property.value_text, 'normal') AS partner_trust,
                COALESCE(account_move_line.currency_id, journal.currency_id) AS report_currency_id,
                account_move_line.payment_id AS payment_id,
                COALESCE(account_move_line.date_maturity, account_move_line.date) AS report_date,
                account_move_line.expected_pay_date AS expected_pay_date,
                move.move_type AS move_type,
                move.name AS move_name,
                move.ref AS move_ref,
                account.code || ' ' || account.name AS account_name,
                account.code AS account_code,""" + ','.join([("""
                CASE WHEN period_table.period_index = {i}
                THEN %(sign)s * ROUND((
                    account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0)
                ) * currency_table.rate, currency_table.precision)
                ELSE 0 END AS period{i}""").format(i=i) for i in range(6)]) + """
            FROM account_move_line
            JOIN account_move move ON account_move_line.move_id = move.id
            JOIN account_journal journal ON journal.id = account_move_line.journal_id
            JOIN account_account account ON account.id = account_move_line.account_id
            LEFT JOIN (
                SELECT aml.id AS id, am.invoice_user_id AS user_id, p.name
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                JOIN res_users u ON u.id = am.invoice_user_id
                JOIN res_partner p ON p.id = u.partner_id
                GROUP BY aml.id, am.invoice_user_id, p.name
            ) sales ON sales.id = account_move_line.id
            LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
            LEFT JOIN ir_property trust_property ON (
                trust_property.res_id = 'res.partner,'|| account_move_line.partner_id
                AND trust_property.name = 'trust'
                AND trust_property.company_id = account_move_line.company_id
            )
            JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id
            LEFT JOIN LATERAL (
                SELECT part.amount, part.debit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %(date)s
            ) part_debit ON part_debit.debit_move_id = account_move_line.id
            LEFT JOIN LATERAL (
                SELECT part.amount, part.credit_move_id
                FROM account_partial_reconcile part
                WHERE part.max_date <= %(date)s
            ) part_credit ON part_credit.credit_move_id = account_move_line.id
            JOIN {period_table} ON (
                period_table.date_start IS NULL
                OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
            )
            AND (
                period_table.date_stop IS NULL
                OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
            )
            WHERE account.internal_type = %(account_type)s
            AND account.exclude_from_aged_reports IS NOT TRUE
            GROUP BY account_move_line.id, partner.id, sales.user_id, sales.name, trust_property.id, journal.id, move.id, account.id,
                     period_table.period_index, currency_table.rate, currency_table.precision
            HAVING ROUND(account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0), currency_table.precision) != 0
        """).format(
            move_line_fields=self._get_move_line_fields('account_move_line'),
            currency_table=self.env['res.currency']._get_query_currency_table(options),
            period_table=self._get_query_period_table(options),
        )
        params = {
            'account_type': options['filter_account_type'],
            'sign': 1 if options['filter_account_type'] == 'receivable' else -1,
            'date': options['date']['date_to'],
        }
        return self.env.cr.mogrify(query, params).decode(self.env.cr.connection.encoding)

    def _get_hierarchy_details(self, options):
        if options.get('group_by_saleperson') is not True:
            return super()._get_hierarchy_details(options)

        return [
            self._hierarchy_level('saleperson_id', foldable=True, namespan=len(self._get_column_details(options)) - 7),
            self._hierarchy_level('partner_id', foldable=True, namespan=len(self._get_column_details(options)) - 7),
            self._hierarchy_level('id'),
        ]

    def _format_saleperson_id_line(self, res, value_dict, options):
        res['name'] = value_dict['saleperson_name'][:128] if value_dict['saleperson_name'] else _('Unknown Saleperson')

    def get_report_informations(self, options):
        options = self._get_options(options)
        options['unfolded_lines'] = []
        return super().get_report_informations(options)

    def _append_grouped(self, lines, current, line_dict, value_getters, value_formatters, options, hidden_lines):
        if not line_dict['values']:
            return
        return super()._append_grouped(lines, current, line_dict, value_getters, value_formatters, options, hidden_lines)

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = super()._get_lines(options, line_id)
        if options.get('group_by_saleperson') is not True or not line_id:
            return lines

        for line in lines:
            if line['id'] == line_id:
                line['parent_id'] = None
                break
        return lines
