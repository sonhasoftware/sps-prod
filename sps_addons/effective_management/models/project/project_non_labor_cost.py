# -*- coding: utf-8 -*-

from datetime import timedelta, date, datetime
import base64

import os
from io import BytesIO
import openpyxl
from openpyxl.styles import NamedStyle, Font, Border, Side
from openpyxl.writer.excel import save_virtual_workbook
from odoo import api, fields, models


class NonLaborCost(models.Model):
    _name = 'project.non.labor.cost'
    _description = 'báo cáo ngân sách ngoài nhân công'

    master_key = fields.Integer('Master Key', index=True)
    project_code = fields.Char('Mã dự án')
    project_name = fields.Char('Tên dự án')
    date_close = fields.Char('Ngày đóng ')
    budget = fields.Float('Ngân sách')
    expenses_company = fields.Float('Chi phí thuế TNDN')
    expenses = fields.Float('Chi phí thực tế')
    dif = fields.Float('Chênh lệch', compute = 'compute_value', store=True)
    result = fields.Char('Dự án hiệu quả', compute = 'compute_value', store=True)

    def compute_value(self):
        for r in self:
            res = r.budget - r.expenses - r.expenses_company
            r.dif =res
            if res >= 0:
                r.result = 'Profit'
            else:
                r.result = 'Loss'