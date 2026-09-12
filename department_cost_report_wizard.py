from odoo import fields, models
from odoo.exceptions import UserError


class DepartmentCostReportWizard(models.TransientModel):
    _name = "department.cost.report.wizard"
    _description = "IT Department Cost Report Wizard"

    date_from = fields.Date(string="From Date", required=True,
                             default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string="To Date", required=True, default=fields.Date.today)
    department_ids = fields.Many2many("hr.department", string="Departments",
                                       help="Leave empty to include all departments")
    charge_state = fields.Selection([
        ("all", "All"),
        ("not_charged", "Not Charged Only"),
        ("charged", "Charged Only"),
    ], string="Charge Status", default="all", required=True)

    def _get_domain(self):
        domain = [
            ("cost_date", ">=", self.date_from),
            ("cost_date", "<=", self.date_to),
        ]
        if self.department_ids:
            domain.append(("department_id", "in", self.department_ids.ids))
        if self.charge_state != "all":
            domain.append(("charge_state", "=", self.charge_state))
        return domain

    def action_view_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError("'From Date' cannot be after 'To Date'.")

        action = self.env.ref("it_management.action_it_department_cost_report").read()[0]
        action["domain"] = self._get_domain()
        action["context"] = {"group_by": ["department_id"]}
        return action
