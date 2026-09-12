from odoo import fields, models


class ITNotification(models.Model):
    _name = "it.notification"
    _description = "IT Notification"
    _order = "create_date desc"

    title = fields.Char(required=True)
    message = fields.Text(required=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, ondelete="cascade")
    ticket_id = fields.Many2one("it.ticket", ondelete="cascade")
    is_read = fields.Boolean(default=False)
    create_date = fields.Datetime(readonly=True)

    def action_mark_read(self):
        self.write({"is_read": True})

    def action_mark_unread(self):
        self.write({"is_read": False})
