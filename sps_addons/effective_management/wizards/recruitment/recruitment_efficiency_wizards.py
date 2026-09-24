from collections import OrderedDict
import datetime as dt
from dateutil.relativedelta import relativedelta
from reportlab import xrange
from odoo import fields, api, models, tools


class RecruitmentEfficiencyWizards(models.TransientModel):
    _name = 'recruitment.efficiency.wizards'
    _description = 'Báo cáo hiệu quả tuyển dụng'

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
        current_year = int(self.year) -1
        self._cr.execute(
            "delete from recruitment_efficiency_report where master_key = {key}".format(key=self.master_key))
        sql = ''' with  hieu_qua_tuyen_dung as 
                            (select view_tong.year_datestart as year_createdate,
                                    view_tong.month_datestart as month_createdate,
                                    sum(view_tong.income_value)*12 as ngansachtuyendung,
                                    sum(view_tong.wage_actual)*12 as ngansachthucte,
                                    sum(view_tong.income_value)*12 - sum(view_tong.wage_actual)*12 as hieuquatuyendung
                            from 
                                (select hr_recruit_request.id as request_id,
                                        hr_recruit_request.create_date::date as ngaytaoyeucau,
                                        hr_recruit_request.date_start as ngaybatdaulamviec,
                                        hr_recruit_request.quantity as soluongtuyen,
                                        hr_recruit_request.state as request_state,
                                        hr_employee.id as employee_id,
                                        hr_employee.name as employee_name,
                                        view_firstcontract.datestart as ngayhopdongdautien,
                                        extract ('year' from view_firstcontract.datestart)::character varying as year_datestart,
                                        extract ('month' from view_firstcontract.datestart) as month_datestart,
                                        view_ngaynhanluongcuoi.ngaynhanluongcuoi as date_endcontract,
                                        hr_recruit_request.income_value,
                                        view_wage_actual.wage_actual,
                                        (case when view_ngaynhanluongcuoi.ngaynhanluongcuoi - view_firstcontract.datestart >= 365 then 1 else 0 end) as dieukienhople
                                from hr_employee
                                left join hr_applicant on hr_employee.x_cv_code = hr_applicant.id 
                                left join hr_recruit_request on hr_applicant.recruit_rq_id = hr_recruit_request.id
                                left join 
                                    (--Ngay ky hop dong dau tien cua nhan vien
                                    select 	hr_contract.employee_id,
                                            min(hr_contract.date_start) as datestart
                                    from hr_contract 
                                    where hr_contract.state not in ('cancel', 'draft')
                                    group by employee_id
                                    ) as view_firstcontract
                                on hr_employee.id = view_firstcontract.employee_id
                                left join 
                                    (--Luong thuc te cua nhan vien
                                    select 	view_firstcontract.employee_id,
                                            view_firstcontract.datestart,
                                            hr_contract.id as contract_id,
                                            (hr_contract.wage + hr_contract.x_allowance_phone) as wage_actual
                                    from
                                        (select hr_contract.employee_id,
                                                min(hr_contract.date_start) as datestart
                                        from hr_contract 
                                        where hr_contract.state not in ('cancel', 'draft') and x_contract_type not in ('hdtv','hddv')
                                        group by employee_id
                                        ) as view_firstcontract
                                    left join hr_contract on view_firstcontract.employee_id = hr_contract.employee_id and view_firstcontract.datestart = hr_contract.date_start
                                    where hr_contract.state not in ('cancel', 'draft')
                                    ) as view_wage_actual
                                on hr_employee.id = view_wage_actual.employee_id
                                left join 
                                    (--Ngay ket thuc hop dong
                                    select  view_base.employee_id,
                                            (case when current_date < view_base.ngaynhanluongcuoi then current_date else view_base.ngaynhanluongcuoi end) as ngaynhanluongcuoi
                                    from
                                        (select hr_contract.employee_id,
                                                max(hr_contract.date_end) as ngaynhanluongcuoi
                                        from hr_contract 
                                        where hr_contract.state not in ('cancel', 'draft')
                                        group by hr_contract.employee_id
                                        ) as view_base
                                    ) as view_ngaynhanluongcuoi
                                on hr_employee.id = view_ngaynhanluongcuoi.employee_id
                            ) as view_tong
                            where view_tong.dieukienhople = 1
                            group by  view_tong.year_datestart, view_tong.month_datestart
                            order by  view_tong.year_datestart, view_tong.month_datestart)
                select
                1 as sequence,
                'Tổng giá trị lương ngân sách tuyển dụng' as name,
                sum(case when ert.month_createdate = '1' and ert.year_createdate = '{y1}' then ert.ngansachtuyendung end)
                as m1,
                sum(case when ert.month_createdate = '2' and ert.year_createdate = '{y2}' then ert.ngansachtuyendung end)
                as m2,
                sum(case when ert.month_createdate = '3' and ert.year_createdate = '{y3}' then ert.ngansachtuyendung end)
                as m3,
                sum(case when ert.month_createdate = '4' and ert.year_createdate = '{y4}' then ert.ngansachtuyendung end)
                as m4,
                sum(case when ert.month_createdate = '5' and ert.year_createdate = '{y5}' then ert.ngansachtuyendung end)
                as m5,
                sum(case when ert.month_createdate = '6' and ert.year_createdate = '{y6}' then ert.ngansachtuyendung end)
                as m6,
                sum(case when ert.month_createdate = '7' and ert.year_createdate = '{y7}' then ert.ngansachtuyendung end)
                as m7,
                sum(case when ert.month_createdate = '8' and ert.year_createdate = '{y8}' then ert.ngansachtuyendung end)
                as m8,
                sum(case when ert.month_createdate = '9' and ert.year_createdate = '{y9}' then ert.ngansachtuyendung end)
                as m9,
                sum(case when ert.month_createdate = '10' and ert.year_createdate = '{y10}' then ert.ngansachtuyendung end)
                as m10,
                sum(case when ert.month_createdate = '11' and ert.year_createdate = '{y11}' then ert.ngansachtuyendung end)
                as m11,
                sum(case when ert.month_createdate = '12' and ert.year_createdate = '{y12}' then ert.ngansachtuyendung end)
                as m12
                from hieu_qua_tuyen_dung ert
                
                
                union
                
                select
                2 as sequence,
                'Tổng giá trị thu nhập ứng viên đã tuyển' as name,
                sum(case when ert.month_createdate = '1' and ert.year_createdate = '{y1}' then ert.ngansachthucte end)
                as m1,
                sum(case when ert.month_createdate = '2' and ert.year_createdate = '{y2}' then ert.ngansachthucte end)
                as m2,
                sum(case when ert.month_createdate = '3' and ert.year_createdate = '{y3}' then ert.ngansachthucte end)
                as m3,
                sum(case when ert.month_createdate = '4' and ert.year_createdate = '{y4}' then ert.ngansachthucte end)
                as m4,
                sum(case when ert.month_createdate = '5' and ert.year_createdate = '{y5}' then ert.ngansachthucte end)
                as m5,
                sum(case when ert.month_createdate = '6' and ert.year_createdate = '{y6}' then ert.ngansachthucte end)
                as m6,
                sum(case when ert.month_createdate = '7' and ert.year_createdate = '{y7}' then ert.ngansachthucte end)
                as m7,
                sum(case when ert.month_createdate = '8' and ert.year_createdate = '{y8}' then ert.ngansachthucte end)
                as m8,
                sum(case when ert.month_createdate = '9' and ert.year_createdate = '{y9}' then ert.ngansachthucte end)
                as m9,
                sum(case when ert.month_createdate = '10' and ert.year_createdate = '{y10}' then ert.ngansachthucte end)
                as m10,
                sum(case when ert.month_createdate = '11' and ert.year_createdate = '{y11}' then ert.ngansachthucte end)
                as m11,
                sum(case when ert.month_createdate = '12' and ert.year_createdate = '{y12}' then ert.ngansachthucte end)
                as m12
                from hieu_qua_tuyen_dung ert
                
                
                union 
                
                select
                3 as sequence,
                'Hiệu quả tuyển dụng' as name,
                sum(case when ert.month_createdate = '1' and ert.year_createdate = '{y1}' then  ert.hieuquatuyendung end)
                as m1,
                sum(case when ert.month_createdate = '2' and ert.year_createdate = '{y2}' then ert.hieuquatuyendung end)
                as m2,
                sum(case when ert.month_createdate = '3' and ert.year_createdate = '{y3}' then ert.hieuquatuyendung end)
                as m3,
                sum(case when ert.month_createdate = '4' and ert.year_createdate = '{y4}' then ert.hieuquatuyendung end)
                as m4,
                sum(case when ert.month_createdate = '5' and ert.year_createdate = '{y5}' then ert.hieuquatuyendung end)
                as m5,
                sum(case when ert.month_createdate = '6' and ert.year_createdate = '{y6}' then ert.hieuquatuyendung end)
                as m6,
                sum(case when ert.month_createdate = '7' and ert.year_createdate = '{y7}' then ert.hieuquatuyendung end)
                as m7,
                sum(case when ert.month_createdate = '8' and ert.year_createdate = '{y8}' then ert.hieuquatuyendung end)
                as m8,
                sum(case when ert.month_createdate = '9' and ert.year_createdate = '{y9}' then ert.hieuquatuyendung end)
                as m9,
                sum(case when ert.month_createdate = '10' and ert.year_createdate = '{y10}' then ert.hieuquatuyendung end)
                as m10,
                sum(case when ert.month_createdate = '11' and ert.year_createdate = '{y11}' then ert.hieuquatuyendung end)
                as m11,
                sum(case when ert.month_createdate = '12' and ert.year_createdate = '{y12}' then ert.hieuquatuyendung end)
                as m12
                from hieu_qua_tuyen_dung ert
            '''.format(
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
            y12=current_year,
        )
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()
        for r in recs:
            insert = '''INSERT INTO recruitment_efficiency_report (master_key,sequence,name ,m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12)
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
            'name': 'Báo cáo hiệu quả tuyển dụng',
            'view_mode': 'tree',
            'res_model': 'recruitment.efficiency.report',
            # 'context': {'year': current_year},
            'view_id': self.env.ref('effective_management.recruitment_efficiency_report_view').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }