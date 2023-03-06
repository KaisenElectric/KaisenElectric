from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_invoice_values(self, order, name, amount, so_line):
        """
        Method adds partner_bank_id in AM.
        """
        invoice_vals = super()._prepare_invoice_values(order, name, amount, so_line)
        invoice_vals["partner_bank_id"] = order.company_recipient_bank_id.id
        return invoice_vals

