# -*- coding: utf-8 -*-
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EfficiencyCoefficient(models.TransientModel):
    _name = "project.efficiency.coefficient.wizards"
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

    def action_report(self):
        current_year = self.year
        sql_get_data = f"""
                select  employee_id ,target  from annual_labor_productivity_target where year = '{str(current_year)}'
                """
        self._cr.execute(sql_get_data)
        data_annual_labor_productivity_target = self._cr.dictfetchall()
        employee_target_dict = {}
        for item in data_annual_labor_productivity_target:
            employee_target_dict[item['employee_id']] = item['target']
        self._cr.execute(
            "delete from project_efficiency_coefficient where master_key = {key}".format(key=self.master_key))
        sql = f''' select  view_base.year_chamcong,
                            view_base.month_chamcong,
                            (case 	when view_base.x_resource_type = 'seniorengsub' then 'Kỹ sư/ Giám sát cao cấp'
                                    when view_base.x_resource_type = 'engsub' then 'Kỹ sư/ Giám sát'
                                    when view_base.x_resource_type = 'teamleader' then 'Trưởng nhóm'
                                    when view_base.x_resource_type = 'technician' then 'Kỹ thuật viên'
                                    when view_base.x_resource_type = 'internship' then 'Thực tập sinh'
                                    else 'others' end
                            ) as x_resource_type,
                            view_base.employee_id,
                            view_base.name_employee,
                        --    coalesce(view_trocapdilai.sogiotrocapdilai_project,0) as sogiotrocapdilai_project,
                        --    coalesce(view_trocapdilai.sogiotrocapdilai,0) as sogiotrocapdilai,
                        --    coalesce(view_base.hour_project,0) as sogiochamcong_project,
                        --    coalesce(view_base.hour,0) as sogiochamcong,
                        --    coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0) as sogiohotroluongbuducong,
                        --    (coalesce(view_base.hour_project,0) + coalesce(view_trocapdilai.sogiotrocapdilai_project,0)) as hour_project,
                        --  (coalesce(view_trocapdilai.sogiotrocapdilai,0) + coalesce(view_base.hour,0) + coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0)) as sogioquydoi,
                            round(((coalesce(view_base.hour_project,0) + coalesce(view_trocapdilai.sogiotrocapdilai_project,0))/(coalesce(view_base.hour,0) + coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0) + coalesce(view_trocapdilai.sogiotrocapdilai,0))*100)::numeric,2) as hieuqua
                    from
                        (--Cham cong
                        select  view_detail.year_chamcong,
                                view_detail.month_chamcong,
                                view_detail.x_resource_type,
                                view_detail.employee_id,
                                view_detail.name_employee,
                                sum(view_detail.hour) as hour,
                                sum(view_detail.hour_project) as hour_project
                        from
                            (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                    extract ('month' from hr_work_entry.x_date) as month_chamcong,
                                    hr_work_entry_line.entry_id,
                                    hr_work_entry_line.id as wrl_id,
                                    hr_work_entry_line.project_id,
                                    (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                    hr_work_entry.employee_id,
                                    hr_employee.name as name_employee,
                                    hr_employee.x_resource_type,
                                    hr_work_entry.x_date,
                                    hr_work_entry_line.hour, 
                                    (case when project_project.x_project_type in ('service', 'maintainance', 'operation') then hr_work_entry_line.hour else 0 end) as hour_project
                            from hr_work_entry_line
                            left join hr_work_entry on hr_work_entry_line.entry_id = hr_work_entry.id
                            left join project_project on hr_work_entry_line.project_id = project_project.id
                            left join hr_employee on hr_work_entry.employee_id = hr_employee.id and hr_employee.active = True
                            ) as view_detail
                        group by view_detail.year_chamcong, view_detail.month_chamcong, view_detail.x_resource_type, view_detail.employee_id, view_detail.name_employee
                        ) as view_base
                    left join 
                        (--So gio ho tro luong bu du cong
                        select  extract ('year' from hr_payslip.date_from):: character varying as year_payslip,
                                extract ('month' from hr_payslip.date_from) as month_payslip,
                                hr_payslip.id,
                                hr_payslip.employee_id,
                                hr_payslip_input.amount as sogiohotroluongbuducong
                        from hr_payslip
                        left join hr_payslip_input on hr_payslip.id = hr_payslip_input.payslip_id 
                        where hr_payslip_input.input_type_id = 13
                        ) as view_sogiohotroluongbuducong
                    on 	view_base.year_chamcong = view_sogiohotroluongbuducong.year_payslip 
                        and view_base.month_chamcong = view_sogiohotroluongbuducong.month_payslip 
                        and view_base.employee_id = view_sogiohotroluongbuducong.employee_id
                    left join 
                        (--So gio tro cap di lai
                        select	view_detail.year_chamcong,
                                view_detail.month_chamcong,
                                view_detail.employee_id,
                                view_detail.name_employee,
                                sum(view_detail.hour) as sogiotrocapdilai,
                                sum(view_detail.sogiotrocapdilai_project) as sogiotrocapdilai_project
                        from
                            (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                    extract ('month' from hr_work_entry.x_date) as month_chamcong,
                                    hr_work_entry.x_date,
                                    hr_work_entry_allowance.entry_id,
                                    hr_work_entry_allowance.id as allowance_id,
                                    hr_work_entry_allowance.project_id,
                                    project_project.name as project_name,
                                    (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                    hr_work_entry.employee_id,
                                    hr_employee.name as name_employee,
                                    hr_employee.x_resource_type,
                                    hr_work_entry_allowance.hour,
                                    (case when project_project.x_project_type in ('service', 'maintainance', 'operation') then hr_work_entry_allowance.hour else 0 end) as sogiotrocapdilai_project
                            from hr_work_entry_allowance
                            left join hr_work_entry on hr_work_entry_allowance.entry_id = hr_work_entry.id
                            left join project_project on hr_work_entry_allowance.project_id = project_project.id
                            left join hr_employee on hr_work_entry.employee_id = hr_employee.id and hr_employee.active = True
                            ) as view_detail
                        group by view_detail.year_chamcong, view_detail.month_chamcong, view_detail.employee_id, view_detail.name_employee
                        ) as view_trocapdilai
                    on 	view_base.year_chamcong = view_trocapdilai.year_chamcong 
                        and view_base.month_chamcong = view_trocapdilai.month_chamcong 
                        and view_base.employee_id = view_trocapdilai.employee_id
                    where  view_base.year_chamcong ='{current_year}' 
                    order by view_base.year_chamcong, view_base.month_chamcong, view_base.x_resource_type, view_base.name_employee
'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        # tạo ra data cuối
        if len(recs_last)<0:
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        # gom nhóm theo form báo cáo
        key_account = []
        for rec in recs_last:
            if rec['name_employee'] and rec['name_employee'] not in key_account:
                key_account.append(rec['name_employee'])
        last_data={}
        for account in key_account:
            for line in recs_last:
                if line['name_employee'] == account:
                    key_month = 't' + str(int(line['month_chamcong']))
                    if account not in last_data:
                        last_data[account] = {'type': line.get('x_resource_type') or 'Chưa biết',
                                            'employee_id': line.get('employee_id')}
                        last_data[account][key_month] = round(line.get('hieuqua') or 0, 2)
                    else:
                        last_data[account][key_month] = round(line.get('hieuqua') or 0, 2)
        #LẤY CỘT TỔNG CỘNG
        sql_total = f'''select  view_base.year_chamcong,
                        (case 	when view_base.x_resource_type = 'seniorengsub' then 'Kỹ sư/ Giám sát cao cấp'
                                when view_base.x_resource_type = 'engsub' then 'Kỹ sư/ Giám sát'
                                when view_base.x_resource_type = 'teamleader' then 'Trưởng nhóm'
                                when view_base.x_resource_type = 'technician' then 'Kỹ thuật viên'
                                when view_base.x_resource_type = 'internship' then 'Thực tập sinh'
                                else 'others' end
                        ) as x_resource_type,
                        view_base.name_employee,
                        coalesce(view_trocapdilai.sogiotrocapdilai_project,0) as sogiotrocapdilai_project,
                        coalesce(view_trocapdilai.sogiotrocapdilai,0) as sogiotrocapdilai,
                        coalesce(view_base.hour_project,0) as sogiochamcong_project,
                        coalesce(view_base.hour,0) as sogiochamcong,
                        coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0) as sogiohotroluongbuducong,
                        (coalesce(view_base.hour_project,0) + coalesce(view_trocapdilai.sogiotrocapdilai_project,0)) as hour_project,
                        (coalesce(view_trocapdilai.sogiotrocapdilai,0) + coalesce(view_base.hour,0) + coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0)) as sogioquydoi,
                        round(((coalesce(view_base.hour_project,0) + coalesce(view_trocapdilai.sogiotrocapdilai_project,0))/(coalesce(view_base.hour,0) + coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0) + coalesce(view_trocapdilai.sogiotrocapdilai,0))*100)::numeric,2) as hieuqua
                from
                    (--Cham cong
                    select  view_detail.year_chamcong,
                            view_detail.x_resource_type,
                            view_detail.employee_id,
                            view_detail.name_employee,
                            sum(view_detail.hour) as hour,
                            sum(view_detail.hour_project) as hour_project
                    from
                        (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                hr_work_entry_line.entry_id,
                                hr_work_entry_line.id as wrl_id,
                                hr_work_entry_line.project_id,
                                (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                hr_work_entry.employee_id,
                                hr_employee.name as name_employee,
                                hr_employee.x_resource_type,
                                hr_work_entry.x_date,
                                hr_work_entry_line.hour, 
                                (case when project_project.x_project_type in ('service', 'maintainance', 'operation') then hr_work_entry_line.hour else 0 end) as hour_project
                        from hr_work_entry_line
                        left join hr_work_entry on hr_work_entry_line.entry_id = hr_work_entry.id
                        left join project_project on hr_work_entry_line.project_id = project_project.id
                        left join hr_employee on hr_work_entry.employee_id = hr_employee.id and hr_employee.active = True
                        ) as view_detail
                    group by view_detail.year_chamcong, view_detail.x_resource_type, view_detail.employee_id, view_detail.name_employee
                    ) as view_base
                left join 
                    (--So gio ho tro luong bu du cong
                    select  extract ('year' from hr_payslip.date_from):: character varying as year_payslip,
                            hr_payslip.employee_id,
                            sum(hr_payslip_input.amount) as sogiohotroluongbuducong
                    from hr_payslip
                    left join hr_payslip_input on hr_payslip.id = hr_payslip_input.payslip_id 
                    where hr_payslip_input.input_type_id = 13
                    group by extract ('year' from hr_payslip.date_from):: character varying, hr_payslip.employee_id
                    ) as view_sogiohotroluongbuducong
                on view_base.year_chamcong = view_sogiohotroluongbuducong.year_payslip and view_base.employee_id = view_sogiohotroluongbuducong.employee_id
                left join 
                    (--So gio tro cap di lai
                    select	view_detail.year_chamcong,
                            view_detail.employee_id,
                            view_detail.name_employee,
                            sum(view_detail.hour) as sogiotrocapdilai,
                            sum(view_detail.sogiotrocapdilai_project) as sogiotrocapdilai_project
                    from
                        (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                hr_work_entry.x_date,
                                hr_work_entry_allowance.entry_id,
                                hr_work_entry_allowance.id as allowance_id,
                                hr_work_entry_allowance.project_id,
                                project_project.name as project_name,
                                (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                hr_work_entry.employee_id,
                                hr_employee.name as name_employee,
                                hr_employee.x_resource_type,
                                hr_work_entry_allowance.hour,
                                (case when project_project.x_project_type in ('service', 'maintainance', 'operation') then hr_work_entry_allowance.hour else 0 end) as sogiotrocapdilai_project
                        from hr_work_entry_allowance
                        left join hr_work_entry on hr_work_entry_allowance.entry_id = hr_work_entry.id
                        left join project_project on hr_work_entry_allowance.project_id = project_project.id
                        left join hr_employee on hr_work_entry.employee_id = hr_employee.id and hr_employee.active = True
                        ) as view_detail
                    group by view_detail.year_chamcong, view_detail.employee_id, view_detail.name_employee
                    ) as view_trocapdilai
                on view_base.year_chamcong = view_trocapdilai.year_chamcong and view_base.employee_id = view_trocapdilai.employee_id
                 where  view_base.year_chamcong ='{current_year}' 
                order by view_base.year_chamcong,view_base.x_resource_type, view_base.name_employee'''
        self._cr.execute(sql_total)
        recs_total = self._cr.dictfetchall()
        for account in key_account:
            for line in recs_total:
                if line['name_employee'] == account:
                        last_data[account]['total'] = round(line.get('hieuqua') or 0, 2)
                else:continue
        #đổ dữ liệu
        for key,value in last_data.items():
            target = employee_target_dict.get(int(f"{value.get('employee_id')}")) or 0
            insert = '''INSERT INTO project_efficiency_coefficient (master_key, classification,resource_type ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total,employee_id,target,year)
                                          VALUES ({key},'{classification}','{resource_type}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total},{employee_id},{target},{year})
                                      '''.format(key=self.master_key,
                                                 classification=key,
                                                 resource_type=value.get('type'),
                                                 t1=value.get('t1') or 0,
                                                 t2=value.get('t2') or 0,
                                                 t3=value.get('t3') or 0,
                                                 t4=value.get('t4') or 0,
                                                 t5=value.get('t5') or 0,
                                                 t6=value.get('t6') or 0,
                                                 t7=value.get('t7') or 0,
                                                 t8=value.get('t8') or 0,
                                                 t9=value.get('t9') or 0,
                                                 t10=value.get('t10') or 0,
                                                 t11=value.get('t11') or 0,
                                                 t12=value.get('t12') or 0,
                                                 total = value.get('total') or 0,
                                                 employee_id = value.get('employee_id') or 'NULL',
                                                 target = target,
                                                 year=self.year
                                                 )
            self._cr.execute(insert)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo hiệu suất lao động',
            'view_mode': 'tree',
            'res_model': "project.efficiency.coefficient",
            'context' : {'year': current_year,
                         'search_default_resource_type':0},
            'view_id': self.env.ref('effective_management.project_efficiency_coefficient_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }