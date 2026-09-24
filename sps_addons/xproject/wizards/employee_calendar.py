# -*- coding: utf-8 -*-
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Calendar(models.TransientModel):
    _name = 'wizard.employee.calendar'
    _description = 'Lịch làm việc'

    date = fields.Date('Ngày làm việc', required=1, default=fields.Date.today())
    line_ids = fields.One2many('wizard.employee.calendar.line', 'calendar_id', 'Chi tiết', readonly=1)

    def get_data(self, date):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self._uid)])
        # employee_id = self.env['hr.employee'].search([('id', '=', 1516)])
        if not employee_id:
            return [(5, 0)]
        entry_lines = self.env['hr.work.entry.line'].search([
            ('entry_id.employee_id', '=', employee_id.id),
            ('entry_id.x_date', '=', date),
        ])
        projects = entry_lines.mapped('project_id')
        res = [(5, 0)]
        for p in projects:
            entries = entry_lines.filtered(lambda s: s.project_id == p)
            a_line_id = entries.sorted(key='time_from')[0]
            z_line_id = entries.sorted(key='time_to')[-1]
            res.append((0, 0, {
                'employee_id': employee_id.id,
                'project_id': p.id,
                'scope': p.x_scope,
                'address': p.x_address,
                'time_from': a_line_id.time_from_raw,
                'time_to': z_line_id.time_to_raw,
            }))
        return res

    @api.model
    def default_get(self, fields_list):
        res = super(Calendar, self).default_get(fields_list)
        if 'date' in res:
            res['line_ids'] = self.get_data(res['date'])
        return res

    def button_view_calendar(self):
        self.ensure_one()
        self.line_ids = self.get_data(self.date)


class CalendarLine(models.TransientModel):
    _name = 'wizard.employee.calendar.line'
    _description = 'Chi tiết lịch làm việc'

    calendar_id = fields.Many2one('wizard.employee.calendar', 'Lịch làm việc')
    employee_id = fields.Many2one('hr.employee', 'Nhân viên')
    job_id = fields.Many2one('hr.job', 'Chức danh', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', 'Phòng ban', related='employee_id.department_id')
    project_id = fields.Many2one('project.project', 'Dự án')
    scope = fields.Char('Phạm vi công việc')
    address = fields.Char('Địa điểm')
    time_from = fields.Float('Từ lúc')
    time_to = fields.Float('Tới lúc')
