# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api

class OtherExpenses(models.Model):
    _name = 'other.expenses'

    type = fields.Selection([('uniform', 'Đồng phục'), ('health', 'An toàn, Sức khỏe'), ('holiday', 'Thưởng ngày lễ'),
                             ('travel', 'Du lịch, tiệc cuối năm')], string='Loại chi phí')
    detail = fields.Char(string='Phân loại chi tiết khoản chi')
    price = fields.Integer(string='Đơn giá')
    job_apply = fields.Many2many('hr.job', 'hr_job_other_expenses_rel', 'other_expenses_id', 'hr_job_id', "Jobs")
    start_year = fields.Integer()
    end_year = fields.Integer()
    active = fields.Boolean()
    gender = fields.Selection([('male', 'Nam'), ('female', 'Nữ')], string='Giới tính')
