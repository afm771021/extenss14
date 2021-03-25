from odoo import fields, models, api, _, exceptions
from odoo.exceptions import Warning, UserError, ValidationError

from datetime import datetime, date

CONCEPT = [
    ('pay_initial','Pay Initial'),
    ('pay_notice','Pay Notice'),
    ('early_set','Early Settlement'),
    ('dispersion', 'Collection'),
]

class Datamart(models.Model):
    _name = 'extenss.datamart'
    _description = 'Datamart'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date = fields.Date(string='Date', tracking=True, translate=True)
    name = fields.Char(string='Name', tracking=True, translate=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True, translate=True)
    ref = fields.Char(string='Reference', tracking=True, translate=True)
    # journal_id = fields.Many2one('account.journal', string='Journal', tracking=True, translate=True)
    # company_id = fields.Many2one('res.company', string='Company', tracking=True, translate=True)
    # amount_total_signed = fields.Monetary(string='Total', currency_field='company_currency', tracking=True, translate=True)
    # state = fields.Selection([('draft','Draft'),('posted','Posted'),('cancel','Cancel')], string='State', tracking=True, translate=True)

    # company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    # company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    datamart_ids = fields.One2many('extenss.datamart.lines', 'datamart_id', string=' ')
    ##Proceso para generar los eventos contables
    ##Proceso para enviar los registros a la contabilidad
    def action_send_account(self):
        ###, partnerid, amount_trans, accountid
        regs_lines = self.env['extenss.datamart.lines'].search([('check', '=', True),('status', '=', 'to_send')])
        for reg_line in regs_lines:
            reg_catalogs = self.env['extenss.datamart.contable_events'].search([('event_key', '=', reg_line.type_line)])
            if reg_catalogs:
                new_aml_dicts = []
                id_acc_mov = self.env['account.move'].sudo().create({
                    'name': reg_line.name,
                    #'ref': 'Prueba',
                    'date': datetime.now().date(),
                    'journal_id': reg_catalogs.journal_id.id,
                    'state': 'draft',
                    'type': 'entry',
                    'to_check': 'false',
                    'partner_id': reg_line.partner_id.id, #partnerid,#<---partnerid---26
                })
                for accts in reg_catalogs.con_event_ids:
                    if accts.type_amount == 'abono':
                        new_aml_dicts.append ({
                            'move_id': id_acc_mov.id,
                            'partner_id': reg_line.partner_id.id, #partnerid, 
                            'currency_id': False, 
                            'debit': False, 
                            'credit': reg_line.amount, #amount_trans,#<----amount_trans--- 1000
                            'quantity': 1,
                            'discount': 0,
                            'sequence': 10,
                            'tax_exigible': True,
                            'display_type': False, 
                            'account_id': accts.account_id.id, #<----accountid---2
                            'name': 'Prueba', 
                            'analytic_account_id': False, 
                            'amount_currency': 0, 
                            'payment_id': False, 
                            'product_id': False, 
                            'product_uom_id': False, 
                            'price_unit': 0, 
                            'tax_repartition_line_id': False, 
                            'tax_base_amount': 0, 
                            #'purchase_line_id': False, 
                            'recompute_tax_line': False, 
                            'predict_from_name': False, 
                            'predict_override_default_account': False, 
                            'is_rounding_line': False, 
                            'exclude_from_invoice_tab': False,
                            'company_currency_id': False,
                        })
                    if accts.type_amount == 'cargo':
                        new_aml_dicts.append ({
                            'move_id': id_acc_mov.id,
                            'partner_id': reg_line.partner_id.id, #partnerid, #data_line.partner_id.id
                            'currency_id': False, 
                            'debit': reg_line.amount, #amount_trans, #data_line.debit
                            'credit': False, #data_line.credit
                            'quantity': 1,
                            'discount': 0,
                            'sequence': 10,
                            'tax_exigible': True,
                            'display_type': False, 
                            'account_id': accts.account_id.id, #data_line.account_id--- 2 
                            'name': 'Prueba', 
                            'analytic_account_id': False,
                            'amount_currency': 0, 
                            'payment_id': False, 
                            'product_id': False, 
                            'product_uom_id': False, 
                            'price_unit': 0, 
                            'tax_repartition_line_id': False, 
                            'tax_base_amount': 0, 
                            #'purchase_line_id': False, 
                            'recompute_tax_line': False, 
                            'predict_from_name': False, 
                            'predict_override_default_account': False, 
                            'is_rounding_line': False, 
                            'exclude_from_invoice_tab': False,
                            'company_currency_id': False
                        })

                self.env['account.move.line'].create(new_aml_dicts)
                reg_line.status = 'sent'
                id_acc_mov.write({
                    'state': 'posted',
                })
            else:
                raise ValidationError(_('Not exist the event contable'))

