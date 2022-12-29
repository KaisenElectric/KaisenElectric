from odoo import models, fields, api, _
import requests
from urllib.parse import urlparse
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    logismart_api_key = fields.Char(string="Logismart API Key")
    logismart_api_url = fields.Char(string="Logismart API URL")

    @api.model
    def set_values(self):
        """Set values"""
        result = super(ResConfigSettings, self).set_values()
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("logismart_api_key", self.logismart_api_key)
        params.set_param("logismart_api_url", self.logismart_api_url)
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
            }
        )
        return result

    def send_request_to_logismart(self, method, url, payload):
        """Sends request to logismart"""
        api_url = self.env["ir.config_parameter"].sudo().get_param("logismart_api_url")
        api_key = self.env["ir.config_parameter"].sudo().get_param("logismart_api_key")
        url = f"{api_url}{url}"
        headers = {
            "api-key": api_key,
            "Host": urlparse(url).hostname,
        }
        response = requests.request(method, url, headers=headers, params=payload)
        data = response.json()
        if not response.ok:
            message = "Logismart Error\n" + data.get("error", "")
            for key, value in data.get("errors", {}).items():
                error = f"{key}: {value}"
                message = f"{message}\n{error}"
            raise UserError(message)
        return data
