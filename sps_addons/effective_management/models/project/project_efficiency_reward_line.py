# -*- coding: utf-8 -*-

import os
from datetime import date
from io import BytesIO

import openpyxl
from openpyxl.styles import Border, Side, Font, Alignment

from odoo import api, fields, models
from odoo.modules import get_module_path
from odoo.http import content_disposition, Response


class ProjectEfficiencyRewardLine(models.Model):
    _name = 'project.efficiency.reward.line'
    _description = 'Chi tiết thưởng hiệu quả dự án theo thành viên'
    _order = 'year desc, month desc, detail_id, role, reward desc'

    detail_id = fields.Many2one(
        'project.efficiency.detail', string='Dự án',
        ondelete='cascade', index=True)
    master_key = fields.Integer('Master Key', index=True)
    employee_id = fields.Many2one('hr.employee', string='Nhân viên')
    member_name = fields.Char('Thành viên')
    role = fields.Selection([
        ('leader', 'Phụ trách dự án'),
        ('technician', 'Thành viên dự án'),
        ('supporter', 'Hỗ trợ dự án'),
    ], string='Vai trò')
    total_work_hour = fields.Float('Tổng số giờ')
    work_hour = fields.Float('Số giờ tham gia')
    ratio = fields.Float('Phần trăm tham gia (%)')
    reward = fields.Float('Dự kiến thưởng')
    month = fields.Integer('Tháng')
    year = fields.Integer('Năm')

    # Các cột lấy từ project.efficiency.detail (cho màn hình "Bảng thống kê chi tiết thưởng")
    pp_name_report = fields.Char(related='detail_id.pp_name_report', string='Số phụ dự án')
    project_name = fields.Char(related='detail_id.project_name', string='Tên dự án')
    leader = fields.Char(related='detail_id.leader', string='Phụ trách')
    project_supporter = fields.Char(related='detail_id.project_supporter', string='Người hỗ trợ')
    project_type = fields.Char(related='detail_id.project_type', string='Phân loại')
    end_month = fields.Char(related='detail_id.end_month', string='Tháng kết thúc')
    budget = fields.Float(related='detail_id.budget', string='Dự toán nhân công')
    estimate_materials_and_other_costs = fields.Float(
        related='detail_id.estimate_materials_and_other_costs', string='Dự toán vật tư và chi phí khác')
    total_1 = fields.Float(related='detail_id.total_1', string='Tổng cộng dự toán')
    actual_labor = fields.Float(related='detail_id.actual_labor', string='Chi phí nhân công')
    actual_materials_and_other_costs = fields.Float(
        related='detail_id.actual_materials_and_other_costs', string='Chi phí vật tư và chi phí khác')
    total_depreciation_cost = fields.Float(related='detail_id.total_depreciation_cost', string='Chi phí CCDC')
    total_2 = fields.Float(related='detail_id.total_2', string='Tổng cộng chi phí')
    diff = fields.Float(related='detail_id.diff', string='Chênh lệch')
    rate = fields.Char(related='detail_id.rate', string='Mức độ hài lòng')

    # Hiệu quả dự án theo phần tham gia của thành viên: diff × ratio%.
    # Leader có ratio = 100 nên member_diff = full diff (giữ 100%).
    member_diff = fields.Float(
        'Hiệu quả tham gia', compute='_compute_member_diff', store=False)

    @api.depends('diff', 'ratio')
    def _compute_member_diff(self):
        for rec in self:
            rec.member_diff = (rec.diff or 0.0) * (rec.ratio or 0.0) / 100.0

    # ------------------------------------------------------------------
    # Excel export — "Sổ tính thưởng theo thành viên"
    # ------------------------------------------------------------------
    _ROLE_LABELS = {'leader': 'Phụ trách dự án', 'technician': 'Thành viên dự án',
                    'supporter': 'Hỗ trợ dự án'}
    # Tỷ lệ thưởng CỐ ĐỊNH cho người hỗ trợ dự án (không theo customer.rate).
    SUPPORTER_PCT = 5.0

    # Layout sheet Efficient: data bắt đầu row 4; cột B = thành viên (khoá SUMIF),
    # H = hiệu quả dự án (diff), K = dự kiến thưởng.
    _EFF_DATA_START = 4
    # Layout sheet E(PM): data bắt đầu row 4; B2 giữ rate cao nhất (%).
    _EPM_DATA_START = 4
    _EPM_RATE_CELL = 'B2'

    @staticmethod
    def _parse_end_month_to_date(value):
        if not value:
            return None
        try:
            month_str, year_str = (s.strip() for s in str(value).split('-', 1))
            return date(int(year_str), int(month_str), 1)
        except (ValueError, AttributeError):
            return None

    def _get_max_customer_rate(self):
        """Rate cao nhất (%) trong customer.rate; rỗng = 100 (coi như không chặn)."""
        rates = [r.rate for r in self.env['customer.rate'].search([]) if r.rate]
        return max(rates) if rates else 100.0

    def _fill_reward_summary(self, ws, members, role_label, title, year_label,
                             num_fmt, border, center, bold, rate_value=None,
                             combine_from=None):
        """Đổ 1 sheet tổng hợp thưởng (1 dòng / thành viên), dùng công thức trỏ
        về sheet Efficient.

        role_label = None  -> gộp MỌI vai trò (leader + technician + supporter)
                              theo tên thành viên (SUMIF) -> tổng hiệu quả/thưởng.
        role_label = '...'  -> chỉ cộng các dòng có vai trò đó (SUMIFS thêm điều
                               kiện cột C = vai trò) để tách leader / technician / supporter.
        rate_value = tỷ lệ (%) ghi vào ô rate B2; None -> rate cao nhất customer.rate.
        combine_from = danh sách tên sheet vai trò (vd ['E(PM)','E(Technician)',
                       'E(Supporter)']). Khi set: cột Thưởng đề xuất (F) = TỔNG cap
                       RIÊNG của các sheet đó (mỗi chức danh một mốc) thay vì cap
                       gộp 20%. Dùng cho sheet E để khớp 11.2.
        """
        if year_label:
            ws['A1'] = '%s - NĂM %s' % (title, year_label)
        else:
            ws['A1'] = title
        ws[self._EPM_RATE_CELL] = (self._get_max_customer_rate()
                                   if rate_value is None else rate_value)
        # Giá trị vẫn là số (vd 20) để công thức $B2/100 chạy đúng; hiển thị kèm '%'
        # qua format literal. Dùng General (KHÔNG dùng '0.##' vì locale VN hiện dấu
        # phẩy thừa "20,%"; KHÔNG dùng '0%' vì Excel sẽ nhân 100).
        ws[self._EPM_RATE_CELL].number_format = 'General"%"'
        ws[self._EPM_RATE_CELL].alignment = center
        ws[self._EPM_RATE_CELL].border = border

        rate_ref = '$%s' % self._EPM_RATE_CELL  # $B$2
        start = self._EPM_DATA_START

        def _sumif(col_letter, r):
            # Tổng theo thành viên ($B{r}); có lọc vai trò ở cột C nếu chỉ định.
            if role_label:
                return ('=SUMIFS(Efficient!$%s:$%s,Efficient!$B:$B,$B%d,'
                        'Efficient!$C:$C,"%s")' % (col_letter, col_letter, r, role_label))
            # Sheet E: gộp MỌI vai trò (gồm supporter).
            return '=SUMIF(Efficient!$B:$B,$B%d,Efficient!$%s:$%s)' % (
                r, col_letter, col_letter)

        for i, name in enumerate(members):
            r = start + i
            ws.cell(row=r, column=1, value=i + 1).alignment = center
            ws.cell(row=r, column=2, value=name)
            # Tổng hiệu quả tham gia = Σ cột H (Efficient)
            ws.cell(row=r, column=3, value=_sumif('H', r)).number_format = num_fmt
            # Tổng dự kiến thưởng = Σ cột K (Efficient)
            ws.cell(row=r, column=4, value=_sumif('K', r)).number_format = num_fmt
            # Lãi/Lỗ
            ws.cell(row=r, column=5,
                    value='=IF(C%d>0,"Lãi","Lỗ")' % r).alignment = center
            # Thưởng đề xuất:
            #  - combine_from (sheet E): TỔNG cap RIÊNG từng vai trò = Σ cột F của
            #    các sheet E(PM)/E(Technician)/E(Supporter) theo thành viên.
            #  - còn lại: MIN(tổng dự kiến thưởng, tổng hiệu quả × rate của sheet).
            if combine_from:
                f_formula = '=' + '+'.join(
                    "SUMIF('%s'!$B:$B,$B%d,'%s'!$F:$F)" % (s, r, s)
                    for s in combine_from)
            else:
                f_formula = "=IF(C%d>0,MIN(D%d,C%d*%s/100),0)" % (r, r, r, rate_ref)
            ws.cell(row=r, column=6, value=f_formula).number_format = num_fmt
            for col in range(1, 7):
                ws.cell(row=r, column=col).border = border

        if members:
            last = start + len(members) - 1
            tr = last + 1
            ws.cell(row=tr, column=2, value='TỔNG CỘNG').font = bold
            for col in (3, 4, 6):
                cl = openpyxl.utils.get_column_letter(col)
                cell = ws.cell(row=tr, column=col,
                               value="=SUM(%s%d:%s%d)" % (cl, start, cl, last))
                cell.number_format = num_fmt
                cell.font = bold
            for col in range(1, 7):
                ws.cell(row=tr, column=col).border = border

    def export_project_efficiency_reward_line(self, domain, context):
        """Xuất Excel sổ tính thưởng theo thành viên.

        - Sheet Efficient: 1 dòng / (thành viên × dự án).
        - Sheet E: tổng hợp MỌI vai trò (leader + technician + supporter).
        - Sheet E(PM): tổng hợp thưởng chỉ vai trò Phụ trách dự án (leader).
        - Sheet E(Technician): tổng hợp thưởng chỉ vai trò Thành viên dự án.
        - Sheet E(Supporter): tổng hợp thưởng hỗ trợ dự án (rate 5% cố định).
        Các sheet tổng hợp dùng SUMIF/SUMIFS + MIN trỏ về Efficient để xét lãi/lỗ
        và giới hạn thưởng theo rate tương ứng.
        """
        module_path = get_module_path('effective_management')
        excel_path = os.path.join(
            module_path, 'templates', 'template_so_tinh_thuong_thanh_vien.xlsx')
        wb = openpyxl.load_workbook(excel_path, data_only=False)
        # Template có sẵn 4 sheet tổng hợp: E, E(PM) leader, E(Technician), E(Supporter).
        pm_ws = wb['E(PM)']
        tech_ws = wb['E(Technician)']
        sup_ws = wb['E(Supporter)']

        lines = self.search(domain)

        # Năm dữ liệu đang xuất (lấy từ field year của các dòng) — ghi vào tiêu đề.
        years = sorted({rec.year for rec in lines if rec.year})
        year_label = ', '.join(str(y) for y in years) if years else ''

        thin = Side(style='thin')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        num_fmt = '#,##0;(#,##0)'
        center = Alignment(horizontal='center', vertical='center')
        bold = Font(bold=True)

        # ---- Sheet Efficient ----
        eff = wb['Efficient']
        if year_label:
            eff['A1'] = 'BẢNG CHI TIẾT THƯỞNG HIỆU QUẢ DỰ ÁN THEO THÀNH VIÊN - NĂM %s' % year_label
        row = self._EFF_DATA_START
        for stt, rec in enumerate(lines, start=1):
            eff.cell(row=row, column=1, value=stt).alignment = center
            eff.cell(row=row, column=2, value=rec.member_name or '')
            eff.cell(row=row, column=3,
                     value=self._ROLE_LABELS.get(rec.role, rec.role or ''))
            eff.cell(row=row, column=4, value=rec.pp_name_report or '')
            eff.cell(row=row, column=5, value=rec.project_name or '')
            eff.cell(row=row, column=6, value=rec.leader or '')
            end_cell = eff.cell(row=row, column=7)
            end_date = self._parse_end_month_to_date(rec.end_month)
            if end_date:
                end_cell.value = end_date
                end_cell.number_format = 'mm/yyyy'
            else:
                end_cell.value = rec.end_month or ''
            # Hiệu quả theo phần tham gia (leader full, technician theo ratio)
            eff.cell(row=row, column=8, value=rec.member_diff or 0).number_format = num_fmt
            eff.cell(row=row, column=9, value=rec.ratio or 0).number_format = '0.00'
            eff.cell(row=row, column=10, value=rec.work_hour or 0).number_format = '0.00'
            eff.cell(row=row, column=11, value=rec.reward or 0).number_format = num_fmt
            eff.cell(row=row, column=12, value=rec.rate or '')
            for col in range(1, 13):
                eff.cell(row=row, column=col).border = border
            row += 1

        # ---- Gom thành viên theo vai trò (giữ thứ tự xuất hiện) ----
        # members_all = MỌI vai trò (gồm supporter) -> sheet E tổng thưởng cuối/người.
        members_all, members_leader, members_tech, members_sup = [], [], [], []
        seen_all, seen_ld, seen_tech, seen_sup = set(), set(), set(), set()
        for rec in lines:
            name = rec.member_name or ''
            if not name:
                continue
            if name not in seen_all:
                seen_all.add(name)
                members_all.append(name)
            if rec.role == 'leader' and name not in seen_ld:
                seen_ld.add(name)
                members_leader.append(name)
            if rec.role == 'technician' and name not in seen_tech:
                seen_tech.add(name)
                members_tech.append(name)
            if rec.role == 'supporter' and name not in seen_sup:
                seen_sup.add(name)
                members_sup.append(name)

        # Sheet E (mọi vai trò), E(PM) (leader), E(Technician), E(Supporter).
        # Sheet E: Thưởng đề xuất = TỔNG cap RIÊNG 3 sheet vai trò (mỗi chức danh
        # một mốc) -> khớp chi_tieu_11_2.
        self._fill_reward_summary(
            wb['E'], members_all, None,
            'BẢNG TỔNG HỢP THƯỞNG THEO THÀNH VIÊN', year_label,
            num_fmt, border, center, bold,
            combine_from=['E(PM)', 'E(Technician)', 'E(Supporter)'])
        self._fill_reward_summary(
            pm_ws, members_leader, self._ROLE_LABELS['leader'],
            'BẢNG TỔNG HỢP THƯỞNG - PHỤ TRÁCH DỰ ÁN (LEADER)', year_label,
            num_fmt, border, center, bold)
        self._fill_reward_summary(
            tech_ws, members_tech, self._ROLE_LABELS['technician'],
            'BẢNG TỔNG HỢP THƯỞNG - THÀNH VIÊN (TECHNICIAN)', year_label,
            num_fmt, border, center, bold)
        # Supporter: rate 5% cố định.
        self._fill_reward_summary(
            sup_ws, members_sup, self._ROLE_LABELS['supporter'],
            'BẢNG TỔNG HỢP THƯỞNG - HỖ TRỢ DỰ ÁN (SUPPORTER)', year_label,
            num_fmt, border, center, bold, rate_value=self.SUPPORTER_PCT)

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = 'Bảng chi tiết thưởng.xlsx'
        return Response(
            output.getvalue(),
            headers=[
                ('Content-Type',
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ],
        )
