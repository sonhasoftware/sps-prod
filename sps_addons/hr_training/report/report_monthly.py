import os
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Border, Side, Alignment
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import fields, api, models, tools
from odoo.modules import get_module_path
from odoo.http import Response, content_disposition

class ReportTrainingMonthlyLine(models.Model):
    _name = 'report.training.monthly.line'
    _auto = False
    _description = 'report monthly'

    group_type = fields.Selection([
        ('group_a', 'A. Number of times with Basic or Advanced training'),
        ('group_b', 'B. Number of times with different contents'),
        ('group_c', 'C. Number of training times by department')
    ], required=True, string='Group type')
    name = fields.Char()
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
    total = fields.Integer()
    ratio = fields.Char(compute='_compute_ratio')

    def _compute_ratio(self):
        total_a, total_b, total_c = [], [], []
        for item in self:
            if item.group_type == 'group_a':
                total_a.append(item.total)
            if item.group_type == 'group_b':
                total_b.append(item.total)
            if item.group_type == 'group_c':
                total_c.append(item.total)
        for item in self:
            if item.group_type == 'group_a':
                item.ratio = '{}%'.format(round((item.total/sum(total_a))*100 if sum(total_a) > 0 else 0, 2))
            if item.group_type == 'group_b':
                item.ratio = '{}%'.format(round((item.total/sum(total_b))*100 if sum(total_b) > 0 else 0, 2))
            if item.group_type == 'group_c':
                item.ratio = '{}%'.format(round((item.total/sum(total_c))*100 if sum(total_c) > 0 else 0, 2))

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
        res = super(ReportTrainingMonthlyLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
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

    def _get_time_report(self, year=None):
        selected_year = self._get_selected_year(year)
        vals = {}
        for i in range(1, 13):
            vals[f'm{i}'] = datetime(selected_year, i, 1)
        return vals

    @api.model
    def _create_or_replace_view(self, year=None):
        time = self._get_time_report(year)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute(""" CREATE VIEW {table} AS (
            select 
                row_number() OVER () AS id
                , group_type
                , name
                , count(m1) as m1 
                , count(m2) as m2 
                , count(m3) as m3
                , count(m4) as m4
                , count(m5) as m5
                , count(m6) as m6
                , count(m7) as m7
                , count(m8) as m8
                , count(m9) as m9
                , count(m10) as m10
                , count(m11) as m11
                , count(m12) as m12
                , (count(m1) + count(m2) + count(m3) + count(m4) + count(m5) + count(m6) + 
                   count(m7) + count(m8) + count(m9) + count(m10) + count(m11) + count(m12)) as total
            from (
                select
                    'group_a' as group_type
                    , 'Cơ bản' as name
                    , (case when (extract(month from t1.date) = {m1}) and (extract(year from t1.date) = {y1}) then t2.id end)
                    as m1
                    , (case when (extract(month from t1.date) = {m2}) and (extract(year from t1.date) = {y2}) then t2.id end)
                    as m2
                    , (case when (extract(month from t1.date) = {m3}) and (extract(year from t1.date) = {y3}) then t2.id end)
                    as m3
                    , (case when (extract(month from t1.date) = {m4}) and (extract(year from t1.date) = {y4}) then t2.id end)
                    as m4
                    , (case when (extract(month from t1.date) = {m5}) and (extract(year from t1.date) = {y5}) then t2.id end)
                    as m5
                    , (case when (extract(month from t1.date) = {m6}) and (extract(year from t1.date) = {y6}) then t2.id end)
                    as m6
                    , (case when (extract(month from t1.date) = {m7}) and (extract(year from t1.date) = {y7}) then t2.id end)
                    as m7
                    , (case when (extract(month from t1.date) = {m8}) and (extract(year from t1.date) = {y8}) then t2.id end)
                    as m8
                    , (case when (extract(month from t1.date) = {m9}) and (extract(year from t1.date) = {y9}) then t2.id end)
                    as m9
                    , (case when (extract(month from t1.date) = {m10}) and (extract(year from t1.date) = {y10}) then t2.id end)
                    as m10
                    , (case when (extract(month from t1.date) = {m11}) and (extract(year from t1.date) = {y11}) then t2.id end)
                    as m11
                    , (case when (extract(month from t1.date) = {m12}) and (extract(year from t1.date) = {y12}) then t2.id end)
                    as m12
                from hr_training_result t1 
                join (
                    select id, master_id from hr_training_result_line
                    where type = 'basic' group by id
                ) as t2 on t1.id = t2.master_id
                group by t1.id, t2.id

                union

                select
                    'group_a' as group_type
                    , 'Nâng cao' as name
                    , (case when (extract(month from t1.date) = {m1}) and (extract(year from t1.date) = {y1}) then t2.id end)
                    as m1
                    , (case when (extract(month from t1.date) = {m2}) and (extract(year from t1.date) = {y2}) then t2.id end)
                    as m2
                    , (case when (extract(month from t1.date) = {m3}) and (extract(year from t1.date) = {y3}) then t2.id end)
                    as m3
                    , (case when (extract(month from t1.date) = {m4}) and (extract(year from t1.date) = {y4}) then t2.id end)
                    as m4
                    , (case when (extract(month from t1.date) = {m5}) and (extract(year from t1.date) = {y5}) then t2.id end)
                    as m5
                    , (case when (extract(month from t1.date) = {m6}) and (extract(year from t1.date) = {y6}) then t2.id end)
                    as m6
                    , (case when (extract(month from t1.date) = {m7}) and (extract(year from t1.date) = {y7}) then t2.id end)
                    as m7
                    , (case when (extract(month from t1.date) = {m8}) and (extract(year from t1.date) = {y8}) then t2.id end)
                    as m8
                    , (case when (extract(month from t1.date) = {m9}) and (extract(year from t1.date) = {y9}) then t2.id end)
                    as m9
                    , (case when (extract(month from t1.date) = {m10}) and (extract(year from t1.date) = {y10}) then t2.id end)
                    as m10
                    , (case when (extract(month from t1.date) = {m11}) and (extract(year from t1.date) = {y11}) then t2.id end)
                    as m11
                    , (case when (extract(month from t1.date) = {m12}) and (extract(year from t1.date) = {y12}) then t2.id end)
                    as m12
                from hr_training_result t1 
                join (
                    select id, master_id from hr_training_result_line
                    where type = 'advance' group by id
                ) as t2 on t1.id = t2.master_id
                group by t1.id, t2.id

                union 

                select
                    'group_b' as group_type
                    , t2.name as name
                    , (case when (extract(month from t1.date) = {m1}) and (extract(year from t1.date) = {y1}) then t2.id end)
                    as m1
                    , (case when (extract(month from t1.date) = {m2}) and (extract(year from t1.date) = {y2}) then t2.id end)
                    as m2
                    , (case when (extract(month from t1.date) = {m3}) and (extract(year from t1.date) = {y3}) then t2.id end)
                    as m3
                    , (case when (extract(month from t1.date) = {m4}) and (extract(year from t1.date) = {y4}) then t2.id end)
                    as m4
                    , (case when (extract(month from t1.date) = {m5}) and (extract(year from t1.date) = {y5}) then t2.id end)
                    as m5
                    , (case when (extract(month from t1.date) = {m6}) and (extract(year from t1.date) = {y6}) then t2.id end)
                    as m6
                    , (case when (extract(month from t1.date) = {m7}) and (extract(year from t1.date) = {y7}) then t2.id end)
                    as m7
                    , (case when (extract(month from t1.date) = {m8}) and (extract(year from t1.date) = {y8}) then t2.id end)
                    as m8
                    , (case when (extract(month from t1.date) = {m9}) and (extract(year from t1.date) = {y9}) then t2.id end)
                    as m9
                    , (case when (extract(month from t1.date) = {m10}) and (extract(year from t1.date) = {y10}) then t2.id end)
                    as m10
                    , (case when (extract(month from t1.date) = {m11}) and (extract(year from t1.date) = {y11}) then t2.id end)
                    as m11
                    , (case when (extract(month from t1.date) = {m12}) and (extract(year from t1.date) = {y12}) then t2.id end)
                    as m12
                from hr_training_result t1 
                join (
                    select t2.id, t2.master_id, htc.name as name from hr_training_result_line t2
                    join hr_training_item hti on hti.id = t2.training_item_id 
                    join hr_training_categ htc on htc.id = hti.categ_id
                    group by t2.id, htc.name
                ) as t2 on t1.id = t2.master_id

                union 

                select
                    'group_c' as group_type
                    , t2.name as name
                    , (case when (extract(month from t1.date) = {m1}) and (extract(year from t1.date) = {y1}) then t2.id end)
                    as m1
                    , (case when (extract(month from t1.date) = {m2}) and (extract(year from t1.date) = {y2}) then t2.id end)
                    as m2
                    , (case when (extract(month from t1.date) = {m3}) and (extract(year from t1.date) = {y3}) then t2.id end)
                    as m3
                    , (case when (extract(month from t1.date) = {m4}) and (extract(year from t1.date) = {y4}) then t2.id end)
                    as m4
                    , (case when (extract(month from t1.date) = {m5}) and (extract(year from t1.date) = {y5}) then t2.id end)
                    as m5
                    , (case when (extract(month from t1.date) = {m6}) and (extract(year from t1.date) = {y6}) then t2.id end)
                    as m6
                    , (case when (extract(month from t1.date) = {m7}) and (extract(year from t1.date) = {y7}) then t2.id end)
                    as m7
                    , (case when (extract(month from t1.date) = {m8}) and (extract(year from t1.date) = {y8}) then t2.id end)
                    as m8
                    , (case when (extract(month from t1.date) = {m9}) and (extract(year from t1.date) = {y9}) then t2.id end)
                    as m9
                    , (case when (extract(month from t1.date) = {m10}) and (extract(year from t1.date) = {y10}) then t2.id end)
                    as m10
                    , (case when (extract(month from t1.date) = {m11}) and (extract(year from t1.date) = {y11}) then t2.id end)
                    as m11
                    , (case when (extract(month from t1.date) = {m12}) and (extract(year from t1.date) = {y12}) then t2.id end)
                    as m12
                from hr_training_result t1 
                join (
                    select t2.id, t2.master_id, hd.name as name from hr_training_result_line t2
                    join hr_employee he on he.id = t2.trainee_id
                    join hr_department hd on he.department_id = hd.id
                    group by t2.id, hd.name
                ) as t2 on t1.id = t2.master_id
                group by t1.id, t2.id, t2.name
            ) mt group by group_type, name
            HAVING (count(m1) + count(m2) + count(m3) + count(m4) + count(m5) + count(m6) + 
                    count(m7) + count(m8) + count(m9) + count(m10) + count(m11) + count(m12)) != 0
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

    # @api.model
    # def init(self):
    #     self._create_or_replace_view()

    def export_excel_report(self, domain, context):
        model = self.with_context(context or {})
        module_path = get_module_path('hr_training')
        excel_path = os.path.join(module_path, 'report', 'templates', 'report_training_monthly_template.xlsx')
        wb = openpyxl.load_workbook(excel_path, data_only=False)
        ws = wb.active  # Use active sheet (Sheet2)
        monthly_ids = model.search(domain, order='group_type, name')

        # Define styles
        center_alignment = Alignment(horizontal='center', vertical='center')
        left_alignment = Alignment(horizontal='left', vertical='center')
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        bold_font = Font(bold=True, size=11)
        normal_font = Font(size=11)
        number_format = '#,##0'

        # Get month labels
        label = model._prepare_value_month()

        # Write main header row (row 4) with month labels
        header_row = 4
        ws.cell(row=header_row, column=1, value='Phân loại')
        ws.cell(row=header_row, column=1).font = bold_font
        ws.cell(row=header_row, column=1).alignment = center_alignment
        ws.cell(row=header_row, column=1).border = thin_border

        for i in range(1, 13):
            col = i + 1
            ws.cell(row=header_row, column=col, value=label.get(f'm{i}', ''))
            ws.cell(row=header_row, column=col).font = bold_font
            ws.cell(row=header_row, column=col).alignment = center_alignment
            ws.cell(row=header_row, column=col).border = thin_border

        ws.cell(row=header_row, column=14, value='Tổng')
        ws.cell(row=header_row, column=14).font = bold_font
        ws.cell(row=header_row, column=14).alignment = center_alignment
        ws.cell(row=header_row, column=14).border = thin_border

        ws.cell(row=header_row, column=15, value='Tỷ lệ')
        ws.cell(row=header_row, column=15).font = bold_font
        ws.cell(row=header_row, column=15).alignment = center_alignment
        ws.cell(row=header_row, column=15).border = thin_border

        # Group records by group_type for calculating totals
        from collections import defaultdict
        group_data = defaultdict(list)
        for record in monthly_ids:
            group_data[record.group_type].append(record)

        # Start writing data from row 5
        current_row = 5
        group_labels = {
            'group_a': 'A. Số lượt đào tạo Cơ bản và Nâng cao',
            'group_b': 'B. Số lượt đào tạo với các nội dung khác nhau',
            'group_c': 'C. Số lượt đào tạo theo bộ phận'
        }

        for group_type in ['group_a', 'group_b', 'group_c']:
            if group_type not in group_data:
                continue

            records = group_data[group_type]

            # Calculate group totals for each month
            group_totals = {f'm{i}': 0 for i in range(1, 13)}
            group_total_all = 0

            for record in records:
                for i in range(1, 13):
                    group_totals[f'm{i}'] += getattr(record, f'm{i}', 0) or 0
                group_total_all += record.total or 0

            # Write group header row with totals
            ws.cell(row=current_row, column=1, value=group_labels.get(group_type, group_type))
            ws.cell(row=current_row, column=1).font = bold_font
            ws.cell(row=current_row, column=1).alignment = left_alignment
            ws.cell(row=current_row, column=1).border = thin_border

            # Write monthly totals for the group
            for i in range(1, 13):
                col = i + 1
                ws.cell(row=current_row, column=col, value=group_totals[f'm{i}'])
                ws.cell(row=current_row, column=col).font = bold_font
                ws.cell(row=current_row, column=col).alignment = center_alignment
                ws.cell(row=current_row, column=col).border = thin_border
                ws.cell(row=current_row, column=col).number_format = number_format

            # Total column for group
            ws.cell(row=current_row, column=14, value=group_total_all)
            ws.cell(row=current_row, column=14).font = bold_font
            ws.cell(row=current_row, column=14).alignment = center_alignment
            ws.cell(row=current_row, column=14).border = thin_border
            ws.cell(row=current_row, column=14).number_format = number_format

            # Ratio column for group (100%)
            ws.cell(row=current_row, column=15, value='100%')
            ws.cell(row=current_row, column=15).font = bold_font
            ws.cell(row=current_row, column=15).alignment = center_alignment
            ws.cell(row=current_row, column=15).border = thin_border

            current_row += 1

            # Write detail rows for each record in the group
            for record in records:
                # Column 1: Name (indented)
                ws.cell(row=current_row, column=1, value=f'  {record.name or ""}')
                ws.cell(row=current_row, column=1).alignment = left_alignment
                ws.cell(row=current_row, column=1).border = thin_border
                ws.cell(row=current_row, column=1).font = normal_font

                # Columns 2-13: Monthly data (m1-m12)
                for i in range(1, 13):
                    col = i + 1
                    value = getattr(record, f'm{i}', 0) or 0
                    ws.cell(row=current_row, column=col, value=value)
                    ws.cell(row=current_row, column=col).alignment = center_alignment
                    ws.cell(row=current_row, column=col).border = thin_border
                    ws.cell(row=current_row, column=col).number_format = number_format
                    ws.cell(row=current_row, column=col).font = normal_font

                # Column 14: Total
                ws.cell(row=current_row, column=14, value=record.total or 0)
                ws.cell(row=current_row, column=14).alignment = center_alignment
                ws.cell(row=current_row, column=14).border = thin_border
                ws.cell(row=current_row, column=14).number_format = number_format
                ws.cell(row=current_row, column=14).font = normal_font

                # Column 15: Ratio
                ws.cell(row=current_row, column=15, value=record.ratio or '0%')
                ws.cell(row=current_row, column=15).alignment = center_alignment
                ws.cell(row=current_row, column=15).border = thin_border
                ws.cell(row=current_row, column=15).font = normal_font

                current_row += 1

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Create filename with current year
        current = fields.Date.today()
        filename = f'Báo cáo đào tạo hàng tháng {current}.xlsx'

        # Return response
        response = Response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename))
            ]
        )

        return response
