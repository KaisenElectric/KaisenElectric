from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    registry_number = fields.Char(string="Registry Number")
    user_id = fields.Many2one(inverse="_inverse_user_id")
    country_id = fields.Many2one(inverse="_inverse_country_id")

    def _inverse_user_id(self):
        """
        Method update account.analytic.default depends on user_id
        """
        for record in self:
            record.update_account_analytic_default()

    def _inverse_country_id(self):
        """
        Method update account.analytic.default depends on country_id
        """
        for record in self:
            record.update_account_analytic_default()

    def update_account_analytic_default(self):
        """
        Method update account.analytic.default depends on country_id or user_id
        """
        self.ensure_one()
        account_analytic_account_id = self.env["account.analytic.account"]
        account_analytic_tag_id = self.env["account.analytic.tag"]
        if self.user_id.name:
            account_analytic_account_id = self.get_or_create_account_analytic_account()
        if self.country_id.name:
            account_analytic_tag_id = self.get_or_create_account_analytic_tag()
        if self.user_id.name or self.country_id.name:
            account_analytic_default_id = self.get_or_create_account_analytic_default()
            account_analytic_default_id.write({
                "analytic_id": account_analytic_account_id.id or account_analytic_default_id.analytic_id.id,
                "analytic_tag_ids": [(6, 0, account_analytic_tag_id.ids)],
            })

    def get_or_create_account_analytic_account(self):
        """
        Method get exist account_analytic_account or create new with name = user_id.name
        """
        self.ensure_one()
        utils_obj = self.env["icode.model.utils"]
        account_analytic_account_id = utils_obj.get_or_create_record(
            model_name="account.analytic.account",
            search_domain=[("name", "=", self.user_id.name)],
            name=self.user_id.name,
        )
        return account_analytic_account_id

    def get_or_create_account_analytic_tag(self):
        """
        Method get exist tag or create new with name = country_id.name
        """
        self.ensure_one()
        utils_obj = self.env["icode.model.utils"]
        account_analytic_tag_id = utils_obj.get_or_create_record(
            model_name="account.analytic.tag",
            search_domain=[("name", "=", self.country_id.name)],
            name=self.country_id.name,
        )
        return account_analytic_tag_id

    def get_or_create_account_analytic_default(self):
        """
        Method get exist account_analytic_default or create new
        """
        self.ensure_one()
        utils_obj = self.env["icode.model.utils"]
        account_analytic_default_id = utils_obj.get_or_create_record(
            model_name="account.analytic.default",
            search_domain=[("partner_id", "=", self.id)],
            partner_id=self.id,
        )
        return account_analytic_default_id

