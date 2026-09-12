IT Management - Odoo 19

Features:
- IT Asset inventory
- Employee / department assignment
- Asset status workflow
- IT support tickets with priority and technician
- Maintenance history
- Chatter and activities
- Multi-company record rules
- IT User and IT Manager security groups

Installation:
1. Extract the it_management folder into your Odoo custom addons path.
2. Restart Odoo.
3. Enable Developer Mode if needed.
4. Apps > Update Apps List.
5. Search "IT Management" and install it.
6. Settings > Users: assign IT Management / IT User or IT Manager to the desired users.

Dependencies:
- base
- mail
- hr

Target:
- Odoo 19.0

Version 19.0.4.0.0
- Professional IT dashboard redesign.
- Automatic browser client IP capture on tickets and support chats.
- AnyDesk ID fields and Connect AnyDesk actions.
- Recent-ticket dashboard table with IP / AnyDesk / priority / state.
- Two-way ticket resolution verification: IT sends for verification; ticket owner confirms close or reopens.
- Support chat uses native Odoo mail.thread chatter to avoid custom fetch/JSON HTML-response errors.

Version 19.0.5.0.0
- IT Management remains independent from Maintenance Extension; no merge/dependency on maintenance_extension.
- Fixed IT parts transfer context leakage that could pass ticket state "new" into stock.picking.
- Parts consumption now creates DRAFT transfers only. No automatic confirm/assign/validation.
- Stock valuation layers remain standard Odoo-generated on validation and are traceable to IT Ticket / Asset.
- Added IT Settings: stock location, consumption location, internal operation type, purchase deliver-to, low-stock threshold, default expense account and journal.
- Added draft RFQ creation from IT ticket parts requirements and IT Purchase Orders menu.
- Added IT Stock Report and IT Stock Valuation Layers report.
- Expanded IT Equipment / Asset with assignment, PO/bill references, accounting/cost-center fields and lifetime parts cost.
