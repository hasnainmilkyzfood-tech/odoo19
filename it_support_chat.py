from odoo import api, fields, models, _
from odoo.exceptions import UserError


def _request_ip():
    try:
        from odoo.http import request
        httprequest = request.httprequest
        forwarded = httprequest.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return httprequest.headers.get("X-Real-IP") or httprequest.remote_addr
    except Exception:
        return False


class ITSupportChat(models.Model):
    _name = "it.support.chat"
    _description = "IT Support Conversation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Conversation", readonly=True, copy=False, default=lambda self: _("New"))
    subject = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", default=lambda self: self._default_employee(), tracking=True)
    assigned_to_id = fields.Many2one("res.users", string="Assigned To", domain="[('share','=',False)]", tracking=True)
    message_body = fields.Html(string="Initial Message", required=True)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
    state = fields.Selection([("open", "Open"), ("closed", "Closed")], default="open", tracking=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    source_ip = fields.Char(string="User IP", readonly=True, copy=False, default=_request_ip)
    anydesk_id = fields.Char(string="AnyDesk ID", tracking=True)

    def _default_employee(self):
        return self.env["hr.employee"].search([("user_id", "=", self.env.user.id)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        captured_ip = _request_ip()
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("it.support.chat") or _("New")
            if not vals.get("source_ip") and captured_ip:
                vals["source_ip"] = captured_ip
        records = super().create(vals_list)
        # Use Odoo's native chatter for reliable two-way chat. This avoids custom
        # fetch/JSON endpoints that can return HTML login/error pages.
        for rec in records:
            if rec.message_body:
                rec.message_post(body=rec.message_body, message_type="comment", subtype_xmlid="mail.mt_comment")
        return records

    def action_close(self):
        self.write({"state": "closed"})

    def action_reopen(self):
        self.write({"state": "open"})

    def action_open_anydesk(self):
        self.ensure_one()
        if not self.anydesk_id:
            raise UserError(_("Please enter the user's AnyDesk ID first."))
        clean_id = "".join(ch for ch in self.anydesk_id if ch.isalnum())
        return {"type": "ir.actions.act_url", "url": "anydesk:%s" % clean_id, "target": "self"}
