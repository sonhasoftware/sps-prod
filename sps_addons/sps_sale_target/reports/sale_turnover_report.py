from io import BytesIO
from os.path import abspath, dirname, join
from odoo import fields, models

STYLES = {
    "header_1": {"font_name": "Times New Roman", "font_size": 18, "bold": True, "align": "center"},
    "header_2": {"font_name": "Times New Roman", "font_size": 14, "italic": True, "align": "center"},
    "doc_bold_14": {"font_name": "Times New Roman", "font_size": 11, "bold": True, 'text_wrap': True},
    "doc_bold_14_border": {"font_name": "Times New Roman", "font_size": 11, "bold": True, "border": 1, 'text_wrap': True},
    "doc_bold_14_border_center": {"font_name": "Times New Roman", "font_size": 11, "bold": True, "border": 1, "align": "center", 'text_wrap': True},
    "doc_bold_16_center": {"font_name": "Times New Roman", "font_size": 14, "bold": True, "align": "center", 'text_wrap': True},
    "doc_normal_12": {"font_name": "Times New Roman", "font_size": 11, "align": "left", 'text_wrap': True},
    "doc_normal_14": {"font_name": "Times New Roman", "font_size": 11, "align": "left", 'text_wrap': True},
    "doc_normal_14_border_center": {"font_name": "Times New Roman", "font_size": 11, 'border': 1, "align": "center", 'valign': 'vcenter', 'text_wrap': True},
    "doc_normal_14_border_center_money": {"font_name": "Times New Roman", "font_size": 11, "bold": True, "border": 1, "align": "center", 'text_wrap': True, 'num_format': '#,##0'},
    "doc_normal_14_border_center_percent": {"font_name": "Times New Roman", "font_size": 11, "bold": True, "border": 1, "align": "center", 'text_wrap': True, 'num_format': '#,##0.00'},
    "doc_normal_14_border": {"font_name": "Times New Roman", "font_size": 11, "align": "left", "border": 1, 'text_wrap': True},
    "doc_normal_16": {"font_name": "Times New Roman", "font_size": 11, "align": "left", 'text_wrap': True},
}

def process_report_data(report_data):
    # region ::PROCESS REPORT DATA FUNC::
    def dict_filter(dictlist, key, value):
        return list(filter(lambda x: x.get(key) == value, dictlist))
    month_1_data = dict_filter(report_data, 'month', 1)
    month_2_data = dict_filter(report_data, 'month', 2)
    month_3_data = dict_filter(report_data, 'month', 3)
    month_4_data = dict_filter(report_data, 'month', 4)
    month_5_data = dict_filter(report_data, 'month', 5)
    month_6_data = dict_filter(report_data, 'month', 6)
    month_7_data = dict_filter(report_data, 'month', 7)
    month_8_data = dict_filter(report_data, 'month', 8)
    month_9_data = dict_filter(report_data, 'month', 9)
    month_10_data = dict_filter(report_data, 'month', 10)
    month_11_data = dict_filter(report_data, 'month', 11)
    month_12_data = dict_filter(report_data, 'month', 12)

    month_1_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 1]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 1]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 1]) or 0
    month_2_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 2]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 2]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 2]) or 0
    month_3_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 3]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 3]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 3]) or 0
    month_4_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 4]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 4]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 4]) or 0
    month_5_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 5]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 5]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 5]) or 0
    month_6_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 6]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 6]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 6]) or 0
    month_7_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 7]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 7]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 7]) or 0
    month_8_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 8]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 8]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 8]) or 0
    month_9_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 9]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 9]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 9]) or 0
    month_10_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 10]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 10]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 10]) or 0
    month_11_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 11]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 11]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 11]) or 0
    month_12_cumulative_percentage_fail = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 12]) and sum([_["untaxed_failed"] for _ in report_data if _["month"] <= 12]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 12]) or 0

    month_1_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 1]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 1]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 1]) or 0
    month_2_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 2]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 2]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 2]) or 0
    month_3_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 3]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 3]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 3]) or 0
    month_4_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 4]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 4]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 4]) or 0
    month_5_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 5]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 5]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 5]) or 0
    month_6_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 6]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 6]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 6]) or 0
    month_7_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 7]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 7]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 7]) or 0
    month_8_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 8]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 8]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 8]) or 0
    month_9_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 9]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 9]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 9]) or 0
    month_10_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 10]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 10]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 10]) or 0
    month_11_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 11]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 11]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 11]) or 0
    month_12_cumulative_percentage_sign = sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 12]) and sum([_["untaxed_signed"] for _ in report_data if _["month"] <= 12]) * 100 / sum([_["untaxed_sent"] for _ in report_data if _["month"] <= 12]) or 0

    return (
        month_1_data,
        month_2_data,
        month_3_data,
        month_4_data,
        month_5_data,
        month_6_data,
        month_7_data,
        month_8_data,
        month_9_data,
        month_10_data,
        month_11_data,
        month_12_data,
        month_1_cumulative_percentage_fail,
        month_2_cumulative_percentage_fail,
        month_3_cumulative_percentage_fail,
        month_4_cumulative_percentage_fail,
        month_5_cumulative_percentage_fail,
        month_6_cumulative_percentage_fail,
        month_7_cumulative_percentage_fail,
        month_8_cumulative_percentage_fail,
        month_9_cumulative_percentage_fail,
        month_10_cumulative_percentage_fail,
        month_11_cumulative_percentage_fail,
        month_12_cumulative_percentage_fail,
        month_1_cumulative_percentage_sign,
        month_2_cumulative_percentage_sign,
        month_3_cumulative_percentage_sign,
        month_4_cumulative_percentage_sign,
        month_5_cumulative_percentage_sign,
        month_6_cumulative_percentage_sign,
        month_7_cumulative_percentage_sign,
        month_8_cumulative_percentage_sign,
        month_9_cumulative_percentage_sign,
        month_10_cumulative_percentage_sign,
        month_11_cumulative_percentage_sign,
        month_12_cumulative_percentage_sign,
    )
    # endregion

class SaleTurnOverReportXlsx(models.AbstractModel):
    _name = 'report.sps_sale_target.sale_turnover_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, partners):
        sheet = workbook.add_worksheet('BÁO CÁO DOANH SỐ ')
        # region ::SET ROW - SET COL::
        sheet.set_row(0, height=40)
        sheet.set_row(1, height=20)
        sheet.set_row(2, height=20)
        sheet.set_row(4, height=40)
        sheet.set_row(5, height=40)
        sheet.set_row(6, height=40)
        sheet.set_row(7, height=40)
        sheet.set_row(8, height=40)
        sheet.set_row(9, height=40)
        sheet.set_row(10, height=40)
        sheet.set_row(11, height=40)
        sheet.set_row(12, height=40)
        sheet.set_column('A:A', width=20)
        sheet.set_column('B:B', width=30)
        sheet.set_column('C:C', width=14)
        sheet.set_column('D:D', width=14)
        sheet.set_column('E:E', width=14)
        sheet.set_column('F:F', width=14)
        sheet.set_column('G:G', width=14)
        sheet.set_column('H:H', width=14)
        sheet.set_column('I:I', width=14)
        sheet.set_column('J:J', width=14)
        sheet.set_column('K:K', width=14)
        sheet.set_column('L:L', width=14)
        sheet.set_column('M:M', width=14)
        sheet.set_column('N:N', width=14)
        sheet.set_column('O:O', width=20)
        # endregion
        # region ::HEADER::
        sheet.write('H1', 'BÁO CÁO DOANH SỐ (KÝ MỚI)', workbook.add_format(STYLES['header_1']))
        sheet.write('H2', 'SALES TURNOVER REPORT (NEW ORDER)', workbook.add_format(STYLES['header_2']))
        sheet.write('G3', 'YEAR', workbook.add_format(STYLES['doc_normal_16']))
        sheet.write('H3', data['form_data'][0]['report_year'], workbook.add_format(STYLES['doc_bold_16_center']))
        sheet.write('N1', 'Prepared by:', workbook.add_format(STYLES['doc_normal_12']))
        sheet.write('N2', 'Updated on:', workbook.add_format(STYLES['doc_normal_12']))
        sheet.write('O1', self.env.user.name, workbook.add_format(STYLES['doc_normal_12']))
        sheet.write('O2', fields.Date.today().strftime('%d-%m-%Y'), workbook.add_format(STYLES['doc_normal_12']))
        # endregion
        # region ::TABLE HEADER::
        module_loc = dirname(dirname(abspath(__file__)))
        img_path = join(module_loc, 'static/description/sps.png')
        logo = open(img_path, 'rb').read()
        sheet.insert_image('A1', img_path, {'image_data': BytesIO(logo), 'x_scale': 0.2, 'y_scale': 0.2})
        sheet.write('A4', 'Item', workbook.add_format(STYLES['doc_bold_14_border']))
        sheet.write('B4', 'Month', workbook.add_format(STYLES['doc_bold_14_border']))
        doc_bold_14_border = workbook.add_format(STYLES['doc_bold_14_border'])
        doc_bold_14_border_center = workbook.add_format(STYLES['doc_bold_14_border_center'])
        doc_normal_14_border = workbook.add_format(STYLES['doc_normal_14_border'])
        sheet.write('C4', '1', doc_bold_14_border_center)
        sheet.write('D4', '2', doc_bold_14_border_center)
        sheet.write('E4', '3', doc_bold_14_border_center)
        sheet.write('F4', '4', doc_bold_14_border_center)
        sheet.write('G4', '5', doc_bold_14_border_center)
        sheet.write('H4', '6', doc_bold_14_border_center)
        sheet.write('I4', '7', doc_bold_14_border_center)
        sheet.write('J4', '8', doc_bold_14_border_center)
        sheet.write('K4', '9', doc_bold_14_border_center)
        sheet.write('L4', '10', doc_bold_14_border_center)
        sheet.write('M4', '11', doc_bold_14_border_center)
        sheet.write('N4', '12', doc_bold_14_border_center)
        sheet.write('O4', 'Total', doc_bold_14_border_center)
        sheet.merge_range('A5:B5', 'Tổng giá trị báo giá đã gửi\nTotal value of inquiries sent', doc_bold_14_border)
        sheet.merge_range('A6:B6', 'Giá trị báo giá trượt\nValue of inquiries failed', doc_bold_14_border)
        sheet.merge_range('A7:B7', 'Tỉ lệ lũy kế giá trị báo giá trượt\nPercentage of cumulative value of inquiries failed', doc_normal_14_border)
        sheet.merge_range('A8:B8', 'Giá trị báo giá đã ký\nValue of inquiries signed', doc_bold_14_border)
        sheet.merge_range('A9:B9', 'Tỉ lệ lũy kế giá trị báo giá được ký\nPercentage of cumulative value of inquiries signed', doc_normal_14_border)
        sheet.merge_range('A10:B10', 'Tổng doanh số mục tiêu\nTotal turnover target', doc_bold_14_border)
        sheet.merge_range('A11:B11', 'Giá trị báo giá quản lý vận hành đã ký\nValue of facility management inquiries signed', doc_bold_14_border)
        sheet.merge_range('A12:B12', 'Giá trị báo giá bảo trì & dịch vụ đã ký\nValue of maintenance & services inquiries signed', doc_bold_14_border)
        # endregion
        # region ::DATA::
        report_data = data['report_data']
        (
            month_1_data,
            month_2_data,
            month_3_data,
            month_4_data,
            month_5_data,
            month_6_data,
            month_7_data,
            month_8_data,
            month_9_data,
            month_10_data,
            month_11_data,
            month_12_data,
            month_1_cumulative_percentage_fail,
            month_2_cumulative_percentage_fail,
            month_3_cumulative_percentage_fail,
            month_4_cumulative_percentage_fail,
            month_5_cumulative_percentage_fail,
            month_6_cumulative_percentage_fail,
            month_7_cumulative_percentage_fail,
            month_8_cumulative_percentage_fail,
            month_9_cumulative_percentage_fail,
            month_10_cumulative_percentage_fail,
            month_11_cumulative_percentage_fail,
            month_12_cumulative_percentage_fail,
            month_1_cumulative_percentage_sign,
            month_2_cumulative_percentage_sign,
            month_3_cumulative_percentage_sign,
            month_4_cumulative_percentage_sign,
            month_5_cumulative_percentage_sign,
            month_6_cumulative_percentage_sign,
            month_7_cumulative_percentage_sign,
            month_8_cumulative_percentage_sign,
            month_9_cumulative_percentage_sign,
            month_10_cumulative_percentage_sign,
            month_11_cumulative_percentage_sign,
            month_12_cumulative_percentage_sign,
        ) = process_report_data(report_data)
        # endregion
        # region ::TABLE FILL::
        doc_normal_14_border_center = workbook.add_format(STYLES['doc_normal_14_border_center'])
        doc_normal_14_border_center_money = workbook.add_format(STYLES['doc_normal_14_border_center_money'])
        doc_normal_14_border_center_percent = workbook.add_format(STYLES['doc_normal_14_border_center_percent'])
        sheet.write('C5', month_1_data and month_1_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('C6', month_1_data and month_1_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('C7', month_1_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('C8', month_1_data and month_1_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('C9', month_1_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('C10', month_1_data and month_1_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('C11', month_1_data and month_1_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('C12', month_1_data and month_1_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('D5', month_2_data and month_2_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('D6', month_2_data and month_2_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('D7', month_2_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('D8', month_2_data and month_2_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('D9', month_2_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('D10', month_2_data and month_2_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('D11', month_2_data and month_2_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('D12', month_2_data and month_2_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('E5', month_3_data and month_3_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('E6', month_3_data and month_3_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('E7', month_3_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('E8', month_3_data and month_3_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('E9', month_3_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('E10', month_3_data and month_3_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('E11', month_3_data and month_3_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('E12', month_3_data and month_3_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('F5', month_4_data and month_4_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('F6', month_4_data and month_4_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('F7', month_4_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('F8', month_4_data and month_4_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('F9', month_4_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('F10', month_4_data and month_4_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('F11', month_4_data and month_4_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('F12', month_4_data and month_4_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('G5', month_5_data and month_5_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('G6', month_5_data and month_5_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('G7', month_5_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('G8', month_5_data and month_5_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('G9', month_5_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('G10', month_5_data and month_5_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('G11', month_5_data and month_5_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('G12', month_5_data and month_5_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('H5', month_6_data and month_6_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('H6', month_6_data and month_6_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('H7', month_6_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('H8', month_6_data and month_6_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('H9', month_6_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('H10', month_6_data and month_6_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('H11', month_6_data and month_6_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('H12', month_6_data and month_6_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('I5', month_7_data and month_7_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('I6', month_7_data and month_7_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('I7', month_7_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('I8', month_7_data and month_7_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('I9', month_7_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('I10', month_7_data and month_7_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('I11', month_7_data and month_7_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('I12', month_7_data and month_7_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('J5', month_8_data and month_8_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('J6', month_8_data and month_8_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('J7', month_8_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('J8', month_8_data and month_8_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('J9', month_8_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('J10', month_8_data and month_8_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('J11', month_8_data and month_8_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('J12', month_8_data and month_8_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('K5', month_9_data and month_9_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('K6', month_9_data and month_9_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('K7', month_9_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('K8', month_9_data and month_9_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('K9', month_9_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('K10', month_9_data and month_9_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('K11', month_9_data and month_9_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('K12', month_9_data and month_9_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('L5', month_10_data and month_10_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('L6', month_10_data and month_10_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('L7', month_10_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('L8', month_10_data and month_10_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('L9', month_10_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('L10', month_10_data and month_10_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('L11', month_10_data and month_10_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('L12', month_10_data and month_10_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('M5', month_11_data and month_11_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('M6', month_11_data and month_11_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('M7', month_11_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('M8', month_11_data and month_11_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('M9', month_11_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('M10', month_11_data and month_11_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('M11', month_11_data and month_11_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('M12', month_11_data and month_11_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('N5', month_12_data and month_12_data[0]['untaxed_sent'] or 0, doc_normal_14_border_center_money)
        sheet.write('N6', month_12_data and month_12_data[0]['untaxed_failed'] or 0, doc_normal_14_border_center_money)
        sheet.write('N7', month_12_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('N8', month_12_data and month_12_data[0]['untaxed_signed'] or 0, doc_normal_14_border_center_money)
        sheet.write('N9', month_12_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('N10', month_12_data and month_12_data[0]['turnover_target'] or 0, doc_normal_14_border_center_money)
        sheet.write('N11', month_12_data and month_12_data[0]['operation'] or 0, doc_normal_14_border_center_money)
        sheet.write('N12', month_12_data and month_12_data[0]['service_maintainance'] or 0, doc_normal_14_border_center_money)
        sheet.write('O5', sum([_['untaxed_sent'] for _ in report_data]), doc_normal_14_border_center_money)
        sheet.write('O6', sum([_['untaxed_failed'] for _ in report_data]), doc_normal_14_border_center_money)
        sheet.write('O7', month_12_cumulative_percentage_fail, doc_normal_14_border_center_percent)
        sheet.write('O8', sum([_['untaxed_signed'] for _ in report_data]), doc_normal_14_border_center_money)
        sheet.write('O9', month_12_cumulative_percentage_sign, doc_normal_14_border_center_percent)
        sheet.write('O10', sum([_['turnover_target'] for _ in report_data]), doc_normal_14_border_center_money)
        sheet.write('O11', sum([_['operation'] for _ in report_data]), doc_normal_14_border_center_money)
        sheet.write('O12', sum([_['service_maintainance'] for _ in report_data]), doc_normal_14_border_center_money)
        # endregion
