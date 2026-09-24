from io import BytesIO
from os.path import abspath, dirname, join
from odoo import fields, models

STYLES = {
    "header_1": {"font_name": "Times New Roman", "font_size": 16, "bold": True, "align": "center"},
    "header_2": {"font_name": "Times New Roman", "font_size": 12, "italic": True, "align": "center"},
    "doc_bold_12": {"font_name": "Times New Roman", "font_size": 12, "bold": True, 'text_wrap': True},
    "doc_bold_12_border": {"font_name": "Times New Roman", "font_size": 11, "bold": True, "border": 1, 'text_wrap': True},
    "doc_bold_12_border_center": {"font_name": "Times New Roman", "font_size": 11, "bold": True, "border": 1, "align": "center", 'text_wrap': True},
    "doc_normal_12": {"font_name": "Times New Roman", "font_size": 11, "align": "left", 'text_wrap': True},
    "doc_normal_12_border_center": {"font_name": "Times New Roman", "font_size": 11, "border": 1, "align": "center", 'text_wrap': True},
    "doc_normal_12_border_center_money": {"font_name": "Times New Roman", "font_size": 11, "border": 1, "align": "center", 'text_wrap': True, 'num_format': '#,##0'},
    "doc_normal_12_border_center_percent": {"font_name": "Times New Roman", "font_size": 11, "border": 1, "align": "center", 'text_wrap': True, 'num_format': '#,##0.00'},
}

def process_report_data(report_data):
    def dict_filter(dictlist, key, value):
        res = list(filter(lambda x: x.get(key) == value, dictlist))
        if res:
            res = res[0]
            res['profit_ratio'] = res['amount'] and res['profit'] * 100 / res['amount'] or 0
            return res
        return {}
    current_year = fields.Date.today().year
    year_1 = dict_filter(report_data, "year", current_year - 5)
    year_2 = dict_filter(report_data, "year", current_year - 4)
    year_3 = dict_filter(report_data, "year", current_year - 3)
    year_4 = dict_filter(report_data, "year", current_year - 2)
    year_5 = dict_filter(report_data, "year", current_year - 1)
    year_6 = dict_filter(report_data, "year", current_year)
    year_7 = dict_filter(report_data, "year", current_year + 1)
    year_8 = dict_filter(report_data, "year", current_year + 2)
    year_9 = dict_filter(report_data, "year", current_year + 3)
    year_10 = dict_filter(report_data, "year", current_year + 4)
    return (
        year_1,
        year_2,
        year_3,
        year_4,
        year_5,
        year_6,
        year_7,
        year_8,
        year_9,
        year_10,
    )

