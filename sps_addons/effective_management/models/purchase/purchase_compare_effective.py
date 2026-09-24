# -*- coding: utf-8 -*-

from datetime import timedelta, date, datetime
import base64

import os
from io import BytesIO
import openpyxl
from openpyxl.styles import NamedStyle, Font, Border, Side
from openpyxl.writer.excel import save_virtual_workbook
from odoo import api, fields, models


class PurchaseCompareEffective(models.Model):
    _name = 'purchase.compare.effective'
    _description = 'Báo cáo giao hàng'

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
    total = fields.Float('Tổng cộng', compute='compute_amount')
    hight_light = fields.Boolean('bôi đậm', compute = 'compute_hight_light')

    def compute_amount(self):
        for r in self:
            r.total = r.t1 + r.t2 + r.t3 + r.t4 + r.t5 + r.t6 + r.t7 + r.t8 + r.t9 + r.t10 + r.t11 + r.t12

    @api.depends('classification')
    def compute_hight_light(self):
        for r in self :
            if r.classification in ('Tổng giá trị ngân sách','Tổng giá trị đã mua','Tổng hiệu quả mua hàng','Người lập dự toán','Người đàm phán'):
                r.hight_light = True
            else:
                r.hight_light =False
