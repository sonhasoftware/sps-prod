# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Employee(models.Model):
    _inherit = 'hr.employee'

    x_resource_type = fields.Selection([
        ('seniorengsub', 'Kỹ sư / Giám sát cao cấp'),
        ('engsub', 'Kỹ sư / Giám sát'),
        ('teamleader', 'Trưởng nhóm'),
        ('technician', 'Kỹ thuật viên'),
        ('internship', 'Thực tập sinh'),
    ], string='Loại nguồn lực')


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    x_resource_type = fields.Selection([
        ('seniorengsub', 'Kỹ sư / Giám sát cao cấp'),
        ('engsub', 'Kỹ sư / Giám sát'),
        ('teamleader', 'Trưởng nhóm'),
        ('technician', 'Kỹ thuật viên'),
        ('internship', 'Thực tập sinh'),
    ], string='Loại nguồn lực')


class HrJob(models.Model):
    _inherit = 'hr.job'

    x_labor_efficiency = fields.Float(string='Hiệu suất lao động')
