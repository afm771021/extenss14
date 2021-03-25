from odoo import fields, models, api, _, exceptions
from odoo.exceptions import Warning, UserError, ValidationError

from datetime import timedelta
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

class ExtenssFF(models.Model):
    _inherit = 'extenss.credit'

    # def get_count_credits(self):
    #     count = self.env['extenss.credit'].search_count([('id', '=', self.id)])
    #     self.count_credits = count

    # def action_calculate_request(self):
    #     out_balance = 0
    #     vat_capital = 0
    #     # credit_id = self.env['extenss.credit'].browse(self.env.context.get('active_ids'))
    #     # rcs = self.env['extenss.credit'].search([('id', '=', credit_id.id)])
    #     #for rc in rcs:
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
    #     settle_total = 0
    #     sum_total = 0
    #     records = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('req_credit_id', '=', False)])
    #     for rec_notice in records:
    #         past_due_balance += rec_notice.total_to_pay
    #         pay_num = rec_notice.payment_number
    #         balance_initial = rec_notice.outstanding_balance

    #     pay_num_amort = pay_num+1

    #     reg_due = self.env['extenss.credit.amortization'].search([('no_pay', '=', pay_num_amort),('credit_id', '=', self.id)])
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

    #     if self.ff:
    #         sum_total = out_balance + int_tmp + vat_int

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
    #     if self.ff:
    #         if self.outstanding_balance > 0:
    #             list_concepts.append(['capital', self.outstanding_balance])
    #     # if self.af:       
    #     #     if self.capital_vat > 0:
    #     #         list_concepts.append(['capvat', self.capital_vat])
    #     if self.ff:
    #         if self.interests > 0:
    #             list_concepts.append(['interest', self.interests])
    #     if self.ff:
    #         if self.interests_vat > 0:
    #             list_concepts.append(['intvat', self.interests_vat])
        
    #     if self.penalty_amount > 0:
    #         list_concepts.append(['penalty_amount', self.penalty_amount])
    #     # if self.purchase_option > 0:
    #     #     list_concepts.append(['purchase_option', self.purchase_option])
    #     # if self.vat_purchase_option > 0:
    #     #     list_concepts.append(['vat_option', self.vat_purchase_option])
    #     if self.interests_moratoriums > 0:
    #         list_concepts.append(['morint', self.interests_moratoriums])
    #     if self.vat_interest_mora > 0:
    #         list_concepts.append(['morintvat', self.vat_interest_mora])

    #     amount = self.security_deposit_balance + self.balance_income_deposit + self.total_settle - self.overdue_balance
    #     self.create_notice_expiry(num_rec, self.id, amount, list_concepts, self.id,self.date_settlement, self.balance_inicial, factor_rate)

        # #realiza trasacciones a la cuenta eje
        # if self.security_deposit_balance > 0:
        #     self.env['extenss.credit.accounting_payments'].action_apply_movement(id_accnt, 'abono', self.security_deposit_balance, 'Security Deposit Balance payment')
        #     guarantee_dep_balance = 0 #09062020
        # if self.balance_income_deposit > 0:
        #     self.env['extenss.credit.accounting_payments'].action_apply_movement(id_accnt, 'abono', self.balance_income_deposit, 'Balance Income on Deposit payment')
        #     balance_income_deposit = 0 #09062020

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

    # conciliation_credit_ids = fields.Many2many('extenss.credit.conciliation_lines',string='Payment')#, domain=lambda self:[('type_rec', '=', 'dn')]
    # balance = fields.Monetary(related='bill_id.balance',currency_field='company_currency')

    init_date = fields.Date(string='Init date', tracking=True, translate=True)
    invoice_date = fields.Date(string='Invoice date', tracking=True, translate=True)
    capacity = fields.Float('% Capacity', (2,2), tracking=True, translate=True)
    days = fields.Integer(string='Days', tracking=True, translate=True)

    # company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    # company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    # def action_apply_payment(self):
    #     #self.apply_mov_pay()
    #     list_concepts = []
    #     for reg in self.conciliation_credit_ids:
    #         if reg.check == False and reg.status == 'pending' and reg.customer == self.customer_id:
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

    # def action_pay_early_settlement(self):
    #     self.action_apply_request()
    #     list_concepts = []
    #     for reg in self.conciliation_credit_ids:
    #         if reg.check == False and reg.status == 'pending':
    #             self.env['extenss.credit.accounting_payments'].action_apply_movement(self.bill_id.id, 'abono', reg.amount,'')
    #             reg.status = 'applied'
    #             reg.check = True
    #     exp_notices = self.env['extenss.credit.expiry_notices'].search([('credit_expiry_id', '=', self.id),('total_to_pay', '>', 0)])
    #     for exp_notice in exp_notices:
    #         self.env['extenss.credit.conciliation'].apply_payment(exp_notice.id, self.payment_date)

    #     regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'early_set')])
    #     if regs_conf:
    #         for reg_conf in regs_conf:
    #             # print(reg.id)
    #             for reg_events in reg_conf.event_id:
    #                 event_key = reg_events.event_key
    #                 list_concepts.append(reg.customer.id)
    #                 list_concepts.append(reg.amount) 
    #                 list_concepts.append(self.product_id.id)
    #                 list_concepts.append(event_key)
    #                 self.env['extenss.credit'].create_records(list_concepts)
    #                 list_concepts = []
    #         self.flag_early_settlement = True
    #         self.credit_status = 'liquidated'
    #     else:
    #         raise ValidationError(_('Not exist record in Configuration in Datamart'))

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
    #                 'description': 'Datamart',
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
    #             'description': 'Datamart',
    #             'amount': list_data[1],#lines.amount,
    #             'product_id': list_data[2],#self.productid.id,
    #             'type_line': list_data[3],#'700',
    #         })

