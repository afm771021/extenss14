from odoo import fields, models, api, _, exceptions
from odoo.exceptions import Warning, UserError, ValidationError

from datetime import timedelta
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar
import os
import glob
import base64
import logging

CREDIT_STATUS = [
    ('pending', 'Pending'),
    ('active', 'Active'),
    ('finished', 'Finished'),
    ('liquidated', 'Liquidated'),
    ('cancelled', 'Cancelled'),
]

CONCEPTS = [
    ('capital','Capital'),
    ('interest','Interest'),
    ('capvat','Capital VAT'),
    ('intvat','Interest VAT'),
    ('penalty_amount', 'Penalty Amount'),
    ('purchase_option', 'Purchase Option'),
    ('vat_option','Purchase Option VAT'),
    ('morint', 'Moratorium Interest'),
    ('morintvat', 'Moratorium Interest VAT'),
    ('payment', 'Payment'),
    ('paymentvat', 'VAT Payment'),
    ('condonation', 'Condonation interest moratoriums')
]

TYPE_REQ = [
    ('early_settlement','Early settlement'),
    ('atc', 'Advanced to capital'),
]

ADV_CAP = [
    ('term','Term'),
    ('amount','Amount')
]
_logger = logging.getLogger(__name__)

class Credits(models.Model):
    _name = 'extenss.credit'
    _description = 'Credit'

    def open_request_count(self):
        domain = [('credit_request_id', '=', [self.id])]
        return {
            'name': _('Request'),
            'view_type': 'form',
            'domain': domain,
            'res_model': 'extenss.credit.request',
            'type': 'ir.actions.act_window',
            #'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'tree,form',
            'context': "{'default_credit_request_id': %s}" % self.id
        }

    def get_request_count(self):
        count = self.env['extenss.credit.request'].search_count([('credit_request_id', '=', self.id)])
        self.request_count = count

    def action_new_request(self):
        action = self.env.ref("extenss_credit.action_menu_request").read()[0]
        action['context'] = {
            'default_credit_request_id': self.id,
        }
        return action

    @api.constrains('number_days_overdue')
    def _check_number_days_overdue(self):
        for reg in self:
            if reg.number_days_overdue > reg.days_transfer_past_due:
                reg.portfolio_type = 'vencida'

    def action_calculate_early(self):
        _logger.info('Inicia el proceso de action_calculate_early')
        out_balance = 0
        vat_capital = 0

        vat_credit = self.vat_factor
        penalty_percentage = self.penalty
        poa = self.purchase_option_amount
        gda = self.total_guarantee_deposit #guarantee_dep_application
        bid = self.total_deposit_income #balance_income_deposit
        int_mora = self.factor_rate
        base_type = self.calculation_base
        itr = self.interest_rate

        if base_type == '360/360':
            base = 360
        if base_type == '365/365' or base_type == '360/365':
            base = 365

        balance_initial = 0
        past_due_balance = 0
        interest_mora = 0
        interest_mora_tmp = 0
        pay_num = 0
        vat_capital = 0
        amount_penalty = 0
        vat_poa = 0
        vat_interest_mora = 0
        days = 0
        interest_due = 0
        interest_mora_sum = 0
        settle_total = 0
        sum_total = 0
        
        count_records = self.env['extenss.credit.expiry_notices'].search_count([('credit_expiry_id', '=', self.id)])
        if count_records == 0:
            reg_due = self.env['extenss.credit.amortization'].search([('no_pay', '=', 1),('credit_id', '=', self.id)])
            for rec in reg_due:
                days = self.days_between(rec.expiration_date, self.date_settlement)

            rec_amort = self.env['extenss.credit.amortization'].search([('no_pay', '=', 1),('credit_id', '=', self.id)])
            for record in rec_amort:
                out_balance = record.initial_balance
                vat_capital = (vat_credit/100) * out_balance
                amount_penalty = (penalty_percentage/100) * out_balance
                vat_poa = (vat_credit/100) * poa

            int_tmp = out_balance * ((itr/100)/base) * days
            vat_int = (vat_credit/100) * int_tmp

        else:
            records = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('req_credit_id', '=', False)])
            for rec_notice in records:
                past_due_balance += rec_notice.total_to_pay
                pay_num = rec_notice.payment_number
                balance_initial = rec_notice.outstanding_balance

            pay_num_amort = pay_num+1

            # if self.ff: # Validacion solo para Factojare
            #     reg_due = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num_amort),('credit_id', '=', self.id)])
            # if self.cs or self.af or self.ap or self.dn: #validacion para los produc tos AP,AF,DN,
            reg_due = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num),('credit_id', '=', self.id)])
            for rec in reg_due:
                days = self.days_between(rec.expiration_date, self.date_settlement)

            rec_expirys = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('req_credit_id', '=', False)])
            for r_exp in rec_expirys:
                if r_exp.total_to_pay > 0:
                    reg_mor = self.env['extenss.credit.amortization'].search([('no_pay', '=', r_exp.payment_number),('credit_id', '=', self.id)])
                    for rcs in reg_mor:
                        capital = rcs.capital
                        days_mora = self.days_between(rcs.expiration_date, self.date_settlement)
                        interest_mora = capital * ((int_mora/100)/base) * days_mora
                        interest_mora_sum += interest_mora

            vat_interest_mora = (vat_credit/100) * interest_mora_sum

            if self.ff:
                rec_amort = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num),('credit_id', '=', self.id)])
            else:
                rec_amort = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num_amort),('credit_id', '=', self.id)])
            for record in rec_amort:
                out_balance = record.initial_balance
                vat_capital = (vat_credit/100) * out_balance
                amount_penalty = (penalty_percentage/100) * out_balance
                vat_poa = (vat_credit/100) * poa

            int_tmp = out_balance * ((itr/100)/base) * days
            vat_int = (vat_credit/100) * int_tmp

        if self.ff or self.dn or self.af or self.cs:
            sum_total = out_balance + int_tmp + vat_int

        if self.af: 
            sum_total += vat_capital
            
        if self.ap:
            sum_total = out_balance + int_tmp + vat_int + vat_capital

        st = amount_penalty + past_due_balance + interest_mora_sum + vat_interest_mora + poa + vat_poa - gda - bid

        settle_total = sum_total + st

        self.outstanding_balance = out_balance
        self.overdue_balance = past_due_balance
        self.interests = int_tmp
        self.days_interest = days
        self.interests_moratoriums = interest_mora_sum
        self.vat_interest_mora = vat_interest_mora
        self.capital_vat = vat_capital
        self.interests_vat = vat_int
        self.penalty = penalty_percentage
        self.penalty_amount = amount_penalty
        self.purchase_option = poa
        self.vat_purchase_option = vat_poa
        self.security_deposit_balance = bid
        self.balance_income_deposit = gda
        self.total_settle = settle_total
        self.balance_inicial = balance_initial

    def action_apply_request(self):
        list_concepts = []
        amount = 0
        #if self.type_request == 'early_settlement':
        pay_rec = self.env['extenss.credit.expiry_notices'].search_count([('credit_expiry_id', '=', self.id),('req_credit_id', '=', False)])
        num_rec = pay_rec + 1

        # ec_id = self.env['extenss.credit'].browse(self.env.context.get('active_ids'))
        # for rec in ec_id:
        factor_rate = self.factor_rate
        id_accnt = self.bill_id.id
        flag_early_settlement = True
        if self.ff or self.dn or self.cs or self.af:
            if self.outstanding_balance > 0:
                list_concepts.append(['capital', self.outstanding_balance])
        if self.af:       
            if self.capital_vat > 0:
                list_concepts.append(['capvat', self.capital_vat])
        if self.ff or self.dn or self.cs or self.af:
            if self.interests > 0:
                list_concepts.append(['interest', self.interests])
        if self.ff or self.dn or self.cs or self.af:
            if self.interests_vat > 0:
                list_concepts.append(['intvat', self.interests_vat])
        if self.ap:
            payment = self.outstanding_balance + self.interests
            vat_payment = self.interests_vat + self.capital_vat
            list_concepts.append(['payment', payment])
            list_concepts.append(['paymentvat', vat_payment])

        if self.penalty_amount > 0:
            list_concepts.append(['penalty_amount', self.penalty_amount])
        if self.af or self.ap:
            if self.purchase_option > 0:
                list_concepts.append(['purchase_option', self.purchase_option])
            if self.vat_purchase_option > 0:
                list_concepts.append(['vat_option', self.vat_purchase_option])
        if self.interests_moratoriums > 0:
            list_concepts.append(['morint', self.interests_moratoriums])
        if self.vat_interest_mora > 0:
            list_concepts.append(['morintvat', self.vat_interest_mora])

        # #realiza trasacciones a la cuenta eje
        if self.af:
            if self.security_deposit_balance > 0:
                self.env['extenss.credit.accounting_payments'].action_apply_movement(id_accnt, 'abono', self.security_deposit_balance, 'Security Deposit Balance payment')
                self.security_deposit_balance = 0 #09062020
            if self.balance_income_deposit > 0:
                self.env['extenss.credit.accounting_payments'].action_apply_movement(id_accnt, 'abono', self.balance_income_deposit, 'Balance Income on Deposit payment')
                self.balance_income_deposit = 0 #09062020

        amount = self.security_deposit_balance + self.balance_income_deposit + self.total_settle - self.overdue_balance
        id_expiry = self.create_notice_expiry(num_rec, self.id, amount, list_concepts, self.id,self.date_settlement, self.balance_inicial, factor_rate, '')

        return id_expiry

    #Pago liquidacion
    def action_pay_early_settlement(self):
        list_concepts = []
        for reg in self.conciliation_credit_ids:
            if reg.check == False and reg.status == 'pending' and reg.customer == self.customer_id:
                self.env['extenss.credit.accounting_payments'].action_apply_movement(self.bill_id.id, 'abono', reg.amount,'')
                reg.status = 'applied'
                reg.check = True

                exp_notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('total_to_pay', '>', 0)])
                for exp_notice in exp_notices:
                    self.env['extenss.credit.conciliation'].apply_payment(exp_notice.id, self.payment_date)

        if reg:
            id_expiry = self.action_apply_request()
            self.env['extenss.credit.conciliation'].apply_payment(id_expiry.id, self.payment_date)
            regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'early_set')])
            if regs_conf:
                for reg_conf in regs_conf:
                    # print(reg.id)
                    for reg_events in reg_conf.event_id:
                        event_key = reg_events.event_key
                        list_concepts.append(self.customer_id.id)
                        list_concepts.append(reg.amount) 
                        list_concepts.append(self.product_id.id)
                        list_concepts.append(event_key)
                        self.env['extenss.credit'].create_records(list_concepts)
                        list_concepts = []
                self.flag_early_settlement = True
                self.credit_status = 'liquidated'
            else:
                raise ValidationError(_('Not exist record in Configuration in Datamart'))
        else:
            raise ValidationError(_('Select a payment record'))

    def days_between(self, d1, d2):
        return abs((d2 - d1).days)

    name = fields.Char('Credit', related='credit_id')
    credit_id = fields.Char('Credit', copy=False, readonly=True, index=True, tracking=True, translate=True, default=lambda self: _('New'))
    customer_id = fields.Many2one('res.partner', string='Customer', tracking=True, translate=True)
    request_id = fields.Many2one('crm.lead', string='Request Id', tracking=True, translate=True)
    #product_id = fields.Many2one('extenss.product.template', string='Product', tracking=True, translate=True)
    product_id = fields.Many2one('extenss.product.product', string='Product', tracking=True, translate=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson Id', tracking=True, translate=True)
    office_id = fields.Many2one('crm.team', string='Branch office Id', tracking=True, translate=True)
    anchor_id = fields.Char(string='Financial funding', tracking=True, translate=True)
    bill_id = fields.Many2one('extenss.credit.account', string='Bill', tracking=True, translate=True)
    customer_type = fields.Selection([('person','Individual'),('company','Company')], string='Customer type', tracking=True, translate=True)
    #customer_name = fields.Char(string='Customer', tracking=True, translate=True)
    amount_financed = fields.Monetary(string='Amount Financed', currency_field='company_currency', tracking=True, translate=True)
    term = fields.Integer(string='Term', tracking=True, translate=True)
    frequency = fields.Many2one('extenss.product.frequencies', string='Frequency', tracking=True, translate=True)
    vat_factor = fields.Float('VAT factor', (2,6), tracking=True, translate=True)
    rate_type = fields.Char(string='Rate type', tracking=True, translate=True)
    base_rate_type = fields.Char(string='Base rate type', tracking=True, translate=True)
    base_rate_value = fields.Float('Base rate value', (2,6), tracking=True, translate=True)
    differential = fields.Float('Differential', (2,6), tracking=True, translate=True)
    interest_rate = fields.Float('Interest rate', (2,6), tracking=True, translate=True)
    rate_arrears_interest = fields.Float('Factor', (2,1), tracking=True)
    factor_rate = fields.Float('Rate interest moratorium', (2,6), tracking=True)
    #default_factors = fields.Float('Default factors', (2,6), tracking=True, translate=True)##preguntar el nombre en ingles
    days_notice = fields.Integer(string='Days to notice', tracking=True, translate=True)
    type_credit = fields.Many2one('extenss.product.credit_type', string='Type of Credit', tracking=True, translate=True)
    hiring_date = fields.Date(string='Hiring date', tracking=True, translate=True)
    first_payment_date = fields.Date(string='First payment date', tracking=True, translate=True)
    dispersion_date = fields.Date(string='Dispersion date', tracking=True, translate=True)
    last_payment_date = fields.Date(string='Last payment date', tracking=True, translate=True)
    purchase_option = fields.Float('% Purchase option', (2,6), tracking=True, translate=True)
    purchase_option_amount = fields.Monetary(string='Purchase option amount', currency_field='company_currency', tracking=True, translate=True)
    residual_value = fields.Float('% Residual value', (2,6), tracking=True, translate=True)
    amount_residual_value = fields.Monetary(string='Amount of Residual Value', currency_field='company_currency', tracking=True, translate=True)
    total_paid = fields.Monetary(string='Total Paid', currency_field='company_currency', tracking=True, translate=True)
    outstanding_balance = fields.Monetary(string='Outstanding balance', currency_field='company_currency', tracking=True, translate=True)
    past_due_interest = fields.Monetary(string='Past due interest', currency_field='company_currency', tracking=True, translate=True)
    overdue_capital = fields.Monetary(string='Overdue capital', currency_field='company_currency', tracking=True, translate=True)
    expired_capital_vat = fields.Monetary(string='Expired capital VAT', currency_field='company_currency', tracking=True, translate=True)
    expired_interest_vat = fields.Monetary(string='Expired interest VAT', currency_field='company_currency', tracking=True, translate=True)
    overdue_balance = fields.Monetary(string='Overdue balance', compute='_compute_overdue_balance', store=True, currency_field='company_currency', tracking=True, translate=True)
    deposit_income = fields.Monetary(string='Deposit income', currency_field='company_currency', tracking=True, translate=True)
    income_tax_deposit = fields.Monetary(string='Income Tax on deposit', currency_field='company_currency', tracking=True, translate=True)
    total_deposit_income = fields.Monetary(string='Total deposit income', currency_field='company_currency', tracking=True, translate=True)
    percentage_guarantee_deposit = fields.Float('% Guarantee deposit', (2,6), tracking=True, translate=True)
    guarantee_deposit = fields.Monetary(string='Guarantee deposit', currency_field='company_currency', tracking=True, translate=True)
    vat_guarantee_deposit = fields.Monetary(string='VAT guarantee deposit', currency_field='company_currency', tracking=True, translate=True)
    total_guarantee_deposit = fields.Monetary(string='Total guarantee deposit', currency_field='company_currency', tracking=True, translate=True)
    dep_income_application = fields.Monetary(string='Deposit Income Application', currency_field='company_currency', tracking=True, translate=True)
    guarantee_dep_application = fields.Monetary(string='Guarantee Deposit Application', currency_field='company_currency', tracking=True, translate=True)
    balance_income_deposit = fields.Monetary(string='Balance of Income on deposit', currency_field='company_currency', tracking=True, translate=True)
    guarantee_dep_balance = fields.Monetary(string='Guarantee Deposit Balance', currency_field='company_currency', tracking=True, translate=True)
    days_transfer_past_due = fields.Integer(string='Days to transfer to past due portfolio', tracking=True, translate=True)
    number_days_overdue = fields.Integer(string='Number of days overdue', tracking=True, translate=True)
    portfolio_type = fields.Selection([('vigente','Valid'),('vencida','Expired'),('restructuring','Restructuring')], string='Portfolio Type', tracking=True, translate=True)
    credit_status = fields.Selection(CREDIT_STATUS, string='Credit status', tracking=True, translate=True)
    percentage_commission = fields.Float('% Commission', (2,6), tracking=True, translate=True)
    commission_amount = fields.Monetary(string='Commission amount', currency_field='company_currency', tracking=True, translate=True)
    commission_vat = fields.Monetary(string='Commission VAT', currency_field='company_currency', tracking=True, translate=True)
    total_commission = fields.Monetary(string='Total commission', currency_field='company_currency', tracking=True, translate=True)
    ratification = fields.Monetary(string='Ratification', currency_field='company_currency', tracking=True, translate=True)
    ratification_vat = fields.Monetary(string='Ratification VAT', currency_field='company_currency', tracking=True, translate=True)
    total_ratification = fields.Monetary(string='Total Ratification', currency_field='company_currency', tracking=True, translate=True)
    initial_total_payment = fields.Monetary(string='Initial total payment', currency_field='company_currency', tracking=True, translate=True)
    order_id = fields.Integer(String='Order')
    account_status_date = fields.Date(string=u'Account Status Date',
    default=fields.Date.context_today)
    cs = fields.Boolean(String='CS')
    af = fields.Boolean(String='AF')
    ap = fields.Boolean(String='AP')
    dn = fields.Boolean(string='DN')
    ff = fields.Boolean(string='FF')
    amortization_ids = fields.One2many(
        'extenss.credit.amortization', 
        'credit_id', 
        string='Amortization Table')
    leased_team = fields.Char('Leased Team')
    amount_si = fields.Monetary('Amount s/iva', currency_field='company_currency', tracking=True)
    tax_amount = fields.Monetary('Tax Amount', currency_field='company_currency', tracking=True)
    date_limit_pay = fields.Date('Limit Date')
    calculation_base = fields.Char('Calculation Base')
    request_count = fields.Integer(string='Request', compute='get_request_count',  tracking=True)
    flag_early_settlement = fields.Boolean(string='Early settlement', default=False, tracking=True, translate=True)
    moras_ids = fields.One2many(
        'extenss.credit.moras', 
        'credit_id', 
        string='Moras Table')
    notice_date = fields.Date(string=u'Expiry Notices',
    default=fields.Date.context_today)
    payment_date = fields.Date(string=u'Register Payment',
    default=fields.Date.context_today)
    include_taxes = fields.Boolean('Include Taxes', default=False,  translate=True)
    frequency_days = fields.Integer(string='Frequency Days', tracking=True, translate=True)
    iva = fields.Monetary('IVA',  currency_field='company_currency', tracking=True)
    total_purchase_rcal = fields.Monetary('Total Purchase', currency_field='company_currency', tracking=True)
    iva_purchase_rcal = fields.Monetary('IVA Purchase',  currency_field='company_currency', tracking=True)
    residual_value_rcal = fields.Monetary('Residual Value', currency_field='company_currency', tracking=True)
    purchase_option_amount_rcal = fields.Monetary(string='Purchase option amount', currency_field='company_currency', tracking=True, translate=True)
    total_payment = fields.Monetary(string='Total payment', currency_field='company_currency', tracking=True, translate=True)
    reference_number = fields.Char(string='Reference number', size=50, tracking=True, translate=True)
    number_pay_rest = fields.Char(string="Number of payments for restructuring", translate=True)

    count_moras = fields.Integer(string='Total Moras', compute='_get_moras', store=True)
    total_moras = fields.Monetary(string='Total Amount Moras', compute='_get_amount_moras', store=True, currency_field='company_currency')

    ######
    sum_capital = fields.Monetary(string='Paid capital', currency_field='company_currency', compute='_compute_amount_capital', store=True, tracking=True, translate=True)
    sum_interest = fields.Monetary(string='Paid interest', currency_field='company_currency', compute='_compute_amount_interest', store=True, tracking=True, translate=True)
    sum_capvat = fields.Monetary(string='Paid VAT capital', currency_field='company_currency', compute='_compute_amount_capvat', store=True, tracking=True, translate=True)
    sum_intvat = fields.Monetary(string='Paid VAT interest', currency_field='company_currency', compute='_compute_amount_intvat', store=True, tracking=True, translate=True)
    ########

    ###Liquidacion Anticipada###
    date_settlement = fields.Date(string='Settlement date', required=True, tracking=True, translate=True, default=fields.Date.context_today)
    penalty = fields.Float('Penalty', (2,6), tracking=True, translate=True)
    outstanding_balance = fields.Monetary(string='Outstanding balance', currency_field='company_currency', tracking=True, translate=True)
    overdue_balance = fields.Monetary(string='Overdue Balance', currency_field='company_currency', tracking=True, translate=True)
    days_interest = fields.Integer(string='Days of interest', tracking=True, translate=True)
    interests = fields.Monetary(string='Interests', currency_field='company_currency', tracking=True, translate=True)
    interests_moratoriums = fields.Monetary(string='Interests moratoriums', currency_field='company_currency', tracking=True, translate=True)
    vat_interest_mora = fields.Monetary(string='Interest moratoriums VAT', currency_field='company_currency', tracking=True, translate=True)
    capital_vat= fields.Monetary(string='Capital VAT', currency_field='company_currency', tracking=True, translate=True)
    interests_vat = fields.Monetary(string='Interests VAT', currency_field='company_currency', tracking=True, translate=True)

    penalty_amount = fields.Monetary(string='Penalty Amount', currency_field='company_currency', tracking=True, translate=True)
    purchase_option = fields.Monetary(string='Purchase option', currency_field='company_currency', tracking=True, translate=True)
    vat_purchase_option = fields.Monetary(string='VAT Purchase option', currency_field='company_currency', tracking=True, translate=True)
    security_deposit_balance = fields.Monetary(string='Security Deposit Balance', currency_field='company_currency', tracking=True, translate=True)
    balance_income_deposit = fields.Monetary(string='Balance Income on Deposit', currency_field='company_currency', tracking=True, translate=True)
    total_settle = fields.Monetary(string='Total to Settle', currency_field='company_currency', tracking=True, translate=True)
    balance_inicial = fields.Monetary(string='Balance initial', currency_field='company_currency', tracking=True, translate=True)

    conciliation_credit_ids = fields.Many2many('extenss.credit.conciliation_lines',string='Payment')
    #balance = fields.Monetary(related='bill_id.balance',currency_field='company_currency')

    penalty_adv = fields.Float('Penalty', (2,2), tracking=True, translate=True)
    advance_date = fields.Date(string='Advance date', required=True, tracking=True, translate=True, default=fields.Date.context_today)
    amount_req = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    advan_type = fields.Selection([('term', 'Term'),('amount', 'Amount')], string='Type', currency_field='company_currency', tracking=True, translate=True)
    interests_adv = fields.Monetary(string='Interests', currency_field='company_currency', tracking=True, translate=True)
    interests_vat_adv = fields.Monetary(string='Interests VAT', currency_field='company_currency', tracking=True, translate=True)
    capital_vat_adv = fields.Monetary(string='Capital VAT', currency_field='company_currency', tracking=True, translate=True)
    days_interest_adv = fields.Integer(string='Days of interest', tracking=True, translate=True)
    penalty_amount_adv = fields.Monetary(string='Penalty Amount', currency_field='company_currency', tracking=True, translate=True)
    total_advance_adv = fields.Monetary(string='Total advance', currency_field='company_currency', tracking=True, translate=True)
    balance_initial_adv = fields.Monetary(string='Balance initial', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    credit_expiry_ids = fields.One2many('extenss.credit.expiry_notices', 'credit_expiry_id', string=' ', tracking=True)
    restructuring_ids = fields.One2many('extenss.credit.restructuring_table', 'credit_id', string=' ', tracking=True)
    credit_condonation_ids = fields.One2many('extenss.credit.expiry_notices', 'credit_expiry_id', string=' ', tracking=True)
    credit_moras_ids = fields.One2many('extenss.credit.expiry_notices', 'credit_expiry_id', string=' ', tracking=True)

    @api.depends('past_due_interest','expired_interest_vat','overdue_capital','expired_capital_vat')
    def _compute_overdue_balance(self):
        for reg in self:
            reg.overdue_balance = reg.past_due_interest + reg.expired_interest_vat + reg.overdue_capital + reg.expired_capital_vat

    @api.depends('credit_moras_ids')
    def _get_moras(self):
        for reg in self:
            reg.count_moras = len(reg.credit_moras_ids)

    @api.depends('credit_moras_ids','credit_moras_ids.total_paid_moras')
    def _get_amount_moras(self):
        for reg in self:
            reg.total_moras = sum([line.total_paid_moras for line in reg.credit_moras_ids])

    #########
    @api.depends('credit_expiry_ids','credit_expiry_ids.sum_con_capital')
    def _compute_amount_capital(self):
        for reg in self:
            reg.sum_capital = sum([line.sum_con_capital for line in reg.credit_expiry_ids])

    @api.depends('credit_expiry_ids','credit_expiry_ids.sum_con_interest')
    def _compute_amount_interest(self):
        for reg in self:
            reg.sum_interest = sum([line.sum_con_interest for line in reg.credit_expiry_ids])

    @api.depends('credit_expiry_ids','credit_expiry_ids.sum_con_capvat')
    def _compute_amount_capvat(self):
        for reg in self:
            reg.sum_capvat = sum([line.sum_con_capvat for line in reg.credit_expiry_ids])

    @api.depends('credit_expiry_ids','credit_expiry_ids.sum_con_intvat')
    def _compute_amount_intvat(self):
        for reg in self:
            reg.sum_intvat = sum([line.sum_con_intvat for line in reg.credit_expiry_ids])
    ###########

    @api.model
    def create(self, reg):
        if reg:
            if reg.get('credit_id', _('New')) == _('New'):
                reg['credit_id'] = self.env['ir.sequence'].next_by_code('extenss.credit') or _('New')
            result = super(Credits, self).create(reg)
            return result

    def action_calculate_moras(self):
        #date_act = datetime.now().date()
        rate_mora = self.factor_rate
        vat_credit = self.vat_factor
        int_fact_mora = self.factor_rate
        base_type = self.calculation_base
        itr = self.interest_rate

        if base_type == '360/360':
            base = 360
        if base_type == '365/365' or base_type == '360/365':
            base = 365

        reg_moras = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id)])
        for reg in reg_moras:
            if reg.payment_date:
                days_mora = (reg.payment_date - reg.due_not_date).days
            else:
                days_mora = 0
            #else:
                #days_mora = (date_act - reg.due_not_date).days
                #days_mora = (reg.start_date_mora - reg.due_not_date).days

            int_mora = reg.outstanding_balance * ((int_fact_mora/100)/base) * days_mora
            vat_int_mora = vat_interest_mora = (vat_credit/100) * int_mora
            
            reg.interest_moratoriums = int_mora
            reg.vat_interest_mora = vat_int_mora
            reg.rate_moratorium = rate_mora
            reg.days_mora = days_mora
            reg.total_interest_mora = int_mora + vat_int_mora
            #reg.balance_interest_mora = int_mora + vat_int_mora

    def action_condonation(self):
        totalmoras = 0
        print('entra a condonation')
        condonations = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('amount_condonation', '>', 0),('balance_interest_mora', '>', 0)])
        for reg_cond in condonations:
            concepts = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id', '=', reg_cond.id)])
            for concept in concepts:
                if concept.concept == 'morint' or concept.concept == 'morintvat':
                    totalmoras += concept.total_paid_concept

            totalmoras = totalmoras + reg_cond.amount_condonation 
            if reg_cond.amount_condonation <= totalmoras:
            #     reg_cond.balance_interest_mora = 0
            # else:
            #     reg_cond.balance_interest_mora = reg_cond.total_interest_mora - reg_cond.amount_condonation
                exist = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id', '=', reg_cond.id),('concept', '=', 'condonation')])
                if exist:
                    exist.write({
                        'amount_concept': exist.amount_concept + reg_cond.amount_condonation
                    })
                else:
                    morint = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id', '=', reg_cond.id),('concept', '=', 'morint')])
                    mointvat = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id', '=', reg_cond.id),('concept', '=', 'morintvat')])
                    exp_id = self.env['extenss.credit.concepts_expiration'].create({
                        'expiry_notice_id': reg_cond.id,
                        'concept': 'condonation',
                        'amount_concept': reg_cond.amount_condonation,
                        'total_paid_concept': reg_cond.amount_condonation,
                        'full_paid': True,
                    })
                    morint.write({
                        'full_paid': True
                    })
                    mointvat.write({
                        'full_paid': True
                    })

                self.env['extenss.credit.concept_payments'].create({
                    'concept_pay_id': exp_id.id,
                    'date_paid': datetime.now().date(),
                    'total_paid_cp': reg_cond.amount_condonation,
                })
            # print(' reg_cond.total_paid_not ', reg_cond.total_paid_not)
            # print('reg_cond.amount_condonation', reg_cond.amount_condonation)
            # reg_cond.total_paid_not = reg_cond.total_paid_not + reg_cond.amount_condonation
            #search([('expiry_notice_id', '=', self.id)])
            # for concept in concepts:
            #     concept.concept

    def check_credits(self):
        rec_en = self.env['extenss.credit.expiry_notices']
        rec_cp = self.env['extenss.credit.concepts_expiration']
        credit_rec = self.env['extenss.credit'].search([('credit_status', '=', 'active'),('flag_early_settlement', '=', False)])
        for reg in credit_rec:
            now =  reg.notice_date
            new_date = now + timedelta(days=1)
            records_amortization = self.env['extenss.credit.amortization'].search([('credit_id', '=', reg.id),('expiration_date', '=', new_date)])

            print('reg.id', reg.id)
            print('new_date', new_date)
            print('records_amortization.no_pay', records_amortization.no_pay)
            val_regs = self.env['extenss.credit.expiry_notices'].search_count([('credit_expiry_id', '=', reg.id),('due_not_date', '=', new_date),('payment_number', '=', records_amortization.no_pay)])

            if val_regs == 0:
                for rec in records_amortization:
                    if reg.cs == False and reg.dn == False and reg.ff == False:
                        amount = rec.total_rent
                    else:
                        amount = rec.payment

                    rec_en.create({
                        'credit_expiry_id': reg.id,
                        'payment_number': rec.no_pay,
                        'due_not_date': rec.expiration_date,
                        'amount_not': amount,
                        'total_paid_not': 0,
                        'total_to_pay': 0,
                        'outstanding_balance': rec.initial_balance,
                        'rate_moratorium': reg.factor_rate
                        #'rent': rec.total_rent,
                    })

                    rec_notice = self.env['extenss.credit.expiry_notices'].search([('payment_number', '=', rec.no_pay),('credit_expiry_id', '=', reg.id),('req_credit_id', '=', False)])
                    for r in rec_notice:
                        if reg.af or reg.cs or reg.dn or reg.ff:
                            rec_cp.create({
                                'expiry_notice_id': r.id,
                                'concept': 'capital',
                                'amount_concept': rec.capital,
                                'total_paid_concept': 0,
                                'full_paid': False,
                            })
                        if reg.af:
                            rec_cp.create({
                                'expiry_notice_id': r.id,
                                'concept': 'capvat',
                                'amount_concept': rec.iva_capital,
                                'total_paid_concept': 0,
                                'full_paid': False,
                            })
                        if reg.af or reg.cs or reg.dn or reg.ff:
                            rec_cp.create({
                                'expiry_notice_id': r.id,
                                'concept': 'interest',
                                'amount_concept': rec.interest,
                                'total_paid_concept': 0,
                                'full_paid': False,
                            })
                            rec_cp.create({
                                'expiry_notice_id':r.id,
                                'concept': 'intvat',
                                'amount_concept': rec.iva_interest,
                                'total_paid_concept': 0,
                                'full_paid': False,
                            })
                        if reg.ap:
                            rec_cp.create({
                                'expiry_notice_id': r.id,
                                'concept': 'payment',
                                'amount_concept': rec.payment,
                                'total_paid_concept': 0,
                                'full_paid': False,
                            })
                            rec_cp.create({
                                'expiry_notice_id': r.id,
                                'concept': 'paymentvat',
                                'amount_concept': rec.iva_rent,
                                'total_paid_concept': 0,
                                'full_paid': False,
                            })
                    reg.outstanding_balance = rec.initial_balance #08072020

    def register_payment(self):
        #Se comenta el codigo ya que los creditos se crean en activos
        # credit_s = self.env['extenss.credit'].search([('credit_status', '=', 'pending')])
        # for credit in credit_s:
        #     accnts = self.env['extenss.credit.account'].search([('id', '=', credit.bill_id.id)])
        #     for accnt in accnts:
        #         total_deposit = credit.total_deposit_income + credit.total_guarantee_deposit
        #         #if accnt.balance >= credit.total_deposit_income or accnt.balance >= credit.total_guarantee_deposit:
        #         if accnt.balance >= total_deposit:
        #             credit.credit_status = 'active'

        credit_rec = self.env['extenss.credit'].search([('credit_status', '=', 'active')])
        for cred in credit_rec:
            date_payment = cred.payment_date
            not_rec = self.env['extenss.credit.expiry_notices'].search([('due_not_date','=',date_payment),('req_credit_id', '!=', False),('credit_expiry_id.id','=',cred.id)])
            amount=0
            for reg in not_rec:
                if reg.total_to_pay>0:
                    records_account = self.env['extenss.credit.account'].search([('customer_id', '=', reg.credit_expiry_id.customer_id.id)])
                    for act in records_account:
                        req=self.env['extenss.credit.request'].search(['&','|',('id', '=', reg.req_credit_id),('type_request','=','early_settlement'),('type_request','=','atc')])
                        if req.state == 'pending':
                            ex_no=self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id.id','=',req.credit_request_id.id),('total_to_pay','>',0)])
                            over_balance=req.total_settle-req.overdue_balance
                            for exno in ex_no:
                                if exno.req_credit_id == False:
                                    over_balance=over_balance+exno.total_to_pay
                            over_balance=round(over_balance,2)
                            if act.balance>=over_balance:
                                req.write({
                                'state': 'applied'
                                })
                                reg.write({
                                'payment_date': date_payment
                                })
                                cred.write({
                                    'last_payment_date': datetime.now().date()
                                })

                                concepts_expiration = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id','=',reg.id)])
                                for conexp in concepts_expiration :
                                    conexp.write({
                                    'total_paid_concept': round(conexp.amount_concept,2)
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(conexp.amount_concept,2))
                                    })
                                    amount=round(conexp.amount_concept,2)
                                    self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                                    cred.total_paid += amount #08072020
                                ex_no=self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id.id','=',req.credit_request_id.id),('req_credit_id', '=', False)])
                                for exno in ex_no:
                                    concepts_expiration = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id.id','=',exno.id)])
                                    for conexp in concepts_expiration :
                                        if conexp.full_paid == False:
                                            amount=round((conexp.amount_concept-conexp.total_paid_concept),2)
                                            conexp.write({
                                            'total_paid_concept': round(conexp.amount_concept,2)
                                            })
                                            conpay = self.env['extenss.credit.concept_payments']
                                            conpay.create({
                                            'concept_pay_id': conexp.id,
                                            'concept_id': exno.id,
                                            'date_paid': date_payment,
                                            'total_paid_cp': (round(amount,2))
                                            })
                                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                                            cred.total_paid += amount #08072020
                            else:
                                req.write({
                                'state': 'cancelled'
                                })
                                credit=self.env['extenss.credit'].search([('id','=',req.credit_request_id.id)])
                                credit.write({
                                'flag_early_settlement': False
                                })

                        if req.type_request == 'atc' and req.state == 'applied' :
                            if req.type_credit_cs:
                                type_move = req.advan_type_cs
                            if req.type_credit_af:
                                type_move = req.advan_type_af
                            if req.type_credit_ap:
                                type_move = req.advan_type_ap

                            self.recalculate_amortization_table(req.credit_request_id.id, req.id, type_move)

            not_rec = self.env['extenss.credit.expiry_notices'].search([('due_not_date','<=',date_payment),('total_to_pay', '>', '0'),('req_credit_id', '=', False),('credit_expiry_id.id','=',cred.id)])
            for reg in not_rec:
                records_account = self.env['extenss.credit.account'].search([('customer_id', '=', reg.credit_expiry_id.customer_id.id)])
                for act in records_account:
                    calculation_base = self.env['extenss.credit'].search([('credit_expiry_ids.id','=',reg.id)]).calculation_base
                    cs = self.env['extenss.credit'].search([('credit_expiry_ids.id','=',reg.id)]).cs
                    ap = self.env['extenss.credit'].search([('credit_expiry_ids.id','=',reg.id)]).ap
                    vatf = self.env['extenss.credit'].search([('credit_expiry_ids.id','=',reg.id)]).vat_factor
                    int_rate = self.env['extenss.credit'].search([('credit_expiry_ids.id','=',reg.id)]).factor_rate
                    if calculation_base == '360/360' or calculation_base == '360/365' :
                        base=360
                    else:
                        base=365
                    concepts_expiration = self.env['extenss.credit.concepts_expiration']
                    exist_rec_mor = concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','morint')])
                    capital_pay =concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','capital')]).total_paid_concept
                    capital_ven =concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','capital')]).amount_concept
                    int_pay=concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','interest')]).full_paid

                    if ap == True :
                        capital_pay =concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','payment')]).total_paid_concept
                        capital_ven =concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','payment')]).amount_concept
                    capital_ven=capital_ven-capital_pay
                    int_mor=capital_ven * (int_rate/base/100)
                    if act.balance>0:
                        if not reg.payment_date:
                            dias_atr=(date_payment - reg.due_not_date).days
                        else:
                            dias_atr=(date_payment - reg.payment_date).days
                        if date_payment > reg.due_not_date and dias_atr>0 and reg.total_to_pay>0:
                            int_mor=round(int_mor*dias_atr,2)
                            amount_n=0
                            moras_table = self.env['extenss.credit.moras']
                            if not exist_rec_mor :
                                concepts_expiration.create({
                                'expiry_notice_id': reg.id,
                                'concept': 'morint',
                                'amount_concept': int_mor,
                                'total_paid_concept': 0,
                                'full_paid': False,
                                })
                                amount_n=round(int_mor,2)
                                concepts_expiration.create({
                                'expiry_notice_id': reg.id,
                                'concept': 'morintvat',
                                'amount_concept':(round(int_mor * (vatf/100),2)),
                                'total_paid_concept': 0,
                                'full_paid': False,
                                })
                                amount_n=amount_n+round(int_mor * (vatf/100),2)

                                moras_table.create({
                                    'credit_id': reg.credit_expiry_id.id,
                                    'init_date': reg.due_not_date,
                                    'end_date': date_payment,
                                    'days': (date_payment - reg.due_not_date).days,
                                    'past_due_balance': capital_ven,
                                    'rate':(int_rate/base/100),
                                    'interest':amount_n,
                                    'amount_to_payment':reg.amount_not+amount_n
                                })
                            else:
                                exist_rec_mor.write({
                                'amount_concept':(round(exist_rec_mor.amount_concept+int_mor,2)),
                                'full_paid': False,
                                })
                                amount_n=round(int_mor,2)
                                exist_rec_morvat = concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','morintvat')])
                                exist_rec_morvat.write({
                                'amount_concept':(round(exist_rec_mor.amount_concept * (vatf/100),2)),
                                'full_paid': False,
                                })
                                amount_n=amount_n+round(int_mor * (vatf/100),2)
                                moras_table=moras_table.search([('credit_id','=',reg.credit_expiry_id.id),('init_date','=',reg.due_not_date)])
                                moras_table.write({
                                    'end_date':date_payment,
                                    'days': (date_payment - reg.due_not_date ).days,
                                    'past_due_balance': capital_ven,
                                    'rate':(int_rate/base/100),
                                    'interest':moras_table.interest+amount_n,
                                    'amount_to_payment':reg.amount_not+amount_n
                                })
                            reg.write({
                                'amount_not':reg.amount_not+amount_n
                            })

                        concepts_expiration = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id','=',reg.id)])
                        interest,intpay,intvat,intvatpay,capital,capay,capvat,capvatpay,morint,morintpay,morintvat,morintvatpay,payment,paypay,payvat,payvatpay,balance=0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,act.balance
                        fpint,fpcap,fpmorint,fppay,fppayvat=True,True,True,True,True
                        for conexp in concepts_expiration :
                            if conexp.concept == 'morint' :
                                morint=conexp.amount_concept 
                                fpmorint=conexp.full_paid
                                morintpay=conexp.total_paid_concept
                            if conexp.concept == 'morintvat' :
                                morintvat=conexp.amount_concept 
                                morintvatpay=conexp.total_paid_concept
                            if conexp.concept == 'interest' :
                                interest=conexp.amount_concept 
                                fpint=conexp.full_paid
                                intpay=conexp.total_paid_concept
                            if conexp.concept == 'intvat' :
                                intvat=conexp.amount_concept 
                                intvatpay=conexp.total_paid_concept
                            if conexp.concept == 'capital' :
                                capital=conexp.amount_concept
                                fpcap=conexp.full_paid
                                capay=conexp.total_paid_concept
                            if conexp.concept == 'capvat' :
                                capvat=conexp.amount_concept
                                capvatpay=conexp.total_paid_concept
                            if conexp.concept == 'payment' :
                                payment=conexp.amount_concept
                                fppay=conexp.full_paid
                                paypay=conexp.total_paid_concept
                            if conexp.concept == 'paymentvat' :
                                payvat=conexp.amount_concept
                                fppayvat=conexp.full_paid
                                payvatpay=conexp.total_paid_concept
                        if balance >= ((morint+morintvat)-(morintpay+morintvatpay)) and fpmorint == False:
                            fpmorint=True
                            balance=balance-((morint+morintvat)-(morintpay+morintvatpay))
                            reg.write({
                            'payment_date': date_payment
                            })
                            cred.write({
                                'last_payment_date': datetime.now().date()
                            })
                            amount=0
                            for conexp in concepts_expiration :
                                if conexp.concept == 'morint' :
                                    conexp.write({
                                    'total_paid_concept': round(conexp.amount_concept,2)
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round((conexp.amount_concept - morintpay),2))
                                    })
                                    amount=round((conexp.amount_concept - morintpay),2)
                                if conexp.concept == 'morintvat' :
                                    conexp.write({
                                    'total_paid_concept':(round(conexp.amount_concept,2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round((conexp.amount_concept - morintvatpay),2))
                                    })
                                    amount=amount+round((conexp.amount_concept - morintvatpay),2)
                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                            cred.total_paid += amount #08072020
                        elif balance>0 and fpmorint == False :
                            amount=0
                            for conexp in concepts_expiration :
                                if conexp.concept == 'morint' :
                                    conexp.write({
                                    'total_paid_concept': (round((balance/(1+(vatf/100)) + morintpay),2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(balance/(1+(vatf/100)),2))
                                    })
                                    amount=(round(balance/(1+(vatf/100)),2))
                                if conexp.concept == 'morintvat' :
                                    conexp.write({
                                    'total_paid_concept': (round((((balance/(1+(vatf/100)))*(vatf/100)) + morintvatpay),2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(((balance/(1+(vatf/100)))*(vatf/100)),2))
                                    })
                                    amount=amount+round(((balance/(1+(vatf/100)))*(vatf/100)),2)
                            balance=0
                            reg.write({
                            'payment_date': date_payment
                            })
                            cred.write({
                                'last_payment_date': datetime.now().date()
                            })
                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                            cred.total_paid += amount #08072020
                        if balance > 0 and payvat>0 and  fpmorint == True and fppayvat==False:
                            if balance>= (payvat-payvatpay):
                                balance=balance-(payvat-payvatpay)
                                total_paid_concept=(payvat-payvatpay)
                            else:
                                total_paid_concept=balance
                                balance=0
                            if payvat == (total_paid_concept+payvatpay) :
                                fppayvat=True
                            reg.write({
                            'payment_date': date_payment
                            })
                            cred.write({
                                'last_payment_date': datetime.now().date()
                            })
                            amount=0
                            for conexp in concepts_expiration :
                                if conexp.concept == 'paymentvat' :
                                    conexp.write({
                                    'total_paid_concept': (round((total_paid_concept+payvatpay),2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(total_paid_concept,2))
                                    })
                                    amount=round(total_paid_concept,2)
                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                            cred.total_paid += amount #08072020
                        if balance > 0 and payment>0 and fppayvat==True and  fpmorint == True and fppay==False:
                            if balance>= (payment-paypay):
                                balance=balance-(payment-paypay)
                                total_paid_concept=(payment-paypay)
                            else:
                                total_paid_concept=balance
                                balance=0
                            reg.write({
                            'payment_date': date_payment
                            })
                            cred.write({
                                'last_payment_date': datetime.now().date()
                            })
                            amount=0
                            for conexp in concepts_expiration :
                                if conexp.concept == 'payment' :
                                    conexp.write({
                                    'total_paid_concept': (round((total_paid_concept+paypay),2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(total_paid_concept,2))
                                    })
                                    amount=round(total_paid_concept,2)
                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                            cred.total_paid += amount #08072020
                        if balance >= ((interest+intvat)-(intpay+intvatpay)) and interest>0 and fpmorint == True and fpint == False:
                            fpint=True
                            balance=balance-((interest+intvat)-(intpay+intvatpay))
                            reg.write({
                            'payment_date': date_payment
                            })
                            cred.write({
                                'last_payment_date': datetime.now().date()
                            })
                            amount=0
                            for conexp in concepts_expiration :
                                if conexp.concept == 'interest' :
                                    conexp.write({
                                    'total_paid_concept': (round(conexp.amount_concept,2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round((conexp.amount_concept - intpay),2))
                                    })
                                    amount=round((conexp.amount_concept - intpay),2)
                                if conexp.concept == 'intvat' :
                                    conexp.write({
                                    'total_paid_concept': (round(conexp.amount_concept,2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({ 
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round((conexp.amount_concept - intvatpay),2))
                                    })
                                    amount=amount+round((conexp.amount_concept - intvatpay),2)
                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                            cred.total_paid += amount #08072020
                        elif balance>0 and interest>0 and fpmorint == True and fpint == False:
                            amount=0
                            for conexp in concepts_expiration :
                                if conexp.concept == 'interest' :
                                    conexp.write({
                                    'total_paid_concept': (round(((balance/(1+(vatf/100))) + intpay),2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(balance/(1+(vatf/100)),2))
                                    })
                                    amount=(round(balance/(1+(vatf/100)),2))
                                if conexp.concept == 'intvat' :
                                    conexp.write({
                                    'total_paid_concept': (round((((balance/(1+(vatf/100))))*(vatf/100) + intvatpay),2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(((balance/(1+(vatf/100)))*(vatf/100)),2))
                                    })
                                    amount=amount+round(((balance/(1+(vatf/100)))*(vatf/100)),2)
                            balance=0
                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                            cred.total_paid += amount #08072020
                            reg.write({
                            'payment_date': date_payment
                            })
                            cred.write({
                                'last_payment_date': datetime.now().date()
                            })
                        if balance >= ((capital+capvat)-(capay+capvatpay)) and fpint== True and fpcap == False :
                            balance=balance-((capital+capvat)-(capay+capvatpay))
                            reg.write({
                            'payment_date': date_payment
                            })
                            cred.write({
                                'last_payment_date': datetime.now().date()
                            })
                            amount=0
                            for conexp in concepts_expiration :
                                if conexp.concept == 'capital' :
                                    conexp.write({
                                    'total_paid_concept': (round(conexp.amount_concept,2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round((conexp.amount_concept - capay),2))
                                    })
                                    amount=round((conexp.amount_concept - capay),2)
                                if conexp.concept == 'capvat' :
                                    conexp.write({
                                    'total_paid_concept': (round(conexp.amount_concept,2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round((conexp.amount_concept - capvatpay),2))
                                    })
                                    amount=amount+round((conexp.amount_concept - capvatpay),2)
                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                            cred.total_paid += amount #08072020
                        elif balance>0 and fpint == True and fpcap == False:
                            total_paid_concept=balance + capay
                            amount=0
                            for conexp in concepts_expiration :
                                if conexp.concept == 'capital' :
                                    if cs == False:
                                        total_paid_concept = ((balance/(1+(vatf/100))) + capay)
                                    conexp.write({
                                    'total_paid_concept': (round(total_paid_concept,2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round((total_paid_concept - capay),2))
                                    })
                                    amount=round((total_paid_concept - capay),2)
                                if conexp.concept == 'capvat' :
                                    conexp.write({
                                    'total_paid_concept': (round((((balance/(1+(vatf/100))))*(vatf/100) + capvatpay),2))
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp':(round(((balance/(1+(vatf/100)))*(vatf/100)),2))
                                    })
                                    amount=amount+round(((balance/(1+(vatf/100)))*(vatf/100)),2)
                            balance=0
                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                            cred.total_paid += amount #08072020
                            reg.write({
                            'payment_date': date_payment
                            })
                            cred.write({
                                'last_payment_date': datetime.now().date()
                            })

            notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id.id', '=', cred.id)])
            tmp_cap = 0
            tmp_int = 0
            tmp_cap_vat = 0
            tmp_int_vat = 0
            for notice in notices:
                if notice.total_to_pay > 0:
                    concepts = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id', '=', notice.id)])
                    for concept in concepts:
                        print('concept.id', concept.id)
                        if cred.cs or cred.af:
                            if concept.concept == 'capital':
                                tmp_cap += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.overdue_capital', cred.overdue_capital)
                            if concept.concept == 'interest':
                                tmp_int += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.past_due_interest', cred.past_due_interest)
                            if concept.concept == 'intvat':
                                tmp_int_vat += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.expired_interest_vat', cred.expired_interest_vat)
                        if cred.af:
                            if concept.concept == 'capvat':
                                tmp_cap_vat += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.expired_capital_vat', cred.expired_capital_vat)
                        if cred.ap:
                            if concept.concept == 'payment':
                                tmp_cap += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.overdue_capital', cred.overdue_capital)
                            if concept.concept == 'paymentvat':
                                tmp_cap_vat += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.expired_capital_vat', cred.expired_capital_vat)
                            if concept.concept == 'intvat':
                                tmp_int_vat += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.expired_interest_vat', cred.expired_interest_vat)

            cred.overdue_capital = tmp_cap
            cred.past_due_interest = tmp_int
            cred.expired_capital_vat = tmp_cap_vat
            cred.expired_interest_vat = tmp_int_vat

            expirys = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id.id', '=', cred.id)])
            tmp_days = 0
            for expiry in expirys:
                now = datetime.now().date()
                if expiry.total_to_pay > 0:
                    days_due = (now - expiry.due_not_date).days
                    if days_due > tmp_days:
                        tmp_days = days_due
            
            cred.number_days_overdue = tmp_days

    def send_expiry_notices(self):
        credit_rec = self.env['extenss.credit'].search([('credit_status', '=', 'active'),('flag_early_settlement', '=', False)])
        for reg_cred in credit_rec:
            if reg_cred.ff:
                requests = self.env['crm.lead'].search([('id', '=', reg_cred.request_id.id)])
                for req in requests:
                    body_html = _('<p>Factoring company: %s ,</p><p>Assignor: %s ,</p>'
                        '<p>Assigned %s </p>') % (req.factoring_company.name, req.assignor.name, req.assigned.name)

                    mail_value = {
                        'subject': 'Financial Factoring Opening',
                        'body_html': body_html,
                        'email_to': req.email_from,
                        'email_from': 'odoo@odoo.com',
                        #'attachment_ids': [(6,0,[att.id])],
                    }
                    self.env['mail.mail'].sudo().create(mail_value).send()

            if reg_cred.ap or reg_cred.cs or reg_cred.af or reg_cred.dn:
                date_name = datetime.now().date()
                dir_create = "Account_status"
                path_act = os.getcwd()
                path_archivo = path_act+"/"+dir_create+"/"+reg_cred.name+"/"+_("Bank Statement %s.pdf") % date_name
                date_rec_amort = 0
                now = datetime.now().date()
                new_date = now + timedelta(days=reg_cred.days_notice)

                records_amort = self.env['extenss.credit.amortization'].search([('credit_id', '=', reg_cred.id),('expiration_date', '=', new_date)])
                for reg_exp in records_amort:
                    date_rec_amort = reg_exp.expiration_date

                if new_date == date_rec_amort:
                    body_html = _('<p>No. Pago %s ,</p><p>Fecha de vencimiento %s ,</p>'
                            '<p>Saldo inicial %s ,</p><p>Capital %s ,</p><p>Interes %s ,'
                            '</p><p> Payment %s ,</p><p> IVA renta %s ,</p><p> Renta total %s </p>') % (reg_exp.no_pay, reg_exp.expiration_date, reg_exp.initial_balance, reg_exp.capital, 
                            reg_exp.interest, reg_exp.payment, reg_exp.iva_rent, reg_exp.total_rent)

                    files = sorted(glob.iglob(path_archivo), key=os.path.getctime, reverse=True)
                    print(files)
                    print(path_archivo)
                    with open(files[0], 'rb') as fd:
                        camt_file = base64.b64encode(fd.read())

                # content = self.env.ref('extenss_credit.report_extenss_credit_account_status').render_qweb_pdf(reg_cred.id)[0]########
                    #datas_f = base64.encodebytes(camt_file.getvalue().encode(encoding))
                    att = self.env['ir.attachment'].create({
                        'name': reg_cred.name and _("Bank Statement %s.pdf") % reg_cred.name or _("Bank Statement.pdf"),
                        'type': 'binary',
                        #'datas': base64.encodestring(camt_file),
                        'datas': camt_file,#base64.b64encode(camt_file),
                        'res_model': reg_cred._name,
                        'res_id': reg_cred.id
                    })

                    mail_value = {
                        'subject': 'PRUEBA',
                        'body_html': body_html,
                        'email_to': reg_cred.customer_id.email,
                        'email_from': 'odoo@odoo.com',
                        'attachment_ids': [(6,0,[att.id])],
                    }
                    self.env['mail.mail'].sudo().create(mail_value).send()

    def action_calculate_advance(self):
        out_balance = 0
        vat_capital = 0

        vat_credit = self.vat_factor
        penalty_percentage = self.penalty_adv
        int_mora = self.factor_rate
        base_type = self.calculation_base
        itr = self.interest_rate

        if base_type == '360/360':
            base = 360
        if base_type == '365/365' or base_type == '360/365':
            base = 365

        balance_initial = 0
        past_due_balance = 0
        interest_mora = 0
        interest_mora_tmp = 0
        pay_num = 0
        vat_capital = 0
        amount_penalty = 0
        vat_poa = 0
        vat_interest_mora = 0
        days = 0
        interest_due = 0
        interest_mora_sum = 0
        settle_total = 0
        sum_total = 0

        if not self.advance_date:
            raise ValidationError(_('Enter the Date for calculation'))

        if not self.amount_req:
            raise ValidationError(_('Enter the amount, for calculation'))

        if not self.advan_type:
            raise ValidationError(_('Enter the type, for calculation'))

        if self.ap or self.af:
            if self.penalty_adv == 0:
                raise ValidationError(_('Enter the penalty percentage, is required for the type of credit'))

        notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('req_credit_id', '=', False)])
        for notice in notices:
            if notice.total_to_pay > 0:
                raise ValidationError(_('The credit must be current'))

        #Buscar el ultimo aviso creado
        records = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('req_credit_id', '=', False)])
        pay_num = 0
        for rec_notice in records:
            pay_num = rec_notice.payment_number

        num_pay_new = pay_num + 1
        #se obtiene los datos de la tabla de amortizacion
        reg_due = self.env['extenss.credit.amortization'].search([('no_pay', '=', num_pay_new),('credit_id', '=', self.id)])
        for rec in reg_due:
            days = self.days_between(rec.expiration_date, self.advance_date)
            outstanding_balance = rec.initial_balance

        int_tmp = round(outstanding_balance * ((itr/100)/base) * days,2)
        int_vat = round(int_tmp * (vat_credit/100),2)

        amount_advance = round(((self.amount_req - int_tmp) / 1.17),2)

        if self.cs or self.dn or self.ff:
            cap_vat = 0
        else:
            #cap_vat = outstanding_balance * (vat_credit/100)
            cap_vat = round(amount_advance * (vat_credit/100),2)

        amount_penalty = round(amount_advance * (penalty_percentage/100),2)
        total_req = self.amount_req - amount_penalty - int_tmp - int_vat - cap_vat

        self.interests_adv = round(int_tmp,2)
        self.capital_vat_adv = round(cap_vat,2)
        self.interests_vat_adv = round(int_vat,2)
        self.days_interest_adv = round(days,2)
        self.penalty_amount_adv = round(amount_penalty,2)
        self.total_advance_adv = round(total_req,2)
        #self.total_settle = round(total_req,2)
        self.balance_initial_adv = outstanding_balance

    def recalculate_amortization_table(self, credit_id, id_notice, type_req):
        # cred_s = self.env['extenss.credit'].search([('id', '=', credit_id)])
        # for cred in cred_s:
        #notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id.id', '=', credit_id),('req_credit_id', '=', req_id)])
        notices = self.env['extenss.credit.expiry_notices'].search([('id', '=', id_notice)])
        for notice in notices:
            date_create_amort = notice.due_not_date
            pen_req = self.penalty_amount_adv
            new_pay_num  = notice.payment_number + 1
            new_pay_num2 = notice.payment_number
            type_record = notice.type_rec
            
            # requests = self.env['extenss.credit.request'].search([('id', '=', req_id)])
            # for req in requests:
            #     int_req = req.interests
            #     cap_vat_req = req.capital_vat
            #     vat_int_req = req.interests_vat
            #     
            #     total_req = req.total_advance

            capital_req = 0
            interest_req = 0
            int_vat_req = 0
            iva_capital_req = 0
            int_vat_ap = 0
            iva_capital_ap = 0
            payment_req = 0
            capital_ap = 0
            interest_ap = 0
            payment_req = 0
            iva_rent_req = 0
            concepts = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id', '=', notice.id)])
            for concept in concepts:
                pay_req = notice.amount_not
                if self.cs == True or self.af == True or self.dn == True or self.ff == True:
                    if concept.concept == 'capital':
                        capital_req = concept.amount_concept
                    if concept.concept == 'interest':
                        interest_req = concept.amount_concept
                    if concept.concept == 'intvat':
                        int_vat_req = concept.amount_concept
                    total_rent_req = 0
                if self.af == True:
                    if concept.concept == 'capvat':
                        iva_capital_req = concept.amount_concept
                    pay_req = capital_req + interest_req
                    total_rent_req = pay_req + iva_capital_req

                if self.ap == True:
                    if concept.concept == 'payment':
                        capital_req = concept.amount_concept
                    if concept.concept == 'paymentvat':
                        iva_rent_req = concept.amount_concept
                    if concept.concept == 'intvat':
                        int_vat_req = concept.amount_concept
                    interest_req = self.interests_adv
                    pay_req = capital_req + interest_req
                    total_rent_req = iva_rent_req + pay_req

            reg_amort = self.env['extenss.credit.amortization'].search([('credit_id.id', '=', credit_id),('no_pay', '=', new_pay_num2)])
            for reg in reg_amort:
                new_balance_table = reg.initial_balance - capital_req
                credit_s = self.env['extenss.credit'].search([('id', '=', credit_id)])
                for credit in credit_s:
                    if type_req == 'term':
                        print("term")#liquidar las amotizaciones que alcancen y regenerar la tabla
                        di=credit.first_payment_date#credit.hiring_date#
                        df=credit.first_payment_date#credit.hiring_date
                        dfq=credit.first_payment_date#credit.hiring_date

                        if credit.calculation_base=='360/360':
                            if credit.af == True or credit.ap == True:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 360 )/(1+(credit.vat_factor/100))
                                else:
                                    dr=(credit.interest_rate / 360 )
                            else:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 360 )
                                else:
                                    dr=(credit.interest_rate / 360 ) * (1+(credit.vat_factor/100))
                            if credit.frequency_days == 30:
                                dm=30
                                rate=(dr/100*30)
                            if credit.frequency_days == 15:
                                dm=15
                                rate=(dr/100*15)
                            if credit.frequency_days == 7:
                                dm=7
                                rate=(dr/100*7)
                        if credit.calculation_base=='365/365':
                            if credit.af == True or credit.ap == True:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 365 )/(1+(credit.vat_factor/100))
                                else:
                                    dr=(credit.interest_rate / 365 )
                            else:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 365 )
                                else:
                                    dr=(credit.interest_rate / 365 ) * (1+(credit.vat_factor/100))
                            if credit.frequency_days == 30:
                                dm=calendar.monthrange(di.year,di.month)[1]
                                rate=(dr/100*30.5)
                            if credit.frequency_days == 15:
                                dm=15
                                rate=(dr/100*15.25)
                            if credit.frequency_days == 7:
                                dm=7
                                rate=(dr/100*7)

                        if credit.calculation_base=='360/365':
                            if credit.af == True or credit.ap == True:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 360 )/(1+(credit.vat_factor/100))
                                else:
                                    dr=(credit.interest_rate / 360 )
                            else:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 360 )
                                else:
                                    dr=(credit.interest_rate / 360 ) * (1+(credit.vat_factor/100))
                            if credit.frequency_days == 30:
                                dm=calendar.monthrange(di.year,di.month)[1]
                                rate=(dr/100*30.5)
                            if credit.frequency_days == 15:
                                dm=15
                                rate=(dr/100*15.25)
                            if credit.frequency_days == 7:
                                dm=7
                                rate=(dr/100*7)

                        if credit.af == True or credit.ap == True:
                            credit.amount_si_rcal=(credit.amount_financed/(1+(credit.vat_factor/100)))
                            ra=(credit.amount_si)
                            credit.purchase_option_amount_rcal=(credit.purchase_option/100*ra)
                            if credit.ap == True:
                                credit.residual_value_rcal=(ra*credit.residual_value/100)
                            if credit.af == True:
                                credit.iva=(ra*credit.vat_factor/100)
                                credit.total_guarantee_deposit=(ra*credit.percentage_guarantee_deposit/100)
                            credit.iva_purchase_rcal=(credit.purchase_option_amount*(credit.vat_factor/100))
                            credit.total_purchase_rcal=(credit.purchase_option_amount+credit.iva_purchase_rcal)
                            # quotation.total_commision=0
                            # for com in quotation.commision_ids:
                            #     quotation.total_commision=(quotation.total_commision+(com.value_commision))
                            if credit.af == True:
                                pay=((ra*(rate)*pow((1+(rate)),credit.term))-(0*(rate)))/(pow(1+(rate),credit.term)-1)
                            if credit.ap == True:
                                pay=((ra*(rate)*pow((1+(rate)),credit.term))-(credit.residual_value_rcal*(rate)))/(pow(1+(rate),credit.term)-1)
                        else:
                            ra=credit.amount_financed
                            pay=credit.amount_financed/((1-(1/pow((1+(rate)),credit.term)))/(rate))

                        if type_record == 'ADV_REC':
                            new_pay_num = new_pay_num2#####
                            new_pay_num2 = 0 #####

                        for amort in credit.amortization_ids:
                            if amort.no_pay > new_pay_num2:
                                id_amort = amort.id
                                amortization_ids = [(2, id_amort, 0)]
                                credit.amortization_ids = amortization_ids
                            else:
                                ra=amort.initial_balance-amort.capital

                        if type_record == 'ADV_REC':
                            new_pay_num2 = new_pay_num2 + 1

                        amortization_ids = [(4, 0, 0)]
                        data = {
                            'no_pay': new_pay_num2,
                            'expiration_date': date_create_amort,
                            'initial_balance': ra,
                            'capital': capital_req,#19854.12,
                            'interest': interest_req,#126.85,
                            'iva_interest': int_vat_req,#19.03,
                            'payment': pay_req,
                            'iva_rent': iva_rent_req,
                            'total_rent': total_rent_req,####preguntar
                            'iva_capital': iva_capital_req,
                            'penalty_amount': pen_req,
                        }
                        amortization_ids.append((0, 0, data))
                        credit.update({
                            'amortization_ids': amortization_ids
                        })
                        #new_pay_num2 = new_pay_num#####
                        ra=ra-capital_req
                        #print('df',df)
                        #dfq = False
                        for i in range(credit.term):
                            print('df',df)
                            print('i',i)
                            if i+1 > new_pay_num2:
                                if credit.frequency_days == 30:
                                    df = df + relativedelta(months=1)
                                if credit.frequency_days == 15:
                                    # if i%2 == 0:
                                    #     print('dfq',dfq)
                                    #     print('df',df)
                                    #     print('i',i)
                                    #     df = df + relativedelta(days=15)
                                    #     dfq=df
                                    # else:
                                    #     if not dfq:
                                    #         print('dfq',dfq)
                                    #         print('df',df) 
                                    #         print('i',i)
                                    #         dfq=df
                                    #         print('df else',df)
                                    #     else:
                                    #         print('dfq',dfq)
                                    #         print('df',df)
                                    #         print('i',i)
                                    #         df=dfq + relativedelta(months=1)
                                    #         print('df',df)
                                    if i%2 == 0:
                                        print("entra en el if")
                                        print("i",i)
                                        print("df",df)
                                        print("dfq",dfq)
                                        dfq = df
                                        df = df + relativedelta(days=15)
                                        print("df",df)
                                        print("dfq",df)
                                    else:
                                        print("entra al else")
                                        print("i",i)
                                        print("dfq",dfq)
                                        print("df",df)
                                        df = dfq + relativedelta(months=1)
                                        print("df",df)
                                        print("dfq",df)
                                if credit.frequency_days == 7:
                                    df = df + relativedelta(days=7)

                                if credit.calculation_base=='365/365' or credit.calculation_base=='360/365':
                                    if credit.frequency_days == 30:
                                        dm=calendar.monthrange(df.year,df.month)[1]
                                    if credit.frequency_days == 15:
                                        if i%2 == 0:
                                            dm=15
                                        else:
                                            dm=(calendar.monthrange(df.year,df.month)[1]-15)

                                if credit.af == True or credit.ap == True:
                                    interest=round(((ra*dr*dm)/100),2)
                                else:
                                    ici=round(((ra*dr*dm)/100),2)
                                    interest=ici/(1+(credit.vat_factor/100))
                                ivainterest=interest*(credit.vat_factor/100)
                                if i == (credit.term-1):
                                    capital = 0
                                    interest = 0
                                    ivainterest = 0
                                    pay = 0
                                    ivarent = 0
                                    totalrent = 0
                                    ivacapital = 0
                                else:
                                    if pay >= ra:
                                        if credit.ap == True:
                                            pay=round(pay,2)
                                        else:
                                            if credit.af == True:
                                                pay=round(ra+interest,2)
                                            else:
                                                pay=round(ra+ici,2)
                                    else:
                                        pay=round(pay,2)

                                if credit.af == True or credit.ap == True:
                                    capital=round((pay-(interest)),2)
                                else:
                                    capital=round((pay-ici),2)

                                ivacapital=(capital*(credit.vat_factor/100))
                                fb=round((ra-capital),2)
                                totalrent=0
                                ivarent=0
                                if credit.af == True:
                                    totalrent=round((pay+ivainterest+ivacapital),2)
                                    totalrent=round(totalrent,2)
                                if credit.ap == True:
                                    ivarent=round((pay*(credit.vat_factor/100)),2)
                                    totalrent=round((pay+ivarent),2)
                                    totalrent=round(totalrent,2)

                                rv = credit.amount_residual_value
                                if fb <= rv and credit.ap == True:
                                    capital = ra-rv
                                    interest=round(((capital*dr*dm)/100),2)
                                    pay=round(interest+capital,2)
                                    ivainterest=interest*(credit.vat_factor/100)
                                    ivarent=round((pay*(credit.vat_factor/100)),2)
                                    totalrent=round((pay+ivarent),2)
                                    ivacapital=(capital*(credit.vat_factor/100))
                                    fb=0

                                if ra == 0:
                                    capital = 0
                                    interest = 0
                                    ivainterest = 0
                                    pay = 0
                                    ivarent = 0
                                    totalrent = 0
                                    ivacapital = 0

                                amortization_ids = [(4, 0, 0)]
                                data = {
                                    'no_pay': (i+1),
                                    'expiration_date': df,
                                    'initial_balance': ra,
                                    'capital': capital,
                                    'interest': interest,
                                    'iva_interest': ivainterest,
                                    'payment': pay,
                                    'iva_rent': ivarent,
                                    'total_rent': totalrent,
                                    'iva_capital': ivacapital
                                }
                                print('data',data)
                                amortization_ids.append((0, 0, data))

                                credit.update({
                                    'amortization_ids': amortization_ids
                                })

                                ra=fb
                                di=df
                                self.date_limit_pay=df
    ############################ AMOUNT############
                    if type_req == 'amount':
                        print("amount")#restar el monto que se coloco en al solicitud y regenerar la tabla
                        di=credit.first_payment_date#hiring_date
                        df=credit.first_payment_date#hiring_date
                        dfq=credit.first_payment_date#hiring_date

                        if credit.calculation_base=='360/360':
                            if credit.af == True or credit.ap == True:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 360 )/(1+(credit.vat_factor/100))
                                else:
                                    dr=(credit.interest_rate / 360 )
                            else:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 360 )
                                else:
                                    dr=(credit.interest_rate / 360 ) * (1+(credit.vat_factor/100))
                            if credit.frequency_days == 30:
                                dm=30
                                rate=(dr/100*30)
                            if credit.frequency_days == 15:
                                dm=15
                                rate=(dr/100*15)
                            if credit.frequency_days == 7:
                                dm=7
                                rate=(dr/100*7)
                        if credit.calculation_base=='365/365':
                            if credit.af == True or credit.ap == True:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 365 )/(1+(credit.vat_factor/100))
                                else:
                                    dr=(credit.interest_rate / 365 )
                            else:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 365 )
                                else:
                                    dr=(credit.interest_rate / 365 ) * (1+(credit.vat_factor/100))
                            if credit.frequency_days == 30:
                                dm=calendar.monthrange(di.year,di.month)[1]
                                rate=(dr/100*30.5)
                            if credit.frequency_days == 15:
                                dm=15
                                rate=(dr/100*15.25)
                            if credit.frequency_days == 7:
                                dm=7
                                rate=(dr/100*7)
                            
                        if credit.calculation_base=='360/365':
                            if credit.af == True or credit.ap == True:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 360 )/(1+(credit.vat_factor/100))
                                else:
                                    dr=(credit.interest_rate / 360 )
                            else:
                                if credit.include_taxes:
                                    dr=(credit.interest_rate / 360 )
                                else:
                                    dr=(credit.interest_rate / 360 ) * (1+(credit.vat_factor/100))
                            if credit.frequency_days == 30:
                                dm=calendar.monthrange(di.year,di.month)[1]
                                rate=(dr/100*30.5)
                            if credit.frequency_days == 15:
                                dm=15
                                rate=(dr/100*15.25)
                            if credit.frequency_days == 7:
                                dm=7
                                rate=(dr/100*7)

                        if credit.af == True or credit.ap == True:
                            credit.amount_si=(credit.amount_financed/(1+(credit.vat_factor/100)))
                            ra=(credit.amount_si)
                            credit.purchase_option_amount=(credit.purchase_option/100*ra)
                            if credit.ap == True:
                                credit.residual_value_rcal=(ra*credit.residual_value/100)
                            if credit.af:
                                credit.iva=(ra*credit.vat_factor/100)
                                credit.total_guarantee_deposit=(ra*credit.percentage_guarantee_deposit/100)
                            credit.iva_purchase_rcal=(credit.purchase_option_amount*(credit.vat_factor/100))
                            credit.total_purchase_rcal=(credit.purchase_option_amount+credit.iva_purchase_rcal)
                            # credit.total_commision=0
                            # for com in credit.commision_ids:
                            #     credit.total_commision=(credit.total_commision+(com.value_commision))
                            if credit.af == True:
                                pay=((ra*(rate)*pow((1+(rate)),credit.term))-(0*(rate)))/(pow(1+(rate),credit.term)-1)
                            if credit.ap == True:
                                pay=((ra*(rate)*pow((1+(rate)),credit.term))-(credit.residual_value*(rate)))/(pow(1+(rate),credit.term)-1)
                        else:
                            #ra=new_balance_table
                            pay=new_balance_table/((1-(1/pow((1+(rate)),credit.term-new_pay_num2)))/(rate))
                            #pay=new_balance_table/((1-(1/pow((1+(rate)),credit.term)))/(rate))

                        for amort in credit.amortization_ids:
                            if amort.no_pay > new_pay_num2:
                                id_amort = amort.id
                                amortization_ids = [(2, id_amort, 0)]
                                credit.amortization_ids = amortization_ids
                            else:
                                if type_record == 'ADV_REC':#####
                                    ra=credit.amount_financed
                                else:
                                    ra=amort.initial_balance-amort.capital

                        amortization_ids = [(4, 0, 0)]
                        data = {
                            'no_pay': new_pay_num2,
                            'expiration_date': date_create_amort,#df,
                            'initial_balance': ra,
                            'capital': capital_req,#19854.12,
                            'interest': interest_req,#126.85,
                            'iva_interest': int_vat_req,#19.03,
                            'payment': pay_req,
                            'iva_rent': iva_rent_req,
                            'total_rent': total_rent_req,####preguntar
                            'iva_capital': iva_capital_req,
                            'penalty_amount': pen_req,
                        }
                        print(data)
                        if type_record == 'ADV_REC':#####
                            amortization_ids.append((1, reg.id, data))
                        else:
                            amortization_ids.append((0, 0, data))
                        credit.update({
                            'amortization_ids': amortization_ids
                        })
                        ra=ra-capital_req
                        pay=ra/((1-(1/pow((1+(rate)),credit.term-new_pay_num2)))/(rate))
                        #pay=ra/((1-(1/pow((1+(rate)),credit.term)))/(rate))

                        if type_record == 'ADV_REC':
                            new_pay_num = new_pay_num2
                            new_pay_num2 = 0
                            flag_val = True

                        for i in range(credit.term):
                            if i+1 > new_pay_num2:
                                if i+1 == 1 and new_pay_num2 == 0:
                                    df=credit.first_payment_date
                                else:
                                    if credit.frequency_days == 30:
                                        df = df + relativedelta(months=1)
                                    if credit.frequency_days == 15:
                                        if i%2 == 0:
                                            print("entra al if")
                                            dfq=df
                                            print("dfq",dfq)
                                            df = df + relativedelta(days=15)
                                        else:
                                            print("else")
                                            print("dfq",dfq)
                                            df = dfq + relativedelta(months=1)
                                            print("df",df)

                                    if credit.frequency_days == 7:
                                        df = df + relativedelta(days=7)
                                print("df",df)
                                if credit.calculation_base=='365/365' or credit.calculation_base=='360/365':
                                    if credit.frequency_days == 30:
                                        dm=calendar.monthrange(df.year,df.month)[1]
                                    if credit.frequency_days == 15:
                                        if i%2 == 0:
                                            dm=15
                                        else:
                                            dm=(calendar.monthrange(df.year,df.month)[1]-15)

                                if credit.af == True or credit.ap == True:
                                    interest=round(((ra*dr*dm)/100),2)
                                else:
                                    ici=round(((ra*dr*dm)/100),2)
                                    interest=ici/(1+(credit.vat_factor/100))
                                ivainterest=interest*(credit.vat_factor/100)

                                if i == (credit.term-1):
                                    if credit.ap:
                                        pay=round(pay,2)
                                    else:
                                        if credit.af or credit.ap:
                                            pay=round(ra+interest,2)
                                        else:
                                            pay=round(ra+ici,2)
                                else:
                                    if pay >= ra:
                                        if credit.af == True or credit.ap == True:
                                            pay=round(ra+interest,2)
                                        else:
                                            pay=round(ra+ici,2)
                                    else:
                                        pay=round(pay,2)
                                if credit.af == True or credit.ap == True:
                                    capital=round((pay-(interest)),2)
                                else:
                                    capital=round((pay-ici),2)

                                ivacapital=(capital*(credit.vat_factor/100))
                                fb=round((ra-capital),2)
                                totalrent=0
                                ivarent=0
                                if credit.af == True: 
                                    totalrent=round((pay+ivainterest+ivacapital),2)
                                    totalrent=round(totalrent,2)
                                if credit.ap == True:
                                    ivarent=round((pay*(credit.vat_factor/100)),2)
                                    totalrent=round((pay+ivarent),2)
                                    totalrent=round(totalrent,2)

                                amortization_ids = [(4, 0, 0)]
                                data = {
                                    'no_pay': (i+1),
                                    'expiration_date': df,
                                    'initial_balance': ra,
                                    'capital': capital,
                                    'interest': interest,
                                    'iva_interest': ivainterest,
                                    'payment': pay,
                                    'iva_rent': ivarent,
                                    'total_rent': totalrent,
                                    'iva_capital': ivacapital
                                }
                                print(data)
                                amortization_ids.append((0, 0, data))
                                credit.update({
                                    'amortization_ids': amortization_ids
                                })

                                ra=fb
                                di=df 
                                self.date_limit_pay=df

                            if type_record == 'ADV_REC' and flag_val:
                                new_pay_num2 = new_pay_num
                                flag_val = False

    def generating_account_status(self):
        credit_s = self.env['extenss.credit'].search([('credit_status', '=', 'active')])
        for credit in credit_s:
            print(credit.name)
            dir_create = "Account_status"
            path_act = os.getcwd()
            path_principal = path_act+"/"+dir_create
            path_archivo = path_act+"/"+dir_create+"/"+credit.name

            if not os.path.exists(path_archivo):
                print('entra')
                os.makedirs(path_archivo,exist_ok=True)
                os.chdir(path_archivo)
                content = self.env.ref('extenss_credit.report_extenss_credit_account_status').render_qweb_pdf(credit.id)[0]
                file_pdf = base64.b64encode(content)
                date_name = datetime.now().date()
                with open(date_name and _("Bank Statement %s.pdf") % (date_name) or _("Bank Statement.pdf"), 'wb') as f:
                    f.write(base64.b64decode(file_pdf))
                os.chdir(path_act)
            else:
                os.chdir(path_archivo)
                content = self.env.ref('extenss_credit.report_extenss_credit_account_status').render_qweb_pdf(credit.id)[0]
                file_pdf = base64.b64encode(content)
                date_name = datetime.now().date()
                with open(date_name and _("Bank Statement %s.pdf") % (date_name) or _("Bank Statement.pdf"), 'wb') as f:
                    f.write(base64.b64decode(file_pdf))
                os.chdir(path_act)

    def copy_amortization_table(self):
        self.portfolio_type = 'restructuring'
        restructure = self.env['extenss.credit.restructuring_table']
        amortization = self.env['extenss.credit.amortization'].search([('credit_id', '=', self.id)])
        for amort in amortization:
                restructure.create({
                    'credit_id': self.id,
                    'no_pay': amort.no_pay,
                    'expiration_date': amort.expiration_date,
                    'initial_balance': amort.initial_balance,
                    'capital': amort.capital,
                    'interest': amort.interest,
                    'iva_interest': amort.iva_interest,
                    'payment': amort.payment, 
                    'iva_capital': amort.iva_capital,
                    'total_rent': amort.total_rent,
                    'iva_rent': amort.iva_rent
                })

    def action_apply_payment(self):
        #self.apply_mov_pay()
        list_concepts = []
        for reg in self.conciliation_credit_ids:
            if reg.check == False and reg.status == 'pending' and reg.customer == self.customer_id:
                print(self.bill_id.id)
                self.env['extenss.credit.accounting_payments'].action_apply_movement(self.bill_id.id, 'abono', reg.amount,'')
                print(reg.id)
                print(reg.customer.id)
                print(reg.amount)
                print(reg.status)
                print(self.product_id.id)
                reg.status = 'applied'
                reg.check = True
        exp_notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('total_to_pay', '>', 0)])
        for exp_notice in exp_notices:
            print(exp_notice.total_to_pay)
            print(exp_notice.id)
            self.env['extenss.credit.conciliation'].apply_payment(exp_notice.id, self.payment_date)
        #self.conf_datamart('pay_notice')
        regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'pay_notice')])
        if regs_conf:
            for reg_conf in regs_conf:
                print(reg.id)
                for reg_events in reg_conf.event_id:
                    event_key = reg_events.event_key
                    print(event_key)

                    #for lines in self.conciliation_lines_ids:
                    list_concepts.append(reg.customer.id)
                    list_concepts.append(reg.amount) 
                    list_concepts.append(self.product_id.id)
                    list_concepts.append(event_key) #)
                    print(list_concepts)
                    self.env['extenss.credit'].create_records(list_concepts)
                    list_concepts = []
        else:
            raise ValidationError(_('Not exist record in Configuration in Datamart'))

    def create_notice_expiry(self, num_pay, credit_id, amount, list_concepts, id_req, due_not_date, initial_balance, factor_rate, type_record):
        rec_en = self.env['extenss.credit.expiry_notices']
        rec_cp = self.env['extenss.credit.concepts_expiration']
        id_expiry = rec_en.create({
            'credit_expiry_id': credit_id,
            'payment_number': num_pay,
            'due_not_date': due_not_date,
            'amount_not': amount,
            'total_paid_not': 0,
            'total_to_pay': 0,
            'req_credit_id': id_req,
            'outstanding_balance': initial_balance,
            'rate_moratorium': factor_rate,
            'type_rec': type_record,
        })
        rec_notice = rec_en.search([('payment_number', '=', num_pay),('credit_expiry_id', '=', credit_id)])
        for r_notice in rec_notice:
            r_notice.id
        for rec in list_concepts:
            a=0
            b=1
            rec[a]
            rec[b]
            rec_cp.create({
                'expiry_notice_id': r_notice.id,
                'concept': rec[a],
                'amount_concept': rec[b],
                'total_paid_concept': 0,
                'full_paid': False,
            })
            a += 1
            b += 1
        return id_expiry

    def action_pay_advance(self):
        _logger.info('Inicia el proceso de action_pay_advance')
        list_concepts = []
        reg = ''
        if self.total_advance_adv == 0:
            raise ValidationError(_('Calculations are missing'))

        for reg in self.conciliation_credit_ids:
            if reg.check == False and reg.status == 'pending' and reg.customer == self.customer_id:
                id_expiry = self.action_create_advance()
                _logger.info('id_expiry', id_expiry)
                self.env['extenss.credit.accounting_payments'].action_apply_movement(self.bill_id.id, 'abono', reg.amount,'')
                _logger.info('Despues de action_apply_movement')
                _logger.info('id_expiry.id', id_expiry.id)
                _logger.info('self.advance_date', self.advance_date)
                self.env['extenss.credit.conciliation'].apply_payment(id_expiry.id, self.advance_date)
                _logger.info('Despues de apply_payment')
                self.recalculate_amortization_table(self.id, id_expiry.id, self.advan_type)
                _logger.info('Despues de recalculate_amortization_table')
                reg.status = 'applied'
                reg.check = True
            #else:
                #raise ValidationError(_('Data is incorrect, amount or customer'))

        if reg != '':
            regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'pay_notice')])
            if regs_conf:
                for reg_conf in regs_conf:
                    for reg_events in reg_conf.event_id:
                        _logger.info('reg_events')
                        event_key = reg_events.event_key
                        list_concepts.append(reg.customer.id)
                        list_concepts.append(reg.amount) 
                        list_concepts.append(self.product_id.id)
                        list_concepts.append(event_key)
                        self.env['extenss.credit'].create_records(list_concepts)
                        list_concepts = []
            else:
                raise ValidationError(_('Not exist record in Configuration in Datamart'))
        else:
            raise ValidationError(_('Selects a record with the correct data, amount or client'))

    def create_records(self, list_data):
        today = datetime.now().date()
        #for lines in self.conciliation_lines_ids:
        ext_dats = self.env['extenss.datamart'].search([('date', '=', today)])
        if ext_dats:
            for ext_dat in ext_dats:
                self.env['extenss.datamart.lines'].create({
                    'datamart_id': ext_dat.id,
                    #'account_id': 2,
                    'partner_id': list_data[0],#lines.customer.id,
                    'description': 'Datamart',
                    'amount': list_data[1],#lines.amount,
                    'product_id': list_data[2],#self.productid.id,
                    'type_line': list_data[3],#'700',
                })
        else:
            id_exdat =  self.env['extenss.datamart'].create({
                'date': datetime.now().date(),
                'name': datetime.now().date(),
            })
            self.env['extenss.datamart.lines'].create({
                'datamart_id': id_exdat.id,
                #'account_id': 2,
                'partner_id': list_data[0],#lines.customer.id,
                'description': 'Datamart',
                'amount': list_data[1],#lines.amount,
                'product_id': list_data[2],#self.productid.id,
                'type_line': list_data[3],#'700',
            })

    def action_create_advance(self):
        amount = 0.0
        list_concepts = []
        type_rec = ''
        num_rec  = self.env['extenss.credit.expiry_notices'].search_count([('credit_expiry_id', '=', self.id)])

        if num_rec == 0:
            num_rec = 1
            type_rec = 'ADV_REC'

        if self.cs or self.af or self.dn or self.ff:
            if self.total_advance_adv > 0:
                list_concepts.append(['capital', self.total_advance_adv])#self.total_settle
        if self.af:
            if self.capital_vat_adv > 0:
                list_concepts.append(['capvat', self.capital_vat_adv])
            amount += round(self.capital_vat_adv,2)
        if self.cs or self.af or self.dn or self.ff:
            if self.interests_adv > 0:
                list_concepts.append(['interest', self.interests_adv])
            if self.interests_vat_adv > 0:
                list_concepts.append(['intvat', self.interests_vat_adv])
            if self.penalty_amount_adv > 0:
                list_concepts.append(['penalty_amount', self.penalty_amount_adv])
            amount = round(self.total_advance_adv + self.interests_adv + self.interests_vat_adv + self.penalty_amount_adv,2)

        if self.ap:
            payment = self.total_advance_adv + self.interests_adv
            vat_payment = self.interests_vat_adv + self.capital_vat_adv
            list_concepts.append(['payment', payment])
            list_concepts.append(['paymentvat', vat_payment])
            if self.penalty_amount_adv > 0:
                list_concepts.append(['penalty_amount', self.penalty_amount_adv])
            amount = round(payment + vat_payment + self.penalty_amount_adv,2)

        id_expiry = self.create_notice_expiry(num_rec, self.id, amount, list_concepts, self.id, self.advance_date, self.balance_initial_adv, self.factor_rate, type_rec)
        return id_expiry

