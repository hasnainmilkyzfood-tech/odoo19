from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ITAsset(models.Model):
    _name = "it.asset"
    _description = "IT Asset"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Asset Name", required=True, tracking=True)
    asset_code = fields.Char(
        string="Asset Code", required=True, copy=False, readonly=True,
        default=lambda self: _("New"), tracking=True
    )
    serial_number = fields.Char(string="Serial Number", tracking=True)
    asset_type = fields.Selection([
        ("laptop", "Laptop"),
        ("desktop", "Desktop"),
        ("monitor", "Monitor"),
        ("printer", "Printer"),
        ("mobile", "Mobile / Tablet"),
        ("network", "Network Device"),
        ("server", "Server"),
        ("accessory", "Accessory"),
        ("other", "Other"),
    ], string="Asset Type", required=True, default="laptop", tracking=True)
    brand = fields.Char(string="Brand")
    model_name = fields.Char(string="Model")
    employee_id = fields.Many2one(
        "hr.employee", string="Assigned Employee", tracking=True,
        domain="[('company_id', 'in', [False, company_id])]"
    )
    department_id = fields.Many2one(
        "hr.department", string="Department",
        related="employee_id.department_id", store=True, readonly=True
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company
    )
    purchase_date = fields.Date(string="Purchase Date")
    purchase_cost = fields.Monetary(string="Purchase Cost")
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True
    )
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    warranty_expiry = fields.Date(string="Warranty Expiry", tracking=True)
    location = fields.Char(string="Location")
    note = fields.Html(string="Notes")
    state = fields.Selection([
        ("available", "Available"),
        ("assigned", "Assigned"),
        ("repair", "Under Repair"),
        ("retired", "Retired"),
        ("lost", "Lost"),
    ], string="Status", default="available", required=True, tracking=True)
    ticket_count = fields.Integer(compute="_compute_ticket_count")

    _asset_code_uniq = models.Constraint(
        "UNIQUE(asset_code)",
        "Asset Code must be unique."
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("asset_code", _("New")) == _("New"):
                vals["asset_code"] = self.env["ir.sequence"].next_by_code("it.asset") or _("New")
            if vals.get("employee_id") and vals.get("state", "available") == "available":
                vals["state"] = "assigned"
        return super().create(vals_list)

    def write(self, vals):
        if "employee_id" in vals:
            vals = dict(vals)
            if vals["employee_id"] and "state" not in vals:
                vals["state"] = "assigned"
            elif not vals["employee_id"] and "state" not in vals and self.filtered(lambda r: r.state == "assigned"):
                vals["state"] = "available"
        return super().write(vals)

    @api.constrains("purchase_date", "warranty_expiry")
    def _check_dates(self):
        for rec in self:
            if rec.purchase_date and rec.warranty_expiry and rec.warranty_expiry < rec.purchase_date:
                raise ValidationError(_("Warranty expiry cannot be before purchase date."))

    def _compute_ticket_count(self):
        grouped = self.env["it.ticket"].read_group(
            [("asset_id", "in", self.ids)], ["asset_id"], ["asset_id"]
        ) if self.ids else []
        counts = {g["asset_id"][0]: g["asset_id_count"] for g in grouped}
        for rec in self:
            rec.ticket_count = counts.get(rec.id, 0)

    def action_view_tickets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("it_management.action_it_ticket")
        action["domain"] = [("asset_id", "=", self.id)]
        action["context"] = {"default_asset_id": self.id}
        return action

    def action_set_available(self):
        self.write({"state": "available", "employee_id": False})

    def action_set_assigned(self):
        self.write({"state": "assigned"})

    def action_set_repair(self):
        self.write({"state": "repair"})

    def action_set_retired(self):
        self.write({"state": "retired"})



class ITAssetAdvanced(models.Model):
    _inherit = "it.asset"

    asset_tag = fields.Char(string="Asset Tag", copy=False, tracking=True)
    serial_number = fields.Char(string="Serial Number", tracking=True)
    hostname = fields.Char(tracking=True)
    ip_address = fields.Char(string="IP Address")
    mac_address = fields.Char(string="MAC Address")
    operating_system = fields.Char(string="Operating System")
    physical_location = fields.Char(string="Physical Location")
    purchase_date = fields.Date()
    warranty_expiry = fields.Date()
    acquisition_cost = fields.Monetary(currency_field="asset_currency_id")
    asset_currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    lifecycle_state = fields.Selection([
        ("stock", "In Stock"), ("assigned", "Assigned"), ("repair", "Under Repair"),
        ("retired", "Retired"), ("disposed", "Disposed")
    ], default="stock", tracking=True)


class ITAssetAccounting(models.Model):
    _inherit = "it.asset"

    assigned_date = fields.Date(string="Assigned Date", tracking=True)
    returned_date = fields.Date(string="Returned Date", tracking=True)
    custodian_id = fields.Many2one("res.users", string="IT Custodian", tracking=True)
    purchase_order_id = fields.Many2one("purchase.order", string="Purchase Order", copy=False)
    vendor_bill_id = fields.Many2one("account.move", string="Vendor Bill", domain="[('move_type','in',('in_invoice','in_refund'))]", copy=False)
    expense_account_id = fields.Many2one("account.account", string="IT / Equipment Expense Account", check_company=True)
    journal_id = fields.Many2one("account.journal", string="IT Accounting Journal", check_company=True)
    analytic_account_id = fields.Many2one("account.analytic.account", string="Analytic Account / Cost Center", check_company=True)
    actual_parts_cost = fields.Monetary(string="Actual Parts Cost", compute="_compute_actual_parts_cost", currency_field="currency_id")
    lifetime_cost = fields.Monetary(string="Lifetime Cost", compute="_compute_actual_parts_cost", currency_field="currency_id")

    def _compute_actual_parts_cost(self):
        Move = self.env["stock.move"]
        for rec in self:
            moves = Move.search([
                ("it_asset_id", "=", rec.id),
                ("state", "=", "done"),
            ])
            consumed = sum(abs(move.value or 0.0) for move in moves)
            rec.actual_parts_cost = consumed
            rec.lifetime_cost = (rec.purchase_cost or rec.acquisition_cost or 0.0) + consumed
