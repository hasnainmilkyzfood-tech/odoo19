from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ITDepartmentChargeMixin(models.AbstractModel):
    """Shared logic to charge a record's IT cost (parts + service/labor) back
    to the consuming department's analytic account via a journal entry.

    Models that use this mixin must implement:
      - _compute_charge_department(): sets `charge_department_id`
      - _get_charge_amount(): returns the amount (float) to charge
      - _get_charge_description(): returns a label for the journal entry
    and must already provide a `company_id` field.
    """
    _name = "it.department.charge.mixin"
    _description = "Department Cost Charge-back Mixin"

    charge_department_id = fields.Many2one(
        "hr.department", string="Charged Department",
        compute="_compute_charge_department", store=True,
    )
    charge_state = fields.Selection([
        ("not_charged", "Not Charged"),
        ("charged", "Charged"),
    ], string="Charge Status", default="not_charged", copy=False, tracking=True)
    charge_move_id = fields.Many2one(
        "account.move", string="Charge Journal Entry", readonly=True, copy=False
    )

    def _compute_charge_department(self):
        for rec in self:
            rec.charge_department_id = False

    def _get_charge_amount(self):
        self.ensure_one()
        return 0.0

    def _get_charge_description(self):
        self.ensure_one()
        return self.display_name

    def action_charge_department(self):
        AccountMove = self.env["account.move"]
        for rec in self:
            if rec.charge_state == "charged":
                raise UserError(_("This record has already been charged to a department."))

            department = rec.charge_department_id
            if not department:
                raise UserError(_(
                    "No department could be determined for this record. "
                    "Make sure the employee or asset has a department assigned."
                ))
            if not department.it_analytic_account_id:
                raise UserError(_(
                    "Set an 'IT Cost Center' analytic account on department '%s' first "
                    "(Employees > Departments)."
                ) % department.name)

            amount = rec._get_charge_amount()
            if amount <= 0:
                raise UserError(_("There is no cost on this record to charge."))

            company = rec.company_id or self.env.company
            expense_account = company.it_default_expense_account_id
            journal = company.it_default_journal_id
            if not expense_account or not journal:
                raise UserError(_(
                    "Configure the 'Default IT Expense Account' and 'Default IT Journal' "
                    "in IT Management Settings first."
                ))

            description = rec._get_charge_description()
            debit_line = (0, 0, {
                "name": description,
                "account_id": expense_account.id,
                "debit": amount,
                "credit": 0.0,
                "analytic_distribution": {str(department.it_analytic_account_id.id): 100.0},
            })
            credit_vals = {
                "name": description,
                "account_id": expense_account.id,
                "debit": 0.0,
                "credit": amount,
            }
            recovery_analytic = company.it_recovery_analytic_account_id
            if recovery_analytic:
                credit_vals["analytic_distribution"] = {str(recovery_analytic.id): 100.0}
            credit_line = (0, 0, credit_vals)

            move = AccountMove.create({
                "move_type": "entry",
                "journal_id": journal.id,
                "date": fields.Date.context_today(rec),
                "ref": description,
                "company_id": company.id,
                "line_ids": [debit_line, credit_line],
            })
            rec.write({"charge_state": "charged", "charge_move_id": move.id})
            if "message_post" in dir(rec):
                rec.message_post(body=_(
                    "Cost of %(amount)s charged to department %(dept)s via journal entry %(move)s.",
                    amount=amount, dept=department.name, move=move.display_name,
                ))
        return True

    def action_view_charge_move(self):
        self.ensure_one()
        if not self.charge_move_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.charge_move_id.id,
            "view_mode": "form",
            "target": "current",
        }
