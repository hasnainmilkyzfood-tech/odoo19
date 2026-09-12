from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    it_ticket_id = fields.Many2one("it.ticket", string="IT Ticket", index=True, copy=False)
    it_asset_id = fields.Many2one("it.asset", string="IT Equipment / Asset", index=True, copy=False)