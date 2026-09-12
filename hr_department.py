from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    it_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="IT Cost Center",
        help="Analytic account used to charge back IT costs (parts, services, "
             "maintenance) consumed by employees of this department.",
    )
