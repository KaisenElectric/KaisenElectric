from odoo import models, api


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Override method to allow searching records even if the current user
        does not have read access to them.
        """
        if self.env.context.get("allow_wh"):
            self = self.sudo()
        return super().name_search(name=name, args=args, operator=operator, limit=limit)
