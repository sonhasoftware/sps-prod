# -*- coding: utf-8 -*-

from odoo import api, models, fields


class CashReport(models.Model):
    _name = 'cash.report'
    _description = 'Báo cáo Sổ quỹ tiền mặt'

    master_key = fields.Integer('Master Key', index=True)
    number_license = fields.Char("Số hiệu chứng từ")
    date = fields.Date('Ngày')
    receive_or_pay = fields.Char('Người nhận or nộp tiền')
    name = fields.Char('Tên khách hàng/nhà thầu')
    explain = fields.Char('Diễn giải')
    code_project = fields.Char('Mã dự án')
    type_license = fields.Char('Phân loại chứng từ')
    code = fields.Char('Mã khoản tiền')
    type = fields.Char('Hình thức Thu/Chi')
    thu = fields.Float('Thu')
    chi = fields.Float('Chi')
    so_du = fields.Float('Số dư')
    note = fields.Char('Ghi chú')

    # @api.depends('chi', 'thu')
    # def compute_so_du(self):
    #     luy_ke = 0.0
    #     for r in self:
    #         so_du_line = r.thu - r.chi + luy_ke
    #         r.so_du = so_du_line
    #         luy_ke = so_du_line
