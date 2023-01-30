from odoo import models, fields, api, _
import requests
from urllib.parse import urlparse
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)
from lxml import etree
from odoo.addons.web.controllers.main import xml2json_from_elementtree


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def update_currency_rates(self):
        ''' This method is used to update all currencies given by the provider.
        It calls the parse_function of the selected exchange rates provider automatically.

        For this, all those functions must be called _parse_xxx_data, where xxx
        is the technical name of the provider in the selection field. Each of them
        must also be such as:
            - It takes as its only parameter the recordset of the currencies
              we want to get the rates of
            - It returns a dictionary containing currency codes as keys, and
              the corresponding exchange rates as its values. These rates must all
              be based on the same currency, whatever it is. This dictionary must
              also include a rate for the base currencies of the companies we are
              updating rates from, otherwise this will result in an error
              asking the user to choose another provider.

        :return: True if the rates of all the records in self were updated
                 successfully, False if at least one wasn't.
        '''
        rslt = True
        active_currencies = self.env['res.currency'].search([])
        for (currency_provider, companies) in self._group_by_provider().items():
            _logger.info(currency_provider)
            _logger.info(companies)
            parse_results = None
            parse_function = getattr(companies, '_parse_' + currency_provider + '_data')
            parse_results = parse_function(active_currencies)

            if parse_results == False:
                # We check == False, and don't use bool conversion, as an empty
                # dict can be returned, if none of the available currencies is supported by the provider
                _logger.warning('Unable to connect to the online exchange rate platform %s. The web service may be temporary down.', currency_provider)
                rslt = False
            else:
                companies._generate_currency_rates(parse_results)

        return rslt

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
