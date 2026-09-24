# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo.osv import expression

class Location(models.Model):
    _inherit = 'stock.location'

    x_partner_id = fields.Many2one('res.partner', string='Khánh hàng')
    x_location = fields.Char(string='Địa điểm')
    x_name = fields.Char(string='xname')
    location_id = fields.Many2one(default=lambda self: self.env['stock.location'].search([('id', '=', self.env['stock.warehouse'].search([],limit=1).view_location_id.id)], limit=1).id)
    location_type = fields.Selection([
        ('normal', 'Normal Location'),
        ('damaged', 'Damaged Location'),
        ('scrap', 'Scrap Location'),
        ('storage', 'Storage Location')
    ], string='Location Type', default='normal', help="Specify the type of location.")

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):

        if (self._context.get('location_id', False) and self._context.get('picking_type') in ('type_3','type_4','type_7')) or (self._context.get('location_dest_id', False) and self._context.get('picking_type') in ('type_1','type_2','type_6','type_7','type_8')):
            args = args or []
            domain = []
            records = self.env['stock.location'].sudo().search([('usage', 'in',('internal','inventory'))])
            domain = [('id', 'in', [x.id for x in records])]
            return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

        return super()._name_search(name, args, operator, limit, name_get_uid)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if (self._context.get('location_id', False) and self._context.get('picking_type') in ('type_3', 'type_4', 'type_7')) or (self._context.get('location_dest_id', False) and self._context.get('picking_type') in ('type_1', 'type_2', 'type_6', 'type_7', 'type_8')):
            records = self.env['stock.location'].sudo().search([('usage', 'in', ('internal', 'inventory'))])
            domain.append(('id', 'in', [x.id for x in records]))
        return super(Location, self).search_read(domain, fields, offset, limit, order)

