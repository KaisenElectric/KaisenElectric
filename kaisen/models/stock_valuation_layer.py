from odoo import models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    def create(self, values):
        result = super().create(values)
        if self.env.context.get("force_period_date") and result.id:
            create_date = self.env.context.get("force_period_date").strftime("%Y-%m-%d %H:%M:%S")
            self._cr.execute("UPDATE stock_valuation_layer SET create_date = %s WHERE id=%s", (create_date, result.id))
        return result
