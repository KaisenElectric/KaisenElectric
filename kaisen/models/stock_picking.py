from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.payment import utils as payment_utils
from odoo.tests import Form
import base64

DELIVERY_INCOTERMS = [("DDP", "DDP"), ("DAP", "DAP")]
from datetime import timedelta


class StockPicking(models.Model):
    _inherit = "stock.picking"

    external_integration_id = fields.Many2one(comodel_name="external.integration", string="External Integration")
    logismart_delivery_method = fields.Integer(
        related="carrier_id.logismart_delivery_method", string="Logismart Delivery Method"
    )
    country_code = fields.Char(string="Country Code", compute="_compute_country_code")
    city = fields.Char(string="City", compute="_compute_city")
    logismart_delivery_post = fields.Char(string="Logismart Delivery Post")
    delivery_incoterm = fields.Selection(selection=DELIVERY_INCOTERMS, string="Delivery Incoterm")
    is_packing_operation = fields.Boolean(string="Packing Operation")
    is_external_transfer = fields.Boolean(string="External Transfer")
    picking_type_code = fields.Selection(related="picking_type_id.code", string="Picking Type Code")

    @api.model
    def get_logismart_delivery_posts(self):
        """Return Logismart delivery posts by context and Logismart API"""
        logismart_delivery_method = self.env.context.get("logismart_delivery_method")
        country_code = self.env.context.get("country_code")
        city = self.env.context.get("city")
        if not logismart_delivery_method or not country_code or not city:
            return []
        payload = {
            "delivery_id": logismart_delivery_method,
            "country": country_code,
            "fields": "post_id,address,city",
        }
        try:
            data = self.env["res.config.settings"].send_request_to_logismart("get", "/couriers/posts", payload)
        except Exception as e:
            return []
        else:
            return [(x.get("post_id"), x.get("address")) for x in data.get("posts") if x.get("city") == city]

    @api.onchange("is_packing_operation")
    def _onchange_is_packing_operation(self):
        for record_id in self:
            if record_id.is_packing_operation:
                record_id.is_external_transfer = False

    @api.onchange("is_external_transfer")
    def _onchange_is_external_transfer(self):
        for record_id in self:
            if record_id.is_external_transfer:
                record_id.is_packing_operation = False

    @api.depends("is_packing_operation", "sale_id.partner_shipping_id.country_id.code", "location_dest_id.warehouse_id.partner_id.country_id.code")
    def _compute_country_code(self):
        """Computes country code for stock picking"""
        for record_id in self:
            if record_id.is_external_transfer:
                record_id.country_code = record_id.location_dest_id.warehouse_id.partner_id.country_id.code
            elif record_id.is_packing_operation:
                record_id.city = record_id.partner_id.country_id.code
            else:
                record_id.country_code = record_id.sale_id.partner_shipping_id.country_id.code

    @api.depends("is_packing_operation", "sale_id.partner_shipping_id.city", "location_dest_id.warehouse_id.partner_id.city")
    def _compute_city(self):
        """Computes city for stock picking"""
        for record_id in self:
            if record_id.is_external_transfer:
                record_id.city = record_id.location_dest_id.warehouse_id.partner_id.city
            elif record_id.is_packing_operation:
                record_id.city = record_id.partner_id.city
            else:
                record_id.city = record_id.sale_id.partner_shipping_id.city

    @api.constrains("state")
    def _check_state(self):
        """Checks field product_packaging_qty for integer when moving stock picking to done stage"""
        for record_id in self:
            if record_id.state == "done":
                picking_type_code = record_id.picking_type_id.code
                for move_id in record_id.move_ids_without_package:
                    if not move_id.product_packaging_qty.is_integer():
                        raise UserError("Packaging Quality must be whole number")
                if record_id.external_integration_id == self.env.ref("kaisen.external_integration_logismart"):
                    if picking_type_code != "internal" and (record_id.is_packing_operation or record_id.is_external_transfer):
                        raise UserError("Packing Operation only for internal transfers")
                    if picking_type_code == "internal" and record_id.is_packing_operation:
                        record_id.with_context(is_internal_order=True).create_order_in_logismart()
                        record_id.with_context(is_internal_arrival=True).create_arrival_in_logismart()
                    elif picking_type_code == "internal" and record_id.is_external_transfer:
                        record_id.with_context(is_internal_order=True).create_order_in_logismart()
                    elif picking_type_code == "incoming":
                        record_id.create_arrival_in_logismart()
                    elif picking_type_code == "outgoing":
                        record_id.create_order_in_logismart()
                sale_id = self.env["sale.order"]
                if record_id.purchase_id:
                    sale_id = sale_id.search([("auto_purchase_order_id", "=", record_id.purchase_id.id)], limit=1)
                if picking_type_code == "incoming" and sale_id:
                    if sale_id.state not in ("done", "cancel"):
                        sale_id.action_confirm()
                    for picking_id in sale_id.picking_ids:
                        for move_id in picking_id.move_lines:
                            move_id.quantity_done = move_id.product_uom_qty
                        wizard_action = picking_id.button_validate()
                        if wizard_action is not True:
                            Form(
                                self.env[wizard_action["res_model"]].with_context(wizard_action["context"])
                            ).save().process()

    def get_products_for_logismart(self):
        """Returns products for logismart"""
        self.ensure_one()
        products = []
        for move_id in self.move_ids_without_package:
            if self.env.context.get("is_internal_arrival"):
                destination_package_qty = move_id.move_line_ids[:1].result_package_id.product_packaging_id.qty
                self.check_package_qty(destination_package_qty, "Destination Packaging Quantity")
                source_package_qty = move_id.move_line_ids[:1].package_id.product_packaging_id.qty
                self.check_package_qty(source_package_qty, "Source Packaging Quantity")
                quantity = move_id.product_packaging_qty * source_package_qty / destination_package_qty
                self.check_package_qty(quantity, "Transfer Packaging Quantity")
            else:
                self.check_package_qty(move_id.product_packaging_qty, "Packaging Quantity")
                quantity = int(move_id.product_packaging_qty)
            product = {
                "product_code": move_id.get_logismart_product_code(),
                "quantity": quantity,
            }
            if move_id.product_id.hs_code:
                product["hs_code"] = move_id.product_id.hs_code
            products.append(product)
        return products

    @staticmethod
    def check_package_qty(amount, field_name):
        if not amount.is_integer() or amount <= 0:
            raise UserError(f"{field_name} must be whole number")

    def create_arrival_in_logismart(self):
        """Creates arrival in logismart"""
        self.ensure_one()
        products = self.get_products_for_logismart()
        if products:
            payload = {
                "delivery_date": fields.Date.today().strftime("%Y-%m-%d"),
                "products": products,
            }
            self.env["res.config.settings"].send_request_to_logismart("post", "/arrivals/add", payload)

    def create_order_in_logismart(self):
        """Create order in logismart"""
        self.ensure_one()
        products = self.get_products_for_logismart()
        if products:
            if not self.carrier_id:
                raise UserError("Carrier field not filled")
            if not self.carrier_id.logismart_delivery_method:
                raise UserError("You need to fill in Logismart Shipping Method field in Carrier")
            delivery = {
                "method": self.carrier_id.logismart_delivery_method,
            }
            if self.logismart_delivery_post:
                delivery["post"] = int(self.logismart_delivery_post)
            if self.is_external_transfer:
                partner_id = self.location_dest_id.warehouse_id.partner_id
            elif self.is_packing_operation:
                partner_id = self.partner_id
            else:
                partner_id = self.sale_id.partner_shipping_id
            first_name, last_name = payment_utils.split_partner_name(partner_id.name)
            payload = {
                "order_code": self.name,
                "products": products,
                "delivery": delivery,
                "customer_code": f"{first_name} {last_name}",
                "first_name": first_name,
                "last_name": last_name,
                "email": partner_id.email,
                "phone": partner_id.phone,
                "address": partner_id.street_name,
                "house": partner_id.street_number,
                "postcode": partner_id.zip,
                "city": self.city,
                "country_code": partner_id.country_id.code,
                "total": self.sale_id.amount_total,
            }
            if self.delivery_incoterm:
                payload["delivery_incoterm"] = self.delivery_incoterm
            attachment_id = self.env["ir.attachment"].search(
                [("res_model", "=", self._name), ("res_id", "=", self.id)], order="create_date desc", limit=1
            )
            if attachment_id:
                payload["document"] = {
                    "pdf": attachment_id.datas.decode(),
                    "name": attachment_id.name,
                }
            # if method of delivery is "DHL" then hs_code in required for products
            if payload.get("delivery", {}).get("method") in (24, 25, 26, 27, 28, 30, 34, 35, 39):
                for product in payload["products"]:
                    if not product.get("hs_code"):
                        raise UserError(f"HS Code field not filled in product {product.get('product_code')}")
            self.env["res.config.settings"].send_request_to_logismart("post", "/orders/add", payload)
