import itertools
import logging

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.osv import expression

CALC_TYPE = [
    ('0', 'Saldos Insolutos'),
]
CT = [
    ('Credito Simple'),
    ('Arrendamiento Financiero'),
    ('Arrendamiento Puro'),
]

_logger = logging.getLogger(__name__)

class ExtenssProductCreditType(models.Model):
    _name = 'extenss.product.credit_type'
    _order = 'name'
    _description = 'Credit Type'

    name = fields.Char(string='Credit Type',  translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssProductCalculationBase(models.Model):
    _name = 'extenss.product.calculation_base'
    _orde = 'name'
    _description = 'Calculation Base'
    
    name = fields.Char(string='Calculation Base',  translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)

class ExtenssProductBaseInterestRate(models.Model):
    _name = 'extenss.product.base_interest_rate'
    _orde = 'name'
    _description = 'Base Interest Rate'
    
    name = fields.Char(string='Base Interest Rate',  translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)
    interest_rate_ids = fields.One2many('extenss.product.interest_rate_date','base_interest_rate_id',string=' ')

class ExtenssProductTypeDocs(models.Model):
    _name = 'extenss.product.type_docs'
    _order = 'name'
    _description = 'Type Documents'

    name = fields.Char(string='Document Name', translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)
    related_to = fields.Selection(string='Related to', selection=[('contact', 'Contact'), ('request', 'Request')], default='contact')
    
    _sql_constraints = [
        ('name_unique',
        'UNIQUE(name)',
        "The Document name must be unique"),
    ]

class ExtenssProductRecDocs(models.Model):
    _name = 'extenss.product.rec_docs'
    _order = 'name'
    _description = 'Recruitment Documents'

    name = fields.Char(string='Document Name', translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)
    
    _sql_constraints = [
        ('name_unique',
        'UNIQUE(name)',
        "The Document name must be unique"),
    ]

    @api.constrains('name')
    def _check_name_insensitive(self):
        model_ids = self.search([('id', '!=', self.id)])
        list_names = [x.name.upper() for x in model_ids if x.name]
        if self.name.upper() in list_names:
            raise Warning(
                "Ya existe un registro con el nombre: %s " % (self.name.upper())
            )

class ExtenssFrequencies(models.Model):
    _name = "extenss.product.frequencies"
    _description = "Frequencies"

    name = fields.Char('Frequency', required=True)
    days = fields.Integer('Days', required=True)

class ExtenssProductTemplate(models.Model):
    _name = "extenss.product.template"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = "Extenss Product Template"
    #_order = "name"

    @api.constrains('min_age', 'max_age', 'min_amount', 'max_amount', 'rec_docs_ids', 'docs_ids')   
    def _check_fields(self):
        for product in self:
            if product.min_age <=0:
                raise ValidationError(_('The Min. Age must be greater than 0'))
            if product.max_age <=0:
                raise ValidationError(_('The Max. Age must be greater than 0'))
            if product.min_age >99:
                raise ValidationError(_('The Min. Age is not valid'))
            if product.max_age >99:
                raise ValidationError(_('The Max. Age is not valid'))
            if product.min_age >= product.max_age:
                raise ValidationError(_('The Min. Age must be less than The Max. Age'))
            if product.min_amount <= 0:
                raise ValidationError(_('The Min. Amount must be greater than 0'))
            if product.max_amount <= 0:
                raise ValidationError(_('The Max. Amount must be greater than 0'))
            if product.min_amount >= product.max_amount:
                raise ValidationError(_('The Min. Amount must be less than The Max. Amount'))
            if len(product.rec_docs_ids)==0:
                raise ValidationError(_('Must add Recruitment Documents'))
            if len(product.docs_ids)==0:
                raise ValidationError(_('Must add official documents in tab Documents'))

    @api.constrains('base_interest_rate')   
    def _check_bir(self):
        for product in self:
            if product.base_interest_rate.id != False and product.point_base_interest_rate == False:
                raise ValidationError(_('The Point Base Interest Rate at must be greater than'))

    @api.onchange('base_interest_rate')
    def base_interest_rate_change(self):
        if not self.base_interest_rate:
            return
        self.hide=False

    name = fields.Char('Product Name', index=True, required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1, help='Gives the sequence order when displaying a product list')
    description = fields.Text('Description', translate=True)
    description_purchase = fields.Text('Purchase Description', translate=True)
    description_sale = fields.Text('Sales Description', translate=True,
        help="A description of the Product that you want to communicate to your customers. "
            "This description will be copied to every Sales Order, Delivery Order and Customer Invoice/Credit Note")
    type = fields.Selection([('consu', 'Consumable'),('service', 'Service')], string='Product Type', default='consu', required=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
            'A consumable product is a product for which stock is not managed.\n'
            'A service is a non-material product you provide.')
    #company_id = fields.Many2one('res.company', 'Company', index=1)
    active = fields.Boolean('Active', default=True, help="If unchecked, it will allow you to hide the product without removing it.")
    color = fields.Integer('Color Index')
    default_code = fields.Char('Product Code',  store=True)#inverse='_set_default_code', compute='_compute_default_code',
    taxes_id = fields.Many2many('account.tax', 'extenss_product_taxes_rel', 'prod_id', 'tax_id', help="Default taxes used when selling the product.", string='Customer Taxes',
    default=lambda self: self.env.company.account_sale_tax_id)#domain=[('type_tax_use', '=', 'sale')]
    ####extenss_product
    credit_type = fields.Many2one('extenss.product.credit_type')
    calculation_type = fields.Selection(CALC_TYPE, string='Calculation Type', index=True, default=CALC_TYPE[0][0])
    calculation_base = fields.Many2one('extenss.product.calculation_base')
    base_interest_rate = fields.Many2one('extenss.product.base_interest_rate')
    point_base_interest_rate = fields.Float('P. of Base Interest Rate', (2,6), translate=True)
    rate_arrears_interest = fields.Float('Factor', (2,1), tracking=True, translate=True)
    include_taxes = fields.Boolean('Include Taxes', default=False,  translate=True)
    min_age = fields.Integer('Min. Age', translate=True)
    max_age = fields.Integer('Max. Age',  translate=True)
    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
    min_amount = fields.Monetary('Min. Amount',  currency_field='company_currency', tracking=True)
    max_amount = fields.Monetary('Max. Amount',  currency_field='company_currency', tracking=True)
    apply_company = fields.Boolean('Apply Company', default=False,  translate=True)
    apply_person = fields.Boolean('Apply Person', default=False,  translate=True)
    endorsement = fields.Boolean('Requires Endorsement', default=False,  translate=True)
    obligated_solidary = fields.Boolean('Requires Obligated solidary', default=False,  translate=True)
    guarantee = fields.Boolean('Requires Warranty', default=False,  translate=True)
    socioeconomic_study = fields.Boolean('Socio-economic study', default=False,  translate=True)
    sic_consult = fields.Boolean('SIC Query', default=False,  translate=True)
    beneficiaries = fields.Boolean('Beneficiaries', default=False,  translate=True)
    patrimonial_relationship = fields.Boolean('Patrimonial Declaration', default=False,  translate=True)
    financial_situation = fields.Boolean('Business information', default=False,  translate=True)

    docs_ids = fields.One2many('extenss.product.cat_docs','doc_id', string=' ')
    rec_docs_ids = fields.One2many('extenss.product.recruitment_documents', 'product_id', string=' ')
    hide = fields.Boolean(string="Hide", default=True)
    days_pre_notice = fields.Char(string="Days pre-notice", translate=True)
    days_past_due = fields.Char(string="Days past due", translate=True)
    number_pay_rest = fields.Char(string="Number of payments for restructuring", translate=True)

    #######
    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency_id')
    attribute_line_ids = fields.One2many('extenss.product.template.attribute.line', 'product_tmpl_id', 'Product Attributes', copy=True)
    valid_product_template_attribute_line_ids = fields.Many2many('extenss.product.template.attribute.line',
    compute="_compute_valid_product_template_attribute_line_ids", string='Valid Product Attribute Lines', help="Technical compute")

    product_variant_ids = fields.One2many('extenss.product.product', 'product_tmpl_id', 'Products', required=True)
    product_variant_count = fields.Integer('Product Variants', compute='_compute_product_variant_count')
    product_child = fields.Many2one('extenss.product.template', string="Subproduct", domain="[('credit_type.shortcut', '=', 'ff')]")
    credit_type_sc = fields.Char(related='credit_type.shortcut', string='Abbreviation')

    @api.depends('company_id')
    def _compute_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        for template in self:
            template.currency_id = template.company_id.sudo().currency_id.id or main_company.currency_id.id

    def _compute_is_product_variant(self):
        for template in self:
            template.is_product_variant = False

    @api.depends('product_variant_ids.product_tmpl_id')
    def _compute_product_variant_count(self):
        for template in self:
            # do not pollute variants to be prefetched when counting variants
            template.product_variant_count = len(template.with_prefetch().product_variant_ids)

    def _create_variant_ids(self):
        self.flush()
        Product = self.env["extenss.product.product"]

        variants_to_create = []
        variants_to_activate = Product
        variants_to_unlink = Product

        for tmpl_id in self:
            lines_without_no_variants = tmpl_id.valid_product_template_attribute_line_ids._without_no_variant_attributes()

            all_variants = tmpl_id.with_context(active_test=False).product_variant_ids.sorted('active')

            current_variants_to_create = []
            current_variants_to_activate = Product

            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            single_value_lines = lines_without_no_variants.filtered(lambda ptal: len(ptal.product_template_value_ids._only_active()) == 1)
            if single_value_lines:
                for variant in all_variants:
                    combination = variant.product_template_attribute_value_ids | single_value_lines.product_template_value_ids._only_active()
                    # Do not add single value if the resulting combination would
                    # be invalid anyway.
                    if (
                        len(combination) == len(lines_without_no_variants) and
                        combination.attribute_line_id == lines_without_no_variants
                    ):
                        variant.product_template_attribute_value_ids = combination

            if not tmpl_id.has_dynamic_attributes():
                # Iterator containing all possible `product.template.attribute.value` combination
                # The iterator is used to avoid MemoryError in case of a huge number of combination.
                all_combinations = itertools.product(*[
                    ptal.product_template_value_ids._only_active() for ptal in lines_without_no_variants
                ])
                # Set containing existing `product.template.attribute.value` combination
                existing_variants = {
                    variant.product_template_attribute_value_ids: variant for variant in all_variants
                }
                # For each possible variant, create if it doesn't exist yet.
                for combination_tuple in all_combinations:
                    combination = self.env['extenss.product.template.attribute.value'].concat(*combination_tuple)
                    if combination in existing_variants:
                        current_variants_to_activate += existing_variants[combination]
                    else:
                        current_variants_to_create.append({
                            'product_tmpl_id': tmpl_id.id,
                            'product_template_attribute_value_ids': [(6, 0, combination.ids)],
                            'active': tmpl_id.active,
                        })
                        if len(current_variants_to_create) > 1000:
                            raise UserError(_(
                                'The number of variants to generate is too high. '
                                'You should either not generate variants for each combination or generate them on demand from the sales order. '
                                'To do so, open the form view of attributes and change the mode of *Create Variants*.'))
                variants_to_create += current_variants_to_create
                variants_to_activate += current_variants_to_activate

            variants_to_unlink += all_variants - current_variants_to_activate

        if variants_to_activate:
            variants_to_activate.write({'active': True})
        if variants_to_create:
            Product.create(variants_to_create)
        if variants_to_unlink:
            variants_to_unlink._unlink_or_archive()

        self.flush()
        self.invalidate_cache()
        return True

    def has_dynamic_attributes(self):
        """Return whether this `product.template` has at least one dynamic
        attribute.

        :return: True if at least one dynamic attribute, False otherwise
        :rtype: bool
        """
        self.ensure_one()
        return any(a.create_variant == 'dynamic' for a in self.valid_product_template_attribute_line_ids.attribute_id)

    @api.depends('attribute_line_ids.value_ids')
    def _compute_valid_product_template_attribute_line_ids(self):
        """A product template attribute line is considered valid if it has at
        least one possible value.

        Those with only one value are considered valid, even though they should
        not appear on the configurator itself (unless they have an is_custom
        value to input), indeed single value attributes can be used to filter
        products among others based on that attribute/value.
        """
        for record in self:
            record.valid_product_template_attribute_line_ids = record.attribute_line_ids.filtered(lambda ptal: ptal.value_ids)

class ExtenssProductProduct(models.Model):
    _name = "extenss.product.product"
    _description = "Product"
    _inherits = {'extenss.product.template': 'product_tmpl_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    #_order = 'default_code, name, id'

    cat_extra = fields.Float(
        'Variant Cat Extra', compute='_compute_product_cat_extra',
        help="This is the sum of the extra price of all attributes")
    interest_rate_extra = fields.Float(
        'Variant Cat Extra', compute='_compute_product_interest_rate_extra',
        help="This is the sum of the extra price of all attributes")
    term_extra = fields.Integer(
        'Variant Term Extra', compute='_compute_product_term_extra',
        help="This is the sum of the extra price of all attributes")
    frequency_extra = fields.Integer(
        'Variant Fequency Extra', compute='_compute_product_frequency_extra',
        help="This is the sum of the extra price of all attributes")
    def _compute_product_cat_extra(self):
        for product in self:
            product.cat_extra = sum(product.product_template_attribute_value_ids.mapped('cat_extra'))
    def _compute_product_interest_rate_extra(self):
        for product in self:
            product.interest_rate_extra = sum(product.product_template_attribute_value_ids.mapped('interest_rate_extra'))
    def _compute_product_term_extra(self):
        for product in self:
            product.term_extra = sum(product.product_template_attribute_value_ids.mapped('term_extra'))
    def _compute_product_frequency_extra(self):
        for product in self:
            product.frequency_extra = sum(product.product_template_attribute_value_ids.mapped('frequency_extra'))

    product_tmpl_id = fields.Many2one('extenss.product.template', 'Product Template', auto_join=True, index=True, ondelete="cascade", required=True)
    default_code = fields.Char('Internal Reference', index=True)
    code = fields.Char('Reference')#, compute='_compute_product_code'
    #partner_ref = fields.Char('Customer Ref', compute='_compute_partner_ref')

    active = fields.Boolean('Active', default=True, help="If unchecked, it will allow you to hide the product without removing it.")
    product_template_attribute_value_ids = fields.Many2many('extenss.product.template.attribute.value', relation='extenss_product_variant_combination', string="Attribute Values")#ondelete='restrict'
    combination_indices = fields.Char(compute='_compute_combination_indices', store=True, index=True)
    is_product_variant = fields.Boolean(compute='_compute_is_product_variant')
    image_variant_1920 = fields.Image("Variant Image", max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_variant_1024 = fields.Image("Variant Image 1024", related="image_variant_1920", max_width=1024, max_height=1024, store=True)
    image_variant_512 = fields.Image("Variant Image 512", related="image_variant_1920", max_width=512, max_height=512, store=True)
    image_variant_256 = fields.Image("Variant Image 256", related="image_variant_1920", max_width=256, max_height=256, store=True)
    image_variant_128 = fields.Image("Variant Image 128", related="image_variant_1920", max_width=128, max_height=128, store=True)
    can_image_variant_1024_be_zoomed = fields.Boolean("Can Variant Image 1024 be zoomed", compute='_compute_can_image_variant_1024_be_zoomed', store=True)

    # Computed fields that are used to create a fallback to the template if
    # necessary, it's recommended to display those fields to the user.
    image_1920 = fields.Image("Image", compute='_compute_image_1920', inverse='_set_image_1920')
    image_1024 = fields.Image("Image 1024", compute='_compute_image_1024')
    image_512 = fields.Image("Image 512", compute='_compute_image_512')
    image_256 = fields.Image("Image 256", compute='_compute_image_256')
    image_128 = fields.Image("Image 128", compute='_compute_image_128')
    #can_image_1024_be_zoomed = fields.Boolean("Can Image 1024 be zoomed", compute='_compute_can_image_1024_be_zoomed')

    @api.depends('image_variant_1920', 'image_variant_1024')
    def _compute_can_image_variant_1024_be_zoomed(self):
        for record in self:
            record.can_image_variant_1024_be_zoomed = record.image_variant_1920 and tools.is_image_size_above(record.image_variant_1920, record.image_variant_1024)

    def _compute_image_1920(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_1920 = record.image_variant_1920 or record.product_tmpl_id.image_1920

    def _set_image_1920(self):
        for record in self:
            if (
                # We are trying to remove an image even though it is already
                # not set, remove it from the template instead.
                not record.image_1920 and not record.image_variant_1920 or
                # We are trying to add an image, but the template image is
                # not set, write on the template instead.
                record.image_1920 and not record.product_tmpl_id.image_1920 or
                # There is only one variant, always write on the template.
                self.search_count([
                    ('product_tmpl_id', '=', record.product_tmpl_id.id),
                    ('active', '=', True),
                ]) <= 1
            ):
                record.image_variant_1920 = False
                record.product_tmpl_id.image_1920 = record.image_1920
            else:
                record.image_variant_1920 = record.image_1920

    def _compute_image_1024(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_1024 = record.image_variant_1024 or record.product_tmpl_id.image_1024

    def _compute_image_512(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_512 = record.image_variant_512 or record.product_tmpl_id.image_512

    def _compute_image_256(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_256 = record.image_variant_256 or record.product_tmpl_id.image_256

    def _compute_image_128(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_128 = record.image_variant_128 or record.product_tmpl_id.image_128

    # def _compute_can_image_1024_be_zoomed(self):
    #     """Get the image from the template if no image is set on the variant."""
    #     for record in self:
    #         record.can_image_1024_be_zoomed = record.can_image_variant_1024_be_zoomed if record.image_variant_1920 else record.product_tmpl_id.can_image_1024_be_zoomed

    def init(self):
        """Ensure there is at most one active variant for each combination.

        There could be no variant for a combination if using dynamic attributes.
        """
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS product_product_combination_unique ON %s (product_tmpl_id, combination_indices) WHERE active is true"
            % self._table)

    def _get_invoice_policy(self):
        return False

    @api.depends('product_template_attribute_value_ids')
    def _compute_combination_indices(self):
        for product in self:
            product.combination_indices = product.product_template_attribute_value_ids._ids2str()

    def _compute_is_product_variant(self):
        for product in self:
            product.is_product_variant = True

    def open_product_template(self):
        """ Utility method used to add an "Open Template" button in product views """
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'res_model': 'extenss.product.template',
                'view_mode': 'form',
                'res_id': self.product_tmpl_id.id,
                'target': 'new'}

class ExtenssProductAttribute(models.Model):
    _name = "extenss.product.attribute"
    _description = "Product Attribute"
    # if you change this _order, keep it in sync with the method
    # `_sort_key_attribute_value` in `product.template`
    _order = 'sequence, id'

    name = fields.Char('Attribute', required=True, translate=True)
    sequence = fields.Integer('Sequence', help="Determine the display order", index=True)
    value_ids = fields.One2many('extenss.product.attribute.value', 'attribute_id', 'Values', copy=True)
    
    #attribute_line_ids = fields.One2many('extenss.product.template.attribute.line', 'attribute_id', 'Lines')
    create_variant = fields.Selection([
       ('always', 'Instantly'),
       ('dynamic', 'Dynamically'),
       ('no_variant', 'Never')],
       default='always',
       string="Variants Creation Mode",
       help="""- Instantly: All possible variants are created as soon as the attribute and its values are added to a product.
       - Dynamically: Each variant is created only when its corresponding attributes and values are added to a sales order.
       - Never: Variants are never created for the attribute.
       Note: the variants creation mode cannot be changed once the attribute is used on at least one product.""",
       required=True)
    #is_used_on_products = fields.Boolean('Used on Products')#compute='_compute_is_used_on_products'
    #product_tmpl_ids = fields.Many2many('extenss.product.template', string="Related Products",  store=True)#compute='_compute_products',
class ExtenssProductTemplateAttributeValue(models.Model):
    """Materialized relationship between attribute values
    and product template generated by the product.template.attribute.line"""

    _name = "extenss.product.template.attribute.value"
    _description = "Product Template Attribute Value"
    _order = 'attribute_line_id, product_attribute_value_id, id'

    @api.constrains('interest_rate_extra', 'cat_extra')   
    def _check_intcatextra(self):
        for intrat in self: 
            if intrat.interest_rate_extra <= 0:
                raise ValidationError(_('The Interest Rate must be greater than 0'))
            if intrat.cat_extra <= 0:
                raise ValidationError(_('The Cat must be greater than 0'))
            if intrat.term_extra <= 0:
                raise ValidationError(_('The Term must be greater than 0'))

    interest_rate_extra = fields.Float('Interest Rate',(2,6) ,translate=True)###, required=True
    cat_extra = fields.Float('Cat',(2,6),translate=True)#, required=True
    frequencies_extra = fields.Many2one('extenss.product.frequencies', string="Frequencies", translate=True)#, required=True
    term_extra = fields.Integer('Term', translate=True)#, required=True
    frequency_extra = fields.Integer('Frequency')
    # Not just `active` because we always want to show the values except in
    # specific case, as opposed to `active_test`.
    ptav_active = fields.Boolean("Active", default=True)
    name = fields.Char('Value', related="product_attribute_value_id.name")

    # defining fields: the product template attribute line and the product attribute value
    product_attribute_value_id = fields.Many2one('extenss.product.attribute.value', string='Attribute Value',
        required=True, ondelete='cascade', index=True)
    attribute_line_id = fields.Many2one('extenss.product.template.attribute.line', required=True, ondelete='cascade', index=True)

    # related fields: product template and product attribute
    product_tmpl_id = fields.Many2one('extenss.product.template', string="Product Template", related='attribute_line_id.product_tmpl_id', store=True, index=True)
    attribute_id = fields.Many2one('extenss.product.attribute', string="Attribute", related='attribute_line_id.attribute_id', store=True, index=True)
    ptav_product_variant_ids = fields.Many2many('extenss.product.product', relation='extenss_product_variant_combination', string="Related Variants", readonly=True)

    _sql_constraints = [
        ('attribute_value_unique', 'unique(attribute_line_id, product_attribute_value_id)', "Each value should be defined only once per attribute per product."),
    ]

    @api.onchange('frequencies_extra')
    def frequencies_extra_change(self):
        if not self.frequencies_extra:
            return
        self.frequency_extra = self.frequencies_extra.id

    @api.constrains('attribute_line_id', 'product_attribute_value_id')
    def _check_valid_values(self):
        for ptav in self:
            if ptav.product_attribute_value_id not in ptav.attribute_line_id.value_ids:
                raise ValidationError(
                    _("The value %s is not defined for the attribute %s on the product %s.") %
                    (ptav.product_attribute_value_id.display_name, ptav.attribute_id.display_name, ptav.product_tmpl_id.display_name)
                )

    @api.model_create_multi
    def create(self, vals_list):
        if any('ptav_product_variant_ids' in v for v in vals_list):
            # Force write on this relation from `product.product` to properly
            # trigger `_compute_combination_indices`.
            raise UserError(_("You cannot update related variants from the values. Please update related values from the variants."))
        return super(ExtenssProductTemplateAttributeValue, self).create(vals_list)

    def write(self, values):
        if 'ptav_product_variant_ids' in values:
            # Force write on this relation from `product.product` to properly
            # trigger `_compute_combination_indices`.
            raise UserError(_("You cannot update related variants from the values. Please update related values from the variants."))
        pav_in_values = 'product_attribute_value_id' in values
        product_in_values = 'product_tmpl_id' in values
        if pav_in_values or product_in_values:
            for ptav in self:
                if pav_in_values and ptav.product_attribute_value_id.id != values['product_attribute_value_id']:
                    raise UserError(
                        _("You cannot change the value of the value %s set on product %s.") %
                        (ptav.display_name, ptav.product_tmpl_id.display_name)
                    )
                if product_in_values and ptav.product_tmpl_id.id != values['product_tmpl_id']:
                    raise UserError(
                        _("You cannot change the product of the value %s set on product %s.") %
                        (ptav.display_name, ptav.product_tmpl_id.display_name)
                    )
        return super(ExtenssProductTemplateAttributeValue, self).write(values)

    # def unlink(self):
    #     """Override to:
    #     - Clean up the variants that use any of the values in self:
    #         - Remove the value from the variant if the value belonged to an
    #             attribute line with only one value.
    #         - Unlink or archive all related variants.
    #     - Archive the value if unlink is not possible.

    #     Archiving is typically needed when the value is referenced elsewhere
    #     (on a variant that can't be deleted, on a sales order line, ...).
    #     """
    #     # Directly remove the values from the variants for lines that had single
    #     # value (counting also the values that are archived).
    #     single_values = self.filtered(lambda ptav: len(ptav.attribute_line_id.product_template_value_ids) == 1)
    #     for ptav in single_values:
    #         ptav.ptav_product_variant_ids.write({'product_template_attribute_value_ids': [(3, ptav.id, 0)]})
    #     # Try to remove the variants before deleting to potentially remove some
    #     # blocking references.
    #     self.ptav_product_variant_ids._unlink_or_archive()
    #     # Now delete or archive the values.
    #     ptav_to_archive = self.env['extenss.product.template.attribute.value']
    #     for ptav in self:
    #         try:
    #             with self.env.cr.savepoint(), tools.mute_logger('odoo.sql_db'):
    #                 super(ExtenssProductTemplateAttributeValue, ptav).unlink()
    #         except Exception:
    #             # We catch all kind of exceptions to be sure that the operation
    #             # doesn't fail.
    #             ptav_to_archive += ptav
    #     ptav_to_archive.write({'ptav_active': False})
    #     return True

    def name_get(self):
        """Override because in general the name of the value is confusing if it
        is displayed without the name of the corresponding attribute.
        Eg. on exclusion rules form
        """
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]

    def _only_active(self):
        return self.filtered(lambda ptav: ptav.ptav_active)

    def _without_no_variant_attributes(self):
        return self.filtered(lambda ptav: ptav.attribute_id.create_variant != 'no_variant')

    def _ids2str(self):
        return ','.join([str(i) for i in sorted(self.ids)])

    def _get_combination_name(self):
        """Exclude values from single value lines or from no_variant attributes."""
        return ", ".join([ptav.name for ptav in self._without_no_variant_attributes()._filter_single_value_lines()])

    def _filter_single_value_lines(self):
        """Return `self` with values from single value lines filtered out
        depending on the active state of all the values in `self`.

        If any value in `self` is archived, archived values are also taken into
        account when checking for single values.
        This allows to display the correct name for archived variants.

        If all values in `self` are active, only active values are taken into
        account when checking for single values.
        This allows to display the correct name for active combinations.
        """
        only_active = all(ptav.ptav_active for ptav in self)
        return self.filtered(lambda ptav: not ptav._is_from_single_value_line(only_active))

    def _is_from_single_value_line(self, only_active=True):
        """Return whether `self` is from a single value line, counting also
        archived values if `only_active` is False.
        """
        self.ensure_one()
        all_values = self.attribute_line_id.product_template_value_ids
        if only_active:
            all_values = all_values._only_active()
        return len(all_values) == 1

class ExtenssProductTemplateAttributeLine(models.Model):
    _name = "extenss.product.template.attribute.line"
    _description = 'Product Template Attribute Line'
    #_rec_name = 'attribute_id'
    #_order = 'attribute_id, id'

    active = fields.Boolean(default=True)
    product_tmpl_id = fields.Many2one('extenss.product.template', string="Product Template", ondelete='cascade', required=True, index=True)
    attribute_id = fields.Many2one('extenss.product.attribute', string="Attribute", ondelete='restrict', required=True, index=True)
    value_ids = fields.Many2many('extenss.product.attribute.value', string="Values", domain="[('attribute_id', '=', attribute_id)]",
        relation='ext_prod_attr_val_prod_temp_attr_line_rel', ondelete='restrict')
    product_template_value_ids = fields.One2many('extenss.product.template.attribute.value', 'attribute_line_id', string="Product Attribute Values")

    @api.onchange('attribute_id')
    def _onchange_attribute_id(self):
        self.value_ids = self.value_ids.filtered(lambda pav: pav.attribute_id == self.attribute_id)

    @api.constrains('active', 'value_ids', 'attribute_id')
    def _check_valid_values(self):
        for ptal in self:
            if ptal.active and not ptal.value_ids:
                raise ValidationError(
                    _("The attribute %s must have at least one value for the product %s.") %
                    (ptal.attribute_id.display_name, ptal.product_tmpl_id.display_name)
                )
            for pav in ptal.value_ids:
                if pav.attribute_id != ptal.attribute_id:
                    raise ValidationError(
                        _("On the product %s you cannot associate the value %s with the attribute %s because they do not match.") %
                        (ptal.product_tmpl_id.display_name, pav.display_name, ptal.attribute_id.display_name)
                    )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Override to:
        - Activate archived lines having the same configuration (if they exist)
            instead of creating new lines.
        - Set up related values and related variants.

        Reactivating existing lines allows to re-use existing variants when
        possible, keeping their configuration and avoiding duplication.
        """
        create_values = []
        activated_lines = self.env['extenss.product.template.attribute.line']
        for value in vals_list:
            vals = dict(value, active=value.get('active', True))
            # While not ideal for peformance, this search has to be done at each
            # step to exclude the lines that might have been activated at a
            # previous step. Since `vals_list` will likely be a small list in
            # all use cases, this is an acceptable trade-off.
            archived_ptal = self.search([
                ('active', '=', False),
                ('product_tmpl_id', '=', vals.pop('product_tmpl_id', 0)),
                ('attribute_id', '=', vals.pop('attribute_id', 0)),
            ], limit=1)
            if archived_ptal:
                # Write given `vals` in addition of `active` to ensure
                # `value_ids` or other fields passed to `create` are saved too,
                # but change the context to avoid updating the values and the
                # variants until all the expected lines are created/updated.
                archived_ptal.with_context(update_product_template_attribute_values=False).write(vals)
                activated_lines += archived_ptal
            else:
                create_values.append(value)
        res = activated_lines + super(ExtenssProductTemplateAttributeLine, self).create(create_values)
        res._update_product_template_attribute_values()
        return res

    def write(self, values):
        """Override to:
        - Add constraints to prevent doing changes that are not supported such
            as modifying the template or the attribute of existing lines.
        - Clean up related values and related variants when archiving or when
            updating `value_ids`.
        """
        if 'product_tmpl_id' in values:
            for ptal in self:
                if ptal.product_tmpl_id.id != values['product_tmpl_id']:
                    raise UserError(
                        _("You cannot move the attribute %s from the product %s to the product %s.") %
                        (ptal.attribute_id.display_name, ptal.product_tmpl_id.display_name, values['product_tmpl_id'])
                    )

        if 'attribute_id' in values:
            for ptal in self:
                if ptal.attribute_id.id != values['attribute_id']:
                    raise UserError(
                        _("On the product %s you cannot transform the attribute %s into the attribute %s.") %
                        (ptal.product_tmpl_id.display_name, ptal.attribute_id.display_name, values['attribute_id'])
                    )
        # Remove all values while archiving to make sure the line is clean if it
        # is ever activated again.
        if not values.get('active', True):
            values['value_ids'] = [(5, 0, 0)]
        res = super(ExtenssProductTemplateAttributeLine, self).write(values)
        if 'active' in values:
            self.flush()
            self.env['product.template'].invalidate_cache(fnames=['attribute_line_ids'])
        # If coming from `create`, no need to update the values and the variants
        # before all lines are created.
        if self.env.context.get('update_product_template_attribute_values', True):
            self._update_product_template_attribute_values()
        return res

    def unlink(self):
        """Override to:
        - Archive the line if unlink is not possible.
        - Clean up related values and related variants.

        Archiving is typically needed when the line has values that can't be
        deleted because they are referenced elsewhere (on a variant that can't
        be deleted, on a sales order line, ...).
        """
        # Try to remove the values first to remove some potentially blocking
        # references, which typically works:
        # - For single value lines because the values are directly removed from
        #   the variants.
        # - For values that are present on variants that can be deleted.
        self.product_template_value_ids._only_active().unlink()
        # Keep a reference to the related templates before the deletion.
        templates = self.product_tmpl_id
        # Now delete or archive the lines.
        ptal_to_archive = self.env['extenss.product.template.attribute.line']
        for ptal in self:
            try:
                with self.env.cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                    super(ExtenssProductTemplateAttributeLine, ptal).unlink()
            except Exception:
                # We catch all kind of exceptions to be sure that the operation
                # doesn't fail.
                ptal_to_archive += ptal
        ptal_to_archive.write({'active': False})
        # For archived lines `_update_product_template_attribute_values` is
        # implicitly called during the `write` above, but for products that used
        # unlinked lines `_create_variant_ids` has to be called manually.
        (templates - ptal_to_archive.product_tmpl_id)._create_variant_ids()
        return True

    def _update_product_template_attribute_values(self):
        """Create or unlink `product.template.attribute.value` for each line in
        `self` based on `value_ids`.

        The goal is to delete all values that are not in `value_ids`, to
        activate those in `value_ids` that are currently archived, and to create
        those in `value_ids` that didn't exist.

        This is a trick for the form view and for performance in general,
        because we don't want to generate in advance all possible values for all
        templates, but only those that will be selected.
        """
        ProductTemplateAttributeValue = self.env['extenss.product.template.attribute.value']
        ptav_to_create = []
        ptav_to_unlink = ProductTemplateAttributeValue
        for ptal in self:
            ptav_to_activate = ProductTemplateAttributeValue
            remaining_pav = ptal.value_ids
            for ptav in ptal.product_template_value_ids:
                if ptav.product_attribute_value_id not in remaining_pav:
                    # Remove values that existed but don't exist anymore, but
                    # ignore those that are already archived because if they are
                    # archived it means they could not be deleted previously.
                    if ptav.ptav_active:
                        ptav_to_unlink += ptav
                else:
                    # Activate corresponding values that are currently archived.
                    remaining_pav -= ptav.product_attribute_value_id
                    if not ptav.ptav_active:
                        ptav_to_activate += ptav

            for pav in remaining_pav:
                # The previous loop searched for archived values that belonged to
                # the current line, but if the line was deleted and another line
                # was recreated for the same attribute, we need to expand the
                # search to those with matching `attribute_id`.
                # While not ideal for peformance, this search has to be done at
                # each step to exclude the values that might have been activated
                # at a previous step. Since `remaining_pav` will likely be a
                # small list in all use cases, this is an acceptable trade-off.
                ptav = ProductTemplateAttributeValue.search([
                    ('ptav_active', '=', False),
                    ('product_tmpl_id', '=', ptal.product_tmpl_id.id),
                    ('attribute_id', '=', ptal.attribute_id.id),
                    ('product_attribute_value_id', '=', pav.id),
                ], limit=1)
                if ptav:
                    ptav.write({'ptav_active': True, 'attribute_line_id': ptal.id})
                    # If the value was marked for deletion, now keep it.
                    ptav_to_unlink -= ptav
                else:
                    # create values that didn't exist yet
                    ptav_to_create.append({
                        'product_attribute_value_id': pav.id,
                        'attribute_line_id': ptal.id
                    })
            # Handle active at each step in case a following line might want to
            # re-use a value that was archived at a previous step.
            ptav_to_activate.write({'ptav_active': True})
            ptav_to_unlink.write({'ptav_active': False})
        ptav_to_unlink.unlink()
        ProductTemplateAttributeValue.create(ptav_to_create)
        self.product_tmpl_id._create_variant_ids()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            args = args or []
            domain = ['|', ('attribute_id', operator, name), ('value_ids', operator, name)]
            attribute_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
            return models.lazy_name_get(self.browse(attribute_ids).with_user(name_get_uid))
        return super(ExtenssProductTemplateAttributeLine, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    def _without_no_variant_attributes(self):
        return self.filtered(lambda ptal: ptal.attribute_id.create_variant != 'no_variant')

class ExtenssProductAttributeValue(models.Model):
    _name = "extenss.product.attribute.value"
    _order = 'attribute_id, sequence, id'
    _description = 'Attribute Value'

    name = fields.Char(string='Value', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', help="Determine the display order", index=True)
    attribute_id = fields.Many2one('extenss.product.attribute', string="Attribute", ondelete='cascade', required=True, index=True,
        help="The attribute cannot be changed once the value is used on at least one product.")
    #pav_attribute_line_ids = fields.Many2many('extenss.product.template.attribute.line', string="Lines",
    #relation='ext_prod_attr_value_prod_temp_att_line_rel')
    #is_used_on_products = fields.Boolean('Used on Products')#, compute='_compute_is_used_on_products'

class ExtenssProductCatDocs(models.Model):
    _name = 'extenss.product.cat_docs'
    _description = 'Documentos requeridos'

    doc_id = fields.Many2one('extenss.product.template')
    catalogo_docs = fields.Many2one('extenss.product.type_docs', string='Document name', translate=True)
    flag_activo = fields.Boolean(string='Required', default=False, translate=True)
    
    _sql_constraints = [
        ('name_unique',
        'UNIQUE(doc_id,catalogo_docs)',
        "The Document name must be unique"),
    ]

class ExtenssInterestRateDate(models.Model):
    _name = 'extenss.product.interest_rate_date'
    _description = 'Interest Rate Date'

    base_interest_rate_id = fields.Many2one('extenss.product.base_interest_rate')
    date = fields.Date('Date')
    interest_rate = fields.Float('Interest Rate',(2,6) ,translate=True)

    _sql_constraints = [
        ('name_unique',
        'UNIQUE(base_interest_rate_id,date)',
        "The Date must be unique"),
    ]

class ExtenssProductRecruitmentDocuments(models.Model):
    _name = 'extenss.product.recruitment_documents'
    _description = 'Recruitmen Documents'

    product_id = fields.Many2one('extenss.product.template')
    catalog_recru_docs = fields.Many2one('extenss.product.rec_docs', string='Document', translate=True)
    
    _sql_constraints = [
        ('name_unique',
        'UNIQUE(product_id,catalog_recru_docs)',
        "The Document name must be unique"),
    ]