# class ExtenssLead(models.Model):
#     _inherit = 'crm.lead'

    # amount_ff = fields.Monetary(string='Amount', currency_field='company_currency')
    # amount_out_vat = fields.Monetary(string='Amount without VAT', currency_field='company_currency', compute='_compute_amount', store=True, tracking=True, translate=True)
    # purpose = fields.Char(string='Purpose', tracking=True, translate=True)
    # description_purpose = fields.Char(string='Description purpose', tracking=True, translate=True)

    # init_date = fields.Date(string='Init date', tracking=True, translate=True)
    # invoice_date = fields.Date(string='Invoice date', tracking=True, translate=True)
    # payment_method = fields.Char(string='Payment method', tracking=True, translate=True)
    # capacity = fields.Float('% Capacity', (2,2), tracking=True, translate=True)
    # amount_financed = fields.Monetary(string='Amount financed', currency_field='company_currency', compute='_compute_amount_financed',store=True, tracking=True, translate=True)
    # commission_details = fields.Float('Commission Details', (2,2), tracking=True, translate=True)
    # commissions = fields.Monetary(string='Commissions', currency_field='company_currency', compute='_compute_commission', store=True, tracking=True, translate=True)
    # commission_vat = fields.Monetary(string='Commissions VAT', currency_field='company_currency', tracking=True, translate=True)
    # total_commission = fields.Monetary(string='Initial payment', currency_field='company_currency')
    # tax_rate = fields.Many2many('account.tax','crm_taxes_rel', 'crm_id', 'tax_id', tracking=True, translate=True)
    # fixed = fields.Boolean(string='Fixed', default=True, tracking=True, translate=True)
    # fixed_rate = fields.Float('Fixed rate', (2,6), tracking=True, translate=True)
    # base_rate = fields.Char(string='Base rate', tracking=True, translate=True)
    # variance = fields.Char(string='Variance', tracking=True, translate=True)
    # current_rate = fields.Float(string='Current rate', tracking=True, translate=True, compute='_compute_current_rate', store=True)
    # days = fields.Integer(string='Days', compute='_compute_days', store=True, tracking=True, translate=True)
    # amount_delivered = fields.Monetary(string='Amount delivered', currency_field='company_currency', tracking=True, translate=True)
    # total_available = fields.Monetary(string='Total available', currency_field='company_currency', compute='_compute_total_available', store=True, tracking=True, translate=True)
    # total_willing = fields.Monetary(string='Total willing', currency_field='company_currency', tracking=True, translate=True )

    # conciliation_lines_ids = fields.Many2many('extenss.credit.conciliation_lines', 'crm_lines_rel', 'crm_id', 'lines_id', string='Payment', domain=lambda self:[('type_rec', '!=', 'pi')])#,  default=_default_conciliation)#,'crm_con_rel', 'crm_id', 'con_id'
    # con_lines_ids = fields.Many2many('extenss.credit.conciliation_lines', 'crm_lines_rel', 'crm_id', 'lines_id', string='Payment', domain=lambda self:[('type_rec', '!=', 'di')])#domain=lambda self:[('type_rec', '=', 'pi')
    #flag_dispersion = fields.Boolean(string='Dispersion', default=False, tracking=True, translate=True)

    # company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    # company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    #lineff_ids = fields.One2many('crm.lead', 'lineff_id', string=' ')

    # @api.depends('amount_financed')
    # def _compute_total_available(self):
    #     for reg in self:
    #         reg.total_available = reg.amount_ff - reg.total_willing

    ####Metodo para Pago inicial
    # def action_apply_payment(self):
    #     print('entra a metodo')
    #     list_data = []
    #     regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'pay_initial')])
    #     if regs_conf:
    #         for reg_conf in regs_conf:
    #             for reg_events in reg_conf.event_id:
    #                 event_key = reg_events.event_key
    #                 #for reg_order in self.sale_order_ids:
    #                 for lines in self.con_lines_ids:#self.conciliation_lines_ids:
    #                     if self.total_commission == abs(lines.amount) and self.partner_id == lines.customer:
    #                         print('entra ')
    #                         list_data.append(lines.customer.id)
    #                         list_data.append(abs(lines.amount))
    #                         list_data.append(self.productid.id)
    #                         list_data.append(event_key)
    #                         self.env['extenss.credit'].create_records(list_data)
    #                         list_data = []
    #                         lines.status = 'applied'
    #                         lines.check = True
    #                         lines.type_rec = 'pi'
    #                         #self.stage_id = self.env['crm.stage'].search([('sequence', '=', '6')]).id
    #                         self.flag_initial_payment = True
    #     else:
    #         raise ValidationError(_('Not exist record in Configuration in Datamart'))

    # def action_apply_dispersion(self):
    #     #print('entra a metodo')
    #     list_data = []
    #     regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'dispersion')])
    #     if regs_conf:
    #         for reg_conf in regs_conf:
    #             for reg_events in reg_conf.event_id:
    #                 event_key = reg_events.event_key
    #                 #for reg_order in self.sale_order_ids:
    #                 for lines in self.conciliation_lines_ids:
    #                     if self.amount_delivered == abs(lines.amount) and self.partner_id == lines.customer:
    #                         print('entra ')
    #                         list_data.append(lines.customer.id)
    #                         list_data.append(abs(lines.amount))
    #                         list_data.append(self.productid.id)
    #                         list_data.append(event_key)
    #                         self.env['extenss.credit'].create_records(list_data)
    #                         list_data = []
    #                         lines.status = 'applied'
    #                         lines.check = True
    #                         lines.type_rec='di'
    #                         #self.stage_id = self.env['crm.stage'].search([('sequence', '=', '6')]).id
    #                         self.flag_dispersion = True
    #     else:
    #         raise ValidationError(_('Not exist record in Configuration in Datamart'))