class ExtenssCreditExpiryNotices(models.Model):
    _name = 'extenss.credit.expiry_notices'
    _description = 'Expiry Notices'

    credit_expiry_id = fields.Many2one('extenss.credit', ondelete='cascade', tracking=True, translate=True)
    payment_number = fields.Integer(string='Payment number', tracking=True, translate=True)
    expiry_number = fields.Char(string='Expiry notice number', copy=False, readonly=True, index=True, tracking=True, translate=True, default=lambda self: _('New'))
    due_not_date = fields.Date(string='Due notice date', tracking=True, translate=True)
    amount_not = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    total_paid_not = fields.Monetary(string='Total paid', compute='_compute_total_paid_not', store=True, currency_field='company_currency', tracking=True, translate=True)
    total_to_pay = fields.Monetary(string='Total to pay', currency_field='company_currency', compute='_compute_total_to_pay', store=True, tracking=True, translate=True)
    payment_date = fields.Date(string='Payment date notice', tracking=True, translate=True)
    req_credit_id = fields.Char(string='Id Request')
    type_rec = fields.Char(string='Type Rec')

    ###### Moras #######
    outstanding_balance = fields.Monetary(string='Outstanding balance', currency_field='company_currency', tracking=True, translate=True)
    start_date_mora = fields.Date(string='Start date mora', tracking=True, translate=True)
    date_payment = fields.Date(string='Date payment moras', tracking=True, translate=True)
    #base_amount = fields.Monetary(string='Base amount', currency_field='company_currency', tracking=True, translate=True)
    rate_moratorium = fields.Float('Rate moratorium', (2,2), tracking=True, translate=True)
    days_mora = fields.Char(string='Days mora', tracking=True, translate=True)
    resp_days_mora = fields.Char(string='Resp Days mora', tracking=True, translate=True)
    interest_moratoriums = fields.Float('Interest moratoriums', (2,2), tracking=True, translate=True)
    vat_interest_mora = fields.Float('Vat interest moratoriums', (2,2), tracking=True, translate=True)
    total_interest_mora = fields.Monetary(string='Total interest mora', compute='_compute_total_int_mora', currency_field='company_currency', tracking=True, translate=True)
    #total_payment = fields.Monetary(string='Total payment', currency_field='company_currency', tracking=True, translate=True)
    to_pay = fields.Monetary(string='To pay', compute='_compute_to_pay', currency_field='company_currency', tracking=True, translate=True)
    #rent = fields.Monetary(string='Rent', currency_field='company_currency', tracking=True, translate=True)
    total_rent = fields.Monetary(string='Total rent', currency_field='company_currency', tracking=True, translate=True)
    total_paid_moras = fields.Monetary(string='Total paid moras', compute='_compute_total_moras', store=True, currency_field='company_currency', tracking=True, translate=True)
    
    ####### Condonacion #######
    balance_interest_mora = fields.Monetary(string='Balance interest moratoriums', currency_field='company_currency', tracking=True, translate=True)
    amount_condonation = fields.Monetary(string='Amount condonation', currency_field='company_currency', tracking=True, translate=True)

    #####
    sum_con_capital = fields.Monetary(string='sum capital', currency_field='company_currency', compute='_compute_amount_con_capital', store=True, tracking=True, translate=True)
    sum_con_interest = fields.Monetary(string='sum interest', currency_field='company_currency', compute='_compute_amount_con_interest', store=True, tracking=True, translate=True)
    sum_con_capvat = fields.Monetary(string='sum capvat', currency_field='company_currency', compute='_compute_amount_con_capvat', store=True, tracking=True, translate=True)
    sum_con_intvat = fields.Monetary(string='sum intvat', currency_field='company_currency', compute='_compute_amount_con_intvat', store=True, tracking=True, translate=True)
    #####

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    @api.model
    def create(self, reg):
        if reg:
            if reg.get('expiry_number', _('New')) == _('New'):
                reg['expiry_number'] = self.env['ir.sequence'].next_by_code('extenss.credit.expiry_notices') or _('New')
            result = super(ExtenssCreditExpiryNotices, self).create(reg)
            return result

    @api.depends('amount_not','total_paid_not')
    def _compute_total_to_pay(self):
        for reg in self:
            reg.total_to_pay = reg.amount_not - reg.total_paid_not
            if reg.total_to_pay < 0 or reg.total_to_pay < .06 :
                reg.total_to_pay = 0

    @api.depends('expiry_notice_ids','expiry_notice_ids.total_paid_concept')
    def _compute_total_paid_not(self):
        for reg in self:
            reg.total_paid_not = sum([line.total_paid_concept for line in reg.expiry_notice_ids])#if line.concept != 'morint' and line.concept != 'morintvat' ##OQJ 09032021 - Se quita esta parte del codigo para que cuadren los montos

    @api.depends('expiry_notice_ids','expiry_notice_ids.total_paid_concept','expiry_notice_ids.amount_concept')
    def _compute_total_moras(self):
        for reg in self:
            reg.total_paid_moras = sum([line.total_paid_concept for line in reg.expiry_notice_ids if line.concept == 'morint' or line.concept == 'morintvat' or line.concept == 'condonation'])
            #reg.balance_interest_mora = sum([line.total_paid_concept for line in reg.expiry_notice_ids if line.concept == 'morint' or line.concept == 'morintvat' or line.concept == 'condonation'])

    @api.depends('interest_moratoriums','vat_interest_mora')
    def _compute_total_int_mora(self):
        for reg in self:
            reg.total_interest_mora = reg.interest_moratoriums + reg.vat_interest_mora
            reg.total_rent = reg.total_interest_mora + reg.amount_not
    
    @api.depends('total_paid_moras','total_interest_mora')
    def _compute_to_pay(self):
        for reg in self:
            reg.to_pay = reg.total_interest_mora - reg.total_paid_moras
            reg.balance_interest_mora = reg.total_interest_mora - reg.total_paid_moras

    ###############
    @api.depends('expiry_notice_ids','expiry_notice_ids.total_paid_concept','expiry_notice_ids.amount_concept')
    def _compute_amount_con_capital(self):
        for reg in self:
            reg.sum_con_capital = sum([line.total_paid_concept for line in reg.expiry_notice_ids if line.concept == 'capital'])

    @api.depends('expiry_notice_ids','expiry_notice_ids.total_paid_concept','expiry_notice_ids.amount_concept')
    def _compute_amount_con_interest(self):
        for reg in self:
            reg.sum_con_interest = sum([line.total_paid_concept for line in reg.expiry_notice_ids if line.concept == 'interest'])

    @api.depends('expiry_notice_ids','expiry_notice_ids.total_paid_concept','expiry_notice_ids.amount_concept')
    def _compute_amount_con_capvat(self):
        for reg in self:
            reg.sum_con_capvat = sum([line.total_paid_concept for line in reg.expiry_notice_ids if line.concept == 'capvat'])

    @api.depends('expiry_notice_ids','expiry_notice_ids.total_paid_concept','expiry_notice_ids.amount_concept')
    def _compute_amount_con_intvat(self):
        for reg in self:
            reg.sum_con_intvat = sum([line.total_paid_concept for line in reg.expiry_notice_ids if line.concept == 'intvat'])
    ###############

    def automatic_generating_moras(self):
        print('print automatic_generating_moras')
        # creds = self.env['extenss.credit'].browse(env.context['active_id'])
        expirys = self.env['extenss.credit.expiry_notices'].search([('id', '=', self.id)])
        for expiry in expirys:
            print('expiry.credit_expiry_id', expiry.credit_expiry_id)
            #reg.resp_days_mora = reg.days_mora 

            creds =self.env['extenss.credit'].search([('id', '=', expiry.credit_expiry_id.id)])
            for cred in creds:
                rate_mora = cred.factor_rate
                vat_credit = cred.vat_factor
                int_fact_mora = cred.factor_rate
                base_type = cred.calculation_base
                itr = cred.interest_rate
                print('rate_mora', rate_mora)
                print('vat_credit', vat_credit)
                print('int_fact_mora', int_fact_mora)
                print('base_type', base_type)
                print('itr', itr)
                print('cred.id',cred.id)
                if base_type == '360/360':
                    base = 360
                if base_type == '365/365' or base_type == '360/365':
                    base = 365

                if expiry.date_payment:
                    days_mora = (expiry.date_payment - expiry.due_not_date).days
                else:
                    #days_mora = (date_act - reg.due_not_date).days
                    days_mora = 0#(expiry.start_date_mora - expiry.due_not_date).days

                int_mora = expiry.outstanding_balance * ((int_fact_mora/100)/base) * days_mora
                vat_int_mora = vat_interest_mora = (vat_credit/100) * int_mora
                
                expiry.interest_moratoriums = int_mora
                expiry.vat_interest_mora = vat_int_mora
                expiry.rate_moratorium = rate_mora
                expiry.days_mora = days_mora
                expiry.total_interest_mora = int_mora + vat_int_mora
                #expiry.balance_interest_mora = int_mora + vat_int_mora

    expiry_notice_ids = fields.One2many('extenss.credit.concepts_expiration', 'expiry_notice_id', string=' ', tracking=True)

