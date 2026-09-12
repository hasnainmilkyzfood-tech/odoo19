from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ITTicketParts(models.Model):
    _inherit = "it.ticket"

    part_line_ids = fields.One2many("it.ticket.part.line", "ticket_id", string="Parts Used")
    parts_cost = fields.Monetary(compute="_compute_parts_cost", store=True, currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)
    parts_picking_count = fields.Integer(compute="_compute_parts_picking_count")
    purchase_order_count = fields.Integer(compute="_compute_purchase_order_count")
    purchase_vendor_id = fields.Many2one("res.partner", string="Purchase Vendor", domain="[('supplier_rank', '>', 0)]")

    @api.depends("part_line_ids.subtotal")
    def _compute_parts_cost(self):
        for rec in self:
            rec.parts_cost = sum(rec.part_line_ids.mapped("subtotal"))

    def _compute_parts_picking_count(self):
        Picking = self.env["stock.picking"]
        for rec in self:
            rec.parts_picking_count = Picking.search_count([("it_ticket_id", "=", rec.id)])

    def _compute_purchase_order_count(self):
        Purchase = self.env["purchase.order"]
        for rec in self:
            rec.purchase_order_count = Purchase.search_count([("it_ticket_id", "=", rec.id)])

    def _clean_stock_context(self):
        ctx = dict(self.env.context)
        # Ticket actions commonly carry default_state='new'. That value is invalid for stock.picking.
        for key in list(ctx):
            if key.startswith("default_") and key not in ("default_company_id",):
                ctx.pop(key, None)
        return ctx

    def action_consume_parts(self):
        Picking = self.env["stock.picking"]
        Move = self.env["stock.move"]
        Quant = self.env["stock.quant"]
        for rec in self:
            lines = rec.part_line_ids.filtered(lambda l: not l.move_id and l.quantity > 0)
            if not lines:
                raise UserError(_("There are no new part lines to consume."))
            company = rec.company_id
            warehouse = self.env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
            picking_type = company.it_internal_picking_type_id or (warehouse and warehouse.int_type_id)
            if not picking_type:
                raise UserError(_("Configure the IT Internal Transfer Operation Type in IT Management Settings."))
            default_source = company.it_stock_location_id or picking_type.default_location_src_id or (warehouse and warehouse.lot_stock_id)
            destination = company.it_consumption_location_id or self.env.ref("it_management.location_it_parts_consumption")
            if not default_source or not destination:
                raise UserError(_("Configure IT Stock Location and IT Consumption Location in IT Management Settings."))
            stock_ctx = rec._clean_stock_context()
            picking = Picking.with_context(stock_ctx).create({
                "picking_type_id": picking_type.id,
                "location_id": default_source.id,
                "location_dest_id": destination.id,
                "origin": rec.name,
                "it_ticket_id": rec.id,
                "company_id": rec.company_id.id,
            })
            for line in lines:
                source = line.location_id or default_source
                available = Quant._get_available_quantity(line.product_id, source)
                if available < line.quantity:
                    raise UserError(_("Not enough stock for %(product)s. Available: %(available)s, required: %(required)s", product=line.product_id.display_name, available=available, required=line.quantity))
                move = Move.with_context(stock_ctx).create({
                    "name": line.product_id.display_name,
                    "product_id": line.product_id.id,
                    "product_uom_qty": line.quantity,
                    "product_uom_id": line.uom_id.id,
                    "picking_id": picking.id,
                    "location_id": source.id,
                    "location_dest_id": destination.id,
                    "it_ticket_id": rec.id,
                    "it_ticket_part_line_id": line.id,
                    "it_asset_id": rec.asset_id.id,
                    "company_id": rec.company_id.id,
                })
                line.move_id = move
            # Intentionally keep the picking and its moves in DRAFT.
            # Stock quantity, valuation layer and accounting impact only occur after normal Odoo validation.
            rec.message_post(body=_("Draft parts transfer %(picking)s created. Review and validate it in Inventory to finalize consumption and valuation.", picking=picking.display_name))
        return True

    def action_create_draft_po(self):
        Purchase = self.env["purchase.order"]
        for rec in self:
            if not rec.purchase_vendor_id:
                raise UserError(_("Select a Purchase Vendor first."))
            lines = rec.part_line_ids.filtered(lambda l: l.quantity > 0)
            if not lines:
                raise UserError(_("Add at least one part requirement before creating an RFQ."))
            vals = {
                "partner_id": rec.purchase_vendor_id.id,
                "company_id": rec.company_id.id,
                "origin": rec.name,
                "it_ticket_id": rec.id,
                "it_asset_id": rec.asset_id.id,
                "order_line": [],
            }
            if rec.company_id.it_purchase_picking_type_id:
                vals["picking_type_id"] = rec.company_id.it_purchase_picking_type_id.id
            for line in lines:
                vals["order_line"].append((0, 0, {
                    "product_id": line.product_id.id,
                    "name": line.description or line.product_id.display_name,
                    "product_qty": line.quantity,
                    "product_uom_id": line.uom_id.id,
                    "price_unit": line.unit_cost or line.product_id.standard_price,
                    "date_planned": fields.Datetime.now(),
                }))
            po = Purchase.create(vals)
            rec.message_post(body=_("Draft RFQ %(po)s created for IT requirement.", po=po.display_name))
            return {"type": "ir.actions.act_window", "res_model": "purchase.order", "res_id": po.id, "view_mode": "form", "target": "current"}
        return True

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("IT Purchase Orders"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("it_ticket_id", "=", self.id)],
            "context": {"default_it_ticket_id": self.id, "default_it_asset_id": self.asset_id.id},
        }

    def action_view_parts_transfers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Parts Transfers"),
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("it_ticket_id", "=", self.id)],
        }


