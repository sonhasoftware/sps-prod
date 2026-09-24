# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError
class PayrollOtherCategogry(models.Model):
    _name = 'hr.payroll.other.category'
    _description = 'Other advantage category'

    name = fields.Char('Name')
    type = fields.Selection([
        ('bonus', 'Bonus'),
        ('fined', 'Fined'),
        ('advance', 'Advance'),
        ('fee', 'Bussiness fee'),
        ('tax_refund', 'Tax refund'),
        ('instant_bonus', 'Instant Bonus'),
    ], 'Type')
    code = fields.Char('Code')
    count_in_unit_price = fields.Boolean(
        'Tính vào đơn giá nhân công',
        help='Nếu tích, khoản thu nhập (type = Bonus) này sẽ được cộng vào '
             'đơn giá nhân công dự án và ghi vào cột "Thưởng NVXS" trên báo cáo lương.',
        default=False,
    )

    @api.constrains('code')
    def constrain_code(self):
        for r in self:
            if r.code:
                records = self.env['hr.payroll.other.category'].search([('code', '=', r.code)])
                if len(records) > 1:
                    raise ValidationError('Mã phải là duy nhất!')


class PayrollOther(models.Model):
    _name = 'hr.payroll.other'
    _inherit = ['mail.thread']
    _description = 'Other advantage'

    name = fields.Char('Name', tracking=1)
    date = fields.Date('Date', tracking=1)
    categ_id = fields.Many2one('hr.payroll.other.category', 'Category', tracking=1)
    categ_type = fields.Selection(related='categ_id.type', string='Type', store=1)
    employee_id = fields.Many2one('hr.employee', 'Employee', tracking=1)
    amount = fields.Float('Amount', tracking=1)
    note = fields.Text('Note', tracking=1)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('canceled', 'Canceled'),
    ], 'State', default='draft', copy=0, tracking=1)

    def action_approve(self):
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'approved'

    def action_cancel(self):
        self.ensure_one()
        if self.state != 'canceled':
            self.state = 'canceled'


class PayrollTaxConfig(models.Model):
    _name = 'hr.payroll.tax.config'
    _description = 'Personal income tax config'

    sequence = fields.Integer('Sequence', default=1)
    income_from = fields.Float('Tax income from')
    income_to = fields.Float('Tax income to')
    factor = fields.Float('Factor')
    last_tax_amount = fields.Float('Last tax amount')


class PayrollOilPrice(models.Model):
    _name = 'hr.payroll.oil.price'
    _description = 'Oil price'
    _order = 'year desc, month desc, id desc'

    name = fields.Char('Name', default='/')
    month = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
    ], 'Month', default=fields.Date.today().month, required=1)
    year = fields.Integer('Year', default=fields.Date.today().year, required=1)
    price = fields.Float('Price', required=1)

    _sql_constraints = [
        ('month_year_uniq', 'unique (month, year)', 'Oil price must be unique per month and year!'),
    ]

    @api.depends('month', 'year')
    @api.onchange('month', 'year')
    def compute_name(self):
        if self.month and self.year:
            self.name = '%s/%s' % (self.month, self.year)


class SalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    _sql_constraints = [
        ('code_uniq', 'unique (code, struct_id)', 'Trùng mã quy tắc trên cùng một cấu trúc lương!'),
    ]


class PayrollOtherHour(models.Model):
    _name = 'hr.payroll.other.hour'
    _inherit = ['mail.thread']
    _description = 'Other hour'
    _order = 'id desc'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', 'Employee', required=1, tracking=1)
    date = fields.Date('Date', required=1, tracking=1)
    project_id = fields.Many2one('project.project', 'Project', required=1, tracking=1)
    hour = fields.Float('Converted Hour', required=1, tracking=1)
    note = fields.Text('Note', tracking=1)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('canceled', 'Canceled'),
    ], 'State', default='draft', copy=0, tracking=1)
    cost_hours = fields.Float('Cost by hours', readonly=1)

    def compute_cost_hours(self):
        def num_days_between(start, end, week_day):
            num_weeks, remainder = divmod((end - start).days, 7)
            if (week_day - start.weekday()) % 7 <= remainder:
                return num_weeks + 1
            else:
                return num_weeks

        def get_theory_hour_of_month_by_day(contract, day):
            is_saturday_half = contract.resource_calendar_id and contract.resource_calendar_id.full_time_required_hours == 44.0
            is_saturday_full = contract.resource_calendar_id and contract.resource_calendar_id.full_time_required_hours == 48.0
            date_from = date(day.year, day.month, 1)
            date_to = date_from + relativedelta(months=1, days=-1)
            num_of_sunday = num_days_between(date_from, date_to, 6)
            num_of_saturday = num_days_between(date_from, date_to, 5)
            num_of_days = (date_to - date_from).days + 1
            if is_saturday_full:
                theory_days = num_of_days - num_of_sunday
            elif is_saturday_half:
                theory_days = num_of_days - num_of_sunday - num_of_saturday * 0.5
            else:
                theory_days = num_of_days - num_of_sunday - num_of_saturday
            return theory_days * 8

        day2month_hours = {}
        for r in self:
            entry_date = r.date
            contracts = self.employee_id._get_contracts(entry_date, entry_date, ['open'])
            if not contracts:
                continue

            contract_id = contracts[0]
            if contract_id.structure_type_id.wage_type == 'hourly':
                cost_hour = contract_id.hourly_wage
            else:
                if entry_date not in day2month_hours:
                    day2month_hours[entry_date] = get_theory_hour_of_month_by_day(contract_id, entry_date)
                cost_hour = contract_id.wage / day2month_hours[entry_date]
            r.cost_hours = cost_hour * r.hour

    def action_approve(self):
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'approved'
            self.compute_cost_hours()

    def action_cancel(self):
        self.ensure_one()
        if self.state != 'canceled':
            self.state = 'canceled'
