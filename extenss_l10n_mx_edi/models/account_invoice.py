from odoo import fields, models, exceptions, api, _

class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'l10n_mx_edi.pac.sw.mixin']

    l10n_mx_edi_cfdi_name = fields.Char(string='CFDI name', copy=False, readonly=False, help='The attachment name of the CFDI.')