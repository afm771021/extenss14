from odoo import fields, models, api, _, exceptions
from odoo.exceptions import Warning, UserError, ValidationError

from datetime import timedelta
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

class ExtenssAF(models.Model):
    _inherit = 'extenss.credit'
    _description = 'Credit Financial leasing'

    # def action_calculate_request(self):
    #     out_balance = 0
    #     vat_capital = 0

    #     vat_credit = self.vat_factor
    #     penalty_percentage = self.penalty
    #     poa = self.purchase_option_amount
    #     gda = self.total_guarantee_deposit #guarantee_dep_application
    #     bid = self.total_deposit_income #balance_income_deposit
    #     int_mora = self.factor_rate
    #     base_type = self.calculation_base
    #     itr = self.interest_rate

    #     if base_type == '360/360':
    #         base = 360
    #     if base_type == '365/365' or base_type == '360/365':
    #         base = 365

    #     # if self.type_request == 'early_settlement':
    #     balance_initial = 0
    #     past_due_balance = 0
    #     interest_mora = 0
    #     interest_mora_tmp = 0
    #     pay_num = 0
    #     vat_capital = 0
    #     amount_penalty = 0
    #     vat_poa = 0
    #     vat_interest_mora = 0
    #     days = 0
    #     interest_due = 0
    #     interest_mora_sum = 0
    #     records = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('req_credit_id', '=', False)])
    #     for rec_notice in records:
    #         past_due_balance += rec_notice.total_to_pay
    #         pay_num = rec_notice.payment_number
    #         balance_initial = rec_notice.outstanding_balance

    #     pay_num_amort = pay_num+1

    #     reg_due = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num),('credit_id', '=', self.id)])
    #     for rec in reg_due:
    #         days = self.days_between(rec.expiration_date, self.date_settlement)

    #     rec_expirys = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('req_credit_id', '=', False)])
    #     for r_exp in rec_expirys:
    #         if r_exp.total_to_pay > 0:
    #             reg_mor = self.env['extenss.credit.amortization'].search([('no_pay', '=', r_exp.payment_number),('credit_id', '=', self.id)])
    #             for rcs in reg_mor:
    #                 capital = rcs.capital
    #                 days_mora = self.days_between(rcs.expiration_date, self.date_settlement)
    #                 interest_mora = capital * ((int_mora/100)/base) * days_mora
    #                 interest_mora_sum += interest_mora

    #     vat_interest_mora = (vat_credit/100) * interest_mora_sum

    #     rec_amort = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num_amort),('credit_id', '=', self.id)])
    #     for record in rec_amort:
    #         out_balance = record.initial_balance

    #         vat_capital = (vat_credit/100) * out_balance

    #         amount_penalty = (penalty_percentage/100) * out_balance
    #         vat_poa = (vat_credit/100) * poa

    #     int_tmp = out_balance * ((itr/100)/base) * days
    #     vat_int = (vat_credit/100) * int_tmp

    #     if self.af:
    #         sum_total = out_balance + int_tmp + vat_int

    #     if self.af: 
    #         sum_total += vat_capital

    #     st = amount_penalty + past_due_balance + interest_mora_sum + vat_interest_mora + poa + vat_poa - gda - bid

    #     settle_total = sum_total + st

    #     self.outstanding_balance = out_balance
    #     self.overdue_balance = past_due_balance
    #     self.interests = int_tmp
    #     self.days_interest = days
    #     self.interests_moratoriums = interest_mora_sum
    #     self.vat_interest_mora = vat_interest_mora
    #     self.capital_vat = vat_capital
    #     self.interests_vat = vat_int
    #     self.penalty = penalty_percentage
    #     self.penalty_amount = amount_penalty
    #     self.purchase_option = poa
    #     self.vat_purchase_option = vat_poa
    #     self.security_deposit_balance = bid
    #     self.balance_income_deposit = gda
    #     self.total_settle = settle_total
    #     self.balance_inicial = balance_initial

    # def action_apply_request(self):
    #     list_concepts = []
    #     amount = 0
    #     #if self.type_request == 'early_settlement':
    #     pay_rec = self.env['extenss.credit.expiry_notices'].search_count([('credit_expiry_id', '=', self.id),('req_credit_id', '=', False)])
    #     num_rec = pay_rec + 1

    #     # ec_id = self.env['extenss.credit'].browse(self.env.context.get('active_ids'))
    #     # for rec in ec_id:
    #     factor_rate = self.factor_rate
    #     id_accnt = self.bill_id.id
    #     flag_early_settlement = True
    #     if self.af:
    #         if self.outstanding_balance > 0:
    #             list_concepts.append(['capital', self.outstanding_balance])
    #     if self.af:       
    #         if self.capital_vat > 0:
    #             list_concepts.append(['capvat', self.capital_vat])
    #     if self.af:
    #         if self.interests > 0:
    #             list_concepts.append(['interest', self.interests])
    #     if self.af:
    #         if self.interests_vat > 0:
    #             list_concepts.append(['intvat', self.interests_vat])
        
    #     if self.penalty_amount > 0:
    #         list_concepts.append(['penalty_amount', self.penalty_amount])
    #     if self.purchase_option > 0:
    #         list_concepts.append(['purchase_option', self.purchase_option])
    #     if self.vat_purchase_option > 0:
    #         list_concepts.append(['vat_option', self.vat_purchase_option])
    #     if self.interests_moratoriums > 0:
    #         list_concepts.append(['morint', self.interests_moratoriums])
    #     if self.vat_interest_mora > 0:
    #         list_concepts.append(['morintvat', self.vat_interest_mora])

    #     amount = self.security_deposit_balance + self.balance_income_deposit + self.total_settle - self.overdue_balance
    #     self.create_notice_expiry(num_rec, self.id, amount, list_concepts, self.id,self.date_settlement, self.balance_inicial, factor_rate)

    #     # #realiza trasacciones a la cuenta eje
    #     if self.security_deposit_balance > 0:
    #         self.env['extenss.credit.accounting_payments'].action_apply_movement(id_accnt, 'abono', self.security_deposit_balance, 'Security Deposit Balance payment')
    #         guarantee_dep_balance = 0 #09062020
    #     if self.balance_income_deposit > 0:
    #         self.env['extenss.credit.accounting_payments'].action_apply_movement(id_accnt, 'abono', self.balance_income_deposit, 'Balance Income on Deposit payment')
    #         balance_income_deposit = 0 #09062020

    # def days_between(self, d1, d2):
    #     # d1 = datetime.strptime(d1, "%Y-%m-%d")
    #     # d2 = datetime.strptime(d2, "%Y-%m-%d")
    #     return abs((d2 - d1).days)

    # def create_notice_expiry(self, num_pay, credit_id, amount, list_concepts, id_req,due_not_date, initial_balance, factor_rate):
    #     rec_en = self.env['extenss.credit.expiry_notices']
    #     rec_cp = self.env['extenss.credit.concepts_expiration']
    #     id_expiry = rec_en.create({
    #         'credit_expiry_id': credit_id,
    #         'payment_number': num_pay,
    #         'due_not_date': due_not_date,
    #         'amount_not': amount,
    #         'total_paid_not': 0,
    #         'total_to_pay': 0,
    #         'req_credit_id': id_req,
    #         'outstanding_balance': initial_balance,
    #         'rate_moratorium': factor_rate
    #     })
    #     rec_notice = rec_en.search([('payment_number', '=', num_pay),('credit_expiry_id', '=', credit_id)])
    #     for r_notice in rec_notice:
    #         r_notice.id
    #     for rec in list_concepts:
    #         a=0
    #         b=1
    #         rec[a]
    #         rec[b]
    #         rec_cp.create({
    #             'expiry_notice_id': r_notice.id,
    #             'concept': rec[a],
    #             'amount_concept': rec[b],
    #             'total_paid_concept': 0,
    #             'full_paid': False,
    #         })
    #         a += 1
    #         b += 1
    #     return id_expiry

    # def action_apply_pay_adv(self):
    #     print('entra a action_apply_pay_adv')

    # af = fields.Boolean(String='AF')
    # account_status_date = fields.Date(string=u'Account Status Date', default=fields.Date.context_today)
    # conciliation_credit_ids = fields.Many2many('extenss.credit.conciliation_lines', string='Payment')
    # bill_id = fields.Many2one('extenss.credit.account', string='Bill', tracking=True, translate=True)

    # balance = fields.Monetary(related='bill_id.balance',currency_field='company_currency')

    #Liquidacion Anticipada
    # date_settlement = fields.Date(string='Settlement date', required=True, tracking=True, translate=True, default=fields.Date.context_today)
    # penalty = fields.Float('Penalty', (2,6), tracking=True, translate=True)
    # outstanding_balance = fields.Monetary(string='Outstanding balance', currency_field='company_currency', tracking=True, translate=True)
    # overdue_balance = fields.Monetary(string='Overdue Balance', currency_field='company_currency', tracking=True, translate=True)
    # days_interest = fields.Integer(string='Days of interest', tracking=True, translate=True)
    # interests = fields.Monetary(string='Interests', currency_field='company_currency', tracking=True, translate=True)
    # interests_moratoriums = fields.Monetary(string='Interests moratoriums', currency_field='company_currency', tracking=True, translate=True)
    # vat_interest_mora = fields.Monetary(string='Interest moratoriums VAT', currency_field='company_currency', tracking=True, translate=True)
    # capital_vat= fields.Monetary(string='Capital VAT', currency_field='company_currency', tracking=True, translate=True)
    # interests_vat = fields.Monetary(string='Interests VAT', currency_field='company_currency', tracking=True, translate=True)

    # penalty_amount = fields.Monetary(string='Penalty Amount', currency_field='company_currency', tracking=True, translate=True)
    # purchase_option = fields.Monetary(string='Purchase option', currency_field='company_currency', tracking=True, translate=True)
    # vat_purchase_option = fields.Monetary(string='VAT Purchase option', currency_field='company_currency', tracking=True, translate=True)
    # security_deposit_balance = fields.Monetary(string='Security Deposit Balance', currency_field='company_currency', tracking=True, translate=True)
    # balance_income_deposit = fields.Monetary(string='Balance Income on Deposit', currency_field='company_currency', tracking=True, translate=True)
    # total_settle = fields.Monetary(string='Total to Settle', currency_field='company_currency', tracking=True, translate=True)
    # balance_inicial = fields.Monetary(string='Balance intial', currency_field='company_currency', tracking=True, translate=True)

    # company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    # company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    # def action_apply_payment(self):
    #     #self.apply_mov_pay()
    #     list_concepts = []
    #     for reg in self.conciliation_credit_ids:
    #         if reg.check == False and reg.status == 'pending':
    #             print(self.bill_id.id)
    #             self.env['extenss.credit.accounting_payments'].action_apply_movement(self.bill_id.id, 'abono', reg.amount,'')
    #             print(reg.id)
    #             print(reg.customer.id)
    #             print(reg.amount)
    #             print(reg.status)
    #             print(self.product_id.id)
    #             reg.status = 'applied'
    #             reg.check = True
    #     exp_notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('total_to_pay', '>', 0)])
    #     for exp_notice in exp_notices:
    #         print(exp_notice.total_to_pay)
    #         print(exp_notice.id)
    #         self.env['extenss.credit.conciliation'].apply_payment(exp_notice.id, self.payment_date)
    #     #self.conf_datamart('pay_notice')
    #     regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'pay_notice')])
    #     if regs_conf:
    #         for reg_conf in regs_conf:
    #             print(reg.id)
    #             for reg_events in reg_conf.event_id:
    #                 event_key = reg_events.event_key
    #                 print(event_key)

    #                 #for lines in self.conciliation_lines_ids:
    #                 list_concepts.append(reg.customer.id)
    #                 list_concepts.append(reg.amount) 
    #                 list_concepts.append(self.product_id.id)
    #                 list_concepts.append(event_key) #)
    #                 print(list_concepts)
    #                 self.env['extenss.credit'].create_records(list_concepts)
    #                 list_concepts = []
    #     else:
    #         raise ValidationError(_('Not exist record in Configuration in Datamart'))

    # def apply_mov_pay(self):
    #     for reg in self.conciliation_credit_ids:
    #         if reg.check == False and reg.status == 'pending':
    #             #print(self.bill_id.id)
    #             self.env['extenss.credit.accounting_payments'].action_apply_movement(self.bill_id.id, 'abono', reg.amount,'')
    #             # print(reg.id)
    #             # print(reg.customer.id)
    #             # print(reg.amount)
    #             # print(reg.status)
    #             # print(self.product_id.id)
    #             reg.status = 'applied'
    #             reg.check = True
    #         # else:
    #         #     raise ValidationError(_('Not exist record selected in field Payment'))

    #     exp_notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('total_to_pay', '>', 0)])
    #     for exp_notice in exp_notices:
    #         print(exp_notice.total_to_pay)
    #         print(exp_notice.id)
    #         self.env['extenss.credit.conciliation'].apply_payment(exp_notice.id, self.payment_date)

    # def action_pay_early_settlement(self):
    #     self.action_apply_request()
    #     list_concepts = []
    #     for reg in self.conciliation_credit_ids:
    #         if reg.check == False and reg.status == 'pending':
    #             print(self.bill_id.id)
    #             self.env['extenss.credit.accounting_payments'].action_apply_movement(self.bill_id.id, 'abono', reg.amount,'')
    #             print(reg.id)
    #             print(reg.customer.id)
    #             print(reg.amount)
    #             print(reg.status)
    #             print(self.product_id.id)
    #             reg.status = 'applied'
    #             reg.check = True
    #     exp_notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('total_to_pay', '>', 0)])
    #     for exp_notice in exp_notices:
    #         print(exp_notice.total_to_pay)
    #         print(exp_notice.id)
    #         self.env['extenss.credit.conciliation'].apply_payment(exp_notice.id, self.payment_date)

    #     regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'early_set')])
    #     if regs_conf:
    #         for reg_conf in regs_conf:
    #             print(reg.id)
    #             for reg_events in reg_conf.event_id:
    #                 event_key = reg_events.event_key
    #                 print(event_key)

    #                 #for lines in self.conciliation_lines_ids:
    #                 list_concepts.append(reg.customer.id)
    #                 list_concepts.append(reg.amount) 
    #                 list_concepts.append(self.product_id.id)
    #                 list_concepts.append(event_key) #)
    #                 print(list_concepts)
    #                 self.env['extenss.credit'].create_records(list_concepts)
    #                 list_concepts = []
    #         self.flag_early_settlement = True
    #         self.credit_status = 'liquidated'
    #     else:
    #         raise ValidationError(_('Not exist record in Configuration in Datamart'))
        #self.apply_mov_pay()
        #self.action_apply_payment()
        # exp_notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('total_to_pay', '>', 0)])
        # for exp_notice in exp_notices:
        #     print(exp_notice.total_to_pay)
        #     print(exp_notice.id)
            #self.env['extenss.credit.conciliation'].apply_payment(exp_notice.id, self.payment_date)
        #self.conf_datamart('early_set')

    # def conf_datamart(self, type_concept):
    #     list_concepts = []
    #     regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', type_concept)])
    #     if regs_conf:
    #         for reg_conf in regs_conf:
    #             #print(reg.id)
    #             for reg_events in reg_conf.event_id:
    #                 event_key = reg_events.event_key
    #                 print(event_key)

    #                 #for lines in self.conciliation_credit_ids:
    #                 for reg in self.conciliation_credit_ids:
    #                     list_concepts.append(reg.customer.id)
    #                     list_concepts.append(reg.amount) 
    #                     list_concepts.append(self.product_id.id)
    #                     list_concepts.append(event_key) #)
    #                     print(list_concepts)
    #                     self.env['extenss.credit'].create_records(list_concepts)
    #                     list_concepts = []
    #     else:
    #         raise ValidationError(_('Not exist record in Configuration in Datamart'))

    #     # for lines in self.conciliation_lines_ids:
    #     #     list_data.append(lines.customer.id)
    #     #     list_data.append(lines.amount)
    #     #     list_data.append(self.productid.id)
    #     #     list_data.append('250')
    #     #     self.env['extenss.credit'].create_records(list_data)

    # def action_pay_advance(self):
    #     amount_ids = 0
    #     # for reg in self.conciliation_credit_ids:
    #     #     if reg.check == False and reg.status == 'pending':
    #     #         self.env['extenss.credit.accounting_payments'].action_apply_movement(self.bill_id.id, 'abono', reg.amount,'')
    #     #         print(reg.amount)
    #     #         reg.status = 'applied'
    #     #         reg.check = True
    #     #         amount_ids = reg.amount

    #     self.balance

    #     exp_notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('total_to_pay', '>', 0)])
    #     for exp_notice in exp_notices:
    #         print(exp_notice.amount_not)
    #         print(exp_notice.id)
    #         self.env['extenss.credit.conciliation'].apply_payment(exp_notice.id, '')
    #         #print('amount_ids', amount_ids)
    #         print('exp_notice.amount_not', exp_notice.amount_not)
    #         amount_ids = round(self.balance - exp_notice.amount_not,2)
    #         print('amount_ids', amount_ids)
    #         self.env['extenss.credit.conciliation'].apply_amount(exp_notice.id, amount_ids)

    # def create_records(self, list_data):
    #     today = datetime.now().date()
    #     #for lines in self.conciliation_lines_ids:
    #     ext_dats = self.env['extenss.datamart'].search([('date', '=', today)])
    #     if ext_dats:
    #         for ext_dat in ext_dats:
    #             self.env['extenss.datamart.lines'].create({
    #                 'datamart_id': ext_dat.id,
    #                 #'account_id': 2,
    #                 'partner_id': list_data[0],#lines.customer.id,
    #                 'name': 'Datamart',
    #                 'amount': list_data[1],#lines.amount,
    #                 'product_id': list_data[2],#self.productid.id,
    #                 'type_line': list_data[3],#'700',
    #             })
    #     else:
    #         id_exdat =  self.env['extenss.datamart'].create({
    #             'date': datetime.now().date(),
    #             'name': datetime.now().date(),
    #         })
    #         self.env['extenss.datamart.lines'].create({
    #             'datamart_id': id_exdat.id,
    #             #'account_id': 2,
    #             'partner_id': list_data[0],#lines.customer.id,
    #             'name': 'Datamart',
    #             'amount': list_data[1],#lines.amount,
    #             'product_id': list_data[2],#self.productid.id,
    #             'type_line': list_data[3],#'700',
    #         })

