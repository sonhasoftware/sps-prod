# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import logging
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_round, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


_SHIFT_FULL_HOURS = 8.0
_SHIFT_DAYTIME_RANGE = [6.0, 22.0]

_logger = logging.getLogger(__name__)

class WorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'


class WorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    name = fields.Char('Name', compute='compute_entry_name', store=0)
    employee_id = fields.Many2one(domain=[])
    x_employee_code = fields.Char('Employee code', related='employee_id.x_code', store=1)
    employee_department_id = fields.Many2one('hr.department', 'Department', related='employee_id.department_id', store=1)
    employee_project_id = fields.Many2one('project.project', 'Project', related='employee_id.x_project_id', store=1)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_approve', 'Manager Approval'),
        # ('hr_approve', 'HR Approval'),
        ('validated', 'Validated'),
        ('conflict', 'Conflict'),
        ('cancelled', 'Cancelled')
    ], default='draft', copy=0)
    
    date_start = fields.Datetime(required=False, string='From')
    color = fields.Integer('Color', compute='compute_color', related="")
    x_line_ids = fields.One2many('hr.work.entry.line', 'entry_id', 'Entry details', copy=1, required=True)
    x_allowance_ids = fields.One2many('hr.work.entry.allowance', 'entry_id', 'Entry allowances', copy=1,required=True)
    x_date = fields.Date('Date')
    x_note = fields.Text('Note')
    x_time_invalid = fields.Boolean('Time invalid?', default=False)
    x_calendar_type = fields.Selection('Calendar type', related='employee_id.x_calendar_type')
    x_weekend = fields.Boolean('Is weekend?', default=False)
    x_ot_allow = fields.Boolean('Is OT allow', default=False)
    x_shift_id = fields.Many2one('hr.work.shift.config', 'Shift')
    x_shift_leave = fields.Boolean('Is leave shift', related='x_shift_id.is_leave')
    x_manager_user_id = fields.Many2one('res.users', 'Project Manager')
    x_is_manager = fields.Boolean('Is Manager', compute='compute_manager')
    x_is_hr = fields.Boolean('Is HR', compute='compute_manager')
    x_rejectable = fields.Boolean('Rejectable', compute='compute_manager')
    # Field to mark an entry as leave
    x_leave = fields.Boolean('Is Leave?', default=False)
    x_hour = fields.Float('Leave hours', copy=0)
    x_leave_type_id = fields.Many2one('hr.leave.type', 'Leave Type', copy=0)
    x_leave_note = fields.Char('Leave note', compute='compute_leave_note')
    x_biz_fee_ids = fields.One2many('hr.work.entry.biz.fee', 'entry_id', 'Business Fee', copy=1,required=True)
    x_total_allowance = fields.Float('Total moves allowance', compute='compute_total', store=1)
    x_total_hours = fields.Float('Total hours', compute='compute_total', store=1)
    x_total_hours_convert = fields.Float('Total hours convert', compute='compute_total', store=1)
    x_total_fee = fields.Float('Total business fee', compute='compute_total', store=1)
    timekeeping_status = fields.Selection([
        ('late_timekeeping', 'Chấm công muộn'),
    ], copy=0, string="Trạng thái chấm công", compute='compute_timekeeping_status')
    time_submit = fields.Datetime()
    is_timekeeping_status = fields.Boolean(default=False)


    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        return super(WorkEntry, self)._search(args, offset=offset, limit=limit, order=order,
                                            count=count, access_rights_uid=access_rights_uid)


    def recovery_compute_costing_hours(self):
        hr_work_entry_ids = self.env['hr.work.entry'].search([
            ('x_date', '>=', self.x_date.replace(day=1)),
            ('x_date', '<', (self.x_date.replace(day=1) + relativedelta(months=1)))
        ])
        for rec in hr_work_entry_ids.x_line_ids:
            rec.compute_costing_hours()
        for hr_w in hr_work_entry_ids:
            hr_w.create_project_wage_cost()

    def compute_timekeeping_status(self):
        current_time = datetime.now()
        for rec in self:
            rec.timekeeping_status = False
            time_diff = False
            if rec.x_date and rec.x_line_ids:
                time_to = max(rec.x_line_ids.mapped('time_to_raw'))
                time_from = min(rec.x_line_ids.mapped('time_from_raw'))
                work_end_time = datetime.combine(rec.x_date, datetime.min.time()) + timedelta(hours=time_to) - timedelta(hours=7)
                if time_to < time_from:
                    work_end_time = work_end_time + timedelta(days=1)
                if rec.state != 'draft' and rec.time_submit:
                    time_diff = rec.time_submit - work_end_time
                elif rec.state == 'draft':
                    time_diff = current_time - work_end_time
                if time_diff and time_diff.days >= 1:
                    rec.timekeeping_status = 'late_timekeeping'
                    rec.is_timekeeping_status = True

    @api.constrains('state')
    def constrain_state_validate(self):
        for r in self.filtered(lambda s: s.state == 'validate'):
            r.x_line_ids.compute_cost_hours()
            r.x_allowance_ids.compute_cost_hours()

    @api.depends('x_line_ids', 'x_allowance_ids', 'x_biz_fee_ids')
    def compute_total(self):
        for r in self:
            r.x_total_allowance = sum([x.hour for x in r.x_allowance_ids])
            r.x_total_hours = sum([x.hour for x in r.x_line_ids])
            r.x_total_hours_convert = sum([x.hour_converted for x in r.x_line_ids])
            r.x_total_fee = sum([x.amount for x in r.x_biz_fee_ids])

    def compute_color(self):
        for r in self:
            #Tạm thời comment
            if r.timekeeping_status == 'late_timekeeping':
                r.color = 3
            elif r.x_leave_type_id:
                r.color = 9
            elif r.work_entry_type_id:
                r.color = r.work_entry_type_id.color
            else:
                r.color = 0

    @api.depends('x_shift_id')
    @api.onchange('x_shift_id')
    def set_default_entry_lines(self):
        lines = [(5, )]
        if self.x_shift_id:
            for line in self.x_shift_id.line_ids.sorted(key=lambda l: l.sequence):
                lines.append((0, 0, {
                    'time_from_raw': line.time_from,
                    'time_to_raw': line.time_to,
                }))
        self.x_line_ids = lines
        self.x_allowance_ids = [(5, )]
        self.x_biz_fee_ids = [(5, )]
        self.onchange_entry_lines()

    def compute_leave_note(self):
        for r in self:
            r.x_leave_note = r.leave_id.name if r.leave_id else False

    @api.depends('x_leave', 'x_shift_id')
    def compute_entry_name(self):
        for r in self:
            if r.x_leave:
                r.name = r.x_leave_type_id.code or r.x_leave_type_id.name
            elif r.x_shift_id:
                r.name = r.x_shift_id.code
            else:
                r.name = 'HC'

    def compute_manager(self):
        is_hr = self.user_has_groups('hr.group_hr_user')
        for r in self:
            r.x_is_manager = r.x_manager_user_id.id == self._uid or (r.employee_id.parent_id and r.employee_id.parent_id.user_id and r.employee_id.parent_id.user_id.id == self._uid)
            r.x_is_hr = is_hr
            if r.x_is_manager and r.state == 'manager_approve':
                r.x_rejectable = True
            elif r.x_is_hr and r.state == 'validated':
                r.x_rejectable = True
            else:
                r.x_rejectable = False

    # tạo chi phí nhân công ở dự án
    def create_project_wage_cost(self, extra_project_ids=None):
        """Recompute wage cost totals for affected projects in the current month.

        ``extra_project_ids`` lets the caller force-recompute projects that are
        no longer referenced by this entry (e.g. khi đổi/xóa dự án trên dòng
        chấm công) để dọn lại số giờ cũ về 0.
        """
        self.ensure_one()
        if not self.x_date:
            return

        project_ids = (self.x_line_ids.project_id | self.x_allowance_ids.project_id).ids
        project_ids = [pid for pid in project_ids if pid]
        if extra_project_ids:
            project_ids = list(set(project_ids) | {pid for pid in extra_project_ids if pid})
        if not project_ids:
            return

        month_start = self.x_date.replace(day=1)
        month_end = month_start + relativedelta(months=1)
        year = int(self.x_date.year)
        month = str(self.x_date.month)
        data = {pid: {'hour_converted': 0.0, 'hour': 0.0, 'costing_hours': 0.0} for pid in project_ids}

        line_domain = [
            ('entry_id.employee_id', '=', self.employee_id.id),
            ('entry_id.x_date', '>=', month_start),
            ('entry_id.x_date', '<', month_end),
            ('entry_id.state', '=', 'validated'),
            ('project_id', 'in', project_ids),
        ]
        line_groups = self.env['hr.work.entry.line'].read_group(
            line_domain, ['hour_converted:sum', 'costing_hours:sum'], ['project_id'], lazy=False
        )
        for group in line_groups:
            project_id = group['project_id'][0] if group.get('project_id') else False
            if not project_id:
                continue
            data.setdefault(project_id, {'hour_converted': 0.0, 'hour': 0.0, 'costing_hours': 0.0})
            data[project_id]['hour_converted'] = group['hour_converted']
            data[project_id]['costing_hours'] = group['costing_hours']

        allowance_domain = [
            ('entry_id.employee_id', '=', self.employee_id.id),
            ('entry_id.x_date', '>=', month_start),
            ('entry_id.x_date', '<', month_end),
            ('entry_id.state', '=', 'validated'),
            ('project_id', 'in', project_ids),
        ]
        allowance_groups = self.env['hr.work.entry.allowance'].read_group(
            allowance_domain, ['hour:sum'], ['project_id'], lazy=False
        )
        for group in allowance_groups:
            project_id = group['project_id'][0] if group.get('project_id') else False
            if not project_id:
                continue
            data.setdefault(project_id, {'hour_converted': 0.0, 'hour': 0.0, 'costing_hours': 0.0})
            data[project_id]['hour'] = group['hour']

        wage_cost_model = self.env['project.wage.cost']
        existing_costs = wage_cost_model.search([
            ('project_id', 'in', list(data.keys())),
            ('employee_id', '=', self.employee_id.id),
            ('year', '=', year),
            ('month', '=', month),
        ])
        cost_map = {wc.project_id.id: wc for wc in existing_costs}

        # Liên kết sẵn đơn giá nhân công (nếu phiếu lương tháng đã có) để
        # dòng chi phí mới hiện ngay giá trị, không phải chờ payslip chạy lại.
        wage_actual = self.env['wage.cost.actual'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '>=', month_start),
            ('date_from', '<', month_end),
        ], order='date_to desc', limit=1)

        for project_id, values in data.items():
            values.setdefault('hour', 0.0)
            values.setdefault('hour_converted', 0.0)
            values.setdefault('costing_hours', 0.0)
            if project_id not in cost_map:
                create_vals = {
                    'project_id': project_id,
                    'employee_id': self.employee_id.id,
                    'year': year,
                    'month': month,
                    'hour_converted': values['hour_converted'],
                    'hour': values['hour'],
                    'costing_hours': values['costing_hours'],
                }
                if wage_actual:
                    create_vals['wage_cost_id'] = wage_actual.id
                wage_cost_model.create(create_vals)
            else:
                write_vals = {
                    'hour_converted': values['hour_converted'],
                    'hour': values['hour'],
                    'costing_hours': values['costing_hours'],
                }
                if wage_actual and not cost_map[project_id].wage_cost_id:
                    write_vals['wage_cost_id'] = wage_actual.id
                cost_map[project_id].write(write_vals)

    # Neu approve phieu cong thi cap nhat vao customer satifaction
    def update_to_customer_satistaction(self):
        # Các đăng ký từng dòng chấm công
        for line in self.x_line_ids:
            if line.project_id:
                # List các line trong customer satisfaction
                if line.project_id.satisfaction_ids:
                    for cs_line in line.project_id.satisfaction_ids:
                        if cs_line.start_date and cs_line.end_date:
                            if (cs_line.start_date <= self.x_date <= cs_line.end_date) and (self.employee_id.id not in cs_line.employee_ids.ids):
                                employee_list = cs_line.employee_ids.ids
                                employee_list.append(self.employee_id.id)
                                cs_line.employee_ids = [(6, 0, employee_list)]


    def button_manager_approve(self):
        self.ensure_one()
        if self.state == 'manager_approve':
            if self.user_has_groups('hr.group_hr_user'):
                self.state = 'validated'
            elif self.x_manager_user_id.id == self._uid:
                self.state = 'validated'
            # Neu approve phieu cong thi cap nhat vao customer satifaction
            self.update_to_customer_satistaction()
            self.create_project_wage_cost()
    
    def button_submit(self):
        self.ensure_one()
        if any(not x.project_id for x in self.x_line_ids):
            raise UserError(_('Anh/chị vui lòng nhập dự án cho tất cả các dòng chấm công'))
        if any(not x.project_id for x in self.x_allowance_ids):
            raise UserError(_('Anh/chị vui lòng nhập dự án cho tất cả các dòng trợ cấp đi lại'))
        if any(not x.project_id for x in self.x_biz_fee_ids):
            raise UserError(_('Anh/chị vui lòng nhập dự án cho tất cả các dòng công tác phí'))
        if self.x_shift_id.is_leave is False:
            if any(self.x_line_ids or self.x_allowance_ids or self.x_biz_fee_ids) is False:
                raise UserError(_('Anh/chị vui lòng nhập thông tin phiếu chấm công'))
        if self.state == 'draft':
            self.state = 'manager_approve'
            if not self.time_submit:
                self.time_submit = datetime.now()

    def delete_submit(self):
        self.sudo().unlink()
        return {
            'type': 'ir.actions.act_window',
            'name': "Chấm Công",
            'res_model': "hr.work.entry",
            'view_mode': 'gantt,tree',
            'target': 'current',  # Options: 'current', 'new', 'inline', 'fullscreen'
        }

    def button_reject(self):
        self.ensure_one()
        if self.leave_id:
            raise UserError(_('Phiếu công này liên kết đến một phiếu nghỉ phép. Vui lòng huỷ phiếu nghỉ phép'))
        if self.state in ['manager_approve', 'validated']:
            self.state = 'draft'
            self.create_project_wage_cost()

    # def button_reject(self):
    #     self.ensure_one()
    #     if self.leave_id:
    #         raise UserError(_('Phiếu công này liên kết đến một phiếu nghỉ phép. Vui lòng huỷ phiếu nghỉ phép'))
    #     if self.state in ['manager_approve', 'validated']:
    #         self.state = 'draft'


    @api.model
    def _set_current_contract(self, vals):
        if not vals.get('contract_id') and vals.get('date_start') and vals.get('date_stop') and vals.get('employee_id'):
            contract_start = fields.Datetime.to_datetime(vals.get('date_stop')).date()
            contract_end = fields.Datetime.to_datetime(vals.get('date_stop')).date()
            employee = self.env['hr.employee'].browse(vals.get('employee_id'))
            contracts = employee.sudo()._get_contracts(contract_start, contract_end,
                                                       states=['open', 'pending', 'close'])
            if not contracts:
                raise ValidationError(
                    _("%s does not have a contract from %s to %s.") % (employee.name, contract_start, contract_end))
            elif len(contracts) > 1:
                raise ValidationError(
                    _("%s has multiple contracts from %s to %s. A work entry cannot overlap multiple contracts.")
                    % (employee.name, contract_start, contract_end))
            return dict(vals, contract_id=contracts[0].id)
        return vals

    @api.model
    def _mark_conflicting_work_entries(self, start, stop):
        return False

    def _check_if_error(self):
        return False

    def re_sequence_lines(self):
        # Check overlap
        data = []
        ranges = []
        time_invalid = False
        for line in self.x_line_ids:
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

        # Mark global overlapped
        self.x_time_invalid = time_invalid or len(data) != len(set(data))
        # Sort asc
        ranges = sorted(ranges, key=lambda r: r.start)
        orders = {}
        for index, r in enumerate(ranges):
            start_value = (r[0] - 1)
            orders[start_value] = index

        # Set sequence
        for line in self.x_line_ids:
            if line.time_from == line.time_to:
                continue
            sequence = orders.get(int(line.time_from * 1000))
            if sequence is not None:
                sequence += 1
            line.sequence = sequence or 1000

        # Recheck overlap each line if global overlapped
        if self.x_time_invalid:
            last_line_data = None
            for line in self.x_line_ids.sorted(key=lambda l: l.sequence):
                if line.sequence > 1000:
                    continue
                value_from = int(line.time_from * 1000)
                value_to = int(line.time_to * 1000)
                # Midnight shift
                if line.time_from > line.time_to:
                    value_to = int((line.time_to + 24) * 1000)
                range_temp = range(value_from + 1, value_to)

                if not last_line_data:
                    last_line_data = range_temp
                else:
                    if len(list(set(last_line_data) & set(range_temp))):
                        line.sequence = 1000
                    last_line_data = range_temp

    def _get_calendar_day_hours(self, calendar, weekday):
        """Tổng số giờ làm theo lịch (resource.calendar) của 1 ngày trong tuần.
        weekday: 0=Thứ 2 ... 5=Thứ 7, 6=Chủ nhật (Python weekday(), trùng dayofweek của Odoo)."""
        if not calendar:
            return 0.0
        return sum(
            a.hour_to - a.hour_from
            for a in calendar.attendance_ids
            if not a.display_type and a.dayofweek and int(a.dayofweek) == weekday
        )

    def calculate_ratio(self):
        if not self.x_date:
            return
        # Check if entry date is a global time off
        global_off_id = self.env['hr.global.off'].sudo().search([
            ('active', '=', True),
            ('date_start', '<=', self.x_date),
            ('date_end', '>=', self.x_date),
        ], limit=1)
        is_global_off = len(global_off_id)
        is_weekend = self.x_weekend
        day_type = 'holiday' if is_global_off else ('weekend' if is_weekend else 'normal')
        # Ngưỡng "đủ ca" = số giờ làm theo LỊCH LÀM VIỆC của từng người cho đúng ngày trong
        # tuần (vượt ngưỡng mới tính OT). Mặc định 8h; nếu ngày đó theo lịch ngắn hơn (vd Thứ 7
        # nửa ngày lịch 44h => 4h) thì hạ ngưỡng tương ứng, nên giờ làm vượt số giờ theo lịch
        # được tính OT. Chỉ áp dụng khi có lương OT, không phải ngày lễ/cuối tuần.
        _shift_full_hour = _SHIFT_FULL_HOURS
        # Tổng giờ làm có đủ ngưỡng đủ ca?
        is_full_shift = sum(line.hour for line in self.x_line_ids) >= _shift_full_hour
        contract_id = self.env['hr.contract'].sudo().browse(self.contract_id.id)
        self.x_ot_allow = contract_id.x_ot_allowed
        if not is_global_off and not is_weekend and contract_id.x_ot_allowed:
            weekday = self.x_date.weekday()
            scheduled_hour = self._get_calendar_day_hours(contract_id.resource_calendar_id, weekday)
            if scheduled_hour:
                _shift_full_hour = scheduled_hour
                is_full_shift = sum(line.hour for line in self.x_line_ids) >= _shift_full_hour

        # Xác định thời điểm mà số giờ làm đạt đủ 8h
        shift_full_point_sec = False
        if is_full_shift:
            total_sec = 0.0
            for line in self.x_line_ids.sorted(key=lambda l: l.sequence):
                start, stop = line.get_time_range(3600)
                time_range = range(int(start), int(stop))
                total_sec_temp = total_sec + len(list(time_range))
                # Đủ 8h?
                if total_sec_temp / 3600 >= _shift_full_hour:
                    diff = total_sec_temp - _shift_full_hour * 3600
                    shift_full_point_sec = int(stop - diff)
                    break
                else:
                    total_sec += len(list(time_range))

        # Lấy cấu hình hệ số công
        factors = self.env['hr.work.factor'].sudo().search([])

        # Tính số giờ quy đổi
        is_daytime_ot = False
        for line in self.x_line_ids.sorted(key=lambda l: l.sequence):
            start, stop = line.get_time_range(3600)

            # Các nhân viên ko được tính OT, thời gian OT sẽ bị loại bỏ
            if not self.x_ot_allow:
                stop = min(stop, shift_full_point_sec or stop)

            time_range_normal = False    # Khoảng giờ thường (cộng dồn <= 8h)
            time_range_normal_day = False    # Khoảng giờ thường ca ngày (cộng dồn <= 8h)
            time_range_normal_nextday = False    # Khoảng giờ thường ca ngày hôm sau
            time_range_normal_night = False    # Khoảng giờ thường ca đêm (cộng dồn <= 8h)
            time_range_ot = False    # Khoảng giờ OT (cộng dồn > 8h)
            time_range_ot_day = False    # Khoảng giờ OT ca ngày (cộng dồn > 8h)
            time_range_ot_nextday = False    # Khoảng giờ OT ca ngày hôm sau
            time_range_ot_night = False    # Khoảng giờ OT ca đêm (cộng dồn > 8h)
            if shift_full_point_sec:
                if start <= shift_full_point_sec:
                    if stop <= shift_full_point_sec:
                        time_range_normal = range(start, stop)
                    else:
                        time_range_normal = range(start, shift_full_point_sec)
                        time_range_ot = range(shift_full_point_sec, stop)
                else:
                    time_range_ot = range(start, stop)
            else:
                time_range_normal = range(start, stop)

            if time_range_normal:
                # Giờ bắt đầu trong khoảng 6h-22h
                if (_SHIFT_DAYTIME_RANGE[0] * 3600) <= time_range_normal.start <= (_SHIFT_DAYTIME_RANGE[1] * 3600):
                    # Giờ kết thúc trước 22h
                    if time_range_normal.stop <= (_SHIFT_DAYTIME_RANGE[1] * 3600):
                        time_range_normal_day = range(time_range_normal.start, time_range_normal.stop)
                    # Giờ kết thúc sau 22h
                    else:
                        time_range_normal_day = range(time_range_normal.start, int(_SHIFT_DAYTIME_RANGE[1] * 3600))
                        time_range_normal_night = range(int(_SHIFT_DAYTIME_RANGE[1] * 3600), time_range_normal.stop)
                # Giờ bắt đầu sau 22h
                else:
                    # Ca đêm chỉ tính đến tối đa <= 6h
                    _shift_next_day = _SHIFT_DAYTIME_RANGE[0] + 24
                    time_range_normal_night = range(time_range_normal.start, min(time_range_normal.stop, int(_shift_next_day * 3600)))
                    # Qua 6h:
                        # Nếu tổng giờ làm trước 8 tiếng => làm thường ban ngày
                        # Nếu trên 8h => số giờ còn lại tính làm thêm ban ngày

                    if int(_shift_next_day * 3600) < time_range_normal.stop:
                        time_range_normal_nextday = range(int(_shift_next_day * 3600), min(time_range_normal.stop, shift_full_point_sec))

            if time_range_ot:
                # Giờ bắt đầu trong khoảng 6h-22h
                if (_SHIFT_DAYTIME_RANGE[0] * 3600) <= time_range_ot.start <= (_SHIFT_DAYTIME_RANGE[1] * 3600):
                    if time_range_ot.stop <= (_SHIFT_DAYTIME_RANGE[1] * 3600):
                        time_range_ot_day = range(time_range_ot.start, time_range_ot.stop)
                    else:
                        time_range_ot_day = range(time_range_ot.start, int(_SHIFT_DAYTIME_RANGE[1] * 3600))
                        time_range_ot_night = range(int(_SHIFT_DAYTIME_RANGE[1] * 3600), time_range_ot.stop)
                # Giờ bắt đầu sau 22h
                else:
                    # Giờ OT có thể là sau 6h sáng => nếu sau 6h thì coi là OT ca ngày
                    split_point = 30 * 3600
                    if split_point < time_range_ot.stop:
                        time_range_ot_night = range(time_range_ot.start, split_point)
                        time_range_ot_nextday = range(max(split_point, shift_full_point_sec), time_range_ot.stop)
                    else:
                        time_range_ot_night = range(time_range_ot.start, time_range_ot.stop)

            line_hours = 0.0
            if time_range_normal_day:
                factor_id = factors.filtered(
                    lambda f: f.type_day == day_type and f.type_time == 'normal' and f.shift == 'day'
                )
                if len(factor_id) == 1:
                    print('Factor:', factor_id.percent)
                    line_hours += (time_range_normal_day.stop - time_range_normal_day.start) * factor_id.percent * 0.01
                else:
                    line_hours += (time_range_normal_day.stop - time_range_normal_day.start)

            if time_range_normal_nextday:
                print('Normal next day:', time_range_normal_nextday.start/3600, time_range_normal_nextday.stop/3600)
                factor_id = factors.filtered(
                    lambda f: f.type_day == day_type and f.type_time == 'normal' and f.shift == 'day'
                )
                if len(factor_id) == 1:
                    print('Factor:', factor_id.percent)
                    line_hours += (time_range_normal_nextday.stop - time_range_normal_nextday.start) * factor_id.percent * 0.01
                else:
                    line_hours += (time_range_normal_nextday.stop - time_range_normal_nextday.start)

            if time_range_ot_day:
                is_daytime_ot = True
                print('OT day:', time_range_ot_day.start/3600, time_range_ot_day.stop/3600)
                factor_id = factors.filtered(
                    lambda f: f.type_day == day_type and f.type_time == 'ot' and f.shift == 'day'
                )
                if len(factor_id) == 1:
                    print('Factor:', factor_id.percent)
                    line_hours += (time_range_ot_day.stop - time_range_ot_day.start) * factor_id.percent * 0.01
                else:
                    line_hours += (time_range_ot_day.stop - time_range_ot_day.start)

            if time_range_normal_night:
                print('Normal night:', time_range_normal_night.start/3600, time_range_normal_night.stop/3600)
                factor_id = factors.filtered(
                    lambda f: f.type_day == day_type and f.type_time == 'normal' and f.shift == 'night' and
                              f.has_ot == (is_daytime_ot and shift_full_point_sec and time_range_normal_night.start >= shift_full_point_sec)
                )
                if len(factor_id) == 1:
                    line_hours += (time_range_normal_night.stop - time_range_normal_night.start) * factor_id.percent * 0.01
                    print('Factor:', factor_id.percent)
                else:
                    line_hours += (time_range_normal_night.stop - time_range_normal_night.start)

            if time_range_ot_night:
                print('OT night:', time_range_ot_night.start/3600, time_range_ot_night.stop/3600)
                factor_id = factors.filtered(
                    lambda f: f.type_day == day_type and f.type_time == 'ot' and f.shift == 'night' and
                              f.has_ot == (is_daytime_ot and shift_full_point_sec and time_range_ot_night.start >= shift_full_point_sec)
                )
                if len(factor_id) == 1:
                    print('Factor:', factor_id.percent)
                    line_hours += (time_range_ot_night.stop - time_range_ot_night.start) * factor_id.percent * 0.01
                else:
                    line_hours += (time_range_ot_night.stop - time_range_ot_night.start)

            if time_range_ot_nextday:
                print('OT next day:', time_range_ot_nextday.start/3600, time_range_ot_nextday.stop/3600)
                factor_id = factors.filtered(
                    lambda f: f.type_day == day_type and f.type_time == 'ot' and f.shift == 'day'
                )
                if len(factor_id) == 1:
                    print('Factor:', factor_id.percent)
                    line_hours += (time_range_ot_nextday.stop - time_range_ot_nextday.start) * factor_id.percent * 0.01
                else:
                    line_hours += (time_range_ot_nextday.stop - time_range_ot_nextday.start)

            # Update converted hour
            line.hour_converted = line_hours / 3600

        # Với NV không hưởng lương OT (làm gói/khoán): giờ công quy đổi trong NGÀY tối đa
        # = số giờ làm theo LỊCH LÀM VIỆC của ngày đó.
        #   - Thứ 2-6: 8h; Thứ 7: 4h (lịch 44h/tuần) / 8h (lịch 48h/tuần)
        #   - Chủ nhật (ngày nghỉ theo lịch): 0h, kể cả có chấm công
        if not self.x_ot_allow:
            weekday = self.x_date.weekday()
            if weekday == 6:  # Chủ nhật
                scheduled = 0.0
            elif weekday == 5:  # Thứ 7
                is_sat_half = contract_id.resource_calendar_id and \
                    contract_id.resource_calendar_id.full_time_required_hours == 44.0
                scheduled = 4.0 if is_sat_half else 8.0
            else:  # Thứ 2 - Thứ 6
                scheduled = 8.0
            # Cắt giảm theo thứ tự ca: các ca đầu được tính trước tới khi đạt trần
            remaining = scheduled
            for line in self.x_line_ids.sorted(key=lambda l: l.sequence):
                if line.hour_converted <= remaining:
                    remaining -= line.hour_converted
                else:
                    line.hour_converted = remaining
                    remaining = 0.0

    @api.onchange('x_line_ids', 'x_weekend', 'x_date', 'employee_id', 'x_shift_id')
    def onchange_entry_lines(self):
        # Check invalid time ranges and re-sequence lines
        self.re_sequence_lines()
        # Compute ratio
        self.calculate_ratio()

    @api.model
    def create(self, vals_list):
        if vals_list.get('x_time_invalid'):
            raise ValidationError(_('Some ranges of time are invalid! Please check lines with red color.'))
        return super(WorkEntry, self).create(vals_list)

    def write(self, vals):
        if len(self) == 1 and vals.get('x_time_invalid'):
            raise ValidationError(_('Some ranges of time are invalid! Please check lines with red color.'))
        res = super(WorkEntry, self).write(vals)
        return res

    @api.model
    def default_get(self, fields):
        vals = super(WorkEntry, self).default_get(fields)
        vals['name'] = '/'
        vals['work_entry_type_id'] = self.env.ref('hr_work_entry.work_entry_type_attendance').id
        if self._context.get('default_date_start'):
            vals['x_date'] = (datetime.strptime(self._context.get('default_date_start'), DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(days=1)).date()

        if self._context.get('x_employee_code'):
            vals['employee_id'] = self.env['hr.employee'].sudo().search([
                ('x_code', '=', self._context['x_employee_code'])
            ], limit=1).id

        return vals

    @api.depends('x_date', 'employee_id')
    @api.onchange('x_date', 'employee_id')
    def onchange_entry_date(self):
        if self.x_date and self.employee_id:
            ids = self.ids if self.ids and isinstance(self.ids[0], int) else []
            # Warning if entry date already existed
            entry_id = self.sudo().search([
                ('employee_id', '=', self.employee_id.id),
                ('x_date', '=', self.x_date),
                ('id', 'not in', ids),
                ('work_entry_type_id', '=', self.env.ref('hr_work_entry.work_entry_type_attendance').id),
            ], limit=1)
            if entry_id:
                raise ValidationError(_('There is already exist an entry item with the same date of %s!') % self.employee_id.name)

            # Hợp đồng hiệu lực
            contract_ids = self.env['hr.contract'].sudo().search([
                ('employee_id', '=', self.employee_id.id),
                ('state', 'in', ['open', 'close']),
                '|',
                '&', ('date_start', '<=', self.x_date), ('date_end', '>=', self.x_date),
                '&', ('date_start', '<=', self.x_date), ('date_end', '=', False),
            ])
            if len(contract_ids) == 1:
                self.x_ot_allow = contract_ids[0].x_ot_allowed
            elif len(contract_ids) > 1:
                active_contracts = contract_ids.filtered(lambda s: s.state == 'open')
                if active_contracts:
                    self.x_ot_allow = active_contracts[0].x_ot_allowed
                else:
                    closed_contracts = contract_ids.filtered(lambda s: s.state == 'close')
                    if closed_contracts:
                        self.x_ot_allow = closed_contracts[0].x_ot_allowed
            else:
                raise ValidationError(_('Employee %s do not have any contract!') % self.employee_id.name)
            # Check if is weekend
            if self.employee_id.x_calendar_type == 'fix':
                weekday = self.x_date.weekday()
                found = self.env['resource.calendar.attendance'].sudo().search([
                    ('calendar_id', '=', self.employee_id.resource_calendar_id.id),
                    ('dayofweek', '=', weekday),
                ])
                self.x_weekend = False if found else True
            elif self.employee_id.x_calendar_type == 'plan':
                self.x_weekend = (self.x_shift_id and self.x_shift_id.is_leave) or False

            # Set default origin date range to full day
            self.date_start = datetime(self.x_date.year, self.x_date.month, self.x_date.day, 0, 0, 0) - timedelta(hours=7)
            self.date_stop = datetime(self.x_date.year, self.x_date.month, self.x_date.day, 23, 59, 59) - timedelta(hours=7)

            # Set employee manager
            if self.employee_id.parent_id and self.employee_id.parent_id.user_id:
                self.x_manager_user_id = self.employee_id.parent_id.user_id

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['x_date'] = False
        return super(WorkEntry, self).copy(default=default)

    def unlink(self):
        current_user = self.env.user
        group_admin = current_user.has_group('hr.group_hr_user')
        for rec in self:
            if not group_admin and (current_user.id != rec.employee_id.user_id.id and current_user.id != rec.x_manager_user_id.id):
                raise UserError(_('Bạn không có quyền xóa phiếu chấm công này!'))

            if rec.state not in ['draft', 'manager_approve']:
                raise UserError(_('Cannot delete validated work entries!'))

        return super(WorkEntry, self).unlink()


class WorkEntryLine(models.Model):
    _name = 'hr.work.entry.line'
    _description = 'Work entry line'
    _order = 'sequence asc, id asc'

    entry_id = fields.Many2one('hr.work.entry', 'Entry ID')
    project_id = fields.Many2one('project.project', 'Project')
    is_next_day = fields.Boolean('Is next day?', compute='compute_hour', store=1)
    time_from_raw = fields.Float('From time', required=1)
    time_from = fields.Float('From time rounded', required=1)
    time_to_raw = fields.Float('To time', required=1)
    time_to = fields.Float('To time rounded', required=1)
    hour = fields.Float('Hour(s)', compute='compute_hour', store=1)
    hour_converted = fields.Float('Hour(s) converted', readonly=1)
    ratio = fields.Float('Ratio', readonly=1)
    sequence = fields.Integer('Sequence', default=1000)
    cost_hours = fields.Float('Cost by hours', readonly=1)
    costing_hours = fields.Float('Costing hours', readonly=1, compute='compute_costing_hours', store=1)


    @api.depends('entry_id','hour','hour_converted')
    def compute_costing_hours(self):
        for rec in self:
            x_date = rec.entry_id.x_date
            contract_id = rec.entry_id.employee_id._get_contracts(x_date, x_date, states=['open', 'close'])
            if contract_id and contract_id[0].x_ot_allowed:
                rec.costing_hours = rec.hour_converted
            else:
                rec.costing_hours = rec.hour


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
        for r in self.filtered(lambda s: s.entry_id):
            contract_id = r.entry_id.contract_id
            if contract_id.structure_type_id.wage_type == 'hourly':
                cost_hour = contract_id.hourly_wage
            else:
                entry_date = r.entry_id.x_date
                if entry_date not in day2month_hours:
                    day2month_hours[entry_date] = get_theory_hour_of_month_by_day(contract_id, entry_date)
                cost_hour = contract_id.wage / day2month_hours[entry_date]
            r.cost_hours = cost_hour * r.hour_converted

    def get_time_range(self, ratio):
        self.ensure_one()
        start = self.time_from
        stop = self.time_to
        if start < _SHIFT_DAYTIME_RANGE[0]:
            start += 24.0
            stop += 24.0
        elif self.time_to < self.time_from:
            stop += 24.0
        start *= ratio
        stop *= ratio
        return int(start), int(stop)

    @api.depends('time_from_raw', 'time_to_raw')
    @api.onchange('time_from_raw', 'time_to_raw')
    def compute_hour(self):
        for r in self:
            if not r.time_from_raw and not r.time_to_raw:
                r.hour = 0.0
                continue
            is_next_day = False
            # Time from rounded
            hour_start_int = float_round(r.time_from_raw, precision_digits=0, rounding_method='DOWN')
            odd = r.time_from_raw - hour_start_int
            if float_compare(odd, 0.0, precision_digits=2) == 0:
                r.time_from = hour_start_int
            else:
                diff = float_compare(odd, 0.5, precision_digits=2)
                if diff <= 0:
                    r.time_from = hour_start_int + 0.5
                elif diff == 1:
                    r.time_from = hour_start_int + 1.0

            # Time to rounded
            hour_end_int = float_round(r.time_to_raw, precision_digits=0, rounding_method='DOWN')
            odd = r.time_to_raw - hour_end_int
            if float_compare(odd, 0.0, precision_digits=2) == 0:
                r.time_to = hour_end_int
            else:
                diff = float_compare(odd, 0.5, precision_digits=2)
                if diff == -1:
                    r.time_to = hour_end_int
                else:
                    r.time_to = hour_end_int + 0.5
            if r.time_from < _SHIFT_DAYTIME_RANGE[0]:
                r.time_from += 24.0
                r.time_to += 24.0
                is_next_day = True
            elif r.time_from > r.time_to:
                r.time_to += 24.0
                is_next_day = True
            r.is_next_day = is_next_day
            r.hour = r.time_to - r.time_from

    def validate_timer(self):
        def get_timer_string(float_time):
            if not isinstance(float_time, float):
                raise ValidationError(_('%s must in type of float!') % float_time)
            h = int(round(float_time, 0))
            m = int(abs(round(float_time - h, 2)) * 60)
            if len(str(h)) == 1:
                h = '0' + str(h)
            if len(str(m)) == 1:
                m = '0' + str(m)
            return '%s:%s' % (h, m)

        for r in self:
            if float_compare(r.time_from_raw, 24, precision_digits=2) == 1 or float_compare(r.time_from_raw, 0, precision_digits=2) == -1:
                time_str = get_timer_string(r.time_from_raw)
                raise ValidationError(_('%s is not valid time! Acceptable time range is 00:00 to 24:00') % time_str)
            if float_compare(r.time_to_raw, 24, precision_digits=2) == 1 or float_compare(r.time_to_raw, 0, precision_digits=2) == -1:
                time_str = get_timer_string((r.time_to_raw))
                raise ValidationError(_('%s is not valid time!! Acceptable time range is 00:00 to 24:00') % time_str)

    def _trigger_project_wage_cost_sync(self, old_by_entry=None):
        """Đồng bộ ngay project.wage.cost cho các phiếu đã validated bị ảnh
        hưởng khi dòng chấm công thay đổi (targeted, nhẹ). ``old_by_entry``
        map entry_id -> set project cũ để dọn số giờ của dự án vừa bị bỏ."""
        old_by_entry = old_by_entry or {}
        for entry in self.mapped('entry_id'):
            if entry.state != 'validated':
                continue
            entry.create_project_wage_cost(
                extra_project_ids=list(old_by_entry.get(entry.id, ())))

    @api.model
    def create(self, vals_list):
        res = super(WorkEntryLine, self).create(vals_list)
        res.validate_timer()
        res._trigger_project_wage_cost_sync()
        return res

    def write(self, vals):
        old_by_entry = {}
        if 'project_id' in vals:
            for r in self:
                if r.project_id:
                    old_by_entry.setdefault(r.entry_id.id, set()).add(r.project_id.id)
        res = super(WorkEntryLine, self).write(vals)
        self.validate_timer()
        self._trigger_project_wage_cost_sync(old_by_entry)
        return res

    def unlink(self):
        old_by_entry = {}
        for r in self:
            if r.entry_id.state == 'validated' and r.project_id:
                old_by_entry.setdefault(r.entry_id.id, set()).add(r.project_id.id)
        entries = self.mapped('entry_id')
        res = super(WorkEntryLine, self).unlink()
        for entry in entries:
            if entry.exists() and entry.state == 'validated':
                entry.create_project_wage_cost(
                    extra_project_ids=list(old_by_entry.get(entry.id, ())))
        return res


class WorkEntryAllowance(models.Model):
    _name = 'hr.work.entry.allowance'
    _description = 'Work entry allowance'

    entry_id = fields.Many2one('hr.work.entry', 'Entry ID')
    project_id = fields.Many2one('project.project', 'Project')
    allowance_id = fields.Many2one('hr.work.entry.allowance.config', 'Allowance reason', required=1)
    hour = fields.Float('Hour', related='allowance_id.hour', store=1)
    cost_hours = fields.Float('Cost by hours', readonly=1)

    def _trigger_project_wage_cost_sync(self, old_by_entry=None):
        """Đồng bộ ngay project.wage.cost khi dòng trợ cấp đi lại của phiếu đã
        validated thay đổi."""
        old_by_entry = old_by_entry or {}
        for entry in self.mapped('entry_id'):
            if entry.state != 'validated':
                continue
            entry.create_project_wage_cost(
                extra_project_ids=list(old_by_entry.get(entry.id, ())))

    @api.model
    def create(self, vals_list):
        res = super(WorkEntryAllowance, self).create(vals_list)
        res._trigger_project_wage_cost_sync()
        return res

    def write(self, vals):
        old_by_entry = {}
        if 'project_id' in vals:
            for r in self:
                if r.project_id:
                    old_by_entry.setdefault(r.entry_id.id, set()).add(r.project_id.id)
        res = super(WorkEntryAllowance, self).write(vals)
        self._trigger_project_wage_cost_sync(old_by_entry)
        return res

    def unlink(self):
        old_by_entry = {}
        for r in self:
            if r.entry_id.state == 'validated' and r.project_id:
                old_by_entry.setdefault(r.entry_id.id, set()).add(r.project_id.id)
        entries = self.mapped('entry_id')
        res = super(WorkEntryAllowance, self).unlink()
        for entry in entries:
            if entry.exists() and entry.state == 'validated':
                entry.create_project_wage_cost(
                    extra_project_ids=list(old_by_entry.get(entry.id, ())))
        return res

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
        for r in self.filtered(lambda s: s.entry_id):
            contract_id = r.entry_id.contract_id
            if contract_id.structure_type_id.wage_type == 'hourly':
                cost_hour = contract_id.hourly_wage
            else:
                entry_date = r.entry_id.x_date
                if entry_date not in day2month_hours:
                    day2month_hours[entry_date] = get_theory_hour_of_month_by_day(contract_id, entry_date)
                cost_hour = contract_id.wage / day2month_hours[entry_date]
            r.cost_hours = cost_hour * r.hour


class WorkEntryAllowanceConfig(models.Model):
    _name = 'hr.work.entry.allowance.config'
    _inherit = ['mail.thread']
    _description = 'Work entry allowance config'

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char('name', required=1, tracking=1)
    hour = fields.Float('Allowance hour(s)', required=1, tracking=1)
    active = fields.Boolean('Active', default=1, tracking=1)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)


class WorkEntryBizFee(models.Model):
    _name = 'hr.work.entry.biz.fee'
    _inherit = ['mail.thread']
    _description = 'Work entry business fee'

    entry_id = fields.Many2one('hr.work.entry', 'Entry ID')
    project_id = fields.Many2one('project.project', 'Project')
    config_id = fields.Many2one('hr.work.entry.biz.config', 'Business fee')
    amount = fields.Float('Amount', related='config_id.amount', store=1, digits='Product Price')


class WorkEntryBizConfig(models.Model):
    _name = 'hr.work.entry.biz.config'
    _inherit = ['mail.thread']
    _description = 'Work entry business fee config'

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char('Name', required=1, tracking=1)
    amount = fields.Float('Amount', required=1, tracking=1)
    active = fields.Boolean('Active', default=1, tracking=1)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
