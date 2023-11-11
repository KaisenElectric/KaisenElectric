from odoo import models, _


communication_pos = False

class AccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"


    def _get_columns_name(self, options):
        global communication_pos
        headers = super()._get_columns_name(options)
        if not self.env.context.get("print_mode"):
            return headers
        communication = _("Communication")
        result = []
        for index, header in enumerate(headers):
            if not header or "name" not in header or header["name"] != communication:
                result.append(header)
                continue
            communication_pos = index - 1
        return result

    def _get_lines(self, options, line_id=None):
        global communication_pos
        lines = super()._get_lines(options, line_id)
        if not self.env.context.get("print_mode"):
            return lines
        for line in lines:
            del line["columns"][communication_pos]
        communication_pos = False
        return lines
