from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    intercompany_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Intercompany Warehouse",
    )
    is_same_partner = fields.Boolean(
        compute="_compute_is_same_partner",
        string="Same partner",
        invisible=True
    )

    @api.depends("partner_id")
    def _compute_is_same_partner(self):
        """
        Method checks if partner_id in company_ids.partner_id.
        """
        for record in self:
            company_count = self.env["res.company"].search_count([
                "|", ("partner_id", "=", record.partner_id.id),
                ("parent_id.partner_id", "=", record.partner_id.id)
            ])
            record.is_same_partner = bool(company_count)

    def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
        """
        Method adds intercompany_warehouse_id in SO.
        """
        self.ensure_one()
        result = super(PurchaseOrder, self.sudo())._prepare_sale_order_data(name, partner, company, direct_delivery_address)
        result["warehouse_id"] = self.intercompany_warehouse_id.id
        return result

    @api.model
    def _prepare_sale_order_line_data(self, line, company):
        """
        OVERRIDE
        Adds purchase_order_line_ids in line.
        """
        result = super()._prepare_sale_order_line_data(line, company)
        result["purchase_order_line_ids"] = [(6, 0, [line.id])]
        result["product_packaging_id"] = line.product_packaging_id.id
        result["product_packaging_qty"] = line.product_packaging_qty
        return result
