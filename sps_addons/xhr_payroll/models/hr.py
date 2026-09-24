# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import logging

from odoo import models, fields, api
from odoo.exceptions import MissingError, AccessError

_logger = logging.getLogger(__name__)


class WorkFactor(models.Model):
    _name = 'hr.work.factor'
    _inherit = ['mail.thread']
    _description = 'Work factor'

    name = fields.Char('Name', tracking=1)
    type_day = fields.Selection([
        ('normal', 'Normal working day'),
        ('weekend', 'Weekend off'),
        ('holiday', 'Holiday'),
    ], 'Type of day', required=1, tracking=1)
    type_time = fields.Selection([
        ('normal', 'Normal time'),
        ('ot', 'Over time'),
    ], 'Type of time', required=1, tracking=1)
    # time_start = fields.Float('Start time', required=1, tracking=1)
    # time_end = fields.Float('End time', required=1, tracking=1)
    has_ot = fields.Boolean('Has Overtime?', default=False, tracking=1)
    shift = fields.Selection([
        ('day', 'Daytime (6:00 - 22:00)'),
        ('night', 'Nighttime (22:00 - 6:00)'),
    ], 'Shift', default='day', required=1, tracking=1)
    percent = fields.Float('Percent (%)', required=1, tracking=1)
    note = fields.Text('Note')


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _get_contracts(self, date_from, date_to, states=['open'], kanban_state=False):
        res = super(Employee, self)._get_contracts(date_from=date_from, date_to=date_to, states=states, kanban_state=kanban_state)
        if self._context.get('x_generate_batch_payslip'):
            records = self.env['hr.contract'].browse()
            employee_id2contract_id = {}
            for r in res.sorted(key='id', reverse=True):
                if r.employee_id.id not in employee_id2contract_id:
                    records |= r
                    employee_id2contract_id[r.employee_id.id] = r.id
            return records
        return res

    # Working hours
    x_calendar_type = fields.Selection([
        ('fix', 'Fix by calendar'),
        ('plan', 'Fix by plan'),
        ('dynamic', 'Dynamic input'),
    ], 'Work hour type', default='fix', required=1)

    def generate_work_entries(self, date_start, date_stop):
        return False

    def _cron_generate_daily_work_entry(self):
        today = date.today()
        self._generate_daily_work_entry(str(today))


    def _generate_daily_work_entry(self, date_daily):
        if date_daily:
            today = date(int(date_daily[0:4]), int(date_daily[5:7]), int(date_daily[8:10]))
        else:
            today = date.today()
        # Các mục nghỉ lễ trong tháng
        global_offs = self.env['hr.global.off'].sudo().search([
            ('active', '=', True),
            ('date_start', '<=', today),
            ('date_end', '>=', today)
        ])
        if global_offs:
            return

        employees = self.search([
            ('x_calendar_type', '=', 'fix'),
            ('active', '=', True),
        ])
        weekday = today.weekday()
        weekday_str = '%s' % weekday
        entry_obj = self.env['hr.work.entry']
        sql = '''
                select hwe.employee_id
                from hr_work_entry hwe
                where 1=1
                    and hwe.employee_id in %s
                    and hwe.x_date = '%s'
                    and hwe.active = 't'
        		    and hwe.state != 'cancelled'
                '''
        self._cr.execute(sql % (tuple(employees.ids + [0, 0]), today))
        recs = self._cr.fetchall()
        exclude_employees = [r[0] for r in recs]

        for e in employees:
            if e.id in exclude_employees:
                continue
            contracts = e._get_contracts(today, today, ['open'])
            if not contracts:
                continue
            calendar_id = contracts[0].resource_calendar_id
            entry_lines = []
            for item in calendar_id.attendance_ids.filtered(lambda x: x.dayofweek == weekday_str):
                entry_lines.append((0, 0, {
                    'time_from': item.hour_from,
                    'time_to': item.hour_to,
                    'time_from_raw': item.hour_from,
                    'time_to_raw': item.hour_to,
                    'project_id': e.x_project_id.id,
                }))
            if not entry_lines:
                continue
            vals = {
                'x_date': today,
                'employee_id': e.id,
                'contract_id': contracts[0].id,
                'x_ot_allow': contracts[0].x_ot_allowed,
                'date_start': datetime(today.year, today.month, today.day, 0, 0, 0) - timedelta(hours=7),
                'date_stop': datetime(today.year, today.month, today.day, 23, 59, 59) - timedelta(hours=7),
                'x_line_ids': entry_lines,
                'state': 'draft',
            }
            if e.parent_id and e.parent_id.user_id:
                vals['x_manager_user_id'] = e.parent_id.user_id.id
            else:
                vals['x_manager_user_id'] = e.user_id.id
            entry_id = entry_obj.create(vals)
            entry_id.x_line_ids.compute_hour()
            entry_id.onchange_entry_lines()
            _logger.info('Create daily work entry for employee %s with data %s' % (e.name, vals))
