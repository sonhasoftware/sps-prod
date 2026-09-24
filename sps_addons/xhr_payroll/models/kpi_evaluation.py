# -*- coding: utf-8 -*-
import logging
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class HrKpiEvaluation(models.Model):
    """Đánh giá KPI theo đợt lương.

    Mỗi bản ghi = 1 nhân viên / 1 đợt lương. Tự sinh khi tạo đợt lương (cùng lúc
    sinh phiếu lương), điểm mặc định 1000 (=100%). Quản lý nhập điểm sau, rồi tính
    lại phiếu lương để "Lương KPI thực tế" chảy vào lương (P4).

    Công thức (mẫu nội bộ từ 01/07/2026):
        hệ số giờ  = giờ trả lương thực tế (trừ OT & đi lại) / giờ công tiêu chuẩn
        Lương KPI  = KPI định mức x hệ số giờ x (điểm / 1000)
    """
    _name = 'hr.kpi.evaluation'
    _description = 'Đánh giá KPI'
    _order = 'date_from desc, employee_id'

    payslip_run_id = fields.Many2one('hr.payslip.run', 'Đợt lương', ondelete='cascade', index=True)
    payslip_id = fields.Many2one('hr.payslip', 'Phiếu lương', ondelete='set null')
    employee_id = fields.Many2one('hr.employee', 'Nhân viên', required=True, index=True)
    contract_id = fields.Many2one('hr.contract', 'Hợp đồng')
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    date_from = fields.Date('Từ ngày', required=True)
    date_to = fields.Date('Đến ngày', required=True)

    score = fields.Integer('Điểm đánh giá', default=1000,
                           help="Điểm đánh giá hiệu suất, thang 0 - 1000 (1000 = 100%).")
    kpi_norm = fields.Monetary('KPI định mức', currency_field='currency_id')
    paid_hours = fields.Float('Tổng giờ trả lương thực tế', digits=(16, 2),
                              help="Không bao gồm giờ OT và giờ đi lại.")
    standard_hours = fields.Float('Tổng giờ công tiêu chuẩn', digits=(16, 2),
                                  help="Theo giờ làm việc tiêu chuẩn của lịch làm việc.")
    coefficient = fields.Float('Hệ số giờ làm việc', digits=(16, 4),
                               compute='_compute_kpi', store=True)
    kpi_salary = fields.Monetary('Lương KPI thực tế', currency_field='currency_id',
                                 compute='_compute_kpi', store=True)

    _sql_constraints = [
        ('uniq_run_employee', 'unique(payslip_run_id, employee_id)',
         'Mỗi nhân viên chỉ có 1 đánh giá KPI trong 1 đợt lương.'),
    ]

    @api.constrains('score')
    def _check_score(self):
        for rec in self:
            if rec.score < 0 or rec.score > 1000:
                raise ValidationError(_('Điểm đánh giá phải trong khoảng 0 - 1000.'))

    def write(self, vals):
        # Đợt lương đã xác nhận (đóng) -> khóa sửa đánh giá KPI (điểm).
        if 'score' in vals:
            for rec in self:
                if rec.payslip_run_id.state == 'close':
                    raise UserError(_(
                        'Đợt lương "%s" đã xác nhận (đóng) - không được sửa đánh giá KPI.'
                    ) % (rec.payslip_run_id.name or ''))
        return super(HrKpiEvaluation, self).write(vals)

    @api.depends('paid_hours', 'standard_hours', 'kpi_norm', 'score')
    def _compute_kpi(self):
        for rec in self:
            # Dùng tỷ lệ CHƯA làm tròn để tính lương (field coefficient chỉ làm tròn
            # 4 chữ số để hiển thị) -> khớp số liệu mẫu nội bộ.
            ratio = (rec.paid_hours / rec.standard_hours) if rec.standard_hours else 0.0
            rec.coefficient = ratio
            rec.kpi_salary = rec.kpi_norm * ratio * (rec.score / 1000.0)

    @api.model
    def generate_for_run(self, payslip_run):
        """Sinh / cập nhật bản ghi đánh giá KPI cho toàn bộ phiếu lương của đợt.

        Idempotent: chạy lại giữ nguyên ĐIỂM đã nhập tay, chỉ cập nhật số liệu giờ
        và KPI định mức từ hợp đồng.
        """
        Eval = self.sudo()
        for payslip in payslip_run.slip_ids:
            vals = {
                'payslip_run_id': payslip_run.id,
                'payslip_id': payslip.id,
                'employee_id': payslip.employee_id.id,
                'contract_id': payslip.contract_id.id,
                'date_from': payslip.date_from,
                'date_to': payslip.date_to,
                'kpi_norm': payslip.contract_id.kpi_norm,
                'paid_hours': payslip._get_kpi_paid_hours(),
                'standard_hours': payslip._get_kpi_standard_hours(),
            }
            existing = Eval.search([
                ('payslip_run_id', '=', payslip_run.id),
                ('employee_id', '=', payslip.employee_id.id),
            ], limit=1)
            if existing:
                existing.write({k: v for k, v in vals.items() if k != 'score'})
            else:
                Eval.create(vals)


class PayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    kpi_evaluation_ids = fields.One2many('hr.kpi.evaluation', 'payslip_run_id', 'Đánh giá KPI')

    def action_refresh_kpi(self):
        """Cập nhật bảng KPI theo phiếu lương hiện tại của đợt.

        Dùng sau khi sửa & tính lại phiếu lương: làm mới giờ trả lương thực tế
        (paid_hours), giờ công tiêu chuẩn, KPI định mức từ phiếu — GIỮ NGUYÊN
        điểm đánh giá đã nhập tay (generate_for_run idempotent). kpi_salary tự
        tính lại theo số liệu mới.
        """
        for run in self:
            if run.state == 'close':
                raise UserError(_(
                    'Đợt lương "%s" đã xác nhận (đóng) - không được cập nhật đánh giá KPI.'
                ) % (run.name or ''))
            self.env['hr.kpi.evaluation'].generate_for_run(run)
        return True


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_kpi_standard_hours(self):
        """Giờ công tiêu chuẩn = input OTHER_WORK_HOUR_THEORY (đã tính khi compute_sheet)."""
        self.ensure_one()
        line = self.input_line_ids.filtered(
            lambda l: l.input_type_id.code == 'OTHER_WORK_HOUR_THEORY')[:1]
        return line.amount if line else 0.0

    def _get_kpi_score(self):
        """Điểm KPI của phiếu (từ bản ghi hr.kpi.evaluation); mặc định 1000 nếu chưa có."""
        self.ensure_one()
        Eval = self.env['hr.kpi.evaluation'].sudo()
        ev = Eval.search([('payslip_id', '=', self.id)], limit=1)
        if not ev:
            ev = Eval.search([
                ('employee_id', '=', self.employee_id.id),
                ('date_from', '=', self.date_from),
                ('date_to', '=', self.date_to),
            ], limit=1)
        return ev.score if ev else 1000

    def _get_kpi_paid_hours(self):
        """Giờ trả lương thực tế cho KPI = min(giờ quy đổi − đi lại, giờ chuẩn).

        Đúng bằng công thức phiếu lương dùng để chia base/KPI (OTHER_WORK_HOUR_CONVERTED
        đã trừ giờ đi lại, cắt trần tổng theo giờ chuẩn) -> bảng KPI khớp dòng LKPI trên
        phiếu và khớp mẫu gốc (sheet 'Lương KPI': H = min(tổng giờ trả lương, giờ chuẩn)).
        Đọc thẳng input của phiếu + giờ đi lại, KHÔNG tính lại phiếu, KHÔNG thêm input.
        """
        self.ensure_one()
        I = {i.input_type_id.code: i.amount for i in self.input_line_ids}
        conv = I.get('OTHER_WORK_HOUR_CONVERTED', 0.0)
        std = I.get('OTHER_WORK_HOUR_THEORY', 0.0)
        travel = sum(a.hour for a in self.env['hr.work.entry.allowance'].sudo().search([
            ('entry_id.employee_id', '=', self.employee_id.id),
            ('entry_id.x_date', '>=', self.date_from),
            ('entry_id.x_date', '<=', self.date_to),
            ('entry_id.state', '=', 'validated'),
        ]))
        return min(max(0.0, conv - travel), std)

    def _compute_kpi_paid_hours(self):
        """Giờ trả lương thực tế TRỪ OT và đi lại (phục vụ đánh giá KPI).

        = tổng giờ quy đổi mỗi ngày CẮT TRẦN theo lịch làm việc (T2-6=8h, T7=4/8h,
          CN=0h) -> loại bỏ phần OT premium cho mọi loại hợp đồng
        + nghỉ phép có tính lương (8h/ngày)
        + nghỉ lễ trong tuần (8h; T7 = 4h/8h theo lịch)
        + bù công thủ công đã duyệt
        KHÔNG cộng giờ hỗ trợ đi lại.
        """
        self.ensure_one()
        contract = self.contract_id
        if not self.date_from or not self.date_to or not contract:
            return 0.0

        _date_from = max(self.date_from, contract.date_start)
        _date_to = self.date_to if not contract.date_end else min(self.date_to, contract.date_end)
        is_saturday_half = bool(contract.resource_calendar_id) and \
            contract.resource_calendar_id.full_time_required_hours == 44.0
        is_saturday_full = bool(contract.resource_calendar_id) and \
            contract.resource_calendar_id.full_time_required_hours == 48.0
        is_hourly_wage = contract.structure_type_id.wage_type == 'hourly'

        def _scheduled_hours(wdate):
            wd = wdate.weekday()
            if wd == 6:            # Chủ nhật
                return 0
            if wd == 5:            # Thứ 7
                return 4 if is_saturday_half else 8
            return 8               # Thứ 2 - Thứ 6

        global_offs = self.env['hr.global.off'].sudo().search([
            ('active', '=', True),
            '|',
            '&', ('date_start', '>=', _date_from), ('date_start', '<=', _date_to),
            '&', ('date_end', '>=', _date_from), ('date_end', '<=', _date_to),
        ])

        def _is_global_off_date(d):
            return any(g.date_start <= d <= g.date_end for g in global_offs)

        # Giờ quy đổi theo ngày, cắt trần theo lịch (loại OT); bỏ ngày nghỉ lễ (cộng riêng)
        lines = self.env['hr.work.entry.line'].sudo().search([
            ('entry_id.employee_id', '=', self.employee_id.id),
            ('entry_id.x_date', '>=', self.date_from),
            ('entry_id.x_date', '<=', self.date_to),
            ('entry_id.state', '=', 'validated'),
        ])
        daily = {}
        for x in lines:
            wdate = x.entry_id.x_date
            if global_offs and _is_global_off_date(wdate):
                continue
            daily[wdate] = daily.get(wdate, 0.0) + x.hour_converted
        paid_hours = sum(min(h, _scheduled_hours(wd)) for wd, h in daily.items())

        # Nghỉ phép có tính lương = 8h/ngày
        paid_leaves = self.env['hr.leave.log'].sudo().search([
            ('leave_id.employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('leave_id.state', '=', 'validate'),
            ('leave_id.holiday_status_id.x_pay', '=', True),
        ])
        for item in paid_leaves:
            paid_hours += 8.0 * item.number_of_days

        # Nghỉ lễ trong tuần
        if not is_hourly_wage:
            for item in global_offs:
                ds = max(item.date_start, _date_from)
                de = min(item.date_end, _date_to)
                for i in range((de - ds).days + 1):
                    d = ds + relativedelta(days=i)
                    if d.weekday() != 5:
                        paid_hours += 8
                    elif is_saturday_half:
                        paid_hours += 4
                    elif is_saturday_full:
                        paid_hours += 8

        # Bù công thủ công đã duyệt
        manual = self.env['hr.payroll.other.hour'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'approved'),
        ])
        paid_hours += sum(x.hour for x in manual)

        return paid_hours
