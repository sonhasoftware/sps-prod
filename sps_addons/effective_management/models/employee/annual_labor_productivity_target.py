# -*- coding: utf-8 -*-
import datetime as dt
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AnnualLaborProductivityTarget(models.Model):
    _name = 'annual.labor.productivity.target'
    _description = 'Annual labor productivity target'
    _order = 'employee_id, year desc'

    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True, index=True)
    year = fields.Char(string='Năm',required=True)
    target = fields.Float('Hiệu suất (%)', required=True, help="Annual productivity target percentage")

    @api.constrains('employee_id', 'year')
    def _check_unique_employee_year(self):
        for record in self:
            domain = [
                ('employee_id', '=', record.employee_id.id),
                ('year', '=', record.year),
                ('id', '!=', record.id)
            ]
            existing = self.search(domain)
            if existing:
                raise ValidationError(f'Nhân viên {record.employee_id.name} đã có mục tiêu hiệu suất cho năm {record.year}!')

    @api.constrains('target')
    def _check_target_percentage(self):
        for record in self:
            if record.target < 0 or record.target > 100:
                raise ValidationError('Hiệu suất (%) phải nằm trong khoảng từ 0% đến 100%!')

    def _change_project_wage_cost(self):
        for rec in self:
            wage_cost_ids = self.env['project.wage.cost'].sudo().search([('employee_id', '=', rec.employee_id.id), ('year', '=', rec.year)])
            wage_cost_ids.compute_cost()

    def write(self, values):
        res = super(AnnualLaborProductivityTarget, self).write(values)
        self._change_project_wage_cost()
        return res

    @api.model
    def create(self, values):
        res = super(AnnualLaborProductivityTarget, self).create(values)
        res._change_project_wage_cost()
        return res