# class ExtenssProvisions(models.Model):
#     _inherit = 'crm.lead'

#     lineff_id = fields.Many2one('crm.lead', string='Lineff Id')
#     name = fields.Char(string='Name')
#     catlg_product = fields.Many2one('extenss.product.template', string='Product', domain="[('credit_type.shortcut', '=', product_name)]")

#     def action_create_provision(self):
#         self.create({
#             'lineff_id': self.id,
#             'product_name': 'ff',
#             'catlg_product': 2,#7
#             'stage_id': self.env['crm.stage'].search([('sequence', '=', '5')]).id,
#             'partner_id': self.partner_id.id,
#             'capacity': self.capacity,
#             'tax_rate': self.tax_rate,
#             'fixed_rate': self.fixed_rate,
#             'current_rate': self.current_rate,
#         })

# class ExtenssCreditConciliation(models.Model):
#     _inherit = 'extenss.credit.conciliation'

#     type_conciliation = fields.Selection(selection_add=[('pi', 'PI'),], default='dn', string='Type', tracking=True, translate=True)

class ExtenssCreditConciliationLines(models.Model):
    _inherit = 'extenss.credit.conciliation_lines'
    _description = 'Conciliation Lines'

#     conciliation_credit_id = fields.Many2one('extenss.credit', string='Credit_id', ondelete='cascade', tracking=True, translate=True)
#     conciliation_lines_id = fields.Many2one('crm.lead', string='CRM id', ondelete='cascade', tracking=True, translate=True)
#     conciliation_id = fields.Many2one('extenss.credit.conciliation', string='Conciliation', ondelete='cascade', tracking=True, translate=True)
    type_rec = fields.Selection(selection_add=[('pi', 'PI'),('di','DI'),])
#     status = fields.Selection(string='Status', default='pending', tracking=True, translate=True)
