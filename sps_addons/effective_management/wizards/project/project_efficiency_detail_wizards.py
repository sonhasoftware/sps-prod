# -*- coding: utf-8 -*-
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectEfficiencyDetailWizards(models.TransientModel):
    _name = "project.efficiency.detail.wizards"
    _description = "Nhập tham số non_labor"

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
    year = fields.Selection(
        selection='years_selection',
        string="Năm",
        default=str(dt.datetime.now().year), required=True)

    def remove_single_quote(self,input_string):
        # Sử dụng phương thức replace() để thay thế ký tự "'" bằng chuỗi rỗng ""
        result = input_string.replace("'", "")
        return result

    def years_selection(self):
        y = dt.datetime.now().year
        year_list = []
        while y != 1939:
            year_list.append((str(y), str(y)))
            y -= 1
        return year_list

    def action_report(self):
        current_year = self.year
        
        # Xóa dữ liệu cũ an toàn
        self.env['project.efficiency.detail'].search([('master_key', '=', self.master_key)]).unlink()

        # Ngày hoàn thành/dự án — NGUỒN CHUNG (project.project._project_completion_dates):
        # dự án archive+completed coi là hoàn thành kể cả không phát sinh chi phí;
        # ngày = nguồn -> x_date_end -> x_date_plan_end; None thì bỏ qua.
        current_year_int = int(current_year)
        comp = self.env['project.project']._project_completion_dates()
        completion_date_map = {pid: d for pid, d in comp.items()
                               if d and d.year == current_year_int}
        if not completion_date_map:
            raise UserError("Hiện không có dữ liệu cho báo cáo năm " + current_year)
        # Sắp theo ngày hoàn thành GIẢM DẦN (giữ thứ tự hiển thị như cũ).
        project_ids = sorted(completion_date_map,
                             key=lambda pid: completion_date_map[pid], reverse=True)
        projects = self.env['project.project'].browse(project_ids)
        
        # Prefetch tất cả related fields một lần
        projects.read([
            'name', 'label_tasks', 'x_project_type', 'x_date_end', 'e_fm', 'r_maintenace',
            'x_cost_estimate', 'x_material_estimate_total', 'wage_cost_total', 'actual_costs'
        ])
        projects.mapped('user_id.name')
        projects.mapped('project_supporter_id.name')
        
        # Rate ĐGHQ chính thức / dự án (xác định, tránh non-deterministic khi 1 dự
        # án có nhiều đánh giá) — dùng chung với báo cáo hiệu suất 11.1/11.2.
        satisfaction_map = self.env['customer.satisfaction'].official_rate_code_map(
            projects.ids)

        # Batch create records thay vì insert từng cái
        detail_vals = []
        for project in projects:
            # Lấy ngày hoàn thành thực tế từ mapping
            actual_completion_date = completion_date_map.get(project.id)
            
            end_month = ''
            if actual_completion_date:
                end_month = f'{actual_completion_date.month} - {actual_completion_date.year}'
            
            real_cost = round((project.actual_costs or 0) + (project.wage_cost_total or 0))
            diff_cost = round((project.x_cost_estimate or 0) + (project.x_material_estimate_total or 0) - real_cost) - project.iv_costs_total

            # Cờ bổ trợ chỉ áp dụng đúng loại dự án:
            #   FM (operation) + e_fm        -> E-FM
            #   Maintenance (maintainance) + r_maintenace -> R-Maintenace
            if project.x_project_type == 'operation' and project.e_fm:
                project_type = 'E-FM'
            elif project.x_project_type == 'maintainance' and project.r_maintenace:
                project_type = 'R-Maintenace'
            else:
                project_type = project.x_project_type or ''

            detail_vals.append({
                'master_key': self.master_key,
                'pp_name_report': project.name or '',
                'project_name': self.remove_single_quote(project.label_tasks or ''),
                'leader': project.user_id.name if project.user_id else '',
                'project_supporter': project.project_supporter_id.name if project.project_supporter_id else '',
                'project_type': project_type,
                'end_month': end_month,
                'budget': project.x_cost_estimate or 0,
                'estimate_materials_and_other_costs': project.x_material_estimate_total or 0,
                'actual_labor': project.wage_cost_total or 0,
                'actual_materials_and_other_costs': project.actual_costs or 0,
                'real': real_cost,
                'diff': diff_cost,
                'iv_fee': project.iv_costs_total,
                'rate': satisfaction_map.get(project.id, ''),
                # Chi phí CCDC = khấu hao + giá trị CCDC báo hỏng/mất quy về dự án.
                'total_depreciation_cost': (project.total_depreciation_cost or 0)
                                           + (project.x_damage_cost_total or 0),
                'invoice_processing_profit': project.invoice_processing_profit or 0,
                'no_invoice_extra_cost': project.no_invoice_extra_cost or 0,
                'budget_cost': project.budget_cost or 0,
            })
        if detail_vals:
            details = self.env['project.efficiency.detail'].create(detail_vals)
            # detail_vals được build theo đúng thứ tự duyệt `projects`, nên zip 1:1.
            self._create_reward_lines(details, projects, completion_date_map)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo hiệu quả dự án',
            'view_mode': 'tree',
            'res_model': "project.efficiency.detail",
            'context': {'year': current_year},
            'view_id': self.env.ref('effective_management.project_efficiency_detail_tree').id,
            'search_view_id': self.env.ref('effective_management.project_efficiency_detail_search').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',
        }

    # Tỷ lệ thưởng CỐ ĐỊNH cho người hỗ trợ dự án (không theo customer.rate).
    _SUPPORTER_PCT = 5.0

    def _get_rate_map(self):
        """code (E/S/A/D...) -> tỷ lệ % thưởng, lấy từ customer.rate (SPS chỉnh được)."""
        return {r.code: r.rate for r in self.env['customer.rate'].search([]) if r.code}

    def _create_reward_lines(self, details, projects, completion_date_map):
        """Sinh chi tiết thưởng cho từng dự án: leader hưởng full pool,
        technician chia pool theo tỷ trọng work_hour.
            pool = diff * rate% / 100   (chỉ khi diff > 0)
        diff = dự toán - chi phí thực tế - chi phí IV - chi phí CCDC (khấu hao + hỏng/mất).
        """
        rate_map = self._get_rate_map()
        line_vals = []
        for detail, project in zip(details, projects):
            # Loại dự án CHƯA PHÂN LOẠI (x_project_type trống) — đồng nhất với báo
            # cáo hiệu suất 11.1/11.2 (không sinh dòng thưởng cho dự án overhead/
            # nội bộ). Các dự án còn lại tính CẢ lãi lẫn lỗ.
            if not project.x_project_type:
                continue
            diff = detail.diff or 0
            # chưa đánh giá (rỗng) = mặc định 5%; còn lại theo customer.rate
            pct = 5.0 if not detail.rate else rate_map.get(detail.rate, 0.0)
            pool = diff * pct / 100.0 if diff > 0 else 0.0

            comp_date = completion_date_map.get(project.id)
            month = comp_date.month if comp_date else 0
            year = comp_date.year if comp_date else 0

            # Xác định leader (để loại trừ dòng technician trùng leader).
            # active_test=False: leader đã nghỉ (hr.employee archived) vẫn tìm được
            # -> loại đúng dòng technician, tránh thưởng 2 lần; order='id' cho xác định.
            leader_emp = (self.env['hr.employee'].with_context(active_test=False).search(
                [('user_id', '=', project.user_id.id)], order='id', limit=1)
                if project.user_id else self.env['hr.employee'])
            leader_emp_id = leader_emp.id if leader_emp else False
            leader_user_id = project.user_id.id if project.user_id else False

            # Gom giờ technician trước để có tổng số giờ dự án
            # (GỒM cả giờ leader để chia tỷ lệ cho đúng).
            tech_hours = {}
            for wc in project.wage_cost_ids:
                if not wc.employee_id:
                    continue
                rec = tech_hours.setdefault(wc.employee_id.id, [wc.employee_id, 0.0])
                rec[1] += wc.work_hour or 0.0
            total_hours = sum(h for _, h in tech_hours.values())

            # Leader = user_id của dự án (hưởng full pool)
            if project.user_id:
                line_vals.append({
                    'detail_id': detail.id,
                    'master_key': self.master_key,
                    'employee_id': leader_emp_id,
                    'member_name': project.user_id.name,
                    'role': 'leader',
                    'total_work_hour': total_hours,
                    'work_hour': 0.0,
                    'ratio': 100.0,
                    'reward': pool,
                    'month': month,
                    'year': year,
                })

            # Technician = wage_cost_ids, chia pool theo work_hour.
            # BỎ dòng technician của chính leader (đã hưởng full pool) để tránh
            # thưởng 2 lần; giờ của leader vẫn nằm trong total_hours.
            for emp, hours in tech_hours.values():
                if hours <= 0:
                    continue
                # So theo USER — robust khi leader có nhiều / đã archive hr.employee.
                if leader_user_id and emp.user_id.id == leader_user_id:
                    continue
                ratio = hours / total_hours if total_hours else 0.0
                line_vals.append({
                    'detail_id': detail.id,
                    'master_key': self.master_key,
                    'employee_id': emp.id,
                    'member_name': emp.name,
                    'role': 'technician',
                    'total_work_hour': total_hours,
                    'work_hour': hours,
                    'ratio': ratio * 100.0,
                    'reward': pool * ratio,
                    'month': month,
                    'year': year,
                })

            # Người hỗ trợ dự án (project_supporter_id): hưởng FULL diff (ratio=100)
            # với tỷ lệ thưởng CỐ ĐỊNH 5% — không theo customer.rate, KHÔNG chặn
            # per-dự-án (dự án lỗ vẫn trừ vào tổng năm; floor >0 làm ở sheet
            # E(Supporter)). Khớp công thức supporter trong template hiệu quả.
            supporter = project.project_supporter_id
            if supporter:
                line_vals.append({
                    'detail_id': detail.id,
                    'master_key': self.master_key,
                    'employee_id': supporter.id,
                    'member_name': supporter.name,
                    'role': 'supporter',
                    'total_work_hour': 0.0,
                    'work_hour': 0.0,
                    'ratio': 100.0,
                    # Dự án hiệu quả âm KHÔNG tính thưởng (=0, không âm); hiệu quả âm
                    # vẫn kéo tổng ở sheet E(Supporter) qua MIN(D, C×5%).
                    'reward': (diff * self._SUPPORTER_PCT / 100.0) if diff > 0 else 0.0,
                    'month': month,
                    'year': year,
                })

        if line_vals:
            self.env['project.efficiency.reward.line'].create(line_vals)
