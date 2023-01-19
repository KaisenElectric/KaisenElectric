from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id,
                               values):
        move_values = super()._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin,
                                                     company_id, values)
        if values.get("product_packaging_id"):
            move_values["package_level_id"] = self.env["stock.package_level"].create({
                "package_id": values.get("product_packaging_id").stock_quant_package_id.id,
                "company_id": company_id.id,
            }).id
        return move_values

    def _get_custom_move_fields(self):
        fields = super()._get_custom_move_fields()
        fields += ["package_level_id"]
        return fields
