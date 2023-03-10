from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)
from lxml import etree
from odoo.addons.web.controllers.main import xml2json_from_elementtree
import requests


class ResCompany(models.Model):
    _inherit = "res.company"

    parent_ids = fields.Many2many(
        comodel_name="res.company",
        name="Parent companies",
        relation="parent_companies_rel",
        column1="child_id",
        column2="parent_id",
    )

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
            _logger.info(parse_results)
            if parse_results == False:
                # We check == False, and don't use bool conversion, as an empty
                # dict can be returned, if none of the available currencies is supported by the provider
                _logger.warning('Unable to connect to the online exchange rate platform %s. The web service may be temporary down.', currency_provider)
                rslt = False
            else:
                companies._generate_currency_rates(parse_results)

        return rslt

    # def _parse_ecb_data(self, available_currencies):
    #     ''' This method is used to update the currencies by using ECB service provider.
    #         Rates are given against EURO
    #     '''
    #     request_url = "http://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    #     try:
    #         parse_url = requests.request('GET', request_url)
    #     except:
    #         #connection error, the request wasn't successful
    #         return False
    #
    #     xmlstr = etree.fromstring(parse_url.content)
    #     data = xml2json_from_elementtree(xmlstr)
    #     node = data['children'][2]['children'][0]
    #     available_currency_names = available_currencies.mapped('name')
    #     rslt = {x['attrs']['currency']:(float(x['attrs']['rate']), fields.Date.today()) for x in node['children'] if x['attrs']['currency'] in available_currency_names}
    #
    #     if rslt and 'EUR' in available_currency_names:
    #         rslt['EUR'] = (1.0, fields.Date.today())
    #     _logger.info(rslt)
    #     return rslt
