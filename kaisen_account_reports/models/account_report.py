from odoo import models, api, _


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_partners_include_exclude = True
    filter_saleperson = None

    @api.model
    def _get_options_partner_domain(self, options):
        domain = super()._get_options_partner_domain(options)
        if options['partners_include_exclude']:
            return domain
        result = []
        for item in domain:
            if len(item) < 3 or item[0] != 'partner_id':
                result.append(item)
            result.append((item[0], 'not in', item[2]))
        return result

    def _init_filter_saleperson(self, options, previous_options=None):
        if not self.filter_saleperson:
            return

        options['saleperson'] = True
        options['saleperson_ids'] = previous_options and previous_options.get('saleperson_ids') or []
        selected_saleperson_ids = [int(partner) for partner in options['saleperson_ids']]
        selected_saleperson = selected_saleperson_ids and self.env['res.users'].browse(selected_saleperson_ids) or self.env['res.users']
        options['selected_saleperson_ids'] = selected_saleperson.mapped('name')

    @api.model
    def _get_options_saleperson_domain(self, options):
        domain = []
        if options.get('saleperson_ids'):
            saleperson_ids = [int(saleperson) for saleperson in options['saleperson_ids']]
            domain.append(('saleperson_id', 'in', saleperson_ids))
        return domain

    @api.model
    def _get_options_domain(self, options):
        domain = super()._get_options_domain(options)
        domain += self._get_options_saleperson_domain(options)
        return domain
