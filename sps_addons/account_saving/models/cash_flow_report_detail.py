# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class CashFlowReportDetail(models.Model):
    _name = 'cash.flow.report.detail'
    _rec_name = 'year'
    _order = 'year desc, parent_2_order, sequence'

    year = fields.Integer(string='Năm')
    sequence = fields.Integer(string='Thứ tự')
    code = fields.Char(string='Mã')
    name = fields.Char(string='Diễn giải')
    parent = fields.Char(string='Nhóm cha')
    parent_2 = fields.Selection([('thu', 'Thu'), ('chi', 'Chi'), ('ton_cuoi_ky', 'Tiền tồn cuối kỳ')], string='Loại')
    parent_2_order = fields.Integer(string='Thứ tự loại', compute='_compute_parent_2_order', store=True)
    t1 = fields.Float(string='Tháng 1')
    t2 = fields.Float(string='Tháng 2')
    t3 = fields.Float(string='Tháng 3')
    t4 = fields.Float(string='Tháng 4')
    t5 = fields.Float(string='Tháng 5')
    t6 = fields.Float(string='Tháng 6')
    t7 = fields.Float(string='Tháng 7')
    t8 = fields.Float(string='Tháng 8')
    t9 = fields.Float(string='Tháng 9')
    t10 = fields.Float(string='Tháng 10')
    t11 = fields.Float(string='Tháng 11')
    t12 = fields.Float(string='Tháng 12')
    total = fields.Float(string='Tổng cộng', compute='_compute_total', store=True)
    radio = fields.Float(string='Tỉ lệ(%)',compute='_compute_radio')

    @api.depends('t1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9', 't10', 't11', 't12')
    def _compute_total(self):
        for record in self:
            record.total = (record.t1 + record.t2 + record.t3 + record.t4 + 
                          record.t5 + record.t6 + record.t7 + record.t8 + 
                          record.t9 + record.t10 + record.t11 + record.t12)
            if record.parent_2 == 'ton_cuoi_ky' and record.code not in ['SC']:
                record.total = record.t12

    def _compute_radio(self):
        for rec in self:
            rec.radio = 0
            if rec.parent_2 == 'chi':
                total = sum(rec.search([('parent_2', '=', 'chi')]).mapped('total'))
                rec.radio = (rec.total/total)*100
            elif  rec.parent_2 == 'thu':
                total = sum(rec.search([('parent_2', '=', 'thu')]).mapped('total'))
                rec.radio = (rec.total / total) * 100
            elif rec.parent_2 == 'ton_cuoi_ky' and rec.code not in ['SC','TCBS']:
                total = sum(rec.search([('parent_2', '=', 'ton_cuoi_ky'),('code','!=','SC')]).mapped('total'))
                rec.radio = (rec.total / total) * 100

    @api.depends('parent_2')
    def _compute_parent_2_order(self):
        for record in self:
            if record.parent_2 == 'thu':
                record.parent_2_order = 1
            elif record.parent_2 == 'chi':
                record.parent_2_order = 2
            elif record.parent_2 == 'ton_cuoi_ky':
                record.parent_2_order = 3
            else:
                record.parent_2_order = 999
