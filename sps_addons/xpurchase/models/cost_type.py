# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CostType(models.Model):
    _name = 'cost.type'
    _description = 'phân loại chi phí'
    _rec_name = 'cost_category'
    _order = 'id desc'

    account_id  = fields.Many2one('account.account','Tài khoản hạch toán')
    cost_category = fields.Char('Tên', required=True)
    cost_type = fields.Selection([
        ('labor', 'Nhân công'),
        ('move', 'Đi lại'),
        ('stay', 'Lưu trú'),
        ('transport', 'Vận chuyển'),
        ('material_out', 'Vật tư dự án'),
        ('material_in', 'Vật tư nhập kho'),
        ('receive_guests', 'Tiếp khách'),
        ('vat', 'VAT'),
        ('iv', 'IV'),
        ('cr', 'CR'),
        ('management', 'Quản lý'),
        ('indirectly', 'Chi phí gián tiếp khác'),
        ('tool', 'Công cụ dụng cụ'),
        ('intermediary', 'Trung gian'),
        ('other', 'Chi phí dự án khác'),
    ], required=True, string='Hạng mục')
    content = fields.Char('Nội dung')
    cost_group = fields.Char('Nhóm chi phí')
    fixed_cost = fields.Boolean('Chi phí cố định')
    variation_cost = fields.Boolean('Chi phí biến đổi')
    active = fields.Boolean(default=True)

    _sql_constraints = [
            ('cost_category', 'UNIQUE(cost_category)', 'Tên loại chi phí không được trùng lặp')
        ]
