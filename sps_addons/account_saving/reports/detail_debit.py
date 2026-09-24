# -*- coding: utf-8 -*-

from odoo import models, fields


class DetailDebit(models.Model):
    _name = 'detail.debit'
    _description = 'Báo cáo chi tiết công nợ khách hàng / nhà cung cấp'

    master_key = fields.Integer('Master Key', index=True)
    index = fields.Integer('STT')
    date = fields.Char('Ngày chứng từ')
    number = fields.Char('Số chứng từ')
    explain = fields.Char('Diễn giải')
    # tk = fields.Char('TK đối ứng')
    debt = fields.Float("PS nợ")
    credit = fields.Float("PS có")
    code = fields.Char("Mã dự án")

    def view_detail(self):
        acc_move_id = self.env['account.move'].search([('name','=',self.number)])
        result = {
            'type': 'ir.actions.act_window',
            'name': 'Công nợ khách hàng / nhà cung cấp',
            'view_mode': 'form',
            'res_id':acc_move_id.id,
            'res_model': 'account.move',
            'view_id': self.env.ref('xaccount.view_move_form_inherit').id,
            'target': 'target',
        }
        return result
