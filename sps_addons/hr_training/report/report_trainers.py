import os
from io import BytesIO
from collections import OrderedDict
from datetime import datetime, timedelta

import openpyxl
from dateutil.relativedelta import relativedelta
from openpyxl.styles import Alignment, Border, Font, Side
from reportlab import xrange

from odoo import api, fields, models, tools
from odoo.http import Response, content_disposition
from odoo.modules import get_module_path

class ReportTrainers(models.Model):
    _name = 'report.trainers'
    _auto = False
    _description = 'report trainner'

    trainer = fields.Char()
    m1 = fields.Integer()
    m2 = fields.Integer()
    m3 = fields.Integer()
    m4 = fields.Integer()
    m5 = fields.Integer()
    m6 = fields.Integer()
    m7 = fields.Integer()
    m8 = fields.Integer()
    m9 = fields.Integer()
    m10 = fields.Integer()
    m11 = fields.Integer()
    m12 = fields.Integer()
    total = fields.Integer(compute='_compute_total')
    ratio = fields.Char(compute='_compute_ratio')
    result = fields.Integer()
    result_total = fields.Integer()

    def _compute_ratio(self):
        for item in self:
            item.ratio = '{}%'.format(round((item.result/item.result_total)*100 if item.result_total > 0 else 0, 2))

    def _compute_total(self):
        for i in self:
            i.total = i.m1 + i.m2 + i.m3 + i.m4 + i.m5 + i.m6 + i.m7 + i.m8 + i.m9 + i.m10 + i.m11 + i.m12


    def _get_selected_year(self, year=None):
        ctx_year = year or self.env.context.get('year')
        if ctx_year:
            try:
                return int(ctx_year)
            except (TypeError, ValueError):
                pass
        return fields.Date.context_today(self).year

    def _prepare_value_month(self):
        vals = {}
        year = self._get_selected_year()
        for index in range(12):
            dt_value = datetime(year, index + 1, 1)
            vals[f'm{index + 1}'] = dt_value.strftime(r"%b-%y")
        return vals

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        label = self._prepare_value_month()
        res = super(ReportTrainers, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                          submenu=submenu)
        if view_type == 'tree':
            fields = res.get('fields')
            if fields:
                res['fields']['m1']['string'] = label['m1']
                res['fields']['m2']['string'] = label['m2']
                res['fields']['m3']['string'] = label['m3']
                res['fields']['m4']['string'] = label['m4']
                res['fields']['m5']['string'] = label['m5']
                res['fields']['m6']['string'] = label['m6']
                res['fields']['m7']['string'] = label['m7']
                res['fields']['m8']['string'] = label['m8']
                res['fields']['m9']['string'] = label['m9']
                res['fields']['m10']['string'] = label['m10']
                res['fields']['m11']['string'] = label['m11']
                res['fields']['m12']['string'] = label['m12']
        return res

    # @api.model
    # def init(self):
    #     self._create_or_replace_view()


    def _get_time_report(self, year=None):
        selected_year = self._get_selected_year(year)
        vals = {}
        for i in range(1, 13):
            vals[f'm{i}'] = datetime(selected_year, i, 1)
        return vals

    @api.model
    def _create_or_replace_view(self, year=None):
        time = self._get_time_report(year)
        """ Event Question main report """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute(""" CREATE VIEW {table} AS (
                    select
                        row_number() OVER () AS id
                        , trainer
                        , sum(m1) as m1
                        , sum(m2) as m2
                        , sum(m3) as m3
                        , sum(m4) as m4
                        , sum(m5) as m5
                        , sum(m6) as m6
                        , sum(m7) as m7
                        , sum(m8) as m8
                        , sum(m9) as m9
                        , sum(m10) as m10
                        , sum(m11) as m11
                        , sum(m12) as m12
                        , sum(result) as result
                        , sum(result_total) as result_total
                    from (
                        select
                            trainer
                            , sum(m1) as m1
                            , sum(m2) as m2
                            , sum(m3) as m3
                            , sum(m4) as m4
                            , sum(m5) as m5
                            , sum(m6) as m6
                            , sum(m7) as m7
                            , sum(m8) as m8
                            , sum(m9) as m9
                            , sum(m10) as m10
                            , sum(m11) as m11
                            , sum(m12) as m12
                            , sum(result) as result
                            , sum(result_total) as result_total
                        from (
                            select
                                t3.name as trainer
                                , count(case when (extract(month from t1.date) = {m1}) and (extract(year from t1.date) = {y1}) then t2.id end)
                                as m1
                                , count(case when (extract(month from t1.date) = {m2}) and (extract(year from t1.date) = {y2}) then t2.id end)
                                as m2
                                , count(case when (extract(month from t1.date) = {m3}) and (extract(year from t1.date) = {y3}) then t2.id end)
                                as m3
                                , count(case when (extract(month from t1.date) = {m4}) and (extract(year from t1.date) = {y4}) then t2.id end)
                                as m4
                                , count(case when (extract(month from t1.date) = {m5}) and (extract(year from t1.date) = {y5}) then t2.id end)
                                as m5
                                , count(case when (extract(month from t1.date) = {m6}) and (extract(year from t1.date) = {y6}) then t2.id end)
                                as m6
                                , count(case when (extract(month from t1.date) = {m7}) and (extract(year from t1.date) = {y7}) then t2.id end)
                                as m7
                                , count(case when (extract(month from t1.date) = {m8}) and (extract(year from t1.date) = {y8}) then t2.id end)
                                as m8
                                , count(case when (extract(month from t1.date) = {m9}) and (extract(year from t1.date) = {y9}) then t2.id end)
                                as m9
                                , count(case when (extract(month from t1.date) = {m10}) and (extract(year from t1.date) = {y10}) then t2.id end)
                                as m10
                                , count(case when (extract(month from t1.date) = {m11}) and (extract(year from t1.date) = {y11}) then t2.id end)
                                as m11
                                , count(case when (extract(month from t1.date) = {m12}) and (extract(year from t1.date) = {y12}) then t2.id end)
                                as m12
                                , sum(case 
                                        when CAST (t2.result AS INTEGER) >= 75
                                         and (
                                                ((extract(month from t1.date) = {m1}) and (extract(year from t1.date) = {y1}))
                                             or ((extract(month from t1.date) = {m2}) and (extract(year from t1.date) = {y2}))
                                             or ((extract(month from t1.date) = {m3}) and (extract(year from t1.date) = {y3}))
                                             or ((extract(month from t1.date) = {m4}) and (extract(year from t1.date) = {y4}))
                                             or ((extract(month from t1.date) = {m5}) and (extract(year from t1.date) = {y5}))
                                             or ((extract(month from t1.date) = {m6}) and (extract(year from t1.date) = {y6}))
                                             or ((extract(month from t1.date) = {m7}) and (extract(year from t1.date) = {y7}))
                                             or ((extract(month from t1.date) = {m8}) and (extract(year from t1.date) = {y8}))
                                             or ((extract(month from t1.date) = {m9}) and (extract(year from t1.date) = {y9}))
                                             or ((extract(month from t1.date) = {m10}) and (extract(year from t1.date) = {y10}))
                                             or ((extract(month from t1.date) = {m11}) and (extract(year from t1.date) = {y11}))
                                             or ((extract(month from t1.date) = {m12}) and (extract(year from t1.date) = {y12}))
                                         )
                                     then 1 else 0 end) as result
                                , count(
                                    case when 
                                            ((extract(month from t1.date) = {m1}) and (extract(year from t1.date) = {y1}))
                                         or ((extract(month from t1.date) = {m2}) and (extract(year from t1.date) = {y2}))
                                         or ((extract(month from t1.date) = {m3}) and (extract(year from t1.date) = {y3}))
                                         or ((extract(month from t1.date) = {m4}) and (extract(year from t1.date) = {y4}))
                                         or ((extract(month from t1.date) = {m5}) and (extract(year from t1.date) = {y5}))
                                         or ((extract(month from t1.date) = {m6}) and (extract(year from t1.date) = {y6}))
                                         or ((extract(month from t1.date) = {m7}) and (extract(year from t1.date) = {y7}))
                                         or ((extract(month from t1.date) = {m8}) and (extract(year from t1.date) = {y8}))
                                         or ((extract(month from t1.date) = {m9}) and (extract(year from t1.date) = {y9}))
                                         or ((extract(month from t1.date) = {m10}) and (extract(year from t1.date) = {y10}))
                                         or ((extract(month from t1.date) = {m11}) and (extract(year from t1.date) = {y11}))
                                         or ((extract(month from t1.date) = {m12}) and (extract(year from t1.date) = {y12}))
                                         then t2.id end
                                ) as result_total
                            from
                                hr_training_result t1
                            join hr_training_result_line as t2 ON t1.id = t2.master_id
                            join hr_employee as t3 ON t2.trainer_id = t3.id
                            where t3.active = true
                            group by t3.name
                            union all
                            select
                                t3.name as trainer
                                , 0 as m1, 0 as m2, 0 as m3, 0 as m4, 0 as m5, 0 as m6
                                , 0 as m7, 0 as m8, 0 as m9, 0 as m10, 0 as m11, 0 as m12
                                , 0 as result
                                , 0 as result_total
                            from hr_employee as t3
                            where t3.active = true
                        ) mt group by trainer
                    ) mt
                    group by mt.trainer
                    having sum(m1) + sum(m2) + sum(m3) + sum(m4) + sum(m5) + sum(m6) +
                           sum(m7) + sum(m8) + sum(m9) + sum(m10) + sum(m11) + sum(m12) > 0
                    )""".format(
            table=self._table,
            m1=time['m1'].month, y1=time['m1'].year,
            m2=time['m2'].month, y2=time['m2'].year,
            m3=time['m3'].month, y3=time['m3'].year,
            m4=time['m4'].month, y4=time['m4'].year,
            m5=time['m5'].month, y5=time['m5'].year,
            m6=time['m6'].month, y6=time['m6'].year,
            m7=time['m7'].month, y7=time['m7'].year,
            m8=time['m8'].month, y8=time['m8'].year,
            m9=time['m9'].month, y9=time['m9'].year,
            m10=time['m10'].month, y10=time['m10'].year,
            m11=time['m11'].month, y11=time['m11'].year,
            m12=time['m12'].month, y12=time['m12'].year
        ))

    def export_excel_report(self, domain, context):
        module_path = get_module_path('hr_training')
        template_path = os.path.join(module_path, 'report', 'templates', 'nguoi_dao_tao.xlsx')
        wb = openpyxl.load_workbook(template_path, data_only=False)
        ws = wb.active

        trainers = self.search(domain or [], order='trainer')

        # Update report date (cell P2) to today's date
        today_date = fields.Date.context_today(self)
        ws.cell(row=2, column=16, value=datetime.combine(today_date, datetime.min.time()))

        # Prepare styles
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin'),
        )
        center_alignment = Alignment(horizontal='center', vertical='center')
        left_alignment = Alignment(horizontal='left', vertical='center')
        verdana_font = Font(name='Verdana', size=11)
        verdana_bold = Font(name='Verdana', size=11, bold=True)
        number_format = '#,##0'

        # Fill month headers C3-N3
        month_labels = self._prepare_value_month()
        header_row = 3
        for idx in range(1, 13):
            col = idx + 2  # Column C starts at index 3
            ws.cell(row=header_row, column=col, value=month_labels.get(f'm{idx}', ''))
            ws.cell(row=header_row, column=col).font = verdana_font
            ws.cell(row=header_row, column=col).alignment = center_alignment
            ws.cell(row=header_row, column=col).border = thin_border
        # Ensure Total/Ratio headers use Verdana, with only column O bold
        total_header = ws.cell(row=header_row, column=15)
        total_header.font = verdana_bold
        total_header.alignment = center_alignment
        total_header.border = thin_border

        ratio_header = ws.cell(row=header_row, column=16)
        ratio_header.font = verdana_font
        ratio_header.alignment = center_alignment
        ratio_header.border = thin_border

        # Write detail rows starting from row 4
        start_row = 4
        for idx, record in enumerate(trainers, start=1):
            row = start_row + idx - 1

            # Column A: sequence
            cell = ws.cell(row=row, column=1, value=idx)
            cell.alignment = center_alignment
            cell.border = thin_border
            cell.font = verdana_font

            # Column B: trainer name
            cell = ws.cell(row=row, column=2, value=record.trainer or '')
            cell.alignment = left_alignment
            cell.border = thin_border
            cell.font = verdana_font

            # Columns C-N: monthly values
            for month_idx in range(1, 13):
                col = month_idx + 2
                value = getattr(record, f'm{month_idx}', 0) or 0
                cell = ws.cell(row=row, column=col, value=value)
                cell.alignment = center_alignment
                cell.border = thin_border
                cell.number_format = number_format
                cell.font = verdana_font

            # Column O: total
            cell = ws.cell(row=row, column=15, value=record.total or 0)
            cell.alignment = center_alignment
            cell.border = thin_border
            cell.number_format = number_format
            cell.font = verdana_bold

            # Column P: ratio (>=75%)
            cell = ws.cell(row=row, column=16, value=record.ratio or '0%')
            cell.alignment = center_alignment
            cell.border = thin_border
            cell.font = verdana_font

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f'Báo cáo người đào tạo {fields.Date.today()}.xlsx'
        response = Response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ],
        )
        return response
    #
    # def export_excel_report(self, domain, context):
    #     print('dsdsd')
    #     module_path = get_module_path('hr_training')
    #     excel_path = os.path.join(module_path, 'report', 'templates', 'report_training_monthly_template.xlsx')
    #     wb = openpyxl.load_workbook(excel_path, data_only=False)
    #     ws = wb.active  # Use active sheet (Sheet2)