class DatamartLines(models.Model):
    _name = 'extenss.datamart.lines'
    _description = 'Datamart lines'

    name = fields.Char(string='Name', copy=False, readonly=True, index=True, tracking=True, translate=True, default=lambda self: _('New'))
    datamart_id = fields.Many2one('extenss.datamart', string='Datamart id')
    check = fields.Boolean(string='Selected', default=False, tracking=True, translate=True)
    account_id = fields.Many2one('account.account', string='Account', tracking=True, translate=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True, translate=True)
    description = fields.Char(string='Description', tracking=True, translate=True)
    product_id = fields.Many2one('extenss.product.product', string='Product', tracking=True, translate=True)
    credit_id = fields.Many2one('extenss.credit', tracking=True, translate=True)
    amount = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    type_line = fields.Integer(string='Type', tracking=True, translate=True)
    status = fields.Selection([('sent','Sent'),('to_send','To Send'),], default='to_send', string='Status', tracking=True, translate=True)
    # debit = fields.Monetary(string='Debit', currency_field='company_currency', tracking=True, translate=True)
    # credit = fields.Monetary(string='Credit', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    @api.model
    def create(self, reg):
        if reg:
            if reg.get('name', _('New')) == _('New'):
                reg['name'] = self.env['ir.sequence'].next_by_code('extenss.datamart.lines') or _('New')
            result = super(DatamartLines, self).create(reg)
            return result


class ExtenssDatamartContableEvents(models.Model):
    _name = 'extenss.datamart.contable_events'
    _description = 'Contable events'

    @api.constrains('event_key')
    def _check_event_key(self):
        for reg in self:
            if reg.event_key:
                reg.flag_active = True

    event_key = fields.Integer(string='Event key', tracking=True, translate=True)
    name = fields.Char(string='Event description', tracking=True, translate=True)
    active_event = fields.Boolean(string='Active', dafault=False, tracking=True, translate=True)
    policy_category = fields.Selection([('value1','Value 1'),('datamart','Datamart'),], string='Policy category', default=False, tracking=True, translate=True)
    grouper = fields.Selection([('value1','Value 1'),('value2','Value 2'),], string='Grouper', default=False, tracking=True, translate=True)
    start_date = fields.Date(string='Start date', default=fields.Date.context_today, tracking=True, translate=True)
    end_date = fields.Date(string='End date', tracking=True, translate=True)
    flag_active = fields.Boolean(string='Active', dafault=False, tracking=True, translate=True)
    company_id = fields.Many2one('res.company', string='CIA', tracking=True, translate=True)#, required=True
    journal_id = fields.Many2one('account.journal', string='Journal', tracking=True, translate=True)

    con_event_ids = fields.One2many('extenss.datamart.events_lines', 'con_event_id', string=' ')

