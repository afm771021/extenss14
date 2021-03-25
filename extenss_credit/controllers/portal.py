from odoo.tools import html2plaintext, DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo import http, _, fields
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from werkzeug.urls import url_encode
from babel.dates import format_datetime, format_date

class PortalCredit(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(PortalCredit, self)._prepare_portal_layout_values()
        user = request.env.user.id
        #domain = [('customer_id.id','=',user),('company_id.id','=',request.env.company.id)]
        domain = [('company_id.id','=',request.env.company.id)]
        credit_count = request.env['extenss.credit'].search_count(domain)
        values['credit_count'] = credit_count
        return values
    # ------------------------------------------------------------
    # My Appointments
    # ------------------------------------------------------------
    def _credit_get_page_view_values(self, credit, access_token,edit, **kwargs):
        # if not appointment.allday:
        #     url_date_start = fields.Datetime.from_string(appointment.start_datetime).strftime('%Y%m%dT%H%M%SZ')
        #     url_date_stop = fields.Datetime.from_string(appointment.stop_datetime).strftime('%Y%m%dT%H%M%SZ')
        # else:
        #     url_date_start = url_date_stop = fields.Date.from_string(appointment.start_date).strftime('%Y%m%d')
        #     format_func = format_date
        #     date_start_suffix = _(', All Day')
        # details = appointment.appointment_type_id and appointment.appointment_type_id.message_confirmation or appointment.description or ''
        # params = url_encode({
        #     'action': 'TEMPLATE',
        #     'text': appointment.name,
        #     'dates': url_date_start + '/' + url_date_stop,
        #     'details': html2plaintext(details.encode('utf-8'))
        # })
        # google_url = 'https://www.google.com/calendar/render?' + params
        values = {
            'page_name': 'credit',
            'credit': credit,
            'edit': edit
            #'google_url': google_url
        }
        return self._get_page_view_values(credit, access_token, values, 'my_credits_history', False, **kwargs)
    
    @http.route(['/my/credit', '/my/credit/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_credits(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        credit = request.env['extenss.credit']
        user = request.env.user.id
        #domain = [('customer_id.id','=',user),('company_id.id','=',request.env.company.id)]
        domain = [('company_id.id','=',request.env.company.id)]
        archive_groups = self._get_archive_groups('extenss.credit', domain)
        searchbar_sortings = {
            'create_date': {'label': _('DateTime'), 'order': 'create_date desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'create_date'
        order = searchbar_sortings[sortby]['order']
        # count for pagerç
        #domain = [('customer_id.id','=',user),('company_id.id','=',request.env.company.id)]
        domain = [('company_id.id','=',request.env.company.id)]
        credit_count = credit.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/credit",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=credit_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        credits = credit.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )       
        request.session['my_credits_history'] = credits.ids[:100]
        
        values.update({
            'date': date_begin,
            'credits': credits,
            'page_name': 'credit',
            'pager': pager,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'default_url': '/my/credit',
        })
        return request.render("extenss_credit.portal_my_credits", values)

    @http.route(['/my/credit/<int:id>'], type='http', auth="public", website=True)
    def portal_my_credit_detail(self, id, access_token=None, edit=None, download=False, **kw):
        try:
            credit_sudo = self._document_check_access('extenss.credit', id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = self._credit_get_page_view_values(credit_sudo, access_token,edit, **kw)
        return request.render("extenss_credit.portal_credit_page", values)
    
    @http.route(['/my/credit/<int:id>/submit'], type='http', website=True, method=["POST"])
    def calendar_credit_submit(self, id,description,access_token=None,edit=None,**kw):
        
        credit = request.env['extenss.credit'].search([('id','=',id)]).sudo().update({
            'description': description,
        })
        return request.redirect('/my/credit/%s' % id)