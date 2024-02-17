from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    registry_number = fields.Char(string="Registry Number")
    user_id = fields.Many2one(inverse="_inverse_user_id")
    country_id = fields.Many2one(inverse="_inverse_country_id")
    has_default_analytic_rule = fields.Boolean(
        string="Default Analytic Rule",
        compute="_compute_has_default_analytic_rule",
        inverse="_inverse_has_default_analytic_rule",
        readonly=False,
    )

    @api.onchange("user_id")
    def _onchange_user_id(self):
        """
        Method change team_id depends on user_id
        """
        for record in self:
            id_team = False
            user_id = record.user_id
            if user_id:
                team_id = self.env["crm.team"].search([
                    ("member_ids", "=", user_id.id),
                ], limit=1)
                id_team = team_id.id
            record.update({
                "team_id": id_team,
            })

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
        if not self.user_id.has_group("sales_team.group_sale_manager") and (self.user_id.name or self.country_id.name):
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

    def _compute_has_default_analytic_rule(self):
        partner_with_rule_ids = self.env["account.analytic.default"].search([
            ("partner_id", "in", self.ids)
        ]).partner_id
        partner_with_rule_ids.update({"has_default_analytic_rule": True})
        (self - partner_with_rule_ids).update({"has_default_analytic_rule": False})

    def _prepare_data_for_new_rules(self):
        analytic_account_by_user = {}
        new_analytic_account = self.user_id.mapped('name')
        for analytic_account_id in  self.env["account.analytic.account"].search([
            ("name", "in", new_analytic_account)
        ]):
            analytic_account_by_user[analytic_account_id.name] = analytic_account_id.id
        new_analytic_account = set(new_analytic_account) - analytic_account_by_user.keys()
        if new_analytic_account:
            for analytic_account_id in self.env["account.analytic.account"].create([
                {"name": name} for name in new_analytic_account
            ]):
                analytic_account_by_user[analytic_account_id.name] = analytic_account_id.id

        analytic_tag_by_country = {}
        new_analytic_tag = self.country_id.mapped('name')
        for analytic_tag_id in  self.env["account.analytic.tag"].search([
            ("name", "in", new_analytic_tag)
        ]):
            analytic_tag_by_country[analytic_tag_id.name] = analytic_tag_id.id
        new_analytic_tag = set(new_analytic_tag) - analytic_tag_by_country.keys()
        if new_analytic_tag:
            for analytic_tag_id in self.env["account.analytic.tag"].create([
                {"name": name} for name in new_analytic_tag
            ]):
                analytic_tag_by_country[analytic_tag_id.name] = analytic_tag_id.id
        result = []
        for partner_id in self:
            data = {}
            if partner_id.user_id.name in analytic_account_by_user:
                data['analytic_id'] = analytic_account_by_user[partner_id.user_id.name]
            if partner_id.country_id.name in analytic_tag_by_country:
                data['analytic_tag_ids'] = [(6, 0, [analytic_tag_by_country[partner_id.country_id.name]])]
            if data:
                result.append({**data, "partner_id": partner_id.id})
        return result

    def _inverse_has_default_analytic_rule(self):
        partner_with_rule_ids = self.env["account.analytic.default"].search([
            ("partner_id", "in", self.ids)
        ]).partner_id
        self_with_rule_ids = self.filtered('has_default_analytic_rule')
        new_rules = (self_with_rule_ids - partner_with_rule_ids)._prepare_data_for_new_rules()
        if new_rules:
            self.env["account.analytic.default"].create(new_rules)
        self.env["account.analytic.default"].search([
            ("partner_id", "in", (partner_with_rule_ids & (self - self_with_rule_ids)).ids)
        ]).unlink()