# class ExtenssLead(models.Model):
#     _inherit = 'crm.lead'

#     sale_order_ids = fields.One2many('sale.order', 'opportunity_id', string='Orders', domain=lambda self:[('state','=','sale')])
#     af_s = fields.Boolean(related='sale_order_ids.af')
#     productid = fields.Many2one(related='sale_order_ids.product_id')
#     conciliation_lines_ids = fields.Many2many('extenss.credit.conciliation_lines', string='Payment')#,  default=_default_conciliation)
#     flag_initial_payment = fields.Boolean(string='Inital Payment', default=False, tracking=True, translate=True)

#     ####Metodo para Pago inicial
#     def action_apply_payment_af(self):
#         list_data = []
#         regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'pay_initial')])
#         for reg_conf in regs_conf:
#             for reg_events in reg_conf.event_id:
#                 event_key = reg_events.event_key
#                 for reg_order in self.sale_order_ids:
#                     if reg_order.total_deposit > 0 and event_key == 120:
#                         amount = reg_order.total_deposit
#                     if reg_order.total_guarantee > 0 and event_key == 140:
#                         amount = reg_order.total_guarantee
#                     if reg_order.total_commision > 0 and event_key == 210:
#                         amount = reg_order.total_commision

#                     if amount > 0:
#                         for lines in self.conciliation_lines_ids:
#                             list_data.append(lines.customer.id)
#                             list_data.append(amount)
#                             list_data.append(self.productid.id)
#                             list_data.append(event_key)
#                             #print(list_data)
#                             self.env['extenss.credit'].create_records(list_data)
#                             list_data = []
#                             amount = 0

