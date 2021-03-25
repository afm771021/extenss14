from odoo import fields, models, api, _, exceptions
from odoo.exceptions import Warning, UserError, ValidationError
import re

class Partner(models.Model):
    _inherit = "res.partner"

    @api.constrains('email')
    def _check_email(self):
        for reg in self:
            if reg.email:
                reg.email.replace(" ","")
                #if not re.match(r"[^@]+@[^@]+\.[^@]+", reg.email):
                if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", reg.email):
                    raise ValidationError(_('Please enter valid email address'))

    @api.constrains('phone')
    def _check_phone(self):
        for reg in self:
            if reg.phone:
                digits = [int(x) for x in reg.phone if x.isdigit()]
                if len(digits) != 10:
                    raise ValidationError(_('The phone must be a 10 digits'))

    @api.constrains('mobile')
    def _check_mobile(self):
        for reg in self:
            if reg.mobile:
                digits = [int(x) for x in reg.mobile if x.isdigit()]
                if len(digits) != 10:
                    raise ValidationError(_('The mobile must be a 10 digits'))

    @api.constrains('years_residence')
    def _check_years(self):
        for reg_years in self:
            if reg_years.years_residence > 999:
                    raise ValidationError(_('The Years residence must be a 3 digits'))

    @api.constrains('dependent_number')
    def _check_dep(self):
        for reg_dep in self:
            if reg_dep.dependent_number > 999:
                raise ValidationError(_('The Dependent number must be a 3 digits'))
    
    @api.constrains('vat')
    def _check_tax_id(self):
        for reg_tax in self:
            if reg_tax.vat:
                if reg_tax.company_type == 'person':
                    if len(reg_tax.vat) != 13:
                        raise ValidationError(_('The Tax ID must be a 13 digits for Individual'))
                    if not re.match(r"^([A-ZÑ\x26]{3,4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$", reg_tax.vat):
                        raise ValidationError(_('The Tax ID is not valid for Individual'))
                if reg_tax.company_type == 'company':
                    if len(reg_tax.vat) != 12:
                        raise ValidationError(_('The Tax ID must be a 12 digits for Company'))
                    if not re.match(r"^([A-ZÑ\x26]{3,4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$", reg_tax.vat):
                        raise ValidationError(_('The Tax ID is not valid for Company'))
    
    @api.constrains('ssn')
    def _check_opt_ssn(self):
        for reg_ssn in self:
            if not reg_ssn.ssn == False:
                digits1 = [int(x) for x in reg_ssn.ssn if x.isdigit()]
                if len(digits1) != 11:
                    raise ValidationError(_('The ssn must be a 11 digits'))

    #vat = fields.Char(string='Tax ID', translate=True)
    gender = fields.Selection([('male', 'Male'),('female','Female')], string='Gender', help="Select one option")
    birth_date = fields.Date(string='Birth Date', translate=True)
    identification_type = fields.Many2one('extenss.customer.identification_type', required=True)
    identification = fields.Char(string='Identification', required=True, translate=True)
    # country_birth = fields.Many2one('res.country', string='Country of birth', required=True, translate=True)
    # state_birth = fields.Many2one('res.country.state', string='State of birth', domain="[('country_birth', '=?', country_birth)]", translate=True)#related='country_id.code', store=True
    country_birth = fields.Many2one('res.country', string='Country', ondelete='restrict')
    state_birth = fields.Many2one("res.country.state", string='State of birth', ondelete='restrict', domain="[('country_id', '=?', country_birth)]")
    marital_status = fields.Many2one('extenss.customer.marital_status')
    occupation = fields.Char(string='Occupation', translate=True)
    function = fields.Char(string='Job title', translate=True)
    #job_title = fields.Many2one('extenss.customer.job_title')
    politically_person = fields.Boolean(string='Politically exposed person', default=True, translate=True)
    housing_type = fields.Many2one('extenss.customer.housing_type')
    years_residence = fields.Integer(string='Years of residence', translate=True)
    level_study = fields.Many2one('extenss.customer.level_study')
    dependent_number = fields.Integer(string='Dependent number', translate=True)
    ssn = fields.Char(string='SSN', size=11, translate=True)

    constitution_date = fields.Date(string='Constitution date', translate=True)
    start_operations = fields.Date(string='Start operations', translate=True)
    number_employees = fields.Integer(string='Number of employees', translate=True)

    bankref_ids = fields.One2many('extenss.customer.bank_ref', 'bank_ref_id', string=' ')
    persref_ids = fields.One2many('extenss.customer.personal_ref', 'personal_ref_id', string=' ')
    add_identifi_ids = fields.One2many('extenss.customer.add_identifications', 'add_ident_id', string=' ')
    work_inf_ids = fields.One2many('extenss.customer.work_info', 'work_inf_id', string=' ')
    #product_type_ids = fields.One2many('extenss.customer.product_type', 'product_type_id', string='Product type')

