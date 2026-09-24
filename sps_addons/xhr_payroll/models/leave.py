# -*- coding: utf-8 -*-
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LeaveType(models.Model):
    _inherit = 'hr.leave.type'

    x_pay = fields.Boolean('Payable?', default=1)


class Leave(models.Model):
    _inherit = 'hr.leave'

    x_log_ids = fields.One2many('hr.leave.log', 'leave_id', 'Logs')
    x_phone_status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
    ], 'Điện thoại', default='online')

    @api.depends('date_from', 'date_to', 'employee_id')
    @api.onchange('date_from', 'date_to', 'employee_id')
    def _compute_number_of_days(self):
        global_off_obj = self.env['hr.global.off'].sudo()
        logs = [(5,)]
        if self.request_unit_half:
            logs.append((0, 0, {
                # 'leave_id': r.id,
                'leave_type_id': self.holiday_status_id.id,
                'date': self.request_date_from,
                'number_of_days': 0.5,
            }))
            self.number_of_days = 0.5
        elif self.request_date_from and self.request_date_to and self.employee_id.id:
            total = 0.0
            for index in range(0, (self.request_date_to - self.request_date_from).days + 1):
                date = self.request_date_from + relativedelta(days=index)
                # Check if date is global off
                global_offs = global_off_obj.search_count([
                    ('date_start', '<=', date),
                    ('date_end', '>=', date),
                    ('active', '=', True),
                ])
                if global_offs:
                    continue
                # Check if is weekend
                if self.employee_id.x_calendar_type == 'fix':
                    weekday = date.weekday()
                    found = self.env['resource.calendar.attendance'].sudo().search([
                        ('calendar_id', '=', self.employee_id.resource_calendar_id.id),
                        ('dayofweek', '=', weekday),
                    ])
                    if not found:  # <== mean weekend
                        continue
                elif self.employee_id.x_calendar_type == 'plan':
                    entries = self.env['hr.work.entry'].sudo().search([
                        ('employee_id', '=', self.employee_id.id),
                        ('x_date', '=', date),
                        ('x_shift_id', '!=', False),
                    ])
                    if entries and any(x.x_shift_id.is_leave for x in entries):
                        continue
                day = 1
                if date.weekday() == 5:  # Saturday morning only (44hs/week)
                    contracts = self.employee_id._get_contracts(date, date)
                    if contracts and contracts[0].resource_calendar_id \
                            and contracts[0].resource_calendar_id.full_time_required_hours == 44.0:
                        day = 0.5
                total += day
                logs.append((0, 0, {
                    # 'leave_id': r.id,
                    'leave_type_id': self.holiday_status_id.id,
                    'date': date,
                    'number_of_days': day,
                }))
            self.number_of_days = total
        else:
            self.number_of_days = 0
        self.x_log_ids = logs

    def _cancel_work_entry_conflict(self):
        pass

    def default_get(self, fields):
        res = super(Leave, self).default_get(fields)
        res['holiday_status_id'] = False
        return res

    def action_validate(self):
        super(Leave, self).action_validate()
        # Create leave work entries
        entry_obj = self.env['hr.work.entry']
        for leave in self:
            for log in leave.x_log_ids:
                contracts = leave.employee_id._get_contracts(log.date, log.date)
                if not contracts:
                    raise UserError(_('Employee %s do not have any contract running on %s') % (
                        leave.employee_id.name,
                        log.date.strftime('%d/%m/%Y')
                    ))
                # leave_entries = entry_obj.search([
                #     ('employee_id', '=', leave.employee_id.id),
                #     ('x_date', '=', log.date),
                #     ('x_leave_type_id', '=', leave.holiday_status_id.id),
                # ])
                # if leave_entries:
                #     raise UserError(_('There are some leave entries with the same leave type on %s of ' + leave.employee_id.name) % (
                #         log.date.strftime('%d/%m/%Y')
                #     ))
                entry_obj.create({
                    'employee_id': leave.employee_id.id,
                    'contract_id': contracts[0].id,
                    'x_date': log.date,
                    'x_leave': True,
                    'x_hour': log.number_of_days * 8,
                    'x_note': leave.name or None,
                    'date_start': datetime.combine(log.date, datetime.min.time()),
                    'date_stop': datetime.combine(log.date, datetime.min.time()) + timedelta(seconds=1),
                    'work_entry_type_id': leave.holiday_status_id.work_entry_type_id.id,
                    'leave_id': leave.id,
                    'x_leave_type_id': leave.holiday_status_id.id,
                    'state': 'validated',
                })
        return True

    def write(self, vals):
        return super(Leave, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        res = super(Leave, self).create(vals_list)
        date_from = vals_list[0].get('request_date_from')
        date_to = vals_list[0].get('request_date_to')
        self._cr.execute(
            f'''select id from hr_contract where employee_id ={vals_list[0].get('employee_id')} and date_start <='{date_from}' and date_end >='{date_to}' and state not in ('draft','cancel') ''')
        rec = self._cr.dictfetchall()
        if not rec:
            raise UserError('Nhân viên không có hợp đồng khả dụng trong khoảng thời gian xin nghỉ')
        return res


class LeaveLog(models.Model):
    _name = 'hr.leave.log'
    _description = 'Leave logs'

    leave_id = fields.Many2one('hr.leave', 'Master ID')
    leave_type_id = fields.Many2one('hr.leave.type', 'Leave type')
    date = fields.Date('Leave date')
    number_of_days = fields.Float('Number of days')
