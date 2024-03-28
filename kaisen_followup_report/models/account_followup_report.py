from odoo import models, _


del_columns = False

class AccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"


    def _get_columns_name(self, options):
        global del_columns
        headers = super()._get_columns_name(options)
        if not self.env.context.get("print_mode"):
            return headers
        del_columns_name = (_("Communication"), _("Source Document"))
        result = []
        for index, header in enumerate(headers):
            if not header or "name" not in header or header["name"] not in del_columns_name:
                result.append(header)
                continue
            if not del_columns:
                del_columns = [False, False]
            del_columns[del_columns_name.index(header["name"])] = index - 1
        return result

    def _get_lines(self, options, line_id=None):
        global del_columns
        lines = super()._get_lines(options, line_id)
        if not self.env.context.get("print_mode"):
            return lines
        for line in lines:
            for column_pos in del_columns or []:
                if column_pos is not False:
                    del line["columns"][column_pos]
        del_columns = False
        return lines
