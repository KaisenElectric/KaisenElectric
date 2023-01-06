from odoo import models, fields, api, _
import requests
from urllib.parse import urlparse
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    logismart_api_key = fields.Char(string="Logismart API Key")
    logismart_api_url = fields.Char(string="Logismart API URL")
    logismart_username = fields.Char(string="Logismart Username")
    logismart_password = fields.Char(string="Logismart Password")

    @api.model
    def set_values(self):
        """Set values"""
        result = super(ResConfigSettings, self).set_values()
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("logismart_api_key", self.logismart_api_key)
        params.set_param("logismart_api_url", self.logismart_api_url)
        params.set_param("logismart_username", self.logismart_username)
        params.set_param("logismart_password", self.logismart_password)
        return result

    @api.model
    def get_values(self):
        """Get values"""
        result = super(ResConfigSettings, self).get_values()
        params = self.env["ir.config_parameter"].sudo()
        result.update(
            {
                "logismart_api_key": params.get_param("logismart_api_key"),
                "logismart_api_url": params.get_param("logismart_api_url"),
                "logismart_username": params.get_param("logismart_username"),
                "logismart_password": params.get_param("logismart_password"),
            }
        )
        return result

    def send_request_to_logismart(self, method, url, payload):
        """Sends request to logismart"""
        api_url = self.env["ir.config_parameter"].sudo().get_param("logismart_api_url")
        api_key = self.env["ir.config_parameter"].sudo().get_param("logismart_api_key")
        username = self.env["ir.config_parameter"].sudo().get_param("logismart_username")
        password = self.env["ir.config_parameter"].sudo().get_param("logismart_password")
        if not api_url or not api_key or not username or not password:
            raise UserError("Check fields for integration with Logismart in system settings")
        url = f"{api_url}{url}"
        headers = {
            "api-key": api_key,
            "Host": urlparse(url).hostname,
        }
        if method == "get":
            response = requests.get(url, headers=headers, params=payload, auth=(username, password))
        else:
            response = requests.post(url, headers=headers, json=payload, auth=(username, password))
        data = response.json()
        if not response.ok:
            message = "Logismart Errors:\n" + "\n".join(data.get("errors", {}).values())
            raise UserError(message)
        return data
