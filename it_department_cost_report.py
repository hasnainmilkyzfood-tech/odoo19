# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ITDepartmentCostReport(models.Model):
    """Read-only dynamic report combining IT Ticket costs (parts + service)
    and IT Maintenance costs, so total IT spend can be analyzed per
    department, employee, asset or charge status.
    """
    _name = "it.department.cost.report"
    _description = "IT Department Cost Report"
    _auto = False
    _order = "cost_date desc"

    source_type = fields.Selection([
        ("ticket", "Ticket"),
        ("maintenance", "Maintenance"),
    ], string="Source", readonly=True)
    ticket_id = fields.Many2one("it.ticket", string="Ticket", readonly=True)
    maintenance_id = fields.Many2one("it.maintenance", string="Maintenance", readonly=True)
    department_id = fields.Many2one("hr.department", string="Department", readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    asset_id = fields.Many2one("it.asset", string="Asset", readonly=True)
    cost_date = fields.Date(string="Date", readonly=True)
    amount = fields.Monetary(string="Amount", readonly=True, currency_field="currency_id", aggregator="sum")
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    charge_state = fields.Selection([
        ("not_charged", "Not Charged"),
        ("charged", "Charged"),
    ], string="Charge Status", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    record_count = fields.Integer(string="# Records", readonly=True, default=1)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    (t.id * 2) AS id,
                    'ticket' AS source_type,
                    t.id AS ticket_id,
                    NULL::integer AS maintenance_id,
                    t.department_id AS department_id,
                    t.employee_id AS employee_id,
                    t.asset_id AS asset_id,
                    (t.opened_date)::date AS cost_date,
                    COALESCE(t.parts_cost, 0.0) + COALESCE(t.service_cost, 0.0) AS amount,
                    rc.currency_id AS currency_id,
                    t.charge_state AS charge_state,
                    t.company_id AS company_id,
                    1 AS record_count
                FROM it_ticket t
                LEFT JOIN res_company rc ON rc.id = t.company_id
                WHERE COALESCE(t.parts_cost, 0.0) + COALESCE(t.service_cost, 0.0) > 0

                UNION ALL

                SELECT
                    (m.id * 2 + 1) AS id,
                    'maintenance' AS source_type,
                    NULL::integer AS ticket_id,
                    m.id AS maintenance_id,
                    m.department_id AS department_id,
                    m.employee_id AS employee_id,
                    m.asset_id AS asset_id,
                    m.maintenance_date AS cost_date,
                    COALESCE(m.cost, 0.0) AS amount,
                    rc2.currency_id AS currency_id,
                    m.charge_state AS charge_state,
                    m.company_id AS company_id,
                    1 AS record_count
                FROM it_maintenance m
                LEFT JOIN res_company rc2 ON rc2.id = m.company_id
                WHERE COALESCE(m.cost, 0.0) > 0
            )
        """ % self._table)
