from odoo import api, fields, models


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    product_tag_ids = fields.Many2many(
        comodel_name="product.tag",
        relation="product_tag_account_move_line_rel",
        column1="account_move_line_id",
        column2="product_tag_id",
        string="Tags",
        manual=True,
        copy=False,
    )