class ExtenssCreditConceptsExpiration(models.Model):
    _name = 'extenss.credit.concepts_expiration'
    _description = 'Concepts Expiration Notices'

    expiry_notice_id = fields.Many2one('extenss.credit.expiry_notices', ondelete='cascade', tracking=True, translate=True)
    concept = fields.Selection(CONCEPTS, string='Concept', tracking=True, group_operator=True, translate=True)
    #expiry_num = fields.Char(string='Expiry Notice Number', copy=False, readonly=True, index=True, tracking=True, translate=True, default=lambda self: _('New'))
    amount_concept = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    total_paid_concept = fields.Monetary(string='Total paid', compute='_compute_total_paid', store=True, currency_field='company_currency', tracking=True, translate=True)
    full_paid = fields.Boolean(string='Full payment', default=False, tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    @api.depends('concept_pay_ids','concept_pay_ids.total_paid_cp')
    def _compute_total_paid(self):
        for reg in self:
            reg.total_paid_concept = sum([line.total_paid_cp for line in reg.concept_pay_ids])
            # reg.total_paid_concept = sum(reg.concept_pay_ids.mapped('total_paid_cp'))
            if round(reg.amount_concept,2) == round(reg.total_paid_concept,2):
                reg.full_paid = True

    concept_pay_ids = fields.One2many('extenss.credit.concept_payments', 'concept_pay_id', string=' ', tracking=True)

class ExtenssCreditConceptPayments(models.Model):
    _name = 'extenss.credit.concept_payments'
    _description = 'Concept Payments'

    concept_pay_id = fields.Many2one('extenss.credit.concepts_expiration', ondelete='cascade', tracking=True, translate=True)
    concept_id = fields.Many2one('extenss.credit.expiry_notices', related='concept_pay_id.expiry_notice_id')
    expiry_number_en = fields.Char(string='Expiry notice number', related='concept_id.expiry_number')
    # expiry_not_number_cp = fields.Integer(string='Expiry notice number', tracking=True, translate=True)
    # concept_id_cp = fields.Char(string='Concept', tracking=True, translate=True)
    date_paid = fields.Date(string='Payment date', tracking=True, translate=True)
    total_paid_cp = fields.Monetary(string='Total paid', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class ExtenssCreditAccount(models.Model):
    _name = 'extenss.credit.account'
    _description = 'Account'

    name = fields.Char(string='Account', copy=False, readonly=True, index=True, tracking=True, translate=True, default=lambda self: _('New'))
    customer_id = fields.Many2one('res.partner', string='Customer', tracking=True, translate=True)
    date_opening = fields.Date(string='Account opening date', tracking=True, translate=True)
    status = fields.Selection([('active','Active'),('inactive','Inactive')], string='Status', tracking=True, translate=True) 
    balance = fields.Monetary(string='Balance', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    @api.model
    def create(self, reg):
        if reg:
            if reg.get('name', _('New')) == _('New'):
                reg['name'] = self.env['ir.sequence'].next_by_code('extenss.credit.account') or _('New')
            result = super(ExtenssCreditAccount, self).create(reg)
            return result
    
    accnt_mov_ids = fields.One2many('extenss.credit.movements', 'accnt_mov_id', string=' ', tracking=True)

class ExtenssCreditMovements(models.Model):
    _name = 'extenss.credit.movements'
    _description = 'Account Movements'
    _order = 'date_time_move desc'

    accnt_mov_id = fields.Many2one('extenss.credit.account', string='Account', tracking=True, translate=True)
    date_time_move = fields.Datetime(string='Movement date', tracking=True, translate=True)
    movement_type = fields.Selection([('cargo','Charge'),('abono','Credit')], string='Movement type', tracking=True, translate=True)
    amount = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    initial_balance = fields.Monetary(string='Initial balance', currency_field='company_currency', tracking=True, translate=True)
    ending_balance = fields.Monetary(string='Ending balance', currency_field='company_currency', tracking=True, translate=True)
    comments = fields.Text(string='Comments', tracking=True, translate=True)
    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class CreditsAmortization(models.Model):
    _name = 'extenss.credit.amortization'
    credit_id = fields.Many2one('extenss.credit')
    no_pay = fields.Integer('No Pay', translate=True)
    expiration_date = fields.Date('Expiration Date', translate=True)
    initial_balance = fields.Monetary('Initial Balance',currency_field='company_currency', tracking=True, translate=True)
    capital = fields.Monetary('Capital',currency_field='company_currency', tracking=True, translate=True)
    interest = fields.Monetary('Interest', currency_field='company_currency', tracking=True, translate=True)
    iva_interest = fields.Monetary('IVA Interest',currency_field='company_currency', tracking=True, translate=True)
    payment = fields.Monetary('Payment',currency_field='company_currency', tracking=True, translate=True)
    iva_capital = fields.Monetary('IVA Capital',currency_field='company_currency', tracking=True, translate=True)
    total_rent = fields.Monetary('Total Rent',currency_field='company_currency', tracking=True, translate=True)
    iva_rent = fields.Monetary('IVA Rent',currency_field='company_currency', tracking=True, translate=True)
    penalty_amount = fields.Monetary('Penalty amount', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class CreditsAmortizationMoras(models.Model):
    _name = 'extenss.credit.moras'
    credit_id = fields.Many2one('extenss.credit')
    init_date = fields.Date('Del')
    end_date = fields.Date('Al')
    days = fields.Integer('Days')
    past_due_balance = fields.Monetary('Past due balance',currency_field='company_currency', tracking=True, traslate=True)
    rate = fields.Float('Rate', (2,6), tracking=True, translate=True)
    interest = fields.Monetary('IVA Interest',currency_field='company_currency', tracking=True, translate=True)
    amount_to_payment = fields.Monetary('Payment',currency_field='company_currency', tracking=True, translate=True)
    
    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class CreditsRequest(models.Model):
    _name = 'extenss.credit.request'
    _description = 'Credit Request'

    @api.constrains('date_settlement')   
    def _check_date_settlement(self):
        for rec in self:
            if rec.type_request == 'early_settlement':
                if datetime.now().date() > rec.date_settlement:
                    raise ValidationError(_('Settlement date must be greater or equal than Today'))

    def action_confirm_request(self):
        list_concepts = []
        amount = 0
        if self.type_request == 'early_settlement':
            pay_rec = self.env['extenss.credit.expiry_notices'].search_count([('credit_expiry_id', '=', self.credit_request_id.id),('req_credit_id', '=', False)])
            num_rec = pay_rec + 1

            ec_id = self.env['extenss.credit'].browse(self.env.context.get('active_ids'))
            for rec in ec_id:
                factor_rate = rec.factor_rate
                id_accnt = rec.bill_id.id
                rec.flag_early_settlement = True
            if rec.cs or rec.af:
                if self.outstanding_balance > 0:
                    list_concepts.append(['capital', self.outstanding_balance])
            if rec.af:       
                if self.capital_vat > 0:
                    list_concepts.append(['capvat', self.capital_vat])
            if rec.cs or rec.af:
                if self.interests > 0:
                    list_concepts.append(['interest', self.interests])
            if rec.cs or rec.af:
                if self.interests_vat > 0:
                    list_concepts.append(['intvat', self.interests_vat])

            if rec.ap:
                payment = self.outstanding_balance + self.interests
                vat_payment = self.interests_vat + self.capital_vat
                list_concepts.append(['payment', payment])
                list_concepts.append(['paymentvat', vat_payment])
            
            if self.penalty_amount > 0:
                list_concepts.append(['penalty_amount', self.penalty_amount])
            if self.purchase_option > 0:
                list_concepts.append(['purchase_option', self.purchase_option])
            if self.vat_purchase_option > 0:
                list_concepts.append(['vat_option', self.vat_purchase_option])
            if self.interests_moratoriums > 0:
                list_concepts.append(['morint', self.interests_moratoriums])
            if self.vat_interest_mora > 0:
                list_concepts.append(['morintvat', self.vat_interest_mora])

            amount = self.security_deposit_balance + self.balance_income_deposit + self.total_settle - self.overdue_balance
            self.create_notice_expiry(num_rec, self.credit_request_id.id, amount, list_concepts, self.id,self.date_settlement, self.balance_inicial, factor_rate, '')

            # #realiza trasacciones a la cuenta eje
            if self.security_deposit_balance > 0:
                self.env['extenss.credit.accounting_payments'].action_apply_movement(id_accnt, 'abono', self.security_deposit_balance, 'Security Deposit Balance payment')
                rec.guarantee_dep_balance = 0 #09062020
            if self.balance_income_deposit > 0:
                self.env['extenss.credit.accounting_payments'].action_apply_movement(id_accnt, 'abono', self.balance_income_deposit, 'Balance Income on Deposit payment')
                rec.balance_income_deposit = 0 #09062020

        if self.type_request == 'atc':
            num_rec  = self.env['extenss.credit.expiry_notices'].search_count([('credit_expiry_id', '=', self.credit_request_id.id),('req_credit_id', '=', False)])

            ec_id = self.env['extenss.credit'].browse(self.env.context.get('active_ids'))
            for rec in ec_id:
                if rec.cs or rec.af:
                    if self.total_settle > 0:
                        list_concepts.append(['capital', self.total_settle])
                if rec.af:
                    if self.capital_vat > 0:
                        list_concepts.append(['capvat', self.capital_vat])
                    amount += round(self.capital_vat,2)
                if rec.cs or rec.af:
                    if self.interests > 0:
                        list_concepts.append(['interest', self.interests])
                    if self.interests_vat > 0:
                        list_concepts.append(['intvat', self.interests_vat])
                    if self.penalty_amount > 0:
                        list_concepts.append(['penalty_amount', self.penalty_amount])
                    amount = round(self.total_settle + self.interests + self.interests_vat + self.penalty_amount,2)

                if rec.ap:
                    payment = self.total_settle + self.interests
                    vat_payment = self.interests_vat + self.capital_vat
                    list_concepts.append(['payment', payment])
                    list_concepts.append(['paymentvat', vat_payment])
                    if self.penalty_amount > 0:
                        list_concepts.append(['penalty_amount', self.penalty_amount])
                    amount = round(payment + vat_payment + self.penalty_amount,2)

            self.create_notice_expiry(num_rec, self.credit_request_id.id, amount, list_concepts, self.id,self.advance_date, self.balance_inicial, rec.factor_rate, '')

        self.state = 'pending'

    def action_calculate_request(self):
        out_balance = 0
        vat_capital = 0
        credit_id = self.env['extenss.credit'].browse(self.env.context.get('active_ids'))
        rcs = self.env['extenss.credit'].search([('id', '=', credit_id.id)])
        for rc in rcs:
            vat_credit = rc.vat_factor
            penalty_percentage = self.penalty
            poa = rc.purchase_option_amount
            gda = rc.total_guarantee_deposit #guarantee_dep_application
            bid = rc.total_deposit_income #balance_income_deposit
            int_mora = rc.factor_rate
            base_type = rc.calculation_base
            itr = rc.interest_rate

            if base_type == '360/360':
                base = 360
            if base_type == '365/365' or base_type == '360/365':
                base = 365

        if self.type_request == 'early_settlement':
            past_due_balance = 0
            interest_mora = 0
            interest_mora_tmp = 0
            pay_num = 0
            vat_capital = 0
            amount_penalty = 0
            vat_poa = 0
            vat_interest_mora = 0
            days = 0
            interest_due = 0
            interest_mora_sum = 0
            records = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', credit_id.id),('req_credit_id', '=', False)])
            for rec_notice in records:
                past_due_balance += rec_notice.total_to_pay
                pay_num = rec_notice.payment_number
                balance_initial = rec_notice.outstanding_balance

            pay_num_amort = pay_num+1

            reg_due = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num),('credit_id', '=', credit_id.id)])
            for rec in reg_due:
                days = self.days_between(rec.expiration_date, self.date_settlement)

            rec_expirys = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', credit_id.id),('req_credit_id', '=', False)])
            for r_exp in rec_expirys:
                if r_exp.total_to_pay > 0:
                    reg_mor = self.env['extenss.credit.amortization'].search([('no_pay', '=', r_exp.payment_number),('credit_id', '=', credit_id.id)])
                    for rcs in reg_mor:
                        capital = rcs.capital
                        days_mora = self.days_between(rcs.expiration_date, self.date_settlement)
                        interest_mora = capital * ((int_mora/100)/base) * days_mora
                        interest_mora_sum += interest_mora

            vat_interest_mora = (vat_credit/100) * interest_mora_sum

            rec_amort = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num_amort),('credit_id', '=', credit_id.id)])
            for record in rec_amort:
                out_balance = record.initial_balance
                if rc.cs:
                    vat_capital = 0
                else:
                    vat_capital = (vat_credit/100) * out_balance

                amount_penalty = (penalty_percentage/100) * out_balance
                vat_poa = (vat_credit/100) * poa

            int_tmp = out_balance * ((itr/100)/base) * days
            vat_int = (vat_credit/100) * int_tmp

            if rc.cs or rc.af:
                sum_total = out_balance + int_tmp + vat_int

            if rc.af: 
                sum_total += vat_capital

            if rc.ap:
                sum_total = out_balance + int_tmp + vat_int + vat_capital

            st = amount_penalty + past_due_balance + interest_mora_sum + vat_interest_mora + poa + vat_poa - gda - bid

            settle_total = sum_total + st

            self.outstanding_balance = out_balance
            self.overdue_balance = past_due_balance
            self.interests = int_tmp
            self.days_interest = days
            self.interests_moratoriums = interest_mora_sum
            self.vat_interest_mora = vat_interest_mora
            self.capital_vat = vat_capital
            self.interests_vat = vat_int
            self.penalty = penalty_percentage
            self.penalty_amount = amount_penalty
            self.purchase_option = poa
            self.vat_purchase_option = vat_poa
            self.security_deposit_balance = bid
            self.balance_income_deposit = gda
            self.total_settle = settle_total
            self.balance_inicial = balance_initial

        if self.type_request == 'atc':
            if self.type_credit_ap or self.type_credit_af:
                if self.penalty == 0:
                    raise ValidationError(_('Enter the penalty percentage, is required for the type of credit'))

            notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', credit_id.id),('req_credit_id', '=', False)])
            for notice in notices:
                if notice.total_to_pay > 0:
                    raise ValidationError(_('The credit must be current'))

            records = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', credit_id.id),('req_credit_id', '=', False)])
            pay_num = 0
            for rec_notice in records:
                pay_num = rec_notice.payment_number
                balance_initial = rec_notice.outstanding_balance

            num_pay_new = pay_num + 1

            reg_due = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num),('credit_id', '=', credit_id.id)])
            for rec in reg_due:
                days = self.days_between(rec.expiration_date, self.advance_date)
                outstanding_balance = rec.initial_balance

            int_tmp = round(outstanding_balance * ((itr/100)/base) * days,2)
            int_vat = round(int_tmp * (vat_credit/100),2)

            amount_advance = round(((self.amount_req - int_tmp) / 1.17),2)

            if self.type_credit_cs:
                cap_vat = 0
            else:
                #cap_vat = outstanding_balance * (vat_credit/100)
                cap_vat = round(amount_advance * (vat_credit/100),2)

            amount_penalty = round(amount_advance * (penalty_percentage/100),2)
            total_req = self.amount_req - amount_penalty - int_tmp - int_vat - cap_vat

            self.interests = round(int_tmp,2)
            self.capital_vat = round(cap_vat,2)
            self.interests_vat = round(int_vat,2)
            self.days_interest = round(days,2)
            self.penalty_amount = round(amount_penalty,2)
            self.total_advance = round(total_req,2)
            self.total_settle = round(total_req,2)
            self.balance_inicial = balance_initial

    def create_notice_expiry(self, num_pay, credit_id, amount, list_concepts, id_req,due_not_date, initial_balance, factor_rate):
        rec_en = self.env['extenss.credit.expiry_notices']
        rec_cp = self.env['extenss.credit.concepts_expiration']
        id_expiry = rec_en.create({
            'credit_expiry_id': credit_id,
            'payment_number': num_pay,
            'due_not_date': due_not_date,
            'amount_not': amount,
            'total_paid_not': 0,
            'total_to_pay': 0,
            'req_credit_id': id_req,
            'outstanding_balance': initial_balance,
            'rate_moratorium': factor_rate
        })
        rec_notice = rec_en.search([('payment_number', '=', num_pay),('credit_expiry_id', '=', credit_id)])
        for r_notice in rec_notice:
            r_notice.id
        for rec in list_concepts:
            a=0
            b=1
            rec[a]
            rec[b]
            rec_cp.create({
                'expiry_notice_id': r_notice.id,
                'concept': rec[a],
                'amount_concept': rec[b],
                'total_paid_concept': 0,
                'full_paid': False,
            })
            a += 1
            b += 1
        return id_expiry

    def days_between(self, d1, d2):
        # d1 = datetime.strptime(d1, "%Y-%m-%d")
        # d2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((d2 - d1).days)

    def dynamic_selection_cs(self):
        return [('term', 'Term'),('amount', 'Amount')]

    def dynamic_selection_ap(self):
        return [('term', 'Term')]

    name = fields.Char(related='credit_request_id.credit_id', string='Credit', tracking=True, translate=True)
    credit_request_id = fields.Many2one('extenss.credit', string='Credit', tracking=True, translate=True)
    date_settlement = fields.Date(string='Settlement date', required=True, tracking=True, translate=True, default=fields.Date.context_today)
    advance_date = fields.Date(string='Advance date', tracking=True, translate=True, default=fields.Date.context_today)
    type_request = fields.Selection(TYPE_REQ, string='Type request', required=True, tracking=True, translate=True)
    penalty = fields.Float('Penalty', (2,6), tracking=True, translate=True)
    state = fields.Selection([('draft','Draft'),('pending','Pending'),('applied','Applied'),('cancelled','Cancelled')], string='State', default='draft', tracking=True, translate=True)

    outstanding_balance = fields.Monetary(string='Outstanding balance', currency_field='company_currency', tracking=True, translate=True)
    overdue_balance = fields.Monetary(string='Overdue Balance', currency_field='company_currency', tracking=True, translate=True)
    days_interest = fields.Integer(string='Days of interest', tracking=True, translate=True)
    interests = fields.Monetary(string='Interests', currency_field='company_currency', tracking=True, translate=True)
    interests_moratoriums = fields.Monetary(string='Interests moratoriums', currency_field='company_currency', tracking=True, translate=True)
    vat_interest_mora = fields.Monetary(string='Interest moratoriums VAT', currency_field='company_currency', tracking=True, translate=True)
    capital_vat= fields.Monetary(string='Capital VAT', currency_field='company_currency', tracking=True, translate=True)
    interests_vat = fields.Monetary(string='Interests VAT', currency_field='company_currency', tracking=True, translate=True)

    penalty_amount = fields.Monetary(string='Penalty Amount', currency_field='company_currency', tracking=True, translate=True)
    purchase_option = fields.Monetary(string='Purchase option', currency_field='company_currency', tracking=True, translate=True)
    vat_purchase_option = fields.Monetary(string='VAT Purchase option', currency_field='company_currency', tracking=True, translate=True)
    security_deposit_balance = fields.Monetary(string='Security Deposit Balance', currency_field='company_currency', tracking=True, translate=True)
    balance_income_deposit = fields.Monetary(string='Balance Income on Deposit', currency_field='company_currency', tracking=True, translate=True)
    total_settle = fields.Monetary(string='Total to Settle', currency_field='company_currency', tracking=True, translate=True)
    total_advance = fields.Monetary(string='Total to advance', currency_field='company_currency', tracking=True, translate=True)

    type_credit_cs = fields.Boolean(related='credit_request_id.cs', string='Type of Credit', tracking=True, translate=True)
    type_credit_ap = fields.Boolean(related='credit_request_id.ap', string='Type of Credit', tracking=True, translate=True)
    type_credit_af = fields.Boolean(related='credit_request_id.af', string='Type of Credit', tracking=True, translate=True)

    amount_req = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    advan_type_cs = fields.Selection(selection=lambda x: x.dynamic_selection_cs(), string='Advancement type', tracking=True, translate=True)
    advan_type_ap = fields.Selection(selection=lambda y: y.dynamic_selection_ap(), string='Advancement type', tracking=True, translate=True)
    advan_type_af = fields.Selection(selection=lambda y: y.dynamic_selection_ap(), string='Advancement type', tracking=True, translate=True)
    balance_inicial = fields.Monetary(string='Balance initial', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class ExtenssCreditRestructuring(models.Model):
    _name = 'extenss.credit.restructuring_table'
    _description = 'Credit Restructuring Table'

    credit_id = fields.Many2one('extenss.credit', string='Credit', translate=True)
    no_pay = fields.Integer('No Pay', translate=True)
    expiration_date = fields.Date('Expiration Date', translate=True)
    initial_balance = fields.Monetary('Initial Balance',currency_field='company_currency', tracking=True, translate=True)
    capital = fields.Monetary('Capital',currency_field='company_currency', tracking=True, translate=True)
    interest = fields.Monetary('Interest', currency_field='company_currency', tracking=True, translate=True)
    iva_interest = fields.Monetary('IVA Interest',currency_field='company_currency', tracking=True, translate=True)
    payment = fields.Monetary('Payment',currency_field='company_currency', tracking=True, translate=True)
    iva_capital = fields.Monetary('IVA Capital',currency_field='company_currency', tracking=True, translate=True)
    total_rent = fields.Monetary('Total Rent',currency_field='company_currency', tracking=True, translate=True)
    iva_rent = fields.Monetary('IVA Rent',currency_field='company_currency', tracking=True, translate=True)
    penalty_amount = fields.Monetary('Penalty amount', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class ExtenssCreditConciliation(models.Model):
    _name = 'extenss.credit.conciliation'
    _description = 'Conciliation'

    name = fields.Char(string='Reference', tracking=True, translate=True)
    initial_balance = fields.Monetary(string='Initial balance', currency_field='company_currency', tracking=True, translate=True)
    final_balance = fields.Monetary(string='Final balance', currency_field='company_currency', tracking=True, translate=True)
    status_bank = fields.Selection([('draft','Draft'),('pending','Pending'),('validated','Validated')], string='Status', default='draft', tracking=True, translate=True)
    processing_id = fields.Char(string='Processing id', tracking=True, translate=True)
    type_conciliation = fields.Selection([('conciliation', 'Conciliation')], string='Type', default='conciliation', tracking=True, translate=True)
    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    conciliation_ids = fields.One2many('extenss.credit.conciliation_lines', 'conciliation_id', string=' ', tracking=True)

    def action_copy_data(self):
        ids = []
        flag_check = False
        records = self.env['extenss.credit.conciliation'].search([('type_conciliation', '=', 'conciliation'),('processing_id', '!=', False)])
        for record in records:
            id_procs = record.processing_id
            ids.append(id_procs)

        records_bank = self.env['account.bank.statement'].search([('id', 'not in', ids)])
        for rec_bank in records_bank:
            concs_id = self.env['extenss.credit.conciliation'].create({
                'name': rec_bank.name,
                'initial_balance': rec_bank.balance_start,
                'final_balance': rec_bank.balance_end_real,
                'processing_id': rec_bank.id,
                'type_conciliation': 'conciliation'
            })

            records_lines = self.env['account.bank.statement.line'].search([('statement_id', '=', rec_bank.id)])
            for rec_line in records_lines:
                line_id = self.env['extenss.credit.conciliation_lines'].create({
                    'conciliation_id': concs_id.id,
                    'date': rec_line.date,
                    'description': rec_line.name,
                    'customer': rec_line.partner_id.id,
                    'reference': rec_line.ref,
                    'amount': rec_line.amount,
                    # 'bill_id': rec_ref.bill_id.id,
                    'type_rec': 'conciliation',
                    'status': 'pending',
                    #'expiry_id': rec_line.id
                })


            #     recs_ref = self.env['extenss.credit'].search([('reference_number', '=', rec_line.ref)])
            #     for rec_ref in recs_ref:
            #         if rec_ref:
            #             line_id = self.env['extenss.credit.conciliation_lines'].create({
            #                 'conciliation_id': concs_id.id,
            #                 'date': rec_line.date,
            #                 'description': rec_line.name,
            #                 'customer': rec_line.partner_id.id,
            #                 'reference': rec_line.ref,
            #                 'amount': rec_line.amount,
            #                 'bill_id': rec_ref.bill_id.id,
            #                 'type_rec': 'conciliation',
            #                 'status': 'pending',
            #                 #'expiry_id': rec_line.id
            #             })

                        # recs = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', rec_ref.id),('total_to_pay', '>', 0)])
                        # for rec in recs:
                        #     if rec.total_to_pay > 0:
                        #         if rec_line.amount == rec.total_to_pay:
                        #             flag_check = True
                        #             line_id.write({
                        #                 'check': True,
                        #             })
                        #         else:
                        #             flag_check = False

                            # self.env['extenss.credit.conciliation_lines'].create({
                            #     'conciliation_id': concs_id.id,
                            #     'date': rec.due_not_date,
                            #     'description': rec.expiry_number,
                            #     'customer': rec_ref.customer_id.id,
                            #     'reference': rec_ref.reference_number,
                            #     'amount': rec.total_to_pay,
                            #     'bill_id': rec_ref.bill_id.id,
                            #     'type_rec': 'expiry',
                            #     'status': 'pending',
                            #     'expiry_id': rec.id,
                            #     'check': flag_check
                            # })  

    def action_confirm_conciliation(self):
        flag_complete = False
        count_total = self.env['extenss.credit.conciliation_lines'].search_count([('conciliation_id', '=', self.id)])
        count_checks = self.env['extenss.credit.conciliation_lines'].search_count([('conciliation_id', '=', self.id),('check', '=', True)])
        records_con = self.env['extenss.credit.conciliation_lines'].search([('conciliation_id', '=', self.id),('status', '=', 'pending'),('type_rec', '=', 'conciliation')])
        records_ex = self.env['extenss.credit.conciliation_lines'].search([('conciliation_id', '=', self.id),('status', '=', 'pending'),('type_rec', '=', 'expiry')])

        for record_con in records_con:
            if record_con.check == True:
                amount = round(record_con.amount,2)
                self.env['extenss.credit.accounting_payments'].action_apply_movement(record_con.bill_id.id, 'abono', amount,'')
                record_con.status = 'applied'

        for record_ex in records_ex:
            if record_ex.check == True:
                amount_expiry = record_ex.amount
                amount = round(amount-amount_expiry,2)
                self.apply_payment(record_ex.expiry_id, '')
                record_ex.status = 'applied'
                id_exp = record_ex.expiry_id

        if count_total == count_checks:
            self.status_bank = 'validated'
            flag_complete = True

        if record_ex.type_rec == 'expiry' and amount > 0:
            if record.check == True:
                self.apply_amount(id_exp, amount)

        # flag_complete = False
        # count_total = self.env['extenss.credit.conciliation_lines'].search_count([('conciliation_id', '=', self.id)])
        # count_checks = self.env['extenss.credit.conciliation_lines'].search_count([('conciliation_id', '=', self.id),('check', '=', True)])
        # records = self.env['extenss.credit.conciliation_lines'].search([('conciliation_id', '=', self.id),('status', '=', 'pending')])
        # for record in records:
        #     if record.check == True and record.type_rec == 'conciliation':
        #         #self.env['extenss.credit'].register_payment()
        #         amount = round(record.amount,2)
        #         self.env['extenss.credit.accounting_payments'].action_apply_movement(record.bill_id.id, 'abono', amount,'')
        #         record.status = 'applied'
        #     if record.check == True and record.type_rec == 'expiry':
        #         amount_expiry = record.amount
        #         total_amount = round(amount-amount_expiry,2)
        #         self.apply_payment(record.expiry_id, '')
        #         print('total_amount if', total_amount)
        #         record.status = 'applied'
        #     if count_total == count_checks:
        #         self.status_bank = 'validated'
        #         flag_complete = True

        # if flag_complete and record.type_rec == 'expiry' and total_amount > 0:
        #     print('total_amount',total_amount)
        #     self.apply_amount(record.expiry_id, total_amount)

    def apply_payment(self, id, date_amort):
        _logger.info('Inicia apply_payment')
        _logger.info('id', id)
        _logger.info('date_amort', date_amort)
        date_payment = datetime.now().date()
        not_rec = self.env['extenss.credit.expiry_notices'].search([('id', '=', id)])
        for reg in not_rec:
            cred = self.env['extenss.credit'].search([('id', '=', reg.credit_expiry_id.id)])
            for reg_s in cred:
                if date_amort:
                    date_payment = date_amort
                else:
                    date_payment = reg_s.payment_date
                credit_id = reg_s.id

            if reg.total_to_pay > 0 and reg.due_not_date >= date_payment and reg.req_credit_id != False:
                _logger.info('reg.total_to_pay')
                records_account = self.env['extenss.credit.account'].search([('customer_id', '=', reg.credit_expiry_id.customer_id.id)])
                for act in records_account:
                    # req=self.env['extenss.credit.request'].search([('id', '=', reg.req_credit_id)])#'&','&','|',,('credit_request_id', '=', credit_id),('type_request','=','early_settlement'),('type_request','=','atc')])
                    # for re in req:
                        # if re.state == 'pending':
                            ex_no=self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id','=',reg.credit_expiry_id.id),('total_to_pay','>',0),('req_credit_id', '=', True)])
                            over_balance=reg_s.total_settle-reg_s.overdue_balance
                            for exno in ex_no:
                                if exno.req_credit_id == False:
                                    over_balance=over_balance+exno.total_to_pay
                            over_balance=round(over_balance,2)

                            if act.balance>=over_balance:
                                # reg_s.write({
                                # 'state': 'applied'
                                # })
                                reg_s.write({
                                'payment_date': date_payment
                                })
                                cred.write({
                                    'last_payment_date': datetime.now().date()
                                })

                                concepts_expiration = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id','=',reg.id)])
                                for conexp in concepts_expiration :
                                    conexp.write({
                                    'total_paid_concept': round(conexp.amount_concept,2)
                                    })
                                    conpay = self.env['extenss.credit.concept_payments']
                                    conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(conexp.amount_concept,2))
                                    })
                                    amount=round(conexp.amount_concept,2)
                                    self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                                    cred.total_paid += amount #08072020
                                ex_no=self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id','=',reg.credit_expiry_id.id),('req_credit_id', '=', False)])
                                for exno in ex_no:
                                    concepts_expiration = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id','=',exno.id)])
                                    for conexp in concepts_expiration :
                                        if conexp.full_paid == False:
                                            amount=round((conexp.amount_concept-conexp.total_paid_concept),2)
                                            conexp.write({
                                            'total_paid_concept': round(conexp.amount_concept,2)
                                            })
                                            conpay = self.env['extenss.credit.concept_payments']
                                            conpay.create({
                                            'concept_pay_id': conexp.id,
                                            'concept_id': exno.id,
                                            'date_paid': date_payment,
                                            'total_paid_cp': (round(amount,2))
                                            })
                                            self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                                            cred.total_paid += amount #08072020
                            # else:
                            #     req.write({
                            #     'state': 'cancelled'
                            #     })
                            #     credit=self.env['extenss.credit'].search([('id','=',req.credit_request_id.id)])
                            #     credit.write({
                            #     'flag_early_settlement': False
                            #     })

                        # if re.type_request == 'atc' and re.state == 'applied':
                        #     if re.type_credit_cs:
                        #         type_move = re.advan_type_cs
                        #     if re.type_credit_af:
                        #         type_move = re.advan_type_af
                        #     if re.type_credit_ap:
                        #         type_move = re.advan_type_ap
                            # print('re.credit_request_id.id',re.credit_request_id.id)
                            # print('re.id',re.id)
                            # print('type_move',type_move)

                            #self.env['extenss.credit'].recalculate_amortization_table(re.credit_request_id.id, re.id, type_move)

            #if reg.total_to_pay > 0 and reg.due_not_date < date_payment:
        not_rec = self.env['extenss.credit.expiry_notices'].search([('id', '=', id),('due_not_date','<=',date_payment),('req_credit_id', '=', False)])#,('total_to_pay', '>', '0'),('req_credit_id', '=', False),])
        for reg in not_rec:
            records_account = self.env['extenss.credit.account'].search([('customer_id', '=', reg.credit_expiry_id.customer_id.id)])
            for act in records_account:
                #for act in records_account:
                calculation_base = self.env['extenss.credit'].search([('id','=',reg.credit_expiry_id.id)]).calculation_base
                cs = self.env['extenss.credit'].search([('id','=',reg.credit_expiry_id.id)]).cs
                dn = self.env['extenss.credit'].search([('id','=',reg.credit_expiry_id.id)]).dn
                ap = self.env['extenss.credit'].search([('id','=',reg.credit_expiry_id.id)]).ap
                vatf = self.env['extenss.credit'].search([('id','=',reg.credit_expiry_id.id)]).vat_factor
                int_rate = self.env['extenss.credit'].search([('id','=',reg.credit_expiry_id.id)]).factor_rate
                if calculation_base == '360/360' or calculation_base == '360/365' :
                    base=360
                else:
                    base=365
                concepts_expiration = self.env['extenss.credit.concepts_expiration']
                exist_rec_mor = concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','morint')])
                capital_pay =concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','capital')]).total_paid_concept
                capital_ven =concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','capital')]).amount_concept
                int_pay=concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','interest')]).full_paid

                if ap == True :
                    capital_pay =concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','payment')]).total_paid_concept
                    capital_ven =concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','payment')]).amount_concept
                capital_ven=capital_ven-capital_pay
                #int_mor=capital_ven * (int_rate/base/100)
                int_mor=reg.outstanding_balance * (int_rate/base/100)
                if act.balance>0:
                    if not reg.payment_date:
                        dias_atr=(date_payment - reg.due_not_date).days
                        date_moras = reg.due_not_date + relativedelta(days=1)#OQJ Cambio para la fecha de moras inicial
                    else:
                        dias_atr=(date_payment - reg.payment_date).days
                        date_moras = reg.payment_date + relativedelta(days=1)#OQJ Cambio para la fecha de moras inicial

                    if date_payment > reg.due_not_date and dias_atr>0 and reg.total_to_pay>0:
                        int_mor=round(int_mor*dias_atr,2)
                        amount_n=0
                        #moras_table = self.env['extenss.credit.moras']
                        if not exist_rec_mor :
                            concepts_expiration.create({
                            'expiry_notice_id': reg.id,
                            'concept': 'morint',
                            'amount_concept': int_mor,
                            'total_paid_concept': 0,
                            'full_paid': False,
                            })
                            reg.write({###Actualiza la columna de moras
                                'interest_moratoriums':int_mor,
                                'days_mora': dias_atr,
                                'start_date_mora': date_moras,
                                #'rate_moratorium': int_rate
                            })
                            amount_n=round(int_mor,2)
                            concepts_expiration.create({
                            'expiry_notice_id': reg.id,
                            'concept': 'morintvat',
                            'amount_concept':(round(int_mor * (vatf/100),2)),
                            'total_paid_concept': 0,
                            'full_paid': False,
                            })
                            amount_n=amount_n+round(int_mor * (vatf/100),2)
                            # moras_table.create({
                            #     'credit_id': reg.credit_expiry_id.id,
                            #     'init_date': reg.due_not_date,
                            #     'end_date': date_payment,
                            #     'days': (date_payment - reg.due_not_date).days,
                            #     'past_due_balance': capital_ven,
                            #     'rate':(int_rate/base/100),
                            #     'interest':amount_n,
                            #     'amount_to_payment':reg.amount_not+amount_n
                            # })
                            reg.write({###Actualiza la columna de iva de moras
                                'vat_interest_mora':(round(int_mor * (vatf/100),2))
                            })
                        else:
                            exist_rec_mor.write({
                            'amount_concept':(round(exist_rec_mor.amount_concept+int_mor,2)),
                            'full_paid': False,
                            })
                            reg.write({###Actualiza la columna de moras
                                'interest_moratoriums': reg.interest_moratoriums+int_mor,
                            })
                            amount_n=round(int_mor,2)
                            exist_rec_morvat = concepts_expiration.search([('expiry_notice_id','=',reg.id),('concept','=','morintvat')])
                            exist_rec_morvat.write({
                            'amount_concept':(round(exist_rec_mor.amount_concept * (vatf/100),2)),
                            'full_paid': False,
                            })
                            amount_n=amount_n+round(int_mor * (vatf/100),2)
                            # moras_table=moras_table.search([('credit_id','=',reg.credit_expiry_id.id),('init_date','=',reg.due_not_date)])
                            # moras_table.write({
                            #     'end_date':date_payment,
                            #     'days': (date_payment - reg.due_not_date ).days,
                            #     'past_due_balance': capital_ven,
                            #     'rate':(int_rate/base/100),
                            #     'interest':moras_table.interest+amount_n,
                            #     'amount_to_payment':reg.amount_not+amount_n
                            # })
                            reg.write({###Actualiza la columna de iva de moras
                                'vat_interest_mora': reg.vat_interest_mora+(round(int_mor * (vatf/100),2)),
                                'days_mora': (date_payment - reg.due_not_date).days,
                            })
                        ### Se comenta para no afectar el monto total con las moras
                        # reg.write({
                        #     'amount_not':reg.amount_not+amount_n
                        # })

                    concepts_expiration = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id','=',reg.id)])
                    interest,intpay,intvat,intvatpay,capital,capay,capvat,capvatpay,morint,morintpay,morintvat,morintvatpay,payment,paypay,payvat,payvatpay,balance=0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,act.balance
                    fpint,fpcap,fpmorint,fppay,fppayvat=True,True,True,True,True
                    for conexp in concepts_expiration :
                        if conexp.concept == 'morint' :
                            morint=conexp.amount_concept 
                            fpmorint=conexp.full_paid
                            morintpay=conexp.total_paid_concept
                        if conexp.concept == 'morintvat' :
                            morintvat=conexp.amount_concept 
                            morintvatpay=conexp.total_paid_concept
                        if conexp.concept == 'interest' :
                            interest=conexp.amount_concept 
                            fpint=conexp.full_paid
                            intpay=conexp.total_paid_concept
                        if conexp.concept == 'intvat' :
                            intvat=conexp.amount_concept 
                            intvatpay=conexp.total_paid_concept
                        if conexp.concept == 'capital' :
                            capital=conexp.amount_concept
                            fpcap=conexp.full_paid
                            capay=conexp.total_paid_concept
                        if conexp.concept == 'capvat' :
                            capvat=conexp.amount_concept
                            capvatpay=conexp.total_paid_concept
                        if conexp.concept == 'payment' :
                            payment=conexp.amount_concept
                            fppay=conexp.full_paid
                            paypay=conexp.total_paid_concept
                        if conexp.concept == 'paymentvat' :
                            payvat=conexp.amount_concept
                            fppayvat=conexp.full_paid
                            payvatpay=conexp.total_paid_concept
                    if balance >= ((morint+morintvat)-(morintpay+morintvatpay)) and fpmorint == False:
                        fpmorint=True
                        balance=balance-((morint+morintvat)-(morintpay+morintvatpay))
                        reg.write({
                        'payment_date': date_payment
                        })
                        cred.write({
                            'last_payment_date': datetime.now().date()
                        })
                        amount=0
                        for conexp in concepts_expiration :
                            if conexp.concept == 'morint' :
                                conexp.write({
                                'total_paid_concept': round(conexp.amount_concept,2)
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round((conexp.amount_concept - morintpay),2))
                                })
                                amount=round((conexp.amount_concept - morintpay),2)
                            if conexp.concept == 'morintvat' :
                                conexp.write({
                                'total_paid_concept':(round(conexp.amount_concept,2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round((conexp.amount_concept - morintvatpay),2))
                                })
                                amount=amount+round((conexp.amount_concept - morintvatpay),2)
                        self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                        cred.total_paid += amount #08072020
                    elif balance>0 and fpmorint == False :
                        amount=0
                        for conexp in concepts_expiration :
                            if conexp.concept == 'morint' :
                                conexp.write({
                                'total_paid_concept': (round((balance/(1+(vatf/100)) + morintpay),2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round(balance/(1+(vatf/100)),2))
                                })
                                amount=(round(balance/(1+(vatf/100)),2))
                            if conexp.concept == 'morintvat' :
                                conexp.write({
                                'total_paid_concept': (round((((balance/(1+(vatf/100)))*(vatf/100)) + morintvatpay),2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round(((balance/(1+(vatf/100)))*(vatf/100)),2))
                                })
                                amount=amount+round(((balance/(1+(vatf/100)))*(vatf/100)),2)
                        balance=0
                        reg.write({
                        'payment_date': date_payment
                        })
                        cred.write({
                            'last_payment_date': datetime.now().date()
                        })
                        self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                        cred.total_paid += amount #08072020
                    if balance >= ((payment+payvat)-(paypay+payvatpay)) and fpmorint == True and fppayvat==False:####OQJ 29sep2020  ###aqui esta el error
                        fpint=True
                        balance=balance-((payment+payvat)-(paypay+payvatpay))
                        reg.write({
                            'payment_date': date_payment
                        })
                        cred.write({
                            'last_payment_date': datetime.now().date()
                        })
                        amount=0
                        for conexp in concepts_expiration :
                            if conexp.concept == 'payment':
                                conexp.write({
                                    'total_paid_concept': (round(conexp.amount_concept,2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round((conexp.amount_concept - paypay),2))###s emodifico el valor paypaypor 
                                })
                                amount=round((conexp.amount_concept - payvat),2)
                            if conexp.concept == 'paymentvat':
                                conexp.write({
                                    'total_paid_concept': (round(conexp.amount_concept,2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({ 
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round((conexp.amount_concept - payvatpay),2))
                                })
                                amount=amount+round((conexp.amount_concept - payvatpay),2)
                        self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                        cred.total_paid += amount #08072020
                    elif balance>0 and payment>0 and fpmorint == True and fppay==False:
                        amount=0
                        for conexp in concepts_expiration :
                            if conexp.concept == 'payment' :
                                conexp.write({
                                    'total_paid_concept': (round(((balance/(1+(vatf/100))) + payvat),2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(balance/(1+(vatf/100)),2))
                                })
                                amount=(round(balance/(1+(vatf/100)),2))
                            if conexp.concept == 'paymentvat' :
                                conexp.write({
                                    'total_paid_concept': (round((((balance/(1+(vatf/100))))*(vatf/100) + payvatpay),2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                    'concept_pay_id': conexp.id,
                                    'concept_id': reg.id,
                                    'date_paid': date_payment,
                                    'total_paid_cp': (round(((balance/(1+(vatf/100)))*(vatf/100)),2))
                                })
                                amount=amount+round(((balance/(1+(vatf/100)))*(vatf/100)),2)
                        balance=0
                        self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                        cred.total_paid += amount #08072020
                        reg.write({
                            'payment_date': date_payment
                        })
                        cred.write({
                            'last_payment_date': datetime.now().date()
                        })
                    # # if balance > 0 and payvat>0 and  fpmorint == True and fppayvat==False:
                    # #     print('entra a balance paymentvat')
                    # #     print('balance', balance)
                    # #     print('payvat', payvat)
                    # #     print('payvatpay', payvatpay)
                    # #     if balance>= (payvat-payvatpay):
                    # #         print('entra if balance')
                    # #         balance=balance-(payvat-payvatpay)
                    # #         total_paid_concept=(payvat-payvatpay)
                    # #     else:
                    # #         print('entra else de balance')
                            
                    # #         total_paid_concept=balance
                    # #         balance=balance-(payvat-payvatpay)
                    # #         print('total_paid_concept', total_paid_concept)
                    # #         print('balance', balance)
                    # #         #balance=0
                    # #     if payvat == (total_paid_concept+payvatpay) :
                    # #         print('payvat', payvat)
                    # #         fppayvat=True
                    # #     reg.write({
                    # #     'payment_date': date_payment
                    # #     })
                    # #     cred.write({
                    # #         'last_payment_date': datetime.now().date()
                    # #     })
                    # #     amount=0
                    # #     for conexp in concepts_expiration :
                    # #         if conexp.concept == 'paymentvat' :
                    # #             print('entra aqui en paymentvat')
                    # #             print('total_paid_concept', total_paid_concept)
                    # #             print('ope', total_paid_concept/(1+(vatf/100)))
                    # #             conexp.write({
                    # #             'total_paid_concept': (round((total_paid_concept/(1+(vatf/100)) + payvatpay),2))##OQJ 28Sep2020 se agrego -> /(1+(vatf/100))
                    # #             })
                    # #             conpay = self.env['extenss.credit.concept_payments']
                    # #             conpay.create({
                    # #             'concept_pay_id': conexp.id,
                    # #             'concept_id': reg.id,
                    # #             'date_paid': date_payment,
                    # #             'total_paid_cp': (round(total_paid_concept/(1+(vatf/100)),2))##OQJ 28Sep2020 se agrego -> /(1+(vatf/100))
                    # #             })
                    # #             amount=round(total_paid_concept/(1+(vatf/100)),2)
                    # #     self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                    # #     cred.total_paid += amount #08072020
                    # if balance > 0 and payment>0 and fppayvat==True and  fpmorint == True and fppay==False:
                    #     print('entra a balance payment')
                    #     if balance>= (payment-paypay):
                    #         balance=balance-(payment-paypay)
                    #         total_paid_concept=(payment-paypay)
                    #     else:
                    #         total_paid_concept=balance
                    #         balance=0
                    #     reg.write({
                    #     'payment_date': date_payment
                    #     })
                    #     cred.write({
                    #         'last_payment_date': datetime.now().date()
                    #     })
                    #     amount=0
                    #     for conexp in concepts_expiration :
                    #         if conexp.concept == 'payment' :
                    #             print('entra aqui en payment')
                    #             print('total_paid_concept', total_paid_concept)
                    #             print('ope', total_paid_concept/(1+(vatf/100)))
                    #             conexp.write({
                    #             'total_paid_concept': (round((total_paid_concept/(1+(vatf/100)) + paypay),2))#OQJ 28Sep2020 -> /(1+(vatf/100))
                    #             })
                    #             conpay = self.env['extenss.credit.concept_payments']
                    #             conpay.create({
                    #             'concept_pay_id': conexp.id,
                    #             'concept_id': reg.id,
                    #             'date_paid': date_payment,
                    #             'total_paid_cp': (round(total_paid_concept/(1+(vatf/100)),2))#OQJ 28Sep2020 -> /(1+(vatf/100))
                    #             })
                    #             amount=round(total_paid_concept,2)
                    #     self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                    #     cred.total_paid += amount #08072020
                    if balance >= ((interest+intvat)-(intpay+intvatpay)) and interest>0 and fpmorint == True and fpint == False:
                        fpint=True
                        balance=balance-((interest+intvat)-(intpay+intvatpay))
                        reg.write({
                        'payment_date': date_payment
                        })
                        cred.write({
                            'last_payment_date': datetime.now().date()
                        })
                        amount=0
                        for conexp in concepts_expiration :
                            if conexp.concept == 'interest' :
                                conexp.write({
                                'total_paid_concept': (round(conexp.amount_concept,2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round((conexp.amount_concept - intpay),2))
                                })
                                amount=round((conexp.amount_concept - intpay),2)
                            if conexp.concept == 'intvat' :
                                conexp.write({
                                'total_paid_concept': (round(conexp.amount_concept,2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({ 
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round((conexp.amount_concept - intvatpay),2))
                                })
                                amount=amount+round((conexp.amount_concept - intvatpay),2)
                        self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                        cred.total_paid += amount #08072020
                    elif balance>0 and interest>0 and fpmorint == True and fpint == False:
                        amount=0
                        for conexp in concepts_expiration :
                            if conexp.concept == 'interest' :
                                conexp.write({
                                'total_paid_concept': (round(((balance/(1+(vatf/100))) + intpay),2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round(balance/(1+(vatf/100)),2))
                                })
                                amount=(round(balance/(1+(vatf/100)),2))
                            if conexp.concept == 'intvat' :
                                conexp.write({
                                'total_paid_concept': (round((((balance/(1+(vatf/100))))*(vatf/100) + intvatpay),2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round(((balance/(1+(vatf/100)))*(vatf/100)),2))
                                })
                                amount=amount+round(((balance/(1+(vatf/100)))*(vatf/100)),2)
                        balance=0
                        self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                        cred.total_paid += amount #08072020
                        reg.write({
                        'payment_date': date_payment
                        })
                        cred.write({
                            'last_payment_date': datetime.now().date()
                        })
                    if balance >= ((capital+capvat)-(capay+capvatpay)) and fpint== True and fpcap == False :
                        balance=balance-((capital+capvat)-(capay+capvatpay))
                        reg.write({
                        'payment_date': date_payment
                        })
                        cred.write({
                            'last_payment_date': datetime.now().date()
                        })
                        amount=0
                        for conexp in concepts_expiration :
                            if conexp.concept == 'capital' :
                                conexp.write({
                                'total_paid_concept': (round(conexp.amount_concept,2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round((conexp.amount_concept - capay),2))
                                })
                                amount=round((conexp.amount_concept - capay),2)
                            if conexp.concept == 'capvat' :
                                conexp.write({
                                'total_paid_concept': (round(conexp.amount_concept,2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round((conexp.amount_concept - capvatpay),2))
                                })
                                amount=amount+round((conexp.amount_concept - capvatpay),2)
                        self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                        cred.total_paid += amount #08072020
                    elif balance>0 and fpint == True and fpcap == False:
                        total_paid_concept=balance + capay
                        amount=0
                        for conexp in concepts_expiration :
                            if conexp.concept == 'capital' :
                                if cs == False and dn==False:
                                    total_paid_concept = ((balance/(1+(vatf/100))) + capay)
                                conexp.write({
                                'total_paid_concept': (round(total_paid_concept,2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp': (round((total_paid_concept - capay),2))
                                })
                                amount=round((total_paid_concept - capay),2)
                            if conexp.concept == 'capvat' :
                                conexp.write({
                                'total_paid_concept': (round((((balance/(1+(vatf/100))))*(vatf/100) + capvatpay),2))
                                })
                                conpay = self.env['extenss.credit.concept_payments']
                                conpay.create({
                                'concept_pay_id': conexp.id,
                                'concept_id': reg.id,
                                'date_paid': date_payment,
                                'total_paid_cp':(round(((balance/(1+(vatf/100)))*(vatf/100)),2))
                                })
                                amount=amount+round(((balance/(1+(vatf/100)))*(vatf/100)),2)
                        balance=0
                        self.env['extenss.credit.accounting_payments'].action_apply_movement(act.id, 'cargo', round(amount,2),'')
                        cred.total_paid += amount #08072020
                        reg.write({
                        'payment_date': date_payment
                        })
                        cred.write({
                            'last_payment_date': datetime.now().date()
                        })
            notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id.id', '=', cred.id)])
            tmp_cap = 0
            tmp_int = 0
            tmp_cap_vat = 0
            tmp_int_vat = 0
            for notice in notices:
                if notice.total_to_pay > 0:
                    concepts = self.env['extenss.credit.concepts_expiration'].search([('expiry_notice_id', '=', notice.id)])
                    for concept in concepts:
                        print('concept.id', concept.id)
                        if cred.cs or cred.af:
                            if concept.concept == 'capital':
                                tmp_cap += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.overdue_capital', cred.overdue_capital)
                            if concept.concept == 'interest':
                                tmp_int += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.past_due_interest', cred.past_due_interest)
                            if concept.concept == 'intvat':
                                tmp_int_vat += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.expired_interest_vat', cred.expired_interest_vat)
                        if cred.af:
                            if concept.concept == 'capvat':
                                tmp_cap_vat += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.expired_capital_vat', cred.expired_capital_vat)
                        if cred.ap:
                            if concept.concept == 'payment':
                                tmp_cap += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.overdue_capital', cred.overdue_capital)
                            if concept.concept == 'paymentvat':
                                tmp_cap_vat += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.expired_capital_vat', cred.expired_capital_vat)
                            if concept.concept == 'intvat':
                                tmp_int_vat += (concept.amount_concept - concept.total_paid_concept)
                                print('cred.expired_interest_vat', cred.expired_interest_vat)

            cred.overdue_capital = tmp_cap
            cred.past_due_interest = tmp_int
            cred.expired_capital_vat = tmp_cap_vat
            cred.expired_interest_vat = tmp_int_vat

            expirys = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id.id', '=', cred.id)])
            tmp_days = 0
            for expiry in expirys:
                now = datetime.now().date()
                if expiry.total_to_pay > 0:
                    days_due = (now - expiry.due_not_date).days
                    if days_due > tmp_days:
                        tmp_days = days_due
            
            cred.number_days_overdue = tmp_days
        
        self.change_status_credit(credit_id)

    def apply_amount(self, id, amount):
        print('amount apply_amount', amount)
        print('id apply_amount', id)
        list_concepts = []
        #amount_total = 0
        #amount_pay = 0
        id_req = False

        expirys = self.env['extenss.credit.expiry_notices'].search([('id', '=', id),('req_credit_id', '=', False)])#buscar el ultimo registro aplicado
        if expirys:
            for expiry in expirys:
                pay = expiry.payment_number + 1

            creds = self.env['extenss.credit'].search([('id', '=', expiry.credit_expiry_id.id)])
            for cred in creds:

                while amount > 0:
                    list_concepts = []
                    amount_con = 0
                    amortization_s = self.env['extenss.credit.amortization'].search([('credit_id', '=', expiry.credit_expiry_id.id),('no_pay', '=', pay)])#sumarle uno al numero de aviso para busarlo en las amortizaciones
                    for amortization in amortization_s:
                        if cred.af or cred.cs:
                            list_concepts.append(['capital', amortization.capital])
                            amount_con += amortization.capital

                        if cred.af:
                            list_concepts.append(['capvat', amortization.iva_capital])
                            amount_con += amortization.iva_capital

                        if cred.af or cred.cs:
                            list_concepts.append(['interest', amortization.interest])
                            list_concepts.append(['intvat', amortization.iva_interest])
                            amount_con += amortization.interest + amortization.iva_interest

                        if cred.ap:
                            list_concepts.append(['payment', amortization.payment])
                            list_concepts.append(['paymentvat', amortization.iva_rent])
                            amount_con += amortization.payment + amortization.iva_rent

                        id = self.env['extenss.credit.request'].create_notice_expiry(pay, expiry.credit_expiry_id.id, amount_con, list_concepts, id_req, amortization.expiration_date, amortization.initial_balance, cred.factor_rate).id
                        #expiry_s = self.env['extenss.credit.expiry_notices'].search([('payment_number', '=', pay),('credit_expiry_id', '=', expiry.credit_expiry_id.id)])
                        # print('expiry_s',expiry_s)
                        # for expiry in expiry_s:
                        #     print('expiry.id',expiry.id)
                        self.apply_payment(id, amortization.expiration_date)
                        #aplicar el pago con la funcion de este modelo
                    pay = pay + 1
                    amount = amount - amount_con
                    list_concepts = []
                    print('amount while',amount)
    
    def change_status_credit(self, id_credit):
        creds = self.env['extenss.credit'].search([('id', '=', id_credit)])
        for cred in creds:

            regs_amort = self.env['extenss.credit.amortization'].search_count([('credit_id', '=', cred.id)])
            regs_pays = self.env['extenss.credit.expiry_notices'].search_count([('credit_expiry_id', '=', cred.id)])

            if regs_amort == regs_pays:
                regs_pays = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', id_credit),('total_to_pay', '>', 0)])
                if not regs_pays:
                    if cred.ff:
                        cred.credit_status = 'finished'

class ExtenssCreditConciliationLines(models.Model):
    _name = 'extenss.credit.conciliation_lines'
    _description = 'Conciliation Lines'

    conciliation_id = fields.Many2one('extenss.credit.conciliation', string='Conciliation', ondelete='cascade', tracking=True, translate=True)
    date = fields.Date(string='Date', tracking=True, translate=True)
    description = fields.Char(string='Description', tracking=True, translate=True)
    customer = fields.Many2one('res.partner', string='Customer', tracking=True, translate=True)
    reference = fields.Char(string='Reference', tracking=True, translate=True)
    amount = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    check = fields.Boolean(string='Validate', tracking=True, translate=True)
    status = fields.Selection([('applied', 'Applied'),('pending', 'Pending'),],string='Status', tracking=True, translate=True)
    display_type = fields.Selection([('line_section', 'Section'),('line_note', 'Note'),], default=False)
    type_rec = fields.Selection([('expiry', 'Expiry'),('conciliation', 'Conciliation'),('dn', 'DN'),], default=False)
    bill_id = fields.Many2one('extenss.credit.account', string='Bill', tracking=True, translate=True)
    expiry_id = fields.Char(string='Id expiry', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
