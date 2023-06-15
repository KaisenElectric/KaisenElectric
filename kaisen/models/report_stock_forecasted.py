from odoo import models


class ReplenishmentReport(models.AbstractModel):
    _inherit = "report.stock.report_product_product_replenishment"

    def _get_report_data(self, product_template_ids=False, product_variant_ids=False):
        if self.env["ir.config_parameter"].sudo().get_param("is_availability_including_packaging") and self.env.context.get("sale_line_to_match_id"):
            line_id = self.env["sale.order.line"].search([("id", "=", self.env.context.get("sale_line_to_match_id"))])
            self = self.with_context(package_id=line_id.product_packaging_id.stock_quant_package_id.id or None)
        return super(ReplenishmentReport, self)._get_report_data(product_template_ids, product_variant_ids)
