from odoo import api, fields, models, _


class ITMaintenance(models.Model):
    _name = "it.maintenance"
    _description = "IT Maintenance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "maintenance_date desc, id desc"

    name = fields.Char(
        string="Maintenance No.", required=True, copy=False, readonly=True,
        default=lambda self: _("New")
    )
    asset_id = fields.Many2one("it.asset", string="Asset", required=True, tracking=True)
    employee_id = fields.Many2one("hr.employee", related="asset_id.employee_id", string="Assigned Employee", store=True, readonly=True)
    department_id = fields.Many2one("hr.department", related="asset_id.department_id", string="Department", store=True, readonly=True)
    maintenance_date = fields.Date(
        string="Maintenance Date", required=True,
        default=fields.Date.context_today, tracking=True
    )
    maintenance_type = fields.Selection([
        ("preventive", "Preventive"),
        ("repair", "Repair"),
        ("upgrade", "Upgrade"),
        ("inspection", "Inspection"),
        ("other", "Other"),
    ], string="Type", default="preventive", required=True, tracking=True)
    technician_id = fields.Many2one("res.users", string="Technician", tracking=True)
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    cost = fields.Monetary(string="Cost")
    company_id = fields.Many2one(
        "res.company", related="asset_id.company_id",
        store=True, readonly=True
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True
    )
    description = fields.Html(string="Work Description")
    next_maintenance_date = fields.Date(string="Next Maintenance")
    state = fields.Selection([
        ("planned", "Planned"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ], string="Status", default="planned", required=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("it.maintenance") or _("New")
        return super().create(vals_list)

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset(self):
        self.write({"state": "planned"})
