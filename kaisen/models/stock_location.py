from odoo import models, fields, api


class StockLocation1(models.Model):
    _inherit = "stock.location"

    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse", compute="_compute_warehouse_id", store=True)

    @api.depends("parent_path", "location_id")
    def _compute_warehouse_id(self):
        no_warehouse = self.filtered(lambda l: not l.company_id or not l.parent_path)
        to_compute = self - no_warehouse
        no_warehouse.update({"warehouse_id": False})
        warehouses = {}
        location_ids = set()
        for location_id in to_compute:
            for lp in location_id.parent_path.split("/"):
                if lp:
                    location_ids.add(int(lp))
        for wh in self.env["stock.warehouse"].search([("view_location_id", "in", list(location_ids))]):
            warehouses[wh.view_location_id.id] = wh.id
        for l in to_compute:
            warehouse_id = False
            for lp in l.parent_path.split("/")[::-1]:
                if not lp or int(lp) not in warehouses:
                    continue
                warehouse_id = warehouses[int(lp)]

            l.warehouse_id = warehouse_id