class ExtenssDatamartEventsLines(models.Model):
    _name = 'extenss.datamart.events_lines'
    _description = 'Events lines'

    @api.constrains('apply')
    def _check_apply(self):
        for reg in self:
            if reg.apply > 100:
                raise ValidationError(_('The field value only allows 100 percent'))

    line = fields.Char(string='Line', tracking=True, translate=True)
    con_event_id = fields.Many2one('extenss.datamart.contable_events', string='Contable event', ondelete='cascade', tracking=True, translate=True)
    operative_unit = fields.Many2one('account.analytic.account', string='Operative Unit', tracking=True, translate=True)
    product = fields.Many2one('extenss.product.product', string='Product', tracking=True, translate=True)#, required=True
    account_id = fields.Many2one('account.account', string='Account', tracking=True, translate=True)#, required=True
    rule = fields.Many2one('extenss.datamart.cat_rules', string='Rule', tracking=True, translate=True)
    cicle = fields.Char(string='Cicle', tracking=True, translate=True)
    future_1 = fields.Char(string='Future 1', tracking=True, translate=True)
    future_2 = fields.Char(string='Future 2', tracking=True, translate=True)
    nature = fields.Char(string='Nature', tracking=True, translate=True)
    type_amount = fields.Selection([('cargo','Charge'),('abono','Credit')], string='Type amount', tracking=True, translate=True)
    apply = fields.Float('% Apply', (2,6), tracking=True, translate=True)

class ExtenssDatamartCatRules(models.Model):
    _name = 'extenss.datamart.cat_rules'
    _description = 'Rules catalogue '

    name = fields.Char(string='Name')
    description = fields.Char(string='Description')

class ExtenssDatamartConciliation(models.Model):
    _name = 'extenss.datamart.conciliation'
    _description = 'Conciliation'

    name = fields.Char(string='Reference', tracking=True, translate=True)
    initial_balance = fields.Monetary(string='Initial balance', currency_field='company_currency', tracking=True, translate=True)
    final_balance = fields.Monetary(string='Final balance', currency_field='company_currency', tracking=True, translate=True)
    status_bank = fields.Selection([('draft','Draft'),('pending','Pending'),('validated','Validated')], string='Status', default='draft', tracking=True, translate=True)
    processing_id = fields.Char(string='Processing id', tracking=True, translate=True)
    type = fields.Char(string='Type', default='conciliation', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    conciliation_ids = fields.One2many('extenss.datamart.conciliation_lines', 'conciliation_id', string=' ', tracking=True)

    def action_create_data(self):
        print("entra a metodo")

class ExtenssDatamartConciliationLines(models.Model):
    _name = 'extenss.datamart.conciliation_lines'
    _description = 'Conciliation Lines'

    conciliation_id = fields.Many2one('extenss.datamart.conciliation', string='Conciliation', ondelete='cascade', tracking=True, translate=True)
    date = fields.Date(string='Date', tracking=True, translate=True)
    description = fields.Char(string='Description', tracking=True, translate=True)
    customer = fields.Many2one('res.partner', string='Customer', tracking=True, translate=True)
    reference = fields.Char(string='Reference', tracking=True, translate=True)
    amount = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    check = fields.Boolean(string='Validate', tracking=True, translate=True)
    status = fields.Selection([('applied', 'Applied'),('pending', 'Pending'),],string='Status', tracking=True, translate=True)
    display_type = fields.Selection([('line_section', 'Section'),('line_note', 'Note'),], default=False)
    type_rec = fields.Selection([('expiry', 'Expiry'),('conciliation', 'Conciliation'),], default=False)
    bill_id = fields.Many2one('extenss.credit.account', string='Bill', tracking=True, translate=True)
    expiry_id = fields.Char(string='Id expiry', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class ExtenssDatamartConfiguration(models.Model):
    _name = 'extenss.datamart.configuration'
    _description = 'Datamart Configuration'

    concept = fields.Selection(CONCEPT, string='Concept')
    event_id =fields.Many2many('extenss.datamart.contable_events', 'configuration_events', string='Events', tracking=True, translate=True)