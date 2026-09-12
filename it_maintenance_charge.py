from odoo import _, api, fields, models


class ITMaintenanceCharge(models.Model):
    _name = "it.maintenance"
    _inherit = ["it.maintenance", "it.department.charge.mixin"]

    @api.depends("department_id")
    def _compute_charge_department(self):
        for rec in self:
            rec.charge_department_id = rec.department_id

    def _get_charge_amount(self):
        self.ensure_one()
        return self.cost or 0.0

    def _get_charge_description(self):
        self.ensure_one()
        return _("IT Maintenance %s - %s") % (self.name, self.asset_id.display_name or "")
