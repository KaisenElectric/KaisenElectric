from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.payment import utils as payment_utils


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def get_logismart_delivery_posts(self):
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
        data = self.env["res.config.settings"].send_request_to_logismart("get", "/couriers/posts", payload)
        return [(x.get("post_id"), x.get("address")) for x in data.get("posts") if x.get("city") == city]

    external_integration_id = fields.Many2one(comodel_name="external.integration", string="External Integration")
    logismart_delivery_method = fields.Integer(related="carrier_id.logismart_delivery_method", string="Logismart Delivery Method")
    country_code = fields.Char(related="sale_id.partner_shipping_id.country_id.code", string="Country Code")
    city = fields.Char(related="sale_id.partner_shipping_id.city", string="City")
    logismart_delivery_post = fields.Char(string="Logismart Delivery Post")

    @api.constrains("state")
    def _check_state(self):
        """Checks field product_packaging_qty for integer when moving stock picking to done stage"""
        for record_id in self:
            if record_id.state == "done":
                for move_id in record_id.move_ids_without_package:
                    if not move_id.product_packaging_qty.is_integer():
                        raise UserError("Packaging Quality must be whole number")
                if record_id.external_integration_id == self.env.ref("kaisen.external_integration_logismart"):
                    if record_id.picking_type_id.code == "incoming":
                        record_id.create_arrival_in_logismart()
                    elif record_id.picking_type_id.code == "outgoing":
                        record_id.create_order_in_logismart()

    def get_products_for_logismart(self):
        """Returns products for logismart"""
        self.ensure_one()
        products = []
        for move_id in self.move_ids_without_package:
            if not move_id.product_packaging_qty.is_integer() or move_id.product_packaging_qty <= 0:
                raise UserError("Packaging Quality must be whole number")
            products.append(
                {
                    "product_code": move_id.get_logismart_product_code(),
                    "quantity": int(move_id.product_packaging_qty),
                }
            )
        return products

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
            first_name, last_name = payment_utils.split_partner_name(self.partner_id.name)
            delivery = {
                "method": self.carrier_id.logismart_delivery_method,
            }
            payload = {
                "order_code": self.name,
                "products": products,
                "delivery": delivery,
                "customer_code": f"{first_name} {last_name}",
                "first_name": first_name,
                "last_name": last_name,
                "email": self.partner_id.email,
                "phone": self.partner_id.phone,
                "address": self.sale_id.partner_shipping_id.street_name,
                "house": self.sale_id.partner_shipping_id.street_number,
                "postcode": self.sale_id.partner_shipping_id.zip,
                "city": self.sale_id.partner_shipping_id.city,
                "country_code": self.sale_id.partner_shipping_id.country_id.code,
                "total": self.sale_id.amount_total,
            }
            self.env["res.config.settings"].send_request_to_logismart("post", "/orders/add", payload)