class ITTicketPartLine(models.Model):
    _name = "it.ticket.part.line"
    _description = "IT Ticket Part Consumption"

    ticket_id = fields.Many2one("it.ticket", required=True, ondelete="cascade")
    ticket_number = fields.Char(related="ticket_id.name", store=True)
    company_id = fields.Many2one(related="ticket_id.company_id", store=True)
    currency_id = fields.Many2one(related="ticket_id.currency_id", store=True)
    product_id = fields.Many2one("product.product", required=True, domain="[('type', '=', 'consu'), ('is_storable', '=', True)]")
    description = fields.Char(required=True)
    location_id = fields.Many2one("stock.location", string="Source Location", domain="[('usage', '=', 'internal')]", check_company=True)
    quantity = fields.Float(default=1.0, required=True)
    uom_id = fields.Many2one("uom.uom", required=True)
    unit_cost = fields.Monetary(currency_field="currency_id")
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True, currency_field="currency_id")
    move_id = fields.Many2one("stock.move", readonly=True, copy=False)
    move_state = fields.Selection(related="move_id.state", readonly=True)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.uom_id = self.product_id.uom_id
            self.unit_cost = self.product_id.standard_price

    @api.depends("quantity", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_cost

    @api.constrains("quantity")
    def _check_quantity(self):
        if any(line.quantity <= 0 for line in self):
            raise ValidationError(_("Part quantity must be greater than zero."))

    def unlink(self):
        if any(line.move_id and line.move_id.state != "cancel" for line in self):
            raise UserError(_("You cannot delete a part line after a transfer was created."))
        return super().unlink()


class StockPicking(models.Model):
    _inherit = "stock.picking"

    it_ticket_id = fields.Many2one("it.ticket", index=True)


class StockMove(models.Model):
    _inherit = "stock.move"

    it_ticket_id = fields.Many2one("it.ticket", index=True)
    it_asset_id = fields.Many2one("it.asset", string="IT Equipment / Asset", index=True)
    it_ticket_part_line_id = fields.Many2one("it.ticket.part.line", index=True)
