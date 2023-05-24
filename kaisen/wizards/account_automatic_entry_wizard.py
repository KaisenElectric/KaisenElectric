from odoo import models, fields, api, _
from collections import defaultdict
from odoo.exceptions import UserError
import json


class AccountAutomaticEntryWizard(models.TransientModel):
    _inherit = "account.automatic.entry.wizard"

    action = fields.Selection(
        selection_add=[("change_partner", "Change Partner")], ondelete={"change_partner": "cascade"}
    )
    partner_id = fields.Many2one(comodel_name="res.partner", string="To Partner")
    is_user_exist_in_lines = fields.Boolean(string="User exist in lines", compute="_compute_is_user_exist_in_lines")

    @api.depends("partner_id", "move_line_ids")
    def _compute_is_user_exist_in_lines(self):
        """
        Computes is_user_exist_in_lines field by lines and filed partner_id
        """
        for record_id in self:
            if not record_id.partner_id:
                record_id.is_user_exist_in_lines = False
            elif record_id.partner_id in self.move_line_ids.mapped("partner_id"):
                record_id.is_user_exist_in_lines = True
            else:
                record_id.is_user_exist_in_lines = False

    @api.depends(
        "move_line_ids",
        "journal_id",
        "revenue_accrual_account",
        "expense_accrual_account",
        "percentage",
        "date",
        "account_type",
        "action",
        "destination_account_id",
        "partner_id",
    )
    def _compute_move_data(self):
        """
        OVERWRITE
        Added logic for action change_partner
        """
        super()._compute_move_data()
        for record_id in self:
            if record_id.action == "change_partner":
                record_id.move_data = json.dumps(record_id._get_move_dict_vals_change_partner())

    def do_action(self):
        """
        OVERWRITE
        Added logic for action change_partner
        """
        move_vals = json.loads(self.move_data)
        if self.action == "change_partner":
            return self._do_action_change_partner(move_vals)
        return super().do_action()

    def _compute_preview_move_data(self):
        """
        OVERWRITE
        Added logic for action change_partner
        """
        for record in self:
            preview_columns = [
                {"field": "account_id", "label": _("Account")},
                {"field": "name", "label": _("Label")},
                {"field": "debit", "label": _("Debit"), "class": "text-right text-nowrap"},
                {"field": "credit", "label": _("Credit"), "class": "text-right text-nowrap"},
            ]
            # kaisen: Changes start
            if record.action in ("change_account", "change_partner"):
                # kaisen: Changes end
                preview_columns[2:2] = [{"field": "partner_id", "label": _("Partner")}]

            move_vals = json.loads(record.move_data)
            preview_vals = []
            for move in move_vals[:4]:
                preview_vals += [
                    self.env["account.move"]._move_dict_to_preview_vals(move, record.company_id.currency_id)
                ]
            preview_discarded = max(0, len(move_vals) - len(preview_vals))

            record.preview_move_data = json.dumps(
                {
                    "groups_vals": preview_vals,
                    "options": {
                        "discarded_number": _("%d moves", preview_discarded) if preview_discarded else False,
                        "columns": preview_columns,
                    },
                }
            )

    def _get_move_dict_vals_change_partner(self):
        """
        Returns data lines for wizard, when changes partner
        """
        line_vals = []

        # Group data from selected move lines
        counterpart_balances = defaultdict(lambda: defaultdict(lambda: 0))
        grouped_source_lines = defaultdict(lambda: self.env["account.move.line"])

        for line in self.move_line_ids:
            counterpart_currency = line.currency_id
            counterpart_amount_currency = line.amount_currency
            counterpart_balances[(line.partner_id, counterpart_currency, line.account_id)][
                "amount_currency"
            ] += counterpart_amount_currency
            counterpart_balances[(line.partner_id, counterpart_currency, line.account_id)]["balance"] += line.balance
            if not counterpart_balances[(line.partner_id, counterpart_currency, line.account_id)]["lines"]:
                counterpart_balances[(line.partner_id, counterpart_currency, line.account_id)]["lines"] = self.env[
                    "account.move.line"
                ]
            counterpart_balances[(line.partner_id, counterpart_currency, line.account_id)]["lines"] += line
            grouped_source_lines[(line.partner_id, line.currency_id, line.account_id)] += line

        # Generate counterpart lines' vals
        for (counterpart_partner, counterpart_currency, account_id), counterpart_vals in counterpart_balances.items():
            source_accounts = self.move_line_ids.mapped("account_id")
            if not counterpart_currency.is_zero(counterpart_vals["amount_currency"]):
                line_vals.append(
                    {
                        "name": ", ".join([x.name for x in counterpart_vals["lines"]]),
                        "debit": counterpart_vals["balance"] > 0
                        and self.company_id.currency_id.round(counterpart_vals["balance"])
                        or 0,
                        "credit": counterpart_vals["balance"] < 0
                        and self.company_id.currency_id.round(-counterpart_vals["balance"])
                        or 0,
                        "account_id": account_id.id,
                        "partner_id": self.partner_id.id or None,
                        "amount_currency": counterpart_currency.round(
                            (counterpart_vals["balance"] < 0 and -1 or 1) * abs(counterpart_vals["amount_currency"])
                        )
                        or 0,
                        "currency_id": counterpart_currency.id,
                    }
                )

        # Generate change_account lines' vals
        for (partner, currency, account), lines in grouped_source_lines.items():
            account_balance = sum(line.balance for line in lines)
            if not self.company_id.currency_id.is_zero(account_balance):
                account_amount_currency = currency.round(sum(line.amount_currency for line in lines))
                line_vals.append(
                    {
                        "name": ", ".join([x.name for x in lines]),
                        "debit": account_balance < 0 and self.company_id.currency_id.round(-account_balance) or 0,
                        "credit": account_balance > 0 and self.company_id.currency_id.round(account_balance) or 0,
                        "account_id": account.id,
                        "partner_id": partner.id or None,
                        "currency_id": currency.id,
                        "amount_currency": (account_balance > 0 and -1 or 1) * abs(account_amount_currency),
                    }
                )

        return [
            {
                "currency_id": self.journal_id.currency_id.id or self.journal_id.company_id.currency_id.id,
                "move_type": "entry",
                "journal_id": self.journal_id.id,
                "date": fields.Date.to_string(self.date),
                "ref": _("Adjusting Entry"),
                "line_ids": [(0, 0, line) for line in line_vals],
            }
        ]

    def _do_action_change_partner(self, move_vals):
        """
        Creates lines from wizard, when changes partner
        """
        if not self.partner_id or self.partner_id in self.move_line_ids.mapped("partner_id"):
            raise UserError("This user is exist in lines")
        new_move = self.env["account.move"].create(move_vals)
        new_move._post()

        # Group lines
        grouped_lines = defaultdict(lambda: self.env["account.move.line"])
        for line in self.move_line_ids:
            grouped_lines[(line.partner_id, line.currency_id, line.account_id)] += line

        # Reconcile
        for (partner, currency, account), lines in grouped_lines.items():
            if account.reconcile:
                to_reconcile = lines + new_move.line_ids.filtered(
                    lambda x: x.account_id == account and x.partner_id == partner and x.currency_id == currency
                )
                to_reconcile.reconcile()

        # Log the operation on source moves
        acc_transfer_per_move = defaultdict(lambda: defaultdict(lambda: 0))  # dict(move, dict(account, balance))
        for line in self.move_line_ids:
            acc_transfer_per_move[line.move_id][line.account_id] += line.balance

        for move, balances_per_account in acc_transfer_per_move.items():
            message_to_log = self._format_transfer_source_log(balances_per_account, new_move)
            if message_to_log:
                move.message_post(body=message_to_log)

        # Log on target move as well
        new_move.message_post(body=self._format_new_transfer_move_log(acc_transfer_per_move))

        return {
            "name": _("Transfer"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "account.move",
            "res_id": new_move.id,
        }
