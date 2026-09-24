# -*- coding: utf-8 -*-
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import MissingError, AccessError, ValidationError


class WorkShiftConfig(models.Model):
    _name = 'hr.work.shift.config'
    _description = 'Work shift config'
    _rec_name = 'code'

    name = fields.Char('Name', required=1)
    code = fields.Char('Code', required=1)
    is_leave = fields.Boolean('Is leave?', default=False)
    # is_leave_global = fields.Boolean('Is global timeoff?', default=False)
    # time_start = fields.Float('Start time')
    # time_end = fields.Float('End time')
    line_ids = fields.One2many('hr.work.shift.config.line', 'shift_id', 'Details', copy=1)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_uniq', 'unique (code, company_id)', 'The code of the employee must be unique per company!'),
    ]

    def re_sequence_lines(self):
        for r in self:
            # Check overlap
            data = []
            ranges = []
            time_invalid = False
            for line in r.line_ids:
                value_from = int(line.time_from * 1000)
                value_to = int(line.time_to * 1000)
                # Except new line init data
                if value_from == value_to:
                    time_invalid = True
                    continue
                # Midnight shift
                if line.time_from > line.time_to:
                    value_to = int((line.time_to + 24) * 1000)
                value = range(value_from + 1, value_to)
                data += list(value)
                ranges.append(value)
            if time_invalid or len(data) != len(set(data)):
                raise ValidationError(_('Some items in details are overlap!'))

            # Sort asc
            ranges = sorted(ranges, key=lambda r: r.start)
            orders = {}
            for index, rr in enumerate(ranges):
                start_value = (rr[0] - 1)
                orders[start_value] = index

            # Set sequence
            for line in r.line_ids:
                if line.time_from == line.time_to:
                    continue
                sequence = orders.get(int(line.time_from * 1000))
                if sequence is not None:
                    sequence += 1
                line.sequence = sequence or 1000

    def write(self, vals):
        res = super(WorkShiftConfig, self).write(vals)
        self.re_sequence_lines()
        return res


class WorkShiftConfigLine(models.Model):
    _name = 'hr.work.shift.config.line'
    _description = 'Work shift detail'

    shift_id = fields.Many2one('hr.work.shift.config', 'Shift ID')
    sequence = fields.Integer('Sequence')
    time_from = fields.Float('Start time')
    time_to = fields.Float('End time')


# class WorkShift(models.Model):
#     _name = 'hr.work.shift'
#     _description = 'Work shift'
#
#     name = fields.Char('Name', required=1)
#     date_from = fields.Date('From date', required=1)
#     date_to = fields.Date('To date', required=1)
#     work_days = fields.Integer('Work days')
#     line_ids = fields.One2many('hr.work.shift.line', 'shift_id', 'Lines')
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('confirmed', 'Confirmed'),
#     ], 'State', default='draft')
#     day_start = fields.Integer('Start day', default=0)
#     day_end = fields.Integer('End day', default=0)
#
#     @api.model
#     def action_confirm(self):
#         pass
#
#     @api.onchange('date_from', 'date_to')
#     def onchange_date_range(self):
#         self.day_start = 0
#         self.day_end = 0
#         if not self.date_from or not self.date_to:
#             return
#         if self.date_to < self.date_from:
#             warning = {
#                 'title': _('Date range invalid'),
#                 'message': _('End date must be in the future compare to From date!')}
#             return {'warning': warning}
#         # Date range must in the sam month
#         if self.date_from.month != self.date_to.month:
#             warning = {
#                 'title': _('Date range invalid'),
#                 'message': _('Date range must be in the same month!')}
#             return {'warning': warning}
#         self.day_start = self.date_from.day
#         self.day_end = self.date_to.day
#         # Fake 'onchange' shift line to re-render view with co-respond attributes
#         for line in self.line_ids:
#             line.empty_field = not line.empty_field
#
#
# class WorkShiftLine(models.Model):
#     _name = 'hr.work.shift.line'
#     _description = 'Work shift detail'
#
#     shift_id = fields.Many2one('hr.work.shift', 'Shift')
#     employee_id = fields.Many2one('hr.employee', 'Employee', required=1)
#     employee_code = fields.Char('Employee code', related='employee_id.x_code')
#     project_id = fields.Many2one('project.project', 'Project')
#     empty_field = fields.Boolean('Empty field', store=False)
#     shift_m01 = fields.Many2one('hr.work.shift.config', '01')
#     shift_m02 = fields.Many2one('hr.work.shift.config', '02')
#     shift_m03 = fields.Many2one('hr.work.shift.config', '03')
#     shift_m04 = fields.Many2one('hr.work.shift.config', '04')
#     shift_m05 = fields.Many2one('hr.work.shift.config', '05')
#     shift_m06 = fields.Many2one('hr.work.shift.config', '06')
#     shift_m07 = fields.Many2one('hr.work.shift.config', '07')
#     shift_m08 = fields.Many2one('hr.work.shift.config', '08')
#     shift_m09 = fields.Many2one('hr.work.shift.config', '09')
#     shift_m10 = fields.Many2one('hr.work.shift.config', '10')
#     shift_m11 = fields.Many2one('hr.work.shift.config', '11')
#     shift_m12 = fields.Many2one('hr.work.shift.config', '12')
#     shift_m13 = fields.Many2one('hr.work.shift.config', '13')
#     shift_m14 = fields.Many2one('hr.work.shift.config', '14')
#     shift_m15 = fields.Many2one('hr.work.shift.config', '15')
#     shift_m16 = fields.Many2one('hr.work.shift.config', '16')
#     shift_m17 = fields.Many2one('hr.work.shift.config', '17')
#     shift_m18 = fields.Many2one('hr.work.shift.config', '18')
#     shift_m19 = fields.Many2one('hr.work.shift.config', '19')
#     shift_m20 = fields.Many2one('hr.work.shift.config', '20')
#     shift_m21 = fields.Many2one('hr.work.shift.config', '21')
#     shift_m22 = fields.Many2one('hr.work.shift.config', '22')
#     shift_m23 = fields.Many2one('hr.work.shift.config', '23')
#     shift_m24 = fields.Many2one('hr.work.shift.config', '24')
#     shift_m25 = fields.Many2one('hr.work.shift.config', '25')
#     shift_m26 = fields.Many2one('hr.work.shift.config', '26')
#     shift_m27 = fields.Many2one('hr.work.shift.config', '27')
#     shift_m28 = fields.Many2one('hr.work.shift.config', '28')
#     shift_m29 = fields.Many2one('hr.work.shift.config', '29')
#     shift_m30 = fields.Many2one('hr.work.shift.config', '30')
#     shift_m31 = fields.Many2one('hr.work.shift.config', '31')