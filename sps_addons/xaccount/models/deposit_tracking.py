# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DepositTracking(models.Model):
    _name = 'account.deposit.tracking'
    _description = 'Theo dõi tiền gửi ngân hàng'

    method_settlement = fields.Selection([
        ('collect', 'Thu tiền về tài khoản'),
        ('renew_G', 'Tái tục tiền gốc'),
        ('renew_G&L', 'Tái tục cả gốc và lãi')], string="Phương thức tất toán")
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('official', 'Chính thức'),
        ('settled', 'Đã tất toán'),
        ('has_resumed', 'Đã tái tục')], default="draft", string="state")
    date_sent = fields.Date(string='Ngày gửi', default=fields.Date.today())
    period = fields.Float(string="Kỳ hạn")
    date_type = fields.Selection([('month', 'Tháng'), ('year', 'Năm')], default="month")
    content = fields.Char(string="Nội dung")
    number_contract = fields.Char(string='Số hợp đồng')
    user_create_id = fields.Many2one('res.users', string="Người tạo")
    diary_id = fields.Many2one('account.journal', string='Sổ nhật kí')
    bank_id = fields.Many2one('res.bank', string="Ngân hàng")
    license_type = fields.Selection([
        ('tax', 'Thuế'),
        ('internal', 'Nội bộ ')], string='Phân loại chứng từ')
    code_money = fields.Many2one('code.money', string="Mã khoản tiền")
    deposit_value = fields.Float(string='Giá trị tiền gửi')
    interest_rate = fields.Float(string='Lãi suất(%)')

    date_settlement = fields.Date(string='Ngày tất toán')
    amount_settlement = fields.Float(string="Số tiền khi tất toán")
    note = fields.Char(string="Ghi chú")


    def action_done(self):
        pass

    def action_settlement(self):
        pass