#             self.flag_initial_payment = True
#             lines.status = 'applied'

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', check_company=True)#domain="[('type', '=', 'opportunity'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    total_initial_payments = fields.Monetary('Total Initial Payments', currency_field='company_currency', tracking=True)
    af = fields.Boolean(String='AF')
    product_id = fields.Many2one('extenss.product.product', 'Product Name')

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
# class ExtenssCreditConciliation(models.Model):
#     _inherit = 'extenss.credit.conciliation'

#     credit_request_id = fields.Many2one('crm.lead', string='Credit', tracking=True, translate=True)
#     conciliation_ids = fields.One2many('extenss.credit.conciliation_lines', 'conciliation_id', string=' ', tracking=True)

class ExtenssCreditConciliationLines(models.Model):
    _inherit = 'extenss.credit.conciliation_lines'
    _description = 'Conciliation Lines'

    # conciliation_credit_id = fields.Many2one('extenss.credit', string='Credit_id', ondelete='cascade', tracking=True, translate=True)
    # conciliation_lines_id = fields.Many2one('crm.lead', string='CRM id', ondelete='cascade', tracking=True, translate=True)
    # conciliation_id = fields.Many2one('extenss.credit.conciliation', string='Conciliation', ondelete='cascade', tracking=True, translate=True)