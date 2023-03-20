from odoo import models


class ModelUtils(models.AbstractModel):
    _name = "icode.model.utils"
    _description = "Model utils"

    def get_or_create_record(self, model_name: str, search_domain: list, **kwargs):
        """
        General method for searching or creating record
        """
        try:
            record_id = self.env[model_name].search(search_domain, limit=1)
            if not record_id:
                record_id = self.env[model_name].create(kwargs)
            return record_id
        except (AttributeError, Exception):
            return self.env[model_name].create(kwargs)
