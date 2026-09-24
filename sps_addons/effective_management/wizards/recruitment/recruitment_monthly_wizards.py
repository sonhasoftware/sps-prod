from collections import OrderedDict
import datetime as dt
from dateutil.relativedelta import relativedelta
from reportlab import xrange
from odoo import fields, api, models, tools


class ReportRecruitmentMonthly(models.Model):
    _name = 'recruitment.monthly.wizards'
    _description = 'Recruitment Monthly'

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
    year = fields.Selection(
        selection='years_selection',
        string="Năm",
        default=str(dt.datetime.now().year), required=True)

    def years_selection(self):
        y = dt.datetime.now().year
        year_list = []
        while y != 1939:
            year_list.append((str(y), str(y)))
            y -= 1
        return year_list

    def action_report(self):
        current_year = self.year
        self._cr.execute(
            "delete from report_recruitment_monthly where master_key = {key}".format(key=self.master_key))
        self._cr.execute(""" with tinh_trang_tuyen_dung as 
                        (select view_reportrecruitmentsatus.year_datestart as year_create,
                                view_reportrecruitmentsatus.month_datestart as month_create,
                                sum(view_reportrecruitmentsatus.quantity_yeucautuyendung) as quantity_yeucautuyendung,
                                sum(view_reportrecruitmentsatus.quantity_cancel) as quantity_cancel,
                                sum(view_reportrecruitmentsatus.datuyen_tronghan) as datuyen_tronghan,
                                sum(view_reportrecruitmentsatus.datuyen_quahan) as datuyen_quahan,
                                sum(view_reportrecruitmentsatus.chuatuyen_tronghan) as chuatuyen_tronghan,
                                sum(view_reportrecruitmentsatus.chuatuyen_quahan) as chuatuyen_quahan
                        from
                            (select view_slgyeucautuyendung.year_datestart,
                                    view_slgyeucautuyendung.month_datestart,
                                    (sum(case when view_slgyeucautuyendung.state not in ('draft','canceled') then view_slgyeucautuyendung.quantity else 0 end) + sum(case when view_slgyeucautuyendung.state = 'canceled' then view_slgyeucautuyendung.quantity_datuyen else 0 end)) as quantity_yeucautuyendung,
                                    (sum(case when view_slgyeucautuyendung.state = 'canceled' and view_slgyeucautuyendung.quantity_datuyen = 0 then view_slgyeucautuyendung.quantity else 0 end) + sum(case when view_slgyeucautuyendung.state = 'canceled' and view_slgyeucautuyendung.quantity_datuyen > 0 then view_slgyeucautuyendung.quantity_chuatuyen else 0 end)) as quantity_cancel,
                                    0 as datuyen_tronghan,
                                    0 as datuyen_quahan,
                                    0 as chuatuyen_tronghan,
                                    0 as chuatuyen_quahan
                            from
                                (select hr_recruit_request.id as request_id,
                                        hr_recruit_request.state,
                                        hr_recruit_request.create_date,
                                        hr_recruit_request.date_start,
                                        extract ('year' from hr_recruit_request.date_start)::character varying as year_datestart,
                                        extract ('month' from hr_recruit_request.date_start) as month_datestart,
                                        current_date,
                                        hr_recruit_request.quantity,
                                        coalesce(view_ungviendatuyen.quantity_datuyen,0) as quantity_datuyen,
                                        (hr_recruit_request.quantity - coalesce(view_ungviendatuyen.quantity_datuyen,0)) as quantity_chuatuyen
                                from hr_recruit_request 	
                                left join 
                                    (select view_tinhtrangtuyendung.recruit_rq_id,
                                            count(contract_id) as quantity_datuyen
                                    from
                                        (select view_requestid.contract_id,
                                                view_requestid.employee_id, 
                                                view_requestid.employee_name,
                                                view_requestid.date_start,
                                                view_requestid.first_date_start,
                                                view_requestid.x_cv_code,
                                                view_requestid.recruit_rq_id,
                                                hr_recruit_request.create_date,
                                                hr_recruit_request.date_start as rr_date_start
                                        from
                                            (select view_cvcode.contract_id,
                                                    view_cvcode.employee_id, 
                                                    view_cvcode.employee_name, 
                                                    view_cvcode.date_start,
                                                    view_cvcode.first_date_start,
                                                    view_cvcode.x_cv_code,
                                                    hr_applicant.recruit_rq_id 
                                            from
                                                (select view_base.contract_id,
                                                        view_base.employee_id,
                                                        hr_employee.name as employee_name,
                                                        view_base.date_start,
                                                        view_base.first_date_start,
                                                        hr_employee.x_cv_code 
                                                from
                                                    (select hr_contract.id as contract_id,
                                                            hr_contract.employee_id, 		
                                                            hr_contract.date_start,
                                                            view_firstdatestart.first_date_start
                                                    from hr_contract
                                                    left join
                                                        (select employee_id, 
                                                                min(date_start) as first_date_start
                                                        from hr_contract 
                                                        where state in ('open', 'close')
                                                        group by employee_id
                                                        order by employee_id 
                                                        ) as view_firstdatestart		
                                                    on hr_contract.employee_id = view_firstdatestart.employee_id
                                                    where date_start = first_date_start
                                                    and hr_contract.state in ('open', 'close')
                                                    order by employee_id
                                                    ) as view_base
                                                left join hr_employee on view_base.employee_id = hr_employee.id
                                                ) as view_cvcode
                                            left join hr_applicant on view_cvcode.x_cv_code = hr_applicant.id
                                            ) as view_requestid
                                        left join hr_recruit_request on hr_recruit_request.id = view_requestid.recruit_rq_id
                                        order by contract_id
                                        ) as view_tinhtrangtuyendung
                                    group by view_tinhtrangtuyendung.recruit_rq_id
                                    ) as view_ungviendatuyen
                                on hr_recruit_request.id = view_ungviendatuyen.recruit_rq_id
                                order by request_id desc
                                ) as view_slgyeucautuyendung
                            group by view_slgyeucautuyendung.year_datestart, view_slgyeucautuyendung.month_datestart
                            
                            union all 
                            
                            select 	view_quantitydatuyen.year_datestart,
                                    view_quantitydatuyen.month_datestart,
                                    0 as quantity_yeucautuyendung,
                                    0 as quantity_cancel,
                                    count(case when view_quantitydatuyen.date_start <= view_quantitydatuyen.rr_date_start then 1 end) as datuyen_tronghan,
                                    count(case when view_quantitydatuyen.date_start > view_quantitydatuyen.rr_date_start then 1 end) as datuyen_quahan,
                                    0 as chuatuyen_tronghan,
                                    0 as chuatuyen_quahan
                            from
                                (select hr_recruit_request.create_date,
                                        hr_recruit_request.date_start as date_onboard,
                                        extract ('year' from hr_recruit_request.date_start)::character varying as year_datestart,
                                        extract ('month' from hr_recruit_request.date_start) as month_datestart,	
                                        view_requestid.contract_id,
                                        view_requestid.employee_id, 
                                        view_requestid.employee_name,
                                        view_requestid.date_start,
                                        view_requestid.first_date_start,
                                        view_requestid.x_cv_code,
                                        view_requestid.recruit_rq_id,	
                                        hr_recruit_request.date_start as rr_date_start
                                from
                                    (select view_cvcode.contract_id,
                                            view_cvcode.employee_id, 
                                            view_cvcode.employee_name, 
                                            view_cvcode.date_start,
                                            view_cvcode.first_date_start,
                                            view_cvcode.x_cv_code,
                                            hr_applicant.recruit_rq_id 
                                    from
                                        (select view_base.contract_id,
                                                view_base.employee_id,
                                                hr_employee.name as employee_name,
                                                view_base.date_start,
                                                view_base.first_date_start,
                                                hr_employee.x_cv_code 
                                        from
                                            (select hr_contract.id as contract_id,
                                                    hr_contract.employee_id, 		
                                                    hr_contract.date_start,
                                                    view_firstdatestart.first_date_start
                                            from hr_contract
                                            left join
                                                (select employee_id, 
                                                        min(date_start) as first_date_start
                                                from hr_contract 
                                                where state in ('open', 'close')
                                                group by employee_id
                                                order by employee_id 
                                                ) as view_firstdatestart		
                                            on hr_contract.employee_id = view_firstdatestart.employee_id
                                            where date_start = first_date_start
                                            and hr_contract.state in ('open', 'close')
                                            order by employee_id
                                            ) as view_base
                                        left join hr_employee 
                                        on view_base.employee_id = hr_employee.id
                                        ) as view_cvcode
                                    left join hr_applicant on view_cvcode.x_cv_code = hr_applicant.id
                                    ) as view_requestid
                                left join hr_recruit_request on hr_recruit_request.id = view_requestid.recruit_rq_id
                                order by contract_id
                                ) as view_quantitydatuyen
                            group by view_quantitydatuyen.year_datestart, view_quantitydatuyen.month_datestart
                            
                            union all 
                            
                            select 	view_tonghop.year_datestart,
                                    view_tonghop.month_datestart,
                                    0 as quantity_yeucautuyendung,
                                    0 as quantity_cancel,
                                    0 as datuyen_tronghan,
                                    0 as datuyen_quahan,
                                    sum (case when view_tonghop.date_start >= current_date then quantity_chuatuyen else 0 end) as chuatuyen_tronghan,
                                    sum (case when view_tonghop.date_start < current_date then quantity_chuatuyen else 0 end) as chuatuyen_quahan
                            from
                                (select hr_recruit_request.id as request_id,
                                        hr_recruit_request.state,
                                        hr_recruit_request.create_date,
                                        hr_recruit_request.date_start,
                                        extract ('year' from hr_recruit_request.date_start)::character varying as year_datestart,
                                        extract ('month' from hr_recruit_request.date_start) as month_datestart,	
                                        current_date,
                                        hr_recruit_request.quantity,
                                        coalesce(view_ungviendatuyen.quantity_datuyen,0) as quantity_datuyen,
                                        (hr_recruit_request.quantity - coalesce(view_ungviendatuyen.quantity_datuyen,0)) as quantity_chuatuyen
                                from hr_recruit_request 	
                                left join 
                                    (select view_tinhtrangtuyendung.recruit_rq_id,
                                            count(contract_id) as quantity_datuyen
                                    from
                                        (select view_requestid.contract_id,
                                                view_requestid.employee_id, 
                                                view_requestid.employee_name,
                                                view_requestid.date_start,
                                                view_requestid.first_date_start,
                                                view_requestid.x_cv_code,
                                                view_requestid.recruit_rq_id,
                                                hr_recruit_request.create_date,
                                                hr_recruit_request.date_start as rr_date_start
                                        from
                                            (select view_cvcode.contract_id,
                                                    view_cvcode.employee_id, 
                                                    view_cvcode.employee_name, 
                                                    view_cvcode.date_start,
                                                    view_cvcode.first_date_start,
                                                    view_cvcode.x_cv_code,
                                                    hr_applicant.recruit_rq_id 
                                            from
                                                (select view_base.contract_id,
                                                        view_base.employee_id,
                                                        hr_employee.name as employee_name,
                                                        view_base.date_start,
                                                        view_base.first_date_start,
                                                        hr_employee.x_cv_code 
                                                from
                                                    (select hr_contract.id as contract_id,
                                                            hr_contract.employee_id, 		
                                                            hr_contract.date_start,
                                                            view_firstdatestart.first_date_start
                                                    from hr_contract
                                                    left join
                                                        (select employee_id, 
                                                                min(date_start) as first_date_start
                                                        from hr_contract 
                                                        where state in ('open', 'close')
                                                        group by employee_id
                                                        order by employee_id 
                                                        ) as view_firstdatestart		
                                                    on hr_contract.employee_id = view_firstdatestart.employee_id
                                                    where date_start = first_date_start
                                                    and hr_contract.state in ('open', 'close')
                                                    order by employee_id
                                                    ) as view_base
                                                left join hr_employee on view_base.employee_id = hr_employee.id
                                                ) as view_cvcode
                                            left join hr_applicant on view_cvcode.x_cv_code = hr_applicant.id
                                            ) as view_requestid
                                        left join hr_recruit_request on hr_recruit_request.id = view_requestid.recruit_rq_id
                                        order by contract_id
                                        ) as view_tinhtrangtuyendung
                                    group by view_tinhtrangtuyendung.recruit_rq_id
                                    ) as view_ungviendatuyen
                                on hr_recruit_request.id = view_ungviendatuyen.recruit_rq_id
                                where hr_recruit_request.state not in ('draft', 'canceled')
                                order by request_id desc
                                ) view_tonghop
                            group by view_tonghop.year_datestart, view_tonghop.month_datestart
                            ) as view_reportrecruitmentsatus
                        group by view_reportrecruitmentsatus.year_datestart, view_reportrecruitmentsatus.month_datestart
                        order by view_reportrecruitmentsatus.year_datestart, view_reportrecruitmentsatus.month_datestart)
                select
                1 as sequence,
                'Số ứng viên yêu cầu tuyển dụng (Requested quantity)' as name,
                sum(case when (hrt.month_create = '1') and (hrt.year_create = '{y1}') then hrt.quantity_yeucautuyendung end)
                as m1,
                sum(case when (hrt.month_create = '2') and (hrt.year_create = '{y2}') then hrt.quantity_yeucautuyendung end)
                as m2,
                sum(case when (hrt.month_create = '3') and (hrt.year_create = '{y3}') then hrt.quantity_yeucautuyendung end)
                as m3,
                sum(case when (hrt.month_create = '4') and (hrt.year_create = '{y4}') then hrt.quantity_yeucautuyendung end)
                as m4,
                sum(case when (hrt.month_create = '5') and (hrt.year_create = '{y5}') then hrt.quantity_yeucautuyendung end)
                as m5,
                sum(case when (hrt.month_create = '6') and (hrt.year_create = '{y6}') then hrt.quantity_yeucautuyendung end)
                as m6,
                sum(case when (hrt.month_create = '7') and (hrt.year_create = '{y7}') then hrt.quantity_yeucautuyendung end)
                as m7,
                sum(case when (hrt.month_create = '8') and (hrt.year_create = '{y8}') then hrt.quantity_yeucautuyendung end)
                as m8,
                sum(case when (hrt.month_create = '9') and (hrt.year_create = '{y9}') then hrt.quantity_yeucautuyendung end)
                as m9,
                sum(case when (hrt.month_create = '10') and (hrt.year_create = '{y10}') then hrt.quantity_yeucautuyendung end)
                as m10,
                sum(case when (hrt.month_create = '11') and (hrt.year_create = '{y11}') then hrt.quantity_yeucautuyendung end)
                as m11,
                sum(case when (hrt.month_create = '12') and (hrt.year_create = '{y12}') then hrt.quantity_yeucautuyendung end)
                as m12
                from tinh_trang_tuyen_dung hrt
                
                union
                
                select
                2 as sequence,
                'Số ứng viên tuyển dụng bị hủy (Cancelled quantity)' as name,
                sum(case when (hrt.month_create = '1') and (hrt.year_create = '{y1}') then hrt.quantity_cancel end)
                as m1,
                sum(case when (hrt.month_create = '2') and (hrt.year_create = '{y2}') then hrt.quantity_cancel end)
                as m2,
                sum(case when (hrt.month_create = '3') and (hrt.year_create = '{y3}') then hrt.quantity_cancel end)
                as m3,
                sum(case when (hrt.month_create = '4') and (hrt.year_create = '{y4}') then hrt.quantity_cancel end)
                as m4,
                sum(case when (hrt.month_create = '5') and (hrt.year_create = '{y5}') then hrt.quantity_cancel end)
                as m5,
                sum(case when (hrt.month_create = '6') and (hrt.year_create = '{y6}') then hrt.quantity_cancel end)
                as m6,
                sum(case when (hrt.month_create = '7') and (hrt.year_create = '{y7}') then hrt.quantity_cancel end)
                as m7,
                sum(case when (hrt.month_create = '8') and (hrt.year_create = '{y8}') then hrt.quantity_cancel end)
                as m8,
                sum(case when (hrt.month_create = '9') and (hrt.year_create = '{y9}') then hrt.quantity_cancel end)
                as m9,
                sum(case when (hrt.month_create = '10') and (hrt.year_create = '{y10}') then hrt.quantity_cancel end)
                as m10,
                sum(case when (hrt.month_create = '11') and (hrt.year_create = '{y11}') then hrt.quantity_cancel end)
                as m11,
                sum(case when (hrt.month_create = '12') and (hrt.year_create = '{y12}') then hrt.quantity_cancel end)
                as m12
                from tinh_trang_tuyen_dung hrt
                
                union 
                
                select
                3 as sequence,
                'Số ứng viên được tuyển trong thời hạn (Done quantity)' as name,
                sum(case when (hrt.month_create = '1') and (hrt.year_create = '{y1}') then hrt.datuyen_tronghan end)
                as m1,
                sum(case when (hrt.month_create = '2') and (hrt.year_create = '{y2}') then hrt.datuyen_tronghan end)
                as m2,
                sum(case when (hrt.month_create = '3') and (hrt.year_create = '{y3}') then hrt.datuyen_tronghan end)
                as m3,
                sum(case when (hrt.month_create = '4') and (hrt.year_create = '{y4}') then hrt.datuyen_tronghan end)
                as m4,
                sum(case when (hrt.month_create = '5') and (hrt.year_create = '{y5}') then hrt.datuyen_tronghan end)
                as m5,
                sum(case when (hrt.month_create = '6') and (hrt.year_create = '{y6}') then hrt.datuyen_tronghan end)
                as m6,
                sum(case when (hrt.month_create = '7') and (hrt.year_create = '{y7}') then hrt.datuyen_tronghan end)
                as m7,
                sum(case when (hrt.month_create = '8') and (hrt.year_create = '{y8}') then hrt.datuyen_tronghan end)
                as m8,
                sum(case when (hrt.month_create = '9') and (hrt.year_create = '{y9}') then hrt.datuyen_tronghan end)
                as m9,
                sum(case when (hrt.month_create = '10') and (hrt.year_create = '{y10}') then hrt.datuyen_tronghan end)
                as m10,
                sum(case when (hrt.month_create = '11') and (hrt.year_create = '{y11}') then hrt.datuyen_tronghan end)
                as m11,
                sum(case when (hrt.month_create = '12') and (hrt.year_create = '{y12}') then hrt.datuyen_tronghan end)
                as m12
                from tinh_trang_tuyen_dung hrt
                
                union 
                
                select
                4 as sequence,
                'Số ứng viên đã tuyển, nhưng chậm (Overdeadline quantity)' as name,
                sum(case when (hrt.month_create = '1') and (hrt.year_create = '{y1}') then hrt.datuyen_quahan end)
                as m1,
                sum(case when (hrt.month_create = '2') and (hrt.year_create = '{y2}') then hrt.datuyen_quahan end)
                as m2,
                sum(case when (hrt.month_create = '3') and (hrt.year_create = '{y3}') then hrt.datuyen_quahan end)
                as m3,
                sum(case when (hrt.month_create = '4') and (hrt.year_create = '{y4}') then hrt.datuyen_quahan end)
                as m4,
                sum(case when (hrt.month_create = '5') and (hrt.year_create = '{y5}') then hrt.datuyen_quahan end)
                as m5,
                sum(case when (hrt.month_create = '6') and (hrt.year_create = '{y6}') then hrt.datuyen_quahan end)
                as m6,
                sum(case when (hrt.month_create = '7') and (hrt.year_create = '{y7}') then hrt.datuyen_quahan end)
                as m7,
                sum(case when (hrt.month_create = '8') and (hrt.year_create = '{y8}') then hrt.datuyen_quahan end)
                as m8,
                sum(case when (hrt.month_create = '9') and (hrt.year_create = '{y9}') then hrt.datuyen_quahan end)
                as m9,
                sum(case when (hrt.month_create = '10') and (hrt.year_create = '{y10}') then hrt.datuyen_quahan end)
                as m10,
                sum(case when (hrt.month_create = '11') and (hrt.year_create = '{y11}') then hrt.datuyen_quahan end)
                as m11,
                sum(case when (hrt.month_create = '12') and (hrt.year_create = '{y12}') then hrt.datuyen_quahan end)
                as m12
                from tinh_trang_tuyen_dung hrt
    
                union 
                
                select
                5 as sequence,
                'Số ứng viên đang tuyển trong hạn (Ongoing quantity)' as name,
                sum(case when (hrt.month_create = '1') and (hrt.year_create = '{y1}') then hrt.chuatuyen_tronghan end)
                as m1,
                sum(case when (hrt.month_create = '2') and (hrt.year_create = '{y2}') then hrt.chuatuyen_tronghan end)
                as m2,
                sum(case when (hrt.month_create = '3') and (hrt.year_create = '{y3}') then hrt.chuatuyen_tronghan end)
                as m3,
                sum(case when (hrt.month_create = '4') and (hrt.year_create = '{y4}') then hrt.chuatuyen_tronghan end)
                as m4,
                sum(case when (hrt.month_create = '5') and (hrt.year_create = '{y5}') then hrt.chuatuyen_tronghan end)
                as m5,
                sum(case when (hrt.month_create = '6') and (hrt.year_create = '{y6}') then hrt.chuatuyen_tronghan end)
                as m6,
                sum(case when (hrt.month_create = '7') and (hrt.year_create = '{y7}') then hrt.chuatuyen_tronghan end)
                as m7,
                sum(case when (hrt.month_create = '8') and (hrt.year_create = '{y8}') then hrt.chuatuyen_tronghan end)
                as m8,
                sum(case when (hrt.month_create = '9') and (hrt.year_create = '{y9}') then hrt.chuatuyen_tronghan end)
                as m9,
                sum(case when (hrt.month_create = '10') and (hrt.year_create = '{y10}') then hrt.chuatuyen_tronghan end)
                as m10,
                sum(case when (hrt.month_create = '11') and (hrt.year_create = '{y11}') then hrt.chuatuyen_tronghan end)
                as m11,
                sum(case when (hrt.month_create = '12') and (hrt.year_create = '{y12}') then hrt.chuatuyen_tronghan end)
                as m12
                from tinh_trang_tuyen_dung hrt
                
                union 
                
                select
                6 as sequence,
                'Số ứng viên đã quá hạn cần tuyển dụng (Delay quantity)' as name,
                sum(case when (hrt.month_create = '1') and (hrt.year_create = '{y1}') then hrt.chuatuyen_quahan end)
                as m1,
                sum(case when (hrt.month_create = '2') and (hrt.year_create = '{y2}') then hrt.chuatuyen_quahan end)
                as m2,
                sum(case when (hrt.month_create = '3') and (hrt.year_create = '{y3}') then hrt.chuatuyen_quahan end)
                as m3,
                sum(case when (hrt.month_create = '4') and (hrt.year_create = '{y4}') then hrt.chuatuyen_quahan end)
                as m4,
                sum(case when (hrt.month_create = '5') and (hrt.year_create = '{y5}') then hrt.chuatuyen_quahan end)
                as m5,
                sum(case when (hrt.month_create = '6') and (hrt.year_create = '{y6}') then hrt.chuatuyen_quahan end)
                as m6,
                sum(case when (hrt.month_create = '7') and (hrt.year_create = '{y7}') then hrt.chuatuyen_quahan end)
                as m7,
                sum(case when (hrt.month_create = '8') and (hrt.year_create = '{y8}') then hrt.chuatuyen_quahan end)
                as m8,
                sum(case when (hrt.month_create = '9') and (hrt.year_create = '{y9}') then hrt.chuatuyen_quahan end)
                as m9,
                sum(case when (hrt.month_create = '10') and (hrt.year_create = '{y10}') then hrt.chuatuyen_quahan end)
                as m10,
                sum(case when (hrt.month_create = '11') and (hrt.year_create = '{y11}') then hrt.chuatuyen_quahan end)
                as m11,
                sum(case when (hrt.month_create = '12') and (hrt.year_create = '{y12}') then hrt.chuatuyen_quahan end)
                as m12
                from tinh_trang_tuyen_dung hrt
            """.format(
            table=self._table,
             y1=current_year,
             y2=current_year,
             y3=current_year,
             y4=current_year,
             y5=current_year,
             y6=current_year,
             y7=current_year,
             y8=current_year,
             y9=current_year,
             y10=current_year,
             y11=current_year,
             y12=current_year
        ))
        
        recs = self._cr.dictfetchall()
        for r in recs:
            insert = '''INSERT INTO report_recruitment_monthly (master_key,sequence,name ,m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12)
                                                       VALUES ({key},{sequence},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                                   '''.format(key=self.master_key,
                                                              classification=r['name'],
                                                              sequence=r['sequence'],
                                                              t1=r['m1'] or 0,
                                                              t2=r['m2'] or 0,
                                                              t3=r['m3'] or 0,
                                                              t4=r['m4'] or 0,
                                                              t5=r['m5'] or 0,
                                                              t6=r['m6'] or 0,
                                                              t7=r['m7'] or 0,
                                                              t8=r['m8'] or 0,
                                                              t9=r['m9'] or 0,
                                                              t10=r['m10'] or 0,
                                                              t11=r['m11'] or 0,
                                                              t12=r['m12'] or 0, )
            self._cr.execute(insert)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo tình trạng tuyển dụng',
            'view_mode': 'tree',
            'res_model': 'report.recruitment.monthly',
            # 'context': {'year': current_year},
            'view_id': self.env.ref('effective_management.report_recruitment_monthly_view').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }