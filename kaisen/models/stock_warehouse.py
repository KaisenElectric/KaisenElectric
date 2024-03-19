from odoo import api, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
    )

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Override method to allow searching records even if the current user
        does not have read access to them.
        """
        if self.env.context.get("allow_wh"):
            self = self.sudo()
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        """
        Override method to allow searching records even if the current user
        does not have read access to them.
        """
        if self.env.context.get("allow_wh"):
            self = self.sudo()
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)

    def _read(self, fields):
        """
        Override method to allow searching records even if the current user
        does not have read access to them.
        """
        if self.env.context.get("allow_wh") or "supply_warehouse_id" in fields:
            self = self.sudo()
        return super()._read(fields)
