# -*- coding: utf-8 -*-

from odoo import fields, models, _


class SavingsDepositPopup(models.Model):
    _name = 'savings.deposit.popup'
    _description = "Báo cáo tổng hợp tiền gửi tiết kiệm"

    def action_report_deposit(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo tổng hợp tiền gửi tiết kiệm',
            'view_mode': 'tree',
            'res_model': 'savings.deposit.report',
            'view_id': self.env.ref('account_saving.savings_deposit_report_tree').id,
            'target': 'current',

        }

