# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import models


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _get_html_link(self, title=None):
        """Generate the record html reference for chatter use.

        :param str title: optional reference title, the record display_name
            is used if not provided. The title/display_name will be escaped.
        :returns: generated html reference,
            in the format <a href data-oe-model="..." data-oe-id="...">title</a>
        :rtype: str
        """
        self.ensure_one()
        return Markup("<a href=# data-oe-model='%s' data-oe-id='%s'>%s</a>") % (
            self._name, self.id, title or self.display_name)
