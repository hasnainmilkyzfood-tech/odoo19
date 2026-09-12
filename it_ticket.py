from odoo import api, fields, models, _
from odoo.exceptions import UserError


def _request_ip():
    """Best-effort client IP capture for browser-created tickets."""
    try:
        from odoo.http import request
        httprequest = request.httprequest
        forwarded = httprequest.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return httprequest.headers.get("X-Real-IP") or httprequest.remote_addr
    except Exception:
        return False


class ITTicket(models.Model):
    _name = "it.ticket"
    _description = "IT Support Ticket"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, id desc"

    name = fields.Char(string="Ticket No.", required=True, copy=False, readonly=True, default=lambda self: _("New"))
    subject = fields.Char(string="Title", required=True, tracking=True)
    description = fields.Html(string="Description")
    asset_id = fields.Many2one("it.asset", string="Device / Asset", tracking=True)
    asset_number = fields.Char(string="Device / Asset Number")
    employee_id = fields.Many2one("hr.employee", string="Employee", tracking=True, default=lambda self: self._default_employee())
    department_id = fields.Many2one("hr.department", related="employee_id.department_id", string="Department", store=True, readonly=True)
    assigned_to_id = fields.Many2one("res.users", string="Assigned", tracking=True, domain="[('share', '=', False)]")
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    priority = fields.Selection([
        ("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Critical")
    ], string="Priority", default="1", tracking=True)
    category = fields.Selection([
        ("hardware", "Hardware"), ("software", "Software"), ("network", "Network"),
        ("email", "Email"), ("access", "Access / Account"), ("printer", "Printer"), ("other", "Other")
    ], string="Issue Category", default="hardware", required=True, tracking=True)
    state = fields.Selection([
        ("new", "New"), ("progress", "In Progress"), ("waiting", "Awaiting User Verification"),
        ("resolved", "Resolved"), ("closed", "Closed"), ("cancelled", "Cancelled")
    ], string="Status", default="new", required=True, tracking=True)
    opened_date = fields.Datetime(string="Created", default=fields.Datetime.now, readonly=True)
    resolved_date = fields.Datetime(string="Resolved On", readonly=True)
    resolution = fields.Html(string="Resolution")
    source_ip = fields.Char(string="User IP", readonly=True, copy=False, default=lambda self: _request_ip(),
                            help="Client IP captured when the ticket is created from the web interface.")
    anydesk_id = fields.Char(string="AnyDesk ID", tracking=True, help="User's AnyDesk address / ID for remote support.")
    remote_support_requested = fields.Boolean(string="Remote Support Requested", tracking=True)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")

    verification_status = fields.Selection([
        ("none", "Not Requested"),
        ("pending", "Waiting for User"),
        ("confirmed", "Confirmed by User"),
        ("rejected", "User Says Not Fixed"),
    ], string="User Verification", default="none", readonly=True, tracking=True, copy=False)
    verification_date = fields.Datetime(string="Verification Date", readonly=True, copy=False)
    verified_by_id = fields.Many2one("res.users", string="Verified By", readonly=True, copy=False)
    verification_note = fields.Text(string="User Verification Note", copy=False)
    can_verify = fields.Boolean(compute="_compute_can_verify")

    def _default_employee(self):
        return self.env["hr.employee"].search([("user_id", "=", self.env.user.id)], limit=1)

    @api.depends("employee_id", "state")
    def _compute_can_verify(self):
        user = self.env.user
        for rec in self:
            rec.can_verify = bool(
                rec.state == "waiting"
                and rec.employee_id
                and rec.employee_id.user_id == user
            ) or self.env.is_admin()

    @api.model_create_multi
    def create(self, vals_list):
        records_vals = []
        captured_ip = _request_ip()
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("it.ticket") or _("New")
            if not vals.get("source_ip") and captured_ip:
                vals["source_ip"] = captured_ip
            records_vals.append(vals)
        records = super().create(records_vals)
        for rec in records:
            rec._notify_user(_("New IT ticket created"), _("%s - %s") % (rec.name, rec.subject))
        return records

    def write(self, vals):
        old_states = {r.id: r.state for r in self}
        res = super().write(vals)
        if "state" in vals:
            for rec in self:
                if old_states.get(rec.id) != rec.state:
                    rec._notify_user(_("Ticket status updated"), _("%s is now %s") % (
                        rec.name, dict(rec._fields["state"].selection).get(rec.state, rec.state)
                    ))
        return res

    def _notify_user(self, title, message):
        Notification = self.env["it.notification"].sudo()
        for rec in self:
            target_user = rec.employee_id.user_id or self.env.user
            Notification.create({
                "title": title,
                "message": message,
                "user_id": target_user.id,
                "ticket_id": rec.id,
            })

    def _check_ticket_owner(self):
        for rec in self:
            if self.env.is_admin():
                continue
            if not rec.employee_id or rec.employee_id.user_id != self.env.user:
                raise UserError(_("Only the user who raised this ticket can verify the resolution."))

    def action_start(self):
        self.write({"state": "progress"})

    def action_waiting(self):
        self.write({"state": "waiting", "verification_status": "pending"})

    def action_resolve(self):
        """IT marks the work complete; user must verify before final closure."""
        for rec in self:
            rec.write({
                "state": "waiting",
                "resolved_date": fields.Datetime.now(),
                "verification_status": "pending",
                "verification_date": False,
                "verified_by_id": False,
            })
            rec.message_post(body=_("IT marked this ticket as resolved. User confirmation is required before closure."))
            rec._notify_user(_("Please verify your IT ticket"), _("%s is ready for your confirmation.") % rec.name)

    def action_user_confirm_close(self):
        self._check_ticket_owner()
        for rec in self:
            if rec.state != "waiting":
                raise UserError(_("This ticket is not waiting for user verification."))
            rec.write({
                "state": "closed",
                "verification_status": "confirmed",
                "verification_date": fields.Datetime.now(),
                "verified_by_id": self.env.user.id,
            })
            rec.message_post(body=_("Resolution confirmed by %s. Ticket closed.") % self.env.user.display_name)

    def action_user_reject_resolution(self):
        self._check_ticket_owner()
        for rec in self:
            if rec.state != "waiting":
                raise UserError(_("This ticket is not waiting for user verification."))
            rec.write({
                "state": "progress",
                "verification_status": "rejected",
                "verification_date": fields.Datetime.now(),
                "verified_by_id": self.env.user.id,
                "resolved_date": False,
            })
            note = rec.verification_note or _("User reported that the issue is not fixed.")
            rec.message_post(body=_("User verification failed: %s") % note)

    def action_close(self):
        # Preserve compatibility with old buttons, but enforce two-way verification.
        return self.action_user_confirm_close()

    def action_reopen(self):
        self.write({
            "state": "progress", "resolved_date": False,
            "verification_status": "rejected", "verification_date": fields.Datetime.now(),
        })

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_open_anydesk(self):
        self.ensure_one()
        if not self.anydesk_id:
            raise UserError(_("Please enter the user's AnyDesk ID first."))
        clean_id = "".join(ch for ch in self.anydesk_id if ch.isalnum())
        return {
            "type": "ir.actions.act_url",
            "url": "anydesk:%s" % clean_id,
            "target": "self",
        }
