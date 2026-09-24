# -*- coding: utf-8 -*-
from datetime import date, datetime
import base64
import os
from io import BytesIO
import openpyxl
import re
from openpyxl.writer.excel import save_virtual_workbook
from openpyxl.styles import PatternFill, Font, Border, Alignment
from copy import copy
from odoo import _, api, fields, models
from odoo.exceptions import UserError
import calendar


def copy_cell_style(source_cell, target_cell):
    """Copy all style properties from source cell to target cell"""
    target_cell.number_format = copy(source_cell.number_format)
    target_cell.font = copy(source_cell.font)
    target_cell.border = copy(source_cell.border)
    target_cell.protection = copy(source_cell.protection)
    target_cell.alignment = copy(source_cell.alignment)


CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]')
FORMULA_PREFIXES = ('=', '+', '-', '@')


def clean_text(value):
    """Strip control characters and guard against Excel CSV injection."""
    if isinstance(value, str):
        value = CONTROL_CHAR_PATTERN.sub('', value)
        value = value.replace('\t', ' ')
        stripped = value.lstrip()
        if stripped and stripped[0] in FORMULA_PREFIXES:
            leading_ws = value[:len(value) - len(stripped)]
            value = f"{leading_ws}'{stripped}"
    return value


class CustomerSatisfaction(models.TransientModel):
    _name = 'wizard.customer.satisfaction'
    _description = 'Trình báo cáo chỉ số hài lòng của khách hàng'

    year = fields.Selection([(str(x), str(x)) for x in range(1970, 2050)], 'Năm',
                            default=str(date.today().year))
    partner_id = fields.Many2one('res.partner', 'Khách hàng', domain=[('parent_id', '=', False)])

    def get_report_excel(self):
        self.ensure_one()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/customer_satisfaction.xlsx')
        ws = wb['Báo cáo']

        sql = '''
            drop table if exists month_table;
            CREATE TEMPORARY table month_table(thang integer);
            insert into month_table(thang)
            values (1), (2), (3), (4), (5), (6), (7), (8), (9), (10), (11), (12);
            with detail_data as
            (
                    select 
                            mt.thang,
                            (select count (*) 
                            from project_project pp 
                            where pp.x_merge_project_id is null 
                                        and pp.is_merge_project is False 
                                        and extract(month from pp.x_date_plan_end) = mt.thang::int 
                                        and extract(year from pp.x_date_plan_end) = {year} 
                                        and (case when {partner_id} is not null then pp.partner_id = {partner_id} else 1 = 1 end)) as so_bc_ke_hoach,
                            (select count (*) 
                            from project_project pp 
                            where pp.x_merge_project_id is null 
                                        and pp.is_merge_project is False 
                                        and pp.x_report_date is not null
                                        and extract(month from pp.x_date_plan_end) = mt.thang::int 
                                        and extract(year from pp.x_date_plan_end) = {year}
                                        and (case when {partner_id} is not null then pp.partner_id = {partner_id} else 1 = 1 end)) as so_bc_nhan_ve,
                            (select count (*) 
                            from project_project pp 
                            where pp.x_merge_project_id is null 
                                        and pp.is_merge_project is False 
                                        and extract(month from pp.x_report_date) = mt.thang::int 
                                        and extract(year from pp.x_report_date) = {year} and pp.x_rate = 'E' 
                                        and (case when {partner_id} is not null then pp.partner_id = {partner_id} else 1 = 1 end)) as so_bc_rat_hai_long,
                            (select count (*) 
                            from project_project pp 
                            where pp.x_merge_project_id is null 
                                        and pp.is_merge_project is False 
                                        and extract(month from pp.x_report_date) = mt.thang::int 
                                        and extract(year from pp.x_report_date) = {year} and pp.x_rate = 'S' 
                                        and (case when {partner_id} is not null then pp.partner_id = {partner_id} else 1 = 1 end)) as so_bc_hai_long,
                            (select count (*) 
                            from project_project pp 
                            where pp.x_merge_project_id is null 
                                        and pp.is_merge_project is False 
                                        and extract(month from pp.x_report_date) = mt.thang::int 
                                        and extract(year from pp.x_report_date) = {year} and pp.x_rate = 'A' 
                                        and (case when {partner_id} is not null then pp.partner_id = {partner_id} else 1 = 1 end)) as so_bc_chap_nhan,
                            (select count (*) 
                            from project_project pp 
                            where pp.x_merge_project_id is null 
                                        and pp.is_merge_project is False 
                                        and extract(month from pp.x_report_date) = mt.thang::int 
                                        and extract(year from pp.x_report_date) = {year} and pp.x_rate = 'D' 
                                        and (case when {partner_id} is not null then pp.partner_id = {partner_id} else 1 = 1 end)) as so_bc_khong_hai_long
                    from month_table mt
            )
            select 
                    dd.thang,
                    dd.so_bc_ke_hoach,
                    dd.so_bc_nhan_ve,
                    case when current_date > (DATE_TRUNC('MONTH', TO_DATE(CONCAT({year}, '-', dd.thang, '-01'), 'YYYY-MM-DD') + INTERVAL '1 MONTH') - INTERVAL '1 DAY')::DATE
                            then dd.so_bc_ke_hoach - dd.so_bc_nhan_ve
                            else 0 end so_chua_hoan_thanh,
                    dd.so_bc_rat_hai_long + dd.so_bc_hai_long + dd.so_bc_chap_nhan + dd.so_bc_khong_hai_long as so_bc_co_phan_hoi,
                    dd.so_bc_rat_hai_long,
                    dd.so_bc_hai_long,
                    dd.so_bc_chap_nhan,
                    dd.so_bc_khong_hai_long,
                    0.95 as muc_tieu_muc_hai_long,
                    case when dd.so_bc_rat_hai_long + dd.so_bc_hai_long + dd.so_bc_chap_nhan + dd.so_bc_khong_hai_long > 0 
                            then (dd.so_bc_rat_hai_long + dd.so_bc_hai_long) / (dd.so_bc_rat_hai_long + dd.so_bc_hai_long + dd.so_bc_chap_nhan + dd.so_bc_khong_hai_long) else 0 end as muc_do_hai_long
            from detail_data dd
        '''.format(year=int(self.year), partner_id=self.partner_id and self.partner_id.id or 'null')

        self._cr.execute(sql)
        recs = self._cr.fetchall()

        # Fill general cells
        ws.cell(3, 6).value = str(self.year)
        ws.cell(2, 14).value = self.env.user.name
        ws.cell(3, 14).value = date.today().strftime('%d-%m-%Y')
        if self.partner_id:
            ws.cell(4, 5).value = 'Customer:'
            ws.cell(4, 6).value = self.partner_id.name

        column = 3
        col_index = 0
        for col in range(column, 15):
            row_index = 0
            row = 5
            for row in range(row, 15):
                ws.cell(row, col).value = recs[col_index][row_index]
                row_index += 1
            col_index += 1

        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Chỉ số hài lòng của khách hàng.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }


class CustomerSatisfactionDetail(models.TransientModel):
    _name = 'wizard.customer.satisfaction.detail'
    _description = 'Trình báo cáo Chi tiết chỉ số hài lòng của khách hàng'

    date_from = fields.Date('Từ ngày', required=1, default=date.today())
    date_to = fields.Date('Đến ngày', required=1, default=date.today())

    def get_report_excel(self):
        self.ensure_one()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/customer_satisfaction_detail.xlsx')
        ws = wb['Báo cáo']

        sql = '''
            select row_number() over(order by he."name") as stt,
            he."name" as full_name,
            -- total_report
              (
              select coalesce(count (*),0) as total_report
              from satisfaction_employee_ref ser1
                left join customer_satisfaction as satis1 on satis1.id = ser1.satisfaction_id
              where ser1.employee_id = he.id and satis1.report_date >= '{date_from}' and satis1.report_date <= '{date_to}'
              ),
                -- exceeded_satisfy
                (
              select coalesce(count (*),0) as exceeded_satisfy
              from satisfaction_employee_ref ser2
                left join customer_satisfaction as satis2 on satis2.id = ser2.satisfaction_id
                left join customer_rate as rate2 on rate2.id = satis2.rate_id
              where ser2.employee_id = he.id and satis2.report_date >= '{date_from}' and satis2.report_date <= '{date_to}'
                and rate2.code = 'E'
              ),
                -- satisfied
                (
              select coalesce(count (*),0) as satisfied
              from satisfaction_employee_ref ser3
                left join customer_satisfaction as satis3 on satis3.id = ser3.satisfaction_id
                left join customer_rate as rate3 on rate3.id = satis3.rate_id
              where ser3.employee_id = he.id and satis3.report_date >= '{date_from}' and satis3.report_date <= '{date_to}'
                and rate3.code = 'S'
              ),
                -- acceptable
                (
              select coalesce(count (*),0) as acceptable
              from satisfaction_employee_ref ser4
                left join customer_satisfaction as satis4 on satis4.id = ser4.satisfaction_id
                left join customer_rate as rate4 on rate4.id = satis4.rate_id
              where ser4.employee_id = he.id and satis4.report_date >= '{date_from}' and satis4.report_date <= '{date_to}'
                and rate4.code = 'A'
              ),
                -- dissatisfied
                (
              select coalesce(count (*),0) as dissatisfied
              from satisfaction_employee_ref ser5
                left join customer_satisfaction as satis5 on satis5.id = ser5.satisfaction_id
                left join customer_rate as rate5 on rate5.id = satis5.rate_id
              where ser5.employee_id = he.id and satis5.report_date >= '{date_from}' and satis5.report_date <= '{date_to}'
                and rate5.code = 'D'
              ),
                -- rating
                (
                select coalesce(sum(rating),0) as rating
                  from (select coalesce(rate6.rate, 0) as rating from
                    satisfaction_employee_ref ser6
                    left join customer_satisfaction as satis6 on satis6.id = ser6.satisfaction_id
                    left join customer_rate as rate6 on rate6.id = satis6.rate_id
                  where ser6.employee_id = he.id and satis6.report_date >= '{date_from}' and satis6.report_date <= '{date_to}'
                )

            from hr_employee he
            left join satisfaction_employee_ref as ser on ser.employee_id = he.id
            left join customer_satisfaction as satisfaction on satisfaction.id = ser.satisfaction_id

            where 1=1
            and satisfaction.report_date >= '{date_from}' and satisfaction.report_date <= '{date_to}'
            group by he.id	
            order by he."name"
        '''.format(date_from=self.date_from, date_to=self.date_to)
        self._cr.execute(sql)
        recs = self._cr.fetchall()

        # Fill general cells
        ws.cell(3, 3).value = self.date_from.strftime('%d-%m-%Y')
        ws.cell(3, 5).value = self.date_to.strftime('%d-%m-%Y')
        ws.cell(3, 8).value = self.env.user.name

        row = 7
        for r in recs:
            for col in range(1, 9):
                ws.cell(row, col).value = r[col - 1]
            # Tạo công thức tính toán với điều kiện
            formula = '=IF(SUM(D{0}:G{0})=0, "-", SUM(D{0},E{0}) * 100/SUM(D{0}:G{0}))'.format(row)
            ws.cell(row=row, column=9).value = formula
            ws.cell(row=row, column=9).number_format = '0.00'
            row += 1

        # Fill bottom line
        ws.cell(row, 2).value = 'TOTAL'
        ws.cell(row, 3).value = "=SUM(C7:C%s)" % (row - 1)
        ws.cell(row, 4).value = "=SUM(D7:D%s)" % (row - 1)
        ws.cell(row, 5).value = "=SUM(E7:E%s)" % (row - 1)
        ws.cell(row, 6).value = "=SUM(F7:F%s)" % (row - 1)
        ws.cell(row, 7).value = "=SUM(G7:G%s)" % (row - 1)

        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Chi tiết chỉ số hài lòng của khách hàng đối với nhân viên.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }


class CustomerSatisfactionSum(models.TransientModel):
    _name = 'wizard.customer.satisfaction.sum'
    _description = 'Trình báo cáo Tổng hợp chỉ số hài lòng của khách hàng'

    year = fields.Selection([(str(x), str(x)) for x in range(1970, 2050)], 'Năm',
                            default=str(date.today().year))

    def get_report_excel(self):
        self.ensure_one()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/customer_satisfaction_sum.xlsx')
        ws = wb['Báo cáo']

        sql = '''
            select row_number() over(order by he."name") as stt,
                he."name" as full_name,
            -- rating T1
            (
            select coalesce(sum(rating),0) as JAN
              from (select coalesce(rate1.rate, 0) as rating from
                satisfaction_employee_ref ser1
                left join customer_satisfaction as satis1 on satis1.id = ser1.satisfaction_id
                left join customer_rate as rate1 on rate1.id = satis1.rate_id
              where ser1.employee_id = he.id 
            and extract(year from satis1.end_date) = {year}  and extract(month from satis1.end_date) = 1 ) 
            ),
            -- rating T2
            (
            select coalesce(sum(rating),0) as FEB
              from (select coalesce(rate2.rate, 0) as rating from
                satisfaction_employee_ref ser2
                left join customer_satisfaction as satis2 on satis2.id = ser2.satisfaction_id
                left join customer_rate as rate2 on rate2.id = satis2.rate_id
              where ser2.employee_id = he.id 
            and extract(year from satis2.end_date) = {year}  and extract(month from satis2.end_date) = 2 ) 
            ),
            -- rating T3
            (
            select coalesce(sum(rating),0) as MAR
              from (select coalesce(rate3.rate, 0) as rating from
                satisfaction_employee_ref ser3
                left join customer_satisfaction as satis3 on satis3.id = ser3.satisfaction_id
                left join customer_rate as rate3 on rate3.id = satis3.rate_id
              where ser3.employee_id = he.id 
            and extract(year from satis3.end_date) = {year}  and extract(month from satis3.end_date) = 3 ) 
            ),
            -- rating T4
            (
            select coalesce(sum(rating),0) as APR
              from (select coalesce(rate4.rate, 0) as rating from
                satisfaction_employee_ref ser4
                left join customer_satisfaction as satis4 on satis4.id = ser4.satisfaction_id
                left join customer_rate as rate4 on rate4.id = satis4.rate_id
              where ser4.employee_id = he.id 
            and extract(year from satis4.end_date) = {year}  and extract(month from satis4.end_date) = 4 ) 
            ),
            -- rating T5
            (
            select coalesce(sum(rating),0) as MAY
              from (select coalesce(rate5.rate, 0) as rating from
                satisfaction_employee_ref ser5
                left join customer_satisfaction as satis5 on satis5.id = ser5.satisfaction_id
                left join customer_rate as rate5 on rate5.id = satis5.rate_id
              where ser5.employee_id = he.id 
            and extract(year from satis5.end_date) = {year}  and extract(month from satis5.end_date) = 5 ) 
            ),
            -- rating T6
            (
            select coalesce(sum(rating),0) as JUN
              from (select coalesce(rate6.rate, 0) as rating from
                satisfaction_employee_ref ser6
                left join customer_satisfaction as satis6 on satis6.id = ser6.satisfaction_id
                left join customer_rate as rate6 on rate6.id = satis6.rate_id
              where ser6.employee_id = he.id 
            and extract(year from satis6.end_date) = {year}  and extract(month from satis6.end_date) = 6 ) 
            ),
            -- rating T7
            (
              select coalesce(sum(rating), 0) as JUL
              from (
                select coalesce(rate7.rate, 0) as rating
                from satisfaction_employee_ref ser7
                left join customer_satisfaction as satis7 on satis7.id = ser7.satisfaction_id
                left join customer_rate as rate7 on rate7.id = satis7.rate_id
                where ser7.employee_id = he.id
                and extract(year from satis7.end_date) = {year}
                and extract(month from satis7.end_date) = 7
              )
            ),

            -- rating T8
            (
              select coalesce(sum(rating), 0) as AUG
              from (
                select coalesce(rate8.rate, 0) as rating
                from satisfaction_employee_ref ser8
                left join customer_satisfaction as satis8 on satis8.id = ser8.satisfaction_id
                left join customer_rate as rate8 on rate8.id = satis8.rate_id
                where ser8.employee_id = he.id
                and extract(year from satis8.end_date) = {year}
                and extract(month from satis8.end_date) = 8
              )
            ),

            -- rating T9
            (
              select coalesce(sum(rating), 0) as SEP
              from (
                select coalesce(rate9.rate, 0) as rating
                from satisfaction_employee_ref ser9
                left join customer_satisfaction as satis9 on satis9.id = ser9.satisfaction_id
                left join customer_rate as rate9 on rate9.id = satis9.rate_id
                where ser9.employee_id = he.id
                and extract(year from satis9.end_date) = {year}
                and extract(month from satis9.end_date) = 9
              )
            ),

            -- rating T10
            (
              select coalesce(sum(rating), 0) as OCT
              from (
                select coalesce(rate10.rate, 0) as rating
                from satisfaction_employee_ref ser10
                left join customer_satisfaction as satis10 on satis10.id = ser10.satisfaction_id
                left join customer_rate as rate10 on rate10.id = satis10.rate_id
                where ser10.employee_id = he.id
                and extract(year from satis10.end_date) = {year}
                and extract(month from satis10.end_date) = 10
              )
            ),

            -- rating T11
            (
              select coalesce(sum(rating), 0) as NOV
              from (
                select coalesce(rate11.rate, 0) as rating
                from satisfaction_employee_ref ser11
                left join customer_satisfaction as satis11 on satis11.id = ser11.satisfaction_id
                left join customer_rate as rate11 on rate11.id = satis11.rate_id
                where ser11.employee_id = he.id
                and extract(year from satis11.end_date) = {year}
                and extract(month from satis11.end_date) = 11
              )
            ),

            -- rating T12
            (
              select coalesce(sum(rating), 0) as DEC
              from (
                select coalesce(rate12.rate, 0) as rating
                from satisfaction_employee_ref ser12
                left join customer_satisfaction as satis12 on satis12.id = ser12.satisfaction_id
                left join customer_rate as rate12 on rate12.id = satis12.rate_id
                where ser12.employee_id = he.id
                and extract(year from satis12.end_date) = {year}
                and extract(month from satis12.end_date) = 12
              )
            )  
            from hr_employee he
            left join satisfaction_employee_ref as ser on ser.employee_id = he.id
            left join customer_satisfaction as satisfaction on satisfaction.id = ser.satisfaction_id   
            where 1=1
                and extract(year from satisfaction.end_date) = {year} 
            group by he.id	
            order by he."name"
        '''.format(year=int(self.year))
        self._cr.execute(sql)
        recs = self._cr.fetchall()

        # Fill general cells
        ws.cell(3, 6).value = str(self.year)
        ws.cell(3, 14).value = date.today().strftime('%d-%m-%Y')
        ws.cell(2, 14).value = self.env.user.name

        row = 6
        for r in recs:
            for col in range(1, 15):
                ws.cell(row, col).value = r[col - 1]

            ws.cell(row, 15).value = "=sum(C%s:N%s)" % (row, row)
            row += 1

        # Fill bottom line
        ws.cell(row, 2).value = 'TOTAL'
        ws.cell(row, 3).value = "=SUM(C6:C%s)" % (row - 1)
        ws.cell(row, 4).value = "=SUM(D6:D%s)" % (row - 1)
        ws.cell(row, 5).value = "=SUM(E6:E%s)" % (row - 1)
        ws.cell(row, 6).value = "=SUM(F6:F%s)" % (row - 1)
        ws.cell(row, 7).value = "=SUM(G6:G%s)" % (row - 1)
        ws.cell(row, 8).value = "=SUM(H6:H%s)" % (row - 1)
        ws.cell(row, 9).value = "=SUM(I6:I%s)" % (row - 1)
        ws.cell(row, 10).value = "=SUM(J6:J%s)" % (row - 1)
        ws.cell(row, 11).value = "=SUM(K6:K%s)" % (row - 1)
        ws.cell(row, 12).value = "=SUM(L6:L%s)" % (row - 1)
        ws.cell(row, 13).value = "=SUM(M6:M%s)" % (row - 1)
        ws.cell(row, 14).value = "=SUM(N6:N%s)" % (row - 1)

        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Tổng hợp chỉ số hài lòng của khách hàng đối với nhân viên.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }


class ProjectCustomerSatisfaction(models.TransientModel):
    _name = 'wizard.project.customer.satisfaction'
    _description = 'Trình báo cáo chỉ số hài lòng của khách hàng theo dự án'

    year = fields.Selection([(str(x), str(x)) for x in range(1970, 2050)], 'Năm',
                            default=str(date.today().year))
    month = fields.Selection([(str(x), str(x)) for x in range(1, 13)], 'Tháng',
                             default=str(date.today().month))
    partner_id = fields.Many2one('res.partner', 'Khách hàng', domain=[('parent_id', '=', False)])

    def yearly_satisfaction(self):
        sql = '''
            select row_number() over(order by he."name") as stt,
                he."name" as full_name,
            -- rating T1
            (
            select coalesce(sum(rating),0) as JAN
              from (select coalesce(rate1.rate, 0) as rating from
                satisfaction_employee_ref ser1
                left join customer_satisfaction as satis1 on satis1.id = ser1.satisfaction_id
                left join customer_rate as rate1 on rate1.id = satis1.rate_id
              where ser1.employee_id = he.id 
            and extract(year from satis1.report_date) = {year}  and extract(month from satis1.report_date) = 1 ) 
            ),
            -- rating T2
            (
            select coalesce(sum(rating),0) as FEB
              from (select coalesce(rate2.rate, 0) as rating from
                satisfaction_employee_ref ser2
                left join customer_satisfaction as satis2 on satis2.id = ser2.satisfaction_id
                left join customer_rate as rate2 on rate2.id = satis2.rate_id
              where ser2.employee_id = he.id 
            and extract(year from satis2.report_date) = {year}  and extract(month from satis2.report_date) = 2 ) 
            ),
            -- rating T3
            (
            select coalesce(sum(rating),0) as MAR
              from (select coalesce(rate3.rate, 0) as rating from
                satisfaction_employee_ref ser3
                left join customer_satisfaction as satis3 on satis3.id = ser3.satisfaction_id
                left join customer_rate as rate3 on rate3.id = satis3.rate_id
              where ser3.employee_id = he.id 
            and extract(year from satis3.report_date) = {year}  and extract(month from satis3.report_date) = 3 ) 
            ),
            -- rating T4
            (
            select coalesce(sum(rating),0) as APR
              from (select coalesce(rate4.rate, 0) as rating from
                satisfaction_employee_ref ser4
                left join customer_satisfaction as satis4 on satis4.id = ser4.satisfaction_id
                left join customer_rate as rate4 on rate4.id = satis4.rate_id
              where ser4.employee_id = he.id 
            and extract(year from satis4.report_date) = {year}  and extract(month from satis4.report_date) = 4 ) 
            ),
            -- rating T5
            (
            select coalesce(sum(rating),0) as MAY
              from (select coalesce(rate5.rate, 0) as rating from
                satisfaction_employee_ref ser5
                left join customer_satisfaction as satis5 on satis5.id = ser5.satisfaction_id
                left join customer_rate as rate5 on rate5.id = satis5.rate_id
              where ser5.employee_id = he.id 
            and extract(year from satis5.report_date) = {year}  and extract(month from satis5.report_date) = 5 ) 
            ),
            -- rating T6
            (
            select coalesce(sum(rating),0) as JUN
              from (select coalesce(rate6.rate, 0) as rating from
                satisfaction_employee_ref ser6
                left join customer_satisfaction as satis6 on satis6.id = ser6.satisfaction_id
                left join customer_rate as rate6 on rate6.id = satis6.rate_id
              where ser6.employee_id = he.id 
            and extract(year from satis6.report_date) = {year}  and extract(month from satis6.report_date) = 6 ) 
            ),
            -- rating T7
            (
              select coalesce(sum(rating), 0) as JUL
              from (
                select coalesce(rate7.rate, 0) as rating
                from satisfaction_employee_ref ser7
                left join customer_satisfaction as satis7 on satis7.id = ser7.satisfaction_id
                left join customer_rate as rate7 on rate7.id = satis7.rate_id
                where ser7.employee_id = he.id
                and extract(year from satis7.report_date) = {year}
                and extract(month from satis7.report_date) = 7
              )
            ),

            -- rating T8
            (
              select coalesce(sum(rating), 0) as AUG
              from (
                select coalesce(rate8.rate, 0) as rating
                from satisfaction_employee_ref ser8
                left join customer_satisfaction as satis8 on satis8.id = ser8.satisfaction_id
                left join customer_rate as rate8 on rate8.id = satis8.rate_id
                where ser8.employee_id = he.id
                and extract(year from satis8.report_date) = {year}
                and extract(month from satis8.report_date) = 8
              )
            ),

            -- rating T9
            (
              select coalesce(sum(rating), 0) as SEP
              from (
                select coalesce(rate9.rate, 0) as rating
                from satisfaction_employee_ref ser9
                left join customer_satisfaction as satis9 on satis9.id = ser9.satisfaction_id
                left join customer_rate as rate9 on rate9.id = satis9.rate_id
                where ser9.employee_id = he.id
                and extract(year from satis9.report_date) = {year}
                and extract(month from satis9.report_date) = 9
              )
            ),

            -- rating T10
            (
              select coalesce(sum(rating), 0) as OCT
              from (
                select coalesce(rate10.rate, 0) as rating
                from satisfaction_employee_ref ser10
                left join customer_satisfaction as satis10 on satis10.id = ser10.satisfaction_id
                left join customer_rate as rate10 on rate10.id = satis10.rate_id
                where ser10.employee_id = he.id
                and extract(year from satis10.report_date) = {year}
                and extract(month from satis10.report_date) = 10
              )
            ),

            -- rating T11
            (
              select coalesce(sum(rating), 0) as NOV
              from (
                select coalesce(rate11.rate, 0) as rating
                from satisfaction_employee_ref ser11
                left join customer_satisfaction as satis11 on satis11.id = ser11.satisfaction_id
                left join customer_rate as rate11 on rate11.id = satis11.rate_id
                where ser11.employee_id = he.id
                and extract(year from satis11.report_date) = {year}
                and extract(month from satis11.report_date) = 11
              )
            ),

            -- rating T12
            (
              select coalesce(sum(rating), 0) as DEC
              from (
                select coalesce(rate12.rate, 0) as rating
                from satisfaction_employee_ref ser12
                left join customer_satisfaction as satis12 on satis12.id = ser12.satisfaction_id
                left join customer_rate as rate12 on rate12.id = satis12.rate_id
                where ser12.employee_id = he.id
                and extract(year from satis12.report_date) = {year}
                and extract(month from satis12.report_date) = 12
              )
            )  
            from hr_employee he
            left join satisfaction_employee_ref as ser on ser.employee_id = he.id
            left join customer_satisfaction as satisfaction on satisfaction.id = ser.satisfaction_id   
            where 1=1
                and extract(year from satisfaction.report_date) = {year} 
            group by he.id	
            order by he."name"
        '''.format(year=int(self.year))
        self._cr.execute(sql)
        recs = self._cr.fetchall()
        return recs

    def monthly_satisfaction(self, date_from, date_to):
        sql = '''
            select row_number() over(order by he."name") as stt,
            he."name" as full_name,
            -- total_report
              (
              select coalesce(count (*),0) as total_report
              from satisfaction_employee_ref ser1
                left join customer_satisfaction as satis1 on satis1.id = ser1.satisfaction_id
              where ser1.employee_id = he.id and satis1.report_date BETWEEN '{date_from}' and '{date_to}'
              ),
                -- exceeded_satisfy
                (
              select coalesce(count (*),0) as exceeded_satisfy
              from satisfaction_employee_ref ser2
                left join customer_satisfaction as satis2 on satis2.id = ser2.satisfaction_id
                left join customer_rate as rate2 on rate2.id = satis2.rate_id
              where ser2.employee_id = he.id and satis2.report_date BETWEEN '{date_from}' and '{date_to}' 
                and rate2.code = 'E'
              ),
                -- satisfied
                (
              select coalesce(count (*),0) as satisfied
              from satisfaction_employee_ref ser3
                left join customer_satisfaction as satis3 on satis3.id = ser3.satisfaction_id
                left join customer_rate as rate3 on rate3.id = satis3.rate_id
              where ser3.employee_id = he.id and satis3.report_date BETWEEN '{date_from}' and '{date_to}' 
                and rate3.code = 'S'
              ),
                -- acceptable
                (
              select coalesce(count (*),0) as acceptable
              from satisfaction_employee_ref ser4
                left join customer_satisfaction as satis4 on satis4.id = ser4.satisfaction_id
                left join customer_rate as rate4 on rate4.id = satis4.rate_id
              where ser4.employee_id = he.id and satis4.report_date BETWEEN '{date_from}' and '{date_to}'
                and rate4.code = 'A'
              ),
                -- dissatisfied
                (
              select coalesce(count (*),0) as dissatisfied
              from satisfaction_employee_ref ser5
                left join customer_satisfaction as satis5 on satis5.id = ser5.satisfaction_id
                left join customer_rate as rate5 on rate5.id = satis5.rate_id
              where ser5.employee_id = he.id and satis5.report_date BETWEEN '{date_from}' and '{date_to}'
                and rate5.code = 'D'
              ),
                -- rating
                (
                select coalesce(sum(rating),0) as rating
                  from (select coalesce(rate6.rate, 0) as rating from
                    satisfaction_employee_ref ser6
                    left join customer_satisfaction as satis6 on satis6.id = ser6.satisfaction_id
                    left join customer_rate as rate6 on rate6.id = satis6.rate_id
                  where ser6.employee_id = he.id and satis6.report_date BETWEEN '{date_from}' and '{date_to}')
                )

            from hr_employee he
            left join satisfaction_employee_ref as ser on ser.employee_id = he.id
            left join customer_satisfaction as satisfaction on satisfaction.id = ser.satisfaction_id

            where 1=1
            and satisfaction.report_date BETWEEN '{date_from}' and '{date_to}' 

            group by he.id	
            order by he."name"
        '''.format(date_from=date_from, date_to=date_to)
        self._cr.execute(sql)
        recs = self._cr.fetchall()
        return recs

    def trouble_shooting(self, date_from, date_to):
        sql = '''
            select row_number() over(order by he."name") as stt,
            he."name" as full_name,
            -- total_report
              (
              select coalesce(count (*),0) as total_report
              from satisfaction_employee_ref ser1
                left join customer_satisfaction as satis1 on satis1.id = ser1.satisfaction_id
              where ser1.employee_id = he.id and satis1.report_date BETWEEN '{date_from}' and '{date_to}' 
              ),
                -- exceeded_satisfy
                (
              select coalesce(count (*),0) as exceeded_satisfy
              from satisfaction_employee_ref ser2
                left join customer_satisfaction as satis2 on satis2.id = ser2.satisfaction_id
                left join customer_rate as rate2 on rate2.id = satis2.rate_id
              where ser2.employee_id = he.id and satis2.report_date BETWEEN '{date_from}' and '{date_to}' 
                and rate2.code = 'E'
              ),
                -- satisfied
                (
              select coalesce(count (*),0) as satisfied
              from satisfaction_employee_ref ser3
                left join customer_satisfaction as satis3 on satis3.id = ser3.satisfaction_id
                left join customer_rate as rate3 on rate3.id = satis3.rate_id
              where ser3.employee_id = he.id and satis3.report_date BETWEEN '{date_from}' and '{date_to}'
                and rate3.code = 'S'
              ),
                -- acceptable
                (
              select coalesce(count (*),0) as acceptable
              from satisfaction_employee_ref ser4
                left join customer_satisfaction as satis4 on satis4.id = ser4.satisfaction_id
                left join customer_rate as rate4 on rate4.id = satis4.rate_id
              where ser4.employee_id = he.id and satis4.report_date BETWEEN '{date_from}' and '{date_to}'
                and rate4.code = 'A'
              ),
                -- dissatisfied
                (
              select coalesce(count (*),0) as dissatisfied
              from satisfaction_employee_ref ser5
                left join customer_satisfaction as satis5 on satis5.id = ser5.satisfaction_id
                left join customer_rate as rate5 on rate5.id = satis5.rate_id
              where ser5.employee_id = he.id and satis5.report_date BETWEEN '{date_from}' and '{date_to}'
                and rate5.code = 'D'
              ),
                -- rating
                (
                select coalesce(sum(rating),0) as rating
                  from (select coalesce(rate6.rate, 0) as rating from
                    satisfaction_employee_ref ser6
                    left join customer_satisfaction as satis6 on satis6.id = ser6.satisfaction_id
                    left join customer_rate as rate6 on rate6.id = satis6.rate_id
                  where ser6.employee_id = he.id and satis6.report_date BETWEEN '{date_from}' and '{date_to}')
                )

            from hr_employee he
            left join satisfaction_employee_ref as ser on ser.employee_id = he.id
            left join customer_satisfaction as satisfaction on satisfaction.id = ser.satisfaction_id

            where 1=1
            and satisfaction.report_date BETWEEN '{date_from}' and '{date_to}'
            and satisfaction.project_type = 'trouble'
            group by he.id	
            order by he."name"
        '''.format(date_from=date_from, date_to=date_to)
        self._cr.execute(sql)
        recs = self._cr.fetchall()
        return recs


    def add_total_row(self, ws_trouble_shooting, ws_template, row, template_row=8):
        """Add total row to trouble shooting worksheet"""
        # Empty cell with styling
        self.copy_cell_style(ws_template.cell(template_row, 1), ws_trouble_shooting.cell(row, 1))

        # Total label
        cell = ws_trouble_shooting.cell(row, 2)
        cell.value = 'TOTAL'
        cell.font = Font(bold=True)
        self.copy_cell_style(ws_template.cell(template_row, 2), cell)

        # Sum formulas for columns 3-7
        number_format = '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)'
        for col in range(3, 8):
            cell = ws_trouble_shooting.cell(row, col)
            cell.value = f'=SUM({chr(64 + col)}8:{chr(64 + col)}{row - 1})'
            cell.number_format = number_format
            self.copy_cell_style(ws_trouble_shooting.cell(template_row, col), cell)

        # Percentage formula for total
        cell = ws_trouble_shooting.cell(row, 8)
        cell.value = f'=IF(SUM(D{row}:G{row})=0,"-",SUM(D{row}:E{row})/SUM(D{row}:G{row}))'
        cell.number_format = number_format
        self.copy_cell_style(ws_trouble_shooting.cell(template_row, 8), cell)

        # Empty cell with styling for column 9
        cell = ws_trouble_shooting.cell(row, 9)
        cell.number_format = number_format
        self.copy_cell_style(ws_trouble_shooting.cell(template_row, 9), cell)



    def get_report_excel(self):
        self.ensure_one()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/CUSTOMER_SATISFACTION_REPORT.xlsx')
        ws = wb['DATA']

        # Fill general cells
        ws2 = wb['General']
        ws2.cell(3, 7).value = str(self.year)
        ws2.cell(1, 15).value = clean_text(self.env.user.name)
        ws2.cell(3, 15).value = date.today().strftime('%d-%m-%Y')

        sql = '''
        select distinct on (satis.id) so.id as so_id, so.name as ma_chinh_du_an, project.id as project_id,
        partner.name as ten_kh,
        so.name as name, lp.name as dia_diem,
        project.name as ma_phu_du_an, project.x_scope as ten_du_an,
        -- satis.project_type as loai_du_an,
        case when satis.project_type = 'maintainance' then 'Maintenance'
        when satis.project_type = 'service' then 'Services'
        when satis.project_type = 'operation' then 'Facility Management'
        when satis.project_type = 'trouble' then 'Trouble shooting'
        when satis.project_type = 'warranty' then 'Warranty'
        when satis.project_type = 'support' then 'Support'
        when satis.project_type = 'survey' then 'Survey'
        else '' end as loai_du_an,
        so.device, so.model, so.frequency,
        case when project.x_cost_ok then 'Charge' else 'Free' end as tinh_phi,
        project.x_date_plan_start, project.x_date_plan_end,
        satis.end_date, satis.report_date,
        --project.x_date_start, project.x_date_end,
        satis.general_status, satis.feedback, satis.action,
        -- phu trach du an
        ( select string_agg(DISTINCT he.x_code, ', ') AS employee_names
        from satisfaction_employee_ref ser
        left join hr_employee he on he.id = ser.employee_id
        where ser.satisfaction_id = satis.id),

        -- muc hai long
        rate.code as muc_hai_long, satis.feedback_note, so.user_id,
        partner1.name as pic_leader,
        satis.id as satis_id
        from project_project project
        left join sale_order so on project.x_order_id = so.id
        left join res_partner as partner on so.partner_id = partner.id
        left join res_users as user1 on user1.id = so.user_id
        left join res_partner as partner1 on partner1.id = user1.partner_id
        left join res_partner as lp on lp.id = so.location_partner_id
        left join customer_satisfaction as satis on satis.project_id = project.id
        left join customer_rate as rate on rate.id = satis.rate_id
        left join satisfaction_employee_ref as ser on ser.satisfaction_id = satis.id
        where (
            extract(year from satis.report_date) = {year}
            OR (satis.report_date IS NULL
                AND extract(year from project.x_date_plan_end) = {year})
          )
          and project.export_satisfaction_report = true
        '''.format(year=int(self.year))
        if self.partner_id:
            sql += f' and so.partner_id = {self.partner_id.id}'
        sql += ' order by satis.id, satis.report_date asc'
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()

        sql2 = """
        select so.id as so_id, so.name as ma_chinh_du_an, project.id as project_id,
        partner.name as ten_kh,
        so.name as name, lp.name as dia_diem,
        project.name as ma_phu_du_an, project.x_scope as ten_du_an,
        -- satis.project_type as loai_du_an,
        case when project.x_project_type = 'maintainance' then 'Maintenance'
        when project.x_project_type = 'service' then 'Services'
        when project.x_project_type = 'operation' then 'Facility Management'
        when project.x_project_type = 'trouble' then 'Trouble shooting'
        when project.x_project_type = 'warranty' then 'Warranty'
        when project.x_project_type = 'support' then 'Support'
        when project.x_project_type = 'survey' then 'Survey'
        else '' end as loai_du_an,
        so.device, so.model, so.frequency,
        case when project.x_cost_ok then 'Charge' else 'Free' end as tinh_phi,
        project.x_date_plan_start as date_plan_start,
        project.x_date_plan_end as date_plan_end,
        project.x_date_end as date_end,
        project.x_report_date as report_date,
        --project.x_date_start as date_start, project.x_date_end as date_end,
        project.x_general_status as general_status,
        project.x_feedback as feedback,
        project.x_action as action,
        -- phu trach du an
        ( select string_agg(DISTINCT he.x_code, ', ') AS employee_names
        from satisfaction_employee_ref ser
        left join hr_employee he on he.user_id = project.user_id),

        -- muc hai long
        rate.code as muc_hai_long,
        project.x_feedback_note as feedback_note,
        so.user_id,
        partner1.name as pic_leader
        from project_project project
        left join sale_order so on project.x_order_id = so.id
        left join res_partner as partner on so.partner_id = partner.id
        left join res_users as user1 on user1.id = so.user_id
        left join res_partner as partner1 on partner1.id = user1.partner_id
        left join res_partner as lp on lp.id = so.location_partner_id
        left join customer_rate as rate on rate.id = project.x_rate_id
        where project.export_satisfaction_report = true
        and project.x_rate_id is not null
        and (project.x_report_date IS NULL OR extract(year from project.x_report_date) = {year}
            AND NOT EXISTS (
              SELECT 1
              FROM customer_satisfaction satis
              WHERE satis.project_id = project.id
                AND (satis.report_date IS NULL OR extract(year FROM satis.report_date) = {year})
          ))""".format(year=int(self.year))
        if self.partner_id:
            sql2 += f' and so.partner_id = {self.partner_id.id}'
        sql2 += ' order by project.x_report_date asc'

        self._cr.execute(sql2)
        recs = recs + self._cr.dictfetchall()

        # sql3: Lấy các project có export_satisfaction_report = true
        # nhưng KHÔNG có dữ liệu trong customer_satisfaction và KHÔNG có x_rate_id
        sql3 = """
        select so.id as so_id, so.name as ma_chinh_du_an, project.id as project_id,
        partner.name as ten_kh,
        so.name as name, lp.name as dia_diem,
        project.name as ma_phu_du_an, project.x_scope as ten_du_an,
        case when project.x_project_type = 'maintainance' then 'Maintenance'
        when project.x_project_type = 'service' then 'Services'
        when project.x_project_type = 'operation' then 'Facility Management'
        when project.x_project_type = 'trouble' then 'Trouble shooting'
        when project.x_project_type = 'warranty' then 'Warranty'
        when project.x_project_type = 'support' then 'Support'
        when project.x_project_type = 'survey' then 'Survey'
        else '' end as loai_du_an,
        so.device, so.model, so.frequency,
        case when project.x_cost_ok then 'Charge' else 'Free' end as tinh_phi,
        project.x_date_plan_start as x_date_plan_start,
        project.x_date_plan_end as x_date_plan_end,
        null as end_date,
        null as report_date,
        null as general_status,
        null as feedback,
        null as action,
        null as employee_names,
        null as muc_hai_long,
        null as feedback_note,
        so.user_id,
        partner1.name as pic_leader
        from project_project project
        left join sale_order so on project.x_order_id = so.id
        left join res_partner as partner on so.partner_id = partner.id
        left join res_users as user1 on user1.id = so.user_id
        left join res_partner as partner1 on partner1.id = user1.partner_id
        left join res_partner as lp on lp.id = so.location_partner_id
        where project.export_satisfaction_report = true
          and (project.x_rate_id is null)
          and NOT EXISTS (
              SELECT 1
              FROM customer_satisfaction satis
              WHERE satis.project_id = project.id
          )
          and extract(year from project.x_date_plan_end) = {year}
        """.format(year=int(self.year))
        if self.partner_id:
            sql3 += f' and so.partner_id = {self.partner_id.id}'
        sql3 += ' order by project.x_date_plan_end asc'

        self._cr.execute(sql3)
        recs = self._cr.dictfetchall() + recs

        def set_total(ws, summary_row, template_row, col, formula, bold=False):
            cell = ws.cell(summary_row, column=col)
            template_cell = ws.cell(template_row, column=col)
            copy_cell_style(template_cell, cell)
            cell.value = formula
            cell.number_format = number_format
            if bold:
                cell.font = Font(bold=True)

        def set_cell(ws, template_row, col, val, fmt=True):
            cell = ws.cell(r, column=col)
            template_cell = ws.cell(template_row, column=col)
            cell.value = val
            copy_cell_style(template_cell, cell)
            if fmt:
                cell.number_format = number_format

        row = 8  # 7
        for rec in recs:
            ws.cell(row, 1).value = clean_text(rec.get('ten_kh', ''))
            ws.cell(row, 1).number_format = ws.cell(9, 1).number_format
            ws.cell(row, 2).value = clean_text(rec.get('dia_diem', ''))
            ws.cell(row, 2).number_format = ws.cell(9, 2).number_format
            ws.cell(row, 3).value = clean_text(rec.get('ma_chinh_du_an', ''))
            ws.cell(row, 3).number_format = ws.cell(9, 3).number_format
            ws.cell(row, 4).value = clean_text(rec.get('ma_phu_du_an', ''))
            ws.cell(row, 4).number_format = ws.cell(9, 4).number_format
            ws.cell(row, 5).value = clean_text(rec.get('ten_du_an', ''))
            ws.cell(row, 5).number_format = ws.cell(9, 5).number_format
            ws.cell(row, 6).value = clean_text(rec.get('loai_du_an', ''))
            ws.cell(row, 6).number_format = ws.cell(9, 10).number_format
            ws.cell(row, 7).value = clean_text(rec.get('tinh_phi', ''))
            ws.cell(row, 7).number_format = ws.cell(9, 11).number_format
            ws.cell(row, 8).value = rec.get('x_date_plan_start', '')
            ws.cell(row, 8).number_format = 'dd-mm-yyyy'
            ws.cell(row, 9).value = rec.get('x_date_plan_end', '')
            ws.cell(row, 9).number_format = 'dd-mm-yyyy'
            ws.cell(row, 10).value = rec.get('end_date', '')
            ws.cell(row, 10).number_format = 'dd-mm-yyyy'
            ws.cell(row, 11).value = rec.get('report_date', '')
            ws.cell(row, 11).number_format = 'dd-mm-yyyy'
            ws.cell(row, 12).value = clean_text(rec.get('general_status', ''))
            ws.cell(row, 12).number_format = ws.cell(9, 16).number_format
            ws.cell(row, 13).value = clean_text(rec.get('feedback', ''))
            ws.cell(row, 13).number_format = ws.cell(9, 17).number_format
            ws.cell(row, 14).value = clean_text(rec.get('employee_names', ''))
            ws.cell(row, 14).number_format = ws.cell(9, 18).number_format
            ws.cell(row, 15).value = clean_text(rec.get('action', ''))
            ws.cell(row, 15).number_format = ws.cell(9, 19).number_format
            ws.cell(row, 16).value = clean_text(rec.get('muc_hai_long', ''))
            ws.cell(row, 16).number_format = ws.cell(9, 20).number_format
            ws.cell(row, 17).value = clean_text(rec.get('feedback_note', ''))
            ws.cell(row, 17).number_format = ws.cell(9, 21).number_format
            row += 1

        from openpyxl.styles import Side
        from openpyxl.cell.cell import MergedCell

        columns_to_center = {1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 13, 15}
        thin_side = Side(style='thin')
        thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        max_row = ws.max_row or 0
        max_col = ws.max_column or 0
        start_row = 8
        if max_row >= start_row:
            for row_idx in range(start_row, max_row + 1):
                ws.row_dimensions[row_idx].height = 70
            for row_cells in ws.iter_rows(min_row=start_row, max_row=max_row, min_col=1, max_col=max_col):
                for cell in row_cells:
                    if isinstance(cell, MergedCell):
                        continue
                    cell.font = cell.font.copy(name='Arial', size=12, scheme=None)
                    alignment = cell.alignment or Alignment()
                    if cell.col_idx == 12:
                        cell.alignment = alignment.copy(vertical='center', wrap_text=True)
                    elif cell.col_idx in columns_to_center:
                        cell.alignment = alignment.copy(horizontal='center', vertical='center')
                    else:
                        cell.alignment = alignment.copy(vertical='center')
                    cell.border = thin_border

        ws_stafflist = wb['StaffList']
        sql = """
              select he.id, he.name, he.x_code, job.name as job_name
              from hr_employee he
                       left join hr_contract contract on contract.id = he.contract_id
                       left join hr_job job on job.id = contract.job_id
              where he.active = true
              order by he.id asc"""
        self._cr.execute(sql)
        list_employees = self._cr.dictfetchall()
        row = 5
        index = 1
        for e in list_employees:
            ws_stafflist.cell(row, column=1).value = index
            copy_cell_style(ws_stafflist.cell(5, 1), ws_stafflist.cell(row, column=1))

            ws_stafflist.cell(row, 2).value = clean_text(e.get('x_code', ''))
            copy_cell_style(ws_stafflist.cell(5, 2), ws_stafflist.cell(row, column=2))

            ws_stafflist.cell(row, 3).value = clean_text(e.get('name', ''))
            copy_cell_style(ws_stafflist.cell(5, 3), ws_stafflist.cell(row, column=3))

            ws_stafflist.cell(row, 4).value = clean_text(e.get('job_name', ''))
            copy_cell_style(ws_stafflist.cell(5, 4), ws_stafflist.cell(row, column=4))

            row += 1
            index += 1

        number_format = '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)'
        ws_trouble_shooting = wb['Trouble shooting']
        template_row = 8
        row = template_row
        index = 1
        for e in list_employees:
            r = row
            set_cell(ws_trouble_shooting, template_row, 1, index, fmt=False)
            set_cell(ws_trouble_shooting, template_row, 2, f'=VLOOKUP(J{7 + index}, StaffList!B:C,2,FALSE)', fmt=False)
            set_cell(ws_trouble_shooting, template_row, 3, '=COUNTIFS(DATA!$F:$F,"=Trouble shooting", DATA!$N:$N,"*"&@$J:$J&",*",DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)+COUNTIFS(DATA!$F:$F,"=Trouble shooting", DATA!$N:$N,"*"&@$J:$J,DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)')
            set_cell(ws_trouble_shooting, template_row, 4, '=COUNTIFS(DATA!$P:$P,"=E", DATA!$F:$F,"=Trouble shooting",DATA!$N:$N,"*"&@$J:$J&",*",DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)+COUNTIFS(DATA!$P:$P,"=E", DATA!$F:$F,"=Trouble shooting",DATA!$N:$N,"*"&@$J:$J,DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)')
            set_cell(ws_trouble_shooting, template_row, 5, '=COUNTIFS(DATA!$P:$P,"=S", DATA!$F:$F,"=Trouble shooting",DATA!$N:$N,"*"&@$J:$J&",*",DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)+COUNTIFS(DATA!$P:$P,"=S", DATA!$F:$F,"=Trouble shooting",DATA!$N:$N,"*"&@$J:$J,DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)')
            set_cell(ws_trouble_shooting, template_row, 6, '=COUNTIFS(DATA!$P:$P,"=A", DATA!$F:$F,"=Trouble shooting",DATA!$N:$N,"*"&@$J:$J&",*",DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)+COUNTIFS(DATA!$P:$P,"=A", DATA!$F:$F,"=Trouble shooting",DATA!$N:$N,"*"&@$J:$J,DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)')
            set_cell(ws_trouble_shooting, template_row, 7, '=COUNTIFS(DATA!$P:$P,"=D", DATA!$F:$F,"=Trouble shooting",DATA!$N:$N,"*"&@$J:$J&",*",DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)+COUNTIFS(DATA!$P:$P,"=D", DATA!$F:$F,"=Trouble shooting",DATA!$N:$N,"*"&@$J:$J,DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)')
            # set_cell(ws_trouble_shooting, template_row, 8, f'=IF(SUM(D{7 + index}:G{7 + index})=0,"-",SUM(D{7 + index}:E{7 + index})/SUM(D{7 + index}:G{7 + index}))')
            set_cell(ws_trouble_shooting, template_row, 8, f'=D{7 + index}*10+E{7 + index}')
            set_cell(ws_trouble_shooting, template_row, 10, f'=StaffList!B{4 + index}', fmt=False)
            index += 1
            row += 1
        # Tổng kết
        summary_row = row
        set_total(ws_trouble_shooting, summary_row, template_row, 1, '')
        set_total(ws_trouble_shooting, summary_row, template_row,2, 'TOTAL', bold=True)
        set_total(ws_trouble_shooting, summary_row, template_row,3, f'=SUM(C{template_row}:{chr(66)}{row - 1})')
        set_total(ws_trouble_shooting, summary_row, template_row,4, f'=SUM(D{template_row}:D{row - 1})')
        set_total(ws_trouble_shooting, summary_row, template_row,5, f'=SUM(E{template_row}:E{row - 1})')
        set_total(ws_trouble_shooting, summary_row, template_row,6, f'=SUM(F{template_row}:F{row - 1})')
        set_total(ws_trouble_shooting, summary_row, template_row,7, f'=SUM(G{template_row}:G{row - 1})')
        # set_total(ws_trouble_shooting, summary_row, template_row,8, f'=IF(SUM(D{summary_row}:G{summary_row})=0,"-",SUM(D{summary_row}:E{summary_row})/SUM(D{summary_row}:G{summary_row}))')
        set_total(ws_trouble_shooting, summary_row, template_row,8, '')

        ws_monthly_staff_satisfaction = wb['Monthly Staff Satisfaction']

        template_row = 8
        row = template_row
        index = 1
        for e in list_employees:
            r = row
            set_cell(ws_monthly_staff_satisfaction, template_row, 1, index, fmt=False)
            set_cell(ws_monthly_staff_satisfaction, template_row, 2, f'=VLOOKUP(L{7 + index}, StaffList!B:C,2,FALSE)', fmt=False)
            set_cell(ws_monthly_staff_satisfaction, template_row, 3, f'=SUM(D{7 + index}:G{7 + index})')
            set_cell(ws_monthly_staff_satisfaction, template_row, 4, '=COUNTIFS(DATA!$P:$P,"=E", DATA!$N:$N,"*"&@$L:$L&",*",DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)+COUNTIFS(DATA!$P:$P,"=E", DATA!$N:$N,"*"&@$L:$L,DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)')
            set_cell(ws_monthly_staff_satisfaction, template_row, 5, '=COUNTIFS(DATA!$P:$P,"=S", DATA!$N:$N,"*"&@$L:$L&",*",DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)+COUNTIFS(DATA!$P:$P,"=S", DATA!$N:$N,"*"&@$L:$L,DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)')
            set_cell(ws_monthly_staff_satisfaction, template_row, 6, '=COUNTIFS(DATA!$P:$P,"=A", DATA!$N:$N,"*"&@$L:$L&",*",DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)+COUNTIFS(DATA!$P:$P,"=A", DATA!$N:$N,"*"&@$L:$L,DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)')
            set_cell(ws_monthly_staff_satisfaction, template_row, 7, '=COUNTIFS(DATA!$P:$P,"=D", DATA!$N:$N,"*"&@$L:$L&",*",DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)+COUNTIFS(DATA!$P:$P,"=D", DATA!$N:$N,"*"&@$L:$L,DATA!$K:$K,">="&$C$3,DATA!$K:$K,"<="&$E$3)')
            set_cell(ws_monthly_staff_satisfaction, template_row, 8, f'=IF(SUM(D{7 + index}:G{7 + index})=0,"-",SUM(D{7 + index}:E{7 + index})/SUM(D{7 + index}:G{7 + index}))')
            ws_monthly_staff_satisfaction.cell(r, column=8).number_format = '0%'
            set_cell(ws_monthly_staff_satisfaction, template_row, 9, f'=IF(SUM(D{7 + index}:G{7 + index})=0,"-",D{7 + index}/SUM(D{7 + index}:G{7 + index}))')
            ws_monthly_staff_satisfaction.cell(r, column=9).number_format = '0%'
            set_cell(ws_monthly_staff_satisfaction, template_row, 10, f'=D{7 + index}*10+E{7 + index}')
            set_cell(ws_monthly_staff_satisfaction, template_row, 12, f'=StaffList!B{4 + index}', fmt=False)
            index += 1
            row += 1
        # Tổng kết
        summary_row = row

        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 1, '')
        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 2, 'TOTAL', bold=True)
        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 3, f'=SUM(C{template_row}:C{row - 1})', bold=True)
        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 4, f'=SUM(D{template_row}:D{row - 1})', bold=True)
        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 5, f'=SUM(E{template_row}:E{row - 1})', bold=True)
        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 6, f'=SUM(F{template_row}:F{row - 1})', bold=True)
        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 7, f'=SUM(G{template_row}:G{row - 1})', bold=True)
        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 8, '', bold=True)
        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 9, '', bold=True)
        set_total(ws_monthly_staff_satisfaction, summary_row, template_row, 10,'', bold=True)

        ws_yearly_staff_satisfaction = wb['Yearly Staff Satisfaction']
        template_row = 8
        row = template_row
        index = 1
        for e in list_employees:
            r = row
            set_cell(ws_yearly_staff_satisfaction, template_row, 1, index, fmt=False)
            set_cell(ws_yearly_staff_satisfaction, template_row, 2, f'=VLOOKUP(Q{7 + index}, StaffList!B:C,2,FALSE)', fmt=False)
            set_cell(ws_yearly_staff_satisfaction, template_row, 3, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,C$6,1),DATA!$K:$K,"<="&DATE($F$3,C$6,C$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,C$6,1),DATA!$K:$K,"<="&DATE($F$3,C$6,C$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,C$6,1),DATA!$K:$K,"<="&DATE($F$3,C$6,C$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,C$6,1),DATA!$K:$K,"<="&DATE($F$3,C$6,C$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 4, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,D$6,1),DATA!$K:$K,"<="&DATE($F$3,D$6,D$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,D$6,1),DATA!$K:$K,"<="&DATE($F$3,D$6,D$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,D$6,1),DATA!$K:$K,"<="&DATE($F$3,D$6,D$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,D$6,1),DATA!$K:$K,"<="&DATE($F$3,D$6,D$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 5, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,E$6,1),DATA!$K:$K,"<="&DATE($F$3,E$6,E$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,E$6,1),DATA!$K:$K,"<="&DATE($F$3,E$6,E$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,E$6,1),DATA!$K:$K,"<="&DATE($F$3,E$6,E$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,E$6,1),DATA!$K:$K,"<="&DATE($F$3,E$6,E$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 6, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,F$6,1),DATA!$K:$K,"<="&DATE($F$3,F$6,F$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,F$6,1),DATA!$K:$K,"<="&DATE($F$3,F$6,F$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,F$6,1),DATA!$K:$K,"<="&DATE($F$3,F$6,F$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,F$6,1),DATA!$K:$K,"<="&DATE($F$3,F$6,F$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 7, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,G$6,1),DATA!$K:$K,"<="&DATE($F$3,G$6,G$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,G$6,1),DATA!$K:$K,"<="&DATE($F$3,G$6,G$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,G$6,1),DATA!$K:$K,"<="&DATE($F$3,G$6,G$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,G$6,1),DATA!$K:$K,"<="&DATE($F$3,G$6,G$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 8, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,H$6,1),DATA!$K:$K,"<="&DATE($F$3,H$6,H$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,H$6,1),DATA!$K:$K,"<="&DATE($F$3,H$6,H$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,H$6,1),DATA!$K:$K,"<="&DATE($F$3,H$6,H$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,H$6,1),DATA!$K:$K,"<="&DATE($F$3,H$6,H$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 9, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,I$6,1),DATA!$K:$K,"<="&DATE($F$3,I$6,I$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,I$6,1),DATA!$K:$K,"<="&DATE($F$3,I$6,I$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,I$6,1),DATA!$K:$K,"<="&DATE($F$3,I$6,I$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,I$6,1),DATA!$K:$K,"<="&DATE($F$3,I$6,I$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 10, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,J$6,1),DATA!$K:$K,"<="&DATE($F$3,J$6,J$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,J$6,1),DATA!$K:$K,"<="&DATE($F$3,J$6,J$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,J$6,1),DATA!$K:$K,"<="&DATE($F$3,J$6,J$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,J$6,1),DATA!$K:$K,"<="&DATE($F$3,J$6,J$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 11, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,K$6,1),DATA!$K:$K,"<="&DATE($F$3,K$6,K$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,K$6,1),DATA!$K:$K,"<="&DATE($F$3,K$6,K$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,K$6,1),DATA!$K:$K,"<="&DATE($F$3,K$6,K$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,K$6,1),DATA!$K:$K,"<="&DATE($F$3,K$6,K$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 12, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,L$6,1),DATA!$K:$K,"<="&DATE($F$3,L$6,L$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,L$6,1),DATA!$K:$K,"<="&DATE($F$3,L$6,L$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,L$6,1),DATA!$K:$K,"<="&DATE($F$3,L$6,L$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,L$6,1),DATA!$K:$K,"<="&DATE($F$3,L$6,L$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 13, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,M$6,1),DATA!$K:$K,"<="&DATE($F$3,M$6,M$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,M$6,1),DATA!$K:$K,"<="&DATE($F$3,M$6,M$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,M$6,1),DATA!$K:$K,"<="&DATE($F$3,M$6,M$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,M$6,1),DATA!$K:$K,"<="&DATE($F$3,M$6,M$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 14, f'=((COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,N$6,1),DATA!$K:$K,"<="&DATE($F$3,N$6,N$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=E",DATA!$K:$K,">="&DATE($F$3,N$6,1),DATA!$K:$K,"<="&DATE($F$3,N$6,N$5),DATA!$N:$N,"*"&$Q{7 + index}))*10)+(COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,N$6,1),DATA!$K:$K,"<="&DATE($F$3,N$6,N$5),DATA!$N:$N,"*"&$Q{7 + index}&",*")+COUNTIFS(DATA!$P:$P,"=S",DATA!$K:$K,">="&DATE($F$3,N$6,1),DATA!$K:$K,"<="&DATE($F$3,N$6,N$5),DATA!$N:$N,"*"&$Q{7 + index}))')
            set_cell(ws_yearly_staff_satisfaction, template_row, 15, f'=SUM(C{7 + index}:N{7 + index})')
            set_cell(ws_yearly_staff_satisfaction, template_row, 17, f'=StaffList!B{4 + index}', fmt=False)
            index += 1
            row += 1
        # Tổng kết
        summary_row = row

        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 1, '')
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 2, 'TOTAL', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 3, f'=SUM(C{template_row}:C{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 4, f'=SUM(D{template_row}:D{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 5, f'=SUM(E{template_row}:E{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 6, f'=SUM(F{template_row}:F{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 7, f'=SUM(G{template_row}:G{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 8, f'=SUM(H{template_row}:H{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 9, f'=SUM(I{template_row}:I{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 10, f'=SUM(J{template_row}:J{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 11, f'=SUM(K{template_row}:K{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 12, f'=SUM(L{template_row}:L{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 13, f'=SUM(M{template_row}:M{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 14, f'=SUM(N{template_row}:N{row - 1})', bold=True)
        set_total(ws_yearly_staff_satisfaction, summary_row, template_row, 15, '', bold=True)


        # ghi du lieu vao yearly staff satisfaction
        # recs = self.yearly_satisfaction()
        # ws3 = wb['Yearly Staff Satisfaction']
        # ws3.cell(3, 6).value = str(self.year)
        # ws3.cell(3, 14).value = date.today().strftime('%d-%m-%Y')
        # ws3.cell(1, 14).value = self.env.user.name
        # row = 8
        # for r in recs:
        #     for col in range(1, 15):
        #         ws3.cell(row, col).value = r[col - 1]
        #
        #     ws3.cell(row, 15).value = "=sum(C%s:N%s)" % (row, row)
        #     row += 1
        # # Fill bottom line
        # ws3.cell(row, 2).value = 'TOTAL'
        # ws3.cell(row, 3).value = "=SUM(C8:C%s)" % (row - 1)
        # ws3.cell(row, 4).value = "=SUM(D8:D%s)" % (row - 1)
        # ws3.cell(row, 5).value = "=SUM(E8:E%s)" % (row - 1)
        # ws3.cell(row, 6).value = "=SUM(F8:F%s)" % (row - 1)
        # ws3.cell(row, 7).value = "=SUM(G8:G%s)" % (row - 1)
        # ws3.cell(row, 8).value = "=SUM(H8:H%s)" % (row - 1)
        # ws3.cell(row, 9).value = "=SUM(I8:I%s)" % (row - 1)
        # ws3.cell(row, 10).value = "=SUM(J8:J%s)" % (row - 1)
        # ws3.cell(row, 11).value = "=SUM(K8:K%s)" % (row - 1)
        # ws3.cell(row, 12).value = "=SUM(L8:L%s)" % (row - 1)
        # ws3.cell(row, 13).value = "=SUM(M8:M%s)" % (row - 1)
        # ws3.cell(row, 14).value = "=SUM(N8:N%s)" % (row - 1)

        # ghi du lieu vao monthly staff satisfaction
        # month = int(self.month)
        # year = int(self.year)
        # _, num_days = calendar.monthrange(year, month)
        # date_from = datetime(year, month, 1)
        # date_to = datetime(year, month, num_days)
        # recs = self.monthly_satisfaction(date_from, date_to)
        # ws4 = wb['Monthly Staff Satisfaction']
        # # Fill general cells
        # ws4.cell(3, 3).value = date_from.strftime('%d-%m-%Y')
        # ws4.cell(3, 5).value = date_to.strftime('%d-%m-%Y')
        # ws4.cell(3, 8).value = self.env.user.name
        # row = 7
        # for r in recs:
        #     for col in range(1, 8):
        #         ws4.cell(row, col).value = r[col - 1]
        #     # Tạo công thức tính toán với điều kiện
        #     formula = '=IF(SUM(D{0}:G{0})=0, "-", SUM(D{0},E{0}) /SUM(D{0}:G{0}))'.format(row)
        #     ws4.cell(row=row, column=8).value = formula
        #     ws4.cell(row=row, column=9).number_format = '0.00'
        #     # rating
        #     ws4.cell(row=row, column=9).value = r[7] #r['rating']
        #     row += 1
        # # Fill bottom line
        # ws4.cell(row, 2).value = 'TOTAL'
        # ws4.cell(row, 3).value = "=SUM(C7:C%s)" % (row - 1)
        # ws4.cell(row, 4).value = "=SUM(D7:D%s)" % (row - 1)
        # ws4.cell(row, 5).value = "=SUM(E7:E%s)" % (row - 1)
        # ws4.cell(row, 6).value = "=SUM(F7:F%s)" % (row - 1)
        # ws4.cell(row, 7).value = "=SUM(G7:G%s)" % (row - 1)

        # ghi du lieu vao trouble shooting
        # recs = self.trouble_shooting(date_from, date_to)
        # ws6 = wb['Trouble shooting']
        # # Fill general cells
        # ws6.cell(3, 3).value = date_from.strftime('%d-%m-%Y')
        # ws6.cell(3, 5).value = date_to.strftime('%d-%m-%Y')
        # ws6.cell(3, 8).value = self.env.user.name
        # row = 7
        # for r in recs:
        #     for col in range(1, 8):
        #         ws6.cell(row, col).value = r[col - 1]
        #     # Tạo công thức tính toán với điều kiện
        #     formula = '=IF(SUM(D{0}:G{0})=0, "-", SUM(D{0},E{0}) /SUM(D{0}:G{0}))'.format(row)
        #     ws6.cell(row=row, column=8).value = formula
        #     ws6.cell(row=row, column=9).number_format = '0.00'
        #     ws6.cell(row=row, column=9).value = r[7]
        #     row += 1
        # # Fill bottom line
        # ws6.cell(row, 2).value = 'TOTAL'
        # ws6.cell(row, 3).value = "=SUM(C7:C%s)" % (row - 1)
        # ws6.cell(row, 4).value = "=SUM(D7:D%s)" % (row - 1)
        # ws6.cell(row, 5).value = "=SUM(E7:E%s)" % (row - 1)
        # ws6.cell(row, 6).value = "=SUM(F7:F%s)" % (row - 1)
        # ws6.cell(row, 7).value = "=SUM(G7:G%s)" % (row - 1)

        # ghi du lieu vao staff list

        # ghi du lieu vao file excel
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Chỉ số hài lòng của khách hàng theo dự án.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }


