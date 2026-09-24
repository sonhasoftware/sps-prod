import datetime
from datetime import timedelta, date
import base64

import os
from io import BytesIO
import openpyxl
from openpyxl.utils import get_column_letter
from lxml import etree
from openpyxl.writer.excel import save_virtual_workbook
from openpyxl.styles import NamedStyle, Font, Border, Side,Color,PatternFill
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class ManpowerWeekly(models.Model):
    _name = 'manpower.weekly'
    _description = 'báo cáo nhân lực theo tuần'

    year = fields.Selection([(str(x), str(x)) for x in range(2000, 2050)], 'Năm',
                            default=str(date.today().year), required=1)
    x_block_department = fields.Many2one('hr.department.block', string='Khối phòng ban', domain=[('id', '!=', 1)])
    # style
    no_border = Border(bottom=Side(style='none'), top=Side(style='none'), right=Side(style='none'))
    no_color = Color(indexed=1)

    def print_reports(self):
        a= 'Null'
        if self.x_block_department:
            a=self.x_block_department.id
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(
            dir_path + '%s..%stemplates%smanpower_weekly_template.xlsx' % (os.sep, os.sep, os.sep))
        ws = wb['Sheet1']

        sql = '''
             with date_table as
                    (
                        SELECT
                            cast(generate_series as date) as "date",
                            extract (isodow from generate_series) as day_of_week_iso,
                            floor((cast(generate_series as date) - cast(concat(cast(2022 as varchar),'-01-01') as date) + extract(isodow from cast(concat(cast(2022 as varchar),'-01-01') as date))::int + 6::int) / 7) week_of_year
                        FROM
                            GENERATE_SERIES
                                (
                                    case 
                                        when extract(isodow from cast(concat(cast(2022 as varchar),'-01-01') as date)) = 1 
                                            then cast(concat(cast(2022 as varchar),'-01-01') as date) 
                                        else cast(concat(cast(2022 as varchar),'-01-01') as date) - extract(isodow from cast(concat(cast(2022 as varchar),'-01-01') as date))::int + 1::int
                                    end,
                                    case 
                                        when extract(isodow from cast(concat(cast(2022 as varchar),'-12-31') as date)) = 7 
                                            then cast(concat(cast(2022 as varchar),'-12-31') as date)
                                        else cast(concat(cast(2022 as varchar),'-12-31') as date) - extract(isodow from cast(concat(cast(2022 as varchar),'-12-31') as date))::int + 7::int 
                                    end,
                                    interval '1 day'
                                )
                    ),
                available as
                    (
                        select
                            dt.week_of_year as week_num,
                            sum(case 
                                when rc.full_time_required_hours = 48 and dt.day_of_week_iso not in (7) and hgo.id is null then 8
                                when rc.full_time_required_hours = 44 and dt.day_of_week_iso not in (6,7) and hgo.id is null then 8
                                when rc.full_time_required_hours = 44 and dt.day_of_week_iso = 6 and hgo.id is null then 4
                                else 0
                            end) as hour_weekly,
                            'A' as type_hour
                            ,he.x_resource_type as resource_type
                        from date_table dt
                        left join hr_contract hc on dt."date" between hc.date_start and hc.date_end and hc.state in ('open','close')
                        left join hr_global_off hgo on dt."date" between hgo.date_start and hgo.date_end and hgo.active is true
                        left join resource_calendar rc on rc.id = hc.resource_calendar_id 
                        left join hr_employee he on he.id = hc.employee_id 
                        left join hr_department hd on hd.id = he.department_id 
                        where (case when {block_id} is not null then hd.x_block_id = {block_id} else 1 = 1 end) and hd.x_block_id != 1
                        group by week_num, resource_type
                    ),
                project_est as 
                    (
                        select 
                            dt.week_of_year as week_num,
                            sum(pe.quantity/(case when pp.x_total_plan_day = 0 then 0 else coalesce(pp.x_total_plan_day,1) end)) as hour_weekly,
                            'B' as type_hour,
                            pt.x_resource_type as resource_type
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
                        group by week_num, resource_type
                    ),
                work_hour as 
                    (
                        select 
                            dt.week_of_year as week_num,
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
                        group by week_num, resource_type
                        
                        union all 
                        
                        select 
                            dt.week_of_year as week_num,
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
                        group by week_num, resource_type
                    ),
                work_hour_support as
                    (
                        select
                            dt.week_of_year as week_num,
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
                        group by week_num, resource_type
                    )
                select 
                    a.week_num,
                    extract(month from dt."date") as month_1,
                    dt."date" as firt_day_of_week,
                    coalesce(a.hour_weekly,0) as hour_available,
                    coalesce(pe.hour_weekly,0) as hour_est,
                    coalesce(wh.hour_weekly,0) + coalesce(whs.hour_weekly,0) as hour_plan
                    , a.resource_type
                from available a
                left join date_table dt on dt.week_of_year = a.week_num and dt.day_of_week_iso = 1
                left join project_est pe on pe.week_num = a.week_num and pe.resource_type = a.resource_type
                left join work_hour wh on wh.week_num = a.week_num and wh.resource_type = a.resource_type
                left join work_hour_support whs on whs.week_num = a.week_num and whs.resource_type = a.resource_type

            '''.format(year=self.year, block_id=a)
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()
        today = date.today()
        first_day = date(today.year, 1, 1)
        first_week_day = first_day - timedelta(days=first_day.isoweekday() % 7 - 1)
        number_of_days = (date(today.year, 12, 31) - first_day).days - (first_day - first_week_day).days + 1
        number_of_week = int(number_of_days / 7) + 1
        if (first_day - first_week_day).days > 0:
            number_of_week += 1
        A = {}
        B = {}
        C = {}

        for r in recs:
            week_number = int(r['week_num'])
            if r['hour_available'] > 0:
                if week_number not in A:
                    A[week_number] = {}  # A[0] = {}
                if r['resource_type'] == 'seniorengsub':
                    A[week_number]['seniorengsub'] = r['hour_available']  # A[0] = {'seniorengsub': 1}
                elif r['resource_type'] == 'engsub':
                    A[week_number]['engsub'] = r['hour_available']  # A[0] = {'seniorengsub': 1, 'engsub': 2}
                elif r['resource_type'] == 'teamleader':
                    A[week_number]['teamleader'] = r['hour_available']
                elif r['resource_type'] == 'technician':
                    A[week_number]['technician'] = r['hour_available']
                elif r['resource_type'] == 'internship':
                    A[week_number]['internship'] = r['hour_available']
            if r['hour_est'] > 0:
                if week_number not in B:
                    B[week_number] = {}  # A[0] = {}
                if r['resource_type'] == 'seniorengsub':
                    B[week_number]['seniorengsub'] = r['hour_est']  # A[0] = {'seniorengsub': 1}
                elif r['resource_type'] == 'engsub':
                    B[week_number]['engsub'] = r['hour_est']  # A[0] = {'seniorengsub': 1, 'engsub': 2}
                elif r['resource_type'] == 'teamleader':
                    B[week_number]['teamleader'] = r['hour_est']
                elif r['resource_type'] == 'technician':
                    B[week_number]['technician'] = r['hour_est']
                elif r['resource_type'] == 'internship':
                    B[week_number]['internship'] = r['hour_est']
            if r['hour_plan'] > 0:
                if week_number not in C:
                    C[week_number] = {}  # A[0] = {}
                if r['resource_type'] == 'seniorengsub':
                    C[week_number]['seniorengsub'] = r['hour_plan']  # A[0] = {'seniorengsub': 1}
                elif r['resource_type'] == 'engsub':
                    C[week_number]['engsub'] = r['hour_plan']  # A[0] = {'seniorengsub': 1, 'engsub': 2}
                elif r['resource_type'] == 'teamleader':
                    C[week_number]['teamleader'] = r['hour_plan']
                elif r['resource_type'] == 'technician':
                    C[week_number]['technician'] = r['hour_plan']
                elif r['resource_type'] == 'internship':
                    C[week_number]['internship'] = r['hour_plan']

        column = 2
        ws.cell(3, 8).value = self.year
        for week in range(1, number_of_week + 1):
            ws.cell(4, column).value = week
            ws.cell(5, column).value = first_week_day.month
            ws.cell(6, column).value = first_week_day
            # phân mục A
            ws.cell(7, column).value = '=SUM(%s8:%s12)' % (get_column_letter(column), get_column_letter(column))
            ws.cell(8, column).value = A.get(week) and A[week].get('seniorengsub') or 0
            ws.cell(9, column).value = A.get(week) and A[week].get('engsub') or 0
            ws.cell(10, column).value = A.get(week) and A[week].get('teamleader') or 0
            ws.cell(11, column).value = A.get(week) and A[week].get('technician') or 0
            ws.cell(12, column).value = A.get(week) and A[week].get('internship') or 0
            # phân mục B
            ws.cell(13, column).value = '=SUM(%s14:%s18)' % (get_column_letter(column), get_column_letter(column))
            ws.cell(14, column).value = B.get(week) and B[week].get('seniorengsub') or 0
            ws.cell(15, column).value = B.get(week) and B[week].get('engsub') or 0
            ws.cell(16, column).value = B.get(week) and B[week].get('teamleader') or 0
            ws.cell(17, column).value = B.get(week) and B[week].get('technician') or 0
            ws.cell(18, column).value = B.get(week) and B[week].get('internship') or 0
            # phân mục C
            ws.cell(19, column).value = '=SUM(%s20:%s24)' % (get_column_letter(column), get_column_letter(column))
            ws.cell(20, column).value = C.get(week) and C[week].get('seniorengsub') or 0
            ws.cell(21, column).value = C.get(week) and C[week].get('engsub') or 0
            ws.cell(22, column).value = C.get(week) and C[week].get('teamleader') or 0
            ws.cell(23, column).value = C.get(week) and C[week].get('technician') or 0
            ws.cell(24, column).value = C.get(week) and C[week].get('internship') or 0
            #
            ws.cell(25, column).value = '=(%s13-%s7)/(%s7)' % (
            get_column_letter(column), get_column_letter(column), get_column_letter(column))

            column += 1
            first_week_day += timedelta(days=7)

        column_none = number_of_week + 2
        row_none = 4
        for week in range(number_of_week + 1, number_of_week + 4):
            for r in range(row_none, 25):
                ws.cell(r, column_none).border = self.no_border
                ws.cell(r, column_none).fill = PatternFill(bgColor= self.no_color)
            column_none + 1

        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo nhân lực tuần .xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/' + str(attachment_id.id) + '?download=true',
            'target': 'new',
        }
