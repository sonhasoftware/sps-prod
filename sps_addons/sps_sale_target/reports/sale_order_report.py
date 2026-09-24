from io import BytesIO
from os.path import abspath, dirname, join
from odoo import fields, models

STYLES = {
    "header_1": {"font_name": "Arial", "font_size": 24, "bold": True, "align": "center", "valign": "vcenter"},
    "header_2": {"font_name": "Arial", "font_size": 16, "italic": True, "align": "center", "valign": "vcenter"},
    "header_3": {"font_name": "Arial", "font_size": 24, "bold": True, "align": "left", "valign": "vcenter", 'italic': True},

    # Use for Est
    "header_4": {"font_name": "Times New Roman", "font_size": 15, "bold": True, "align": "left"},
    "header_5": {"font_name": "Times New Roman", "font_size": 11, "underline": True, "align": "left"},

    "doc_bold_10": {"font_name": "Arial", "font_size": 10, "bold": True, "valign": "vcenter", 'text_wrap': True},
    "doc_bold_10_border": {"font_name": "Arial", "font_size": 10, "bold": True, "border": 1, "valign": "vcenter", 'text_wrap': True},
    "doc_bold_10_border_center": {"font_name": "Arial", "font_size": 10, "bold": True, "border": 1, "align": "center", "valign": "vcenter", 'text_wrap': True},
    "doc_bold_10_border_center_money": {"font_name": "Arial", "font_size": 10, "bold": True, "border": 1, "align": "center", "valign": "vcenter", 'text_wrap': True, 'num_format': '#,##0'},
    "doc_bold_10_border_center_percent": {"font_name": "Arial", "font_size": 10, "bold": True, "border": 1, "align": "center", "valign": "vcenter", 'text_wrap': True, 'num_format': '#,##0.00'},
    "doc_bold_10_border_right": {"font_name": "Arial", "font_size": 10, "bold": True, "border": 1, "align": "right", "valign": "vcenter", 'text_wrap': True},
    "doc_bold_11": {"font_name": "Arial", "font_size": 11, "bold": True, "valign": "vcenter", 'text_wrap': True},
    "doc_bold_12_right": {"font_name": "Arial", "font_size": 12, "bold": True, "valign": "vcenter", 'align': 'right', 'text_wrap': True},
    "doc_normal_10": {"font_name": "Arial", "font_size": 10, "align": "left", "valign": "vcenter", 'text_wrap': True},
    "doc_normal_10_center": {"font_name": "Arial", "font_size": 10, "align": "center", "valign": "vcenter", 'text_wrap': True},
    "doc_normal_10_border": {"font_name": "Arial", "font_size": 10, "align": "left", "valign": "vcenter", 'border': 1, 'text_wrap': True},
    "doc_normal_10_border_center": {"font_name": "Arial", "font_size": 10, "border": 1, "align": "center", "valign": "vcenter", 'text_wrap': True},
    "doc_normal_10_border_center_money": {"font_name": "Arial", "font_size": 10, "border": 1, "align": "center", "valign": "vcenter", 'text_wrap': True, 'num_format': '#,##0'},
    "doc_normal_10_border_center_percent": {"font_name": "Arial", "font_size": 10, "border": 1, "align": "center", "valign": "vcenter", 'text_wrap': True, 'num_format': '#,##0.00'},
    "doc_normal_10_border_right": {"font_name": "Arial", "font_size": 10, "border": 1, "align": "right", "valign": "vcenter", 'text_wrap': True},
    "doc_normal_11_right": {"font_name": "Arial", "font_size": 11, "valign": "vcenter", 'align': 'right', 'text_wrap': True},
    'doc_normal_12': {'font_name': 'Arial', 'font_size': 12, 'valign': 'vcenter', 'align': 'center', 'text_wrap': True},
    'doc_normal_12_left': {'font_name': 'Arial', 'font_size': 12, 'valign': 'vcenter', 'align': 'left', 'text_wrap': True},
    'doc_normal_12_bottom': {'font_name': 'Arial', 'font_size': 12, 'valign': 'vcenter', 'align': 'center', 'bottom': 1, 'text_wrap': True},
    'doc_normal_12_bottom_left': {'font_name': 'Arial', 'font_size': 12, 'valign': 'vcenter', 'align': 'left', 'bottom': 1, 'text_wrap': True},
    'doc_normal_12_bottom_money': {'font_name': 'Arial', 'font_size': 12, 'valign': 'vcenter', 'align': 'center', 'bottom': 1, 'text_wrap': True, 'num_format': '#,##0'},
    "doc_italic_10_center": {"font_name": "Arial", 'italic': True, "font_size": 10, "align": "center", "valign": "vcenter", 'text_wrap': True},

    "doc_blue_bold_10_center": {"font_name": "Arial", 'font_color': '#24b3e3', "bold": True, "font_size": 10, "align": "center", "valign": "vcenter", 'text_wrap': True},
}

