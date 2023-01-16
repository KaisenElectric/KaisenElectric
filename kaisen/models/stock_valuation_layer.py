from odoo import models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    def create(self, values):
        result = super().create(values)
        if self.env.context.get("forced_create_date"):
            create_date = self.env.context.get("forced_create_date")
            self._cr.execute("UPDATE stock_valuation_layer SET create_date = %s WHERE id=%s", (create_date, result.id))
        return result
