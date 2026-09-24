import datetime
from datetime import timedelta, date
import base64

import os
from io import BytesIO
import openpyxl
from lxml import etree
from openpyxl.utils import get_column_letter
from openpyxl.writer.excel import save_virtual_workbook
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


PROJECT_TYPE_LABEL = {
    'service': 'Services',
    'maintainance': 'Maintenance',
    'operation': 'FM',
}


class ManpowerEfficiency(models.Model):
    _name = 'manpower.efficiency'
    _description = 'báo cáo hiệu quả nhân lực'

    year = fields.Selection([(str(x), str(x)) for x in range(2000, 2050)], 'Năm',
                            default=str(date.today().year))
    x_block_department = fields.Many2one('hr.department.block', string='Khối phòng ban', domain=[('id', '!=', 1)])

    def print_reports(self):
        block_id = self.x_block_department.id or None
        year = int(self.year) if self.year else date.today().year
        date_from = date(year, 1, 1)
        date_to = date(year, 12, 31)

        params = [date_from, date_to]
        block_filter = ''
        if block_id:
            block_filter = 'AND COALESCE(hist_hd.x_block_id, cur_hd.x_block_id) = %s'
            params.append(block_id)

        sql_lines = '''
            SELECT
                hwe.id AS entry_id,
                hwe.x_date AS x_date,
                he.name AS employee_name,
                he.x_code AS employee_code,
                hj.name AS job_name,
                COALESCE(hist_hd.name, cur_hd.name) AS department_name,
                pp.name AS project_name,
                pp.x_project_type AS project_type,
                COALESCE(hwel.hour, 0) AS line_hour
            FROM hr_work_entry hwe
            INNER JOIN hr_work_entry_line hwel ON hwel.entry_id = hwe.id
            LEFT JOIN project_project pp ON pp.id = hwel.project_id
            INNER JOIN hr_employee he ON he.id = hwe.employee_id
            LEFT JOIN hr_job hj ON hj.id = he.job_id
            LEFT JOIN hr_department cur_hd ON cur_hd.id = he.department_id
            LEFT JOIN LATERAL (
                SELECT hd.name AS name, hd.x_block_id AS x_block_id
                FROM hr_history_job hhj
                INNER JOIN hr_contract hc ON hc.id = hhj.contract_id
                INNER JOIN hr_department hd ON hd.id = hc.department_id
                WHERE hhj.employee_id = hwe.employee_id
                  AND hc.date_start <= hwe.x_date
                  AND (hc.date_end IS NULL OR hc.date_end >= hwe.x_date)
                ORDER BY hc.date_start DESC
                LIMIT 1
            ) hist_hd ON TRUE
            WHERE hwe.x_date BETWEEN %s AND %s
              AND COALESCE(hist_hd.x_block_id, cur_hd.x_block_id) != 1
              {block_filter}
            ORDER BY hwe.x_date, he.name, hwe.id, hwel.id
        '''.format(block_filter=block_filter)

        sql_allowances = '''
            SELECT
                hwe.id AS entry_id,
                hwe.x_date AS x_date,
                he.name AS employee_name,
                he.x_code AS employee_code,
                hj.name AS job_name,
                COALESCE(hist_hd.name, cur_hd.name) AS department_name,
                pp.name AS project_name,
                pp.x_project_type AS project_type,
                COALESCE(hwea.hour, 0) AS allowance_hour
            FROM hr_work_entry hwe
            INNER JOIN hr_work_entry_allowance hwea ON hwea.entry_id = hwe.id
            LEFT JOIN project_project pp ON pp.id = hwea.project_id
            INNER JOIN hr_employee he ON he.id = hwe.employee_id
            LEFT JOIN hr_job hj ON hj.id = he.job_id
            LEFT JOIN hr_department cur_hd ON cur_hd.id = he.department_id
            LEFT JOIN LATERAL (
                SELECT hd.name AS name, hd.x_block_id AS x_block_id
                FROM hr_history_job hhj
                INNER JOIN hr_contract hc ON hc.id = hhj.contract_id
                INNER JOIN hr_department hd ON hd.id = hc.department_id
                WHERE hhj.employee_id = hwe.employee_id
                  AND hc.date_start <= hwe.x_date
                  AND (hc.date_end IS NULL OR hc.date_end >= hwe.x_date)
                ORDER BY hc.date_start DESC
                LIMIT 1
            ) hist_hd ON TRUE
            WHERE hwe.x_date BETWEEN %s AND %s
              AND COALESCE(hist_hd.x_block_id, cur_hd.x_block_id) != 1
              {block_filter}
            ORDER BY hwe.x_date, he.name, hwe.id, hwea.id
        '''.format(block_filter=block_filter)

        self._cr.execute(sql_lines, params)
        line_rows = self._cr.dictfetchall()
        self._cr.execute(sql_allowances, params)
        allowance_rows = self._cr.dictfetchall()

        rows = []
        for r in line_rows:
            rows.append({
                'x_date': r['x_date'],
                'employee_name': r['employee_name'] or '',
                'employee_code': r['employee_code'] or '',
                'job_name': r['job_name'] or '',
                'department_name': r['department_name'] or '',
                'project_name': r['project_name'] or '',
                'project_type': r['project_type'],
                'allowance_hour': 0.0,
                'line_hour': r['line_hour'] or 0.0,
            })
        for r in allowance_rows:
            rows.append({
                'x_date': r['x_date'],
                'employee_name': r['employee_name'] or '',
                'employee_code': r['employee_code'] or '',
                'job_name': r['job_name'] or '',
                'department_name': r['department_name'] or '',
                'project_name': r['project_name'] or '',
                'project_type': r['project_type'],
                'allowance_hour': r['allowance_hour'] or 0.0,
                'line_hour': 0.0,
            })
        rows.sort(key=lambda r: (
            r['x_date'] or date.min,
            r['employee_name'],
            r['project_name'],
        ))

        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(
            dir_path + '%s..%stemplates%sPRODUCTIVITY_REPORTS.xlsx' % (os.sep, os.sep, os.sep))
        ws = wb['Allocated']

        max_row = ws.max_row
        for r_idx in range(2, max_row + 1):
            for c_idx in range(1, 13):
                ws.cell(row=r_idx, column=c_idx).value = None

        for i, r in enumerate(rows):
            row_idx = i + 2
            project_name = r['project_name']
            if project_name:
                project_type_label = PROJECT_TYPE_LABEL.get(r['project_type'], 'Non Project')
            else:
                project_type_label = 'Non Project'
            total_hour = (r['allowance_hour'] or 0.0) + (r['line_hour'] or 0.0)
            ws.cell(row=row_idx, column=1).value = r['x_date']
            ws.cell(row=row_idx, column=2).value = r['x_date']
            ws.cell(row=row_idx, column=3).value = r['employee_name']
            ws.cell(row=row_idx, column=4).value = r['employee_name']
            ws.cell(row=row_idx, column=5).value = r['employee_code']
            ws.cell(row=row_idx, column=6).value = r['allowance_hour']
            ws.cell(row=row_idx, column=7).value = project_name
            ws.cell(row=row_idx, column=8).value = r['line_hour']
            ws.cell(row=row_idx, column=9).value = total_hour
            ws.cell(row=row_idx, column=10).value = project_type_label
            ws.cell(row=row_idx, column=11).value = r['job_name']
            ws.cell(row=row_idx, column=12).value = r['department_name']

        ws_e = wb['E(%)']
        ws_e.cell(row=3, column=6).value = year
        if self.x_block_department:
            ws_e.cell(row=1, column=6).value = 'BÁO CÁO HIỆU QUẢ NHÂN LỰC %s' % self.x_block_department.name.upper()

        last_row = max(len(rows) + 1, 2)
        category_by_row = {
            7: None,
            8: 'Services',
            9: 'Maintenance',
            10: 'FM',
            11: 'Non Project',
            12: 'Standby',
        }
        for e_row, category in category_by_row.items():
            for month in range(1, 13):
                col = month + 1
                col_letter = get_column_letter(col)
                if category is None:
                    formula = (
                        '=SUMPRODUCT((Allocated!$B$2:$B$%d>=%s$4)'
                        '*(Allocated!$B$2:$B$%d<=%s$5)'
                        '*Allocated!$I$2:$I$%d)'
                    ) % (last_row, col_letter, last_row, col_letter, last_row)
                else:
                    formula = (
                        '=SUMPRODUCT((Allocated!$B$2:$B$%d>=%s$4)'
                        '*(Allocated!$B$2:$B$%d<=%s$5)'
                        '*(Allocated!$J$2:$J$%d="%s")'
                        '*Allocated!$I$2:$I$%d)'
                    ) % (last_row, col_letter, last_row, col_letter, last_row, category, last_row)
                ws_e.cell(row=e_row, column=col).value = formula

        months_with_data = set()
        for r in rows:
            if r['x_date'] and ((r['line_hour'] or 0.0) + (r['allowance_hour'] or 0.0)) > 0:
                months_with_data.add(r['x_date'].month)
        for month in range(1, 13):
            col = month + 1
            col_letter = get_column_letter(col)
            if month in months_with_data:
                ws_e.cell(row=13, column=col).value = '=(%s8+%s9+%s10)/%s7' % (
                    col_letter, col_letter, col_letter, col_letter)
            else:
                ws_e.cell(row=13, column=col).value = None
        ws_e.cell(row=13, column=14).value = '=(N8+N9+N10)/N7' if months_with_data else None

        # ----- Sheet Estimation: phân bổ giờ công dự toán ra từng ngày -----
        # Nguồn lực -> cột (I..M) khớp header sheet Estimation.
        RESOURCE_COL = {
            'seniorengsub': 9,
            'engsub': 10,
            'teamleader': 11,
            'technician': 12,
            'internship': 13,
        }
        ws_est = wb['Estimation']
        # Xoá dữ liệu cũ (dữ liệu bắt đầu từ dòng 6, header dòng 1-5).
        for r_idx in range(6, ws_est.max_row + 1):
            for c_idx in range(1, 16):
                ws_est.cell(row=r_idx, column=c_idx).value = None
        est_rows = self.env['project.project'].sudo()._build_estimation_rows(year, block_id)
        for i, r in enumerate(est_rows):
            row_idx = i + 6
            ws_est.cell(row=row_idx, column=1).value = r['date']
            ws_est.cell(row=row_idx, column=2).value = '=WEEKNUM(A%d,2)' % row_idx
            ws_est.cell(row=row_idx, column=3).value = '=TEXT(WEEKDAY(A%d),"DDD")' % row_idx
            ws_est.cell(row=row_idx, column=4).value = r['client']
            ws_est.cell(row=row_idx, column=5).value = r['project_no']
            ws_est.cell(row=row_idx, column=6).value = r['project_name']
            ws_est.cell(row=row_idx, column=7).value = r['fre']
            ws_est.cell(row=row_idx, column=8).value = r['classify']
            for rt, col in RESOURCE_COL.items():
                ws_est.cell(row=row_idx, column=col).value = r['hours'].get(rt) or None

        stream = BytesIO(save_virtual_workbook(wb))
        # openpyxl không giữ được chart/logo -> ghép lại từ resource gốc.
        xls = self._inject_chart_drawings(stream.getvalue())

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo hiệu quả nhân lực.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/' + str(attachment_id.id) + '?download=true',
            'target': 'new',
        }

    # Sheet hiển thị -> số thứ tự part drawing gốc (drawing{n}.xml + chart{n}.xml
    # + image{n}.jpeg) trong templates/productivity_drawings.zip.
    # Báo cáo chỉ còn Estimation + E(%) + Allocated nên chỉ ghép chart cho E(%).
    _SHEET_DRAWING = {'E(%)': 1}

    def _inject_chart_drawings(self, xls_bytes):
        """Chèn lại chart + logo gốc vào file .xlsx do openpyxl ghi ra.

        openpyxl không round-trip được chart/ảnh nên template đã bị bỏ các phần
        này; ở đây ta ghép lại ở mức zip: copy các part drawing/chart/media gốc
        và vá worksheet (E(%)/M(M)/M(W)) + rels + [Content_Types].xml để tham
        chiếu tới chúng. Nếu thiếu resource thì trả về nguyên trạng."""
        import io
        import re
        import zipfile
        dir_path = os.path.dirname(os.path.realpath(__file__))
        draw_zip = os.path.join(dir_path, '..', 'templates', 'productivity_drawings.zip')
        if not os.path.exists(draw_zip):
            return xls_bytes
        src = zipfile.ZipFile(draw_zip)
        zin = zipfile.ZipFile(io.BytesIO(xls_bytes))
        names = set(zin.namelist())

        # Map tên sheet hiển thị -> part xl/worksheets/sheetN.xml
        wbxml = zin.read('xl/workbook.xml').decode('utf-8')
        wbrels = zin.read('xl/_rels/workbook.xml.rels').decode('utf-8')
        rid2tgt = {}
        for tag in re.findall(r'<Relationship\b[^>]*/>', wbrels):
            idm = re.search(r'Id="([^"]+)"', tag)
            tm = re.search(r'Target="([^"]+)"', tag)
            if idm and tm:
                rid2tgt[idm.group(1)] = tm.group(1)
        name2part = {}
        for tag in re.findall(r'<sheet\b[^>]*/>', wbxml):
            nm = re.search(r'name="([^"]+)"', tag)
            rid = re.search(r'r:id="([^"]+)"', tag)
            if nm and rid and rid.group(1) in rid2tgt:
                tgt = rid2tgt[rid.group(1)].lstrip('/')
                name2part[nm.group(1)] = tgt if tgt.startswith('xl/') else 'xl/' + tgt

        patched = {}
        ct_overrides = []
        after_tags = ['<legacyDrawing', '<legacyDrawingHF', '<picture', '<oleObjects',
                      '<controls', '<webPublishItems', '<tableParts', '<extLst']
        for sheet_name, dn in self._SHEET_DRAWING.items():
            part = name2part.get(sheet_name)
            if not part or part not in names:
                continue
            sheet_xml = zin.read(part).decode('utf-8')
            if '<drawing ' in sheet_xml:
                continue
            # openpyxl không khai báo xmlns:r trên <worksheet> khi sheet không
            # có tham chiếu quan hệ -> phải thêm để attribute r:id hợp lệ.
            root_end = sheet_xml.find('>')
            if 'xmlns:r=' not in sheet_xml[:root_end]:
                sheet_xml = sheet_xml.replace(
                    '<worksheet ',
                    '<worksheet xmlns:r="http://schemas.openxmlformats.org/'
                    'officeDocument/2006/relationships" ', 1)
            rels_part = re.sub(r'(xl/worksheets/)(sheet[^/]+\.xml)$',
                               r'\1_rels/\2.rels', part)
            if rels_part in names:
                rels_xml = zin.read(rels_part).decode('utf-8')
            else:
                rels_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                            '<Relationships xmlns="http://schemas.openxmlformats.org/'
                            'package/2006/relationships"></Relationships>')
            existing = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels_xml)]
            new_rid = 'rId%d' % ((max(existing) + 1) if existing else 1)
            rel = ('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships/drawing" '
                   'Target="../drawings/drawing%d.xml"/>') % (new_rid, dn)
            rels_xml = rels_xml.replace('</Relationships>', rel + '</Relationships>')
            # Chèn <drawing> trước phần tử đầu tiên phải đứng SAU nó (đúng schema).
            pos = len(sheet_xml)
            for t in after_tags:
                i = sheet_xml.find(t)
                if i != -1:
                    pos = min(pos, i)
            if pos == len(sheet_xml):
                pos = sheet_xml.rfind('</worksheet>')
            sheet_xml = sheet_xml[:pos] + ('<drawing r:id="%s"/>' % new_rid) + sheet_xml[pos:]
            patched[part] = sheet_xml.encode('utf-8')
            patched[rels_part] = rels_xml.encode('utf-8')
            ct_overrides.append(
                '<Override PartName="/xl/drawings/drawing%d.xml" ContentType='
                '"application/vnd.openxmlformats-officedocument.drawing+xml"/>' % dn)
            ct_overrides.append(
                '<Override PartName="/xl/charts/chart%d.xml" ContentType='
                '"application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>' % dn)

        if not patched:
            return xls_bytes

        ct = zin.read('[Content_Types].xml').decode('utf-8')
        if 'Extension="jpeg"' not in ct:
            ct = ct.replace('</Types>', '<Default Extension="jpeg" ContentType="image/jpeg"/></Types>')
        ct = ct.replace('</Types>', ''.join(ct_overrides) + '</Types>')
        patched['[Content_Types].xml'] = ct.encode('utf-8')

        out = io.BytesIO()
        written = set()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                zout.writestr(item, patched.get(item.filename, zin.read(item.filename)))
                written.add(item.filename)
            # Ghi các part MỚI (vd rels sheet vốn chưa có) chưa nằm trong zip gốc.
            for fn, data in patched.items():
                if fn not in written:
                    zout.writestr(fn, data)
            for p in src.namelist():
                zout.writestr(p, src.read(p))
        return out.getvalue()