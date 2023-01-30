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

    def _parse_ecb_data(self, available_currencies):
        ''' This method is used to update the currencies by using ECB service provider.
            Rates are given against EURO
        '''
        request_url = "http://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
        try:
            parse_url = requests.request('GET', request_url)
        except:
            #connection error, the request wasn't successful
            return False

        xmlstr = etree.fromstring(parse_url.content)
        data = xml2json_from_elementtree(xmlstr)
        node = data['children'][2]['children'][0]
        available_currency_names = available_currencies.mapped('name')
        rslt = {x['attrs']['currency']:(float(x['attrs']['rate']), fields.Date.today()) for x in node['children'] if x['attrs']['currency'] in available_currency_names}

        if rslt and 'EUR' in available_currency_names:
            rslt['EUR'] = (1.0, fields.Date.today())
        _logger.info(rslt)
        return rslt