class ExtenssCustomerIdentificationType(models.Model):
    _name = 'extenss.customer.identification_type'
    _order = 'name'
    _description = 'Identification type'

    name = fields.Char(string='Identification type', translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssCustomerJobTitle(models.Model):
    _name = 'extenss.customer.job_title'
    _order = 'name'
    _description = 'Job title'

    name = fields.Char(string='Job title', translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssCustomerMaritalStatus(models.Model):
    _name = 'extenss.customer.marital_status'
    _order = 'name'
    _description = 'Marital status'

    name = fields.Char(string='Marital status', translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtendsCustomerHousingType(models.Model):
    _name = 'extenss.customer.housing_type'
    _order = 'name'
    _description = 'Housing type'

    name = fields.Char(string='Housing type', translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssCustomerTypeRefBank(models.Model):
    _name = 'extenss.customer.type_refbank'
    _order = 'name'
    _description = 'Type of reference'

    name = fields.Char(string='Type of reference', translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssCustomerLevelStudy(models.Model):
    _name = 'extenss.customer.level_study'
    _order = 'name'
    _description = 'Level study'

    name = fields.Char(string='Level study', translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

# class ExtenssCustomerTypeIdentAI(models.Model):
#     _name = 'extenss.customer.type_ident_ai'
#     _order = 'name'
#     _description = 'Type of Identification'

#     name = fields.Char(string='Type of Identification', translate=True)
#     shorcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssCustomerProductType(models.Model):
    _name = 'extenss.customer.product_type'
    _order = 'name'
    _description = 'Product type'

    name = fields.Char(string='Product type', translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

    ###--Bank References
class ExtenssCustomerBankReferences(models.Model):
    _name = "extenss.customer.bank_ref"
    _description = "Bank References"

    @api.constrains('number_account', 'banking_reference')
    def _check_bankref_none(self):
        for reg_number in self:
            print(reg_number.number_account)
            print(reg_number.banking_reference)
            if reg_number.number_account == False and reg_number.banking_reference == False:
                raise ValidationError(_('Enter a value for Banking reference o Number account in tab Bank References'))
            else:
                if reg_number.banking_reference:
                    digits = [int(x) for x in reg_number.banking_reference if x.isdigit()]
                    if len(digits) != 18:
                        raise ValidationError(_('The banking reference must be a 18 digits in tab Bank References'))

    bank_ref_id = fields.Many2one('res.partner')#modelo padre
    #product_type = fields.Char(string='Product type', required=True, translate=True)
    product_type = fields.Many2one('extenss.customer.product_type', required=True, translate=True)
    institution = fields.Many2one('res.bank', required=True)#modelo padre
    banking_reference = fields.Char(string='Banking reference', size=18, translate=True)
    number_account = fields.Char(string='Number account', translate=True)
    comments_bank_ref = fields.Char(string='Comments', translate=True)

    ###--Personal References
class ExtenssCustomerPersonalReferences(models.Model):
    _name = "extenss.customer.personal_ref"
    _description = "Personal references"

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

    personal_ref_id = fields.Many2one('res.partner')#modelo padre
    type_reference_personal_ref = fields.Many2one('extenss.customer.type_refbank', string='Type reference', required=True,translate=True)
    #type_reference_personal_ref = fields.Char(string='Type reference', required=True,translate=True)
    reference_name_personal_ref = fields.Char(string='Reference name', required=True, translate=True)
    phone_personal_ref = fields.Char(string='Phone', translate=True)
    cell_phone_personal_res = fields.Char(string='Cell phone', translate=True)
    email_personal_ref = fields.Char(string='Email', translate=True)

###--Aditional identifications
class ExtenssCustomerAditionalIdentifications(models.Model):
    _name = "extenss.customer.add_identifications"
    _description = "Aditional identifications"

    add_ident_id = fields.Many2one('res.partner')#modelo padre
    type_of_indentification = fields.Many2one('extenss.customer.identification_type', string='Type of identification', required=True,)
    identification_ai = fields.Char(string='Identification', required=True, translate=True)

    ###--Work information
class ExtenssCustomerWorkInfo(models.Model):
    _name = "extenss.customer.work_info"
    _description = "Work information"

    @api.constrains('email_wi')
    def _check_email_wi(self):
        for reg_wi in self:
            if not reg_wi.email_wi == False:
                reg_wi.email_wi.replace(" ","")
                if not re.match(r"[^@]+@[^@]+\.[^@]+", reg_wi.email_wi):
                    raise ValidationError(_('Please enter valid email address in tab Work information'))

    @api.constrains('principal_phone')
    def _check_prin_phone(self):
        for reg_ph_wi in self:
            if not reg_ph_wi.principal_phone == False:
                digits1 = [int(x) for x in reg_ph_wi.principal_phone if x.isdigit()]
                if len(digits1) != 10:
                    raise ValidationError(_('The principal phone must be a 10 digits in tab Work information'))

    @api.constrains('optional_phone')
    def _check_opt_phone(self):
        for reg_opt in self:
            if not reg_opt.optional_phone == False:
                digits1 = [int(x) for x in reg_opt.optional_phone if x.isdigit()]
                if len(digits1) != 10:
                    raise ValidationError(_('The optional phone must be a 10 digits in tab Work information'))

    work_inf_id = fields.Many2one('res.partner')#modelo padre
    company = fields.Char(string='Company', translate=True, required=True)
    position = fields.Char(string='Position', translate=True, required=True)
    start_date = fields.Date(string='Start date', translate=True, required=True)
    close_date = fields.Date(string='Close date', translate=True)
    email_wi = fields.Char(string='Email', translate=True)
    principal_phone = fields.Char(string='Principal phone', translate=True)
    optional_phone = fields.Char(string='Optional phone', translate=True)
