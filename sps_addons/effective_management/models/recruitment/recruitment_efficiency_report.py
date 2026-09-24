from collections import OrderedDict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from reportlab import xrange
from odoo import fields, api, models, tools


class RecruitmentEfficiencyReport(models.Model):
    _name = 'recruitment.efficiency.report'
    _description = 'Báo cáo hiệu quả tuyển dụng'
    _order = 'sequence asc'

    master_key = fields.Integer('Master Key', index=True)
    name = fields.Char("Phân loại")
    m1 = fields.Integer('Jan')
    m2 = fields.Integer('Feb')
    m3 = fields.Integer('Mar')
    m4 = fields.Integer('Apr')
    m5 = fields.Integer('May')
    m6 = fields.Integer('Jun')
    m7 = fields.Integer('Jul')
    m8 = fields.Integer('Aug')
    m9 = fields.Integer('Sep')
    m10 = fields.Integer('Oct')
    m11 = fields.Integer('Nov')
    m12 = fields.Integer('Dec')
    total = fields.Integer(compute='_compute_total')
    sequence = fields.Integer()
    # def _prepare_value_month(self):
    #
    #     vals = {}  # Khởi tạo một từ điển rỗng để chứa kết quả
    #
    #     # Lấy thời gian hiện tại
    #     time_now = datetime.now()
    #
    #     # Tạo danh sách tên 12 tháng của năm hiện tại
    #     list_month = [
    #         (time_now.replace(month=i, day=1).strftime(r"%b-%y"),None)
    #         for i in range(1, 13)
    #     ]
    #
    #     # Thêm tên các tháng vào từ điển với các khóa 'm1', 'm2', ..., 'm12'
    #     for v in range(1, 13):
    #         vals[f'm{v}'] = list_month[v - 1]
    #
    #     return vals
    #
    def _compute_total(self):
        for i in self:
            i.total = i.m1 + i.m2 + i.m3 + i.m4 + i.m5 + i.m6 + i.m7 + i.m8 + i.m9 + i.m10 + i.m11 + i.m12
    #
    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     label = self._prepare_value_month()
    #     res = super(RecruitmentEfficiencyReport, self).fields_view_get(view_id=view_id, view_type=view_type,
    #                                                                 toolbar=toolbar,
    #                                                                 submenu=submenu)
    #     if view_type == 'tree':
    #         fields = res.get('fields')
    #         if fields:
    #             res['fields']['m1']['string'] = label['m1']
    #             res['fields']['m2']['string'] = label['m2']
    #             res['fields']['m3']['string'] = label['m3']
    #             res['fields']['m4']['string'] = label['m4']
    #             res['fields']['m5']['string'] = label['m5']
    #             res['fields']['m6']['string'] = label['m6']
    #             res['fields']['m7']['string'] = label['m7']
    #             res['fields']['m8']['string'] = label['m8']
    #             res['fields']['m9']['string'] = label['m9']
    #             res['fields']['m10']['string'] = label['m10']
    #             res['fields']['m11']['string'] = label['m11']
    #             res['fields']['m12']['string'] = label['m12']
    #     return res
    #
    # def _get_time_report(self):
    #     time_now = datetime.now()
    #     start_time = time_now.replace(month=12, day=31, hour=0, minute=0, second=0, microsecond=0)
    #     vals = {}
    #     for i in range(1, 13):
    #         vals.update({'m{}'.format(i): start_time - relativedelta(months=i - 1)})
    #     return vals

    # def init(self):
    #     time = self._get_time_report()
    #     """ Event main report """
    #     self._cr.execute('''DROP VIEW IF EXISTS hieu_qua_tuyen_dung CASCADE''')
    #     self._cr.execute('''create view hieu_qua_tuyen_dung as
    #                         (select  view_tong.year_createdate,
    #                                 view_tong.month_createdate,
    #                                 sum(view_tong.income_value)*12 as ngansachtuyendung,
    #                                 sum(view_tong.wage_actual)*12 as ngansachthucte,
    #                                 sum(view_tong.income_value)*12 - sum(view_tong.wage_actual)*12 as hieuquatuyendung
    #                         from
    #                             (select hr_recruit_request.id as request_id,
    #                                     hr_recruit_request.create_date as ngaytaoyeucau,
    #                                     extract ('month' from hr_recruit_request.create_date) as month_createdate,
    #                                     extract ('year' from hr_recruit_request.create_date) as year_createdate,
    #                                     hr_recruit_request.date_start as ngaybatdaulamviec,
    #                                     hr_recruit_request.quantity as soluongtuyen,
    #                                     hr_recruit_request.state as request_state,
    #                                     hr_employee.id as employee_id,
    #                                     hr_employee.name as employee_name,
    #                                     view_firstcontract.datestart as ngayhopdongdautien,
    #                                     view_ngaynhanluongcuoi.ngaynhanluongcuoi,
    #                                     hr_recruit_request.income_value,
    #                                     view_wage_actual.wage_actual,
    #                                     (case when view_ngaynhanluongcuoi.ngaynhanluongcuoi - view_firstcontract.datestart >= 365 then 1 else 0 end) as dieukienhople
    #                             from hr_employee
    #                             left join hr_applicant on hr_employee.x_cv_code = hr_applicant.id
    #                             left join hr_recruit_request on hr_applicant.recruit_rq_id = hr_recruit_request.id
    #                             left join
    #                                 (--Ngay ky hop dong dau tien cua nhan vien
    #                                 select 	hr_contract.employee_id,
    #                                         min(hr_contract.date_start) as datestart
    #                                 from hr_contract
    #                                 where hr_contract.state not in ('cancel', 'draft')
    #                                 group by employee_id
    #                                 ) as view_firstcontract
    #                             on hr_employee.id = view_firstcontract.employee_id
    #                             left join
    #                                 (--Luong thuc te cua nhan vien
    #                                 select 	view_firstcontract.employee_id,
    #                                         view_firstcontract.datestart,
    #                                         hr_contract.id as contract_id,
    #                                         (hr_contract.wage + hr_contract.x_allowance_phone) as wage_actual
    #                                 from
    #                                     (select hr_contract.employee_id,
    #                                             min(hr_contract.date_start) as datestart
    #                                     from hr_contract
    #                                     where hr_contract.state not in ('cancel', 'draft') and x_contract_type not in ('hdtv','hddv')
    #                                     group by employee_id
    #                                     ) as view_firstcontract
    #                                 left join hr_contract on view_firstcontract.employee_id = hr_contract.employee_id and view_firstcontract.datestart = hr_contract.date_start
    #                                 where hr_contract.state not in ('cancel', 'draft')
    #                                 ) as view_wage_actual
    #                             on hr_employee.id = view_wage_actual.employee_id
    #                             left join
    #                                 (select hr_payslip.employee_id,
    #                                         max(hr_payslip.date_to) as ngaynhanluongcuoi
    #                                 from hr_payslip
    #                                 where hr_payslip.state = 'done'
    #                                 group by hr_payslip.employee_id
    #                                 ) as view_ngaynhanluongcuoi
    #                             on hr_employee.id = view_ngaynhanluongcuoi.employee_id
    #                         ) as view_tong
    #                         where view_tong.dieukienhople = 1
    #                         group by  view_tong.year_createdate, view_tong.month_createdate
    #                         order by  view_tong.year_createdate, view_tong.month_createdate)''')
    #
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     sql = ''' CREATE VIEW {table} AS (
    #         select row_number() OVER () AS id,
    #         *
    #         from (
    #             select
    #             1 as sequence,
    #             'Tổng giá trị lương ngân sách tuyển dụng' as name,
    #             sum(case when ert.month_createdate = '{m1}' and ert.year_createdate = '{y1}' then ert.ngansachtuyendung end)
    #             as m1,
    #             sum(case when ert.month_createdate = '{m2}' and ert.year_createdate = '{y2}' then ert.ngansachtuyendung end)
    #             as m2,
    #             sum(case when ert.month_createdate = '{m3}' and ert.year_createdate = '{y3}' then ert.ngansachtuyendung end)
    #             as m3,
    #             sum(case when ert.month_createdate = '{m4}' and ert.year_createdate = '{y4}' then ert.ngansachtuyendung end)
    #             as m4,
    #             sum(case when ert.month_createdate = '{m5}' and ert.year_createdate = '{y5}' then ert.ngansachtuyendung end)
    #             as m5,
    #             sum(case when ert.month_createdate = '{m6}' and ert.year_createdate = '{y6}' then ert.ngansachtuyendung end)
    #             as m6,
    #             sum(case when ert.month_createdate = '{m7}' and ert.year_createdate = '{y7}' then ert.ngansachtuyendung end)
    #             as m7,
    #             sum(case when ert.month_createdate = '{m8}' and ert.year_createdate = '{y8}' then ert.ngansachtuyendung end)
    #             as m8,
    #             sum(case when ert.month_createdate = '{m9}' and ert.year_createdate = '{y9}' then ert.ngansachtuyendung end)
    #             as m9,
    #             sum(case when ert.month_createdate = '{m10}' and ert.year_createdate = '{y10}' then ert.ngansachtuyendung end)
    #             as m10,
    #             sum(case when ert.month_createdate = '{m11}' and ert.year_createdate = '{y11}' then ert.ngansachtuyendung end)
    #             as m11,
    #             sum(case when ert.month_createdate = '{m12}' and ert.year_createdate = '{y12}' then ert.ngansachtuyendung end)
    #             as m12
    #             from hieu_qua_tuyen_dung ert
    #
    #
    #             union
    #
    #             select
    #             2 as sequence,
    #             'Tổng giá trị thu nhập ứng viên đã tuyển' as name,
    #             sum(case when ert.month_createdate = '{m1}' and ert.year_createdate = '{y1}' then ert.ngansachthucte end)
    #             as m1,
    #             sum(case when ert.month_createdate = '{m2}' and ert.year_createdate = '{y2}' then ert.ngansachthucte end)
    #             as m2,
    #             sum(case when ert.month_createdate = '{m3}' and ert.year_createdate = '{y3}' then ert.ngansachthucte end)
    #             as m3,
    #             sum(case when ert.month_createdate = '{m4}' and ert.year_createdate = '{y4}' then ert.ngansachthucte end)
    #             as m4,
    #             sum(case when ert.month_createdate = '{m5}' and ert.year_createdate = '{y5}' then ert.ngansachthucte end)
    #             as m5,
    #             sum(case when ert.month_createdate = '{m6}' and ert.year_createdate = '{y6}' then ert.ngansachthucte end)
    #             as m6,
    #             sum(case when ert.month_createdate = '{m7}' and ert.year_createdate = '{y7}' then ert.ngansachthucte end)
    #             as m7,
    #             sum(case when ert.month_createdate = '{m8}' and ert.year_createdate = '{y8}' then ert.ngansachthucte end)
    #             as m8,
    #             sum(case when ert.month_createdate = '{m9}' and ert.year_createdate = '{y9}' then ert.ngansachthucte end)
    #             as m9,
    #             sum(case when ert.month_createdate = '{m10}' and ert.year_createdate = '{y10}' then ert.ngansachthucte end)
    #             as m10,
    #             sum(case when ert.month_createdate = '{m11}' and ert.year_createdate = '{y11}' then ert.ngansachthucte end)
    #             as m11,
    #             sum(case when ert.month_createdate = '{m12}' and ert.year_createdate = '{y12}' then ert.ngansachthucte end)
    #             as m12
    #             from hieu_qua_tuyen_dung ert
    #
    #
    #             union
    #
    #             select
    #             3 as sequence,
    #             'Hiệu quả tuyển dụng' as name,
    #             sum(case when ert.month_createdate = '{m1}' and ert.year_createdate = '{y1}' then  ert.hieuquatuyendung end)
    #             as m1,
    #             sum(case when ert.month_createdate = '{m2}' and ert.year_createdate = '{y2}' then ert.hieuquatuyendung end)
    #             as m2,
    #             sum(case when ert.month_createdate = '{m3}' and ert.year_createdate = '{y3}' then ert.hieuquatuyendung end)
    #             as m3,
    #             sum(case when ert.month_createdate = '{m4}' and ert.year_createdate = '{y4}' then ert.hieuquatuyendung end)
    #             as m4,
    #             sum(case when ert.month_createdate = '{m5}' and ert.year_createdate = '{y5}' then ert.hieuquatuyendung end)
    #             as m5,
    #             sum(case when ert.month_createdate = '{m6}' and ert.year_createdate = '{y6}' then ert.hieuquatuyendung end)
    #             as m6,
    #             sum(case when ert.month_createdate = '{m7}' and ert.year_createdate = '{y7}' then ert.hieuquatuyendung end)
    #             as m7,
    #             sum(case when ert.month_createdate = '{m8}' and ert.year_createdate = '{y8}' then ert.hieuquatuyendung end)
    #             as m8,
    #             sum(case when ert.month_createdate = '{m9}' and ert.year_createdate = '{y9}' then ert.hieuquatuyendung end)
    #             as m9,
    #             sum(case when ert.month_createdate = '{m10}' and ert.year_createdate = '{y10}' then ert.hieuquatuyendung end)
    #             as m10,
    #             sum(case when ert.month_createdate = '{m11}' and ert.year_createdate = '{y11}' then ert.hieuquatuyendung end)
    #             as m11,
    #             sum(case when ert.month_createdate = '{m12}' and ert.year_createdate = '{y12}' then ert.hieuquatuyendung end)
    #             as m12
    #             from hieu_qua_tuyen_dung ert
    #
    #         ) as master
    #         )'''.format(
    #         table=self._table,
    #         m1=time['m12'].month,y1=time['m12'].year -1,
    #         m2=time['m11'].month,y2=time['m11'].year -1,
    #         m3=time['m10'].month,y3=time['m10'].year -1,
    #         m4=time['m9'].month,y4=time['m9'].year -1,
    #         m5=time['m8'].month,y5=time['m8'].year -1,
    #         m6=time['m7'].month,y6=time['m7'].year -1,
    #         m7=time['m6'].month,y7=time['m6'].year -1,
    #         m8=time['m5'].month,y8=time['m5'].year -1,
    #         m9=time['m4'].month,y9=time['m4'].year -1,
    #         m10=time['m3'].month,y10=time['m3'].year -1,
    #         m11=time['m2'].month,y11=time['m2'].year -1,
    #         m12=time['m1'].month,y12=time['m1'].year -1,
    #     )
    #     # print(sql)
    #     self._cr.execute(sql)
