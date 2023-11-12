from odoo import models, fields, api, _


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_partners_include_exclude = True

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
