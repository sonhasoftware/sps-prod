# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_round
from datetime import datetime


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get('type') in ('type_4', 'type_5', 'type_6'):
            args = args or []
            domain1 = ['&'] + args + ['&', ('default_code', operator, name)]
            domain2 = ['&'] + args + ['&', ('name', operator, name)]
            records = self.env['product.template'].sudo().search([
                ('x_type', '=', 'product'),
                ('x_product_type', '=', 'tools'),
            ])
            domain1.append(('product_tmpl_id', 'in', [x.id for x in records]))
            domain2.append(('product_tmpl_id', 'in', [x.id for x in records]))
            return self._search(expression.OR([domain1, domain2]), limit=limit, access_rights_uid=name_get_uid)

        elif self._context.get('type') in ('type_2', 'type_3', 'type_8'):
            args = args or []
            domain1 = ['&'] + args + ['&', ('default_code', operator, name)]
            domain2 = ['&'] + args + ['&', ('name', operator, name)]
            records = self.env['product.template'].sudo().search([
                ('x_type', '=', 'product'),
                ('x_product_type', '=', 'supplies'),
            ])
            domain1.append(('product_tmpl_id', 'in', [x.id for x in records]))
            domain2.append(('product_tmpl_id', 'in', [x.id for x in records]))

            return self._search(expression.OR([domain1, domain2]), limit=limit, access_rights_uid=name_get_uid)
        return super()._name_search(name, args, operator, limit, name_get_uid)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self._context.get('type') in ('type_4', 'type_5', 'type_6'):
            records = self.env['product.template'].sudo().search([
                ('x_type', '=', 'product'),
                ('x_product_type', '=', 'tools'),
            ])
            domain.append(('product_tmpl_id', 'in', [x.id for x in records]))
        elif self._context.get('type') in ('type_2', 'type_3', 'type_8'):
            records = self.env['product.template'].sudo().search([
                ('x_type', '=', 'product'),
                ('x_product_type', '=', 'supplies'),
            ])
            domain.append(('product_tmpl_id', 'in', [x.id for x in records]))
        return super(ProductProduct, self).search_read(domain, fields, offset, limit, order)

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_quant_loc.append(('location_id.location_type', 'not in', ['damaged', 'scrap']))
        domain_move_in_loc.append(('location_id.location_type', 'not in', ['damaged', 'scrap']))
        domain_move_out_loc.append(('location_id.location_type', 'not in', ['damaged', 'scrap']))

        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
        dates_in_the_past = False
        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
            domain_move_out += [('restrict_partner_id', '=', owner_id)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if from_date:
            date_date_expected_domain_from = [('date', '>=', from_date)]
            domain_move_in += date_date_expected_domain_from
            domain_move_out += date_date_expected_domain_from
        if to_date:
            date_date_expected_domain_to = [('date', '<=', to_date)]
            domain_move_in += date_date_expected_domain_to
            domain_move_out += date_date_expected_domain_to

        Move = self.env['stock.move'].with_context(active_test=False)
        Quant = self.env['stock.quant'].with_context(active_test=False)
        domain_move_in_todo = [('state', 'in',
                                ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
        domain_move_out_todo = [('state', 'in',
                                 ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in
                            Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'],
                                            orderby='id'))
        moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in
                             Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'],
                                             orderby='id'))
        quants_res = dict((item['product_id'][0], (item['quantity'], item['reserved_quantity'])) for item in
                          Quant.read_group(domain_quant, ['product_id', 'quantity', 'reserved_quantity'],
                                           ['product_id'], orderby='id'))
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
            domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
            moves_in_res_past = dict((item['product_id'][0], item['product_qty']) for item in
                                     Move.read_group(domain_move_in_done, ['product_id', 'product_qty'], ['product_id'],
                                                     orderby='id'))
            moves_out_res_past = dict((item['product_id'][0], item['product_qty']) for item in
                                      Move.read_group(domain_move_out_done, ['product_id', 'product_qty'],
                                                      ['product_id'], orderby='id'))

        res = dict()
        for product in self.with_context(prefetch_fields=False):
            product_id = product.id
            if not product_id:
                res[product_id] = dict.fromkeys(
                    ['qty_available', 'free_qty', 'incoming_qty', 'outgoing_qty', 'virtual_available'],
                    0.0,
                )
                continue
            rounding = product.uom_id.rounding
            res[product_id] = {}
            if dates_in_the_past:
                qty_available = quants_res.get(product_id, [0.0])[0] - moves_in_res_past.get(product_id,
                                                                                             0.0) + moves_out_res_past.get(
                    product_id, 0.0)
            else:
                qty_available = quants_res.get(product_id, [0.0])[0]
            reserved_quantity = quants_res.get(product_id, [False, 0.0])[1]
            res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
            res[product_id]['free_qty'] = float_round(qty_available - reserved_quantity, precision_rounding=rounding)
            res[product_id]['incoming_qty'] = float_round(moves_in_res.get(product_id, 0.0),
                                                          precision_rounding=rounding)
            res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(product_id, 0.0),
                                                          precision_rounding=rounding)
            res[product_id]['virtual_available'] = float_round(
                qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'],
                precision_rounding=rounding)

        return res

    def action_open_quants(self):
        action = super(ProductProduct, self).action_open_quants()
        valid_quants = self.env['stock.quant'].search([
            ('product_id', 'in', self.ids),
            ('location_id.location_type', 'not in', ['damaged', 'scrap'])
        ])
        action['domain'] = [('id', 'in', valid_quants.ids)]
        return action


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    standard_price = fields.Float(store=True)
    status_warning = fields.Selection([
        ('normal', 'Bình thường'),
        ('warning', 'Cảnh báo'),
        ('overdue', 'Quá hạn')
    ], string='Phân loại cảnh báo', compute='compute_status_warning')
    color_code = fields.Char()

    def compute_status_warning(self):
        now = datetime.now().date()
        for rec in self:
            if not rec.use_expiration_date:
                rec.status_warning = False
                continue
                
            rec.status_warning = 'normal'
            stock_lots = self.env['stock.production.lot'].search([
                ('product_id', '=', rec.product_variant_id.id)])
            if not stock_lots:
                continue
            status_priority = []
            
            for lot in stock_lots:
                if lot.expiration_date:
                    expiration_date = lot.expiration_date.date()
                    if expiration_date <= now:
                        status_priority.append(3)
                        continue
                if lot.alert_date:
                    alert_date = lot.alert_date.date()
                    if alert_date <= now:
                        status_priority.append(2)
            
            if status_priority:
                max_priority = max(status_priority)
                if max_priority == 3:
                    rec.status_warning = 'overdue'
                elif max_priority == 2:
                    rec.status_warning = 'warning'