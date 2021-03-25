from odoo import http
from odoo import http, _, fields
from odoo.http import request
from babel.dates import format_datetime, format_date
from datetime import datetime
from odoo.addons.website_sale.controllers.main import WebsiteSale

class LeadController(http.Controller):
    
    @http.route('/ff', website=True, auth='public')
    def crm_ff(self, **kw):
        return request.render("extenss_request.ff_template_page", {})

    @http.route('/ff_cal', auth='public', website=True)
    def calculate_form(self, request, **kw):
        if kw.get('amount_ff'):
            amount_ff = float(kw.get('amount_ff'))
            amount_out_vat = amount_ff / 1.16
            amount_out_vat = round(amount_out_vat,2)
            amount_financed = amount_out_vat / 1.16
            amount_financed = round(amount_financed,2)
            #commission_details = kw.get('commission_details')
            #capacity = kw.get('capacity')
            commissions = amount_financed * (1/100)# (int(kw.get('commission_details')/100)
            commissions = round(commissions,2)
            commission_vat = commissions * 0.16
            commission_vat = round(commission_vat,2)
            inv_date = kw.get('invoice_date')
            invoice_date = datetime.strptime(inv_date, '%Y-%m-%d')
            in_date = kw.get('init_date')
            init_date = datetime.strptime(in_date, '%Y-%m-%d')
            days = abs((invoice_date - init_date).days)
            rate = 16 / 360
            interest = ((amount_financed * rate)/360) * days
            interest = round(interest,2)
            interest_vat = interest * 0.16
            interest_vat = round(interest_vat,2)
            total_payment = interest + interest_vat
            total_payment = round(total_payment,2)
            amount_delivered = amount_financed - commissions - commission_vat
            amount_delivered = round(amount_delivered,2)

            id_curp = request.env['extenss.customer.identification_type'].search([('name', '=', 'CURP')])
            if not id_curp:
                id_curp = request.env['extenss.customer.identification_type'].sudo().create(
                    {
                        'name': 'CURP',
                        'shortcut': 'CURP'
                    }
                )

            id_customer = request.env['res.partner'].sudo().create(
                {
                    'name': kw.get('partner_id'),
                    'email': kw.get('email_from'),
                    'identification_type': id_curp.id,
                    'identification': kw.get('curp'),
                    'birth_date': kw.get('birth_date'),
                    'phone': kw.get('phone'),
                    'vat': kw.get('vat'),
                    'street': kw.get('street'),
                    'city': kw.get('city'),
                    #'curp'
                })

            id_channel = request.env['extenss.request.sales_channel_id'].search([('name', '=', 'Website')])
            if not id_channel:
                id_channel = request.env['extenss.request.sales_channel_id'].sudo().create(
                    {
                        'name': 'Website',
                        'shortcut': 'WS',
                    })

            id_prod = request.env['extenss.product.template'].search([('credit_type.shortcut', '=', 'LFF')])

            request.env['crm.lead'].sudo().create(
                {
                    'partner_id': id_customer.id,
                    'type': 'opportunity',
                    'product_name': 'LFF',
                    'sales_channel_id': id_channel.id,
                    'catlg_product': id_prod.id,
                    'amount_ff': kw.get('amount_ff'),
                    'amount_out_vat': amount_out_vat,
                    'amount_financed': amount_financed,
                    'init_date': kw.get('init_date'),
                    'invoice_date': kw.get('invoice_date'),

                    'capacity': 16,
                    'commission_details': 1,
                    'commissions': commissions,
                    'commission_vat': commission_vat,
                    'days': days,
                    'interest': interest,
                    'interest_vat': interest_vat,
                    'total_payment': total_payment,
                    'amount_delivered': amount_delivered,
                })
            print('amount_out_vat', amount_out_vat)
            print('amount_financed', amount_financed)

            return request.render("extenss_request.ff_calculate_ok", {
                'amount_ff': amount_ff,
                'amount_out_vat': amount_out_vat,
                'capacity': 16,
                'commission_details': 1,
                'commissions': commissions,
                'commission_vat': commission_vat,
                'days': days,
                'interest': interest,
                'interest_vat': interest_vat,
                'total_payment': total_payment,
                'amount_delivered': amount_delivered,
            })
