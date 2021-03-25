from odoo.tools import html2plaintext, DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo import http, _, fields
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from werkzeug.urls import url_encode
from babel.dates import format_datetime, format_date

class PortalExtenssFF(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(PortalExtenssFF, self)._prepare_portal_layout_values()
        user = request.env.user.id
        #domain = [('partner_ids.user_ids.id','=',user),('company_id.id','=',request.env.company.id)]
        domain = [('company_id.id','=',request.env.company.id),('product_name', '=', 'LFF'),('stage_id', '=', 6)]
        extenss_ff_count = request.env['crm.lead'].search_count(domain)
        values['extenss_ff_count'] = extenss_ff_count
        return values
    # ------------------------------------------------------------
    # My Appointments
    # ------------------------------------------------------------
    def _extenss_ff_get_page_view_values(self, extenss_ff, access_token,edit, **kwargs):
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
            'page_name': 'extenss_ff',
            'extenss_ff': extenss_ff,
            'edit': edit,
            #'google_url': google_url
        }
        return self._get_page_view_values(extenss_ff, access_token, values, 'my_extenss_ffs_history', False, **kwargs)
    
    @http.route(['/my/extenss_ff', '/my/extenss_ff/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_extenss_ffs(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        extenss_ff = request.env['crm.lead']
        user = request.env.user.id
        #domain = [('partner_ids.user_ids.id','=',user),('company_id.id','=',request.env.company.id)]
        domain = [('company_id.id','=',request.env.company.id),('product_name', '=', 'LFF'),('stage_id', '=', 6)]
        archive_groups = self._get_archive_groups('crm.lead', domain)
        searchbar_sortings = {
            'create_date': {'label': _('DateTime'), 'order': 'create_date desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'create_date'
        order = searchbar_sortings[sortby]['order']
        # count for pager
        domain = [('company_id.id','=',request.env.company.id),('product_name', '=', 'LFF'),('stage_id', '=', 6)]
        extenss_ff_count = extenss_ff.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/extenss_ff",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=extenss_ff_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        extenss_ffs = extenss_ff.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )       
        request.session['my_extenss_ffs_history'] = extenss_ffs.ids[:100]
        
        values.update({
            'date': date_begin,
            'extenss_ffs': extenss_ffs,
            'page_name': 'extenss_ff',
            'pager': pager,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'default_url': '/my/extenss_ff',
        })
        return request.render("extenss_ff.portal_my_extenss_ffs", values)

    @http.route(['/my/extenss_ff/<int:id>'], type='http', auth="public", website=True)
    def portal_my_extenss_ff_detail(self, id, access_token=None, edit=None, download=False, **kw):
        try:
            extenss_ff_sudo = self._document_check_access('crm.lead', id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = self._extenss_ff_get_page_view_values(extenss_ff_sudo, access_token,edit, **kw)
        return request.render("extenss_ff.portal_extenss_ff_page", values)
    
    @http.route(['/my/extenss_ff/<int:id>/submit'], type='http', website=True, method=["POST"])
    def calendar_extenss_ff_submit(self, id,description,access_token=None,edit=None,**kw):
        
        event = request.env['crm.lead'].search([('id','=',id)]).sudo().update({
            'description': description,
        })
        return request.redirect('/my/extenss_ff/%s' % id)