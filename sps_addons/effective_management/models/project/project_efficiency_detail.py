# -*- coding: utf-8 -*-

from datetime import timedelta, date, datetime
import base64

import os
from io import BytesIO
import openpyxl
from openpyxl.styles import NamedStyle, Font, Border, Side
from openpyxl.writer.excel import save_virtual_workbook
from odoo import api, fields, models

from datetime import timedelta, date, datetime
import base64

import os
from docutils.nodes import target
from io import BytesIO
import openpyxl
from openpyxl.styles import NamedStyle, Font, Border, Side
from openpyxl.writer.excel import save_virtual_workbook
from odoo import api, fields, models
import os
from io import BytesIO
import openpyxl
from openpyxl.styles import NamedStyle, Font, Border, Side, PatternFill, Alignment
from openpyxl.writer.excel import save_virtual_workbook
from openpyxl.worksheet import filters
from odoo.modules import get_module_path
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception, Response


class NonLaborCost(models.Model):
    _name = 'project.efficiency.detail'
    _description = 'Bảng thống kê các dự án đã hoàn thành và xem xét hiệu quả'

    master_key = fields.Integer('Master Key', index=True)
    pp_name_report = fields.Char('Số phụ dự án')
    project_name = fields.Char('Tên dự án')
    leader = fields.Char('Phụ trách')
    project_type = fields.Char('Phân loại')
    end_month = fields.Char('Tháng kết thúc')
    resource_types = fields.Char('Loại nguồn lực')
    budget = fields.Float('Dự toán nhân công')
    estimate_materials_and_other_costs = fields.Float('Dự toán vật tư và chi phí khác')
    total_1 = fields.Float(compute='_compute_total_1',string='Tổng cộng dự toán')
    total_2 = fields.Float(compute='_compute_total_2', string='Tổng cộng chi phí')
    real = fields.Float('Chi phí')
    diff = fields.Float('Chênh lệch',compute='_compute_diff')
    rate = fields.Char('Mức độ hài lòng')
    iv_fee = fields.Float('Chi phí IV')
    reward = fields.Float('Dự kiến thưởng',compute='_compute_reward')
    project_supporter = fields.Char(string='Người hỗ trợ')
    actual_labor = fields.Float('Chi phí nhân công')
    actual_materials_and_other_costs = fields.Float('Chi phí vật tư và chi phí khác')
    total_depreciation_cost = fields.Float('Chi phí CCDC')
    invoice_processing_profit = fields.Float('Doanh thu IV')
    no_invoice_extra_cost = fields.Float('Phí mua hàng không HĐ')
    budget_cost = fields.Float('Hiệu quả dự án')
    reward_line_ids = fields.One2many(
        'project.efficiency.reward.line', 'detail_id', string='Chi tiết thưởng')

    def action_view_reward_lines(self):
        """Mở bảng phụ chi tiết thưởng (leader + technician) của dự án."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết thưởng - %s' % (self.project_name or self.pp_name_report or ''),
            'res_model': 'project.efficiency.reward.line',
            'view_mode': 'tree',
            'view_id': self.env.ref(
                'effective_management.project_efficiency_reward_line_tree').id,
            'domain': [('detail_id', '=', self.id)],
            'target': 'new',
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    def _compute_total_1(self):
        for rec in self:
            rec.total_1 = rec.estimate_materials_and_other_costs + rec.budget

    def _compute_total_2(self):
        # Tổng cộng chi phí thực tế = Nhân công + Vật tư + Chi phí CCDC (khấu hao + hỏng/mất).
        for rec in self:
            rec.total_2 = (rec.actual_labor + rec.actual_materials_and_other_costs
                           + rec.total_depreciation_cost)

    def _compute_diff(self):
        # Chi phí CCDC (khấu hao + hỏng/mất) đã nằm trong total_2 nên không trừ lại ở đây.
        # Điều chỉnh TNDN: + lợi nhuận IV - phí mua hàng không hóa đơn.
        for rec in self:
            rec.diff = (rec.total_1 - rec.total_2 - rec.iv_fee
                        + rec.invoice_processing_profit - rec.no_invoice_extra_cost)

    # Tỷ lệ thưởng mặc định khi dự án CHƯA có đánh giá khách hàng (rate rỗng).
    UNRATED_REWARD_PCT = 5.0

    def _compute_reward(self):
        # E/S/A/D lấy đúng customer.rate (SPS chỉnh được); rỗng = mặc định 5%.
        rate_map = {r.code: r.rate
                    for r in self.env['customer.rate'].search([]) if r.code}
        for rec in self:
            rec.reward = 0
            if rec.diff > 0:
                pct = self.UNRATED_REWARD_PCT if not rec.rate else rate_map.get(rec.rate, 0.0)
                rec.reward = pct / 100.0 * rec.diff

    # Default layout of the E(PM) template sheet.
    _EPM_LEADER_START = 21
    _EPM_LEADER_TPL_COUNT = 30
    _EPM_SUPPORTER_TPL_COUNT = 5
    _EPM_MONTH_COLS = 'DEFGHIJKLMNO'  # 12 month columns (D..O)

    def _fill_epm_sheet(self, epm_ws, records):
        """Resize leader/supporter sections in E(PM) to match data and refresh formulas."""
        ld_start = self._EPM_LEADER_START
        ld_tpl = self._EPM_LEADER_TPL_COUNT
        sup_tpl = self._EPM_SUPPORTER_TPL_COUNT

        quit_employees = {
            epm_ws.cell(row=r, column=2).value
            for r in range(6, ld_start)
            if epm_ws.cell(row=r, column=2).value
        }

        leaders = []
        seen = set(quit_employees)
        for rec in records:
            if rec.leader and rec.leader not in seen:
                seen.add(rec.leader)
                leaders.append(rec.leader)

        supporters = []
        seen = set()
        for rec in records:
            if rec.project_supporter and rec.project_supporter not in seen:
                seen.add(rec.project_supporter)
                supporters.append(rec.project_supporter)

        L = len(leaders)
        M = len(supporters)

        # ---- Resize leader section ----
        if L > ld_tpl:
            extra = L - ld_tpl
            epm_ws.insert_rows(ld_start + ld_tpl, amount=extra)
            for i in range(extra):
                self._fill_leader_row(epm_ws, ld_start + ld_tpl + i)
        elif L < ld_tpl:
            epm_ws.delete_rows(ld_start + max(L, 1), ld_tpl - max(L, 1))
            # Keep at least 1 row to preserve the section if L == 0; clear it instead.
            if L == 0:
                for col in range(1, 23):
                    epm_ws.cell(row=ld_start, column=col).value = None

        leader_last = ld_start + max(L, 1) - 1
        total_row = ld_start + max(L, 1)
        ms_row = total_row + 1
        fm_row = total_row + 2
        sup_start = total_row + 4  # skip TOTAL, MS, FM, supporter header

        # Fill leader names + sequence numbers
        for i, name in enumerate(leaders):
            r = ld_start + i
            epm_ws.cell(row=r, column=1, value=i + 1)
            epm_ws.cell(row=r, column=2, value=name)

        # ---- Resize supporter section ----
        if M > sup_tpl:
            extra = M - sup_tpl
            epm_ws.insert_rows(sup_start + sup_tpl, amount=extra)
            for i in range(extra):
                self._fill_supporter_row(epm_ws, sup_start + sup_tpl + i)
        elif M < sup_tpl:
            keep = max(M, 1)
            epm_ws.delete_rows(sup_start + keep, sup_tpl - keep)
            if M == 0:
                for col in range(1, 23):
                    epm_ws.cell(row=sup_start, column=col).value = None

        sup_end = sup_start + max(M, 1) - 1

        for i, name in enumerate(supporters):
            r = sup_start + i
            epm_ws.cell(row=r, column=1, value=i + 1)
            epm_ws.cell(row=r, column=2, value=name)

        # ---- Update aggregate formulas with new ranges ----
        # TOTAL row
        for col in self._EPM_MONTH_COLS:
            epm_ws[f'{col}{total_row}'] = f'=SUM({col}6:{col}{leader_last})'
        for col in 'QRS':
            epm_ws[f'{col}{total_row}'] = f'=SUM({col}5:{col}{leader_last})'
        for col in 'UV':
            epm_ws[f'{col}{total_row}'] = f'=SUM({col}{ld_start}:{col}{leader_last})'

        # Tổng dự án MS / FM rows
        for div_row in (ms_row, fm_row):
            for col in self._EPM_MONTH_COLS:
                epm_ws[f'{col}{div_row}'] = (
                    f'=SUMIF($C$6:$C${leader_last},$C${div_row},'
                    f'{col}6:{col}{leader_last})'
                )
            epm_ws[f'Q{div_row}'] = f'=SUM(D{div_row}:O{div_row})'
            epm_ws[f'R{div_row}'] = (
                f'=SUMIF($C$5:$C${leader_last},$C{div_row},'
                f'R$5:R${leader_last})'
            )
            epm_ws[f'S{div_row}'] = f'=SUM(Q{div_row}:R{div_row})'
            epm_ws[f'V{div_row}'] = f'=IF(S{div_row}>0,S{div_row}*5%,0)'

        # Supporter rows: rewrite all formulas (rows shifted after leader-section
        # delete/insert, but openpyxl does not adjust formula text on shift, so the
        # SUMIFS still reference the original $B55..$B59 positions until we replace).
        for i in range(max(M, 1)):
            self._fill_supporter_row(epm_ws, sup_start + i)

        if M > 0:
            sum_q = f'Q{sup_start}:Q{sup_end}'
            for i in range(M):
                r = sup_start + i
                epm_ws[f'R{r}'] = f'=$R${ms_row}/SUM({sum_q})*Q{r}'

        # Re-merge A:B header cells at new TOTAL and supporter-header positions.
        # delete_rows leaves stale merged ranges referencing removed cells, so we
        # drop them from the ranges list directly (unmerge_cells would crash on
        # cells that no longer exist).
        for mr in [m for m in list(epm_ws.merged_cells.ranges)
                   if str(m) in ('A51:B51', 'A54:B54')]:
            epm_ws.merged_cells.ranges.remove(mr)
        epm_ws.merge_cells(start_row=total_row, start_column=1,
                           end_row=total_row, end_column=2)
        epm_ws.merge_cells(start_row=total_row + 3, start_column=1,
                           end_row=total_row + 3, end_column=2)

        # The template has rows 44-50 marked hidden as placeholder slots; after
        # delete_rows shifts the Note row up into one of those positions it stays
        # hidden, swallowing the warranty-cost note for supporters. Unhide every
        # row in the active content area.
        for r in range(total_row, sup_end + 3):
            if epm_ws.row_dimensions[r].hidden:
                epm_ws.row_dimensions[r].hidden = False

        # Give the "HỖ TRỢ DỰ ÁN / Project Supporter" header a bit more height —
        # the template's original 34pt does not survive the row shift.
        epm_ws.row_dimensions[total_row + 3].height = 40

        # Drop the stale P-column SUMIFS in supporter rows (template formula
        # references $B55 and the empty P$4 header — survives the row shift and
        # produces #VALUE! noise next to the supporter total).
        for i in range(max(M, 1)):
            epm_ws.cell(row=sup_start + i, column=16).value = None

    def _fill_leader_row(self, ws, row):
        # Efficient!$P = Chênh lệch (diff), Efficient!$R = Dự kiến thưởng
        # (đã dịch +1 cột do chèn 'Chi phí CCDC' tại cột M trong template).
        for col in self._EPM_MONTH_COLS:
            ws[f'{col}{row}'] = (
                f'=SUMIFS(Efficient!$P:$P,Efficient!$E:$E,$B{row},'
                f'Efficient!$G:$G,">"&EOMONTH({col}$4,-1),'
                f'Efficient!$G:$G,"<="&EOMONTH({col}$4,0))'
            )
        ws[f'Q{row}'] = f'=SUM(D{row}:O{row})'
        ws[f'R{row}'] = (
            f"=SUMIF(Efficient!$E$2154:$E$2175,B{row},"
            f"Efficient!$P$2154:$P$2175)"
        )
        ws[f'S{row}'] = f'=Q{row}+R{row}'
        ws[f'T{row}'] = (
            f'=IF(Q{row}>0,SUMIFS(Efficient!$R:$R,Efficient!$E:$E,$B{row},'
            f'Efficient!$G:$G,">"&EOMONTH(D$4,-1),'
            f'Efficient!$G:$G,"<="&EOMONTH(O$4,0)),0)'
        )
        ws[f'U{row}'] = f'=IF(S{row}>0,MIN(S{row}*20%,T{row}),0)'
        ws[f'V{row}'] = f'=IF(S{row}>0,MIN(S{row},T{row}),0)'

    def _fill_supporter_row(self, ws, row):
        for col in self._EPM_MONTH_COLS:
            ws[f'{col}{row}'] = (
                f'=SUMIFS(Efficient!$P:$P,Efficient!$D:$D,$B{row},'
                f'Efficient!$G:$G,">"&EOMONTH({col}$4,-1),'
                f'Efficient!$G:$G,"<="&EOMONTH({col}$4,0))'
            )
        ws[f'Q{row}'] = f'=SUM(D{row}:O{row})'
        ws[f'S{row}'] = f'=Q{row}+R{row}'
        ws[f'U{row}'] = f'=IF(S{row}>0,S{row}*5%,0)'

    @staticmethod
    def _parse_end_month_to_date(value):
        if not value:
            return None
        try:
            month_str, year_str = (s.strip() for s in str(value).split('-', 1))
            return date(int(year_str), int(month_str), 1)
        except (ValueError, AttributeError):
            return None

    def export_project_efficiency_detail(self, domain, context):
        module_path = get_module_path('effective_management')
        excel_path = os.path.join(module_path, 'templates', 'template_bao_cao_hieu_qua.xlsx')
        wb = openpyxl.load_workbook(excel_path, data_only=False)
        ws = wb['Efficient']
        project_efficiency_detail_ids = self.search(domain)

        start_row = 5
        current_row = start_row
        stt = 0

        for record in project_efficiency_detail_ids:
            stt+=1
            ws.cell(row=current_row, column=1, value=stt or '')
            ws.cell(row=current_row, column=2, value=record.pp_name_report or '')
            ws.cell(row=current_row, column=3, value=record.project_name or '')
            ws.cell(row=current_row, column=4, value=record.project_supporter or '')
            ws.cell(row=current_row, column=5, value=record.leader or '')
            ws.cell(row=current_row, column=6, value=record.project_type or '')
            end_month_cell = ws.cell(row=current_row, column=7)
            end_month_date = self._parse_end_month_to_date(record.end_month)
            if end_month_date:
                end_month_cell.value = end_month_date
                end_month_cell.number_format = 'mm/yyyy'
            else:
                end_month_cell.value = record.end_month or ''
            ws.cell(row=current_row, column=8, value=record.budget or '')
            ws.cell(row=current_row, column=9, value=record.estimate_materials_and_other_costs or '0')
            ws.cell(row=current_row, column=10, value=record.total_1 or '0')
            ws.cell(row=current_row, column=11, value=record.actual_labor or '0')
            ws.cell(row=current_row, column=12, value=record.actual_materials_and_other_costs or '0')
            ws.cell(row=current_row, column=13, value=record.total_depreciation_cost or '0')
            ws.cell(row=current_row, column=14, value=record.total_2 or '0')
            ws.cell(row=current_row, column=15, value=record.iv_fee or '0')
            ws.cell(row=current_row, column=16, value=record.invoice_processing_profit or '0')
            ws.cell(row=current_row, column=17, value=record.no_invoice_extra_cost or '0')
            ws.cell(row=current_row, column=18, value=record.diff or '0')
            ws.cell(row=current_row, column=19, value=record.rate or '')
            ws.cell(row=current_row, column=20, value=record.reward or '0')
            current_row += 1

        # Populate E(PM) sheet: leader + supporter sections sized to actual data.
        if 'E(PM)' in wb.sheetnames:
            self._fill_epm_sheet(wb['E(PM)'], project_efficiency_detail_ids)

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Tạo filename
        filename = f'Bao_cao_hieu_qua_du_an.xlsx'

        # Return response
        response = Response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename))
            ]
        )

        return response