class AnnualSaleReportXlsx(models.AbstractModel):
    _name = 'report.sps_sale_target.annual_sale_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, partners):
        sheet = workbook.add_worksheet('BÁO CÁO DOANH SỐ NĂM')
        # region ::SET ROW - SET COL::
        sheet.set_row(0, height=25)
        sheet.set_row(1, height=15)
        sheet.set_row(2, height=15)
        sheet.set_row(3, height=30)
        sheet.set_row(4, height=30)
        sheet.set_row(5, height=30)
        sheet.set_row(6, height=30)
        sheet.set_row(7, height=30)
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
        # endregion
        # region ::HEADER::
        module_loc = dirname(dirname(abspath(__file__)))
        img_path = join(module_loc, 'static/description/sps.png')
        logo = open(img_path, 'rb').read()
        sheet.insert_image('A1', img_path, {'image_data': BytesIO(logo), 'x_scale': 0.2, 'y_scale': 0.2})
        sheet.write('F1', 'BÁO CÁO DOANH SỐ NĂM', workbook.add_format(STYLES["header_1"]))
        sheet.write('F2', 'ANNUAL SALES REPORT', workbook.add_format(STYLES["header_2"]))
        sheet.write('K1', 'Prepared by:', workbook.add_format(STYLES["doc_normal_12"]))
        sheet.write('L1', self.env.user.name, workbook.add_format(STYLES["doc_normal_12"]))
        sheet.write('K2', 'Updated on:', workbook.add_format(STYLES["doc_normal_12"]))
        sheet.write('L2', fields.Date.today().strftime('%d-%b-%Y'), workbook.add_format(STYLES["doc_normal_12"]))
        # endregion
        # region ::TABLE HEADER::
        doc_bold_12_border = workbook.add_format(STYLES["doc_bold_12_border"])
        doc_bold_12_border_center = workbook.add_format(STYLES["doc_bold_12_border_center"])
        current_year = fields.Date.today().year
        sheet.write('A3', 'Item', doc_bold_12_border)
        sheet.write('B3', 'Year', doc_bold_12_border)
        sheet.merge_range('A4:B4', 'Tổng doanh số mục tiêu\nTotal turnover target', doc_bold_12_border)
        sheet.merge_range('A5:B5', 'Tổng doanh số đạt được\nTotal turnover', doc_bold_12_border)
        sheet.merge_range('A6:B6', 'Tăng trưởng doanh số\nTurnover growth rate', doc_bold_12_border)
        sheet.merge_range('A7:B7', 'Lợi nhuận sau thuế thu nhập doanh nghiệp\nProfit after corporate income tax', doc_bold_12_border)
        sheet.merge_range('A8:B8', 'Tỉ lệ lợi nhuận\nRatio of profit (%)', doc_bold_12_border)
        sheet.write('C3', current_year - 5, doc_bold_12_border_center)
        sheet.write('D3', current_year - 4, doc_bold_12_border_center)
        sheet.write('E3', current_year - 3, doc_bold_12_border_center)
        sheet.write('F3', current_year - 2, doc_bold_12_border_center)
        sheet.write('G3', current_year - 1, doc_bold_12_border_center)
        sheet.write('H3', current_year, doc_bold_12_border_center)
        sheet.write('I3', current_year - 1, doc_bold_12_border_center)
        sheet.write('J3', current_year - 2, doc_bold_12_border_center)
        sheet.write('K3', current_year - 3, doc_bold_12_border_center)
        sheet.write('L3', current_year - 4, doc_bold_12_border_center)
        sheet.write('M3', 'Total', doc_bold_12_border_center)
        # endregion
        # region ::DATA::
        doc_normal_12_border_center = workbook.add_format(STYLES["doc_normal_12_border_center"])
        doc_normal_12_border_center_money = workbook.add_format(STYLES["doc_normal_12_border_center_money"])
        doc_normal_12_border_center_percent = workbook.add_format(STYLES["doc_normal_12_border_center_percent"])
        (
            year_1,
            year_2,
            year_3,
            year_4,
            year_5,
            year_6,
            year_7,
            year_8,
            year_9,
            year_10
        ) = process_report_data(data['report_data'])
        sheet.write('C4', year_1 and year_1['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('C5', year_1 and year_1['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('C6', 0, doc_normal_12_border_center_percent)
        sheet.write('C7', year_1 and year_1['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('C8', year_1 and year_1['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('D4', year_2 and year_2['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('D5', year_2 and year_2['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('D6', year_1.get('amount', 0) and year_2.get('amount', 0) * 100 / year_1.get('amount', 0) or 0, doc_normal_12_border_center_percent)
        sheet.write('D7', year_2 and year_2['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('D8', year_2 and year_2['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('E4', year_3 and year_3['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('E5', year_3 and year_3['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('E6', year_2.get('amount', 0) and year_3.get('amount', 0) * 100 / year_2.get('amount', 0) or 0, doc_normal_12_border_center_percent)
        sheet.write('E7', year_3 and year_3['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('E8', year_3 and year_3['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('F4', year_4 and year_4['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('F5', year_4 and year_4['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('F6', year_3.get('amount', 0) and year_4.get('amount', 0) * 100 / year_3.get('amount', 0) or 0, doc_normal_12_border_center_percent)
        sheet.write('F7', year_4 and year_4['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('F8', year_4 and year_4['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('G4', year_5 and year_5['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('G5', year_5 and year_5['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('G6', year_4.get('amount', 0) and year_5.get('amount', 0) * 100 / year_4.get('amount', 0) or 0, doc_normal_12_border_center_percent)
        sheet.write('G7', year_5 and year_5['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('G8', year_5 and year_5['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('H4', year_6 and year_6['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('H5', year_6 and year_6['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('H6', year_5.get('amount', 0) and year_6.get('amount', 0) * 100 / year_5.get('amount', 0) or 0, doc_normal_12_border_center_percent)
        sheet.write('H7', year_6 and year_6['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('H8', year_6 and year_6['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('I4', year_7 and year_7['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('I5', year_7 and year_7['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('I6', year_6.get('amount', 0) and year_7.get('amount', 0) * 100 / year_6.get('amount', 0) or 0, doc_normal_12_border_center_percent)
        sheet.write('I7', year_7 and year_7['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('I8', year_7 and year_7['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('J4', year_8 and year_8['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('J5', year_8 and year_8['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('J6', year_7.get('amount', 0) and year_8.get('amount', 0) * 100 / year_7.get('amount', 0) or 0, doc_normal_12_border_center_percent)
        sheet.write('J7', year_8 and year_8['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('J8', year_8 and year_8['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('K4', year_9 and year_9['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('K5', year_9 and year_9['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('K6', year_8.get('amount', 0) and year_9.get('amount', 0) * 100 / year_8.get('amount', 0) or 0, doc_normal_12_border_center_percent)
        sheet.write('K7', year_9 and year_9['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('K8', year_9 and year_9['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('L4', year_10 and year_10['sale_target'] or 0, doc_normal_12_border_center_money)
        sheet.write('L5', year_10 and year_10['amount'] or 0, doc_normal_12_border_center_money)
        sheet.write('L6', year_9.get('amount', 0) and year_10.get('amount', 0) * 100 / year_9.get('amount', 0) or 0, doc_normal_12_border_center_percent)
        sheet.write('L7', year_10 and year_10['profit'] or 0, doc_normal_12_border_center_money)
        sheet.write('L8', year_10 and year_10['profit_ratio'] or 0, doc_normal_12_border_center_percent)
        sheet.write('M4', sum([_['sale_target'] for _ in data['report_data']]), doc_normal_12_border_center_money)
        sheet.write('M5', sum([_['amount'] for _ in data['report_data']]), doc_normal_12_border_center_money)
        sheet.write('M6', 0, doc_normal_12_border_center_percent)
        sheet.write('M7', sum([_['profit'] for _ in data['report_data']]), doc_normal_12_border_center_money)
        sheet.write('M8', sum([_['amount'] for _ in data['report_data']]) and sum([_['profit'] for _ in data['report_data']]) / sum([_['amount'] for _ in data['report_data']]) or 0, doc_normal_12_border_center_percent)
        # endregion
