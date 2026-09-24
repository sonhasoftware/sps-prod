from odoo import api, fields, models


class EmployeeEthnic(models.Model):
    _name = 'hr.employee.ethnic'

    name = fields.Char(string='Tên', required=1)

