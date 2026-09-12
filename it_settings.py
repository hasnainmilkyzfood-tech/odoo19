from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    it_stock_location_id = fields.Many2one(
        "stock.location", string="IT Stock Location",
        domain="[('usage','=','internal')]", check_company=True,
    )
    it_consumption_location_id = fields.Many2one(
        "stock.location", string="IT Consumption Location",
        domain="[('usage','in',('inventory','internal'))]", check_company=True,
    )
    it_internal_picking_type_id = fields.Many2one(
        "stock.picking.type", string="IT Internal Transfer Operation Type",
        domain="[('code','=','internal')]", check_company=True,
    )
    it_purchase_picking_type_id = fields.Many2one(
        "stock.picking.type", string="IT Purchase Deliver-To Operation Type",
        domain="[('code','=','incoming')]", check_company=True,
    )
    it_default_expense_account_id = fields.Many2one(
        "account.account", string="Default IT Expense Account", check_company=True,
    )
    it_default_journal_id = fields.Many2one(
        "account.journal", string="Default IT Journal", check_company=True,
    )
    it_recovery_analytic_account_id = fields.Many2one(
        "account.analytic.account", string="IT Recovery / Shared Services Analytic Account",
        check_company=True,
        help="Optional analytic account representing the IT department's own cost pool. "
             "When set, department charge-back entries credit this account so IT's "
             "analytic reporting reflects the cost being recovered from other departments.",
    )
    it_low_stock_threshold = fields.Float(string="Default IT Low Stock Threshold", default=0.0)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    it_stock_location_id = fields.Many2one(related="company_id.it_stock_location_id", readonly=False)
    it_consumption_location_id = fields.Many2one(related="company_id.it_consumption_location_id", readonly=False)
    it_internal_picking_type_id = fields.Many2one(related="company_id.it_internal_picking_type_id", readonly=False)
    it_purchase_picking_type_id = fields.Many2one(related="company_id.it_purchase_picking_type_id", readonly=False)
    it_default_expense_account_id = fields.Many2one(related="company_id.it_default_expense_account_id", readonly=False)
    it_default_journal_id = fields.Many2one(related="company_id.it_default_journal_id", readonly=False)
    it_recovery_analytic_account_id = fields.Many2one(related="company_id.it_recovery_analytic_account_id", readonly=False)
    it_low_stock_threshold = fields.Float(related="company_id.it_low_stock_threshold", readonly=False)
