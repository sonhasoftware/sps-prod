# -*- coding: utf-8 -*-

from datetime import timedelta, date, datetime
import base64

import os
from io import BytesIO
import openpyxl
from openpyxl.styles import NamedStyle, Font, Border, Side
from openpyxl.writer.excel import save_virtual_workbook
from odoo import api, fields, models


class EmployeeToolsValue(models.Model):
    _name = 'employee.tools.value.report'
    _description = 'Báo cáo giá trị công cụ nhân viên quản lý'

    master_key = fields.Integer('Master Key', index=True)
    index = fields.Integer('STT')
    login = fields.Char('Short name')
    name = fields.Char('Full name')
    amount_bf = fields.Integer('Amount_before')
    t1 = fields.Integer('Jan')
    t2 = fields.Integer('Feb')
    t3 = fields.Integer('Mar')
    t4 = fields.Integer('Apr')
    t5 = fields.Integer('May')
    t6 = fields.Integer('Jun')
    t7 = fields.Integer('Jul')
    t8 = fields.Integer('Aug')
    t9 = fields.Integer('Sep')
    t10 = fields.Integer('Oct')
    t11 = fields.Integer('Nov')
    t12 = fields.Integer('Dev')
    this_year = fields.Integer('This year' ,compute='compute_amount')
    total = fields.Integer('Tổng cộng',compute='compute_amount')
    remark = fields.Char('Remark')

    def compute_amount(self):
        for r in self:
            r.this_year = r.t1 + r.t2 + r.t3 + r.t4 + r.t5 + r.t6 + r.t7 + r.t8 + r.t9 + r.t10 + r.t11 + r.t12
            r.total = r.amount_bf + r.this_year
