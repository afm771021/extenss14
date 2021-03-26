# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Extenss Request',
    'version' : '1.0',
    'summary': 'Extenss Request Loan',
    'description': 'Extenss Request Loan',
    'author': 'Mastermind Software Services',
    'depends': ['crm','sale_crm','sale_management','documents','website'],#extenss_financial_product
    'application': False,
    'website': 'https://www.mss.mx',
    'category': 'Sales/CRM',
    'data': [
        'data/ir_sequence_data.xml',
        'data/crm_stage_data.xml',
        'data/conciliation_request_cron.xml',
        #'data/website_simulator_crm_data.xml',
        'security/extenss_request_security.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/sale_order_views.xml',
        'views/request_portal_template.xml',
        'views/website_form.xml',
        'reports/report_amortization.xml',
        'reports/contrato_amortization.xml',
        'reports/pagare_amortization.xml',
        'reports/report.xml',
        'data/mail_templete.xml',
        'data/quotation_template.xml',
        'reports/contrato_ff.xml',
        'reports/pagare_ff.xml',
    ],
}