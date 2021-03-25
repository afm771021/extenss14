from odoo import fields, models, exceptions, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, UserError, ValidationError
import base64
import math
import re

PROD_NAME = [
    ('af','Arrendamiento Financiero'),
    ('ap','Arrendamiento Puro'),
    ('cs','Crédito Simple'),
    ('DN','Descuento Nómina'),
    ('LFF','Apertura de Factoraje Financiero'),
    ('ff', 'Factoraje Financiero')]

class ExtenssRequestDestination(models.Model):
    _name =  'extenss.request.destination'
    _order = 'name'
    _description = 'Destination loan'

    name = fields.Char(string='Destination loan', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssRequestSalesChannelId(models.Model):
    _name = 'extenss.request.sales_channel_id'
    _order = 'name'
    _description ='Sales channel'

    name = fields.Char(string='Sales channel', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssRequestCategoryAct(models.Model):
    _name = 'extenss.request.category_act'
    _order = 'name'
    _description = 'Category'

    name = fields.Char(strig='Category', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssRequestCategoryPas(models.Model):
    _name = 'extenss.request.category_pas'
    _order = 'name'
    _description = 'Category'

    name = fields.Char(strig='Category', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssRequestHipoteca(models.Model):
    _name = 'extenss.request.hipoteca'
    _order = 'name'
    _description = 'Tipo de hipoteca'

    name = fields.Char(string='Tipo de hipoteca', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssRequestTipoIngreso(models.Model):
    _name = 'extenss.request.tipo_ingreso'
    _order = 'name'
    _description = 'Tipo de ingreso'

    name = fields.Char(string='Tipo de ingreso', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssRequestTipoGasto(models.Model):
    _name = 'extenss.request.tipo_gasto'
    _order = 'name'
    _description = 'Tipo de gasto'

    name = fields.Char(string='Tipo de gasto', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssRequestFrecuencia(models.Model):
    _name = 'extenss.request.frecuencia'
    _order = 'name'
    _description = 'Frecuencia'

    name = fields.Char(string='Frequency', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssRequestBase(models.Model):
    _name = 'extenss.request.base'
    _order = 'name'
    _description = 'Base'

    name = fields.Char(string='Base', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class Lead(models.Model):
    _inherit = "crm.lead"

    @api.constrains('owners_phone')
    def _check_prin_phone(self):
        for reg in self:
            if not reg.owners_phone == False:
                digits1 = [int(x) for x in reg.owners_phone if x.isdigit()]
                if len(digits1) != 10:
                    raise ValidationError(_('The principal phone must be a 10 digits'))
    
    @api.constrains('months_residence')
    def _check_years(self):
        for reg_years in self:
            if reg_years.months_residence > 999:
                raise ValidationError(_('The Years residence must be a 3 digits'))

    @api.constrains('stage_id')
    def _check_stage_id(self):
        if self.stage_id.id == self.env['crm.stage'].search([('sequence', '=', '2')]).id:
            #self.validate_quotations()
            if self.flag_validated == False:
                raise ValidationError(_('Not validated or missing information'))
            #self.validations()### Se comenta esta validacion ya que se realiza el llamado de este metodo en el boton de enviar
            self.user_send_req = self.env.user.id
            #self.stage_id =  2
        if self.stage_id.id != self.env['crm.stage'].search([('sequence', '=', '6')]).id and self.btn_active == False:
            raise UserError('It is not allowed to return the stage')

    @api.constrains('name')
    def _copy_data(self):
        self.ref_number = self.name + '-S'

    @api.constrains('amount_ff')
    def _validate_amount_ff(self):
        if self.product_name == 'LFF':
            if self.lineff_id:
                if self.amount_ff > self.lineff_id.amount_ff:
                    raise UserError('The amount is greater than the amount of the opening request')
        if self.product_name == 'ff':
            if self.lineff_id:
                if self.amount_ff > self.lineff_id.total_available:
                    raise UserError('The amount is greater than the amount of the opening request, the available amount is: %s' % self.lineff_id.total_available)

    @api.constrains('init_date')
    def _validate_init_date(self):
        if self.lineff_id:
            if self.init_date and self.invoice_date:
                if self.init_date < self.lineff_id.init_date:
                    raise UserError('The start date must be within the range of the application start date and invoice date')
                if self.invoice_date > self.lineff_id.invoice_date:
                    raise UserError('The invoice date must be less than the invoice date of the request')
        else:
            if self.init_date and self.invoice_date:
                if self.init_date > self.invoice_date:
                    raise UserError('The initial date must be less than the invoice date')

    @api.constrains('invoice_date')
    def _validate_invoice_date(self):
        if self.lineff_id:
            if self.init_date and self.invoice_date:
                if self.init_date < self.lineff_id.init_date:
                    raise UserError('The start date must be within the range of the application start date and invoice date')
                if self.invoice_date > self.lineff_id.invoice_date:
                    raise UserError('The invoice date must be less than the invoice date of the request')
        else:
            if self.init_date and self.invoice_date:
                if self.init_date > self.invoice_date:
                    raise UserError('The initial date must be less than the invoice date')

    def open_docs_count(self):
        domain = ['|', ('lead_id', '=', [self.id]), ('partner_id', '=', self.partner_id.id)]
        return {
            'name': _('Documents'),
            'view_type': 'kanban',
            'domain': domain,
            'res_model': 'documents.document',
            'type': 'ir.actions.act_window',
            #'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'kanban,tree,form',
            'context': "{'default_folder_id': %s}" % self.ids
        }

    def get_document_count(self):
        count = self.env['documents.document'].search_count(['|', ('lead_id', '=', self.id), ('partner_id', '=', self.partner_id.id)])
        self.document_count = count

    def action_send_sale(self):
        if self.product_name == 'LFF' or self.product_name == 'ff':
            self.validations_ff()
        else:
            self.validations()
        self.validatedocs()
        self.send_crm = 'Sending'
        self.user_send_req = self.env.user.id
        self.stage_id = self.env['crm.stage'].search([('sequence', '=', '2')]).id

    def action_approved_sale(self):
        if self.product_name == 'LFF' or self.product_name == 'ff':
            if self.stage_id.id == self.env['crm.stage'].search([('sequence', '=', '5')]).id:
                if self.amount_ff == 0 and self.product_name == 'ff':
                    raise ValidationError(_('Enter the amount for disposition'))
                if self.flag_initial_payment == False:
                    if self.total_commission > 0:    
                        raise ValidationError(_('Initial payment is missing'))
                    self.flag_initial_payment = True
                if self.flag_dispersion == False and self.product_name == 'ff':
                    raise ValidationError(_('Dispersion is missing'))
                self.validatedocs()
                if self.product_name == 'LFF':
                    self.validate_docs_ff()
                    self.send_notification_ff()
                self.stage_id = self.env['crm.stage'].search([('sequence', '=', '6')]).id

            if self.stage_id.id == self.env['crm.stage'].search([('sequence', '=', '4')]).id:
                self.stage_id = self.env['crm.stage'].search([('sequence', '=', '5')]).id

            if self.stage_id.id == self.env['crm.stage'].search([('sequence', '=', '3')]).id:
                if self.flag_documents == False:
                    raise ValidationError(_('Please download the documents to continue'))
                self.stage_id = self.env['crm.stage'].search([('sequence', '=', '4')]).id
        else:
            self.user_send_req = self.env.user.id
            if self.stage_id.id == self.env['crm.stage'].search([('sequence', '=', '5')]).id:
                #self.action_duplicate()
                af = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')]).af
                ap = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')]).ap
                cs = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')]).cs
                dn = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')]).dn
                if af == True or ap == True:
                    if self.flag_initial_payment == True:
                        self.stage_id = self.env['crm.stage'].search([('sequence', '=', '6')]).id
                    else:
                        raise ValidationError(_('Initial payment is missing'))
                elif cs == True:
                    self.stage_id = self.env['crm.stage'].search([('sequence', '=', '6')]).id
                elif dn == True:
                    if self.flag_dispersion == True:
                        self.stage_id = self.env['crm.stage'].search([('sequence', '=', '6')]).id
                    else:
                        raise ValidationError(_('Dispersion is missing'))
            if self.stage_id.id == self.env['crm.stage'].search([('sequence', '=', '4')]).id:
                self.send_notification()
                self.stage_id = self.env['crm.stage'].search([('sequence', '=', '5')]).id
            if self.stage_id.id == self.env['crm.stage'].search([('sequence', '=', '3')]).id:
                if self.flag_documents == False:
                    raise ValidationError(_('Please download the documents to continue'))
                self.stage_id = self.env['crm.stage'].search([('sequence', '=', '4')]).id

    def action_rejected_sale(self):
        self.user_refuse_req = self.env.user.id
        self.active = False
    
    def action_send_activation(self):
        if self.stage_id == 3:
            request_ids = self.env['sign.request.item'].search([('partner_id', '=', self.partner_id.id)]).mapped('sign_request_id')
            for ref in request_ids:
                doc_name=ref.reference[-10:-4]
                if doc_name == quotations.name :
                    if ref.state != 'signed' :
                        raise ValidationError(_('Unsigned document %s') % ref.reference)
                    self.stage_id =  4
    
    def create_account(self):
        rec_accnt = self.env['extenss.credit.account']
        exist_rec = rec_accnt.search([('customer_id', '=', self.partner_id.id)])
        if not exist_rec:
            accnt_id = rec_accnt.create({
                'customer_id': self.partner_id.id,
                'date_opening': datetime.now().date(),
                'status': 'active',
                'balance': 0,
            })
            return accnt_id.id
        else:
            return exist_rec.id

    def action_duplicate(self):
        id_cuenta = self.create_account()

        record_new = self.env['extenss.credit']
        quotations_sale = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')])
        for rec_sale in quotations_sale:
            di = rec_sale.total_deposit/(1+(rec_sale.tax_id/100))
            itd = di*(rec_sale.tax_id/100)
            gd = rec_sale.total_guarantee/(1+(rec_sale.tax_id/100))
            gdv = gd*(rec_sale.tax_id/100)

            commision_rec = self.env['extenss.request.commision']
            com_rec_porc = commision_rec.search([('sale_order_id', '=', rec_sale.id),('type_commision', '=', '0')])
            com_rec_amount = commision_rec.search([('sale_order_id', '=', rec_sale.id),('type_commision', '=', '1')])
            percent_rec_p = 0
            amount_rec_p = 0
            amount_rec_am = 0
            amount_rec_val = 0
            brv = 0
            for rec_porc in com_rec_porc:
                percent_rec_p += rec_porc.commision
                amount_rec_p += rec_porc.value_commision

            for rec_amount in com_rec_amount:
                amount_rec_am += rec_amount.commision
                amount_rec_val += rec_amount.value_commision

            ca = amount_rec_p/(1+(rec_sale.tax_id/100))
            cv = ca*(rec_sale.tax_id/100)

            ratif = amount_rec_val/(1+(rec_sale.tax_id/100))
            ratif_v = ratif*(rec_sale.tax_id/100)

            # reg_accnt = rec_accnt.search([('customer_id', '=', self.partner_id.id)])
            # for r in reg_accnt:
            #     id_cuenta = r.id

            if rec_sale.base_interest_rate == 'TIIE':
                base_rate_id = self.env['extenss.product.base_interest_rate'].search([('name', '=', rec_sale.base_interest_rate)])
                records_ird = self.env['extenss.product.interest_rate_date'].search([('base_interest_rate_id', '=', base_rate_id.id)])
                for reg in records_ird:
                    if datetime.now().date() == reg.date:
                        reg.interest_rate
                        brv = reg.interest_rate
                rt = 'Variable'
            else:
                rt = 'Fixed'

            itp = rec_sale.total_guarantee + rec_sale.total_deposit + amount_rec_val + amount_rec_p

            record_new.create({
                'customer_id': self.partner_id.id,
                'request_id': self.id,
                'product_id': rec_sale.product_id.id, #product_id.id
                'salesperson_id': self.user_id.id,
                'office_id': self.team_id.id,
                'anchor_id': rec_sale.fondeador.name,
                'bill_id': id_cuenta,
                'customer_type': self.partner_type,
                'amount_financed': rec_sale.amount,
                'term': rec_sale.term,
                'frequency': rec_sale.frequency_id.id,
                'vat_factor': rec_sale.tax_id,
                'rate_type': rt,
                'base_rate_type': rec_sale.base_interest_rate,
                'base_rate_value': brv,
                'differential': rec_sale.point_base_interest_rate,
                'interest_rate': rec_sale.interest_rate_value,
                'rate_arrears_interest': rec_sale.rate_arrears_interest,
                'factor_rate': rec_sale.factor_rate,
                'days_notice': rec_sale.days_pre_notice,
                'type_credit': rec_sale.credit_type.id,
                'hiring_date': rec_sale.date_start,
                'first_payment_date': rec_sale.date_first_payment,
                'purchase_option': rec_sale.purchase_option,
                'purchase_option_amount': rec_sale.purchase_option2,
                'order_id': rec_sale.id,
                'residual_value': rec_sale.residual_porcentage,
                'amount_residual_value': rec_sale.residual_value,
                'residual_value_rcal': rec_sale.residual_value,
                'total_deposit_income': rec_sale.total_deposit,
                'deposit_income': di,
                'income_tax_deposit': itd,
                'percentage_guarantee_deposit': rec_sale.guarantee_percentage,
                'guarantee_deposit': gd,
                'vat_guarantee_deposit': gdv,
                'total_guarantee_deposit': rec_sale.total_guarantee,
                'portfolio_type': 'vigente',
                'credit_status': 'active',
                'percentage_commission': percent_rec_p,
                'commission_amount': ca,
                'commission_vat': cv,
                'total_commission': amount_rec_p,
                'ratification': ratif,
                'ratification_vat': ratif_v,
                'total_ratification': amount_rec_val,
                'initial_total_payment': itp,
                'cs': rec_sale.cs,
                'af': rec_sale.af,
                'ap': rec_sale.ap,
                'dn': rec_sale.dn,
                'leased_team': rec_sale.description,
                'amount_si': rec_sale.amount_si,
                'tax_amount': rec_sale.tax_amount,
                'date_limit_pay': rec_sale.date_limit_pay,
                'calculation_base': rec_sale.calculation_base,
                'dispersion_date': datetime.now().date(),
                'days_transfer_past_due': rec_sale.days_past_due,
                'include_taxes': rec_sale.include_taxes,
                'frequency_days': rec_sale.frequency_id.days,
                'total_payment': rec_sale.total_payment,
                'number_pay_rest': rec_sale.number_pay_rest,
                'reference_number': self.name + '-C'
            })

            for amort in rec_sale.amortization_ids:
                amortization_ids = [(4, 0, 0)]
                data = {
                    'no_pay': amort.no_payment,
                    'expiration_date': amort.date_end,
                    'initial_balance': amort.initial_balance,
                    'capital': amort.capital,
                    'interest': amort.interest,
                    'iva_interest': amort.iva_interest,
                    'payment': amort.payment, 
                    'iva_capital': amort.iva_capital,
                    'total_rent': amort.total_rent,
                    'iva_rent': amort.iva_rent
                }
                amortization_ids.append((0, 0, data))
                record_ids = self.env['extenss.credit'].search([('order_id', '=', rec_sale.id)])
                for record in record_ids:
                    record.write({
                        'amortization_ids': amortization_ids
                    })

    def validatedocs(self):
        docs = self.env['documents.document'].search(['|', ('partner_id', '=', self.partner_id.id), ('lead_id', '=', self.id)])
        for reg_docs in docs:
            if not reg_docs.attachment_id:
                raise ValidationError(_('Attach the corresponding documents'))

    # def validate_quotations(self):
    #     count_sales = self.env['sale.order'].search_count([('opportunity_id', '=', self.id),('state', '=', 'sale')])
    #     if count_sales == 0 and self.product_name != 'LFF':
    #         raise ValidationError(_('Please add a quote'))

    def validations(self):
        if self.stage_id.id == self.env['crm.stage'].search([('sequence', '=', '2')]).id:
            #self.validate_quotations()
            count_sales = self.env['sale.order'].search_count([('opportunity_id', '=', self.id),('state', '=', 'sale')])
            if count_sales == 0 and self.product_name != 'LFF':
                raise ValidationError(_('Please add a quote'))

        # docs = self.env['documents.document'].search(['|', ('partner_id', '=', self.partner_id.id), ('lead_id', '=', self.id)])
        # for reg_docs in docs:
        #     if not reg_docs.attachment_id:
        #         raise ValidationError(_('Attach the corresponding documents'))

        quotations = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')])
        #if quotations:
        for reg in quotations:
            if not reg.signature:
                raise ValidationError(_('Missing the quote signature %s') % reg.name)

            if self.partner_type == 'company':
                if reg.product_id.financial_situation:
                    reg_fs = self.env['extenss.crm.lead.financial_sit'].search([('financial_id', '=', self.id)])
                    if not reg_fs:
                        raise ValidationError(_('Enter a record in Financial Situation tab'))
                    if reg_fs.activos_totales <= 0.0:
                        raise ValidationError(_('Enter data in the Assets tab in any of the sections'))
                    if reg_fs.pasivo_total_capital_contable <= 0.0:
                        raise ValidationError(_('Enter data in Liabilities tab in any of the sections'))
                    if not reg_fs.beneficios_ope_totales:
                        raise ValidationError(_('Enter data in Income statement tab in any of the sections'))
            if self.partner_type == 'person':
                if reg.product_id.endorsement:
                    cont_reg_av = 0
                    reg_pf = self.env['extenss.crm.personal_ref'].search([('personal_ref_id', '=', self.id)])
                    if not reg_pf:
                        raise ValidationError(_('Add an Aval type record in the Personal References tab'))
                    for r in reg_pf:
                        reg_p = self.env['extenss.customer.type_refbank'].search([('id', '=', r.type_reference_personal_ref.id)])
                        if reg_p.shortcut == 'AV':
                            cont_reg_av += 1
                    if cont_reg_av <= 0:
                        raise ValidationError(_('Enter a Endorsement type record in Personal references tab for quotation number %s') % reg.name)
                if reg.product_id.guarantee:
                    reg_w = self.env['extenss.crm.lead.ownership'].search([('ownership_id', '=', self.id)])
                    if not reg_w:
                        raise ValidationError(_('Enter a record in Ownership tab %s') % reg.name)
                if reg.product_id.socioeconomic_study:
                    reg_source = self.env['extenss.crm.lead.source_income'].search([('surce_id', '=', self.id)])
                    reg_exp = self.env['extenss.crm.lead.source_income'].search([('gasto_id', '=', self.id)])
                    if not reg_source:
                        raise ValidationError(_('Enter a record in Source income tab in the section of Income for quotation number %s') % reg.name)
                    if not reg_exp:
                        raise ValidationError(_('Enter a record in Source income tab in the section of Expenses for quotation number %s') % reg.name)
                if reg.product_id.beneficiaries:
                    cont_reg_bf = 0
                    reg_benef = self.env['extenss.crm.personal_ref'].search([('personal_ref_id', '=', self.id)])
                    if not reg_benef:
                        raise ValidationError(_('Add a beneficiary type record in the Personal References tab'))
                    for r in reg_benef:
                        reg_p = self.env['extenss.customer.type_refbank'].search([('id', '=', r.type_reference_personal_ref.id)])
                        if reg_p.shortcut == 'BF':
                            cont_reg_bf += 1
                    if cont_reg_bf <= 0:
                        raise ValidationError(_('Enter a Beneficiaries type record in Personal references tab for quotation number %s') % reg.name)
                if reg.product_id.financial_situation:
                    reg_pos = self.env['extenss.crm.lead.financial_pos'].search([('financial_pos_id', '=', self.id)])
                    reg_pas = self.env['extenss.crm.lead.financial_pos'].search([('financial_pas_id', '=', self.id)])
                    if not reg_pos:
                        raise ValidationError(_('Enter a record in Financial position tab in the section Assets for quotation number %s') % reg.name)
                    if not reg_pas:
                        raise ValidationError(_('Enter a record in Financial position tab in the section Passives for quotation number %s') % reg.name)

                if reg.product_id.patrimonial_relationship:
                    if self.total_resident <= 0.0:
                        raise ValidationError(_('Enter data in Residence profile tab for quotation number %s') % reg.name)
                if reg.product_id.obligated_solidary:
                    cont_reg_os = 0
                    reg_os = self.env['extenss.crm.personal_ref'].search([('personal_ref_id', '=', self.id)])
                    if not reg_os:
                        raise ValidationError(_('Add a record of type bound by solidarity in the Personal References tab'))
                    for r in reg_os:
                        reg_p = self.env['extenss.customer.type_refbank'].search([('id', '=', r.type_reference_personal_ref.id)])
                        if reg_p.shortcut == 'OS':
                            cont_reg_os += 1
                    if cont_reg_os <= 0:
                        raise ValidationError(_('Enter a Solidarity bound type record in Personal references tab for quotation number %s') % reg.name)
            self.flag_validated = True

    def validate_docs_rec(self):
        if self.product_name == 'ff':
            self.validate_docs_ff()
            self.release_ff()

        quotations = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')])
        for reg in quotations:
            #if self.stage_id.id == self.env['crm.stage'].search([('sequence', '=', '6')]).id:
            if len(reg.product_id.rec_docs_ids) == 0 :
                raise ValidationError(_('Must add Recruitment documents of product %s') % reg.product_id.name)
            request_ids = self.env['sign.request.item'].search([('partner_id', '=', self.partner_id.id)]).mapped('sign_request_id')
            for df in reg.product_id.rec_docs_ids:
                doc_fal = df.catalog_recru_docs.name
                for ref in request_ids:
                    doc_name=ref.reference[-10:-4]
                    if doc_name == reg.name :
                        doc_name=ref.reference[0:-11]
                        if doc_name == 'Contrato': doc_name='CON'
                        if doc_name == 'Pagare': doc_name='PAY'
                        if doc_name == df.catalog_recru_docs.shortcut :
                            doc_fal=''
                            doc_name=ref.reference[-10:-4]
                            if doc_name == reg.name :
                                if ref.state != 'signed' :
                                    raise ValidationError(_('Unsigned document %s') % ref.reference)
                if len(doc_fal) > 0:
                    raise ValidationError(_('Must add %s for order %s') % (doc_fal,reg.name))

            self.action_duplicate()
            self.btn_active = False

    def validate_docs_ff(self):
        docs_ids = self.env['sign.request.item'].search([('partner_id', '=', self.partner_id.id)]).mapped('sign_request_id')
        for df in self.catlg_product.rec_docs_ids:
            doc_fal = df.catalog_recru_docs.name
            for ref in docs_ids:
                doc_name=ref.reference[-19:-4]
                if doc_name == self.name:
                    doc_name=ref.reference[0:-20]
                    if doc_name == 'Contrato': doc_name='CON'
                    if doc_name == 'Pagare': doc_name='PAY'
                    if doc_name == df.catalog_recru_docs.shortcut :
                        doc_fal=''
                        doc_name=ref.reference[-19:-4]
                        if doc_name == self.name :
                            if ref.state != 'signed' :
                                raise ValidationError(_('Unsigned document %s') % ref.reference)
            if len(doc_fal) > 0:
                raise ValidationError(_('Must add %s for order %s') % (doc_fal,self.name))
            self.btn_active = False

    def action_autorize_sale(self):
        self.user_auth_req = self.env.user.id
        self.stage_id = self.env['crm.stage'].search([('sequence', '=', '3')]).id

    def action_refuse_sale(self):
        self.user_refuse_req = self.env.user.id

    def download_file_contrato(self):
        quotations = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')])
        for quotation in quotations:
            self.flag_documents = True
            return self.env.ref('extenss_request.contrato_extenss_request_sale_order').report_action(quotation)

    def download_file_pagare(self):
        quotations = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')])
        for quotation in quotations:
            self.flag_documents = True
            return self.env.ref('extenss_request.pagare_extenss_request_sale_order').report_action(quotation)

    def download_file_contrato_ff(self):
        self.flag_documents = True
        return self.env.ref('extenss_request.contrato_extenss_request').report_action(self.id)

    def download_file_pagare_ff(self):
        self.flag_documents = True
        return self.env.ref('extenss_request.pagare_extenss_request').report_action(self.id)

    def download_file_amortization(self):
        quotations = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')])
        for quotation in quotations:
            self.flag_documents = True
            return self.env.ref('extenss_request.report_extenss_request_sale_order').report_action(quotation)

    def action_get_offers(self):
        anualperiods = 0
        amount = self.payment_capacity
        # cred_type_prod = self.env['extenss.product.template'].search([('credit_type.shortcut', '=', 'DN')])
        # for cred in cred_type_prod:
        prods_ids = self.env['extenss.product.product'].search([('product_tmpl_id', '=', self.catlg_product.id)])
        for prod_id in prods_ids:
            print('prod_id.min_amount', prod_id.min_amount)
            print('prod_id.max_amount', prod_id.max_amount)

            term = prod_id.product_template_attribute_value_ids.term_extra
            anual_rate = prod_id.product_template_attribute_value_ids.interest_rate_extra
            frecuency = prod_id.product_template_attribute_value_ids.frequencies_extra.name
            name_prod = prod_id.name

            print(frecuency)

            if frecuency == 'Mensual':
                anualperiods = 12
            if frecuency == 'Quincenal':
                anualperiods = 24

            print(name_prod)
            print('term',term)
            print('anual_rate',anual_rate)
            #anual_rate = anual_rate/1.16
            anual_rate = anual_rate/100

            period_rate = anual_rate / anualperiods

            print(period_rate)
            op2 = (period_rate + 1).__pow__(term)
            print(op2)
            op3 = ((period_rate + 1).__pow__(term)) - 1
            print(op3)
            divisor = (op2 /op3) * period_rate
            print(divisor)
            max_cap = amount/divisor
            print(max_cap)

            max_cap = round(math.floor(max_cap), -3)

            self.write({
                'planned_revenue': max_cap,# * term,
            })

            if prod_id.min_amount < max_cap and prod_id.max_amount > max_cap:
                id_order = self.env['sale.order'].create({
                    'opportunity_id': self.id,
                    'partner_id': self.partner_id.id,
                    'product_id': prod_id.id,
                    'date_order': datetime.now().date(),
                    'date_start': datetime.now().date(),
                    'amount': max_cap,
                    'credit_type': prod_id.credit_type.id,
                    'min_age': prod_id.min_age,
                    'max_age': prod_id.max_age,
                    'min_amount': prod_id.min_amount,
                    'max_amount': prod_id.max_amount,
                    'hide': True,
                    'dn': True,
                    'hidepo': True,
                    'hidevr': True,
                    'calculation_base': prod_id.calculation_base.name,
                    'tax_id': prod_id.taxes_id.amount,
                    'rate_arrears_interest': prod_id.rate_arrears_interest,
                    'interest_rate_value': prod_id.interest_rate_extra,
                    'base_interest_rate': prod_id.base_interest_rate.name,
                    'point_base_interest_rate': prod_id.point_base_interest_rate,
                    'include_taxes': prod_id.include_taxes,
                    'term': prod_id.product_template_attribute_value_ids.term_extra,
                    'days_pre_notice': prod_id.days_pre_notice,
                    'days_past_due': prod_id.days_past_due,
                    'number_pay_rest': prod_id.number_pay_rest,
                    'frequency_id': prod_id.frequency_extra,
                })

                id_order.write({
                    'amount_total': max_cap,
                })
            else:
                raise ValidationError(_('The amount of the selected product exceeds the limits, please select another product'))
    
    def action_calculate_pc(self):
        self.payment_capacity = (self.perceptions - self.deductions) * .80

    def send_notification(self):
        offers = self.env['sale.order'].search([('opportunity_id', '=', self.id),('state', '=', 'sale')])
        for offer in offers:
            body_html = _('<p>Solicitud: %s ,</p><p>Cliente: %s ,</p><p>Monto: %s ,</p>') % (self.name, offer.partner_id.name, offer.amount)
            mail_value = {
                        'subject': 'Dispersion',
                        'body_html': body_html,
                        'email_to': self.email_from,
                        'email_from': 'odoo@odoo.com',
                        #'attachment_ids': [(6,0,[att.id])],
                    }
            self.env['mail.mail'].sudo().create(mail_value).send()

    def release_ff(self):
        id_cuenta = self.create_account()
        prods_ids = self.env['extenss.product.product'].search([('product_tmpl_id', '=', self.catlg_product.id)])
        for prod_id in prods_ids:
            id_prod = prod_id.id
            base = prod_id.calculation_base.name
            tax = prod_id.taxes_id.amount
            factor_rate = tax * prod_id.rate_arrears_interest

        credit_id = self.env['extenss.credit'].create({
            'customer_id': self.partner_id.id,
            'request_id': self.id,
            'product_id': id_prod,
            'salesperson_id': self.user_id.id,
            'office_id': self.team_id.id,
            'bill_id': id_cuenta,
            'amount_financed': self.amount_financed,
            'type_credit': self.catlg_product.credit_type.id,
            'rate_type': 'Fixed',
            'customer_type': self.partner_type,
            'ff': True,
            'dispersion_date': datetime.now().date(),
            'percentage_commission': self.commission_details,
            'commission_amount': self.commissions,
            'commission_vat': self.commission_vat,
            'total_commission': self.total_commission,
            'interest_rate': self.current_rate,
            'first_payment_date': self.invoice_date,
            'portfolio_type': 'vigente',
            'credit_status': 'active',
            'reference_number': self.name + '-C',
            'init_date': self.init_date,
            'invoice_date': self.invoice_date,
            'capacity': self.capacity,
            'days': self.days,
            'calculation_base': base,
            'vat_factor': tax,
            'factor_rate': factor_rate,
            'rate_arrears_interest': prod_id.rate_arrears_interest
        })

        self.env['extenss.credit.amortization'].create({
            'credit_id': credit_id.id,
            'no_pay': 1,
            'expiration_date': self.invoice_date,
            'initial_balance': self.amount_financed,
            'capital': self.amount_financed,
            'interest': self.interest,
            'iva_interest': self.interest_vat,
            'payment': self.amount_financed + self.interest + self.interest_vat,
            'penalty_amount': 0
        })
        self.btn_active = False

    def validations_ff(self):
        if not self.catlg_product:
            raise ValidationError(_('Enter the product for Opennig in Tab Financial Factoring Opening'))
        if self.amount_ff == 0 and self.catlg_product.credit_type.shortcut == 'LFF':
            raise ValidationError(_('Enter the amount for Opennig in Tab Financial Factoring Opening'))
        if self.amount_ff == 0 and self.catlg_product.credit_type.shortcut == 'ff':
            raise ValidationError(_('Enter the amount for disposition in Tab Financial Factoring Provision'))
        if self.partner_type == 'company':
            if self.catlg_product.financial_situation:
                reg_fs = self.env['extenss.crm.lead.financial_sit'].search([('financial_id', '=', self.id)])
                if not reg_fs:
                    raise ValidationError(_('Enter a record in Financial Situation tab'))
                if reg_fs.activos_totales <= 0.0:
                    raise ValidationError(_('Enter data in the Assets tab in any of the sections'))
                if reg_fs.pasivo_total_capital_contable <= 0.0:
                    raise ValidationError(_('Enter data in Liabilities tab in any of the sections'))
                if not reg_fs.beneficios_ope_totales:
                    raise ValidationError(_('Enter data in Income statement tab in any of the sections'))
        if self.partner_type == 'person':
            if self.catlg_product.endorsement:
                cont_reg_av = 0
                reg_pf = self.env['extenss.crm.personal_ref'].search([('personal_ref_id', '=', self.id)])
                if not reg_pf:
                    raise ValidationError(_('Add an Aval type record in the Personal References tab'))
                for r in reg_pf:
                    reg_p = self.env['extenss.customer.type_refbank'].search([('id', '=', r.type_reference_personal_ref.id)])
                    if reg_p.shortcut == 'AV':
                        cont_reg_av += 1
                if cont_reg_av <= 0:
                    raise ValidationError(_('Enter a Endorsement type record in Personal references tab for request number %s') % self.name)

            if self.catlg_product.guarantee:
                reg_w = self.env['extenss.crm.lead.ownership'].search([('ownership_id', '=', self.id)])
                if not reg_w:
                    raise ValidationError(_('Enter a record in Ownership tab %s') % self.name)

            if self.catlg_product.socioeconomic_study:
                reg_source = self.env['extenss.crm.lead.source_income'].search([('surce_id', '=', self.id)])
                reg_exp = self.env['extenss.crm.lead.source_income'].search([('gasto_id', '=', self.id)])
                if not reg_source:
                    raise ValidationError(_('Enter a record in Source income tab in the section of Income for request number %s') % self.name)
                if not reg_exp:
                    raise ValidationError(_('Enter a record in Source income tab in the section of Expenses for request number %s') % self.name)

            if self.catlg_product.beneficiaries:
                cont_reg_bf = 0
                reg_benef = self.env['extenss.crm.personal_ref'].search([('personal_ref_id', '=', self.id)])
                if not reg_benef:
                    raise ValidationError(_('Add a beneficiary type record in the Personal References tab'))
                for r in reg_benef:
                    reg_p = self.env['extenss.customer.type_refbank'].search([('id', '=', r.type_reference_personal_ref.id)])
                    if reg_p.shortcut == 'BF':
                        cont_reg_bf += 1
                if cont_reg_bf <= 0:
                    raise ValidationError(_('Enter a Beneficiaries type record in Personal references tab for request number %s') % self.name)

            if self.catlg_product.financial_situation:
                reg_pos = self.env['extenss.crm.lead.financial_pos'].search([('financial_pos_id', '=', self.id)])
                reg_pas = self.env['extenss.crm.lead.financial_pos'].search([('financial_pas_id', '=', self.id)])
                if not reg_pos:
                    raise ValidationError(_('Enter a record in Financial position tab in the section Assets for request number %s') % self.name)
                if not reg_pas:
                    raise ValidationError(_('Enter a record in Financial position tab in the section Passives for request number %s') % self.name)

            if self.catlg_product.patrimonial_relationship:
                if self.total_resident <= 0.0:
                    raise ValidationError(_('Enter data in Residence profile tab for request number %s') % self.name)

            if self.catlg_product.obligated_solidary:
                cont_reg_os = 0
                reg_os = self.env['extenss.crm.personal_ref'].search([('personal_ref_id', '=', self.id)])
                if not reg_os:
                    raise ValidationError(_('Add a record of type bound by solidarity in the Personal References tab'))
                for r in reg_os:
                    reg_p = self.env['extenss.customer.type_refbank'].search([('id', '=', r.type_reference_personal_ref.id)])
                    if reg_p.shortcut == 'OS':
                        cont_reg_os += 1
                if cont_reg_os <= 0:
                    raise ValidationError(_('Enter a Solidarity bound type record in Personal references tab for request number %s') % self.name)
        self.flag_validated = True

    destination_id = fields.Many2one('extenss.request.destination', string='Destination loan', tracking=True, translate=True)
    name = fields.Char(string='Request number', required=True, copy=False, readonly=True, index=True, tracking=True, translate=True, default=lambda self: _('New'))
    sales_channel_id = fields.Many2one('extenss.request.sales_channel_id', string='Sales channel', tracking=True, translate=True)
    create_date = fields.Date(string='Create date', readonly=True, tracking=True, translate=True)
    closed_date = fields.Date(string='Closed date', readonly=True, tracking=True, translate=True)
    #product_id = fields.Many2one('extenss.product.template', string='Product', tracking=True, translate=True)
    user_id = fields.Many2one('res.users')
    partner_type = fields.Selection('res.partner', related='partner_id.company_type')
    #team_id = fields.Char(string='Office')
    #planned_revenue = fields.Char(string='Request amount', translate=True)
    description = fields.Text(string='Comments', tracking=True, translate=True)
    document_count = fields.Integer("Documents", compute='get_document_count', tracking=True)
    #stage_id = fields.Many2one('crm.stage', string='Stage', tracking=True, translate=True)
    partner_id = fields.Many2one('res.partner', string='Customer', translate=True)
    send_crm = fields.Char(string='Request send', tracking=True, translate=True)
    user_send_req = fields.Many2one('res.users', string='User sending', tracking=True, translate=True)
    user_auth_req = fields.Many2one('res.users', string='Authorizing user', tracking=True, translate=True)
    user_refuse_req = fields.Many2one('res.users', string='User rejecting', tracking=True, translate=True)
    #Resident Profile
    housing_type_rp = fields.Selection([('rented', 'Rented'),('own','Own')], string='Housing type', tracking=True, translate=True)
    owners_name = fields.Many2one('res.partner', string='Owners name', tracking=True, translate=True)
    owners_phone = fields.Char(string='Owners phone', tracking=True, translate=True)
    montly_rent = fields.Monetary(string='Montly rent', currency_field='company_currency', tracking=True, translate=True)
    months_residence = fields.Integer(string='Months in Residence', tracking=True, translate=True)
    residency_profile = fields.Char(string='Residency profile', tracking=True, translate=True)

    rent = fields.Monetary(string='Rent', currency_field='company_currency', tracking=True, translate=True)
    first_mortage = fields.Monetary(string='First mortage', currency_field='company_currency', tracking=True, translate=True)
    another_finantiation = fields.Monetary(string='Another finantiation', currency_field='company_currency', tracking=True, translate=True)
    risk_insurance = fields.Monetary(string='Risk insurance', currency_field='company_currency', tracking=True, translate=True)
    real_state_taxes = fields.Monetary(string='Real state taxes', currency_field='company_currency', tracking=True, translate=True)
    mortage_insurance = fields.Monetary(string='Mortage insurance', currency_field='company_currency', tracking=True, translate=True)
    debts_cowners = fields.Monetary(string='Debts co-owners', currency_field='company_currency', tracking=True, translate=True)
    other = fields.Monetary(string='Other', currency_field='company_currency', tracking=True, translate=True)
    total_resident = fields.Monetary(string='Total', compute='_compute_total_resident', store=True, currency_field='company_currency')

    sequence_stage = fields.Integer('crm.stage', related="stage_id.sequence")
    flag_documents = fields.Boolean(string='Generating Documents', default=False, readonly=True, tracking=True, translate=True)
    flag_initial_payment = fields.Boolean(string='Inital Payment', default=False, tracking=True, translate=True)
    btn_active = fields.Boolean(string='Button active', default=True, tracking=True, translate=True)
    ref_number = fields.Char(string='Reference number', tracking=True, translate=True)

    product_name = fields.Selection(PROD_NAME, string='Product', tracking=True, translate=True)
    catlg_product = fields.Many2one('extenss.product.template', string='Product', domain="[('credit_type.shortcut', '=', product_name)]")#compute='_compute_catlg_prod', store=True
    perceptions = fields.Monetary(string='Perceptions', currency_field='company_currency', tracking=True, translate=True)
    deductions = fields.Monetary(string='Deductions', currency_field='company_currency', tracking=True, translate=True)
    payment_capacity = fields.Monetary(string='Payment capacity', currency_field='company_currency', tracking=True, translate=True)
    flag_dispersion = fields.Boolean(string='Dispersion', default=False, tracking=True, translate=True)

    ######Factoraje Financiero
    amount_ff = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    amount_out_vat = fields.Monetary(string='Amount without VAT', currency_field='company_currency', compute='_compute_amount', store=True, tracking=True, translate=True)
    purpose = fields.Char(string='Purpose', tracking=True, translate=True)
    description_purpose = fields.Char(string='Description purpose', tracking=True, translate=True)

    init_date = fields.Date(string='Init date', default=fields.Date.context_today, tracking=True, translate=True)
    invoice_date = fields.Date(string='Invoice date', tracking=True, translate=True)
    payment_method = fields.Char(string='Payment method', tracking=True, translate=True)
    capacity = fields.Float('% Capacity', (2,2), tracking=True, translate=True)
    amount_financed = fields.Monetary(string='Amount to be disposed', currency_field='company_currency', compute='_compute_amount_financed',store=True, tracking=True, translate=True)
    commission_details = fields.Float('Commission Details', (2,2), tracking=True, translate=True)
    commissions = fields.Monetary(string='Commissions', currency_field='company_currency', compute='_compute_commission', store=True, tracking=True, translate=True)
    commission_vat = fields.Monetary(string='Commissions VAT', currency_field='company_currency', tracking=True, translate=True)
    total_commission = fields.Monetary(string='Initial payment', currency_field='company_currency', compute='_compute_total_commission', store=True, tracking=True, translate=True)
    tax_rate = fields.Many2many('account.tax','crm_taxes_rel', 'crm_id', 'tax_id', compute='_compute_catlg_product', store=True, tracking=True, translate=True)
    fixed = fields.Boolean(string='Fixed', default=True, tracking=True, translate=True)
    fixed_rate = fields.Float('Fixed rate', (2,2), tracking=True, translate=True)
    base_rate = fields.Char(string='Base rate', tracking=True, translate=True)
    variance = fields.Char(string='Variance', tracking=True, translate=True)
    current_rate = fields.Float(string='Current rate', tracking=True, translate=True, compute='_compute_current_rate', store=True)
    days = fields.Integer(string='Days', compute='_compute_days', store=True, tracking=True, translate=True)

    amount_delivered = fields.Monetary(string='Amount delivered', currency_field='company_currency', compute='_compute_amount_delivered', store=True, tracking=True, translate=True)
    total_available = fields.Monetary(string='Total available', currency_field='company_currency', compute='_compute_total_available', store=True, tracking=True, translate=True)
    total_willing = fields.Monetary(string='Total willing', currency_field='company_currency', compute='_compute_total_willing', store=True, tracking=True, translate=True )

    interest = fields.Monetary(string='Interest', currency_field='company_currency', compute='_compute_interest', store=True, tracking=True, translate=True)
    interest_vat = fields.Monetary(string='Interest VAT', currency_field='company_currency', compute='_compute_interest_vat', store=True, tracking=True, translate=True)
    total_payment = fields.Monetary(string='Total payment', currency_field='company_currency', compute='_compute_total_payment', store=True, tracking=True, translate=True)

    assignor = fields.Many2one('res.partner', string='Assignor', tracking=True, translate=True)
    factoring_company = fields.Many2one('res.company', string='Factoring company', tracking=True, translate=True)
    assigned = fields.Many2one('res.partner', string='Assigned', tracking=True, translate=True)
    contract_number = fields.Char(string='Contract number', tracking=True, translate=True)
    credit_status = fields.Selection(related='credit_ids.credit_status')

    conciliation_lines_ids = fields.Many2many('extenss.credit.conciliation_lines', 'crm_lines_rel', 'crm_id', 'lines_id', string='Payment', domain=lambda self:[('type_rec', '!=', 'pi')])#,  default=_default_conciliation)#,'crm_con_rel', 'crm_id', 'con_id'
    con_lines_ids = fields.Many2many('extenss.credit.conciliation_lines', 'crm_lines_rel', 'crm_id', 'lines_id', string='Payment', domain=lambda self:[('type_rec', '!=', 'di')])

    ##Product DN
    sale_order_ids = fields.One2many('sale.order', 'opportunity_id', string='Orders', domain=lambda self:[('state','=','sale')])
    af_s = fields.Boolean(related='sale_order_ids.af')
    ap_s = fields.Boolean(related='sale_order_ids.ap')
    cs_s = fields.Boolean(related='sale_order_ids.cs')
    amount = fields.Monetary(related='sale_order_ids.amount', currency_field='company_currency')
    dn_s = fields.Boolean(related='sale_order_ids.dn')
    productid = fields.Many2one(related='sale_order_ids.product_id')
    ####
    flag_validated = fields.Boolean(string='Validated', default=False, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    fin_sit_ids = fields.One2many('extenss.crm.lead.financial_sit', 'financial_id', string=' ', tracking=True)
    fin_pos_ids = fields.One2many('extenss.crm.lead.financial_pos', 'financial_pos_id', string=' ')
    fin_pas_ids = fields.One2many('extenss.crm.lead.financial_pos', 'financial_pas_id', string=' ')
    owner_ids = fields.One2many('extenss.crm.lead.ownership', 'ownership_id', string=' ')
    surce_ids = fields.One2many('extenss.crm.lead.source_income', 'surce_id', string=' ')
    exp_ids = fields.One2many('extenss.crm.lead.source_income', 'gasto_id', string=' ')
    personal_ref_ids = fields.One2many('extenss.crm.personal_ref', 'personal_ref_id', string=' ')
    lineff_ids = fields.One2many('crm.lead', 'lineff_id', string=' ')
    credit_ids = fields.One2many('extenss.credit', 'request_id', string=' ')

    @api.depends('catlg_product')
    def _compute_catlg_product(self):
        self.tax_rate = self.catlg_product.taxes_id

        for reg in self:
            if reg.catlg_product.credit_type.shortcut == 'LFF' or reg.catlg_product.credit_type.shortcut == 'ff':
                name = self.env['extenss.product.cat_docs'].search([('doc_id', '=', reg.catlg_product.id)])
                for reg in name:
                    namedoc = self.env['extenss.product.type_docs'].search([('id', '=', reg.catalogo_docs.id)])
                    for regname in namedoc:
                        self.rel = regname.related_to
                        self.nombre = regname.name
                        if self.rel == 'contact':
                            self.contacto = self.partner_id.id
                            self.solicitud = ''
                        if self.rel == 'request':
                            self.solicitud = self.id
                            self.contacto = ''

                        existe = self.env['documents.document'].search(['|', ('partner_id', '=', self.partner_id.id), ('lead_id', '=', self.id), ('doc_prod_id', '=', regname.id)])
                        existe_cliente = self.env['documents.document'].search([('partner_id', '=', self.partner_id.id),('doc_prod_id', '=', regname.id)])

                        if not existe and not existe_cliente:
                            document = self.env['documents.document'].create({
                                'name': namedoc.name,
                                'type': 'empty',
                                'folder_id': 1,
                                'owner_id': self.env.user.id,
                                'partner_id': self.contacto if self.contacto else False,#self.partner_id.id if self.partner_id.id else False,
                                'res_id': 0,
                                'res_model': 'documents.document',
                                'lead_id': self.solicitud,#self.opportunity_id.id
                                'doc_prod_id': regname.id
                        })

    @api.depends('amount_financed','total_willing')
    def _compute_total_available(self):
        for reg in self:
            reg.total_available = reg.amount_ff - reg.total_willing

    @api.depends('amount_ff')
    def _compute_amount(self):
        for reg in self:
            rate_percent = (reg.tax_rate.amount/100)+1
            reg.amount_out_vat = reg.amount_ff / rate_percent

    @api.depends('amount_ff','capacity')
    def _compute_amount_financed(self):
        for reg in self:
            rate_percent = (reg.capacity/100)+1
            reg.amount_financed = reg.amount_out_vat / rate_percent

    @api.depends('amount_financed')
    def _compute_total_willing(self):
        sum_amount = 0
        for reg_h in self:
            if self.lineff_id:
                regs = self.env['crm.lead'].search([('id', '=', self.lineff_id.id)])
                for dat in regs:
                    sum_amount = sum_amount + reg_h.amount_ff + dat.total_willing#amount_financed

                dat.total_willing = sum_amount

    @api.depends('fixed_rate','amount_ff')
    def _compute_current_rate(self):
        for reg in self:
            reg.current_rate = reg.fixed_rate

    @api.depends('commission_details','amount_ff','capacity')
    def _compute_commission(self):
        for reg in self:
            rate_percent = (reg.tax_rate.amount/100)
            if reg.product_name == 'LFF':
                reg.commissions = reg.amount_financed * (reg.commission_details/100)
                reg.commission_vat = reg.commissions * rate_percent
            if reg.product_name == 'ff':
                reg.commissions = ((reg.commission_details/ 3600) * reg.amount_financed) * reg.days
                reg.commission_vat = reg.commissions * rate_percent

    @api.depends('init_date','invoice_date')
    def _compute_days(self):
        for reg in self:
            if reg.init_date and reg.invoice_date:
                reg.days = (reg.invoice_date - reg.init_date).days
            else:
                reg.days = 0

    @api.depends('amount_financed','days')
    def _compute_interest(self):
        for reg in self:
            if reg.amount_financed and reg.days:
                rate = reg.current_rate / 360
                reg.interest = ((reg.amount_financed * rate)/360) * reg.days
    
    @api.depends('amount_financed','interest')
    def _compute_interest_vat(self):
        for reg in self:
            if reg.interest and reg.tax_rate:
                reg.interest_vat = reg.interest * (reg.tax_rate.amount/100)

    @api.depends('amount_financed','interest','interest_vat')
    def _compute_total_payment(self):
        for reg in self:
            if reg.interest and reg.interest_vat:
                reg.total_payment = reg.interest + reg.interest_vat

    @api.depends('amount_financed','capacity','amount_ff','commissions')
    def _compute_amount_delivered(self):
        for reg in self:
            if reg.amount_ff and reg.amount_financed:
                reg.amount_delivered = reg.amount_financed - reg.commissions - reg.commission_vat

    @api.depends('commissions','commission_vat')
    def _compute_total_commission(self):
        for reg in self:
            reg.total_commission = reg.commissions + reg.commission_vat

    @api.depends('rent','first_mortage','another_finantiation','risk_insurance','real_state_taxes','mortage_insurance','debts_cowners','other')
    def _compute_total_resident(self):
        for reg in self:
            reg.total_resident = reg.rent + reg.first_mortage + reg.another_finantiation + reg.risk_insurance + reg.real_state_taxes + reg.mortage_insurance + reg.debts_cowners + reg.other

    @api.model
    def create(self, reg):
        if reg:
            if reg.get('name', _('New')) == _('New'):
                reg['name'] = self.env['ir.sequence'].next_by_code('crm.lead') or _('New')
            result = super(Lead, self).create(reg)
            return result

    ###Pago Inicial 
    def action_apply_payment(self):
        prods_ids = self.env['extenss.product.product'].search([('product_tmpl_id', '=', self.catlg_product.id)])
        for prod_id in prods_ids:
            id_prod = prod_id.id

        list_data = []
        regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'pay_initial')])
        if regs_conf:
            for reg_conf in regs_conf:
                for reg_events in reg_conf.event_id:
                    event_key = reg_events.event_key
                    for lines in self.con_lines_ids:
                        if self.total_commission == abs(lines.amount) and self.partner_id == lines.customer:
                            list_data.append(lines.customer.id)
                            list_data.append(abs(lines.amount))
                            list_data.append(id_prod)
                            list_data.append(event_key)
                            self.env['extenss.credit'].create_records(list_data)
                            list_data = []
                            lines.status = 'applied'
                            lines.check = True
                            lines.type_rec = 'pi'
                            self.flag_initial_payment = True
        else:
            raise ValidationError(_('Not exist record in Configuration in Datamart'))

    ##Dispersion
    def action_apply_dispersion(self):
        if self.catlg_product == 'ff':
            prods_ids = self.env['extenss.product.product'].search([('product_tmpl_id', '=', self.catlg_product.id)])
            for prod_id in prods_ids:
                id_prod = prod_id.id
        else:
            id_prod = self.productid.id

        list_data = []
        regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'dispersion')])
        if regs_conf:
            for reg_conf in regs_conf:
                for reg_events in reg_conf.event_id:
                    event_key = reg_events.event_key
                    for lines in self.conciliation_lines_ids:
                        if self.product_name == 'ff':
                            amount = self.amount_delivered
                        if self.product_name == 'DN':
                            amount = self.amount
                        if amount == abs(lines.amount) and self.partner_id == lines.customer:
                            list_data.append(lines.customer.id)
                            list_data.append(abs(lines.amount))
                            list_data.append(id_prod)
                            list_data.append(event_key)
                            self.env['extenss.credit'].create_records(list_data)
                            list_data = []
                            lines.status = 'applied'
                            lines.check = True
                            lines.type_rec='di'
                            self.flag_dispersion = True
        else:
            raise ValidationError(_('Not exist record in Configuration in Datamart'))

    ####Metodo para Pago inicial
    def action_apply_payment_af(self):
        list_data = []
        regs_conf = self.env['extenss.datamart.configuration'].search([('concept', '=', 'pay_initial')])
        for reg_conf in regs_conf:
            for reg_events in reg_conf.event_id:
                event_key = reg_events.event_key
                for reg_order in self.sale_order_ids:
                    if reg_order.total_deposit > 0 and event_key == 120:
                        amount = reg_order.total_deposit
                    if reg_order.total_guarantee > 0 and event_key == 140:
                        amount = reg_order.total_guarantee
                    if reg_order.total_commision > 0 and event_key == 210:
                        amount = reg_order.total_commision

                    if amount > 0:
                        for lines in self.conciliation_lines_ids:
                            if self.partner_id == lines.customer:
                                list_data.append(lines.customer.id)
                                list_data.append(amount)
                                list_data.append(self.productid.id)
                                list_data.append(event_key)
                                #print(list_data)
                                self.env['extenss.credit'].create_records(list_data)
                                list_data = []
                                amount = 0
                                self.flag_initial_payment = True
                                lines.status = 'applied'

    def send_notification_ff(self):
        body_html = _('<p>Factoring company: %s ,</p><p>Assignor: %s ,</p>'
                        '<p>Assigned %s </p>') % (self.factoring_company.name, self.assignor.name, self.assigned.name)

        mail_value = {
            'subject': 'Financial Factoring Opening',
            'body_html': body_html,
            'email_to': self.email_from,
            'email_from': 'odoo@odoo.com',
            #'attachment_ids': [(6,0,[att.id])],
        }
        self.env['mail.mail'].sudo().create(mail_value).send()

class ExtenssProvisions(models.Model):
    _inherit = 'crm.lead'

    lineff_id = fields.Many2one('crm.lead', string='Lineff Id')

    def action_create_provision(self):
        if self.total_available > 0:
            self.create({
                'lineff_id': self.id,
                'product_name': 'ff',
                'catlg_product': self.catlg_product.product_child.id,
                'stage_id': self.env['crm.stage'].search([('sequence', '=', '5')]).id,
                'partner_id': self.partner_id.id,
                'capacity': self.capacity,
                'tax_rate': self.tax_rate,
                'fixed_rate': self.fixed_rate,
                'current_rate': self.current_rate,
                'invoice_date': self.invoice_date
            })
        else:
            raise ValidationError(_('No amount available to create more provisions'))

class ExtenssDocuments(models.Model):
    _inherit = "documents.document"

    lead_id = fields.Char(string="Lead Id")
    doc_prod_id = fields.Char(string="Document Prod Id")

class ExtenssCrmLeadFinancialSit(models.Model):
    _name = "extenss.crm.lead.financial_sit"
    _description = "Financial Situation"

    financial_id = fields.Many2one('crm.lead', tracking=True)#modelo padre
    date_fin_sit = fields.Date(string='Date', required=True, tracking=True, translate=True)
    #partner_name = fields.Char(string='Company', translate=True)
    partner_id = fields.Many2one('res.partner', string='Customer')#, default=lambda self: self.env.user.partner_id.id)#default=10)#default=lambda self: self.env.partner_id)#
    #partner_name = fields.Char(related='partner_id.name', string='Company', translate=True)
    base = fields.Many2one('extenss.request.base', string='Base', tracking=True, translate=True)
    frequency = fields.Many2one('extenss.request.frecuencia', string='Frequency', tracking=True, translate=True)
    description = fields.Char(string='Description', tracking=True, translate=True)
    #Assets
    efectivo = fields.Monetary(string='Cash', currency_field='company_currency', tracking=True, translate=True)
    cuentas_cobrar = fields.Monetary(string='Accounts receivable', currency_field='company_currency', tracking=True, translate=True)
    inventario = fields.Monetary(string='Inventory', currency_field='company_currency', tracking=True, translate=True)
    activo_adicional1_tipo = fields.Char(string='Additional asset 1 Type', tracking=True, translate=True)
    activo_adicional1_importe = fields.Monetary(string='Additional asset 1 Amount', currency_field='company_currency', tracking=True, translate=True)
    activo_adicional2_tipo = fields.Char(string='Additional asset 2 Type', translate=True)
    activo_adicional2_importe = fields.Monetary(string='Additional asset 2 Amount', currency_field='company_currency', tracking=True, translate=True)
    activo_otras_cuentas = fields.Monetary(string='Assets from other accounts', currency_field='company_currency', tracking=True, translate=True)
    total_activo_circulante = fields.Monetary(string='Total surrounding assets', currency_field='company_currency', compute='_compute_total_circulante', store=True, tracking=True, translate=True)

    activos_fijos = fields.Monetary(string='Fixed assets', currency_field='company_currency', tracking=True, translate=True)
    depreciacion = fields.Monetary(string='Depreciation', currency_field='company_currency', tracking=True, translate=True)
    activos_intangibles = fields.Monetary(string='Intangible assets', currency_field='company_currency', tracking=True, translate=True)
    total_activos_fijos = fields.Monetary(string='Total fixed assets', currency_field='company_currency', compute='_compute_total_af', store=True, tracking=True, translate=True)

    otros_activos = fields.Monetary(string='Other assets', currency_field='company_currency', tracking=True, translate=True)
    otro_activo_adicional = fields.Char(string='Other additional asset, asset type', tracking=True, translate=True)
    otro_activo_importe = fields.Monetary(string='Other additional asset, asset amount', currency_field='company_currency', tracking=True, translate=True)
    total_otros_activos = fields.Monetary(string='Total other assets', currency_field='company_currency', compute='_compute_total_oa', store=True, tracking=True, translate=True)

    activos_totales = fields.Monetary(string='Total assets', currency_field='company_currency', compute='_compute_total_activos', store=True, tracking=True, translate=True)
    verifica_importes = fields.Boolean(string='Check amounts', compute='_compute_flag_vi', store=True, default=False, readonly=True, tracking=True, translate=True)#(Activo=Pasivo+Capital)
    #Liabilities
    proveedores	= fields.Monetary(string='Providers', currency_field='company_currency', tracking=True, translate=True)
    pasivo_tipo = fields.Char(string='Type liabilities', tracking=True, translate=True)
    pasivo_importe = fields.Monetary(string='Liabilities amount', currency_field='company_currency', tracking=True, translate=True)
    parte_corto_plazo = fields.Monetary(string='Short-term share of long-term debt', currency_field='company_currency', tracking=True, translate=True)
    otro_pasivo_circulante = fields.Monetary(string='Other current liabilities', currency_field='company_currency', tracking=True, translate=True)
    pasivo_total_circulante = fields.Monetary(string='Total current liabilities', currency_field='company_currency', compute='_compute_pasivo_tc', store=True, tracking=True, translate=True)

    deuda_largo_plazo = fields.Monetary(string='Long-term debt', currency_field='company_currency', tracking=True, translate=True)
    deuda_adicional_actual_tipo	= fields.Char(string='Current additional debt type', tracking=True, translate=True)
    deuda_adicional_actual_importe = fields.Monetary(string='Current additional debt amount', currency_field='company_currency', tracking=True, translate=True)
    otro_pasivo_no_circulante = fields.Monetary(string='Other non-current liabilities', currency_field='company_currency', tracking=True, translate=True)
    pasivo_total_no_circulante	= fields.Monetary(string='Total non-current liabilities', currency_field='company_currency', compute='_compute_pasivo_tnc', store=True, tracking=True, translate=True)

    capital	= fields.Monetary(string='Capital', currency_field='company_currency', tracking=True, translate=True)
    capital_desembolso = fields.Monetary(string='Disbursement capital', currency_field='company_currency', tracking=True, translate=True)
    utilidades_perdidas_acumuladas = fields.Monetary(string='Accumulated profit (loss)', currency_field='company_currency', tracking=True, translate=True)
    utilidad_ejercicio = fields.Monetary(string='Profit for the year', currency_field='company_currency', tracking=True, translate=True)
    total_capital_contable = fields.Monetary(string='Total stockholders equity', currency_field='company_currency', compute='_compute_total_cc', store=True, tracking=True, translate=True)
    
    pasivo_total_capital_contable = fields.Monetary(string='Total liabilities and Stockholders equity', currency_field='company_currency', compute='_compute_pasivo_tcc', store=True, tracking=True, translate=True)

    #Income Statement
    ventas_netas = fields.Monetary(string='Net sales', currency_field='company_currency', tracking=True, translate=True)

    costo_ventas = fields.Monetary(string='Sales cost', currency_field='company_currency', tracking=True, translate=True)
    ganancia_bruta = fields.Monetary(string='Gross profit', currency_field='company_currency', compute='_compute_ganancia_bruta', store=True, tracking=True, translate=True)

    otros_ingresos_is = fields.Monetary(string='Other income', currency_field='company_currency', tracking=True, translate=True)
    ingresos_adicionales_tipo = fields.Char(string='Additional operating income, type of income', tracking=True, translate=True)
    ingresos_adicionales_importe = fields.Monetary(string='Additional operating income, amount of income', currency_field='company_currency', tracking=True, translate=True)
    gastos_ope_ad_1_tipo= fields.Char(string='Additional operating expenses 1, type of expenses', tracking=True, translate=True)
    gastos_ope_ad_1_importe = fields.Monetary(string='Additional operating expenses 1, amount of expenses', currency_field='company_currency', tracking=True, translate=True)
    gastos_ope_ad_2_tipo = fields.Char(string='Additional operating expenses 2, type of expenses', tracking=True, translate=True)
    gastos_ope_ad_2_importe = fields.Monetary(string='Additional operating expenses 2, amount of expenses', currency_field='company_currency', tracking=True, translate=True)
    beneficios_ope_totales = fields.Monetary(string='Total operating profit', currency_field='company_currency', compute='_compute_beneficios', store=True, tracking=True, translate=True)

    interes = fields.Monetary(string='Interest', currency_field='company_currency', tracking=True, translate=True)
    otros_gastos = fields.Monetary(string='Other expenses', currency_field='company_currency', tracking=True, translate=True)
    depreciación = fields.Monetary(string='Depreciation', currency_field='company_currency', tracking=True, translate=True)
    impuestos = fields.Monetary(string='Taxes', currency_field='company_currency', tracking=True, translate=True)
    utilidad_neta = fields.Monetary(string='Net profit', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    @api.depends('ventas_netas','costo_ventas')
    def _compute_ganancia_bruta(self):
        for reg in self:
            reg.ganancia_bruta = reg.ventas_netas - reg.costo_ventas

    @api.depends('otros_ingresos_is','ingresos_adicionales_importe','gastos_ope_ad_1_importe','gastos_ope_ad_2_importe')
    def _compute_beneficios(self):
        for reg in self:
            reg.beneficios_ope_totales = reg.otros_ingresos_is + reg.ingresos_adicionales_importe - reg.gastos_ope_ad_1_importe - reg.gastos_ope_ad_2_importe

    @api.depends('proveedores','pasivo_importe','parte_corto_plazo','otro_pasivo_circulante')
    def _compute_pasivo_tc(self):
        for reg in self:
            reg.pasivo_total_circulante = reg.proveedores + reg.pasivo_importe + reg.parte_corto_plazo + reg.otro_pasivo_circulante

    @api.depends('deuda_largo_plazo','deuda_adicional_actual_importe','otro_pasivo_no_circulante')
    def _compute_pasivo_tnc(self):
        for reg in self:
            reg.pasivo_total_no_circulante = reg.deuda_largo_plazo + reg.deuda_adicional_actual_importe + reg.otro_pasivo_no_circulante

    @api.depends('capital','capital_desembolso','utilidades_perdidas_acumuladas','utilidad_ejercicio')
    def _compute_total_cc(self):
        for reg in self:
            reg.total_capital_contable = reg.capital + reg.capital_desembolso + reg.utilidades_perdidas_acumuladas + reg.utilidad_ejercicio

    @api.depends('pasivo_total_circulante','pasivo_total_no_circulante','total_capital_contable')
    def _compute_pasivo_tcc(self):
        for reg in self:
            reg.pasivo_total_capital_contable = reg.pasivo_total_circulante + reg.pasivo_total_no_circulante + reg.total_capital_contable

    @api.depends('efectivo','cuentas_cobrar','inventario','activo_adicional1_importe','activo_adicional2_importe','activo_otras_cuentas')
    def _compute_total_circulante(self):
        for reg in self:
            reg.total_activo_circulante = reg.efectivo + reg.cuentas_cobrar + reg.inventario + reg.activo_adicional1_importe + reg.activo_adicional2_importe + reg.activo_otras_cuentas

    @api.depends('activos_fijos','depreciacion','activos_intangibles')
    def _compute_total_af(self):
        for reg in self:
            reg.total_activos_fijos = reg.activos_fijos + reg.depreciacion + reg.activos_intangibles
    
    @api.depends('otros_activos','otro_activo_importe')
    def _compute_total_oa(self):
        for reg in self:
            reg.total_otros_activos = reg.otros_activos + reg.otro_activo_importe

    @api.depends('total_activo_circulante','total_activos_fijos','total_otros_activos')
    def _compute_total_activos(self):
        for reg in self:
            reg.activos_totales = reg.total_activo_circulante + reg.total_activos_fijos + reg.total_otros_activos
    
    @api.depends('activos_totales','pasivo_total_capital_contable')
    def _compute_flag_vi(self):
        for reg in self:
            if reg.activos_totales == reg.pasivo_total_capital_contable:
                reg.verifica_importes = True
            if reg.activos_totales != reg.pasivo_total_capital_contable:
                reg.verifica_importes = False

class ExtenssCrmLeadFinancialPos(models.Model):
    _name = "extenss.crm.lead.financial_pos"
    _description = "Financial position"

    financial_pos_id = fields.Many2one('crm.lead')#modelo padre
    category_act = fields.Many2one('extenss.request.category_act', string='Category', tracking=True, translate=True)
    value_act = fields.Monetary(string='Value', currency_field='company_currency', tracking=True, translate=True)
    description_act = fields.Char(string='Description', tracking=True, translate=True)
    institution_act = fields.Many2one('res.bank', string='Institution', tracking=True, translate=True)#catalogo de bancos
    account_number_act = fields.Char(string='Account number', tracking=True, translate=True)
    verify_act = fields.Boolean(string='Verify', tracking=True, translate=True)
    #total_activos_act = fields.Monetary(string='Total activos', currency_field='company_currency', compute='_compute_total_act', store=True, tracking=True, translate=True)

    financial_pas_id = fields.Many2one('crm.lead')#modelo padre
    category_pas = fields.Many2one('extenss.request.category_pas', string='Category', tracking=True, translate=True)
    value_pas = fields.Monetary(string='Value', currency_field='company_currency', tracking=True, translate=True)
    pago_mensual_pas = fields.Monetary(string='Monthly payment', currency_field='company_currency', tracking=True, translate=True)
    description_pas = fields.Char(string='Description', tracking=True, translate=True)
    institution_pas = fields.Many2one('res.bank', string='Institution', tracking=True, translate=True)#catalogo de bancos
    account_number_pas = fields.Char(string='Account number', tracking=True, translate=True)
    tipo_hipoteca = fields.Many2one('extenss.request.hipoteca', string='Type of mortgage', tracking=True, translate=True)
    #total_pasivos = fields.Monetary(string='Total pasivos', currency_field='company_currency', compute='_compute_pasivos', store=True, tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class ExtenssCrmLeadSourceIncome(models.Model):
    _name = "extenss.crm.lead.source_income"
    _description = "Source of income"

    surce_id = fields.Many2one('crm.lead')
    tipo_ingreso = fields.Many2one('extenss.request.tipo_ingreso', string='Type of income', tracking=True, translate=True)
    importe_ing= fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    persona_ing	= fields.Many2one('res.partner', string='Person', tracking=True, translate=True)
    importe_mensual_ing = fields.Monetary(string='Monthly amount', currency_field='company_currency', tracking=True, translate=True)
    frecuencia_ing = fields.Many2one('extenss.request.frecuencia', string='Frequency', tracking=True, translate=True)#catalogo
    sujeto_impuestos_ing = fields.Boolean(string='Subject to tax', tracking=True, translate=True)
    comentarios_ing	= fields.Char(string='Comments', tracking=True, translate=True)
    total_ingresos = fields.Monetary(string='Total income', currency_field='company_currency', tracking=True, translate=True)
    
    gasto_id = fields.Many2one("crm.lead")
    tipo_gasto = fields.Many2one('extenss.request.tipo_gasto', string='Expense type', tracking=True, translate=True)
    importe_gas = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    persona_gas = fields.Many2one('res.partner', string='Person', tracking=True, translate=True)
    importe_mensual_gas = fields.Monetary(string='Monthly amount', currency_field='company_currency', tracking=True, translate=True)
    frecuencia_gas = fields.Many2one('extenss.request.frecuencia', string='Frequency', tracking=True, translate=True)	
    comentarios_gas = fields.Char(string='Comments', tracking=True, translate=True)
    total_gastos = fields.Monetary(string='Total spends', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class ExtenssCrmLeadOwnership(models.Model):
    _name = "extenss.crm.lead.ownership"
    _description = "Ownership"

    ownership_id = fields.Many2one('crm.lead')#modelo padre
    description_own = fields.Char(string='Description', tracking=True, translate=True)
    percentage_properties = fields.Float(string='Percentage in properties', digits=(2,6), tracking=True, translate=True)
    purchace_price = fields.Monetary(string='Purchace price', currency_field='company_currency', tracking=True, translate=True)
    bookvalue = fields.Monetary(string='Bookvalue', currency_field='company_currency', tracking=True, translate=True)
    market_value = fields.Monetary(string='Market value', currency_field='company_currency', tracking=True, translate=True)
    stock_exchange_value = fields.Monetary(string='Stock exchange value', currency_field='company_currency', tracking=True, translate=True)
    mortages_own = fields.Monetary(string='Mortages', currency_field='company_currency', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class ExtenssCrmPersonalReferences(models.Model):
    _name = 'extenss.crm.personal_ref'
    _description = 'Personal references'

    @api.constrains('email_personal_ref', 'phone_personal_ref', 'cell_phone_personal_res')
    def _check_fields_none(self):
        for reg_pr in self:
            if reg_pr.email_personal_ref == False and reg_pr.phone_personal_ref == False and reg_pr.cell_phone_personal_res == False:
                raise ValidationError(_('Enter a value in any of the fields Phone, Cell phone or Email in tab Personal references'))
    
    @api.constrains('phone_personal_ref')
    def _check_phone_personal(self):
        for reg in self:
            if not reg.phone_personal_ref == False:
                digits = [int(x) for x in reg.phone_personal_ref if x.isdigit()]
                if len(digits) != 10:
                    raise ValidationError(_('The phone must be a 10 digits in tab Personal references'))

    @api.constrains('cell_phone_personal_res')
    def _check_cell_phone_res(self):
        for reg_cell in self:
            if not reg_cell.cell_phone_personal_res == False:
                digits1 = [int(x) for x in reg_cell.cell_phone_personal_res if x.isdigit()]
                if len(digits1) != 10:
                    raise ValidationError(_('The cell phone must be a 10 digits in tab Personal references'))

    @api.constrains('email_personal_ref')
    def _check_email_personal_ref(self):
        for reg_ref in self:
            if not reg_ref.email_personal_ref == False:
                reg_ref.email_personal_ref.replace(" ","")
                if not re.match(r"[^@]+@[^@]+\.[^@]+", reg_ref.email_personal_ref):
                    raise ValidationError(_('Please enter valid email address in tab Personal references'))

    personal_ref_id = fields.Many2one('crm.lead')#modelo padre
    type_reference_personal_ref = fields.Many2one('extenss.customer.type_refbank', string='Type reference', required=True,translate=True)
    reference_name_personal_ref = fields.Char(string='Reference name', required=True, translate=True)
    phone_personal_ref = fields.Char(string='Phone', translate=True)
    cell_phone_personal_res = fields.Char(string='Cell phone', translate=True)
    email_personal_ref = fields.Char(string='Email', translate=True)

class ExtenssCrmConciliation(models.Model):
    _name = 'extenss.crm.conciliation'
    _description = 'Conciliation'

    name = fields.Char(string='Reference', tracking=True, translate=True)
    initial_balance = fields.Monetary(string='Initial balance', currency_field='company_currency', tracking=True, translate=True)
    final_balance = fields.Monetary(string='Final balance', currency_field='company_currency', tracking=True, translate=True)
    status_bank = fields.Selection([('draft','Draft'),('pending','Pending'),('validated','Validated')], string='Status', default='draft', tracking=True, translate=True)
    type = fields.Char(string='Type', default='conciliation', tracking=True, translate=True)
    flag_active = fields.Boolean(string='Show/Hide', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    conciliation_ids = fields.One2many('extenss.crm.conciliation_lines', 'conciliation_id', string=' ', tracking=True, domain=['|','&', ('status', '=', 'applied'),('flag_active_parent', '=', True),'&',('status', '=', 'pending'),('flag_active_parent', '=', False)])#('flag_active_parent', '=', False), '&', ('type', '=', 'lines'),'|',   ,('flag_inactive_parent', '=', True),('check', '=', False)]

    def action_get_data(self):
        # print('entra a crm')
        # statement_s = self.env['account.bank.statement'].search([])
        # for statement in statement_s:
        #     statement.
        ids = []
        records = self.env['extenss.crm.conciliation'].search_count([('type', '=', 'conciliation'),('name', '=', 'Conciliación')])
        print(records)
        if not records:
            con_id = self.env['extenss.crm.conciliation'].create({
                'name': 'Conciliación',
                'initial_balance': 0,
                'final_balance': 0,
                'type': 'conciliation'
            })
        
        records = self.env['extenss.crm.conciliation'].search([('type', '=', 'conciliation'),('name', '=', 'Conciliación')])
        for record in records:
            recs_crm = self.env['crm.lead'].search([('sequence_stage', '=', '5')])
            for rec_crm in recs_crm:
                recs_sale = self.env['sale.order'].search([('opportunity_id', '=', rec_crm.id)])
                for rec_sale in recs_sale:
                    if rec_sale.credit_type.shortcut == 'AF' or rec_sale.credit_type.shortcut == 'AP':
                        print('rec_crm.ref_number',rec_crm.ref_number)
                        amt = 0
                        records_bank = self.env['account.bank.statement.line'].search([('ref', '=', rec_crm.ref_number)])
                        for record_bank in records_bank:
                            print("entra al for bank")
                            amt += record_bank.amount
                            #id_procs = record_bank.id
                            #print("id_procs",id_procs)
                            ids.append(record_bank.id)

                        print('ids_process', ids)
                        tmp = '('+", ".join( repr(e) for e in ids )+')'
                        print('tmp', tmp)

                        rec_lines = self.env['extenss.crm.conciliation_lines'].search([('processing_id', 'not in', tmp),('reference', '=', rec_crm.ref_number),('type_rec', '=', 'conciliation')])#,('status' , '=', 'pending')
                        print('rec_lines', rec_lines)
                        if rec_lines:
                            for rec_line in rec_lines:
                                rec_line.amount = amt
                        else:
                            if rec_crm.ref_number:
                                line_id = self.env['extenss.crm.conciliation_lines'].create({
                                    'conciliation_id': record.id,
                                    'date': datetime.now().date(),#record_bank.date,
                                    'description': '',#record_bank.name,
                                    'customer': rec_crm.partner_id.id,#record_bank.partner_id.id,
                                    'reference': rec_crm.ref_number,#record_bank.ref,
                                    'amount': amt,
                                    #'bill_id': rec_ref.bill_id.id,
                                    'type_rec': 'conciliation',
                                    'status': 'pending',
                                    'processing_id': tmp
                                })

                        tmp = []
                        ids_process = []

                        reg_sales = self.env['sale.order'].search([('opportunity_id', '=', rec_crm.id)])
                        for reg_sale in reg_sales:
                            reg = self.env['extenss.crm.conciliation_lines'].search([('reference', '=', rec_crm.ref_number),('type_rec', '=', 'sale')])
                            print('reg_sales', reg)
                            if not reg:

                                if amt == reg_sale.total_initial_payments:
                                    flag_check = True
                                    line_id.write({
                                        'check': True,
                                    })
                                else:
                                    flag_check = False

                                sale_id = self.env['extenss.crm.conciliation_lines'].create({
                                    'conciliation_id': record.id,
                                    'date': datetime.now().date(),#record_bank.date,
                                    'description': 'Sale order',#record_bank.name,
                                    'customer': rec_crm.partner_id.id,#record_bank.partner_id.id,
                                    'reference': rec_crm.ref_number,#record_bank.ref,
                                    'amount': reg_sale.total_initial_payments,
                                    #'bill_id': rec_ref.bill_id.id,
                                    'type_rec': 'sale',
                                    'status': 'pending',
                                    #'processing_id': record_bank.id
                                    'check': flag_check
                                })

    def action_confirm_conciliation(self):
        print('Entra confirm')
        amount_conc = self.env['extenss.crm.conciliation_lines'].search([('conciliation_id', '=', self.id),('type_rec', '=', 'conciliation'),('check', '=', True),('status', '=', 'pending')]).amount
        # for reg_a_cn in amount_conc:
        #     ref_conc = reg_a_cn.reference

        amount_expiry = self.env['extenss.crm.conciliation_lines'].search([('conciliation_id', '=', self.id),('type_rec', '=', 'sale'),('check', '=', True),('status', '=', 'pending')]).amount
        # for reg_a_ex in amount_expiry:
        #     ref_expiry = reg_a_ex.reference

        if amount_conc != amount_expiry:
            raise ValidationError(_('The amounts are different'))

        count_total = self.env['extenss.crm.conciliation_lines'].search_count([('conciliation_id', '=', self.id)])
        count_checks = self.env['extenss.crm.conciliation_lines'].search_count([('conciliation_id', '=', self.id),('check', '=', True)])
        records = self.env['extenss.crm.conciliation_lines'].search([('conciliation_id', '=', self.id),('status', '=', 'pending')])#,('check', '=', True)
        for record in records:
            if record.check == True:# and record.type_rec == 'conciliation':
                print('entra a if check')
                print('record', record)
                regs_crm = self.env['crm.lead'].search([('ref_number', '=', record.reference)])
                for reg_crm in regs_crm:
                    reg_crm.flag_initial_payment = True
                record.status = 'applied'
    
    # def search_event_cont(self, ref='000000000000005-S', amount=4155.75, customer='46'):
    #     event_id = self.env['extenss.credit.contable_events'].search([('event_key', '=', '900')]).id
    #     self.env['extenss.credit.contable_events'].action_insert_event(event_id, amount, customer, ref)

class ExtenssCrmConciliationLines(models.Model):
    _name = 'extenss.crm.conciliation_lines'
    _description = 'Conciliation Lines'

    conciliation_id = fields.Many2one('extenss.crm.conciliation', string='Conciliation', ondelete='cascade', tracking=True, translate=True)
    flag_active_parent = fields.Boolean(related='conciliation_id.flag_active')
    date = fields.Date(string='Date', tracking=True, translate=True)
    description = fields.Char(string='Description', tracking=True, translate=True)
    customer = fields.Many2one('res.partner', string='Customer', tracking=True, translate=True)
    reference = fields.Char(string='Reference', tracking=True, translate=True)
    amount = fields.Monetary(string='Amount', currency_field='company_currency', tracking=True, translate=True)
    check = fields.Boolean(string='Validate', tracking=True, translate=True)
    status = fields.Selection([('applied', 'Applied'),('pending', 'Pending'),],string='Status', tracking=True, translate=True)
    type_rec = fields.Selection([('sale', 'Sale'),('conciliation', 'Conciliation'),], tracking=True, translate=True)
    processing_id = fields.Char(string='Processing id', tracking=True, translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)