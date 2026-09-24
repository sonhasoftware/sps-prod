# -*- coding: utf-8 -*-
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectSumValueLaborWizards(models.TransientModel):
    _name = "project.sum.value.labor.wizards"
    _description = "Nhập tham số non_labor"

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
    year = fields.Selection(
        selection='years_selection',
        string="Năm",
        default=str(dt.datetime.now().year), required=True)

    def years_selection(self):
        y = dt.datetime.now().year
        year_list = []
        while y != 1939:
            year_list.append((str(y), str(y)))
            y -= 1
        return year_list

    def action_report_new(self):
        def get_projects_with_actual_completion_date():
            projects_sql = """
                           WITH completion_dates AS (
                               -- Ngày từ satisfaction_ids
                               SELECT cs.project_id, MAX(cs.report_date) as completion_date
                               FROM customer_satisfaction cs
                               WHERE cs.report_date IS NOT NULL
                               GROUP BY cs.project_id
    
                               UNION ALL
    
                               -- Ngày từ hr.work.entry.line
                               SELECT wel.project_id, MAX(we.x_date) as completion_date
                               FROM hr_work_entry_line wel
                                        JOIN hr_work_entry we ON we.id = wel.entry_id
                               WHERE we.x_date IS NOT NULL
                               GROUP BY wel.project_id
    
                               UNION ALL
    
                               -- Ngày từ account.advance.line -> account.advance -> account.payment -> account.move
                               SELECT aal.project_id, MAX(am.date) as completion_date
                               FROM account_advance_line aal
                                        JOIN account_advance aa ON aa.id = aal.advance_id
                                        JOIN account_payment ap ON ap.id = aa.payment_id
                                        JOIN account_move am ON am.id = ap.move_id
                               WHERE am.state = 'posted'
                                 AND am.date IS NOT NULL
                               GROUP BY aal.project_id
    
                               UNION ALL
    
                               -- Ngày từ account.repay.line -> account.advance.repay -> account.payment -> account.move
                               SELECT arl.project_id, MAX(am.date) as completion_date
                               FROM account_repay_line arl
                                        JOIN account_advance_repay aar ON aar.id = arl.account_repay_id
                                        JOIN account_payment ap ON ap.id = aar.payment_id
                                        JOIN account_move am ON am.id = ap.move_id
                                        LEFT JOIN cost_type ct ON ct.id = arl.cost_type_id
                               WHERE am.state = 'posted'
                                 AND am.date IS NOT NULL
                                 AND ct.cost_type IS NOT NULL
                                 AND ct.cost_type != 'vat'
                               GROUP BY arl.project_id),
                                project_completion AS (SELECT project_id, \
                                                              MAX(completion_date) as actual_completion_date \
                                                       FROM completion_dates \
                                                       GROUP BY project_id)
                           SELECT pp.id as project_id, \
                                  pc.actual_completion_date
                           FROM project_project pp
                                    JOIN project_completion pc ON pc.project_id = pp.id
                           WHERE pp.active = False
                             AND pp.state = 'completed'
                             AND pc.actual_completion_date >= %s
                             AND pc.actual_completion_date <= %s
                           ORDER BY pc.actual_completion_date DESC \
                           """

            year_start = f'{self.year}-01-01'
            year_end = f'{self.year}-12-31'

            self._cr.execute(projects_sql, (
                year_start, year_end  # Lọc theo actual_completion_date cuối cùng
            ))
            return self._cr.dictfetchall()

        # Lấy danh sách project_ids và ngày hoàn thành thực tế
        project_completion_data = get_projects_with_actual_completion_date()

        if not project_completion_data:
            raise UserError("Hiện không có dữ liệu cho báo cáo năm " + self.year)

        # Lấy project objects và tạo mapping ngày hoàn thành
        project_ids = [p['project_id'] for p in project_completion_data]
        projects = self.env['project.project'].browse(project_ids)
        completion_date_map = {p['project_id']: p['actual_completion_date'] for p in project_completion_data}

        # Prefetch tất cả related fields một lần
        projects.read([
            'name', 'label_tasks', 'x_project_type', 'x_date_end',
            'x_cost_estimate', 'x_material_estimate_total', 'wage_cost_total', 'actual_costs'
        ])
        projects.mapped('user_id.name')
        projects.mapped('project_supporter_id.name')

    def action_report(self):
        def get_projects_with_actual_completion_date():
            # Ngày hoàn thành/dự án — NGUỒN CHUNG project.project._project_completion_dates:
            # dự án archive+completed coi là hoàn thành kể cả không phát sinh chi phí;
            # ngày = nguồn -> x_date_end -> x_date_plan_end; None thì bỏ qua.
            year_int = int(self.year)
            comp = self.env['project.project']._project_completion_dates()
            HrEmp = self.env['hr.employee'].with_context(active_test=False)
            out = []
            for pid, d in comp.items():
                if not d or d.year != year_int:
                    continue
                proj = self.env['project.project'].browse(pid)
                leader_emp = (HrEmp.search([('user_id', '=', proj.user_id.id)],
                                           order='id', limit=1)
                              if proj.user_id else HrEmp)
                out.append({
                    'project_id': pid,
                    'month_lastdate': d.month,
                    'year_lastdate': d.year,
                    'leader': (leader_emp.name if leader_emp else None) or 'Không có người phụ trách',
                    'supporter': proj.project_supporter_id.name or '',
                    'actual_completion_date': d,
                })
            return out

        current_year = self.year
        self._cr.execute(
            "delete from project_sum_value_labor where master_key = {key}".format(key=self.master_key))
        
        # Lấy dữ liệu dự án với ngày hoàn thành thực tế
        project_data = get_projects_with_actual_completion_date()
        
        if not project_data:
            raise UserError("Hiện không có dữ liệu cho báo cáo năm " + self.year)
        
        # Lấy các project objects để truy cập compute fields
        project_ids = [p['project_id'] for p in project_data]
        projects = self.env['project.project'].browse(project_ids)
        
        # Tạo mapping thông tin từ SQL
        project_info_map = {p['project_id']: p for p in project_data}
        
        # Tổng hợp dữ liệu theo leader và tháng
        summary_data = {}
        
        for project in projects:
            if project.id not in project_info_map:
                continue
                
            info = project_info_map[project.id]
            month = int(info['month_lastdate'])
            year = info['year_lastdate']
            leader = info['leader'] or 'Không có người phụ trách'
            supporter = info['supporter'] or ''
            
            # Lấy compute fields từ ORM
            total_budget = (project.x_cost_estimate or 0) + (project.x_material_estimate_total or 0)

            # Tạo key để group theo leader
            key = project.user_id.id

            if key not in summary_data:
                summary_data[key] = {
                    'leader': leader,
                    'supporter': supporter,
                    'year': year,
                    't1': 0, 't2': 0, 't3': 0, 't4': 0, 't5': 0, 't6': 0,
                    't7': 0, 't8': 0, 't9': 0, 't10': 0, 't11': 0, 't12': 0
                }

            # Cộng vào tháng tương ứng
            if 1 <= month <= 12:
                month_key = f't{month}'
                summary_data[key][month_key] += total_budget
        
        # Insert dữ liệu vào bảng project_sum_value_labor
        for key, data in summary_data.items():
            # Tạo classification từ leader và supporter
            classification = data['leader']
            # if data['supporter']:
            #     classification += f" - {data['supporter']}"
                
            insert_sql = """
                INSERT INTO project_sum_value_labor 
                (master_key, classification, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, year)
                VALUES (%(master_key)s, %(classification)s, 
                        %(t1)s, %(t2)s, %(t3)s, %(t4)s, %(t5)s, %(t6)s, 
                        %(t7)s, %(t8)s, %(t9)s, %(t10)s, %(t11)s, %(t12)s, %(year)s)
            """
            
            self._cr.execute(insert_sql, {
                'master_key': self.master_key,
                'classification': classification,
                't1': data['t1'],
                't2': data['t2'], 
                't3': data['t3'],
                't4': data['t4'],
                't5': data['t5'],
                't6': data['t6'],
                't7': data['t7'],
                't8': data['t8'],
                't9': data['t9'],
                't10': data['t10'],
                't11': data['t11'],
                't12': data['t12'],
                'year': self.year
            })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo tổng giá trị ngân sách',
            'view_mode': 'tree',
            'res_model': "project.sum.value.labor",
            'context': {'year': current_year},
            'view_id': self.env.ref('effective_management.project_sum_value_labor_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',
        }