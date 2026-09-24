# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class StockBorrowTools(models.Model):
    _name = 'stock.borrow.tools'

    product_id = fields.Many2one('product.product', string='Sản phẩm', readonly=True, ondelete='restrict')
    lot_id = fields.Many2one('stock.production.lot', string='Số Lô/sê-ri',readonly=True)
    receiver_id = fields.Many2one('res.users', string='Người giữ',readonly=True)
    project_id = fields.Many2one('project.project', string='Dự án',readonly=True)
    amount = fields.Float(string='Số lượng',readonly=True)
    standard_price = fields.Float(related='product_id.standard_price', string='Giá')
    value = fields.Float(string='Giá trị', compute='_compute_value')

    @api.model
    def create(self, vals):
        res = super(StockBorrowTools, self).create(vals)
        return res

    @api.depends('amount', 'standard_price')
    def _compute_value(self):
        for i in self:
            i.value = i.amount * i.standard_price
