from collections import OrderedDict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from reportlab import xrange
from odoo import fields, api, models, tools


class ReportRecruitmentMonthly(models.Model):
    _name = 'report.recruitment.monthly'
    _description = 'Recruitment Monthly'
    _order = 'sequence asc'

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
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
    #
    # def _prepare_value_month(self):
    #     vals = {}  # Khởi tạo một từ điển rỗng để chứa kết quả
    #
    #     # Lấy thời gian hiện tại
    #     time_now = datetime.now()
    #
    #     # Tạo danh sách tên 12 tháng của năm hiện tại
    #     list_month = [
    #         (time_now.replace(month=i, day=1).strftime(r"%b-%y"), None)
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
    #     res = super(ReportRecruitmentMonthly, self).fields_view_get(view_id=view_id, view_type=view_type,
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
    #
    # @api.model
    # def init(self):
    #     time = self._get_time_report()
    #     """ Event main report """
    #     self._cr.execute('''DROP VIEW IF EXISTS tinh_trang_tuyen_dung CASCADE''')
    #     self._cr.execute('''create view tinh_trang_tuyen_dung as
    #                     (select view_reportrecruitmentsatus.year_create,
    #                             view_reportrecruitmentsatus.month_create,
    #                             sum(view_reportrecruitmentsatus.quantity_yeucautuyendung) as quantity_yeucautuyendung,
    #                             sum(view_reportrecruitmentsatus.quantity_cancel) as quantity_cancel,
    #                             sum(view_reportrecruitmentsatus.datuyen_tronghan) as datuyen_tronghan,
    #                             sum(view_reportrecruitmentsatus.datuyen_quahan) as datuyen_quahan,
    #                             sum(view_reportrecruitmentsatus.chuatuyen_tronghan) as chuatuyen_tronghan,
    #                             sum(view_reportrecruitmentsatus.chuatuyen_quahan) as chuatuyen_quahan
    #                     from
    #                         (select view_slgyeucautuyendung.year_create,
    #                                 view_slgyeucautuyendung.month_create,
    #                                 (sum(case when state not in ('draft','canceled') then quantity else 0 end) + sum(case when state = 'canceled' then quantity_datuyen else 0 end)) as quantity_yeucautuyendung,
    #                                 (sum(case when state = 'canceled' and quantity_datuyen = 0 then quantity else 0 end) + sum(case when state = 'canceled' and quantity_datuyen > 0 then quantity_chuatuyen else 0 end)) as quantity_cancel,
    #                                 0 as datuyen_tronghan,
    #                                 0 as datuyen_quahan,
    #                                 0 as chuatuyen_tronghan,
    #                                 0 as chuatuyen_quahan
    #                         from
    #                             (select id as request_id,
    #                                     state,
    #                                     create_date,
    #                                     extract ('year' from create_date)::character varying as year_create,
    #                                     extract ('month' from create_date)::character varying as month_create,
    #                                     date_start,
    #                                     current_date,
    #                                     quantity,
    #                                     coalesce(view_ungviendatuyen.quantity_datuyen,0) as quantity_datuyen,
    #                                     (quantity - coalesce(quantity_datuyen,0)) as quantity_chuatuyen
    #                             from hr_recruit_request
    #                             left join
    #                                 (select view_tinhtrangtuyendung.recruit_rq_id,
    #                                         count(contract_id) as quantity_datuyen
    #                                 from
    #                                     (select view_requestid.contract_id,
    #                                             view_requestid.employee_id,
    #                                             view_requestid.employee_name,
    #                                             view_requestid.date_start,
    #                                             view_requestid.first_date_start,
    #                                             view_requestid.x_cv_code,
    #                                             view_requestid.recruit_rq_id,
    #                                             hr_recruit_request.create_date,
    #                                             hr_recruit_request.date_start as rr_date_start
    #                                     from
    #                                         (select view_cvcode.contract_id,
    #                                                 view_cvcode.employee_id,
    #                                                 view_cvcode.employee_name,
    #                                                 view_cvcode.date_start,
    #                                                 view_cvcode.first_date_start,
    #                                                 view_cvcode.x_cv_code,
    #                                                 hr_applicant.recruit_rq_id
    #                                         from
    #                                             (select view_base.contract_id,
    #                                                     view_base.employee_id,
    #                                                     hr_employee.name as employee_name,
    #                                                     view_base.date_start,
    #                                                     view_base.first_date_start,
    #                                                     hr_employee.x_cv_code
    #                                             from
    #                                                 (select hr_contract.id as contract_id,
    #                                                         hr_contract.employee_id,
    #                                                         hr_contract.date_start,
    #                                                         view_firstdatestart.first_date_start
    #                                                 from hr_contract
    #                                                 left join
    #                                                     (select employee_id,
    #                                                             min(date_start) as first_date_start
    #                                                     from hr_contract
    #                                                     where state in ('open', 'close')
    #                                                     group by employee_id
    #                                                     order by employee_id
    #                                                     ) as view_firstdatestart
    #                                                 on hr_contract.employee_id = view_firstdatestart.employee_id
    #                                                 where date_start = first_date_start
    #                                                     and hr_contract.state in ('open', 'close')
    #                                                 order by employee_id
    #                                                 ) as view_base
    #                                             left join hr_employee on view_base.employee_id = hr_employee.id
    #                                             ) as view_cvcode
    #                                         left join hr_applicant on view_cvcode.x_cv_code = hr_applicant.id
    #                                         ) as view_requestid
    #                                     left join hr_recruit_request on hr_recruit_request.id = view_requestid.recruit_rq_id
    #                                     order by contract_id
    #                                     ) as view_tinhtrangtuyendung
    #                                 group by view_tinhtrangtuyendung.recruit_rq_id
    #                                 ) as view_ungviendatuyen
    #                             on hr_recruit_request.id = view_ungviendatuyen.recruit_rq_id
    #                             order by request_id desc
    #                             ) as view_slgyeucautuyendung
    #                         group by view_slgyeucautuyendung.year_create, view_slgyeucautuyendung.month_create
    #
    #                         union all
    #
    #                         select 	view_quantitydatuyen.year_create,
    #                                 view_quantitydatuyen.month_create,
    #                                 0 as quantity_yeucautuyendung,
    #                                 0 as quantity_cancel,
    #                                 count(case when date_start <= rr_date_start then 1 end) as datuyen_tronghan,
    #                                 count(case when date_start > rr_date_start then 1 end) as datuyen_quahan,
    #                                 0 as chuatuyen_tronghan,
    #                                 0 as chuatuyen_quahan
    #                         from
    #                             (select  hr_recruit_request.create_date,
    #                                     extract ('year' from create_date)::character varying as year_create,
    #                                     extract ('month' from create_date)::character varying as month_create,
    #                                     view_requestid.contract_id,
    #                                     view_requestid.employee_id,
    #                                     view_requestid.employee_name,
    #                                     view_requestid.date_start,
    #                                     view_requestid.first_date_start,
    #                                     view_requestid.x_cv_code,
    #                                     view_requestid.recruit_rq_id,
    #                                     hr_recruit_request.date_start as rr_date_start
    #                             from
    #                                 (select view_cvcode.contract_id,
    #                                         view_cvcode.employee_id,
    #                                         view_cvcode.employee_name,
    #                                         view_cvcode.date_start,
    #                                         view_cvcode.first_date_start,
    #                                         view_cvcode.x_cv_code,
    #                                         hr_applicant.recruit_rq_id
    #                                 from
    #                                     (select view_base.contract_id,
    #                                             view_base.employee_id,
    #                                             hr_employee.name as employee_name,
    #                                             view_base.date_start,
    #                                             view_base.first_date_start,
    #                                             hr_employee.x_cv_code
    #                                     from
    #                                         (select hr_contract.id as contract_id,
    #                                                 hr_contract.employee_id,
    #                                                 hr_contract.date_start,
    #                                                 view_firstdatestart.first_date_start
    #                                         from hr_contract
    #                                         left join
    #                                             (select employee_id,
    #                                                     min(date_start) as first_date_start
    #                                             from hr_contract
    #                                             where state in ('open', 'close')
    #                                             group by employee_id
    #                                             order by employee_id
    #                                             ) as view_firstdatestart on hr_contract.employee_id = view_firstdatestart.employee_id
    #                                         where date_start = first_date_start
    #                                         and hr_contract.state in ('open', 'close')
    #                                         order by employee_id
    #                                         ) as view_base
    #                                     left join hr_employee on view_base.employee_id = hr_employee.id
    #                                     ) as view_cvcode
    #                                 left join hr_applicant on view_cvcode.x_cv_code = hr_applicant.id
    #                                 ) as view_requestid
    #                             left join hr_recruit_request on hr_recruit_request.id = view_requestid.recruit_rq_id
    #                             order by contract_id
    #                             ) as view_quantitydatuyen
    #                         group by year_create, month_create
    #
    #                         union all
    #
    #                         select 	view_tonghop.year_create,
    #                                 view_tonghop.month_create,
    #                                 0 as quantity_yeucautuyendung,
    #                                 0 as quantity_cancel,
    #                                 0 as datuyen_tronghan,
    #                                 0 as datuyen_quahan,
    #                                 sum (case when date_start >= current_date then quantity_chuatuyen else 0 end) as chuatuyen_tronghan,
    #                                 sum (case when date_start < current_date then quantity_chuatuyen else 0 end) as chuatuyen_quahan
    #                         from
    #                             (select id as request_id,
    #                                     state,
    #                                     create_date,
    #                                     extract ('year' from create_date)::character varying as year_create,
    #                                     extract ('month' from create_date)::character varying as month_create,
    #                                     date_start,
    #                                     current_date,
    #                                     quantity,
    #                                     coalesce(view_ungviendatuyen.quantity_datuyen,0) as quantity_datuyen,
    #                                     (quantity - coalesce(quantity_datuyen,0)) as quantity_chuatuyen
    #                             from hr_recruit_request
    #                             left join
    #                                 (select view_tinhtrangtuyendung.recruit_rq_id,
    #                                         count(contract_id) as quantity_datuyen
    #                                 from
    #                                     (select view_requestid.contract_id,
    #                                             view_requestid.employee_id,
    #                                             view_requestid.employee_name,
    #                                             view_requestid.date_start,
    #                                             view_requestid.first_date_start,
    #                                             view_requestid.x_cv_code,
    #                                             view_requestid.recruit_rq_id,
    #                                             hr_recruit_request.create_date,
    #                                             hr_recruit_request.date_start as rr_date_start
    #                                     from
    #                                         (select view_cvcode.contract_id,
    #                                                 view_cvcode.employee_id,
    #                                                 view_cvcode.employee_name,
    #                                                 view_cvcode.date_start,
    #                                                 view_cvcode.first_date_start,
    #                                                 view_cvcode.x_cv_code,
    #                                                 hr_applicant.recruit_rq_id
    #                                         from
    #                                             (select view_base.contract_id,
    #                                                     view_base.employee_id,
    #                                                     hr_employee.name as employee_name,
    #                                                     view_base.date_start,
    #                                                     view_base.first_date_start,
    #                                                     hr_employee.x_cv_code
    #                                             from
    #                                                 (select hr_contract.id as contract_id,
    #                                                         hr_contract.employee_id,
    #                                                         hr_contract.date_start,
    #                                                         view_firstdatestart.first_date_start
    #                                                 from hr_contract
    #                                                 left join
    #                                                     (select employee_id,
    #                                                             min(date_start) as first_date_start
    #                                                     from hr_contract
    #                                                     where state in ('open', 'close')
    #                                                     group by employee_id
    #                                                     order by employee_id
    #                                                     ) as view_firstdatestart on hr_contract.employee_id = view_firstdatestart.employee_id
    #                                                 where date_start = first_date_start
    #                                                     and hr_contract.state in ('open', 'close')
    #                                                 order by employee_id
    #                                                 ) as view_base
    #                                             left join hr_employee
    #                                             on view_base.employee_id = hr_employee.id
    #                                             ) as view_cvcode
    #                                         left join hr_applicant
    #                                         on view_cvcode.x_cv_code = hr_applicant.id
    #                                         ) as view_requestid
    #                                     left join hr_recruit_request
    #                                     on hr_recruit_request.id = view_requestid.recruit_rq_id
    #                                     order by contract_id
    #                                     ) as view_tinhtrangtuyendung
    #                                 group by view_tinhtrangtuyendung.recruit_rq_id
    #                                 ) as view_ungviendatuyen on hr_recruit_request.id = view_ungviendatuyen.recruit_rq_id
    #                             where hr_recruit_request.state not in ('draft', 'canceled')
    #                             order by request_id desc
    #                             ) view_tonghop
    #                         group by view_tonghop.year_create, view_tonghop.month_create
    #                         ) as view_reportrecruitmentsatus
    #                     group by view_reportrecruitmentsatus.year_create, view_reportrecruitmentsatus.month_create
    #                     order by view_reportrecruitmentsatus.year_create, view_reportrecruitmentsatus.month_create)''')
    #
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self._cr.execute(""" CREATE VIEW {table} AS (
    #         select row_number() OVER () AS id,
    #         *
    #         from (
    #             select
    #             1 as sequence,
    #             'Số ứng viên yêu cầu tuyển dụng (Requested quantity)' as name,
    #             sum(case when (hrt.month_create = '{m1}') and (hrt.year_create = '{y1}') then hrt.quantity_yeucautuyendung end)
    #             as m1,
    #             sum(case when (hrt.month_create = '{m2}') and (hrt.year_create = '{y2}') then hrt.quantity_yeucautuyendung end)
    #             as m2,
    #             sum(case when (hrt.month_create = '{m3}') and (hrt.year_create = '{y3}') then hrt.quantity_yeucautuyendung end)
    #             as m3,
    #             sum(case when (hrt.month_create = '{m4}') and (hrt.year_create = '{y4}') then hrt.quantity_yeucautuyendung end)
    #             as m4,
    #             sum(case when (hrt.month_create = '{m5}') and (hrt.year_create = '{y5}') then hrt.quantity_yeucautuyendung end)
    #             as m5,
    #             sum(case when (hrt.month_create = '{m6}') and (hrt.year_create = '{y6}') then hrt.quantity_yeucautuyendung end)
    #             as m6,
    #             sum(case when (hrt.month_create = '{m7}') and (hrt.year_create = '{y7}') then hrt.quantity_yeucautuyendung end)
    #             as m7,
    #             sum(case when (hrt.month_create = '{m8}') and (hrt.year_create = '{y8}') then hrt.quantity_yeucautuyendung end)
    #             as m8,
    #             sum(case when (hrt.month_create = '{m9}') and (hrt.year_create = '{y9}') then hrt.quantity_yeucautuyendung end)
    #             as m9,
    #             sum(case when (hrt.month_create = '{m10}') and (hrt.year_create = '{y10}') then hrt.quantity_yeucautuyendung end)
    #             as m10,
    #             sum(case when (hrt.month_create = '{m11}') and (hrt.year_create = '{y11}') then hrt.quantity_yeucautuyendung end)
    #             as m11,
    #             sum(case when (hrt.month_create = '{m12}') and (hrt.year_create = '{y12}') then hrt.quantity_yeucautuyendung end)
    #             as m12
    #             from tinh_trang_tuyen_dung hrt
    #
    #             union
    #
    #             select
    #             2 as sequence,
    #             'Số ứng viên tuyển dụng bị hủy (Cancelled quantity)' as name,
    #             sum(case when (hrt.month_create = '{m1}') and (hrt.year_create = '{y1}') then hrt.quantity_cancel end)
    #             as m1,
    #             sum(case when (hrt.month_create = '{m2}') and (hrt.year_create = '{y2}') then hrt.quantity_cancel end)
    #             as m2,
    #             sum(case when (hrt.month_create = '{m3}') and (hrt.year_create = '{y3}') then hrt.quantity_cancel end)
    #             as m3,
    #             sum(case when (hrt.month_create = '{m4}') and (hrt.year_create = '{y4}') then hrt.quantity_cancel end)
    #             as m4,
    #             sum(case when (hrt.month_create = '{m5}') and (hrt.year_create = '{y5}') then hrt.quantity_cancel end)
    #             as m5,
    #             sum(case when (hrt.month_create = '{m6}') and (hrt.year_create = '{y6}') then hrt.quantity_cancel end)
    #             as m6,
    #             sum(case when (hrt.month_create = '{m7}') and (hrt.year_create = '{y7}') then hrt.quantity_cancel end)
    #             as m7,
    #             sum(case when (hrt.month_create = '{m8}') and (hrt.year_create = '{y8}') then hrt.quantity_cancel end)
    #             as m8,
    #             sum(case when (hrt.month_create = '{m9}') and (hrt.year_create = '{y9}') then hrt.quantity_cancel end)
    #             as m9,
    #             sum(case when (hrt.month_create = '{m10}') and (hrt.year_create = '{y10}') then hrt.quantity_cancel end)
    #             as m10,
    #             sum(case when (hrt.month_create = '{m11}') and (hrt.year_create = '{y11}') then hrt.quantity_cancel end)
    #             as m11,
    #             sum(case when (hrt.month_create = '{m12}') and (hrt.year_create = '{y12}') then hrt.quantity_cancel end)
    #             as m12
    #             from tinh_trang_tuyen_dung hrt
    #
    #             union
    #
    #             select
    #             3 as sequence,
    #             'Số ứng viên được tuyển trong thời hạn (Done quantity)' as name,
    #             sum(case when (hrt.month_create = '{m1}') and (hrt.year_create = '{y1}') then hrt.datuyen_tronghan end)
    #             as m1,
    #             sum(case when (hrt.month_create = '{m2}') and (hrt.year_create = '{y2}') then hrt.datuyen_tronghan end)
    #             as m2,
    #             sum(case when (hrt.month_create = '{m3}') and (hrt.year_create = '{y3}') then hrt.datuyen_tronghan end)
    #             as m3,
    #             sum(case when (hrt.month_create = '{m4}') and (hrt.year_create = '{y4}') then hrt.datuyen_tronghan end)
    #             as m4,
    #             sum(case when (hrt.month_create = '{m5}') and (hrt.year_create = '{y5}') then hrt.datuyen_tronghan end)
    #             as m5,
    #             sum(case when (hrt.month_create = '{m6}') and (hrt.year_create = '{y6}') then hrt.datuyen_tronghan end)
    #             as m6,
    #             sum(case when (hrt.month_create = '{m7}') and (hrt.year_create = '{y7}') then hrt.datuyen_tronghan end)
    #             as m7,
    #             sum(case when (hrt.month_create = '{m8}') and (hrt.year_create = '{y8}') then hrt.datuyen_tronghan end)
    #             as m8,
    #             sum(case when (hrt.month_create = '{m9}') and (hrt.year_create = '{y9}') then hrt.datuyen_tronghan end)
    #             as m9,
    #             sum(case when (hrt.month_create = '{m10}') and (hrt.year_create = '{y10}') then hrt.datuyen_tronghan end)
    #             as m10,
    #             sum(case when (hrt.month_create = '{m11}') and (hrt.year_create = '{y11}') then hrt.datuyen_tronghan end)
    #             as m11,
    #             sum(case when (hrt.month_create = '{m12}') and (hrt.year_create = '{y12}') then hrt.datuyen_tronghan end)
    #             as m12
    #             from tinh_trang_tuyen_dung hrt
    #
    #             union
    #
    #             select
    #             4 as sequence,
    #             'Số ứng viên đã tuyển, nhưng chậm (Overdeadline quantity)' as name,
    #             sum(case when (hrt.month_create = '{m1}') and (hrt.year_create = '{y1}') then hrt.datuyen_quahan end)
    #             as m1,
    #             sum(case when (hrt.month_create = '{m2}') and (hrt.year_create = '{y2}') then hrt.datuyen_quahan end)
    #             as m2,
    #             sum(case when (hrt.month_create = '{m3}') and (hrt.year_create = '{y3}') then hrt.datuyen_quahan end)
    #             as m3,
    #             sum(case when (hrt.month_create = '{m4}') and (hrt.year_create = '{y4}') then hrt.datuyen_quahan end)
    #             as m4,
    #             sum(case when (hrt.month_create = '{m5}') and (hrt.year_create = '{y5}') then hrt.datuyen_quahan end)
    #             as m5,
    #             sum(case when (hrt.month_create = '{m6}') and (hrt.year_create = '{y6}') then hrt.datuyen_quahan end)
    #             as m6,
    #             sum(case when (hrt.month_create = '{m7}') and (hrt.year_create = '{y7}') then hrt.datuyen_quahan end)
    #             as m7,
    #             sum(case when (hrt.month_create = '{m8}') and (hrt.year_create = '{y8}') then hrt.datuyen_quahan end)
    #             as m8,
    #             sum(case when (hrt.month_create = '{m9}') and (hrt.year_create = '{y9}') then hrt.datuyen_quahan end)
    #             as m9,
    #             sum(case when (hrt.month_create = '{m10}') and (hrt.year_create = '{y10}') then hrt.datuyen_quahan end)
    #             as m10,
    #             sum(case when (hrt.month_create = '{m11}') and (hrt.year_create = '{y11}') then hrt.datuyen_quahan end)
    #             as m11,
    #             sum(case when (hrt.month_create = '{m12}') and (hrt.year_create = '{y12}') then hrt.datuyen_quahan end)
    #             as m12
    #             from tinh_trang_tuyen_dung hrt
    #
    #             union
    #
    #             select
    #             5 as sequence,
    #             'Số ứng viên đang tuyển trong hạn (Ongoing quantity)' as name,
    #             sum(case when (hrt.month_create = '{m1}') and (hrt.year_create = '{y1}') then hrt.chuatuyen_tronghan end)
    #             as m1,
    #             sum(case when (hrt.month_create = '{m2}') and (hrt.year_create = '{y2}') then hrt.chuatuyen_tronghan end)
    #             as m2,
    #             sum(case when (hrt.month_create = '{m3}') and (hrt.year_create = '{y3}') then hrt.chuatuyen_tronghan end)
    #             as m3,
    #             sum(case when (hrt.month_create = '{m4}') and (hrt.year_create = '{y4}') then hrt.chuatuyen_tronghan end)
    #             as m4,
    #             sum(case when (hrt.month_create = '{m5}') and (hrt.year_create = '{y5}') then hrt.chuatuyen_tronghan end)
    #             as m5,
    #             sum(case when (hrt.month_create = '{m6}') and (hrt.year_create = '{y6}') then hrt.chuatuyen_tronghan end)
    #             as m6,
    #             sum(case when (hrt.month_create = '{m7}') and (hrt.year_create = '{y7}') then hrt.chuatuyen_tronghan end)
    #             as m7,
    #             sum(case when (hrt.month_create = '{m8}') and (hrt.year_create = '{y8}') then hrt.chuatuyen_tronghan end)
    #             as m8,
    #             sum(case when (hrt.month_create = '{m9}') and (hrt.year_create = '{y9}') then hrt.chuatuyen_tronghan end)
    #             as m9,
    #             sum(case when (hrt.month_create = '{m10}') and (hrt.year_create = '{y10}') then hrt.chuatuyen_tronghan end)
    #             as m10,
    #             sum(case when (hrt.month_create = '{m11}') and (hrt.year_create = '{y11}') then hrt.chuatuyen_tronghan end)
    #             as m11,
    #             sum(case when (hrt.month_create = '{m12}') and (hrt.year_create = '{y12}') then hrt.chuatuyen_tronghan end)
    #             as m12
    #             from tinh_trang_tuyen_dung hrt
    #
    #             union
    #
    #             select
    #             6 as sequence,
    #             'Số ứng viên đã quá hạn cần tuyển dụng (Delay quantity)' as name,
    #             sum(case when (hrt.month_create = '{m1}') and (hrt.year_create = '{y1}') then hrt.chuatuyen_quahan end)
    #             as m1,
    #             sum(case when (hrt.month_create = '{m2}') and (hrt.year_create = '{y2}') then hrt.chuatuyen_quahan end)
    #             as m2,
    #             sum(case when (hrt.month_create = '{m3}') and (hrt.year_create = '{y3}') then hrt.chuatuyen_quahan end)
    #             as m3,
    #             sum(case when (hrt.month_create = '{m4}') and (hrt.year_create = '{y4}') then hrt.chuatuyen_quahan end)
    #             as m4,
    #             sum(case when (hrt.month_create = '{m5}') and (hrt.year_create = '{y5}') then hrt.chuatuyen_quahan end)
    #             as m5,
    #             sum(case when (hrt.month_create = '{m6}') and (hrt.year_create = '{y6}') then hrt.chuatuyen_quahan end)
    #             as m6,
    #             sum(case when (hrt.month_create = '{m7}') and (hrt.year_create = '{y7}') then hrt.chuatuyen_quahan end)
    #             as m7,
    #             sum(case when (hrt.month_create = '{m8}') and (hrt.year_create = '{y8}') then hrt.chuatuyen_quahan end)
    #             as m8,
    #             sum(case when (hrt.month_create = '{m9}') and (hrt.year_create = '{y9}') then hrt.chuatuyen_quahan end)
    #             as m9,
    #             sum(case when (hrt.month_create = '{m10}') and (hrt.year_create = '{y10}') then hrt.chuatuyen_quahan end)
    #             as m10,
    #             sum(case when (hrt.month_create = '{m11}') and (hrt.year_create = '{y11}') then hrt.chuatuyen_quahan end)
    #             as m11,
    #             sum(case when (hrt.month_create = '{m12}') and (hrt.year_create = '{y12}') then hrt.chuatuyen_quahan end)
    #             as m12
    #             from tinh_trang_tuyen_dung hrt
    #         ) as master
    #         )""".format(
    #         table=self._table,
    #         m1=time['m12'].month, y1=time['m12'].year,
    #         m2=time['m11'].month, y2=time['m11'].year,
    #         m3=time['m10'].month, y3=time['m10'].year,
    #         m4=time['m9'].month, y4=time['m9'].year,
    #         m5=time['m8'].month, y5=time['m8'].year,
    #         m6=time['m7'].month, y6=time['m7'].year,
    #         m7=time['m6'].month, y7=time['m6'].year,
    #         m8=time['m5'].month, y8=time['m5'].year,
    #         m9=time['m4'].month, y9=time['m4'].year,
    #         m10=time['m3'].month, y10=time['m3'].year,
    #         m11=time['m2'].month, y11=time['m2'].year,
    #         m12=time['m1'].month, y12=time['m1'].year
    #     ))
