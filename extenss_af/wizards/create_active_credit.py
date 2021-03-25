from odoo import fields, models, api, _, exceptions
from odoo.exceptions import Warning, UserError, ValidationError

class ExtenssConciliationInitialPay(models.TransientModel):
    _name = 'extenss.conciliation.initial.pay'
    _description = 'Conciliation Initial Pay'

    name = fields.Char(string='Name', tracking=True, translate=True)
    lines_ids = fields.One2many('extenss.conciliation.initial.pay.lines', 'init_id', '', tracking=True)


class ExtenssConciliationInitialPay(models.TransientModel):
    _name = 'extenss.conciliation.initial.pay.lines'
    _description = 'Conciliation Initial Pay'

    name = fields.Char(string='Name', tracking=True, translate=True)
    init_id = fields.Many2one('extenss.conciliation.initial.pay', string='Init Pay', ondelete='cascade', tracking=True, translate=True)
    amount = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)


# class ExtenssCreditConciliation(models.Model):
#     _inherit = 'extenss.credit.conciliation'
#     _description = 'Conciliation'

#     name = fields.Char(string='Reference', tracking=True, translate=True)
#     conciliation_ids = fields.One2many('extenss.credit.conciliation_lines', 'conciliation_id', string=' ', tracking=True)

# class ExtenssCreditConciliationLines(models.Model):
#     _inherit = 'extenss.credit.conciliation_lines'
#     _description = 'Conciliation Lines'

#     conciliation_id = fields.Many2one('extenss.credit.conciliation', string='Conciliation', ondelete='cascade', tracking=True, translate=True)
    