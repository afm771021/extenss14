# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Financial Products',
    'version': '1.0',
    'summary': 'Definition of the Financial Products',
    'description': """
This is the base module for managing products and pricelists in Odoo.
========================================================================

Products support variants, different pricing methods, vendors information,
make to stock/order, different units of measure, packaging and properties.

    """,
    'author': 'Mastermind Software Services',
    'depends': ['base', 'mail','account'],
    'application': True,
    'website': 'https://www.mss.mx',
    'category': 'Sales/Sales',
    'data': [
        'security/product_security.xml',
        'security/ir.model.access.csv',
        'views/product_attribute_views.xml',
        'views/product_template_views.xml',
    ],
}
