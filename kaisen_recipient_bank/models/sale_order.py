from odoo import models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"


    @api.onchange("partner_id", "company_id")
    def _onchange_partner_id(self):
        recipient_bank_id = self.with_company(self.company_id.id).partner_id.property_recipient_bank_id \
                            or self.company_id.partner_id.bank_ids[:1]
        if recipient_bank_id and self.company_recipient_bank_id != recipient_bank_id:
            self.company_recipient_bank_id = recipient_bank_id
