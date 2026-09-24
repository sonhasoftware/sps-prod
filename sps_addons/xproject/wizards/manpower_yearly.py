import datetime
from datetime import timedelta, date
import base64

import os
from io import BytesIO
import openpyxl
from lxml import etree
from openpyxl.writer.excel import save_virtual_workbook
from openpyxl.utils import get_column_letter
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class ManpowerYearly(models.Model):
    _name = 'manpower.yearly'
    _description = 'báo cáo nhân lực theo năm'

    year = fields.Selection([(str(x), str(x)) for x in range(2000, 2050)], 'Năm',
                            default=str(date.today().year))
    x_block_department = fields.Many2one('hr.department.block',string='Khối phòng ban', domain=[('id', '!=', 1)])

    def print_reports(self):
        a ='Null'
        if self.x_block_department:
             a=self.x_block_department.id
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(
            dir_path + '%s..%stemplates%smanpower_yearly_template.xlsx' % (os.sep, os.sep, os.sep))
        ws = wb['Sheet1']
        sql = '''
                with date_table as
                        (
                            select
                                row_number() over() as stt,
                                date_trunc('day', dd):: date as date
                            from generate_series 
                                (
                                    (make_date(extract(year from current_date::date)::int,extract(month from current_date::date)::int,1) - interval'3 months')::date,
                                    (make_date(extract(year from current_date::date)::int,extract(month from current_date::date)::int,1) + interval'9 months' - interval'1 day')::date,
                                    '1 day'::interval
                                ) as dd
                        ),
                    available as
                        (
                            select
                                extract(year from dt."date") as year_1,
                                extract(month from dt."date") as month_1,
                                sum(case 
                                    when extract(isodow from dt."date") = 7 or (rc.full_time_required_hours = 48 and extract(isodow from dt."date") = 6) or hgo.id is not null then 0
                                    when rc.full_time_required_hours = 44 and extract(isodow from dt."date") = 6 then 4
                                    else 8
                                end) as hour_weekly,
                                'A' as type_hour
                                ,he.x_resource_type as resource_type
                            from date_table dt
                            left join hr_global_off hgo on dt."date" between hgo.date_start and hgo.date_end and hgo.active is true
                            left join hr_contract hc on dt."date" between hc.date_start and hc.date_end and hc.state in ('open','close')
                            left join resource_calendar rc on rc.id = hc.resource_calendar_id 
                            left join hr_employee he on he.id = hc.employee_id 
                            left join hr_department hd on hd.id = he.department_id 
                            where (case when {block_id} is not null then hd.x_block_id = {block_id} else 1 = 1 end) and hd.x_block_id != 1
                            group by year_1, month_1, resource_type
                        ),
                    project_est as 
                        (
                            select 
                                extract(year from dt."date") as year_1,
                                extract(month from dt."date") as month_1,
                                sum(pe.quantity/(case when pp.x_total_plan_day = 0 then 0 else coalesce(pp.x_total_plan_day,1) end)) as hour_weekly,
                                'B' as type_hour
                                    ,pt.x_resource_type as resource_type
                            from date_table dt
                            left join project_project pp on 
                                ((case when pp.x_date_start is not null then pp.x_date_start else pp.x_date_plan_start end)::date = dt."date" and coalesce(pp.x_total_plan_day,1)::int = 1)
                                or (dt."date" between (case when pp.x_date_start is not null then pp.x_date_start else pp.x_date_plan_start end)::date and (case when pp.x_date_start is not null then pp.x_date_start else pp.x_date_plan_start end)::date + pp.x_total_plan_day::int
                                    and pp.x_total_plan_day::int > 1)
                            left join project_estimate pe on pe.project_id = pp.id 
                            left join product_product pp2 on pp2.id = pe.product_id 
                            left join product_template pt on pt.id = pp2.product_tmpl_id 
                            where pp.state not in ('canceled') and pt.x_resource_type is not null 
                                and (
                                        case
                                            when {block_id} = 1 then 1=2
                                            when {block_id} = 2 then pp.x_project_type in ('maintainance','service')
                                            when {block_id} = 3 then pp.x_project_type in ('operation')
                                            else pp.x_project_type is not null
                                        end
                                    )
                            group by year_1, month_1, resource_type
                        ),
                    work_hour as 
                        (
                            select 
                                extract(year from dt."date") as year_1,
                                extract(month from dt."date") as month_1,
                                sum(case when hwet.code like 'WORK%' then hwel."hour" else 0 end) as hour_weekly,
                                'C' as type_hour
                                    ,he.x_resource_type as resource_type
                            from date_table dt
                            left join hr_work_entry hwe on hwe.x_date = dt."date"
                            left join hr_work_entry_type hwet on hwet.id = hwe.work_entry_type_id and hwet.code like 'WORK%'
                            left join hr_work_entry_line hwel on hwel.entry_id = hwe.id 
                            left join hr_employee he on he.id = hwe.employee_id 
                            left join hr_department hd on hd.id = he.department_id 
                            where (case when {block_id} is not null then hd.x_block_id = {block_id} else 1 = 1 end) and hd.x_block_id != 1
                            group by year_1, month_1, resource_type
                            
                            union all 
                            
                            select 
                                extract(year from dt."date") as year_1,
                                extract(month from dt."date") as month_1,
                                sum(case when hwet.code like 'WORK%' then hwea."hour" else 0 end) as hour_weekly,
                                'C' as type_hour
                                    ,he.x_resource_type as resource_type
                            from date_table dt
                            left join hr_work_entry hwe on hwe.x_date = dt."date"
                            left join hr_work_entry_type hwet on hwet.id = hwe.work_entry_type_id and hwet.code like 'WORK%'
                            left join hr_work_entry_allowance hwea on hwea.entry_id = hwe.id 
                            left join hr_employee he on he.id = hwe.employee_id 
                            left join hr_department hd on hd.id = he.department_id 
                            where (case when {block_id} is not null then hd.x_block_id = {block_id} else 1 = 1 end) and hd.x_block_id != 1
                            group by year_1, month_1, resource_type
                        ),
                    work_hour_support as
                        (
                            select
                                extract(year from dt."date") as year_1,
                                extract(month from dt."date") as month_1,
                                sum(hpi.amount) * 0.7 as hour_weekly,
                                'C' as type_hour
                                    ,he.x_resource_type as resource_type
                            from date_table dt
                            left join hr_payslip hp on hp.date_to = dt."date"
                            left join hr_payslip_input hpi on hpi.payslip_id = hp.id 
                            left join hr_payslip_input_type hpit on hpit.id = hpi.input_type_id 
                            left join hr_employee he on he.id = hp.employee_id 
                            left join hr_department hd on hd.id = he.department_id 
                            where hp.state = 'done' and hpit.code = 'OTHER_WORK_HOUR_SUPPORT' and (case when {block_id} is not null then hd.x_block_id = {block_id} else 1 = 1 end) and hd.x_block_id != 1
                            group by year_1, month_1, resource_type
                        )
                    select 
                        a.month_1,
                        coalesce(a.hour_weekly,0) as hour_available,
                        coalesce(pe.hour_weekly,0) as hour_est,
                        coalesce(wh.hour_weekly,0) + coalesce(whs.hour_weekly,0) as hour_plan
                        , a.resource_type
                    from available a
                    left join project_est pe on pe.year_1 = a.year_1 and pe.month_1 = a.month_1 and pe.resource_type = a.resource_type
                    left join work_hour wh on wh.year_1 = a.year_1 and wh.month_1 = a.month_1 and wh.resource_type = a.resource_type
                    left join work_hour_support whs on whs.year_1 = a.year_1 and whs.month_1 = a.month_1 and whs.resource_type = a.resource_type
                    order by a.year_1, a.month_1

             '''.format(block_id = a)
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()
        today = date.today()
        start_month = today.month - 3
        end_month = today.month + 8
        A = {}
        B = {}
        C = {}
        for r in recs:
            month_number = int(r['month_1'])
            if r['hour_available'] > 0:
                if month_number not in A:
                    A[month_number] = {}  # A[0] = {}
                if r['resource_type'] == 'seniorengsub':
                    A[month_number]['seniorengsub'] = r['hour_available']  # A[0] = {'seniorengsub': 1}
                elif r['resource_type'] == 'engsub':
                    A[month_number]['engsub'] = r['hour_available']  # A[0] = {'seniorengsub': 1, 'engsub': 2}
                elif r['resource_type'] == 'teamleader':
                    A[month_number]['teamleader'] = r['hour_available']
                elif r['resource_type'] == 'technician':
                    A[month_number]['technician'] = r['hour_available']
                elif r['resource_type'] == 'internship':
                    A[month_number]['internship'] = r['hour_available']
            if r['hour_est'] > 0:
                if month_number not in B:
                    B[month_number] = {}  # A[0] = {}
                if r['resource_type'] == 'seniorengsub':
                    B[month_number]['seniorengsub'] = r['hour_est']  # A[0] = {'seniorengsub': 1}
                elif r['resource_type'] == 'engsub':
                    B[month_number]['engsub'] = r['hour_est']  # A[0] = {'seniorengsub': 1, 'engsub': 2}
                elif r['resource_type'] == 'teamleader':
                    B[month_number]['teamleader'] = r['hour_est']
                elif r['resource_type'] == 'technician':
                    B[month_number]['technician'] = r['hour_est']
                elif r['resource_type'] == 'internship':
                    B[month_number]['internship'] = r['hour_est']
            if r['hour_plan'] > 0:
                if month_number not in C:
                    C[month_number] = {}  # A[0] = {}
                if r['resource_type'] == 'seniorengsub':
                    C[month_number]['seniorengsub'] = r['hour_plan']  # A[0] = {'seniorengsub': 1}
                elif r['resource_type'] == 'engsub':
                    C[month_number]['engsub'] = r['hour_plan']  # A[0] = {'seniorengsub': 1, 'engsub': 2}
                elif r['resource_type'] == 'teamleader':
                    C[month_number]['teamleader'] = r['hour_plan']
                elif r['resource_type'] == 'technician':
                    C[month_number]['technician'] = r['hour_plan']
                elif r['resource_type'] == 'internship':
                    C[month_number]['internship'] = r['hour_plan']
        column = 2
        ws.cell(3, 13).value = today
        for month in range(start_month, end_month + 1):
            current_month = month
            if today.month < 4:
                if month < 1:
                    current_month = month + 12
            elif today.month > 3:
                if month > 12:
                    current_month = month - 12

            ws.cell(4, column).value = current_month
            # phân mục A
            ws.cell(5, column).value = '=SUM(%s6:%s10)' % (get_column_letter(column), get_column_letter(column))
            ws.cell(6, column).value = A.get(current_month) and A[current_month].get('seniorengsub') or 0
            ws.cell(7, column).value = A.get(current_month) and A[current_month].get('engsub') or 0
            ws.cell(8, column).value = A.get(current_month) and A[current_month].get('teamleader') or 0
            ws.cell(9, column).value = A.get(current_month) and A[current_month].get('technician') or 0
            ws.cell(10, column).value = A.get(current_month) and A[current_month].get('internship') or 0
            # phân mục B
            ws.cell(11, column).value = '=SUM(%s12:%s16)' % (get_column_letter(column), get_column_letter(column))
            ws.cell(12, column).value = B.get(current_month) and B[current_month].get('seniorengsub') or 0
            ws.cell(13, column).value = B.get(current_month) and B[current_month].get('engsub') or 0
            ws.cell(14, column).value = B.get(current_month) and B[current_month].get('teamleader') or 0
            ws.cell(15, column).value = B.get(current_month) and B[current_month].get('technician') or 0
            ws.cell(16, column).value = B.get(current_month) and B[current_month].get('internship') or 0
            # phân mục C
            ws.cell(17, column).value = '=SUM(%s18:%s22)' % (get_column_letter(column), get_column_letter(column))
            ws.cell(18, column).value = C.get(current_month) and C[current_month].get('seniorengsub') or 0
            ws.cell(19, column).value = C.get(current_month) and C[current_month].get('engsub') or 0
            ws.cell(20, column).value = C.get(current_month) and C[current_month].get('teamleader') or 0
            ws.cell(21, column).value = C.get(current_month) and C[current_month].get('technician') or 0
            ws.cell(22, column).value = C.get(current_month) and C[current_month].get('internship') or 0
            #
            ws.cell(23, column).value = '=(%s11-%s5)/(%s5)' % (
                get_column_letter(column), get_column_letter(column), get_column_letter(column))

            column += 1

        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo nhân lực năm .xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/' + str(attachment_id.id) + '?download=true',
            'target': 'new',
        }
