from odoo import api, fields, models, _


class ITAccessRequest(models.Model):
    _name = "it.access.request"
    _description = "IT Access Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Request No.", readonly=True, copy=False, default=lambda self: _("New"))
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, default=lambda self: self._default_employee(), tracking=True)
    department_id = fields.Many2one("hr.department", related="employee_id.department_id", store=True, readonly=True)
    request_type = fields.Selection([
        ("software", "Software Access"), ("folder", "Folder / Drive Access"),
        ("system", "System Access"), ("email", "Email / Distribution List"),
        ("vpn", "VPN / Remote Access"), ("other", "Other")
    ], string="Access Type", required=True, default="software", tracking=True)
    resource_name = fields.Char(string="Software / Folder / System", required=True, tracking=True)
    reason = fields.Text(string="Business Justification", required=True)
    approver_id = fields.Many2one("res.users", string="Approver")
    state = fields.Selection([
        ("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"),
        ("rejected", "Rejected"), ("done", "Provisioned")
    ], default="draft", tracking=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)

    def _default_employee(self):
        return self.env["hr.employee"].search([("user_id", "=", self.env.user.id)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("it.access.request") or _("New")
        return super().create(vals_list)

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_done(self):
        self.write({"state": "done"})

    def action_reset(self):
        self.write({"state": "draft"})
