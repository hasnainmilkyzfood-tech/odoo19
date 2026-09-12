from odoo import _, api, fields, models


class ITTicketCharge(models.Model):
    _name = "it.ticket"
    _inherit = ["it.ticket", "it.department.charge.mixin"]

    service_cost = fields.Monetary(
        string="Service / Labor Charge", currency_field="currency_id",
        help="Manual charge for technician time or an external service call, "
             "in addition to any parts consumed.",
    )
    total_charge_cost = fields.Monetary(
        string="Total Chargeable Cost", compute="_compute_total_charge_cost",
        store=True, currency_field="currency_id",
    )

    @api.depends("parts_cost", "service_cost")
    def _compute_total_charge_cost(self):
        for rec in self:
            rec.total_charge_cost = (rec.parts_cost or 0.0) + (rec.service_cost or 0.0)

    @api.depends("department_id")
    def _compute_charge_department(self):
        for rec in self:
            rec.charge_department_id = rec.department_id

    def _get_charge_amount(self):
        self.ensure_one()
        return self.total_charge_cost

    def _get_charge_description(self):
        self.ensure_one()
        return _("IT Ticket %s - %s") % (self.name, self.subject or "")