def convert_roman_number(number: int) -> str:
    """
    Function to convert integer number into Roman numeral (edited by me)
    Source: https://www.geeksforgeeks.org/python-program-to-convert-integer-to-roman/
    Many thanks for these 2 guys:
        https://auth.geeksforgeeks.org/user/Kanchan_Ray/
        https://auth.geeksforgeeks.org/user/simmytarika5/
    Not all the heroes wear capes
    """
    num = [1, 4, 5, 9, 10, 40, 50, 90, 100, 400, 500, 900, 1000]
    sym = ["I", "IV", "V", "IX", "X", "XL", "L", "XC", "C", "CD", "D", "CM", "M"]
    i = 12
    res = ""
    while number:
        div = number // num[i]
        number %= num[i]
        res += sym[i] * div
        i -= 1
    return res

class SaleOrderReportXlsx(models.AbstractModel):
    _name = 'report.sps_sale_target.sale_order_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, obj):
        if data.get('report_type', '') not in ('boq', 'cover', 'est'):
            return None
        if data['report_type'] == 'boq':
            self.generate_xlsx_report_boq(workbook, data, obj)
        elif data['report_type'] == 'cover':
            self.generate_xlsx_report_cover(workbook, data, obj)
        if data['report_type'] == 'est':
            self.generate_xlsx_report_est(workbook, data, obj)

    def generate_xlsx_report_boq(self, workbook, data, obj):
        sheet = workbook.add_worksheet('BÁO GIÁ CHI TIẾT')
        # region ::SET ROW - SET COL::
        sheet.set_row(0, height=30)
        sheet.set_row(1, height=20)
        sheet.set_row(2, height=35)
        sheet.set_row(3, height=15)
        sheet.set_column('A:A', width=5)
        sheet.set_column('B:B', width=35)
        sheet.set_column('C:C', width=5)
        sheet.set_column('D:D', width=5)
        sheet.set_column('E:E', width=12)
        sheet.set_column('F:F', width=12)
        # endregion
        # region ::HEADER::
        doc_normal_10 = workbook.add_format(STYLES["doc_normal_10"])
        sheet.write('B1', 'BÁO GIÁ CHI TIẾT', workbook.add_format(STYLES["header_1"]))
        sheet.write('B2', 'QUOTATION IN DETAILS', workbook.add_format(STYLES["header_2"]))
        sheet.write('E1', 'Ref No.:', doc_normal_10)
        sheet.write('F1', obj.name, doc_normal_10)
        # endregion
        # region ::TABLE HEADER::
        doc_bold_10_border_center = workbook.add_format(STYLES["doc_bold_10_border_center"])
        doc_bold_10_border_center_money = workbook.add_format(STYLES["doc_bold_10_border_center_money"])
        doc_bold_10_border_center_percent = workbook.add_format(STYLES["doc_bold_10_border_center_percent"])
        sheet.write('A3', 'STT\nNo.', doc_bold_10_border_center)
        sheet.write('A4', '(2)', doc_bold_10_border_center)
        sheet.write('B3', 'Hạng mục\nItems', doc_bold_10_border_center)
        sheet.write('B4', '(3)', doc_bold_10_border_center)
        sheet.write('C3', 'Đ.vị\nUnit', doc_bold_10_border_center)
        sheet.write('C4', '(4)', doc_bold_10_border_center)
        sheet.write('D3', 'S.lg\nQ.ty', doc_bold_10_border_center)
        sheet.write('D4', '(5)', doc_bold_10_border_center)
        sheet.write('E3', 'Đơn giá\nUnit price (VND)', doc_bold_10_border_center)
        sheet.write('E4', '(6)', doc_bold_10_border_center)
        sheet.write('F3', 'Thành tiền\nAmount (VND)', doc_bold_10_border_center)
        sheet.write('F4', '(7)', doc_bold_10_border_center)
        # endregion
        # region ::DATA::
        doc_bold_10_border = workbook.add_format(STYLES["doc_bold_10_border"])
        doc_normal_10_border = workbook.add_format(STYLES["doc_normal_10_border"])
        doc_normal_10_border_center = workbook.add_format(STYLES["doc_normal_10_border_center"])
        doc_normal_10_border_center_money = workbook.add_format(STYLES["doc_normal_10_border_center_money"])
        doc_normal_10_border_center_percent = workbook.add_format(STYLES["doc_normal_10_border_center_percent"])
        row = 4
        (section_sq, line_sq, section_row, section_price_total) = (1, 1, 0, 0)
        for line in obj.order_line.sorted(lambda sol: sol.sequence):
            sheet.set_row(row, height=25)
            row += 1
            if line.display_type == 'line_section':
                if section_price_total > 0 and section_row > 0:
                    sheet.write(f'F{section_row}', section_price_total, doc_bold_10_border_center_money)
                section_row = row
                sheet.write(f'A{row}', convert_roman_number(section_sq), doc_bold_10_border_center)
                sheet.write(f'B{row}', line.name, doc_bold_10_border)
                sheet.write(f'C{row}', '', doc_bold_10_border)
                sheet.write(f'D{row}', '', doc_bold_10_border)
                sheet.write(f'E{row}', '', doc_bold_10_border)
                section_sq += 1
                line_sq = 1
                section_price_total = 0
            elif not line.display_type:
                sheet.write(f'A{row}', line_sq, doc_normal_10_border_center)
                sheet.write(f'B{row}', line.name, doc_normal_10_border)
                sheet.write(f'C{row}', line.product_uom.name, doc_normal_10_border_center)
                sheet.write(f'D{row}', line.product_uom_qty, doc_normal_10_border_center)
                sheet.write(f'E{row}', line.price_unit, doc_normal_10_border_center_money)
                sheet.write(f'F{row}', line.product_uom_qty * line.price_unit, doc_normal_10_border_center_money)
                line_sq += 1
                section_price_total += line.product_uom_qty * line.price_unit
        if section_price_total > 0:
            sheet.write(f'F{section_row}', section_price_total, doc_bold_10_border_center_money)
        row += 1
        sheet.set_row(row-1, height=30)
        sheet.write(f'A{row}', '', doc_bold_10_border)
        sheet.merge_range(f'B{row}:E{row}', 'Chi phí chung và chi phí quản lý/\nPreliminaries and management cost', doc_bold_10_border)
        sheet.write(f'F{row}', obj.x_gen_cost, doc_bold_10_border_center_money)
        row += 1
        sheet.write(f'A{row}', '', doc_bold_10_border)
        sheet.merge_range(f'B{row}:E{row}', 'Cộng (Sub-total)', doc_bold_10_border)
        sheet.write(f'F{row}', obj.amount_untaxed, doc_bold_10_border_center_money)
        row += 1
        sheet.write(f'A{row}', '', doc_bold_10_border)
        sheet.merge_range(f'B{row}:E{row}', 'Thuế GTGT (VAT 10%)', doc_bold_10_border)
        sheet.write(f'F{row}', obj.amount_tax, doc_bold_10_border_center_money)
        row += 1
        sheet.write(f'A{row}', '', doc_bold_10_border)
        sheet.merge_range(f'B{row}:E{row}', 'Tổng cộng (Total)', doc_bold_10_border)
        sheet.write(f'F{row}', obj.amount_total, doc_bold_10_border_center_money)
        # endregion
        # region ::FOOTER::
        sheet.set_row(row, height=25)
        row += 2
        sheet.merge_range(f'A{row}:F{row}', f'* Phạm vi công việc / Scope of works: {obj.work_scope and obj.work_scope or ""}', doc_normal_10)
        sheet.set_row(row, height=65)
        row += 1
        sheet.merge_range(f'A{row}:F{row}', f'* Ghi chú / Note: \n {obj.work_note and obj.work_note or ""}', doc_normal_10)
        # endregion

    def generate_xlsx_report_cover(self, workbook, data, obj):
        sheet = workbook.add_worksheet('QUOTATION')
        # region ::SET ROW - SET COL::
        sheet.set_row(0, height=25)
        for _ in range(1, 14):
            sheet.set_row(_, height=15)
        for _ in range(14, 17):
            sheet.set_row(_, height=25)
        for _ in range(17, 44):
            sheet.set_row(_, height=15)
        sheet.set_column('A:A', width=3)
        sheet.set_column('B:B', width=9)
        sheet.set_column('C:C', width=3)
        sheet.set_column('D:D', width=6)
        sheet.set_column('E:E', width=6)
        sheet.set_column('F:F', width=6)
        sheet.set_column('G:G', width=3)
        sheet.set_column('H:H', width=3)
        sheet.set_column('I:I', width=3)
        sheet.set_column('J:J', width=4)
        sheet.set_column('K:K', width=5)
        sheet.set_column('L:L', width=3)
        sheet.set_column('M:M', width=3)
        sheet.set_column('N:N', width=3)
        sheet.set_column('O:O', width=1)
        sheet.set_column('P:P', width=2)
        sheet.set_column('Q:Q', width=4)
        sheet.set_column('R:R', width=3)
        sheet.set_column('S:S', width=3)
        sheet.set_column('T:T', width=4)
        # endregion
        # region ::HEADER::
        module_loc = dirname(dirname(abspath(__file__)))
        img_path = join(module_loc, 'static/description/sps.png')
        logo = open(img_path, 'rb').read()
        sheet.insert_image('A1', img_path, {'image_data': BytesIO(logo), 'x_scale': 0.4, 'y_scale': 0.4})
        sheet.merge_range('F1:T1', self.env.company.name, workbook.add_format(STYLES['doc_bold_12_right']))
        sheet.merge_range('F2:T2', self.env.company.street, workbook.add_format(STYLES['doc_normal_11_right']))
        sheet.merge_range('F3:T3', f'{self.env.company.city}, {self.env.company.state_id.name}', workbook.add_format(STYLES['doc_normal_11_right']))
        sheet.merge_range('F4:T4', f'Hotline: {self.env.company.phone}/ Website: {self.env.company.website}', workbook.add_format(STYLES['doc_normal_11_right']))
        sheet.merge_range('A6:T7', 'QUOTATION', workbook.add_format(STYLES['header_3']))
        sheet.merge_range('A8:M8', f'Quotation No.: {obj.name}', workbook.add_format({'align': 'left', 'font_name': 'Arial', 'font_size': 11, 'valign': 'vcenter', 'top': 6, 'bottom': 1, 'text_wrap': True}))
        # sheet.merge_range('F8:M8', '', workbook.add_format({'top': 6, 'bottom': 1, 'text_wrap': True}))
        sheet.merge_range('N8:T8', f'Date: {obj.date_order.strftime("%d-%b-%Y")}', workbook.add_format({'align': 'right', 'font_name': 'Arial', 'font_size': 11, 'valign': 'vcenter', 'top': 6, 'bottom': 1, 'text_wrap': True}))
        # endregion
        # region ::DATA::
        doc_bold_11 = workbook.add_format(STYLES['doc_bold_11'])
        sheet.merge_range('A9:B9', 'Attn', doc_bold_11)
        sheet.write('C9', ':', doc_bold_11)
        sheet.merge_range('D9:T9', obj.request_partner_id and obj.request_partner_id.name or '', doc_bold_11)
        sheet.merge_range('A10:B10', 'Client', doc_bold_11)
        sheet.write('C10', ':', doc_bold_11)
        sheet.merge_range('D10:T10', obj.partner_id.name, doc_bold_11)
        sheet.merge_range('A11:B11', 'Project Name', doc_bold_11)
        sheet.write('C11', ':', doc_bold_11)
        sheet.merge_range('D11:T11', obj.work_content and obj.work_content or '', doc_bold_11)
        sheet.merge_range('A13:B13', 'Location', doc_bold_11)
        sheet.write('C13', ':', doc_bold_11)
        sheet.merge_range('D13:T13', obj.location_partner_id and obj.location_partner_id.contact_address or '', doc_bold_11)
        sheet.merge_range('A14:T14', '', workbook.add_format({'bottom': 1, 'text_wrap': True}))
        doc_normal_12_bottom = workbook.add_format(STYLES['doc_normal_12_bottom'])
        doc_normal_12_left = workbook.add_format(STYLES['doc_normal_12_left'])
        doc_normal_12_bottom_left = workbook.add_format(STYLES['doc_normal_12_bottom_left'])
        doc_normal_12_bottom_money = workbook.add_format(STYLES['doc_normal_12_bottom_money'])
        sheet.merge_range('C15:E15', 'Direct Amount', doc_normal_12_bottom)
        sheet.write('F15', '', doc_normal_12_bottom)
        sheet.merge_range('G15:K15', obj.amount_untaxed, doc_normal_12_bottom_money)
        sheet.write('L15', '', doc_normal_12_bottom)
        sheet.merge_range('M15:Q15', obj.currency_id.name, doc_normal_12_bottom)
        sheet.merge_range('C16:E16', 'V.A.T 10%', doc_normal_12_bottom)
        sheet.write('F16', '', doc_normal_12_bottom)
        sheet.merge_range('G16:K16', obj.amount_tax, doc_normal_12_bottom_money)
        sheet.write('L16', '', doc_normal_12_bottom)
        sheet.merge_range('M16:Q16', obj.currency_id.name, doc_normal_12_bottom)
        sheet.merge_range('A17:B17', '', doc_normal_12_bottom)
        sheet.merge_range('C17:E17', 'Total Amount', doc_normal_12_bottom)
        sheet.write('F17', '', doc_normal_12_bottom)
        sheet.merge_range('G17:K17', obj.amount_total, doc_normal_12_bottom_money)
        sheet.write('L17', '', doc_normal_12_bottom)
        sheet.merge_range('M17:Q17', obj.currency_id.name, doc_normal_12_bottom)
        sheet.merge_range('R17:T17', '', doc_normal_12_bottom)
        sheet.merge_range('E19:T19', f'{obj.prepare_time} {"ngày" if obj.prepare_time_unit == "day" else "tháng" if obj.prepare_time_unit == "month" else "năm"} sau khi ký hợp đồng', doc_normal_12_left)
        sheet.merge_range('A20:C20', 'Delivery time', doc_normal_12_bottom)
        sheet.write('D20', ':', doc_normal_12_bottom)
        sheet.merge_range('E20:T20', f'{obj.prepare_time} {obj.prepare_time_unit if obj.prepare_time < 2 else obj.prepare_time_unit + "s"} after contract signed', doc_normal_12_bottom_left)
        sheet.merge_range('E22:T22', f'{obj.work_time} {"ngày" if obj.work_time_unit == "day" else "tháng" if obj.work_time_unit == "month" else "năm"}', doc_normal_12_left)
        sheet.merge_range('A23:C23', 'Completion Date', doc_normal_12_bottom)
        sheet.write('D23', ':', doc_normal_12_bottom)
        sheet.merge_range('E23:T23', f'{obj.work_time} {obj.work_time_unit if obj.work_time < 2 else obj.work_time_unit + "s"}', doc_normal_12_bottom_left)
        sheet.merge_range('A25:C28', 'Term of Payment', doc_normal_12_bottom)
        sheet.merge_range('D25:D28', ':', doc_normal_12_bottom)
        sheet.merge_range('E25:T28', obj.payment_term_id.name if obj.payment_term_id else '', doc_normal_12_bottom_left)
        sheet.merge_range('A30:C31', 'Validity period', doc_normal_12_bottom)
        sheet.merge_range('D30:D31', ':', doc_normal_12_bottom)
        sheet.merge_range('E30:T30', f'Báo giá có hiệu lực đến {obj.validity_date and obj.validity_date.strftime("%d/%m/%Y") or ""}', doc_normal_12_left)
        sheet.merge_range('E31:T31', f'This offer is valid until {obj.validity_date and obj.validity_date.strftime("%d %B %Y") or ""}', doc_normal_12_bottom_left)
        sheet.merge_range('A33:C34', 'Remarks', doc_normal_12_bottom)
        sheet.merge_range('D33:D34', ':', doc_normal_12_bottom)
        sheet.merge_range('E33:T34', obj.order_note and obj.order_note or '', doc_normal_12_bottom_left)
        # endregion
        # region ::FOOTER::
        sheet.merge_range('B37:F37', 'REPRESENTATIVES OF SPS', workbook.add_format(STYLES['doc_normal_10_center']))
        sheet.merge_range('B43:F43', 'General Director', workbook.add_format(STYLES['doc_italic_10_center']))
        sheet.merge_range('B44:F44', 'HOANG VAN PHONG', workbook.add_format(STYLES['doc_normal_10_center']))
        sheet.merge_range('M37:S37', 'CONFIRMED BY CLIENT', workbook.add_format(STYLES['doc_normal_10_center']))
        sheet.merge_range('M43:S43', 'Authorized Signature & Stamp', workbook.add_format(STYLES['doc_italic_10_center']))
        # endregion

    def generate_xlsx_report_est(self, workbook, data, obj):
        sheet = workbook.add_worksheet('BÁO GIÁ CHI TIẾT')
        # sheet.set_row(0, height=30)
        # sheet.set_row(1, height=20)
        # sheet.set_row(2, height=35)
        # sheet.set_row(3, height=15)
        sheet.set_column('A:A', width=3)
        sheet.set_column('B:B', width=38)
        sheet.set_column('C:C', width=10)
        sheet.set_column('D:D', width=10)
        sheet.set_column('E:E', width=10)
        sheet.merge_range('A1:D1', 'DỰ TOÁN / ESTIMATION', workbook.add_format(STYLES['header_4']))

        doc_bold_10_border = workbook.add_format(STYLES["doc_bold_10_border"])
        doc_bold_10_border_center = workbook.add_format(STYLES["doc_bold_10_border_center"])
        doc_normal_10_border_center = workbook.add_format({"font_name": "Arial", "font_size": 10, "align": "center", "valign": "vcenter", 'text_wrap': True})
        doc_normal_10_border_left = workbook.add_format({"font_name": "Arial", "font_size": 10, "align": "left", "valign": "vcenter", 'text_wrap': True})
        doc_normal_10_border_right = workbook.add_format({"font_name": "Arial", "font_size": 10, "align": "right", "valign": "vcenter", 'text_wrap': True})

        row = 2
        items_estimate = {}
        items_quote = {}
        last_quote_line_id = False
        count_line = len(obj.sale_estimates_line_ids)

        def add_quote(line_id):
            product_id = line_id.product_id
            if product_id.categ_id not in items_quote:
                items_quote[product_id.categ_id] = []
            items_quote[product_id.categ_id].append(line_id)

        def add_estimate(quote_line_id, line_id):
            product_id = line_id.product_id
            quote_product_id = quote_line_id.product_id
            if quote_product_id not in items_estimate:
                items_estimate[quote_product_id] = {}
            if product_id.categ_id not in items_estimate[quote_product_id]:
                items_estimate[quote_product_id][product_id.categ_id] = []
            items_estimate[quote_product_id][product_id.categ_id].append(line_id)

        i = 0
        has_child = False
        for line in obj.sale_estimates_line_ids.sorted(lambda el: el.sequence):
            i += 1
            if line.order_line_id and not last_quote_line_id:
                last_quote_line_id = line
            # Last line
            if i == count_line:
                if line.order_line_id:
                    if not has_child:
                        add_quote(last_quote_line_id)
                else:
                    add_estimate(last_quote_line_id, line)
                    has_child = True
                continue

            if i == 1:
                continue

            if last_quote_line_id:
                if line.order_line_id:
                    if not has_child:
                        add_quote(last_quote_line_id)
                    has_child = False
                else:
                    add_estimate(last_quote_line_id, line)
                    has_child = True

            if line.order_line_id:
                last_quote_line_id = line

        for quote_product_id in items_estimate:
            row += 1
            sheet.write(f'B{row}', 'HẠNG MỤC:', workbook.add_format(STYLES["header_5"]))
            row += 1
            sheet.merge_range(f'A{row}:D{row}', quote_product_id.name, workbook.add_format(STYLES['doc_blue_bold_10_center']))
            row += 1
            sheet.write(f'A{row}', 'No', doc_bold_10_border_center)
            sheet.write(f'B{row}', 'Hạng mục\nItem', doc_bold_10_border_center)
            sheet.write(f'C{row}', 'Đơn vị\nUnit', doc_bold_10_border_center)
            sheet.write(f'D{row}', 'Số lượng\nQty', doc_bold_10_border_center)

            roman_sec = 0
            for categ_id in items_estimate[quote_product_id]:
                row += 1
                roman_sec += 1
                sheet.write(f'A{row}', convert_roman_number(roman_sec), doc_bold_10_border_center)
                sheet.write(f'B{row}', categ_id.name, doc_bold_10_border_center)
                sheet.write(f'C{row}', '', doc_bold_10_border)
                sheet.write(f'D{row}', '', doc_bold_10_border)
                line_sec = 0
                for line in items_estimate[quote_product_id][categ_id]:
                    row += 1
                    line_sec += 1
                    sheet.write(f'A{row}', line_sec, doc_normal_10_border_center)
                    sheet.write(f'B{row}', line.product_id.name, doc_normal_10_border_left)
                    sheet.write(f'C{row}', line.uom_id.name, doc_normal_10_border_left)
                    sheet.write(f'D{row}', line.qty, doc_normal_10_border_right)

        # Others
        row += 1
        sheet.write(f'B{row}', 'HẠNG MỤC:', workbook.add_format(STYLES["header_5"]))
        row += 1
        sheet.merge_range(f'A{row}:D{row}', 'Khác', workbook.add_format(STYLES['doc_blue_bold_10_center']))
        row += 1
        sheet.write(f'A{row}', 'No', doc_bold_10_border_center)
        sheet.write(f'B{row}', 'Hạng mục\nItem', doc_bold_10_border_center)
        sheet.write(f'C{row}', 'Đơn vị\nUnit', doc_bold_10_border_center)
        sheet.write(f'D{row}', 'Số lượng\nQty', doc_bold_10_border_center)

        roman_sec = 0
        for categ_id in items_quote:
            row += 1
            roman_sec += 1
            sheet.write(f'A{row}', convert_roman_number(roman_sec), doc_bold_10_border_center)
            sheet.write(f'B{row}', categ_id.name, doc_bold_10_border_center)
            sheet.write(f'C{row}', '', doc_bold_10_border)
            sheet.write(f'D{row}', '', doc_bold_10_border)
            line_sec = 0
            for line in items_quote[categ_id]:
                row += 1
                line_sec += 1
                sheet.write(f'A{row}', line_sec, doc_normal_10_border_center)
                sheet.write(f'B{row}', line.product_id.name, doc_normal_10_border_left)
                sheet.write(f'C{row}', line.uom_id.name, doc_normal_10_border_left)
                sheet.write(f'D{row}', line.qty, doc_normal_10_border_right)
