# -*- coding: utf-8 -*-

from odoo import models, fields


class SavingsDepositReport(models.Model):
    _name = 'savings.deposit.report'
    _description = 'Báo cáo tổng hợp tiền gửi tiết kiệm'

    sent_date = fields.Date('Ngày gửi')
    content = fields.Char('Nội dung')
    number_contract = fields.Integer('Số hợp đồng')
    value_money = fields.Float('Giá trị tiền gửi')
    interest_rate = fields.Float('Lãi suất')
    settlement_date = fields.Date('Ngày tất toán')
    money_settlement = fields.Float('Số tiền sau tất toán')
    bank = fields.Char('Ngân hàng')
    note = fields.Char('Ghi chú')

