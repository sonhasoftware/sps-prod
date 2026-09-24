# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CashFlowCodeMapping(models.Model):
    _name = 'cash.flow.code.mapping'
    _description = 'Bảng mã khoản tiền'
    _rec_name = 'name'
    _order = 'sequence, name'

    sequence = fields.Integer(string='Thứ tự', default=10)
    name = fields.Char(string='Tên khoản tiền', required=True)
    code = fields.Char(string='Mã', required=True)
    parent = fields.Char(string='Nhóm cha')
    parent_2 = fields.Selection([('thu', 'Thu'), ('chi', 'Chi'), ('ton_cuoi_ky', 'Tiền tồn cuối kỳ')], string='Loại')
    description = fields.Text(string='Mô tả')
