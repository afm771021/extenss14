from odoo import api, fields, models, _
from odoo.exceptions import Warning, UserError, ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

COMMISION_TYPE = [
    ('0', 'Porcentaje'),
    ('1', 'Monto'),
]

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.constrains('product_id','date_start', 'date_first_payment', 'amount', 'credit_type','rents_deposit','purchase_option','residual_porcentage')   
    def _check_intrat(self):
        for quotation in self:
            if datetime.now().date() > quotation.date_start:
                raise Warning('Star Date must be greater or equal than Today for %s' % quotation.name)
            if not quotation.amount:
                raise Warning('Please provide a Request Amount for %s' % quotation.name)
            # if quotation.amount < quotation.min_amount or quotation.amount > quotation.max_amount:
            #     raise Warning('The Request Amount must be older than Min Amount and less than Max Amount %s' % quotation.name)
            if quotation.credit_type.shortcut == 'AF' or quotation.credit_type.shortcut == 'AP':
                if not quotation.fondeador:
                    raise Warning('Please provide a Fondeador %s' % quotation.name)
                if not quotation.description:
                    raise Warning('Please provide a Description %s' % quotation.name)
                if not quotation.purchase_option:
                    raise Warning('Please provide a Purchase Option Porcentage for %s' % quotation.name)
                if quotation.credit_type.shortcut == 'AP':
                    if not quotation.residual_porcentage:
                        raise Warning('Please provide a Residual Porcentage for %s' % quotation.name)
            quotation.calculate=False

    def action_quotation_calculate(self):
        for quotation in self:
            if not quotation.product_id:
                raise Warning('Please provide a Product for %s' % quotation.name)
            if not quotation.date_start:
                raise Warning('Please provide a Start Date for %s' % quotation.name)
            if not quotation.amount:
                raise Warning('Please provide a Request Amount for %s' % quotation.name)
            if quotation.amount < quotation.min_amount or quotation.amount > quotation.max_amount:
                raise Warning('The Request Amount must be older than Min Amount and less than Max Amount %s' % quotation.name)
            if quotation.credit_type.shortcut == 'AF' or quotation.credit_type == 'AP':
                if quotation.credit_type.shortcut == 'AF':
                    if not quotation.guarantee_percentage:
                        raise Warning('Please provide a Guarantee Porcentage for %s' % quotation.name)
                if quotation.credit_type.shortcut == 'AP':
                    if not quotation.residual_porcentage:
                        raise Warning('Please provide a Residual Porcentage for %s' % quotation.name)
            di=quotation.date_start
            df=quotation.date_start
            #dpp=quotation.date_first_payment
            #diff=dpp-df
            if quotation.calculation_base=='360/360':
                if quotation.credit_type.shortcut == 'AF' or quotation.credit_type.shortcut == 'AP':
                    if quotation.include_taxes:
                        dr=(quotation.interest_rate_value / 360 )/(1+(quotation.tax_id/100))
                    else:
                        dr=(quotation.interest_rate_value / 360 )
                else:
                    if quotation.include_taxes:
                        dr=(quotation.interest_rate_value / 360 )
                    else:
                        dr=(quotation.interest_rate_value / 360 ) * (1+(quotation.tax_id/100))
                if quotation.frequency_id.days == 30:
                    dm=30
                    rate=(dr/100*30)
                if quotation.frequency_id.days == 15:
                    dm=15
                    rate=(dr/100*15)
                if quotation.frequency_id.days == 7:
                    dm=7
                    rate=(dr/100*7)#rate=(dr/100*7,2)
            if quotation.calculation_base=='365/365':
                if quotation.credit_type.shortcut == 'AF' or quotation.credit_type.shortcut == 'AP':
                    if quotation.include_taxes:
                        dr=(quotation.interest_rate_value / 365 )/(1+(quotation.tax_id/100))
                    else:
                        dr=(quotation.interest_rate_value / 365 )
                else:
                    if quotation.include_taxes:
                        dr=(quotation.interest_rate_value / 365 )
                    else:
                        dr=(quotation.interest_rate_value / 365 ) * (1+(quotation.tax_id/100))
                if quotation.frequency_id.days == 30:
                    dm=calendar.monthrange(di.year,di.month)[1]
                    rate=(dr/100*30.5)
                if quotation.frequency_id.days == 15:
                    dm=15
                    rate=(dr/100*15.25)
                if quotation.frequency_id.days == 7:
                    dm=7
                    rate=(dr/100*7)
                
            if quotation.calculation_base=='360/365':
                if quotation.credit_type.shortcut == 'AF' or quotation.credit_type.shortcut == 'AP':
                    if quotation.include_taxes:
                        dr=(quotation.interest_rate_value / 360 )/(1+(quotation.tax_id/100))
                    else:
                        dr=(quotation.interest_rate_value / 360 )
                else:
                    if quotation.include_taxes:
                        dr=(quotation.interest_rate_value / 360 )
                    else:
                        dr=(quotation.interest_rate_value / 360 ) * (1+(quotation.tax_id/100))
                if quotation.frequency_id.days == 30:
                    dm=calendar.monthrange(di.year,di.month)[1]
                    rate=(dr/100*30.5)
                if quotation.frequency_id.days == 15:
                    dm=15
                    rate=(dr/100*15.25)
                if quotation.frequency_id.days == 7:
                    dm=7
                    rate=(dr/100*7)
            amortization_ids = [(5, 0, 0)]
        
            quotation.amortization_ids = amortization_ids
            
            if quotation.credit_type.shortcut == 'AF' or quotation.credit_type.shortcut == 'AP':
                quotation.amount_si=(quotation.amount/(1+(quotation.tax_id/100)))
                ra=(quotation.amount_si)
                quotation.purchase_option2=(quotation.purchase_option/100*ra)
                if quotation.credit_type.shortcut == 'AP':
                    quotation.residual_value=(ra*quotation.residual_porcentage/100)
                if quotation.credit_type.shortcut == 'AF':
                    quotation.iva=(ra*quotation.tax_id/100)
                    quotation.total_guarantee=(ra*quotation.guarantee_percentage/100)
                quotation.iva_purchase=(quotation.purchase_option2*(quotation.tax_id/100))
                quotation.total_purchase=(quotation.purchase_option2+quotation.iva_purchase)
                quotation.total_commision=0
                for com in quotation.commision_ids:
                    quotation.total_commision=(quotation.total_commision+(com.value_commision))
                if quotation.credit_type.shortcut == 'AF':
                    pay=((ra*(rate)*pow((1+(rate)),quotation.term))-(0*(rate)))/(pow(1+(rate),quotation.term)-1)
                if quotation.credit_type.shortcut == 'AP':
                    pay=((ra*(rate)*pow((1+(rate)),quotation.term))-(quotation.residual_value*(rate)))/(pow(1+(rate),quotation.term)-1)
            else:
                ra=quotation.amount
                pay=quotation.amount/((1-(1/pow((1+(rate)),quotation.term)))/(rate))
            for i in range(quotation.term):
                if quotation.frequency_id.days == 30:
                    df = df + relativedelta(months=1)
                if quotation.frequency_id.days == 15:
                    if i%2 == 0:
                        dfq=df
                        df = df + relativedelta(days=15)
                    else:
                        df = dfq + relativedelta(months=1)
                if quotation.frequency_id.days == 7:
                    df = df + relativedelta(days=7)
                if quotation.calculation_base=='365/365' or quotation.calculation_base=='360/365':
                    if quotation.frequency_id.days == 30:
                        dm=calendar.monthrange(df.year,df.month)[1]
                    if quotation.frequency_id.days == 15:
                        if i%2 == 0:
                            dm=15
                        else:
                            dm=(calendar.monthrange(df.year,df.month)[1]-15)
                #if i == 0 :
                #    dmt=dm
                #    dm=diff.days
                #    df= di + relativedelta(days=dm)
                #else:
                #    if quotation.calculation_base =='360/360':
                #        dm=dmt
                if quotation.credit_type.shortcut == 'AF' or quotation.credit_type.shortcut == 'AP':
                    interest=round(((ra*dr*dm)/100),2)
                else:
                    ici=round(((ra*dr*dm)/100),2)
                    interest=ici/(1+(quotation.tax_id/100))
                ivainterest=interest*(quotation.tax_id/100)
                if i == (quotation.term-1):
                    if quotation.credit_type.shortcut == 'AP':
                        pay=round(pay,2)
                    else:
                        if quotation.credit_type.shortcut == 'AF':
                            pay=round(ra+interest,2)
                        else:
                            pay=round(ra+ici,2)
                else:
                    pay=round(pay,2)
                if quotation.credit_type.shortcut == 'AF' or quotation.credit_type.shortcut == 'AP':
                    capital=round((pay-(interest)),2)
                else:
                    capital=round((pay-ici),2)

                ivacapital=(capital*(quotation.tax_id/100))
                fb=round((ra-capital),2)
                totalrent=0
                ivarent=0
                if quotation.credit_type.shortcut == 'AF': 
                    totalrent=round((pay+ivainterest+ivacapital),2)
                    totalrent=round(totalrent,2)
                if quotation.credit_type.shortcut == 'AP':
                    ivarent=round((pay*(quotation.tax_id/100)),2)
                    totalrent=round((pay+ivarent),2)
                    totalrent=round(totalrent,2)
                
                amortization_cs_ids = [(4, 0, 0)]
                data = {
                    'no_payment': (i+1),
                    'date_end': df,
                    'initial_balance': ra,
                    'capital': capital,
                    'interest': interest,
                    'iva_interest': ivainterest,
                    'payment': pay,
                    'iva_rent': ivarent,
                    'total_rent': totalrent,
                    'iva_capital': ivacapital
                }
                amortization_ids.append((0, 0, data))
                self.amortization_ids = amortization_ids
                self.send_email=False
                self.calculate=True
                self.amount_untaxed =0.0
                self.amount_untaxed = self.amount
                self.amount_total = self.amount
                ra=fb
                di=df 
                self.date_limit_pay=df
                if i == 0 :
                    quotation.date_first_payment=df
                    if quotation.credit_type.shortcut == 'AF' or quotation.credit_type.shortcut == 'AP':
                        quotation.tax_amount=pay*(quotation.tax_id/100)
                        quotation.payment_amount=pay
                        quotation.total_payment=pay+quotation.tax_amount   
                        quotation.total_deposit=totalrent*quotation.rents_deposit
                        quotation.total_initial_payments=quotation.total_deposit+quotation.total_commision+quotation.total_guarantee
                    else:
                        quotation.total_payment=pay

    def action_authorize(self):
        data = {
            'model' : 'sale.order',
            'form' : self.read()[1] 
        }
        return self.env.ref('extenss_request.contrato_amortization').report_action(self, data=data)


    def action_confirm(self):
        crms = self.env['crm.lead'].search([('id', '=', self.opportunity_id.id)])
        for reg in crms:
            reg.flag_validated = True

        self.ensure_one()
        self.crear_documentos()
        #self.opportunity_id.product_id = self.product_id.product_tmpl_id.id
        #self.amount = self.opportunity_id.planned_revenue
        #self.opportunity_id.product_id = self.product_id.id
        self.send_email=True
        self.calculate=True
        self.confirm=True
        res = super(SaleOrder, self).action_confirm()
        return res
    
    def action_quotation_send(self):
        self.calculate=True
        self.confirm=False
        self.send_email=True
        res = super(SaleOrder, self).action_quotation_send()
        return res

    def action_cancel(self):
        self.calculate=True
        self.confirm=True
        self.send_email=True
        res = super(SaleOrder, self).action_cancel()
        return res

    def crear_documentos(self):
        if not self.product_id:
            return
        name = self.env['extenss.product.cat_docs'].search([('doc_id', '=', self.product_id.product_tmpl_id.id)])
        for reg in name:
            namedoc = self.env['extenss.product.type_docs'].search([('id', '=', reg.catalogo_docs.id)])
            for regname in namedoc:
                self.rel = regname.related_to
                self.nombre = regname.name
                if self.rel == 'contact':
                    self.contacto = self.partner_id.id
                    self.solicitud = ''
                if self.rel == 'request':
                    self.solicitud = self.opportunity_id.id
                    self.contacto = ''

                existe = self.env['documents.document'].search(['|', ('partner_id', '=', self.partner_id.id), ('lead_id', '=', self.opportunity_id.id), ('doc_prod_id', '=', regname.id)])
                existe_cliente = self.env['documents.document'].search([('partner_id', '=', self.partner_id.id),('doc_prod_id', '=', regname.id)])

                if not existe.id and not existe_cliente:
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

    def action_cancel(self):
        docs_self = []
        docs_ord = []
        bandera = False
        name = self.env['extenss.product.cat_docs'].search([('doc_id', '=', self.product_id.product_tmpl_id.id)])
        for reg_type_or in name:
            namedoc = self.env['extenss.product.type_docs'].search([('id', '=', reg_type_or.catalogo_docs.id)])
            for reg_or in namedoc:
                docs_self.append(reg_or.id)

        orders = self.env['sale.order'].search([('opportunity_id.id', '=', self.opportunity_id.id),('state', '=', 'sale'),('id', '!=', self.id)])
        for reg_ords in orders:
            namedocs_ord = self.env['extenss.product.cat_docs'].search([('doc_id', '=', reg_ords.product_id.product_tmpl_id.id)])
            for regdocs_ord in namedocs_ord:
                namedoc_or = self.env['extenss.product.type_docs'].search([('id', '=', regdocs_ord.catalogo_docs.id)])
                docs_ord.append(namedoc_or.id)

        for record in docs_self:
            if record not in docs_ord:
                id_delete = record
                print("entra a record", id_delete)
                self.env['documents.document'].search(['|', '&', ('partner_id', '=', self.partner_id.id), ('lead_id', '=', self.opportunity_id.id), ('doc_prod_id', '=', id_delete), ('attachment_id', '=', False)]).unlink()

        res = super(SaleOrder, self).action_cancel()
        return res

    include_taxes = fields.Boolean('Include Taxes', default=False,  translate=True)
    min_age = fields.Integer('Min. Age')
    max_age = fields.Integer('Max. Age')
    min_amount = fields.Monetary('Min. Amount',  currency_field='company_currency', tracking=True)
    max_amount = fields.Monetary('Max. Amount',  currency_field='company_currency', tracking=True)
    amount = fields.Monetary('Request Amount', currency_field='company_currency', tracking=True)
    amount_si = fields.Monetary('Amount s/iva', currency_field='company_currency', tracking=True)
    payment_amount = fields.Monetary('Payment Amount', currency_field='company_currency', tracking=True)
    tax_amount = fields.Monetary('Tax Amount', currency_field='company_currency', tracking=True)
    total_payment = fields.Monetary('Total Payment', currency_field='company_currency', tracking=True)
    total_commision = fields.Monetary('Total Commision', currency_field='company_currency', tracking=True)
    rents_deposit = fields.Integer('Rents in Deposit', default=0)
    total_deposit = fields.Monetary('Rent Deposit Amount', currency_field='company_currency', tracking=True)
    guarantee_percentage =  fields.Float('Guarantee Percentage', (2,6))
    total_guarantee = fields.Monetary('Total Guarantee Deposit', currency_field='company_currency', tracking=True)
    total_initial_payments = fields.Monetary('Total Initial Payments', currency_field='company_currency', tracking=True)
    date_start = fields.Date('Start Date')
    date_limit_pay = fields.Date('Limit Date')
    date_first_payment = fields.Date('First Payment Date')
    frequency_id = fields.Many2one('extenss.product.frequencies') 
    term = fields.Integer('Term', required=True,  default=0)
    calculation_base = fields.Char('Calculation Base')
    interest_rate_value = fields.Float('Interest Rate', (2,6))
    cat = fields.Float('CAT', (2,6))
    current_interest_rate_value = fields.Float('Current Interest Rate', (2,6))
    credit_type = fields.Many2one('extenss.product.credit_type')
    base_interest_rate = fields.Char('Base Interest Rate')
    point_base_interest_rate = fields.Float('P. Base Int. Rate', (2,6), translate=True)
    tax_id = fields.Float('Tax Rate', (2,6))
    amortization_ids = fields.One2many(
        'extenss.request.amortization', 
        'sale_order_id', 
        string='Amortization Table')
    rate_arrears_interest = fields.Float('Factor', (2,1), readonly=True, tracking=True,translate=True)
    factor_rate = fields.Float('Rate interest moratorium', (2,6), compute='_compute_factor_rate', store=True, tracking=True, translate=True)
    days_pre_notice = fields.Char(string="Days pre-notice", translate=True)
    days_past_due = fields.Char(string="Days past due", translate=True)
    number_pay_rest = fields.Char(string="Number of payments for restructuring", translate=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
    product_id = fields.Many2one('extenss.product.product', 'Product Name', required=True)
    
    partner_type = fields.Selection('res.partner', related='partner_id.company_type')

    partner_id = fields.Many2one('res.partner', translate=True)

    #product_custom_attribute_value_ids = fields.One2many('extenss.product.attribute.custom.value', 'sale_order_line_id', string="Custom Values")
    order_id = fields.Many2one('sale.order', string='Order Reference', ondelete='cascade', index=True, copy=False)#required=True
    # product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    # product_uom = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    # product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    product_no_variant_attribute_value_ids = fields.Many2many('extenss.product.template.attribute.value', string="Extra Values", ondelete='restrict')
    calculate = fields.Boolean(string="Calculate", default=True)
    send_email = fields.Boolean(string="Send email", default=True)
    confirm = fields.Boolean(string="Confirm", default=True)
    hide = fields.Boolean(string="Hide", default=False)
    hidepo = fields.Boolean(string="Hide", default=False)
    hidevr = fields.Boolean(string="Hide", default=False)
    bir = fields.Boolean(string="Hide", default=False)
    cs = fields.Boolean(String='CS', default=False)
    af = fields.Boolean(String='AF', default=False)
    ap = fields.Boolean(String='AP', default=False)
    dn = fields.Boolean(string='DN', default=False)
    iva = fields.Monetary('IVA',  currency_field='company_currency', tracking=True)
    purchase_option = fields.Float('Purchase Option Porcentage', (2,6))
    purchase_option2 = fields.Monetary('Purchase Option Value', currency_field='company_currency', tracking=True)
    iva_purchase = fields.Monetary('IVA Purchase',  currency_field='company_currency', tracking=True)
    total_purchase =  fields.Monetary('Total Purchase', currency_field='company_currency', tracking=True)
    residual_porcentage = fields.Float('Residual %', (2,6))
    residual_value = fields.Monetary('Residual Value', currency_field='company_currency', tracking=True)
    commision_ids = fields.One2many(
        'extenss.request.commision', 
        'sale_order_id', 
        string='Commision',)
    fondeador = fields.Many2one('extenss.request.fondeador')
    description = fields.Char('Description')
    #opportunity_id = fields.Many2one('crm.lead', string='Opportunity')

    #@api.depends('partner_id')
    #def _compute_amount(self):
    #    monto = self.env['crm.lead'].search([('id', '=', self.opportunity_id.id)])
    #    for reg in monto:
    #        self.amount = reg.planned_revenue
    #        self.amount_untaxed = reg.planned_revenue


    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        monto = self.env['crm.lead'].search([('id', '=', self.opportunity_id.id)])
        for reg in monto:
            self.amount = reg.planned_revenue
        amortization_ids = [(5, 0, 0)]
        self.amortization_ids = amortization_ids
        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
        
       # remove the is_custom values that don't belong to this template
        # for pacv in self.product_custom_attribute_value_ids:
        #     if pacv.custom_product_template_attribute_value_id not in valid_values:
        #         self.product_custom_attribute_value_ids -= pacv
        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav
        vals = {}

        product = self.product_id.with_context(
            #lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            #quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            #pricelist=self.order_id.pricelist_id.id,
            #uom=self.product_uom.id
        )
        self.date_first_payment=''
        self.tax_amount=0.0
        self.payment_amount=0.0
        self.total_payment=0.0
        self.amount_si=0.0
        self.iva=0.0
        self.guarantee_percentage=0.000000
        self.total_guarantee=0.0
        self.purchase_option=0.000000
        self.rents_deposit=0
        self.total_commision=0.0
        self.total_deposit=0.0
        self.total_initial_payments=0.0
        self.residual_porcentage=0.000000
        self.residual_value=0.0
        self.purchase_option2=0.0
        self.iva_purchase=0.0
        self.total_purchase=0.0
        self.fondeador=0
        self.description=''

        self.number_pay_rest = self.product_id.number_pay_rest
        self.days_pre_notice = self.product_id.days_pre_notice
        self.days_past_due = self.product_id.days_past_due
        self.rate_arrears_interest = product.rate_arrears_interest
        self.term = product.product_template_attribute_value_ids.term_extra
        self.credit_type = self.product_id.credit_type.id
        self.calculation_base = self.product_id.calculation_base.name
        self.base_interest_rate = self.product_id.base_interest_rate.name
        self.point_base_interest_rate=self.product_id.point_base_interest_rate
        self.tax_id=self.product_id.taxes_id.amount
        self.min_age=self.product_id.min_age
        self.max_age=self.product_id.max_age
        self.min_amount=self.product_id.min_amount
        self.max_amount=self.product_id.max_amount
        self.frequency_id=product.frequency_extra
        self.interest_rate_value=product.interest_rate_extra
        self.cat=product.cat_extra
        self.include_taxes=self.product_id.include_taxes
        if self.credit_type.shortcut == 'AP':
            self.ap = True
        else:
            self.ap = False
        if self.credit_type.shortcut == 'AF':
            self.af = True
        else:
            self.af = False
        if self.credit_type.shortcut == 'CS':
            self.hide = True
            self.cs = True
        else:
            self.cs = False
        if self.credit_type.shortcut == 'DN':
            self.hide = True
            self.dn = True
        else:
            self.dn = False
        if self.credit_type.shortcut == 'AP' or self.credit_type.shortcut == 'CS' or self.credit_type.shortcut == 'DN':
            self.hidepo = True
        else:
            self.hidepo = False
        if self.credit_type.shortcut == 'AF' or self.credit_type.shortcut == 'CS' or self.credit_type.shortcut == 'DN':
            self.hidevr = True
        else:
            self.hidevr = False
        if self.base_interest_rate == "TIIE":
            self.bir = False
            for reg in self.product_id.base_interest_rate.interest_rate_ids:
                if datetime.now().date() == reg.date:
                    self.interest_rate_value=reg.interest_rate+self.point_base_interest_rate
        else:
            self.bir= True
        #vals.update(name=self.get_sale_order_line_multiline_description_sale(product))
       
        #self._compute_tax_id()
        self.update(vals)

        # title = False
        # message = False
        # result = {}
        # warning = {}
        # if product.sale_line_warn != 'no-message':
        #     title = _("Warning for %s") % product.name
        #     message = product.sale_line_warn_msg
        #     warning['title'] = title
        #     warning['message'] = message
        #     result = {'warning': warning}
        #     if product.sale_line_warn == 'block':
        #         self.product_id = False

        # return result

    @api.onchange('partner_id')
    def add_domain(self):
        for reg in self:
            if reg.partner_type == 'company':
                return {'domain': {'product_id': [('apply_company', '=', 'True')]}}
            if reg.partner_type == 'person':
                return {'domain': {'product_id': [('apply_person', '=', 'True')]}}

    @api.depends('rate_arrears_interest')
    def _compute_factor_rate(self):
        for reg in self:
            reg.factor_rate = reg.rate_arrears_interest * reg.interest_rate_value
    #@api.onchange('product_id')
    #def _onchange_product_id(self):
    #    if not self.product_id:
    #        return
    # To compute the dicount a so line is created in cache
    #    self.frequency = self.product_id.lst_price
    #    res = {
    #        'price_unit': self.price_unit,
            #'tax_ids': [(6, 0, self.tax_id.ids)],
    #    }
    #    return res

    #taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', help="Default taxes used when selling the product.", string='Customer Taxes',
    #    domain=[('type_tax_use', '=', 'sale')], default=lambda self: self.env.company.account_sale_tax_id)

class SaleOrderAmortization(models.Model):
    _name = "extenss.request.amortization"
    _description = "Extenss Amortization Table CS"

    sale_order_id = fields.Many2one('sale.order')
    no_payment = fields.Integer('No.')
    date_end = fields.Date('End Date')
    initial_balance = fields.Monetary('Initial Balance',currency_field='company_currency', tracking=True)
    capital = fields.Monetary('Capital',currency_field='company_currency', tracking=True)
    interest = fields.Monetary('Interest', currency_field='company_currency', tracking=True)
    iva_interest = fields.Monetary('IVA Interest',currency_field='company_currency', tracking=True)
    payment = fields.Monetary('Payment',currency_field='company_currency', tracking=True)
    iva_capital = fields.Monetary('IVA Capital',currency_field='company_currency', tracking=True)
    total_rent = fields.Monetary('Total Rent',currency_field='company_currency', tracking=True)
    iva_rent = fields.Monetary('IVA Rent',currency_field='company_currency', tracking=True)

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

class SaleOrderCommision(models.Model):
    _name = "extenss.request.commision"
    _description = "Extenss Commision"
    

    @api.depends('type_commision','commision')
    def _compute_total_commision(self):
        for reg in self:
            if reg.type_commision == '1':
                reg.value_commision = reg.commision
            else:
                reg.value_commision=reg.sale_order_id.amount*reg.commision/100
                #reg.value_commision = reg.commision_id.amount*commision/100
    
    sale_order_id = fields.Many2one('sale.order')
    detali_commision = fields.Char('Detail Commision')
    type_commision = fields.Selection(COMMISION_TYPE, string='Type Commision', index=True)
    commision = fields.Monetary('Commision',currency_field='company_currency', tracking=True)
    value_commision = fields.Monetary('Commision Value',currency_field='company_currency', tracking=True,compute='_compute_total_commision')

    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)

    @api.constrains('commision')   
    def _check_intrat(self):
        for com in self:
            if not com.detali_commision:
                raise Warning('Please provide a Detail Commision ')
            if not com.type_commision:
                raise Warning('Please provide a Type Commision ')
            if not com.commision:
                raise Warning('Please provide a Commision ')
class ExtenssRequestFondeador(models.Model):
    _name = 'extenss.request.fondeador'
    _order = 'name'
    _description = 'Fondeador'

    name = fields.Char(string='Fondeador',  translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

    _sql_constraints = [
        ('name_unique',
        'UNIQUE(id,name)',
        "The Fondeador name must be unique"),
    ]