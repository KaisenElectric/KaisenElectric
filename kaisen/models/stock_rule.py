from odoo import models, api


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id,
                               values):
        """
        OVERRIDE
        Added package_level_id field when calculating which lines should be unique
        """
        move_values = super()._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin,
                                                     company_id, values)
        if values.get("product_packaging_id"):
            move_values["package_level_id"] = self.env["stock.package_level"].create({
                "package_id": values.get("product_packaging_id").stock_quant_package_id.id,
                "company_id": company_id.id,
            }).id
        return move_values

    def _get_custom_move_fields(self):
        """
        OVERRIDE
        Added package_level_id field when calculating which lines should be unique
        """
        fields = super()._get_custom_move_fields()
        fields += ["package_level_id"]
        return fields

    @api.model
    def _get_procurements_to_merge_groupby(self, procurement):
        """
        OVERRIDE
        Added product_packaging_id and price_unit fields when calculating which so lines should be unique
        """
        return procurement.values.get("product_packaging_id").id if procurement.values.get(
            "product_packaging_id") else False \
            , procurement.values.get("move_dest_ids").sale_line_id.price_unit if procurement.values.get(
            "move_dest_ids") else False, \
               super()._get_procurements_to_merge_groupby(procurement)

    @api.model
    def _get_procurements_to_merge_sorted(self, procurement):
        """
        OVERRIDE
        Added product_packaging_id and price_unit fields when calculating which so lines should be unique
        """
        return procurement.values.get("product_packaging_id").id if procurement.values.get(
            "product_packaging_id") else False, procurement.values.get(
            "move_dest_ids").sale_line_id.price_unit if procurement.values.get(
            "move_dest_ids") else False, super()._get_procurements_to_merge_sorted(procurement)

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        """
        OVERRIDE
        Not updated price_unit when merged purchase order line
        """
        result = super()._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)
        result.pop("price_unit")
        return result
