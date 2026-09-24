# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchasePaymentValue(models.Model):
    _name = 'purchase.payment.value'
    _description = 'Báo cáo tình trạng thanh toán'

    master_key = fields.Integer('Master Key', index=True)
    classification = fields.Char('Phân loại')
    t1 = fields.Float('Jan')
    t2 = fields.Float('Feb')
    t3 = fields.Float('Mar')
    t4 = fields.Float('Apr')
    t5 = fields.Float('May')
    t6 = fields.Float('Jun')
    t7 = fields.Float('Jul')
    t8 = fields.Float('Aug')
    t9 = fields.Float('Sep')
    t10 = fields.Float('Oct')
    t11 = fields.Float('Nov')
    t12 = fields.Float('Dec')
    total = fields.Integer('Total', compute='compute_amount')
    grand_total = fields.Integer('Grand_total',compute='compute_amount')

    def compute_amount(self):
        for r in self:
            r.total = r.t1 + r.t2 + r.t3 + r.t4 + r.t5 + r.t6 + r.t7 + r.t8 + r.t9 + r.t10 + r.t11 + r.t12
            if r.classification == 'Giá trị đã thanh toán':
                r.grand_total = 0
            else:
                r.grand_total = r.total * 1.1


