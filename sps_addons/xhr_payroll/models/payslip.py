# -*- coding: utf-8 -*-
import calendar
from datetime import datetime, date
from calendar import monthrange
import logging
from dateutil.relativedelta import relativedelta

import base64
import os
from io import BytesIO
import openpyxl
from openpyxl.writer.excel import save_virtual_workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from . import num2vnd

from odoo import models, fields, api, _
from odoo.exceptions import UserError, MissingError, ValidationError
_logger = logging.getLogger(__name__)




class Contract(models.Model):
    _inherit = 'hr.contract'

    def _generate_work_entries(self, date_start, date_stop):
        return self.env['hr.work.entry']


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        res = super(HrPayslipEmployees, self.with_context(x_generate_batch_payslip=True)).compute_sheet()
        # Sinh đánh giá KPI cho đợt lương ngay sau khi phiếu lương đã tạo & tính xong
        payslip_run = False
        if self.env.context.get('active_id'):
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
        elif isinstance(res, dict) and res.get('res_model') == 'hr.payslip.run' and res.get('res_id'):
            payslip_run = self.env['hr.payslip.run'].browse(res['res_id'])
        if payslip_run and payslip_run.exists():
            self.env['hr.kpi.evaluation'].generate_for_run(payslip_run)
        return res

    def _check_undefined_slots(self, work_entries, payslip_run):
        pass


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    x_amount_total = fields.Monetary('Total amount', compute='compute_amount_total', store=1, copy=0)
    x_hot_bonus = fields.Monetary('Thưởng nóng', readonly=1)
    x_other_bonus = fields.Monetary('Thưởng và các khoản thu nhập khác', readonly=1)

    def action_payslip_cancel(self):
        # if self.filtered(lambda slip: slip.state == 'done'):
        #     raise UserError(_("Cannot cancel a payslip that is done."))
        self.write({'state': 'cancel'})
        self.mapped('payslip_run_id').action_close()

    def get_amount_text(self):
        self.ensure_one()
        return num2vnd.num2word(self.x_amount_total)

    def merge_data(self,listGenerals):
        merged_generals = {}
        for record in listGenerals:
            manhanvien = record['manhanvien']
            if manhanvien in merged_generals:
                # Cộng tổng các giá trị số
                for key, value in record.items():
                    if key in ['hovaten', 'manhanvien', 'chucvu']:
                        continue
                    elif isinstance(value, (int, float)) and value is not None:
                        merged_generals[manhanvien][key] = (merged_generals[manhanvien].get(key, 0) or 0) + value
                    elif merged_generals[manhanvien].get(key) is None:
                        merged_generals[manhanvien][key] = value
            else:
                merged_generals[manhanvien] = record.copy()

        listGenerals = list(merged_generals.values())
        return  listGenerals
    
    # def count_number_off_holiday(self, date_from, date_to):
    #     number_off_holiday = 0
        
    #     for i in range((date_to - date_from).days + 1):

    # get_holiday_out_contract(l['manhanvien'], month, year)

    def get_holiday_out_contract(self, manhanvien, month, year):
        """
        Tính số giờ nghỉ phép mà nhân viên không được hưởng do nằm ngoài thời gian hợp đồng
        """
        employee_id = self.env['hr.employee'].search([
            ('x_code', '=', manhanvien), 
            ('active', 'in', [True, False])
        ], limit=1)
        
        if not employee_id:
            return 0

        start_of_month = date(year, int(month), 1)
        last_day = calendar.monthrange(year, int(month))[1]
        end_of_month = date(year, int(month), last_day)

        contract_all_ids = employee_id._get_contracts(start_of_month, end_of_month, states=['open', 'close'])
        if not contract_all_ids:
            return 0
        contract_ids = contract_all_ids.filtered(lambda c: c.x_type_employee == '1')
        old_contract_end = min(contract_ids.mapped('date_end')) if contract_ids.filtered('date_end') else None
        current_contract = employee_id.contract_id
        
        if not current_contract:
            return 0

        total_holiday_days = 0

        if (current_contract.date_end and
            start_of_month <= current_contract.date_end <= end_of_month):
            
            total_holiday_days += self._calculate_holiday_days_after_contract_end(
                current_contract.date_end, start_of_month, end_of_month
            )

        if (old_contract_end and current_contract.date_start and
            current_contract.date_start > old_contract_end and
            start_of_month <= current_contract.date_start <= end_of_month and
            start_of_month <= old_contract_end <= end_of_month):
            
            total_holiday_days += self._calculate_holiday_days_between_contracts(
                old_contract_end, current_contract.date_start
            )

        contract_collaborators_ids = contract_all_ids.filtered(lambda c: c.x_type_employee == '2')
        for contact in contract_collaborators_ids:
            if contact.date_end and contact.date_start:
                global_holidays = self.env['hr.global.off'].search([
                    ('date_start', '>=', start_of_month),
                    ('date_end', '<=', end_of_month),
                    ('date_start', '>=', contact.date_start),
                    ('date_end', '<=', contact.date_end),
                ])
                for holi in global_holidays:
                    total_holiday_days+= (holi.date_end - holi.date_start).days +1

        return total_holiday_days * 8

    def _calculate_holiday_days_after_contract_end(self, contract_end_date, start_of_month, end_of_month):
        """
        Tính số ngày nghỉ phép sau khi hợp đồng kết thúc
        """
        holiday_days = 0
        
        global_holidays = self.env['hr.global.off'].search([
            ('date_start', '<=', contract_end_date),
            ('date_end', '>=', contract_end_date),
            ('date_start', '<=', end_of_month),
            ('date_end', '>=', start_of_month),
        ])
        
        for holiday in global_holidays:
            days_after_contract = (holiday.date_end - contract_end_date).days
            if days_after_contract > 0:
                holiday_days += days_after_contract
                
        return holiday_days

    def _calculate_holiday_days_between_contracts(self, old_contract_end, new_contract_start):
        """
        Tính số ngày nghỉ phép trong khoảng trống giữa 2 hợp đồng
        """
        holiday_days = 0
        
        global_holidays = self.env['hr.global.off'].search([
            ('date_start', '<=', old_contract_end),
            ('date_end', '>=', new_contract_start),
        ])
        
        for holiday in global_holidays:
            gap_start = max(holiday.date_start, old_contract_end + relativedelta(days=1))
            gap_end = min(holiday.date_end, new_contract_start)
            
            if gap_start <= gap_end:
                gap_days = (gap_end - gap_start).days
                holiday_days += gap_days
                
        return holiday_days

    def _calculate_aj_ak_values(self, data):
        """
        TH1: N/I >= 1
        - AJ = IF(G-((X-G)*0.15)>0, G-((X-G)*0.15), 0)
        - AK = X-AJ-F

        TH2: N/I < 1
        - AJ = IF(G*N/I-((X-G*N/I)*0.15)>0, G*N/I-((X-G*N/I)*0.15), 0)
        - AK = X-AJ-F*N/I
        """
        # Extract and convert values to float, handle None/empty values
        n = float(data.get('tonggiocongthucte', 0) or 0)  # N - actual working hours
        i = float(data.get('giocongcoso', 1) or 1)  # I - base working hours (avoid division by zero)
        z = float(data.get('tongthunhap', 0) or 0) + float(data.get('thuongnong', 0) or 0)  # X - total income
        g = float(data.get('nhao', 0) or 0)  # G - housing allowance
        f = float(data.get('antrua', 0) or 0)

        ratio = n / i if i != 0 else 0
        if ratio >= 1:
            aj_calculation = g - ((z - g) * 0.15)
            aj = max(aj_calculation, 0)

            ak = z - aj - f

        else:
            g_adjusted = g * ratio
            aj_calculation = g_adjusted - ((z - g_adjusted) * 0.15)
            aj = max(aj_calculation, 0)

            f_adjusted = f * ratio
            ak = z - aj - f_adjusted

        return aj, ak

    # tạo bảng chi phí nhân công
    def _get_wage_cost_data(self):
        """Chạy 1 query tổng hợp chi phí nhân công/khoản phúc lợi (thưởng tháng 13,
        đồng phục, khám sức khỏe, thưởng ngày lễ, du lịch, công đoàn...) cho phiếu
        lương self — dùng chung bởi create_wage_cost_actual() (đơn giá nhân công)
        và báo cáo SALARY NEW (cột Thưởng tháng 13 .. Tổng số giờ công thực tế).

        Trả về (data, tong_chi_phi, paidleave, gio_cong_thuc_te); data=None nếu
        phiếu không khớp query (không có contract/không đúng tháng-năm).
        """
        self.ensure_one()
        date_from = self.date_from
        month = date_from.month
        year = date_from.year
        _, num_days = calendar.monthrange(year, int(month))

        queryGeneral = """
                        select
                  he.name hovaten,
                  he.x_code manhanvien,
                  he.job_title chucvu,
                  hc.x_insurance_wage luongchinh,
                  case when hc.x_type_employee = '2' then 1 else 0 end as is_intern,
                  hc.x_allowance_lunch antrua,
                  hc.x_allowance_home nhao,
                  hc.wage tongthunhaptheohd,
                  x5.amount giocongcoso,
                  case when resource.hours_per_week = 44 then 1 else 0 end as hours_per_week44,
              (select coalesce(sum(hgo.saturdays),0) as saturdays
              from hr_global_off hgo
                        where hgo.active = true
                        and (hgo.date_start <= '{1}-{0}-{3}' AND hgo.date_end >= '{1}-{0}-01')

                ),
                  case when hc.wage = 0 or hc.wage is null then hc.hourly_wage else hc.wage/x5.amount end as dongia,
                  case when hdb.name = 'General' then x2.amount else 0 end as Generall,
                  case when hdb.name = 'Maintenenance & Services' then x2.amount else 0  end as MaintenenanceServices,
                  case when hdb.name = 'Facility Management' then x2.amount else 0  end as FacilityManagement,
                  X2.amount tonggiocongthucte,
                  hpl4.total luongbosung,
                  case when hdb.name = 'General'
                      then
                           hpl5.total
                       else 0
                   end as ThuNhapGenerall,
                   case when hdb.name = 'Maintenenance & Services'
                      then
                           hpl5.total
                       else 0
                   end as ThuNhapMaintenenanceServices,
                    case when hdb.name = 'Facility Management'
                      then
                           hpl5.total
                       else 0
                   end as ThuNhapFacilityManagement,
                  coalesce(hpl5.total,0) tongthunhaptheogiocongthucte,
                  hpl.total thunhapkhac,
                  coalesce(hpl2.total,0) hotroxangxe,
                  hpl3.total butruluongthang,
                  coalesce(hpl4.total,0) luongbuducong,
                  (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0)) tongthunhap,
                  hpl6.amount luongdongbaohiem,
                  hpl6.total BHXH,
                  hpl7.total BHYT,
                  hpl8.total BHTN,
                  (hpl6.total+hpl7.total+hpl8.total) tong,
                  hpl6.amount*0.175 BHXHH,
                  hpl6.amount*0.03 BHYTT,
                  hpl6.amount*0.01 BHTNN,
                  coalesce(hpl6.amount*0.215,0) tongg,
                  (hpl5.total+hpl.total+hpl2.total-hpl3.total+hpl4.total-hpl6.total-hpl7.total-hpl8.total) tongtienbh,
                  case
                      when coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 > 0
                      then coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 else 0 end as hotronhaoduocmienthue,
                  case
                      when coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 > 0
                      then
                          case
                          when (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-(coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15)
                                  -coalesce(hc.x_allowance_lunch,0) + coalesce(hpl13.total,0) > 0
                          then
                              (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-(coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15)
                                  -coalesce(hc.x_allowance_lunch,0) + coalesce(hpl13.total,0)
                          else 0 end
                  else 0
                  end as thunhapchiuthue,
                  hpl9.total trichthuetncn,
                  coalesce(hpl10.total,0) congtacphi,
                  coalesce(hpl14.total,0) as hotrodienthoai,
                  coalesce(hpl_meal.total,0) as an_ca,
                  x6.amount as thuongttthang,

                  -- thuong nhan vien xuat sac
                  (
                  select coalesce(sum(amount),0) as thuong_nvxs
                  from (select he7.id, other7.id as other_id, hpoc7.id as hpoc_id,
                  case when other7.amount > 0 then other7.amount else 0 end as amount
                  from hr_employee he7
                  left join hr_payroll_other other7 on other7.employee_id = he7.id
                  left join hr_payroll_other_category hpoc7 on other7.categ_id = hpoc7.id
                  where he7.id = he.id and other7.state = 'approved'
                      and (hpoc7.name = 'Thưởng nhân viên xuất sắc' or hpoc7.code = 'TNVXS') and
                      (DATE_PART('month', other7.date)= {0} and DATE_PART('year', other7.date)={1})
                      group by he7.id, other7.id, hpoc7.id) nvxs
                  ),
                  -- tong cac khoan type=bonus duoc tich "Tinh vao don gia nhan cong"
                  (
                  select coalesce(sum(amount),0) as tong_bonus_dongia
                  from (select he10.id, other10.id as other_id, hpoc10.id as hpoc_id,
                  case when other10.amount > 0 then other10.amount else 0 end as amount
                  from hr_employee he10
                  left join hr_payroll_other other10 on other10.employee_id = he10.id
                  left join hr_payroll_other_category hpoc10 on other10.categ_id = hpoc10.id
                  where he10.id = he.id and other10.state = 'approved'
                      and hpoc10.type = 'bonus' and hpoc10.count_in_unit_price = true and
                      (DATE_PART('month', other10.date)= {0} and DATE_PART('year', other10.date)={1})
                      group by he10.id, other10.id, hpoc10.id) bonus_dongia
                  ),
                  -- phu cap kiem nhiem
                  (
                    select coalesce(sum(amount),0) as phu_cap_kiem_nhiem
                    from (select he9.id, other9.id as other_id, hpoc9.id as hpoc_id,
                    case when other9.amount > 0 then other9.amount else 0 end as amount
                    from hr_employee he9
                    left join hr_payroll_other other9 on other9.employee_id = he9.id
                    left join hr_payroll_other_category hpoc9 on other9.categ_id = hpoc9.id
                    where he9.id = he.id and other9.state = 'approved'
                      and (hpoc9.name = 'Phụ cấp kiêm nhiệm' or hpoc9.code = 'PCKN') and
                      (DATE_PART('month', other9.date)= {0} and DATE_PART('year', other9.date)={1})
                      group by he9.id, other9.id, hpoc9.id) pckn
                    ),
                  -- thieu thuong nhan vien xuat sac nhat thang
                  --case when hc.x_type_employee != '3' then coalesce(hc.wage/12,0) else 0 end as thuongthang13,
                  -- thuong thang 13
                  (select coalesce(sum(thuong),0) as thuongthang13 from
                  (select he8.id, contract8.id as contract_id,
                  case
                      when contract8.date_start < '{1}-{0}-01' and '{1}-{0}-01' <= contract8.date_end and contract8.date_end < '{1}-{0}-{3}'
                          then (contract8.date_end - '{1}-{0}-01'::DATE + 1) * contract8.wage / (12 * {3})
                      when contract8.date_start < '{1}-{0}-01' and contract8.date_end >= '{1}-{0}-{3}'
  		                then contract8.wage / 12
                      when contract8.date_start >= '{1}-{0}-01' and contract8.date_end < '{1}-{0}-{3}'
                          then (contract8.date_end - contract8.date_start + 1) * contract8.wage / (12 * {3})
                      when contract8.date_start >= '{1}-{0}-01' and contract8.date_start <= '{1}-{0}-{3}' and contract8.date_end >= '{1}-{0}-{3}'
                          then ('{1}-{0}-{3}'::DATE - contract8.date_start + 1) * contract8.wage / (12 * {3})
                      ELSE 0
                      END AS thuong
                  from hr_employee he8
                  left join hr_contract contract8 on he8.id = contract8.employee_id
                  where he8.id = he.id and contract8.state in ('open', 'close') and contract8.x_type_employee != '2' ) thuong_thang_13
                  ),

                  -- dong phuc
                  (
                  select coalesce(sum(price),0) as dongphuc
                  from (select he1.id, job.id as job_id, oe.id as oe_id,
                  case when oe.price > 0 then oe.price/12 else 0 end as price
                  from hr_employee he1
                  left join hr_contract con1 on con1.id = hp.contract_id
                  left join hr_job job on con1.job_id = job.id
                  left join hr_job_other_expenses_rel hjoer on hjoer.hr_job_id = job.id
                  left join other_expenses oe on oe.id = hjoer.other_expenses_id
                  where he1.id = he.id and oe.type = 'uniform' and (oe.gender = he1.gender or oe.gender is null) and (oe.start_year <= {1} and oe.end_year >= {1})
                  group by he1.id, job.id, oe.id) dong_phuc
                  ),
                  -- kham suc khoe
                  (
                  select coalesce(sum(price),0) as khamsuckhoe
                  from (select he2.id, job2.id as job_id, oe2.id as oe_id,
                  case when oe2.price > 0 then oe2.price/12 else 0 end as price
                  from hr_employee he2
                  left join hr_contract con2 on con2.id = hp.contract_id
                  left join hr_job job2 on con2.job_id = job2.id
                  left join hr_job_other_expenses_rel hjoer2 on hjoer2.hr_job_id = job2.id
                  left join other_expenses oe2 on oe2.id = hjoer2.other_expenses_id
                  where he2.id = he.id and oe2.type = 'health' and (oe2.gender = he2.gender or oe2.gender is null) and (oe2.start_year <= {1} and oe2.end_year >= {1})
                  group by he2.id, job2.id, oe2.id) kham_suc_khoe
                  ),
                  -- thuong ngay le
                  (
                  select coalesce(sum(price),0) as thuongngayle
                  from (select he3.id, job3.id as job_id, oe3.id as oe_id,
                  case when oe3.price > 0 then oe3.price/12 else 0 end as price
                  from hr_employee he3
                  left join hr_contract con3 on con3.id = hp.contract_id
                  left join hr_job job3 on con3.job_id = job3.id
                  left join hr_job_other_expenses_rel hjoer3 on hjoer3.hr_job_id = job3.id
                  left join other_expenses oe3 on oe3.id = hjoer3.other_expenses_id
                  where he3.id = he.id and oe3.type = 'holiday' and (oe3.gender = he3.gender or oe3.gender is null) and (oe3.start_year <= {1} and oe3.end_year >= {1})
                  group by he3.id, job3.id, oe3.id) thuong_ngay_le
                  ),
                  -- du lich
                  (
                  select coalesce(sum(price),0) as dulich
                  from (select he4.id, job4.id as job_id, oe4.id as oe_id,
                  case when oe4.price > 0 then oe4.price/12 else 0 end as price
                  from hr_employee he4
                  left join hr_contract con4 on con4.id = hp.contract_id
                  left join hr_job job4 on con4.job_id = job4.id
                  left join hr_job_other_expenses_rel hjoer4 on hjoer4.hr_job_id = job4.id
                  left join other_expenses oe4 on oe4.id = hjoer4.other_expenses_id
                  where he4.id = he.id and oe4.type = 'travel' and (oe4.gender = he4.gender or oe4.gender is null) and (oe4.start_year <= {1} and oe4.end_year >= {1})
                  group by he4.id, job4.id, oe4.id) du_lich
                  ),
                  coalesce((hc.x_insurance_wage * 0.02), 0) as congdoan,
                  -- ngay nghi le trong thang
                        (
                        select coalesce(sum(gionghile),0) as gionghile from
                        (select hgo.id,
                            case
                            when hgo.date_start < '{1}-{0}-01' then
                            --hgo.date_end - '{1}-{0}-01'::DATE + 1
                            (WITH date_series AS (
                            SELECT generate_series('{1}-{0}-01'::date, hgo.date_end::date, '1 day') AS work_date
                            )
                            SELECT
                                SUM(
                                    CASE
                                        WHEN EXTRACT(DOW FROM work_date) IN (1,2,3,4,5) THEN 8  -- Thứ 2 - Thứ 6
                                            WHEN EXTRACT(DOW FROM work_date) = 0 THEN 8 -- Chủ nhật
                                            WHEN EXTRACT(DOW FROM work_date) = 6  THEN 8
                                            ELSE 0  -- Chủ nhật
                                    END
                                ) AS gionghile
                            FROM date_series)
                            when hgo.date_start >= '{1}-{0}-01' and hgo.date_end < '{1}-{0}-{3}' then
                                case when hc.x_type_employee = '3' and (hc.date_start > hgo.date_end or hc.date_end < hgo.date_start) then 0
                                else
                                --hgo.date_end - hgo.date_start + 1
                                (WITH date_series AS (
                                SELECT generate_series(hgo.date_start::date, hgo.date_end::date, '1 day') AS work_date
                                )
                                SELECT
                                    SUM(
                                        CASE
                                            WHEN EXTRACT(DOW FROM work_date) IN (1,2,3,4,5) THEN 8  -- Thứ 2 - Thứ 6
                                            WHEN EXTRACT(DOW FROM work_date) = 0 THEN 8 -- Chủ nhật
                                            WHEN EXTRACT(DOW FROM work_date) = 6  THEN 8
                                            ELSE 0  -- Chủ nhật
                                        END
                                    ) AS gionghile
                                FROM date_series)
                                end
                            when hgo.date_start >= '{1}-{0}-01' and hgo.date_end >= '{1}-{0}-{3}' then
                                case when hc.x_type_employee = '3' and (hc.date_start > hgo.date_end or hc.date_end < hgo.date_start) then 0
                                else
                                --'{1}-{0}-{3}'::DATE - hgo.date_start + 1
                                (WITH date_series AS (
                                SELECT generate_series(hgo.date_start::date, '{1}-{0}-{3}'::date, '1 day') AS work_date
                                )
                                SELECT
                                    SUM(
                                        CASE
                                            WHEN EXTRACT(DOW FROM work_date) IN (1,2,3,4,5) THEN 8  -- Thứ 2 - Thứ 6
                                            WHEN EXTRACT(DOW FROM work_date) = 0 THEN 8 -- Chủ nhật
                                            WHEN EXTRACT(DOW FROM work_date) = 6  THEN 8
                                            ELSE 0  -- Chủ nhật
                                        END
                                    ) AS gionghile
                                FROM date_series)
                                end
                            else 0 end as gionghile
                        from hr_global_off hgo
                        where hgo.active = true
                        and (hgo.date_start <= '{1}-{0}-{3}' AND hgo.date_end >= '{1}-{0}-01')
                            ) working_day
                        ),
                  -- nghi phep co luong
                  (
                  select coalesce(sum(gio_nghi_phep),0) as gio_nghi_phep
                  from (select he5.id, leave5.id as leave_id, log5.id as log_id,
                  case when leave5.number_of_days > 0 then log5.number_of_days * 8 else 0 end as gio_nghi_phep
                  from hr_employee he5
                  left join hr_leave leave5 on leave5.employee_id = he5.id
                  left join hr_leave_log log5 on log5.leave_id = leave5.id
                  left join hr_leave_type hlt5 on hlt5.id = log5.leave_type_id
                  where he5.id = he.id and leave5.state = 'validate' and hlt5.x_pay=true and
                  (DATE_PART('month', log5.date)= {0} and DATE_PART('year', log5.date)={1})
                      group by he5.id, log5.id, leave5.id) nghi_phep
                  ),
                  -- bu gio thu cong
                  (
                  select coalesce(sum(bu_gio_thu_cong),0) as bu_gio_thu_cong
                  from (select he6.id, hpoh6.id as hpoh_id,
                  case when hpoh6.hour > 0 then hpoh6.hour else 0 end as bu_gio_thu_cong
                  from hr_employee he6
                  left join hr_payroll_other_hour hpoh6 on hpoh6.employee_id = he6.id
                  where he6.id = he.id and hpoh6.state = 'approved' and
                      (DATE_PART('month', hpoh6.date)= {0} and DATE_PART('year', hpoh6.date)={1})
                      group by he6.id, hpoh6.id) bu_gio
                  ),
                  hpl11.total hoanthuetncnnamtruoc,
                  hpl12.total datamung,
                  hp.x_amount_total luongthuclinh
                  from hr_payslip hp
                  left join hr_payslip_line hpl on hp.id = hpl.slip_id and hpl.name = 'Thưởng hoặc các khoản thu nhập khác'
                  left join hr_payslip_line hpl2 on hp.id = hpl2.slip_id  and hpl2.name = 'Hỗ trợ xăng xe'
                  left join hr_payslip_line hpl3 on hp.id = hpl3.slip_id  and hpl3.name = 'Bù/Trừ lương tháng'
                  left join hr_payslip_line hpl4 on hp.id = hpl4.slip_id  and hpl4.name = 'Hỗ trợ tiền lương bù đủ công'
                  left join (select slip_id, sum(total) as total from hr_payslip_line where code in ('TNTGCTT','LKPI','LNG','LDL') group by slip_id) hpl5 on hp.id = hpl5.slip_id
                  left join hr_payslip_line hpl_meal on hp.id = hpl_meal.slip_id and hpl_meal.code = 'HTAC'
                  left join hr_payslip_line hpl6 on hp.id = hpl6.slip_id  and hpl6.name = 'Bảo hiểm xã hội'
                  left join hr_payslip_line hpl7 on hp.id = hpl7.slip_id and hpl7.name = 'Bảo hiểm y tế'
                  left join hr_payslip_line hpl8 on hp.id = hpl8.slip_id and hpl8.name = 'Bảo hiểm thất nghiệp'
                  left join hr_payslip_line hpl9 on hp.id = hpl9.slip_id  and hpl9.name = 'Thuế TNCN phải nộp'
                  left join hr_payslip_line hpl10 on hp.id = hpl10.slip_id   and hpl10.name = 'Công tác phí'
                  left join hr_payslip_line hpl11 on hp.id = hpl11.slip_id   and hpl11.name = 'Hoàn thuế TNCN năm trước'
                  left join hr_payslip_line hpl12 on hp.id = hpl12.slip_id  and hpl12.name = 'Tạm ứng'
                  left join hr_payslip_line hpl13 on hp.id = hpl13.slip_id  and hpl13.name = 'Các khoản thưởng nóng'
                  left join hr_payslip_line hpl14 on hp.id = hpl14.slip_id  and hpl14.code = 'HTDT'

                  left join hr_employee he on hp.employee_id = he.id

                  left join hr_contract hc on hp.contract_id = hc.id
                  left join resource_calendar resource on resource.id = hc.resource_calendar_id
                  left join (select hpi.*,hpit.code as codehpit from hr_payslip_input hpi left join hr_payslip_input_type hpit on hpi.input_type_id = hpit.id)X1 on hp.id = X1.payslip_id and X1.codehpit = 'OTHER_WORK_DAY_THEORY'
                  left join (select hpi2.*,hpit2.code as codehpit from hr_payslip_input hpi2 left join hr_payslip_input_type hpit2 on hpi2.input_type_id = hpit2.id)X2 on hp.id = X2.payslip_id and X2.codehpit = 'OTHER_WORK_HOUR_CONVERTED'
                  left join (select hpi3.*,hpit3.code as codehpit from hr_payslip_input hpi3 left join hr_payslip_input_type hpit3 on hpi3.input_type_id = hpit3.id)X3 on hp.id = X3.payslip_id and X3.codehpit = 'OTHER_WORK_HOUR_SUPPORT'
                  left join (select hpi4.*,hpit4.code as codehpit from hr_payslip_input hpi4 left join hr_payslip_input_type hpit4 on hpi4.input_type_id = hpit4.id)X4 on hp.id = X4.payslip_id and X4.codehpit = 'OTHER_WAGE_TOTAL'
                  left join (select hpi5.*,hpit5.code as codehpit from hr_payslip_input hpi5 left join hr_payslip_input_type hpit5 on hpi5.input_type_id = hpit5.id)X5 on hp.id = X5.payslip_id and X5.codehpit = 'OTHER_WORK_HOUR_THEORY'
                  left join (select hpi6.*,hpit6.code as codehpit from hr_payslip_input hpi6 left join hr_payslip_input_type hpit6 on hpi6.input_type_id = hpit6.id)X6 on hp.id = X6.payslip_id and X6.codehpit = 'OTHER_BONUS_INSTANT'
                  left join hr_department hd on he.department_id = hd.id
                  left join hr_department_block hdb on hdb.id = hd.x_block_id
                  where hp.id =  {2}
                  and (DATE_PART('month',hp.date_from)= {0} and DATE_PART('month',hp.date_to)= {0})
                  and (DATE_PART('year',hp.date_from)={1} and DATE_PART('year',hp.date_to)={1})
                                    """.format(month, year, self.id,
                                               num_days)

        self._cr.execute(queryGeneral)
        listData = self._cr.dictfetchall()
        if not listData:
            return None, 0.0, 0.0, 0.0
        data = listData[0]
        # 'thuong_nvxs' đã gom toàn bộ khoản type=bonus được tích
        # "Tính vào đơn giá" (bao gồm cả Phụ cấp kiêm nhiệm), nên không
        # cộng riêng 'phu_cap_kiem_nhiem' nữa để tránh đếm trùng.
        tong_chi_phi = data['tongthunhaptheogiocongthucte'] + data['tong_bonus_dongia'] + data['hotroxangxe'] + data[
            'luongbuducong'] + data['tongg'] + data['congtacphi'] + data['hotrodienthoai'] + data[
                           'thuongthang13'] + data['dongphuc'] + data[
                           'khamsuckhoe'] + data['thuongngayle'] + data['dulich'] + data['congdoan'] + data['an_ca']
        h44 = 0
        if data.get('hours_per_week44'):
            h44 = data.get('saturdays', 0) * 4
        # paidleave = l.get('gionghile', 0)
        paidleave = data.get('gio_nghi_phep', 0) + data.get('gionghile', 0) or 0.0
        paidleave = paidleave - h44 if paidleave - h44 > 0 else 0
        paidleave = paidleave - self.get_holiday_out_contract(data['manhanvien'], month, year)
        if paidleave < 0:
            paidleave = 0
        gio_cong_thuc_te = data['tonggiocongthucte'] - paidleave
        return data, tong_chi_phi, paidleave, gio_cong_thuc_te

    def create_wage_cost_actual(self):
        for rec in self:
            data, tong_chi_phi, paidleave, gio_cong_thuc_te = rec._get_wage_cost_data()
            if not data:
                continue
            unit_price = tong_chi_phi / gio_cong_thuc_te if gio_cong_thuc_te > 0 else 0.0
            # Cộng đơn giá khấu hao CCDC cấp cá nhân (đ/giờ công) vào đơn giá
            # nhân công: máy tính cấp cho cá nhân = giá vốn/năm/2320h = đ/giờ.
            if 'project.depreciation.line' in self.env:
                unit_price += self.env['project.depreciation.line'].get_personal_ccdc_rate(
                    rec.employee_id, rec.date_from.year, rec.date_from.month)
            values = {
                'employee_id': rec.employee_id.id,
                'payslip_id': rec.id,
                'date_from': rec.date_from,
                'date_to': rec.date_to,
                'unit_price': unit_price,
            }
            # tìm kiếm wage.cost.actual nếu có thì update dữ liệu, k có thì tạo mới
            wage_cost = self.env['wage.cost.actual'].search([('date_from', '=', rec.date_from), ('date_to', '=', rec.date_to), ('employee_id', '=', rec.employee_id.id)])
            if wage_cost:
                wage_cost.unit_price = unit_price
            else:
                self.env['wage.cost.actual'].create(values)

    def action_payslip_done(self):
        res = super(Payslip, self).action_payslip_done()
        # Send message to user link to payslips employee
        report_id = self.env.ref('hr_payroll.action_report_payslip')
        channel_obj = self.env['mail.channel'].sudo()
        for r in self.filtered(lambda x: x.state == 'done'):
            if not r.employee_id.user_id:
                continue
            partner_id = r.employee_id.user_id.partner_id
            channel_info = channel_obj.channel_get(partner_id.ids)

            report = report_id._render_qweb_pdf(r.id)
            filename = 'Phiếu lương %s %s.pdf' % (r.employee_id.name, r.date_from.strftime('%m/%Y'))
            attachment_id = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(report[0]),
                'store_fname': filename,
                'res_model': 'hr.payslip',
                'res_id': r.id,
                'mimetype': 'application/x-pdf'
            })

            channel_obj.browse(channel_info['id']).message_post(
                body=_('Phiếu lương %s') % r.date_from.strftime('%m/%Y'),
                message_type='comment',
                subtype_id=self.env.ref('mail.mt_comment').id,
                attachment_ids=[attachment_id.id]
            )

        for record in self:
            record.create_wage_cost_actual()
        return res

    def __format_ws__(self, ws, cell_range):
        # applying border and alignment
        border = Border(left=Side(border_style='thin', color='000000'),
                        right=Side(border_style='thin', color='000000'),
                        top=Side(border_style='thin', color='000000'),
                        bottom=Side(border_style='thin', color='000000'))

        rows = [rows for rows in ws[cell_range]]
        flattened = [item for sublist in rows for item in sublist]
        [(setattr(cell, 'border', border)) for cell in flattened]

    @api.depends('line_ids')
    @api.onchange('line_ids')
    def compute_amount_total(self):
        for r in self:
            amount_total = 0.0
            for item in r.line_ids:
                if item.category_id.code in ['GROSS', 'BASIC', 'ALW', 'NET', 'TAXR']:
                    amount_total += item.total
                elif item.category_id.code in ['DED', 'COMP']:
                    amount_total -= item.total
            r.x_amount_total = amount_total

    def get_excel_report(self, month, year):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/approval.xlsx')
        ws = wb['Data']
        generalTotal = 0.0
        maintenenanceTotal = 0.0
        facilityTotal = 0.0
        generalTotalReal = 0.0
        maintenenanceTotalReal = 0.0
        facilityTotalReal = 0.0

        queryGeneral = """
                        select he.name hovaten, he.x_code manhanvien, he.job_title chucdanh,
                        hc.wage thunhaptheogiocongthucte, hp.x_amount_total luongthuclinh
                        from hr_payslip hp
                        left join hr_employee he on hp.employee_id = he.id
                        left join hr_department hd on he.department_id = hd.id
                        left join hr_department_block hdb on hdb.id = hd.x_block_id 
                        left join hr_contract hc on hc.id = hp.contract_id 
                        where 
                        hp.state = 'done'
                        and (DATE_PART('month',hp.date_from)= {0} and DATE_PART('month',hp.date_to)= {0})
                        and (DATE_PART('year',hp.date_from)={1} and DATE_PART('year',hp.date_to)={1})
                        and hdb.name = 'General'
                        group by he.name, he.x_code, he.job_title, hc.wage , hp.x_amount_total 
                        """.format(month, year)
        self._cr.execute(queryGeneral)
        listGenerals = self._cr.dictfetchall()
        row = 5
        ws.cell(2, 4).value = str(month) + '-' + str(year)
        ws.cell(4, 1).value = 'I'
        ws.cell(4, 2).value = 'General'
        for index, l in enumerate(listGenerals):
            ws.cell(row, 1).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 2).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 3).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 4).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 5).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 6).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['hovaten'] or ''
            ws.cell(row, 3).value = l['manhanvien'] or ''
            ws.cell(row, 4).value = l['chucdanh'] or ''
            ws.cell(row, 5).number_format = '#,##0.00'
            ws.cell(row, 6).number_format = '#,##0.00'
            ws.cell(row, 5).value = l['thunhaptheogiocongthucte'] or ''
            ws.cell(row, 6).value = l['luongthuclinh'] or ''
            generalTotal += l['thunhaptheogiocongthucte']
            generalTotalReal += l['luongthuclinh']
            index += 1
            row += 1
        ws.cell(4, 5).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(4, 5).number_format = '#,##0.00'
        ws.cell(4, 5).value = generalTotal
        ws.cell(4, 6).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(4, 6).number_format = '#,##0.00'
        ws.cell(4, 6).value = generalTotalReal

        queryMaintenenance = """
                               select he.name hovaten, he.x_code manhanvien, he.job_title chucdanh,
                        hc.wage thunhaptheogiocongthucte, hp.x_amount_total luongthuclinh
                        from hr_payslip hp
                        left join hr_employee he on hp.employee_id = he.id
                        left join hr_department hd on he.department_id = hd.id
                        left join hr_department_block hdb on hdb.id = hd.x_block_id 
                        left join hr_contract hc on hc.id = hp.contract_id 
                        where 
                        hp.state = 'done'
                        and (DATE_PART('month',hp.date_from)= {0} and DATE_PART('month',hp.date_to)= {0})
                        and (DATE_PART('year',hp.date_from)={1} and DATE_PART('year',hp.date_to)={1})
                        and hdb.name = 'Maintenenance & Services'
                        group by he.name, he.x_code, he.job_title, hc.wage , hp.x_amount_total 
                                """.format(month, year)
        self._cr.execute(queryMaintenenance)
        listMaintenenances = self._cr.dictfetchall()
        row = row + 2
        ws.cell(row - 1, 1).font = Font(bold=True, size=12, name='Times New Roman')
        ws.cell(row - 1, 1).value = 'II'
        ws.cell(row - 1, 2).font = Font(bold=True, size=12, name='Times New Roman')
        ws.cell(row - 1, 2).value = 'Maintenenance & Services'
        rowX = row
        for index, l in enumerate(listMaintenenances):
            ws.cell(row, 1).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 2).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 3).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 4).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 5).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 6).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['hovaten'] or ''
            ws.cell(row, 3).value = l['manhanvien'] or ''
            ws.cell(row, 4).value = l['chucdanh'] or ''
            ws.cell(row, 5).number_format = '#,##0.00'
            ws.cell(row, 6).number_format = '#,##0.00'
            ws.cell(row, 5).value = l['thunhaptheogiocongthucte'] or ''
            ws.cell(row, 6).value = l['luongthuclinh'] or ''
            maintenenanceTotal += l['thunhaptheogiocongthucte']
            maintenenanceTotalReal += l['luongthuclinh']
            index += 1
            row += 1
        ws.cell(rowX - 1, 5).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(rowX - 1, 5).number_format = '#,##0.00'
        ws.cell(rowX - 1, 5).value = maintenenanceTotal
        ws.cell(rowX - 1, 6).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(rowX - 1, 6).number_format = '#,##0.00'
        ws.cell(rowX - 1, 6).value = maintenenanceTotalReal

        queryFacility = """
                            select he.name hovaten, he.x_code manhanvien, he.job_title chucdanh,
                        hc.wage thunhaptheogiocongthucte, hp.x_amount_total luongthuclinh
                        from hr_payslip hp
                        left join hr_employee he on hp.employee_id = he.id
                        left join hr_department hd on he.department_id = hd.id
                        left join hr_department_block hdb on hdb.id = hd.x_block_id 
                        left join hr_contract hc on hc.id = hp.contract_id 
                        where 
                        hp.state = 'done'
                        and (DATE_PART('month',hp.date_from)= {0} and DATE_PART('month',hp.date_to)= {0})
                        and (DATE_PART('year',hp.date_from)={1} and DATE_PART('year',hp.date_to)={1})
                        and hdb.name = 'Facility Management'
                        group by he.name, he.x_code, he.job_title, hc.wage , hp.x_amount_total
                        """.format(month, year)
        self._cr.execute(queryFacility)
        listFacilitys = self._cr.dictfetchall()
        row = row + 2
        ws.cell(row - 1, 1).font = Font(bold=True, size=12, name='Times New Roman')
        ws.cell(row - 1, 1).value = 'III'
        ws.cell(row - 1, 2).font = Font(bold=True, size=12, name='Times New Roman')
        ws.cell(row - 1, 2).value = 'Facility Management'
        rowX2 = row
        for index, l in enumerate(listFacilitys):
            ws.cell(row, 1).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 2).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 3).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 4).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 5).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 6).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['hovaten'] or ''
            ws.cell(row, 3).value = l['manhanvien'] or ''
            ws.cell(row, 4).value = l['chucdanh'] or ''
            ws.cell(row, 5).number_format = '#,##0.00'
            ws.cell(row, 6).number_format = '#,##0.00'
            ws.cell(row, 5).value = l['thunhaptheogiocongthucte'] or ''
            ws.cell(row, 6).value = l['luongthuclinh'] or ''
            facilityTotal += l['thunhaptheogiocongthucte']
            facilityTotalReal += l['luongthuclinh']
            index += 1
            row += 1
        ws.cell(rowX2 - 1, 5).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(rowX2 - 1, 5).number_format = '#,##0.00'
        ws.cell(rowX2 - 1, 5).value = facilityTotal
        ws.cell(rowX2 - 1, 6).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(rowX2 - 1, 6).number_format = '#,##0.00'
        ws.cell(rowX2 - 1, 6).value = facilityTotalReal
        # merge cell tổng
        A = 'A' + str(row + 1) + ':D' + str(row + 1)
        ws.cell(row + 1, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 1, 1).alignment = Alignment(horizontal='center')
        ws.cell(row + 1, 1).value = 'Tổng'
        ws.merge_cells(A)
        ws.cell(row + 1, 5).number_format = '#,##0.00'
        ws.cell(row + 1, 5).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 1, 5).value = generalTotal + maintenenanceTotal + facilityTotal
        ws.cell(row + 1, 6).number_format = '#,##0.00'
        ws.cell(row + 1, 6).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 1, 6).value = generalTotalReal + maintenenanceTotalReal + facilityTotalReal

        utility_obj = self.env['hcsv.utility']
        company_currency = self.env.user.company_id.currency_id
        sumChu = utility_obj.convert_amount_to_words(
            amount=generalTotalReal + maintenenanceTotalReal + facilityTotalReal,
            currency=company_currency).capitalize()
        ws.cell(row + 2, 2).font = ws.cell(row + 2, 3).font = ws.cell(row + 4, 2).font = ws.cell(row + 4,
                                                                                                 4).font = ws.cell(
            row + 4, 6).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 2, 2).value = 'Bằng chữ: '
        ws.cell(row + 2, 2).alignment = Alignment(horizontal='right')
        ws.cell(row + 2, 3).value = sumChu
        ws.cell(row + 4, 2).alignment = ws.cell(row + 4, 4).alignment = ws.cell(row + 4, 6).alignment = Alignment(
            horizontal='center')
        ws.cell(row + 3, 3).value = fields.datetime.now().date().strftime("%d/%m/%Y")
        ws.cell(row + 4, 2).value = 'NGƯỜI LẬP BẢNG'
        ws.cell(row + 4, 4).value = 'PHỤ TRÁCH KẾ TOÁN'
        ws.cell(row + 4, 6).value = 'NGƯỜI DUYỆT'
        self.__format_ws__(ws, cell_range='A3:F' + str(row + 1))
        for col_range in range(1, 7):
            for row_range in range(row + 2, row + 9):
                cell_title = ws.cell(row_range, col_range)
                cell_title.fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo Approval.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }

    def get_excel_report_approve_with_bank_account(self, month, year):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/approvalwithbankaccount.xlsx')
        ws = wb['Data']
        query = """
                    select he.id, he.name hovaten, he.x_code manhanvien, he.job_title chucdanh,hp.x_amount_total tong,
                    he.x_bank_account sotaikhoan, he.x_bank_branch chinhanh, he.x_bank_name, concat('Công ty SPS thanh toán lương tháng',' ','{0}') as diengiai
                    from hr_payslip hp
                    inner join hr_employee he on hp.employee_id = he.id
                    where 
                    hp.state = 'done'
                    and (DATE_PART('month',hp.date_from)= {0} and DATE_PART('month',hp.date_to)= {0})
                    and (DATE_PART('year',hp.date_from)={1} and DATE_PART('year',hp.date_to)={1})
                """.format(month, year)
        self._cr.execute(query)
        lists = self._cr.dictfetchall()
        row = 4
        ws.cell(2, 6).value = str(month) + '-' + str(year)
        sum = 0.0
        for index, l in enumerate(lists):
            ws.cell(row, 1).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 2).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 3).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 4).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 5).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 6).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 7).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 8).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 9).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['hovaten'] or ''
            ws.cell(row, 3).value = l['manhanvien'] or ''
            ws.cell(row, 4).value = l['chucdanh'] or ''
            ws.cell(row, 5).number_format = '#,##0.00'
            ws.cell(row, 5).value = l['tong'] or ''
            ws.cell(row, 6).value = l['sotaikhoan'] or ''
            ws.cell(row, 7).value = l['chinhanh'] or ''
            ws.cell(row, 8).value = l['x_bank_name'] or ''
            ws.cell(row, 9).value = l['diengiai'] or ''
            index += 1
            sum += l['tong']
            row += 1
        A = 'A' + str(row) + ':D' + str(row)
        ws.cell(row, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 1).alignment = Alignment(horizontal='center')
        ws.cell(row, 1).value = 'Tổng'
        ws.merge_cells(A)
        ws.cell(row, 5).number_format = '#,##0.00'
        ws.cell(row, 5).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 5).value = sum

        utility_obj = self.env['hcsv.utility']
        company_currency = self.env.user.company_id.currency_id
        sumChu = utility_obj.convert_amount_to_words(amount=sum, currency=company_currency).capitalize()
        ws.cell(row + 1, 2).font = ws.cell(row + 1, 3).font = ws.cell(row + 3, 3).font = ws.cell(row + 3,
                                                                                                 8).font = Font(size=12,
                                                                                                                name='Times New Roman',
                                                                                                                bold=True)
        ws.cell(row + 1, 2).value = 'Bằng chữ: '
        ws.cell(row + 1, 2).alignment = Alignment(horizontal='right')
        ws.cell(row + 1, 3).value = sumChu
        ws.cell(row + 2, 3).alignment = ws.cell(row + 3, 8).alignment = Alignment(horizontal='center')
        ws.cell(row + 2, 3).value = fields.datetime.now().date().strftime("%d/%m/%Y")
        ws.cell(row + 3, 3).value = 'NGƯỜI LẬP BẢNG'
        ws.cell(row + 3, 8).value = 'NGƯỜI DUYỆT'
        self.__format_ws__(ws, cell_range='A3:I' + str(row))
        for col_range in range(1, 10):
            for row_range in range(row + 1, row + 9):
                cell_title = ws.cell(row_range, col_range)
                cell_title.fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo ApprovalWithBankAccount.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }

    def get_excel_report_year(self, year):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/year.xlsx')
        ws = wb['Data']
        totalColumn1 = 0.0
        totalColumn2 = 0.0
        totalColumn3 = 0.0
        totalColumn4 = 0.0
        totalColumn5 = 0.0
        totalColumn6 = 0.0
        totalColumn7 = 0.0
        totalColumn8 = 0.0
        totalColumn9 = 0.0
        totalColumn10 = 0.0
        totalColumn11 = 0.0
        totalColumn12 = 0.0
        query = """
                select A.division, sum(A.Jan21) sum1, sum(A.Feb21) sum2, sum(A.Mar21) sum3, sum(A.Apr21) sum4, sum(A.May21) sum5, sum(A.Jun21) sum6, sum(A.Jul21) sum7, sum(A.Aug21) sum8, 
               sum(A.Sep21) sum9, sum(A.Oct21) sum10, sum(A.Nov21) sum11, sum(A.Dec21) sum12, 
               (sum(A.Jan21) + sum(A.Feb21) + sum(A.Mar21) + sum(A.Apr21) + sum(A.May21) + sum(A.Jun21) + sum(A.Jul21) + sum(A.Aug21) + sum(A.Sep21) + sum(A.Oct21) + sum(A.Nov21) + sum(A.Dec21)) as sumRow
               from 
                (select hdb.id id, hdb.name Division,
                     case when (DATE_PART('month',hp.date_from)= 1 and DATE_PART('month',hp.date_to)= 1 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Jan21,
                     case when (DATE_PART('month',hp.date_from)= 2 and DATE_PART('month',hp.date_to)= 2 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Feb21,
                     case when (DATE_PART('month',hp.date_from)= 3 and DATE_PART('month',hp.date_to)= 3 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Mar21,
                     case when (DATE_PART('month',hp.date_from)= 4 and DATE_PART('month',hp.date_to)= 4 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Apr21,
                     case when (DATE_PART('month',hp.date_from)= 5 and DATE_PART('month',hp.date_to)= 5 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end May21,
                     case when (DATE_PART('month',hp.date_from)= 6 and DATE_PART('month',hp.date_to)= 6 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Jun21,
                     case when (DATE_PART('month',hp.date_from)= 7 and DATE_PART('month',hp.date_to)= 7 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Jul21,
                     case when (DATE_PART('month',hp.date_from)= 8 and DATE_PART('month',hp.date_to)= 8 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Aug21,
                     case when (DATE_PART('month',hp.date_from)= 9 and DATE_PART('month',hp.date_to)= 9 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Sep21,
                     case when (DATE_PART('month',hp.date_from)= 10 and DATE_PART('month',hp.date_to)= 10 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Oct21,
                     case when (DATE_PART('month',hp.date_from)= 11 and DATE_PART('month',hp.date_to)= 11 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Nov21,
                     case when (DATE_PART('month',hp.date_from)= 12 and DATE_PART('month',hp.date_to)= 12 and DATE_PART('year',hp.date_to)= {0}) 
                     then hp.x_amount_total else 0 end Dec21
                from hr_department_block hdb
                left join hr_department hd on hdb.id = hd.x_block_id 
                left join hr_employee he on he.department_id = hd.id
                left join hr_payslip hp on hp.employee_id = he.id
                where hp.state = 'done'
                ) 
                as A
                group by A.division, A.id
                order by A.id desc
                        """.format(year)
        self._cr.execute(query)
        lists = self._cr.dictfetchall()
        row = 5
        ws.cell(1, 1).value = 'Bảng chi tiết phân bổ lương năm ' + str(year)
        for l in lists:
            ws.cell(row, 2).value = l['division'] or ''
            ws.cell(row, 3).value = l['sum1'] or ''
            totalColumn1 += l['sum1'] or 0.0
            ws.cell(row, 4).value = l['sum2'] or ''
            totalColumn2 += l['sum2'] or 0.0
            ws.cell(row, 5).value = l['sum3'] or ''
            totalColumn3 += l['sum3'] or 0.0
            ws.cell(row, 6).value = l['sum4'] or ''
            totalColumn4 += l['sum4'] or 0.0
            ws.cell(row, 7).value = l['sum5'] or ''
            totalColumn5 += l['sum5'] or 0.0
            ws.cell(row, 8).value = l['sum6'] or ''
            totalColumn6 += l['sum6'] or 0.0
            ws.cell(row, 9).value = l['sum7'] or ''
            totalColumn7 += l['sum7'] or 0.0
            ws.cell(row, 10).value = l['sum8'] or ''
            totalColumn8 += l['sum8'] or 0.0
            ws.cell(row, 11).value = l['sum9'] or ''
            totalColumn9 += l['sum9'] or 0.0
            ws.cell(row, 12).value = l['sum10'] or ''
            totalColumn10 += l['sum10'] or 0.0
            ws.cell(row, 13).value = l['sum11'] or ''
            totalColumn11 += l['sum11'] or 0.0
            ws.cell(row, 14).value = l['sum12'] or ''
            totalColumn12 += l['sum12'] or 0.0
            ws.cell(row, 15).value = l['sumrow']
            row += 1
        ws.cell(8, 3).value = totalColumn1
        ws.cell(8, 4).value = totalColumn2
        ws.cell(8, 5).value = totalColumn3
        ws.cell(8, 6).value = totalColumn4
        ws.cell(8, 7).value = totalColumn5
        ws.cell(8, 8).value = totalColumn6
        ws.cell(8, 9).value = totalColumn7
        ws.cell(8, 10).value = totalColumn8
        ws.cell(8, 11).value = totalColumn9
        ws.cell(8, 12).value = totalColumn10
        ws.cell(8, 13).value = totalColumn11
        ws.cell(8, 14).value = totalColumn12
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo Year.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }

    def get_excel_report_salary_new(self, month, year, show_draft, with_cost=False):
        """Báo cáo 'Bảng chi phí nhân công' (SALARY NEW) - layout mới từ 01/07/2026.

        Đọc dữ liệu từ salary line theo mã (P1-P4): TNTGCTT (lương chính thực tế),
        LKPI, LNG (OT), LDL (đi lại), HTAC (ăn ca)... + hợp đồng (x_insurance_wage,
        kpi_norm) + hr.kpi.evaluation (paid_hours). Cột thuế 35/45-50 tạm best-effort,
        P7 sẽ tinh chỉnh.

        with_cost=True (process_new): dùng template riêng có thêm 2 cột cuối:
          62 = Đơn giá CCDC cá nhân (đ/giờ, get_personal_ccdc_rate() - tính trực tiếp,
          KHÔNG sum project.wage.cost vì bảng đó có thể trùng dòng khi chấm công được
          gán lại mã dự án),
          63 = Đơn giá nhân công (wage.cost.actual.unit_price - CHỈ có khi phiếu 'done').
        """
        dir_path = os.path.dirname(os.path.realpath(__file__))
        template = 'salary_ver2_cost.xlsx' if with_cost else 'salary_ver2.xlsx'
        wb = openpyxl.load_workbook(dir_path + '/../templates/' + template)
        ws = wb['Data']
        month = int(month)
        # Kỳ báo cáo: ghi cạnh tiêu đề "BẢNG CHI TIẾT LƯƠNG:" (C11) ở C12, dạng m/yyyy (khớp mẫu gốc)
        ws.cell(1, 12).value = '%s/%s' % (month, year)

        last_day = calendar.monthrange(year, month)[1]
        date_from = date(year, month, 1)
        date_to = date(year, month, last_day)
        states = ['draft', 'verify', 'done'] if show_draft else ['done']
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', states),
            ('date_from', '>=', date_from), ('date_to', '<=', date_to),
        ])

        # Thưởng nhân viên xuất sắc (cột 19) - gom theo nhân viên trong kỳ
        nvxs_map = {}
        for r in self.env['hr.payroll.other'].sudo().search([
                ('state', '=', 'approved'),
                ('date', '>=', date_from), ('date', '<=', date_to),
                ('categ_id.code', '=', 'TNVXS')]):
            if r.amount > 0:
                nvxs_map[r.employee_id.id] = nvxs_map.get(r.employee_id.id, 0.0) + r.amount

        deduction_self = float(self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.deduction_self', 0.0))
        deduction_dependent = float(self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.deduction_dependent', 0.0))

        # with_cost: cột 52-60 = Thưởng tháng 13 .. Tổng số giờ công thực tế (khớp
        # mẫu cũ, chèn sau cột 51 "Thuế TNCN"); Đơn giá thực tế/CCDC/đơn giá NC dời
        # xuống 61-63. Bản thường (salary_ver2.xlsx) giữ nguyên layout 52 cột gốc.
        NUM_COLS = 63 if with_cost else 52
        ACC2_COLS = (9, 61, 62, 63) if with_cost else (9, 52)  # cột đơn giá, không cộng tổng
        SUM_COLS = [c for c in range(5, NUM_COLS + 1) if c not in ACC2_COLS]

        # Chi phí nhân công (cột 53/54) - chỉ khi with_cost. Đơn giá nhân công lấy
        # từ wage.cost.actual (chỉ có khi phiếu đã 'done').
        unit_price_map = {}
        if with_cost:
            for w in self.env['wage.cost.actual'].sudo().search([
                    ('date_from', '=', date_from), ('date_to', '=', date_to)]):
                if w.employee_id:
                    unit_price_map[w.employee_id.id] = w.unit_price

        def row_vals(p):
            L = {l.code: l.total for l in p.line_ids}
            Lamt = {l.code: l.amount for l in p.line_ids}
            I = {i.input_type_id.code: i.amount for i in p.input_line_ids}
            c = p.contract_id
            he = p.employee_id
            # Cột 5/6/7 (định mức theo HĐ): HĐ đã tách -> Lương chính = lương BH, KPI định mức
            # = kpi_norm, Tổng = wage. HĐ chưa tách/thử việc (x_insurance_wage=0) -> để TRỐNG
            # cột 5/6, dồn toàn bộ vào cột 7 = wage (khớp mẫu gốc). Tổng cột 7 = tổng lương HĐ.
            lc = c.x_insurance_wage or None
            kpidm = c.kpi_norm or None
            tong = c.wage
            gio_cs = I.get('OTHER_WORK_HOUR_THEORY', 0.0)
            dg = (tong / gio_cs) if gio_cs else 0.0
            lc_tt = L.get('TNTGCTT', 0.0)
            kpi_tt = L.get('LKPI', 0.0)
            ot = L.get('LNG', 0.0)
            dl = L.get('LDL', 0.0)
            # Thực tập sinh (x_type_employee='2'): thu nhập -> cột 17 (không vào lương chính/KPI/OT/ĐL)
            if c.x_type_employee == '2':
                tts = lc_tt
                lc_tt = kpi_tt = ot = dl = 0.0
            else:
                tts = 0.0
            tong_gio = lc_tt + kpi_tt + ot + dl
            an = L.get('HTAC', 0.0)
            nvxs = nvxs_map.get(he.id, 0.0)               # cột 19: Thưởng NV xuất sắc (TNVXS)
            thuong_khac = L.get('THCKTNK', 0.0) - nvxs    # cột 18: tổng bonus - nvxs
            xang = L.get('HTXX', 0.0)
            # Khoản bù/trừ (BTLT) là khoản GIẢM TRỪ (category DED) -> hiển thị SỐ ÂM (cột 21)
            # và LÀM GIẢM tổng thu nhập đợt/tháng + thu nhập chịu thuế (cộng số âm = trừ).
            # Khớp mẫu gốc (col21 âm, col23 = SUM gồm nó). Net vẫn đúng vì phiếu trừ DED sẵn.
            butru = -L.get('BTLT', 0.0)
            thieucong = L.get('HTTLBDC', 0.0)
            tong_dot = tong_gio + an + tts + thuong_khac + nvxs + xang + butru + thieucong
            thuong_tt = p.x_hot_bonus or I.get('OTHER_BONUS_INSTANT', 0.0)
            tong_thang = tong_dot + thuong_tt
            base_bh = Lamt.get('BHXH', 0.0)
            bhxh = L.get('BHXH', 0.0)
            bhyt = L.get('BHYT', 0.0)
            bhtn = L.get('BHTN', 0.0)
            tongbh = bhxh + bhyt + bhtn
            cbhxh = base_bh * 0.175
            cbhyt = base_bh * 0.03
            cbhtn = base_bh * 0.01
            ctong = cbhxh + cbhyt + cbhtn
            tong_all_bh = tongbh + ctong
            ctp = L.get('CTP', 0.0)
            dt = L.get('HTDT', 0.0)
            hoanthue = L.get('HTTNCNNT', 0.0)
            tamung = L.get('TU', 0.0)
            thue = L.get('TTNCNPN', 0.0)
            net = p.x_amount_total
            dep = len(he.x_depend_ids.filtered(lambda x: x.is_depend)) if he.x_depend_ids else 0
            giam_gc = deduction_dependent * dep
            # Thu nhập chịu thuế (cột 35, AI) = Tổng thu nhập tháng − ăn ca − OT = Y − P − M
            # (khớp mẫu gốc: =Y-P-M). Ăn ca (an) và lương ngoài giờ (ot) KHÔNG chịu thuế.
            # Trừ BH + giảm trừ chuyển sang bước tính thuế (cột 45, AS) đúng như gốc.
            tnct = tong_thang - an - ot
            tntt = max(0.0, tnct - deduction_self - giam_gc - tongbh)
            # Thuế theo 5 bậc (khớp biểu của rule): 10tr/30tr/60tr/100tr - 5/10/20/30/35%
            _edges = [0.0, 10000000.0, 30000000.0, 60000000.0, 100000000.0, float('inf')]
            _rates = [0.05, 0.1, 0.2, 0.3, 0.35]
            bracket = [max(0.0, min(tntt, _edges[i + 1]) - _edges[i]) * _rates[i] for i in range(5)]
            # Đơn giá thực tế trong tháng = đơn giá nhân công CHƯA CỘNG CCDC
            # (Tổng chi phí/nhân viên : Giờ công thực tế) - khớp báo cáo cũ. KHÔNG
            # phải tổng giờ lương/giờ KPI paid_hours (bug cũ của nhánh feature).
            wc_data, tong_chi_phi, paidleave, gio_cong_thuc_te = p._get_wage_cost_data()
            dg_tt = (tong_chi_phi / gio_cong_thuc_te) if gio_cong_thuc_te else 0.0
            d = {
                2: he.name, 3: he.x_code, 4: he.job_title,
                5: lc, 6: kpidm, 7: tong, 8: gio_cs, 9: dg,
                10: I.get('OTHER_WORK_HOUR_CONVERTED', 0.0),  # J = tổng giờ quy đổi (khớp gốc)
                11: lc_tt, 12: kpi_tt, 13: ot, 14: dl, 15: tong_gio,
                16: an, 17: tts, 18: thuong_khac, 19: nvxs, 20: xang, 21: butru, 22: thieucong,
                23: tong_dot, 24: thuong_tt, 25: tong_thang,
                26: bhxh, 27: bhyt, 28: bhtn, 29: tongbh,
                30: cbhxh, 31: cbhyt, 32: cbhtn, 33: ctong, 34: tong_all_bh,
                35: tnct, 36: thue, 37: ctp, 38: dt, 39: hoanthue, 40: thuong_tt,
                41: tamung, 42: net, 43: dep, 44: giam_gc, 45: tntt,
                46: bracket[0], 47: bracket[1], 48: bracket[2], 49: bracket[3], 50: bracket[4],
                51: thue,
            }
            if with_cost:
                # 52-60: Thưởng tháng 13, các khoản phúc lợi phân bổ/12 tháng, tổng chi
                # phí/NV và giờ Paid leave/giờ công thực tế. Chỉ có ở bản
                # salary_ver2_cost.xlsx.
                d[52] = wc_data['thuongthang13'] if wc_data else 0.0
                d[53] = wc_data['dongphuc'] if wc_data else 0.0
                d[54] = wc_data['khamsuckhoe'] if wc_data else 0.0
                d[55] = wc_data['thuongngayle'] if wc_data else 0.0
                d[56] = wc_data['dulich'] if wc_data else 0.0
                d[57] = wc_data['congdoan'] if wc_data else 0.0
                d[58] = tong_chi_phi
                d[59] = paidleave
                d[60] = gio_cong_thuc_te
                d[61] = dg_tt
                # 62: đơn giá CCDC cá nhân (đ/giờ) - tính TRỰC TIẾP qua
                # get_personal_ccdc_rate(), KHÔNG sum project.wage.cost.depreciation_cost
                # (bảng đó có thể phát sinh dòng trùng khi 1 khoảng chấm công được gán
                # lại mã dự án, dẫn đến đếm giờ công 2 lần nếu tính theo tổng tiền).
                ccdc_rate = self.env['project.depreciation.line'].get_personal_ccdc_rate(
                    he, year, month) if 'project.depreciation.line' in self.env else 0.0
                d[62] = ccdc_rate or None
                # 63: đơn giá nhân công (đ/giờ, chỉ phiếu done)
                d[63] = unit_price_map.get(he.id) or None
            else:
                d[52] = dg_tt
            return d

        num_font = Font(size=12, name='Times New Roman')
        bold_font = Font(size=12, name='Times New Roman', bold=True)

        # Format kế toán (khớp mẫu gốc): số 0 hiển thị "-", ô rỗng để trống.
        ACC = '_(* #,##0_);_(* \\(#,##0\\);_(* "-"??_);_(@_)'
        ACC2 = '_(* #,##0.00_);_(* \\(#,##0.00\\);_(* "-"??_);_(@_)'

        def write_row(r, vals, bold=False):
            f = bold_font if bold else num_font
            for col in range(1, NUM_COLS + 1):
                cell = ws.cell(r, col)
                if col in vals:
                    cell.value = vals[col]
                cell.font = f
                if col in ACC2_COLS:
                    cell.number_format = ACC2
                elif col >= 5:
                    cell.number_format = ACC

        blocks = ['General', 'Maintenenance & Services', 'Facility Management']
        roman = ['I', 'II', 'III']
        grand = {col: 0.0 for col in SUM_COLS}

        cur = 7
        stt = 0  # STT đánh liên tục xuyên khối (khớp mẫu gốc)
        for bi, block in enumerate(blocks):
            bslips = payslips.filtered(
                lambda p: (p.employee_id.department_id.x_block_id.name or '') == block)
            # Sắp xếp trong khối theo mã hợp đồng tăng dần (thứ tự đăng ký HĐ) - khớp mẫu gốc
            bslips = bslips.sorted(key=lambda p: (p.contract_id.id or 0))
            vals_list = [row_vals(p) for p in bslips]
            bsum = {col: sum((v.get(col) or 0.0) for v in vals_list) for col in SUM_COLS}
            # Khớp gốc: số la mã ở cột 1, tên khối ở cột 2 (không gộp ô)
            header = {1: roman[bi], 2: block}
            header.update(bsum)
            write_row(cur, header, bold=True)
            for col in SUM_COLS:
                grand[col] += bsum[col]
            cur += 1
            for v in vals_list:
                stt += 1
                v[1] = stt
                write_row(cur, v)
                cur += 1

        gtot = {1: 'Tổng cộng'}
        gtot.update(grand)
        write_row(6, gtot, bold=True)
        # Không gộp ô ở dòng "Tổng cộng"/dòng nhóm (khớp mẫu gốc)

        last_row = cur + 1
        ws.cell(last_row, 2).value = 'Ngày: '
        ws.cell(last_row, 2).font = bold_font
        ws.cell(last_row, 2).alignment = Alignment(horizontal='right')
        ws.cell(last_row, 3).value = fields.datetime.now().date().strftime('%d/%m/%Y')
        ws.cell(last_row, 3).font = num_font
        ws.cell(last_row + 1, 3).value = 'NGƯỜI LẬP BẢNG'
        ws.cell(last_row + 1, 30).value = 'NGƯỜI PHÊ DUYỆT'
        ws.cell(last_row + 1, 3).font = ws.cell(last_row + 1, 30).font = bold_font
        ws.cell(last_row + 1, 3).alignment = ws.cell(last_row + 1, 30).alignment = Alignment(horizontal='center')

        self.__format_ws__(ws, cell_range='A2:%s%s' % (get_column_letter(NUM_COLS), cur - 1))

        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()
        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo chi phí nhân công.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id, attachment_id.name),
            'target': 'new',
        }


    def _salary_report_return(self, wb, name):
        """Lưu workbook -> ir.attachment và trả về action tải file."""
        stream = BytesIO(save_virtual_workbook(wb))
        attachment_id = self.env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(stream.getvalue()),
            'type': 'binary',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id, attachment_id.name),
            'target': 'new',
        }

    def get_excel_report_kpi(self, month, year, show_draft):
        """Báo cáo KPI - theo mẫu sheet 'Lương KPI'.

        Nguồn: bảng đánh giá KPI (hr.kpi.evaluation) đã đồng bộ với phiếu lương
        (paid_hours = giờ trả lương thực tế, kpi_salary khớp dòng LKPI).
        """
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/kpi_report.xlsx')
        ws = wb['KPI']
        month = int(month)
        ws.cell(5, 6).value = '%s/%s' % (month, year)   # THÁNG ... (F5)
        last_day = calendar.monthrange(year, month)[1]
        date_from = date(year, month, 1)
        date_to = date(year, month, last_day)
        states = ['draft', 'verify', 'done'] if show_draft else ['done']
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', states),
            ('date_from', '>=', date_from), ('date_to', '<=', date_to),
        ]).sorted(key=lambda p: (p.contract_id.id or 0))
        Eval = self.env['hr.kpi.evaluation'].sudo()

        num_font = Font(size=12, name='Times New Roman')
        bold_font = Font(size=12, name='Times New Roman', bold=True)
        ACC = '_(* #,##0_);_(* \\(#,##0\\);_(* "-"??_);_(@_)'
        SUM_COLS = (7, 8, 9, 11, 12)
        tot = {c: 0.0 for c in SUM_COLS}
        r = 7
        stt = 0
        for p in payslips:
            he = p.employee_id
            ev = Eval.search([('payslip_id', '=', p.id)], limit=1)
            if not ev:
                ev = Eval.search([('employee_id', '=', he.id),
                                  ('date_from', '=', date_from), ('date_to', '=', date_to)], limit=1)
            score = ev.score if ev else p._get_kpi_score()
            kpi_norm = ev.kpi_norm if ev else p.contract_id.kpi_norm
            paid = ev.paid_hours if ev else p._get_kpi_paid_hours()
            standard = ev.standard_hours if ev else p._get_kpi_standard_hours()
            coeff = ev.coefficient if ev else ((paid / standard) if standard else 0.0)
            kpi_salary = ev.kpi_salary if ev else 0.0
            stt += 1
            vals = {1: stt, 2: he.name, 3: he.x_code, 4: he.job_title,
                    5: score / 1000.0, 6: score, 7: kpi_norm, 8: paid, 9: standard,
                    10: coeff, 11: kpi_salary, 12: kpi_salary}
            for col in range(1, 14):
                cell = ws.cell(r, col)
                if col in vals:
                    cell.value = vals[col]
                cell.font = num_font
                if col == 5:
                    cell.number_format = '0%'
                elif col in (8, 9, 10):
                    cell.number_format = '#,##0.00'
                elif col in (7, 11, 12):
                    cell.number_format = ACC
            for c in SUM_COLS:
                tot[c] += vals.get(c) or 0.0
            r += 1
        # Dòng Tổng cộng
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ws.cell(r, 1).value = 'Tổng cộng'
        for col in range(1, 14):
            cell = ws.cell(r, col)
            if col in tot:
                cell.value = tot[col]
            cell.font = bold_font
            if col in (8, 9):
                cell.number_format = '#,##0.00'
            elif col in (7, 11, 12):
                cell.number_format = ACC
        last = r
        # Ép Times New Roman cho vùng header (giữ cỡ/đậm/màu)
        for rr in range(1, 7):
            for cc in range(1, 14):
                f = ws.cell(rr, cc).font
                ws.cell(rr, cc).font = Font(name='Times New Roman', size=f.size or 12,
                                            bold=f.bold, italic=f.italic, color=f.color,
                                            underline=f.underline)
        self.__format_ws__(ws, cell_range='A6:M' + str(last))
        return self._salary_report_return(wb, 'Báo cáo KPI.xlsx')

    def get_excel_report_meal(self, month, year, show_draft):
        """Báo cáo hỗ trợ ăn trưa - theo mẫu sheet 'TIỀN ĂN CA'.

        Số tiền = dòng lương HTAC (ăn ca) trên phiếu; số ngày tính hỗ trợ =
        tiền / định mức mỗi ngày (system param hr_payroll.meal_rate).
        """
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/meal_report.xlsx')
        ws = wb['Meal']
        month = int(month)
        last_day = calendar.monthrange(year, month)[1]
        date_from = date(year, month, 1)
        date_to = date(year, month, last_day)
        # số ngày công tiêu chuẩn tháng = số ngày không phải Chủ nhật
        std_days_month = sum(1 for d in range(1, last_day + 1)
                             if date(year, month, d).weekday() != 6)
        ws.cell(2, 8).value = '%s/%s' % (month, year)   # THÁNG-NĂM (H2)
        ws.cell(3, 8).value = std_days_month            # số ngày công tiêu chuẩn (H3)
        rate = self.env['hr.meal.rate'].get_rate(date_from)   # đơn giá ăn ca theo kỳ

        states = ['draft', 'verify', 'done'] if show_draft else ['done']
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', states),
            ('date_from', '>=', date_from), ('date_to', '<=', date_to),
        ]).sorted(key=lambda p: (p.contract_id.id or 0))

        num_font = Font(size=12, name='Times New Roman')
        bold_font = Font(size=12, name='Times New Roman', bold=True)
        ACC = '_(* #,##0_);_(* \\(#,##0\\);_(* "-"??_);_(@_)'
        SUM_COLS = (7, 8, 9)
        tot = {c: 0.0 for c in SUM_COLS}
        r = 5
        stt = 0
        for p in payslips:
            he = p.employee_id
            I = {i.input_type_id.code: i.amount for i in p.input_line_ids}
            htac = sum(l.total for l in p.line_ids if l.code == 'HTAC')
            std_days = I.get('OTHER_WORK_DAY_THEORY', 0.0) or std_days_month
            meal_days = round(htac / rate) if rate else 0
            no_meal_days = max(0.0, std_days - meal_days)
            stt += 1
            vals = {1: stt, 2: he.name, 3: he.x_code, 4: he.job_title,
                    5: rate, 6: std_days, 7: no_meal_days, 8: meal_days, 9: htac}
            for col in range(1, 11):
                cell = ws.cell(r, col)
                if col in vals:
                    cell.value = vals[col]
                cell.font = num_font
                if col in (5, 9):
                    cell.number_format = ACC
                elif col in (6, 7, 8):
                    cell.number_format = '#,##0'
            for c in SUM_COLS:
                tot[c] += vals.get(c) or 0.0
            r += 1
        # Dòng Tổng cộng
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ws.cell(r, 1).value = 'Tổng cộng'
        for col in range(1, 11):
            cell = ws.cell(r, col)
            if col in tot:
                cell.value = tot[col]
            cell.font = bold_font
            if col == 9:
                cell.number_format = ACC
            elif col in (7, 8):
                cell.number_format = '#,##0'
        last = r
        # Ép Times New Roman cho vùng header (giữ cỡ/đậm/màu)
        for rr in range(1, 5):
            for cc in range(1, 11):
                f = ws.cell(rr, cc).font
                ws.cell(rr, cc).font = Font(name='Times New Roman', size=f.size or 12,
                                            bold=f.bold, italic=f.italic, color=f.color,
                                            underline=f.underline)
        self.__format_ws__(ws, cell_range='A4:J' + str(last))
        return self._salary_report_return(wb, 'Báo cáo hỗ trợ ăn trưa.xlsx')

    def get_excel_report_salary(self, month, year, show_draft,month_to, year_to):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/salary.xlsx')
        ws = wb['Data']

        gluongchinh = 0.0
        gantrua = 0.0
        gnhao = 0.0
        gtongthunhaptheohd = 0.0
        ggiocongcoso = 0.0
        gdongia = 0.0
        ggiocongphanboGeneral = 0.0
        ggiocongphanboMaintenance = 0.0
        ggiocongphanboFacility = 0.0
        gtonggiocongthucte = 0.0
        gluongbosung = 0.0
        gluongphanboGeneral = 0.0
        gluongphanboMaintenance = 0.0
        gluongphanboFacility = 0.0
        gtongthunhaptheogiocongthucte = 0.0
        gthunhapkhac = 0.0
        gthuong_nvxs = 0.0
        ghotroxangxe = 0.0
        gbutruluong = 0.0
        ghotrotienluong = 0.0
        gtongthunhap = 0.0
        gluongdongbaohiem = 0.0
        gbhxh = 0.0
        gbhyt = 0.0
        gbhtn = 0.0
        gtonggiamtrubaohiem = 0.0
        gbhxh2 = 0.0
        gbhyt2 = 0.0
        gbhtn2 = 0.0
        gtonggiamtrubaohiem2 = 0.0
        gtongcacloaibaohiem = 0.0
        ghotronhaoduocmienthue = 0.0
        gthunhapchiuthue = 0.0
        gtrichthuetncn = 0.0
        gcongtacphi = 0.0
        ghoanthuetncn = 0.0
        gdatamung = 0.0
        gluongthuclinh = 0.0

        mluongchinh = 0.0
        mantrua = 0.0
        mnhao = 0.0
        mtongthunhaptheohd = 0.0
        mgiocongcoso = 0.0
        mdongia = 0.0
        mgiocongphanboGeneral = 0.0
        mgiocongphanboMaintenance = 0.0
        mgiocongphanboFacility = 0.0
        mtonggiocongthucte = 0.0
        mluongbosung = 0.0
        mluongphanboGeneral = 0.0
        mluongphanboMaintenance = 0.0
        mluongphanboFacility = 0.0
        mtongthunhaptheogiocongthucte = 0.0
        mthunhapkhac = 0.0
        mhotroxangxe = 0.0
        mbutruluong = 0.0
        mhotrotienluong = 0.0
        mtongthunhap = 0.0
        mluongdongbaohiem = 0.0
        mbhxh = 0.0
        mbhyt = 0.0
        mbhtn = 0.0
        mtonggiamtrubaohiem = 0.0
        mbhxh2 = 0.0
        mbhyt2 = 0.0
        mbhtn2 = 0.0
        mtonggiamtrubaohiem2 = 0.0
        mtongcacloaibaohiem = 0.0
        mhotronhaoduocmienthue = 0.0
        mthunhapchiuthue = 0.0
        mtrichthuetncn = 0.0
        mcongtacphi = 0.0
        mhoanthuetncn = 0.0
        mdatamung = 0.0
        mluongthuclinh = 0.0
        mthuong_nvxs = 0.0

        fluongchinh = 0.0
        fantrua = 0.0
        fnhao = 0.0
        ftongthunhaptheohd = 0.0
        fgiocongcoso = 0.0
        fdongia = 0.0
        fgiocongphanboGeneral = 0.0
        fgiocongphanboMaintenance = 0.0
        fgiocongphanboFacility = 0.0
        ftonggiocongthucte = 0.0
        fluongbosung = 0.0
        fluongphanboGeneral = 0.0
        fluongphanboMaintenance = 0.0
        fluongphanboFacility = 0.0
        ftongthunhaptheogiocongthucte = 0.0
        fthunhapkhac = 0.0
        fhotroxangxe = 0.0
        fbutruluong = 0.0
        fhotrotienluong = 0.0
        ftongthunhap = 0.0
        fluongdongbaohiem = 0.0
        fbhxh = 0.0
        fbhyt = 0.0
        fbhtn = 0.0
        ftonggiamtrubaohiem = 0.0
        fbhxh2 = 0.0
        fbhyt2 = 0.0
        fbhtn2 = 0.0
        ftonggiamtrubaohiem2 = 0.0
        ftongcacloaibaohiem = 0.0
        fhotronhaoduocmienthue = 0.0
        fthunhapchiuthue = 0.0
        ftrichthuetncn = 0.0
        fcongtacphi = 0.0
        fhoanthuetncn = 0.0
        fdatamung = 0.0
        fluongthuclinh = 0.0
        fthuong_nvxs = 0.0
        fthuongnong = 0.0
        gthuongnong = 0.0
        mthuongnong = 0.0
        fhotrodienthoai = 0.0
        ghotrodienthoai = 0.0
        mhotrodienthoai = 0.0
        ftongthunhaptrongthang =0
        gtongthunhaptrongthang =0
        mtongthunhaptrongthang =0

        query_thuong = """
        SELECT 
            he8.x_code AS code,
            SUM(CASE 
                    WHEN other8.state = 'approved'
                     AND other8.categ_type = 'bonus'
                    AND (TO_CHAR(other8.date, 'YYYYMM') >= '{1}{0:0>2}' and TO_CHAR(other8.date, 'YYYYMM') <= '{3}{2:0>2}')
                    THEN COALESCE(other8.amount, 0)
                    ELSE 0
                END) AS thunhapkhac,
            SUM(CASE 
                    WHEN other8.state = 'approved'
                     AND other8.categ_type = 'bonus'
                     AND hpoc8.code = 'TNVXS'
                    AND (TO_CHAR(other8.date, 'YYYYMM') >= '{1}{0:0>2}' and TO_CHAR(other8.date, 'YYYYMM') <= '{3}{2:0>2}')
                    THEN COALESCE(other8.amount, 0)
                    ELSE 0
                END) AS thuongnhanvienxuatsac
        FROM hr_employee he8
        LEFT JOIN hr_payroll_other other8 ON other8.employee_id = he8.id
        LEFT JOIN hr_payroll_other_category hpoc8 ON other8.categ_id = hpoc8.id 
        WHERE he8.x_code is not null
        GROUP BY he8.x_code;

        """.format(month, year, month_to, year_to)
        self._cr.execute(query_thuong)
        listthuong = self._cr.dictfetchall()

        queryGeneral = """
                    select 
                    he.name hovaten, 
                    he.x_code manhanvien, 
                    he.job_title chucvu, 
                    hc.x_insurance_wage luongchinh, 
                    hc.x_allowance_lunch antrua, 
                    hc.x_allowance_home nhao, 
                    hc.wage tongthunhaptheohd,
                    x5.amount giocongcoso,
                    case when hc.wage = 0 or hc.wage is null then hc.hourly_wage else hc.wage/x5.amount end as dongia,
                    case when hdb.name = 'General' then x2.amount else 0 end as Generall,
                    case when hdb.name = 'Maintenenance & Services' then x2.amount else 0  end as MaintenenanceServices,
                    case when hdb.name = 'Facility Management' then x2.amount else 0  end as FacilityManagement,
                    X2.amount tonggiocongthucte, 
                    hpl4.total luongbosung,
                    case when hdb.name = 'General' 
                        then 
                             hpl5.total
                         else 0 
                     end as ThuNhapGenerall,
                     case when hdb.name = 'Maintenenance & Services' 
                        then 
                             hpl5.total 
                         else 0 
                     end as ThuNhapMaintenenanceServices,
                      case when hdb.name = 'Facility Management' 
                        then 
                             hpl5.total
                         else 0 
                     end as ThuNhapFacilityManagement,
                    coalesce(hpl5.total,0) tongthunhaptheogiocongthucte,  
                    coalesce(hpl2.total,0) hotroxangxe, 
                    hpl3.total butruluongthang, 
                    coalesce(hpl4.total,0) luongbuducong,
                    (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0)) tongthunhap, 
                    hpl6.amount luongdongbaohiem,
                    hpl6.total BHXH, 
                    hpl7.total BHYT, 
                    hpl8.total BHTN, 
                    (hpl6.total+hpl7.total+hpl8.total) tong,
                    hpl6.amount*0.175 BHXHH, 
                    hpl6.amount*0.03 BHYTT, 
                    hpl6.amount*0.01 BHTNN, 
                    coalesce(hpl6.amount*0.215,0) tongg,
                    (hpl5.total+hpl.total+hpl2.total-hpl3.total+hpl4.total-hpl6.total-hpl7.total-hpl8.total) tongtienbh,
                    case 
                        when coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 > 0 
                        then coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 else 0 end as hotronhaoduocmienthue,
                    case 
                        when coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 > 0 
                        then 
                            case 
                            when (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-(coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15)
                                    -coalesce(hc.x_allowance_lunch,0) + coalesce(hpl13.total,0) > 0 
                            then
                                (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-(coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15)
                                    -coalesce(hc.x_allowance_lunch,0) + coalesce(hpl13.total,0) 
                            else 0 end
                    else 0
                    end as thunhapchiuthue,
                    hpl9.total trichthuetncn, 
                    coalesce(hpl10.total,0) congtacphi, 
                    hpl11.total hoanthuetncnnamtruoc, 
                    hpl12.total datamung,
                    coalesce(X6.amount,0) thuongnong,
                    coalesce(X7.amount,0) hotrodienthoai,
                    hp.x_amount_total luongthuclinh
                    from hr_payslip hp
                    left join hr_payslip_line hpl on hp.id = hpl.slip_id and hpl.name = 'Thưởng hoặc các khoản thu nhập khác'
                    left join hr_payslip_line hpl2 on hp.id = hpl2.slip_id  and hpl2.name = 'Hỗ trợ xăng xe'
                    left join hr_payslip_line hpl3 on hp.id = hpl3.slip_id  and hpl3.name = 'Bù/Trừ lương tháng'
                    left join hr_payslip_line hpl4 on hp.id = hpl4.slip_id  and hpl4.name = 'Hỗ trợ tiền lương bù đủ công' 
                    left join hr_payslip_line hpl5 on hp.id = hpl5.slip_id  and hpl5.name = 'Thu nhập theo giờ công thực tế' 
                    left join hr_payslip_line hpl6 on hp.id = hpl6.slip_id  and hpl6.name = 'Bảo hiểm xã hội'
                    left join hr_payslip_line hpl7 on hp.id = hpl7.slip_id and hpl7.name = 'Bảo hiểm y tế' 
                    left join hr_payslip_line hpl8 on hp.id = hpl8.slip_id and hpl8.name = 'Bảo hiểm thất nghiệp' 
                    left join hr_payslip_line hpl9 on hp.id = hpl9.slip_id  and hpl9.name = 'Thuế TNCN phải nộp' 
                    left join hr_payslip_line hpl10 on hp.id = hpl10.slip_id   and hpl10.name = 'Công tác phí'
                    left join hr_payslip_line hpl11 on hp.id = hpl11.slip_id   and hpl11.name = 'Hoàn thuế TNCN năm trước' 
                    left join hr_payslip_line hpl12 on hp.id = hpl12.slip_id  and hpl12.name = 'Tạm ứng' 
                    left join hr_payslip_line hpl13 on hp.id = hpl13.slip_id  and hpl13.name = 'Các khoản thưởng nóng'
                    left join hr_employee he on hp.employee_id = he.id
                    left join hr_contract hc on hp.contract_id = hc.id
                    left join (select hpi.*,hpit.code as codehpit from hr_payslip_input hpi left join hr_payslip_input_type hpit on hpi.input_type_id = hpit.id)X1 on hp.id = X1.payslip_id and X1.codehpit = 'OTHER_WORK_DAY_THEORY'
                    left join (select hpi2.*,hpit2.code as codehpit from hr_payslip_input hpi2 left join hr_payslip_input_type hpit2 on hpi2.input_type_id = hpit2.id)X2 on hp.id = X2.payslip_id and X2.codehpit = 'OTHER_WORK_HOUR_CONVERTED'
                    left join (select hpi3.*,hpit3.code as codehpit from hr_payslip_input hpi3 left join hr_payslip_input_type hpit3 on hpi3.input_type_id = hpit3.id)X3 on hp.id = X3.payslip_id and X3.codehpit = 'OTHER_WORK_HOUR_SUPPORT'
                    left join (select hpi4.*,hpit4.code as codehpit from hr_payslip_input hpi4 left join hr_payslip_input_type hpit4 on hpi4.input_type_id = hpit4.id)X4 on hp.id = X4.payslip_id and X4.codehpit = 'OTHER_WAGE_TOTAL'
                                    left join (select hpi5.*,hpit5.code as codehpit from hr_payslip_input hpi5 left join hr_payslip_input_type hpit5 on hpi5.input_type_id = hpit5.id)X5 on hp.id = X5.payslip_id and X5.codehpit = 'OTHER_WORK_HOUR_THEORY'
                left join (select hpi6.*,hpit6.code as codehpit from hr_payslip_input hpi6 left join hr_payslip_input_type hpit6 on hpi6.input_type_id = hpit6.id)X6 on hp.id = X6.payslip_id and X6.codehpit = 'OTHER_BONUS_INSTANT'
                left join (select hpi7.*,hpit7.code as codehpit from hr_payslip_input hpi7 left join hr_payslip_input_type hpit7 on hpi7.input_type_id = hpit7.id)X7 on hp.id = X7.payslip_id and X7.codehpit = 'OTHER_MOBILE'
                left join hr_department hd on he.department_id = hd.id
                left join hr_department_block hdb on hdb.id = hd.x_block_id 
                where hp.state in {2}
                 and TO_CHAR(hp.date_from, 'YYYYMM') >= '{1}{0:0>2}'
                 and TO_CHAR(hp.date_to, 'YYYYMM') <= '{4}{3:0>2}'
                    and hdb.name = 'General'

                                """.format(month, year, "('draft','verify','done')" if show_draft else "('done')", month_to, year_to)
        self._cr.execute(queryGeneral)
        listGenerals = self._cr.dictfetchall()
        listGenerals = self.merge_data(listGenerals)
        row = 8
        ws.cell(1, 9).value = f"Từ {month} - {year} đến {month_to} - {year_to}"
        ws.merge_cells('A6:D6')
        ws.merge_cells('A7:D7')
        ws.cell(6, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(7, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(6, 1).alignment = Alignment(horizontal='center')
        ws.cell(6, 1).value = 'Tổng'
        ws.cell(7, 1).value = 'General'

        for index, l in enumerate(listGenerals):
            ws.cell(row, 1).font = ws.cell(row, 2).font = ws.cell(row, 3).font = ws.cell(row, 4).font = ws.cell(row,
                                                                                                                5).font = ws.cell(
                row, 6).font = ws.cell(row, 7).font = ws.cell(row, 8).font = ws.cell(row, 9).font = ws.cell(row,
                                                                                                            10).font = ws.cell(
                row, 11).font = ws.cell(row, 12).font = ws.cell(row, 13).font = ws.cell(row, 14).font = ws.cell(row,
                                                                                                                15).font = ws.cell(
                row, 16).font = ws.cell(row, 17).font = ws.cell(row, 18).font = ws.cell(row, 19).font = ws.cell(row,
                                                                                                                20).font = ws.cell(
                row, 21).font = ws.cell(row, 22).font = ws.cell(row, 23).font = ws.cell(row, 24).font = ws.cell(row,
                                                                                                                25).font = ws.cell(
                row, 26).font = ws.cell(row, 27).font = ws.cell(row, 28).font = ws.cell(row, 29).font = ws.cell(row,
                                                                                                                30).font = ws.cell(
                row, 31).font = ws.cell(row, 32).font = ws.cell(row, 33).font = ws.cell(row, 34).font = ws.cell(row,
                                                                                                                35).font = ws.cell(
                row, 36).font = ws.cell(row, 37).font = ws.cell(row, 38).font = ws.cell(row, 39).font = ws.cell(row,
                                                                                                                40).font = ws.cell(
                row, 41).font = ws.cell(row, 42).font = ws.cell(row, 43).font = Font(size=12, name='Times New Roman')

            ws.cell(row, 5).number_format = ws.cell(row, 6).number_format = ws.cell(row, 7).number_format = ws.cell(row, 8).number_format = ws.cell(
                row, 10).number_format = ws.cell(row, 11).number_format = ws.cell(row, 12).number_format = ws.cell(row,
                                                                                                                   13).number_format = ws.cell(
                row, 14).number_format = ws.cell(row, 15).number_format = ws.cell(row, 16).number_format = ws.cell(row,
                                                                                                                   17).number_format = ws.cell(
                row, 18).number_format = ws.cell(row, 19).number_format = ws.cell(row, 20).number_format = ws.cell(row,
                                                                                                                   21).number_format = ws.cell(
                row, 22).number_format = ws.cell(row, 23).number_format = ws.cell(row, 24).number_format = ws.cell(row,
                                                                                                                   25).number_format = ws.cell(
                row, 26).number_format = ws.cell(row, 27).number_format = ws.cell(row, 28).number_format = ws.cell(row,
                                                                                                                   29).number_format = ws.cell(
                row, 30).number_format = ws.cell(row, 31).number_format = ws.cell(row, 32).number_format = ws.cell(row,
                                                                                                                   33).number_format = ws.cell(
                row, 34).number_format = ws.cell(row, 35).number_format = ws.cell(row, 36).number_format = ws.cell(row,
                                                                                                                   37).number_format = ws.cell(
                row, 38).number_format = ws.cell(row, 39).number_format = ws.cell(row, 40).number_format = ws.cell(row,
                                                                                                                   41).number_format = ws.cell(row, 42).number_format = ws.cell(row, 43).number_format = '#,##'

            ws.cell(row, 9).number_format = ws.cell(row, 11).number_format = ws.cell(row,
                                                                                                                12).number_format = ws.cell(
                row, 13).number_format = '#,##0.00'

            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['hovaten'] or ''
            ws.cell(row, 3).value = l['manhanvien'] or ''
            ws.cell(row, 4).value = l['chucvu'] or ''
            ws.cell(row, 5).value = l['luongchinh'] or ''
            gluongchinh += l['luongchinh']
            ws.cell(row, 6).value = l['antrua'] or ''
            gantrua += l['antrua'] or 0.0
            ws.cell(row, 7).value = l['nhao'] or ''
            gnhao += l['nhao'] or 0.0
            ws.cell(row, 8).value = l['tongthunhaptheohd'] or ''
            gtongthunhaptheohd += l['tongthunhaptheohd'] or 0.0
            ws.cell(row, 9).value = l['giocongcoso'] or ''
            ggiocongcoso += l['giocongcoso'] or 0.0
            ws.cell(row, 10).value = l['dongia'] or ''
            gdongia += l['dongia'] or 0.0
            ws.cell(row, 11).value = l['generall'] or ''
            ggiocongphanboGeneral += l['generall'] or 0.0
            ws.cell(row, 12).value = l['maintenenanceservices'] or ''
            ggiocongphanboMaintenance += l['maintenenanceservices'] or 0.0
            ws.cell(row, 13).value = l['facilitymanagement'] or ''
            ggiocongphanboFacility += l['facilitymanagement'] or 0.0
            ws.cell(row, 14).value = l['tonggiocongthucte'] or ''
            gtonggiocongthucte += l['tonggiocongthucte'] or 0.0
            # ws.cell(row, 15).value = l['luongbosung'] or ''
            # gluongbosung += l['luongbosung'] or 0.0
            ws.cell(row, 15).value = l['thunhapgenerall'] or ''
            gluongphanboGeneral += l['thunhapgenerall'] or 0.0
            ws.cell(row, 16).value = l['thunhapmaintenenanceservices'] or ''
            gluongphanboMaintenance += l['thunhapmaintenenanceservices'] or 0.0
            ws.cell(row, 17).value = l['thunhapfacilitymanagement'] or ''
            gluongphanboFacility += l['thunhapfacilitymanagement'] or 0.0
            ws.cell(row, 18).value = l['tongthunhaptheogiocongthucte'] or ''
            gtongthunhaptheogiocongthucte += l['tongthunhaptheogiocongthucte'] or 0.0
            thuong_nvxs  = next((item.get('thuongnhanvienxuatsac') for item in listthuong if item['code'] == l.get('manhanvien')), 0.0)
            ws.cell(row, 19).value = thuong_nvxs or ''
            gthuong_nvxs += thuong_nvxs or 0.0
            thunhapkhac = next((item.get('thunhapkhac') for item in listthuong if item['code'] == l.get('manhanvien')), 0.0)
            ws.cell(row, 20).value = thunhapkhac - thuong_nvxs or ''
            gthunhapkhac += thunhapkhac - thuong_nvxs or 0.0
            ws.cell(row, 21).value = l['hotroxangxe'] or ''
            ghotroxangxe += l['hotroxangxe'] or 0.0
            ws.cell(row, 22).value = l['butruluongthang'] or ''
            gbutruluong += l['butruluongthang'] or 0.0
            ws.cell(row, 23).value = l['luongbuducong'] or ''
            ghotrotienluong += l['luongbuducong'] or 0.0
            ws.cell(row, 24).value = l['tongthunhap'] or ''
            gtongthunhap += l['tongthunhap'] or 0.0
            ws.cell(row, 25).value = l['thuongnong'] or ''
            gthuongnong += l['thuongnong'] or 0.0
            ws.cell(row, 26).value = l['thuongnong'] + l['tongthunhap'] or ''
            gtongthunhaptrongthang += l['thuongnong'] + l['tongthunhap'] or 0.0
            # ws.cell(row, 27).value = l['luongdongbaohiem'] or ''
            # gluongdongbaohiem += l['luongdongbaohiem']
            ws.cell(row, 27).value = l['bhxh'] or ''
            gbhxh += l['bhxh'] or 0.0
            ws.cell(row, 28).value = l['bhyt'] or ''
            gbhyt += l['bhyt'] or 0.0
            ws.cell(row, 29).value = l['bhtn'] or ''
            gbhtn += l['bhtn'] or 0.0
            ws.cell(row, 30).value = l['tong'] or ''
            gtonggiamtrubaohiem += l['tong'] or 0.0
            ws.cell(row, 31).value = l['bhxhh'] or ''
            gbhxh2 += l['bhxhh'] or 0.0
            ws.cell(row, 32).value = l['bhytt'] or ''
            gbhyt2 += l['bhytt'] or 0.0
            ws.cell(row, 33).value = l['bhtn'] or ''
            gbhtn2 += l['bhtn'] or 0.0
            ws.cell(row, 34).value = l['tongg'] or ''
            gtonggiamtrubaohiem2 += l['tongg'] or 0.0
            # ws.cell(row, 34).value = l['tongtienbh'] or ''
            ws.cell(row, 35).value = "=sum(AD%s,AH%s)" % (row, row)
            gtongcacloaibaohiem += l['tongtienbh'] or 0.0
            hotronhaoduocmienthue ,thunhapchiuthue=  self._calculate_aj_ak_values(l)
            ws.cell(row, 36).value = hotronhaoduocmienthue or ''
            ghotronhaoduocmienthue += hotronhaoduocmienthue or 0.0
            ws.cell(row, 37).value = thunhapchiuthue or ''
            gthunhapchiuthue += thunhapchiuthue or 0.0
            ws.cell(row, 38).value = l['trichthuetncn'] or ''
            gtrichthuetncn += l['trichthuetncn'] or 0.0
            ws.cell(row, 39).value = l['congtacphi'] or ''
            gcongtacphi += l['congtacphi'] or 0.0
            ws.cell(row, 40).value = l['hotrodienthoai'] or ''
            ghotrodienthoai += l['hotrodienthoai'] or 0.0
            ws.cell(row, 41).value = l['hoanthuetncnnamtruoc'] or ''
            ghoanthuetncn += l['hoanthuetncnnamtruoc'] or 0.0
            ws.cell(row, 42).value = l['datamung'] or ''
            gdatamung += l['datamung'] or 0.0
            ws.cell(row, 43).value = l['luongthuclinh'] or ''
            gluongthuclinh += l['luongthuclinh'] or 0.0
            index += 1
            row += 1
        ws.cell(7, 5).font = ws.cell(7, 6).font = ws.cell(7, 7).font = ws.cell(7, 8).font = ws.cell(7,
                                                                                                    9).font = ws.cell(7,
                                                                                                                      10).font = ws.cell(
            7, 11).font = ws.cell(7, 12).font = ws.cell(7, 13).font = ws.cell(7, 14).font = ws.cell(7,
                                                                                                    15).font = ws.cell(
            7, 16).font = ws.cell(7, 17).font = ws.cell(7, 18).font = ws.cell(7, 19).font = ws.cell(7,
                                                                                                    20).font = ws.cell(
            7, 21).font = ws.cell(7, 22).font = ws.cell(7, 23).font = ws.cell(7, 24).font = ws.cell(7,
                                                                                                    25).font = ws.cell(
            7, 26).font = ws.cell(7, 27).font = ws.cell(7, 28).font = ws.cell(7, 29).font = ws.cell(7,
                                                                                                    30).font = ws.cell(
            7, 31).font = ws.cell(7, 32).font = ws.cell(7, 33).font = ws.cell(7, 34).font = ws.cell(7,
                                                                                                    35).font = ws.cell(
            7, 36).font = ws.cell(7, 37).font = ws.cell(7, 38).font = ws.cell(7, 39).font = ws.cell(7,
                                                                                                    40).font = ws.cell(
            7, 41).font = ws.cell(7, 42).font = ws.cell(7, 43).font = Font(size=12, name='Times New Roman', bold=True)

        ws.cell(7, 5).number_format = ws.cell(7, 6).number_format = ws.cell(7, 7).number_format = ws.cell(
            7,
            9).number_format = ws.cell(7, 14).number_format = ws.cell(
            7,
            15).number_format = ws.cell(
            7, 16).number_format = ws.cell(7, 17).number_format = ws.cell(7, 18).number_format = ws.cell(7,
                                                                                                         19).number_format = ws.cell(
            7,
            20).number_format = ws.cell(
            7, 21).number_format = ws.cell(7, 22).number_format = ws.cell(7, 23).number_format = ws.cell(7,
                                                                                                         24).number_format = ws.cell(
            7,
            25).number_format = ws.cell(
            7, 26).number_format = ws.cell(7, 27).number_format = ws.cell(7, 28).number_format = ws.cell(7,
                                                                                                         29).number_format = ws.cell(
            7, 30).number_format = ws.cell(
            7, 31).number_format = ws.cell(7, 32).number_format = ws.cell(7, 33).number_format = ws.cell(7,
                                                                                                         34).number_format = ws.cell(
            7, 35).number_format = ws.cell(
            7, 36).number_format = ws.cell(7, 37).number_format = ws.cell(7, 38).number_format = ws.cell(7,
                                                                                                         39).number_format = ws.cell(
            7,40).number_format = ws.cell(7, 41).number_format = ws.cell(7, 42).number_format = ws.cell(7, 43).number_format = '#,##'

        ws.cell(7, 9).number_format = ws.cell(7, 11).number_format = ws.cell(7, 12).number_format = ws.cell(7, 13).number_format = '#,##0.00'

        ws.cell(7, 5).value = gluongchinh
        ws.cell(7, 6).value = gantrua
        ws.cell(7, 7).value = gnhao
        ws.cell(7, 8).value = gtongthunhaptheohd
        ws.cell(7, 9).value = ggiocongcoso
        ws.cell(7, 10).value = gdongia
        ws.cell(7, 11).value = ggiocongphanboGeneral
        ws.cell(7, 12).value = ggiocongphanboMaintenance
        ws.cell(7, 13).value = ggiocongphanboFacility
        ws.cell(7, 14).value = gtonggiocongthucte
        # ws.cell(7, 15).value = gluongbosung
        ws.cell(7, 15).value = gluongphanboGeneral
        ws.cell(7, 16).value = gluongphanboMaintenance
        ws.cell(7, 17).value = gluongphanboFacility
        ws.cell(7, 18).value = gtongthunhaptheogiocongthucte
        ws.cell(7, 19).value = gthuong_nvxs
        ws.cell(7, 20).value = gthunhapkhac
        ws.cell(7, 21).value = ghotroxangxe
        ws.cell(7, 22).value = gbutruluong
        ws.cell(7, 23).value = ghotrotienluong
        ws.cell(7, 24).value = gtongthunhap
        ws.cell(7, 25).value = gthuongnong
        ws.cell(7, 26).value = gtongthunhaptrongthang
        # ws.cell(7, 27).value = gluongdongbaohiem
        ws.cell(7, 27).value = gbhxh
        ws.cell(7, 28).value = gbhyt
        ws.cell(7, 29).value = gbhtn
        ws.cell(7, 30).value = gtonggiamtrubaohiem
        ws.cell(7, 31).value = gbhxh2
        ws.cell(7, 32).value = gbhyt2
        ws.cell(7, 33).value = gbhtn2
        ws.cell(7, 34).value = gtonggiamtrubaohiem2
        ws.cell(7, 35).value = "=sum(AD%s,AH%s)" % (7, 7)
        ws.cell(7, 36).value = ghotronhaoduocmienthue
        ws.cell(7, 37).value = gthunhapchiuthue
        ws.cell(7, 38).value = gtrichthuetncn
        ws.cell(7, 39).value = gcongtacphi
        ws.cell(7, 40).value = ghotrodienthoai
        ws.cell(7, 41).value = ghoanthuetncn
        ws.cell(7, 42).value = gdatamung
        ws.cell(7, 43).value = gluongthuclinh

        queryMaintenenance = """
                select 
                he.name hovaten, 
                he.x_code manhanvien, 
                he.job_title chucvu, 
                hc.x_insurance_wage luongchinh, 
                hc.x_allowance_lunch antrua, 
                hc.x_allowance_home nhao, 
                hc.wage tongthunhaptheohd,
                x5.amount giocongcoso,
                case when hc.wage = 0 or hc.wage is null then hc.hourly_wage else hc.wage/x5.amount end as dongia,
                case when hdb.name = 'General' then x2.amount else 0 end as Generall,
                case when hdb.name = 'Maintenenance & Services' then x2.amount else 0  end as MaintenenanceServices,
                case when hdb.name = 'Facility Management' then x2.amount else 0  end as FacilityManagement,
                X2.amount tonggiocongthucte, 
                hpl4.total luongbosung,
                case when hdb.name = 'General' 
                    then 
                         hpl5.total
                     else 0 
                 end as ThuNhapGenerall,
                 case when hdb.name = 'Maintenenance & Services' 
                    then 
                         hpl5.total 
                     else 0 
                 end as ThuNhapMaintenenanceServices,
                  case when hdb.name = 'Facility Management' 
                    then 
                         hpl5.total
                     else 0 
                 end as ThuNhapFacilityManagement,
                coalesce(hpl5.total,0) tongthunhaptheogiocongthucte,
                coalesce(hpl2.total,0) hotroxangxe, 
                hpl3.total butruluongthang, 
                coalesce(hpl4.total,0) luongbuducong,
                (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0)) tongthunhap, 
                hpl6.amount luongdongbaohiem,
                hpl6.total BHXH, 
                hpl7.total BHYT, 
                hpl8.total BHTN, 
                (hpl6.total+hpl7.total+hpl8.total) tong,
                hpl6.amount*0.175 BHXHH, 
                hpl6.amount*0.03 BHYTT, 
                hpl6.amount*0.01 BHTNN, 
                coalesce(hpl6.amount*0.215,0) tongg,
                (hpl5.total+hpl.total+hpl2.total-hpl3.total+hpl4.total-hpl6.total-hpl7.total-hpl8.total) tongtienbh,
                case 
                    when coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 > 0 
                    then coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 else 0 end as hotronhaoduocmienthue,
                case 
                    when coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 > 0 
                    then 
                        case 
                        when (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-(coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15)
                                -coalesce(hc.x_allowance_lunch,0) + coalesce(hpl13.total,0) > 0 
                        then
                            (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-(coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15)
                                -coalesce(hc.x_allowance_lunch,0) + coalesce(hpl13.total,0) 
                        else 0 end
                else 0
                end as thunhapchiuthue,
                hpl9.total trichthuetncn, 
                coalesce(hpl10.total,0) congtacphi, 
                hpl11.total hoanthuetncnnamtruoc, 
                hpl12.total datamung,
                coalesce(X6.amount,0) thuongnong,
                coalesce(X7.amount,0) hotrodienthoai,
                hp.x_amount_total luongthuclinh
                from hr_payslip hp
                left join hr_payslip_line hpl on hp.id = hpl.slip_id and hpl.name = 'Thưởng hoặc các khoản thu nhập khác'
                left join hr_payslip_line hpl2 on hp.id = hpl2.slip_id  and hpl2.name = 'Hỗ trợ xăng xe'
                left join hr_payslip_line hpl3 on hp.id = hpl3.slip_id  and hpl3.name = 'Bù/Trừ lương tháng'
                left join hr_payslip_line hpl4 on hp.id = hpl4.slip_id  and hpl4.name = 'Hỗ trợ tiền lương bù đủ công' 
                left join hr_payslip_line hpl5 on hp.id = hpl5.slip_id  and hpl5.name = 'Thu nhập theo giờ công thực tế' 
                left join hr_payslip_line hpl6 on hp.id = hpl6.slip_id  and hpl6.name = 'Bảo hiểm xã hội'
                left join hr_payslip_line hpl7 on hp.id = hpl7.slip_id and hpl7.name = 'Bảo hiểm y tế' 
                left join hr_payslip_line hpl8 on hp.id = hpl8.slip_id and hpl8.name = 'Bảo hiểm thất nghiệp' 
                left join hr_payslip_line hpl9 on hp.id = hpl9.slip_id  and hpl9.name = 'Thuế TNCN phải nộp' 
                left join hr_payslip_line hpl10 on hp.id = hpl10.slip_id   and hpl10.name = 'Công tác phí'
                left join hr_payslip_line hpl11 on hp.id = hpl11.slip_id   and hpl11.name = 'Hoàn thuế TNCN năm trước' 
                left join hr_payslip_line hpl12 on hp.id = hpl12.slip_id  and hpl12.name = 'Tạm ứng' 
                left join hr_payslip_line hpl13 on hp.id = hpl13.slip_id  and hpl13.name = 'Các khoản thưởng nóng'
                left join hr_employee he on hp.employee_id = he.id
                left join hr_contract hc on hp.contract_id = hc.id
                left join (select hpi.*,hpit.code as codehpit from hr_payslip_input hpi left join hr_payslip_input_type hpit on hpi.input_type_id = hpit.id)X1 on hp.id = X1.payslip_id and X1.codehpit = 'OTHER_WORK_DAY_THEORY'
                left join (select hpi2.*,hpit2.code as codehpit from hr_payslip_input hpi2 left join hr_payslip_input_type hpit2 on hpi2.input_type_id = hpit2.id)X2 on hp.id = X2.payslip_id and X2.codehpit = 'OTHER_WORK_HOUR_CONVERTED'
                left join (select hpi3.*,hpit3.code as codehpit from hr_payslip_input hpi3 left join hr_payslip_input_type hpit3 on hpi3.input_type_id = hpit3.id)X3 on hp.id = X3.payslip_id and X3.codehpit = 'OTHER_WORK_HOUR_SUPPORT'
                left join (select hpi4.*,hpit4.code as codehpit from hr_payslip_input hpi4 left join hr_payslip_input_type hpit4 on hpi4.input_type_id = hpit4.id)X4 on hp.id = X4.payslip_id and X4.codehpit = 'OTHER_WAGE_TOTAL'
                left join (select hpi5.*,hpit5.code as codehpit from hr_payslip_input hpi5 left join hr_payslip_input_type hpit5 on hpi5.input_type_id = hpit5.id)X5 on hp.id = X5.payslip_id and X5.codehpit = 'OTHER_WORK_HOUR_THEORY'
                left join (select hpi6.*,hpit6.code as codehpit from hr_payslip_input hpi6 left join hr_payslip_input_type hpit6 on hpi6.input_type_id = hpit6.id)X6 on hp.id = X6.payslip_id and X6.codehpit = 'OTHER_BONUS_INSTANT'
                left join (select hpi7.*,hpit7.code as codehpit from hr_payslip_input hpi7 left join hr_payslip_input_type hpit7 on hpi7.input_type_id = hpit7.id)X7 on hp.id = X7.payslip_id and X7.codehpit = 'OTHER_MOBILE'
                left join hr_department hd on he.department_id = hd.id
                left join hr_department_block hdb on hdb.id = hd.x_block_id 
                where hp.state in {2}
                and TO_CHAR(hp.date_from, 'YYYYMM') >= '{1}{0:0>2}'
                and TO_CHAR(hp.date_to, 'YYYYMM') <= '{4}{3:0>2}'
                and hdb.name = 'Maintenenance & Services'
                                        """.format(month, year, "('draft','verify','done')" if show_draft else "('done')",month_to, year_to)
        self._cr.execute(queryMaintenenance)
        listMaintenenances = self._cr.dictfetchall()
        listMaintenenances = self.merge_data(listMaintenenances)
        row = row + 1
        A = 'A' + str(row) + ':D' + str(row)
        ws.merge_cells(A)
        ws.cell(row, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 1).value = 'Maintenenance & Services'
        row = row + 1
        indexx = 0
        for index, l in enumerate(listMaintenenances):
            ws.cell(row, 1).font = ws.cell(row, 2).font = ws.cell(row, 3).font = ws.cell(row, 4).font = ws.cell(row,
                                                                                                                5).font = ws.cell(
                row, 6).font = ws.cell(row, 7).font = ws.cell(row, 8).font = ws.cell(row, 9).font = ws.cell(row,
                                                                                                            10).font = ws.cell(
                row, 11).font = ws.cell(row, 12).font = ws.cell(row, 13).font = ws.cell(row, 14).font = ws.cell(row,
                                                                                                                15).font = ws.cell(
                row, 16).font = ws.cell(row, 17).font = ws.cell(row, 18).font = ws.cell(row, 19).font = ws.cell(row,
                                                                                                                20).font = ws.cell(
                row, 21).font = ws.cell(row, 22).font = ws.cell(row, 23).font = ws.cell(row, 24).font = ws.cell(row,
                                                                                                                25).font = ws.cell(
                row, 26).font = ws.cell(row, 27).font = ws.cell(row, 28).font = ws.cell(row, 29).font = ws.cell(row,
                                                                                                                30).font = ws.cell(
                row, 31).font = ws.cell(row, 32).font = ws.cell(row, 33).font = ws.cell(row, 34).font = ws.cell(row,
                                                                                                                35).font = ws.cell(
                row, 36).font = ws.cell(row, 37).font = ws.cell(row, 38).font = ws.cell(row, 39).font = ws.cell(row,
                                                                                                                40).font = ws.cell(
                row, 41).font = ws.cell(row, 42).font = ws.cell(row, 43).font = Font(size=12, name='Times New Roman')

            ws.cell(row, 5).number_format = ws.cell(row, 6).number_format = ws.cell(row, 7).number_format = ws.cell(row,
                                                                                                                    8).number_format = ws.cell(
                row, 10).number_format = ws.cell(row, 11).number_format = ws.cell(row, 12).number_format = ws.cell(row,
                                                                                                                   13).number_format = ws.cell(
                row, 14).number_format = ws.cell(row, 15).number_format = ws.cell(row, 16).number_format = ws.cell(row,
                                                                                                                   17).number_format = ws.cell(
                row, 18).number_format = ws.cell(row, 19).number_format = ws.cell(row, 20).number_format = ws.cell(row,
                                                                                                                   21).number_format = ws.cell(
                row, 22).number_format = ws.cell(row, 23).number_format = ws.cell(row, 24).number_format = ws.cell(row,
                                                                                                                   25).number_format = ws.cell(
                row, 26).number_format = ws.cell(row, 27).number_format = ws.cell(row, 28).number_format = ws.cell(row,
                                                                                                                   29).number_format = ws.cell(
                row, 30).number_format = ws.cell(row, 31).number_format = ws.cell(row, 32).number_format = ws.cell(row,
                                                                                                                   33).number_format = ws.cell(
                row, 34).number_format = ws.cell(row, 35).number_format = ws.cell(row, 36).number_format = ws.cell(row,
                                                                                                                   37).number_format = ws.cell(
                row, 38).number_format = ws.cell(row, 39).number_format = ws.cell(row, 40).number_format = ws.cell(row,
                                                                                                                   41).number_format = ws.cell(row, 42).number_format = ws.cell(row, 43).number_format = '#,##'

            ws.cell(row, 9).number_format = ws.cell(row, 11).number_format = ws.cell(row,
                                                                                                                12).number_format = ws.cell(
                row, 13).number_format = '#,##0.00'

            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['hovaten'] or ''
            ws.cell(row, 3).value = l['manhanvien'] or ''
            ws.cell(row, 4).value = l['chucvu'] or ''
            ws.cell(row, 5).value = l['luongchinh'] or ''
            mluongchinh += l['luongchinh']
            ws.cell(row, 6).value = l['antrua'] or ''
            mantrua += l['antrua'] or 0.0
            ws.cell(row, 7).value = l['nhao'] or ''
            mnhao += l['nhao'] or 0.0
            ws.cell(row, 8).value = l['tongthunhaptheohd'] or ''
            mtongthunhaptheohd += l['tongthunhaptheohd'] or 0.0
            ws.cell(row, 9).value = l['giocongcoso'] or ''
            mgiocongcoso += l['giocongcoso'] or 0.0
            ws.cell(row, 10).value = l['dongia'] or ''
            mdongia += l['dongia'] or 0.0
            ws.cell(row, 11).value = l['generall'] or ''
            mgiocongphanboGeneral += l['generall'] or 0.0
            ws.cell(row, 12).value = l['maintenenanceservices'] or ''
            mgiocongphanboMaintenance += l['maintenenanceservices'] or 0.0
            ws.cell(row, 13).value = l['facilitymanagement'] or ''
            mgiocongphanboFacility += l['facilitymanagement'] or 0.0
            ws.cell(row, 14).value = l['tonggiocongthucte'] or ''
            mtonggiocongthucte += l['tonggiocongthucte'] or 0.0
            # ws.cell(row, 15).value = l['luongbosung'] or ''
            # mluongbosung += l['luongbosung'] or 0.0
            ws.cell(row, 15).value = l['thunhapgenerall'] or ''
            mluongphanboGeneral += l['thunhapgenerall'] or 0.0
            ws.cell(row, 16).value = l['thunhapmaintenenanceservices'] or ''
            mluongphanboMaintenance += l['thunhapmaintenenanceservices'] or 0.0
            ws.cell(row, 17).value = l['thunhapfacilitymanagement'] or ''
            mluongphanboFacility += l['thunhapfacilitymanagement'] or 0.0
            ws.cell(row, 18).value = l['tongthunhaptheogiocongthucte'] or ''
            mtongthunhaptheogiocongthucte += l['tongthunhaptheogiocongthucte'] or 0.0
            thuong_nvxs = next(
                (item.get('thuongnhanvienxuatsac') for item in listthuong if item['code'] == l.get('manhanvien')), 0.0)
            ws.cell(row, 19).value = thuong_nvxs or ''
            mthuong_nvxs += thuong_nvxs or 0.0
            thunhapkhac = next((item.get('thunhapkhac') for item in listthuong if item['code'] == l.get('manhanvien')),
                               0.0)
            ws.cell(row, 20).value = thunhapkhac - thuong_nvxs or ''
            mthunhapkhac += thunhapkhac - thuong_nvxs or 0.0
            ws.cell(row, 21).value = l['hotroxangxe'] or ''
            mhotroxangxe += l['hotroxangxe'] or 0.0
            ws.cell(row, 22).value = l['butruluongthang'] or ''
            mbutruluong += l['butruluongthang'] or 0.0
            ws.cell(row, 23).value = l['luongbuducong'] or ''
            mhotrotienluong += l['luongbuducong'] or 0.0
            ws.cell(row, 24).value = l['tongthunhap'] or ''
            mtongthunhap += l['tongthunhap'] or 0.0
            ws.cell(row, 25).value = l['thuongnong'] or ''
            mthuongnong += l['thuongnong'] or 0.0
            ws.cell(row, 26).value = l['thuongnong'] + l['tongthunhap'] or ''
            mtongthunhaptrongthang += l['thuongnong'] + l['tongthunhap'] or 0.0
            # ws.cell(row, 27).value = l['luongdongbaohiem'] or ''
            # mluongdongbaohiem += l['luongdongbaohiem'] or 0.0
            ws.cell(row, 27).value = l['bhxh'] or ''
            mbhxh += l['bhxh'] or 0.0
            ws.cell(row, 28).value = l['bhyt'] or ''
            mbhyt += l['bhyt'] or 0.0
            ws.cell(row, 29).value = l['bhtn'] or ''
            mbhtn += l['bhtn'] or 0.0
            ws.cell(row, 30).value = l['tong'] or ''
            mtonggiamtrubaohiem += l['tong'] or 0.0
            ws.cell(row, 31).value = l['bhxhh'] or ''
            mbhxh2 += l['bhxhh'] or 0.0
            ws.cell(row, 32).value = l['bhytt'] or ''
            mbhyt2 += l['bhytt'] or 0.0
            # ws.cell(row, 32).value = l['bhtnn'] or ''
            # mbhtn2 += l['bhtnn'] or 0.0
            ws.cell(row, 33).value = l['bhtn'] or ''
            mbhtn2 += l['bhtn'] or 0.0
            ws.cell(row, 34).value = l['tongg'] or ''
            mtonggiamtrubaohiem2 += l['tongg'] or 0.0
            # ws.cell(row, 34).value = l['tongtienbh'] or ''
            ws.cell(row, 35).value = "=sum(AD%s,AH%s)" % (row, row)
            mtongcacloaibaohiem += l['tongtienbh'] or 0.0
            # Calculate AJ and AK values using Python logic
            hotronhaoduocmienthue, thunhapchiuthue = self._calculate_aj_ak_values(l)
            ws.cell(row, 36).value = hotronhaoduocmienthue or ''
            mhotronhaoduocmienthue += hotronhaoduocmienthue or 0.0
            ws.cell(row, 37).value = thunhapchiuthue or ''
            mthunhapchiuthue += thunhapchiuthue or 0.0

            ws.cell(row, 38).value = l['trichthuetncn'] or ''
            mtrichthuetncn += l['trichthuetncn'] or 0.0
            ws.cell(row, 39).value = l['congtacphi'] or ''
            mcongtacphi += l['congtacphi'] or 0.0
            ws.cell(row, 40).value = l['hotrodienthoai'] or ''
            mhotrodienthoai += l['hotrodienthoai'] or 0.0
            ws.cell(row, 41).value = l['hoanthuetncnnamtruoc'] or ''
            mhoanthuetncn += l['hoanthuetncnnamtruoc'] or 0.0
            ws.cell(row, 42).value = l['datamung'] or ''
            mdatamung += l['datamung'] or 0.0
            ws.cell(row, 43).value = l['luongthuclinh'] or ''
            mluongthuclinh += l['luongthuclinh'] or 0.0
            index += 1
            indexx += 1
            row += 1
        row = row - 1
        ws.cell(row - indexx, 5).font = ws.cell(row - indexx, 6).font = ws.cell(row - indexx, 7).font = ws.cell(
            row - indexx, 8).font = ws.cell(row - indexx,
                                            9).font = ws.cell(
            row - indexx,
            10).font = ws.cell(
            row - indexx, 11).font = ws.cell(row - indexx, 12).font = ws.cell(row - indexx, 13).font = ws.cell(
            row - indexx, 14).font = ws.cell(row - indexx,
                                             15).font = ws.cell(
            row - indexx, 16).font = ws.cell(row - indexx, 17).font = ws.cell(row - indexx, 18).font = ws.cell(
            row - indexx, 19).font = ws.cell(row - indexx,
                                             20).font = ws.cell(
            row - indexx, 21).font = ws.cell(row - indexx, 22).font = ws.cell(row - indexx, 23).font = ws.cell(
            row - indexx, 24).font = ws.cell(row - indexx,
                                             25).font = ws.cell(
            row - indexx, 26).font = ws.cell(row - indexx, 27).font = ws.cell(row - indexx, 28).font = ws.cell(
            row - indexx, 29).font = ws.cell(row - indexx,
                                             30).font = ws.cell(
            row - indexx, 31).font = ws.cell(row - indexx, 32).font = ws.cell(row - indexx, 33).font = ws.cell(
            row - indexx, 34).font = ws.cell(row - indexx,
                                             35).font = ws.cell(
            row - indexx, 36).font = ws.cell(row - indexx, 37).font = ws.cell(row - indexx, 38).font = ws.cell(
            row - indexx, 39).font = ws.cell(            row - indexx,
                                             40).font = ws.cell(
            row - indexx, 41).font = ws.cell(row - indexx, 42).font = ws.cell(row - indexx, 43).font = Font(size=12, name='Times New Roman', bold=True)

        ws.cell(row - indexx, 5).number_format = ws.cell(row - indexx, 6).number_format = ws.cell(row - indexx,
                                                                                                  7).number_format = ws.cell(
            row - indexx,
            8).number_format = ws.cell(
            row - indexx,
            10).number_format = ws.cell(
            row - indexx,
            14).number_format = ws.cell(
            row - indexx,
            15).number_format = ws.cell(
            row - indexx, 16).number_format = ws.cell(row - indexx, 17).number_format = ws.cell(row - indexx,
                                                                                                18).number_format = ws.cell(
            row - indexx,
            19).number_format = ws.cell(
            row - indexx,
            20).number_format = ws.cell(
            row - indexx, 21).number_format = ws.cell(row - indexx, 22).number_format = ws.cell(row - indexx,
                                                                                                23).number_format = ws.cell(
            row - indexx,
            24).number_format = ws.cell(
            row - indexx,
            25).number_format = ws.cell(
            row - indexx, 26).number_format = ws.cell(row - indexx, 27).number_format = ws.cell(row - indexx,
                                                                                                28).number_format = ws.cell(
            row - indexx,
            29).number_format = ws.cell(
            row - indexx,
            30).number_format = ws.cell(
            row - indexx, 31).number_format = ws.cell(row - indexx, 32).number_format = ws.cell(row - indexx,
                                                                                                33).number_format = ws.cell(
            row - indexx,
            34).number_format = ws.cell(
            row - indexx,
            35).number_format = ws.cell(
            row - indexx, 36).number_format = ws.cell(row - indexx, 37).number_format = ws.cell(row - indexx,
                                                                                                38).number_format = ws.cell(
            row - indexx,
            39).number_format = ws.cell(
            row - indexx,
            40).number_format = ws.cell(
            row - indexx, 41).number_format = ws.cell(row - indexx, 42).number_format = ws.cell(row - indexx, 43).number_format = '#,##'

        ws.cell(row - indexx, 9).number_format = ws.cell(row - indexx, 11).number_format = ws.cell(row - indexx,
                                                                                 12).number_format = ws.cell(
            row - indexx, 13).number_format = '#,##0.00'

        ws.cell(row - indexx, 5).value = mluongchinh
        ws.cell(row - indexx, 6).value = mantrua
        ws.cell(row - indexx, 7).value = mnhao
        ws.cell(row - indexx, 8).value = mtongthunhaptheohd
        ws.cell(row - indexx, 9).value = mgiocongcoso
        ws.cell(row - indexx, 10).value = mdongia
        ws.cell(row - indexx, 11).value = mgiocongphanboGeneral
        ws.cell(row - indexx, 12).value = mgiocongphanboMaintenance
        ws.cell(row - indexx, 13).value = mgiocongphanboFacility
        ws.cell(row - indexx, 14).value = mtonggiocongthucte
        # ws.cell(row - indexx, 15).value = mluongbosung
        ws.cell(row - indexx, 15).value = mluongphanboGeneral
        ws.cell(row - indexx, 16).value = mluongphanboMaintenance
        ws.cell(row - indexx, 17).value = mluongphanboFacility
        ws.cell(row - indexx, 18).value = mtongthunhaptheogiocongthucte
        ws.cell(row - indexx, 19).value = mthuong_nvxs
        ws.cell(row - indexx, 20).value = mthunhapkhac
        ws.cell(row - indexx, 21).value = mhotroxangxe
        ws.cell(row - indexx, 22).value = mbutruluong
        ws.cell(row - indexx, 23).value = mhotrotienluong
        ws.cell(row - indexx, 24).value = mtongthunhap
        ws.cell(row - indexx, 25).value = mthuongnong
        ws.cell(row - indexx, 26).value = mtongthunhaptrongthang
        # ws.cell(row - indexx, 27).value = mluongdongbaohiem
        ws.cell(row - indexx, 27).value = mbhxh
        ws.cell(row - indexx, 28).value = mbhyt
        ws.cell(row - indexx, 29).value = mbhtn
        ws.cell(row - indexx, 30).value = mtonggiamtrubaohiem
        ws.cell(row - indexx, 31).value = mbhxh2
        ws.cell(row - indexx, 32).value = mbhyt2
        ws.cell(row - indexx, 33).value = mbhtn2
        ws.cell(row - indexx, 34).value = mtonggiamtrubaohiem2
        # ws.cell(row-indexx, 34).value = mtongcacloaibaohiem
        ws.cell(row - indexx, 35).value = "=sum(AD%s,AH%s)" % (row - indexx, row - indexx)
        ws.cell(row - indexx, 36).value = mhotronhaoduocmienthue
        ws.cell(row - indexx, 37).value = mthunhapchiuthue
        ws.cell(row - indexx, 38).value = mtrichthuetncn
        ws.cell(row - indexx, 39).value = mcongtacphi
        ws.cell(row - indexx, 40).value = mhotrodienthoai
        ws.cell(row - indexx, 41).value = mhoanthuetncn
        ws.cell(row - indexx, 42).value = mdatamung
        ws.cell(row - indexx, 43).value = mluongthuclinh
        #
        queryFacility = """
                select 
                he.name hovaten, 
                he.x_code manhanvien, 
                he.job_title chucvu, 
                hc.x_insurance_wage luongchinh, 
                hc.x_allowance_lunch antrua, 
                hc.x_allowance_home nhao, 
                hc.wage tongthunhaptheohd,
                x5.amount giocongcoso,
                case when hc.wage = 0 or hc.wage is null then hc.hourly_wage else hc.wage/x5.amount end as dongia,
                case when hdb.name = 'General' then x2.amount else 0 end as Generall,
                case when hdb.name = 'Maintenenance & Services' then x2.amount else 0  end as MaintenenanceServices,
                case when hdb.name = 'Facility Management' then x2.amount else 0  end as FacilityManagement,
                X2.amount tonggiocongthucte, 
                hpl4.total luongbosung,
                case when hdb.name = 'General' 
                    then 
                         hpl5.total
                     else 0 
                 end as ThuNhapGenerall,
                 case when hdb.name = 'Maintenenance & Services' 
                    then 
                         hpl5.total 
                     else 0 
                 end as ThuNhapMaintenenanceServices,
                  case when hdb.name = 'Facility Management' 
                    then 
                         hpl5.total
                     else 0 
                 end as ThuNhapFacilityManagement,
                coalesce(hpl5.total,0) tongthunhaptheogiocongthucte,  
                coalesce(hpl2.total,0) hotroxangxe, 
                hpl3.total butruluongthang, 
                coalesce(hpl4.total,0) luongbuducong,
                (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0)) tongthunhap, 
                hpl6.amount luongdongbaohiem,
                hpl6.total BHXH, 
                hpl7.total BHYT, 
                hpl8.total BHTN, 
                (hpl6.total+hpl7.total+hpl8.total) tong,
                hpl6.amount*0.175 BHXHH, 
                hpl6.amount*0.03 BHYTT, 
                hpl6.amount*0.01 BHTNN, 
                coalesce(hpl6.amount*0.215,0) tongg,
                (hpl5.total+hpl.total+hpl2.total-hpl3.total+hpl4.total-hpl6.total-hpl7.total-hpl8.total) tongtienbh,
                case 
                    when coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 > 0 
                    then coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 else 0 end as hotronhaoduocmienthue,
                case 
                    when coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15 > 0 
                    then 
                        case 
                        when (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-(coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15)
                                -coalesce(hc.x_allowance_lunch,0) + coalesce(hpl13.total,0) > 0 
                        then
                            (coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-(coalesce(hc.x_allowance_home,0)-((coalesce(hpl5.total,0)+coalesce(hpl.total,0)+coalesce(hpl2.total,0)-coalesce(hpl3.total,0)+coalesce(hpl4.total,0))-coalesce(hc.x_allowance_home,0))*0.15)
                                -coalesce(hc.x_allowance_lunch,0) + coalesce(hpl13.total,0) 
                        else 0 end
                else 0
                end as thunhapchiuthue,
                hpl9.total trichthuetncn, 
                coalesce(hpl10.total,0) congtacphi, 
                hpl11.total hoanthuetncnnamtruoc, 
                hpl12.total datamung,
                coalesce(X6.amount,0) thuongnong,
                coalesce(X7.amount,0) hotrodienthoai,
                hp.x_amount_total luongthuclinh
                from hr_payslip hp
                left join hr_payslip_line hpl on hp.id = hpl.slip_id and hpl.name = 'Thưởng hoặc các khoản thu nhập khác'
                left join hr_payslip_line hpl2 on hp.id = hpl2.slip_id  and hpl2.name = 'Hỗ trợ xăng xe'
                left join hr_payslip_line hpl3 on hp.id = hpl3.slip_id  and hpl3.name = 'Bù/Trừ lương tháng'
                left join hr_payslip_line hpl4 on hp.id = hpl4.slip_id  and hpl4.name = 'Hỗ trợ tiền lương bù đủ công' 
                left join hr_payslip_line hpl5 on hp.id = hpl5.slip_id  and hpl5.name = 'Thu nhập theo giờ công thực tế' 
                left join hr_payslip_line hpl6 on hp.id = hpl6.slip_id  and hpl6.name = 'Bảo hiểm xã hội'
                left join hr_payslip_line hpl7 on hp.id = hpl7.slip_id and hpl7.name = 'Bảo hiểm y tế' 
                left join hr_payslip_line hpl8 on hp.id = hpl8.slip_id and hpl8.name = 'Bảo hiểm thất nghiệp' 
                left join hr_payslip_line hpl9 on hp.id = hpl9.slip_id  and hpl9.name = 'Thuế TNCN phải nộp' 
                left join hr_payslip_line hpl10 on hp.id = hpl10.slip_id   and hpl10.name = 'Công tác phí'
                left join hr_payslip_line hpl11 on hp.id = hpl11.slip_id   and hpl11.name = 'Hoàn thuế TNCN năm trước' 
                left join hr_payslip_line hpl12 on hp.id = hpl12.slip_id  and hpl12.name = 'Tạm ứng' 
                left join hr_payslip_line hpl13 on hp.id = hpl13.slip_id  and hpl13.name = 'Các khoản thưởng nóng'
                left join hr_employee he on hp.employee_id = he.id
                left join hr_contract hc on hp.contract_id = hc.id
                left join (select hpi.*,hpit.code as codehpit from hr_payslip_input hpi left join hr_payslip_input_type hpit on hpi.input_type_id = hpit.id)X1 on hp.id = X1.payslip_id and X1.codehpit = 'OTHER_WORK_DAY_THEORY'
                left join (select hpi2.*,hpit2.code as codehpit from hr_payslip_input hpi2 left join hr_payslip_input_type hpit2 on hpi2.input_type_id = hpit2.id)X2 on hp.id = X2.payslip_id and X2.codehpit = 'OTHER_WORK_HOUR_CONVERTED'
                left join (select hpi3.*,hpit3.code as codehpit from hr_payslip_input hpi3 left join hr_payslip_input_type hpit3 on hpi3.input_type_id = hpit3.id)X3 on hp.id = X3.payslip_id and X3.codehpit = 'OTHER_WORK_HOUR_SUPPORT'
                left join (select hpi4.*,hpit4.code as codehpit from hr_payslip_input hpi4 left join hr_payslip_input_type hpit4 on hpi4.input_type_id = hpit4.id)X4 on hp.id = X4.payslip_id and X4.codehpit = 'OTHER_WAGE_TOTAL'
                left join (select hpi5.*,hpit5.code as codehpit from hr_payslip_input hpi5 left join hr_payslip_input_type hpit5 on hpi5.input_type_id = hpit5.id)X5 on hp.id = X5.payslip_id and X5.codehpit = 'OTHER_WORK_HOUR_THEORY'
                left join (select hpi6.*,hpit6.code as codehpit from hr_payslip_input hpi6 left join hr_payslip_input_type hpit6 on hpi6.input_type_id = hpit6.id)X6 on hp.id = X6.payslip_id and X6.codehpit = 'OTHER_BONUS_INSTANT'
                left join (select hpi7.*,hpit7.code as codehpit from hr_payslip_input hpi7 left join hr_payslip_input_type hpit7 on hpi7.input_type_id = hpit7.id)X7 on hp.id = X7.payslip_id and X7.codehpit = 'OTHER_MOBILE'
                left join hr_department hd on he.department_id = hd.id
                left join hr_department_block hdb on hdb.id = hd.x_block_id 
                where hp.state in {2}
                and TO_CHAR(hp.date_from, 'YYYYMM') >= '{1}{0:0>2}'
                and TO_CHAR(hp.date_to, 'YYYYMM') <= '{4}{3:0>2}'
                and hdb.name = 'Facility Management'
                                                """.format(month, year, "('draft','verify','done')" if show_draft else "('done')",month_to, year_to)
        self._cr.execute(queryFacility)
        listFacilitys = self._cr.dictfetchall()
        listFacilitys = self.merge_data(listFacilitys)
        row = row + 3
        A = 'A' + str(row) + ':D' + str(row)
        ws.merge_cells(A)
        ws.cell(row, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 1).value = 'Facility Management'
        row = row + 1
        indexxx = 0
        for index, l in enumerate(listFacilitys):
            ws.cell(row, 1).font = ws.cell(row, 2).font = ws.cell(row, 3).font = ws.cell(row, 4).font = ws.cell(row,
                                                                                                                5).font = ws.cell(
                row, 6).font = ws.cell(row, 7).font = ws.cell(row, 8).font = ws.cell(row, 9).font = ws.cell(row,
                                                                                                            10).font = ws.cell(
                row, 11).font = ws.cell(row, 12).font = ws.cell(row, 13).font = ws.cell(row, 14).font = ws.cell(row,
                                                                                                                15).font = ws.cell(
                row, 16).font = ws.cell(row, 17).font = ws.cell(row, 18).font = ws.cell(row, 19).font = ws.cell(row,
                                                                                                                20).font = ws.cell(
                row, 21).font = ws.cell(row, 22).font = ws.cell(row, 23).font = ws.cell(row, 24).font = ws.cell(row,
                                                                                                                25).font = ws.cell(
                row, 26).font = ws.cell(row, 27).font = ws.cell(row, 28).font = ws.cell(row, 29).font = ws.cell(row,
                                                                                                                30).font = ws.cell(
                row, 31).font = ws.cell(row, 32).font = ws.cell(row, 33).font = ws.cell(row, 34).font = ws.cell(row,
                                                                                                                35).font = ws.cell(
                row, 36).font = ws.cell(row, 37).font = ws.cell(row, 38).font = ws.cell(row, 39).font = ws.cell(row,
                                                                                                                40).font = ws.cell(
                row, 41).font = ws.cell(row, 42).font = ws.cell(row, 43).font = Font(size=12, name='Times New Roman')

            ws.cell(row, 5).number_format = ws.cell(row, 6).number_format = ws.cell(row, 7).number_format = ws.cell(row,
                                                                                                                    8).number_format = ws.cell(
                row, 10).number_format = ws.cell(
                row, 14).number_format = ws.cell(row, 15).number_format = ws.cell(row, 16).number_format = ws.cell(row,
                                                                                                                   17).number_format = ws.cell(
                row, 18).number_format = ws.cell(row, 19).number_format = ws.cell(row, 20).number_format = ws.cell(row,
                                                                                                                   21).number_format = ws.cell(
                row, 22).number_format = ws.cell(row, 23).number_format = ws.cell(row, 24).number_format = ws.cell(row,
                                                                                                                   25).number_format = ws.cell(
                row, 26).number_format = ws.cell(row, 27).number_format = ws.cell(row, 28).number_format = ws.cell(row,
                                                                                                                   29).number_format = ws.cell(
                row, 30).number_format = ws.cell(row, 31).number_format = ws.cell(row, 32).number_format = ws.cell(row,
                                                                                                                   33).number_format = ws.cell(
                row, 34).number_format = ws.cell(row, 35).number_format = ws.cell(row, 36).number_format = ws.cell(row,
                                                                                                                   37).number_format = ws.cell(
                row, 38).number_format = ws.cell(row, 39).number_format = ws.cell(row, 40).number_format = ws.cell(row,
                                                                                                                   41).number_format = ws.cell(row, 42).number_format = ws.cell(row, 43).number_format = '#,##'

            ws.cell(row, 9).number_format = ws.cell(row, 11).number_format = ws.cell(row,
                                                                                                       12).number_format = ws.cell(
                row, 13).number_format = '#,##0.00'

            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['hovaten'] or ''
            ws.cell(row, 3).value = l['manhanvien'] or ''
            ws.cell(row, 4).value = l['chucvu'] or ''
            ws.cell(row, 5).value = l['luongchinh'] or ''
            fluongchinh += l['luongchinh']
            ws.cell(row, 6).value = l['antrua'] or ''
            fantrua += l['antrua'] or 0.0
            ws.cell(row, 7).value = l['nhao'] or ''
            fnhao += l['nhao'] or 0.0
            ws.cell(row, 8).value = l['tongthunhaptheohd'] or ''
            ftongthunhaptheohd += l['tongthunhaptheohd'] or 0.0
            ws.cell(row, 9).value = l['giocongcoso'] or ''
            fgiocongcoso += l['giocongcoso'] or 0.0
            ws.cell(row, 10).value = l['dongia'] or ''
            fdongia += l['dongia'] or 0.0
            ws.cell(row, 11).value = l['generall'] or ''
            fgiocongphanboGeneral += l['generall'] or 0.0
            ws.cell(row, 12).value = l['maintenenanceservices'] or ''
            fgiocongphanboMaintenance += l['maintenenanceservices'] or 0.0
            ws.cell(row, 13).value = l['facilitymanagement'] or ''
            fgiocongphanboFacility += l['facilitymanagement'] or 0.0
            ws.cell(row, 14).value = l['tonggiocongthucte'] or ''
            ftonggiocongthucte += l['tonggiocongthucte'] or 0.0
            # ws.cell(row, 15).value = l['luongbosung'] or ''
            # fluongbosung += l['luongbosung'] or 0.0
            ws.cell(row, 15).value = l['thunhapgenerall'] or ''
            fluongphanboGeneral += l['thunhapgenerall'] or 0.0
            ws.cell(row, 16).value = l['thunhapmaintenenanceservices'] or ''
            fluongphanboMaintenance += l['thunhapmaintenenanceservices'] or 0.0
            ws.cell(row, 17).value = l['thunhapfacilitymanagement'] or ''
            fluongphanboFacility += l['thunhapfacilitymanagement'] or 0.0
            ws.cell(row, 18).value = l['tongthunhaptheogiocongthucte'] or ''
            ftongthunhaptheogiocongthucte += l['tongthunhaptheogiocongthucte'] or 0.0
            thuong_nvxs = next(
                (item.get('thuongnhanvienxuatsac') for item in listthuong if item['code'] == l.get('manhanvien')), 0.0)
            ws.cell(row, 19).value = thuong_nvxs or ''
            fthuong_nvxs += thuong_nvxs or 0.0
            thunhapkhac = next((item.get('thunhapkhac') for item in listthuong if item['code'] == l.get('manhanvien')),
                               0.0)
            ws.cell(row, 20).value = thunhapkhac - thuong_nvxs or ''
            fthunhapkhac += thunhapkhac - thuong_nvxs or 0.0
            ws.cell(row, 21).value = l['hotroxangxe'] or ''
            fhotroxangxe += l['hotroxangxe'] or 0.0
            ws.cell(row, 22).value = l['butruluongthang'] or ''
            fbutruluong += l['butruluongthang'] or 0.0
            ws.cell(row, 23).value = l['luongbuducong'] or ''
            fhotrotienluong += l['luongbuducong'] or 0.0
            ws.cell(row, 24).value = l['tongthunhap'] or ''
            ftongthunhap += l['tongthunhap'] or 0.0
            ws.cell(row, 25).value = l['thuongnong'] or ''
            fthuongnong += l['thuongnong'] or 0.0
            ws.cell(row, 26).value = l['thuongnong'] + l['tongthunhap']or ''
            ftongthunhaptrongthang += l['thuongnong'] + l['tongthunhap']or 0.0
            # ws.cell(row, 27).value = l['luongdongbaohiem'] or ''
            # fluongdongbaohiem += l['luongdongbaohiem'] or 0.0
            ws.cell(row, 27).value = l['bhxh'] or ''
            fbhxh += l['bhxh'] or 0.0
            ws.cell(row, 28).value = l['bhyt'] or ''
            fbhyt += l['bhyt'] or 0.0
            ws.cell(row, 29).value = l['bhtn'] or ''
            fbhtn += l['bhtn'] or 0.0
            ws.cell(row, 30).value = l['tong'] or ''
            ftonggiamtrubaohiem += l['tong'] or 0.0
            ws.cell(row, 31).value = l['bhxhh'] or ''
            fbhxh2 += l['bhxhh'] or 0.0
            ws.cell(row, 32).value = l['bhytt'] or ''
            fbhyt2 += l['bhytt'] or 0.0
            # ws.cell(row, 32).value = l['bhtnn'] or ''
            # fbhtn2 += l['bhtnn'] or 0.0
            ws.cell(row, 33).value = l['bhtn'] or ''
            fbhtn2 += l['bhtn'] or 0.0
            ws.cell(row, 34).value = l['tongg'] or ''
            ftonggiamtrubaohiem2 += l['tongg'] or 0.0
            # ws.cell(row, 34).value = l['tongtienbh'] or ''
            ws.cell(row, 35).value = "=sum(AD%s,AH%s)" % (row, row)
            ftongcacloaibaohiem += l['tongtienbh'] or 0.0

            hotronhaoduocmienthue, thunhapchiuthue = self._calculate_aj_ak_values(l)
            ws.cell(row, 36).value = hotronhaoduocmienthue or ''
            fhotronhaoduocmienthue += hotronhaoduocmienthue or 0.0
            ws.cell(row, 37).value = thunhapchiuthue or ''
            fthunhapchiuthue += thunhapchiuthue or 0.0

            ws.cell(row, 38).value = l['trichthuetncn'] or ''
            ftrichthuetncn += l['trichthuetncn'] or 0.0
            ws.cell(row, 39).value = l['congtacphi'] or ''
            fcongtacphi += l['congtacphi'] or 0.0
            ws.cell(row, 40).value = l['hotrodienthoai'] or ''
            fhotrodienthoai += l['hotrodienthoai'] or 0.0
            ws.cell(row, 41).value = l['hoanthuetncnnamtruoc'] or ''
            fhoanthuetncn += l['hoanthuetncnnamtruoc'] or 0.0
            ws.cell(row, 42).value = l['datamung'] or ''
            fdatamung += l['datamung'] or 0.0
            ws.cell(row, 43).value = l['luongthuclinh'] or ''
            fluongthuclinh += l['luongthuclinh'] or 0.0
            index += 1
            indexxx += 1
            row += 1
        row = row - indexxx - 1
        ws.cell(row, 5).font = ws.cell(row, 6).font = ws.cell(row, 7).font = ws.cell(row, 8).font = ws.cell(row,
                                                                                                            9).font = ws.cell(
            row,
            10).font = ws.cell(
            row, 11).font = ws.cell(row, 12).font = ws.cell(row, 13).font = ws.cell(row, 14).font = ws.cell(row,
                                                                                                            15).font = ws.cell(
            row, 16).font = ws.cell(row, 17).font = ws.cell(row, 18).font = ws.cell(row, 19).font = ws.cell(row,
                                                                                                            20).font = ws.cell(
            row, 21).font = ws.cell(row, 22).font = ws.cell(row, 23).font = ws.cell(row, 24).font = ws.cell(row,
                                                                                                            25).font = ws.cell(
            row, 26).font = ws.cell(row, 27).font = ws.cell(row, 28).font = ws.cell(row, 29).font = ws.cell(row,
                                                                                                            30).font = ws.cell(
            row, 31).font = ws.cell(row, 32).font = ws.cell(row, 33).font = ws.cell(row, 34).font = ws.cell(row,
                                                                                                            35).font = ws.cell(
            row, 36).font = ws.cell(row, 37).font = ws.cell(row, 38).font = ws.cell(row, 39).font = ws.cell(row,
                                                                                                            40).font = ws.cell(
            row, 41).font = ws.cell(row, 42).font = ws.cell(row, 43).font = Font(size=12, name='Times New Roman', bold=True)

        ws.cell(row, 5).number_format = ws.cell(row, 6).number_format = ws.cell(row, 7).number_format = ws.cell(row,
                                                                                                                8).number_format = ws.cell(
            row,
            10).number_format = ws.cell(row,
                                                                                                               14).number_format = ws.cell(
            row,
            15).number_format = ws.cell(
            row, 16).number_format = ws.cell(row, 17).number_format = ws.cell(row, 18).number_format = ws.cell(row,
                                                                                                               19).number_format = ws.cell(
            row,
            20).number_format = ws.cell(
            row, 21).number_format = ws.cell(row, 22).number_format = ws.cell(row, 23).number_format = ws.cell(row,
                                                                                                               24).number_format = ws.cell(
            row,
            25).number_format = ws.cell(
            row, 26).number_format = ws.cell(row, 27).number_format = ws.cell(row, 28).number_format = ws.cell(row,
                                                                                                               29).number_format = ws.cell(
            row,
            30).number_format = ws.cell(
            row, 31).number_format = ws.cell(row, 32).number_format = ws.cell(row, 33).number_format = ws.cell(row,
                                                                                                               34).number_format = ws.cell(
            row,
            35).number_format = ws.cell(
            row, 36).number_format = ws.cell(row, 37).number_format = ws.cell(row, 38).number_format = ws.cell(row,
                                                                                                               39).number_format = ws.cell(
            row,
            40).number_format = ws.cell(
            row, 41).number_format = ws.cell(row, 42).number_format = ws.cell(row, 43).number_format = '#,##'

        ws.cell(row, 9).number_format = ws.cell(row, 11).number_format = ws.cell(row,
                                                                                 12).number_format = ws.cell(
            row, 13).number_format = '#,##0.00'

        ws.cell(row, 5).value = fluongchinh
        ws.cell(row, 6).value = fantrua
        ws.cell(row, 7).value = fnhao
        ws.cell(row, 8).value = ftongthunhaptheohd
        ws.cell(row, 9).value = fgiocongcoso
        ws.cell(row, 10).value = fdongia
        ws.cell(row, 11).value = fgiocongphanboGeneral
        ws.cell(row, 12).value = fgiocongphanboMaintenance
        ws.cell(row, 13).value = fgiocongphanboFacility
        ws.cell(row, 14).value = ftonggiocongthucte
        # ws.cell(row, 15).value = fluongbosung
        ws.cell(row, 15).value = fluongphanboGeneral
        ws.cell(row, 16).value = fluongphanboMaintenance
        ws.cell(row, 17).value = fluongphanboFacility
        ws.cell(row, 18).value = ftongthunhaptheogiocongthucte
        ws.cell(row, 19).value = fthuong_nvxs
        ws.cell(row, 20).value = fthunhapkhac
        ws.cell(row, 21).value = fhotroxangxe
        ws.cell(row, 22).value = fbutruluong
        ws.cell(row, 23).value = fhotrotienluong
        ws.cell(row, 24).value = ftongthunhap
        ws.cell(row, 25).value = fthuongnong
        ws.cell(row, 26).value = ftongthunhaptrongthang
        # ws.cell(row, 27).value = fluongdongbaohiem
        ws.cell(row, 27).value = fbhxh
        ws.cell(row, 28).value = fbhyt
        ws.cell(row, 29).value = fbhtn
        ws.cell(row, 30).value = ftonggiamtrubaohiem
        ws.cell(row, 31).value = fbhxh2
        ws.cell(row, 32).value = fbhyt2
        ws.cell(row, 33).value = fbhtn2
        ws.cell(row, 34).value = ftonggiamtrubaohiem2
        # ws.cell(row, 34).value = ftongcacloaibaohiem
        ws.cell(row, 35).value = "=sum(AD%s,AH%s)" % (row, row)
        ws.cell(row, 36).value = fhotronhaoduocmienthue
        ws.cell(row, 37).value = fthunhapchiuthue
        ws.cell(row, 38).value = ftrichthuetncn
        ws.cell(row, 39).value = fcongtacphi
        ws.cell(row, 40).value = fhotrodienthoai
        ws.cell(row, 41).value = fhoanthuetncn
        ws.cell(row, 42).value = fdatamung
        ws.cell(row, 43).value = fluongthuclinh
        # format tổng
        ws.cell(6, 5).font = ws.cell(6, 6).font = ws.cell(6, 7).font = ws.cell(6, 8).font = ws.cell(6,
                                                                                                    9).font = ws.cell(
            6,
            10).font = ws.cell(
            6, 11).font = ws.cell(6, 12).font = ws.cell(6, 13).font = ws.cell(6, 14).font = ws.cell(6,
                                                                                                    15).font = ws.cell(
            6, 16).font = ws.cell(6, 17).font = ws.cell(6, 18).font = ws.cell(6, 19).font = ws.cell(6,
                                                                                                    20).font = ws.cell(
            6, 21).font = ws.cell(6, 22).font = ws.cell(6, 23).font = ws.cell(6, 24).font = ws.cell(6,
                                                                                                    25).font = ws.cell(
            6, 26).font = ws.cell(6, 27).font = ws.cell(6, 28).font = ws.cell(6, 29).font = ws.cell(6,
                                                                                                    30).font = ws.cell(
            6, 31).font = ws.cell(6, 32).font = ws.cell(6, 33).font = ws.cell(6, 34).font = ws.cell(6,
                                                                                                    35).font = ws.cell(
            6, 36).font = ws.cell(6, 37).font = ws.cell(6, 38).font = ws.cell(6, 39).font = ws.cell(6,
                                                                                                    40).font = ws.cell(
            6, 41).font = ws.cell(6, 42).font = ws.cell(6, 43).font = Font(size=12, name='Times New Roman', bold=True)

        ws.cell(6, 5).number_format = ws.cell(6, 6).number_format = ws.cell(6, 7).number_format = ws.cell(6,
                                                                                                          8).number_format = ws.cell(
            6,
            10).number_format = ws.cell(6,
                                                                                                         14).number_format = ws.cell(
            6,
            15).number_format = ws.cell(
            6, 16).number_format = ws.cell(6, 17).number_format = ws.cell(6, 18).number_format = ws.cell(6,
                                                                                                         19).number_format = ws.cell(
            6,
            20).number_format = ws.cell(
            6, 21).number_format = ws.cell(6, 22).number_format = ws.cell(6, 23).number_format = ws.cell(6,
                                                                                                         24).number_format = ws.cell(
            6,
            25).number_format = ws.cell(
            6, 26).number_format = ws.cell(6, 27).number_format = ws.cell(6, 28).number_format = ws.cell(6,
                                                                                                         29).number_format = ws.cell(
            6,
            30).number_format = ws.cell(
            6, 31).number_format = ws.cell(6, 32).number_format = ws.cell(6, 33).number_format = ws.cell(6,
                                                                                                         34).number_format = ws.cell(
            6,
            35).number_format = ws.cell(
            6, 36).number_format = ws.cell(6, 37).number_format = ws.cell(6, 38).number_format = ws.cell(6,39).number_format = ws.cell(6,
            40).number_format = ws.cell(
            6, 41).number_format = ws.cell(6,42).number_format = ws.cell(6,43).number_format= '#,##'

        ws.cell(6, 9).number_format = ws.cell(6, 11).number_format = ws.cell(6,
                                                                                 12).number_format = ws.cell(
            6, 13).number_format = '#,##0.00'
        #
        ws.cell(6, 5).value = gluongchinh + mluongchinh + fluongchinh
        ws.cell(6, 6).value = gantrua + mantrua + fantrua
        ws.cell(6, 7).value = gnhao + mnhao + fnhao
        ws.cell(6, 8).value = gtongthunhaptheohd + mtongthunhaptheohd + ftongthunhaptheohd
        ws.cell(6, 9).value = ggiocongcoso + mgiocongcoso + fgiocongcoso
        ws.cell(6, 10).value = gdongia + mdongia + fdongia
        ws.cell(6, 11).value = ggiocongphanboGeneral + mgiocongphanboGeneral + fgiocongphanboGeneral
        ws.cell(6, 12).value = ggiocongphanboMaintenance + mgiocongphanboMaintenance + fgiocongphanboMaintenance
        ws.cell(6, 13).value = ggiocongphanboFacility + mgiocongphanboFacility + fgiocongphanboFacility
        ws.cell(6, 14).value = gtonggiocongthucte + mtonggiocongthucte + ftonggiocongthucte
        # ws.cell(6, 15).value = gluongbosung + mluongbosung + fluongbosung
        ws.cell(6, 15).value = gluongphanboGeneral + mluongphanboGeneral + fluongphanboGeneral
        ws.cell(6, 16).value = gluongphanboMaintenance + mluongphanboMaintenance + fluongphanboMaintenance
        ws.cell(6, 17).value = gluongphanboFacility + mluongphanboFacility + fluongphanboFacility
        ws.cell(6,18).value = gtongthunhaptheogiocongthucte + mtongthunhaptheogiocongthucte + ftongthunhaptheogiocongthucte
        ws.cell(6, 19).value = gthuong_nvxs + mthuong_nvxs + fthuong_nvxs
        ws.cell(6, 20).value = gthunhapkhac + mthunhapkhac + fthunhapkhac
        ws.cell(6, 21).value = ghotroxangxe + mhotroxangxe + fhotroxangxe
        ws.cell(6, 22).value = gbutruluong + mbutruluong + fbutruluong
        ws.cell(6, 23).value = ghotrotienluong + mhotrotienluong + fhotrotienluong
        ws.cell(6, 24).value = gtongthunhap + mtongthunhap + ftongthunhap
        ws.cell(6, 25).value = gthuongnong + mthuongnong + fthuongnong
        ws.cell(6, 26).value = gtongthunhaptrongthang + mtongthunhaptrongthang + ftongthunhaptrongthang
        # ws.cell(6, 27).value = gluongdongbaohiem + mluongdongbaohiem + fluongdongbaohiem
        ws.cell(6, 27).value = gbhxh + mbhxh + fbhxh
        ws.cell(6, 28).value = gbhyt + mbhyt + fbhyt
        ws.cell(6, 29).value = gbhtn + mbhtn + fbhtn
        ws.cell(6, 30).value = gtonggiamtrubaohiem + mtonggiamtrubaohiem + ftonggiamtrubaohiem
        ws.cell(6, 31).value = gbhxh2 + mbhxh2 + fbhxh2
        ws.cell(6, 32).value = gbhyt2 + mbhyt2 + fbhyt2
        ws.cell(6, 33).value = gbhtn2 + mbhtn2 + fbhtn2
        ws.cell(6, 34).value = gtonggiamtrubaohiem2 + mtonggiamtrubaohiem2 + ftonggiamtrubaohiem2
        # ws.cell(6, 34).value = gtongcacloaibaohiem + mtongcacloaibaohiem + ftongcacloaibaohiem
        ws.cell(6, 35).value = "=sum(AD%s,AH%s)" % (6, 6)
        ws.cell(6, 36).value = ghotronhaoduocmienthue + mhotronhaoduocmienthue + fhotronhaoduocmienthue
        ws.cell(6, 37).value = gthunhapchiuthue + mthunhapchiuthue + fthunhapchiuthue
        ws.cell(6, 38).value = gtrichthuetncn + mtrichthuetncn + ftrichthuetncn
        ws.cell(6, 39).value = gcongtacphi + mcongtacphi + fcongtacphi
        ws.cell(6, 40).value = ghotrodienthoai + mhotrodienthoai + fhotrodienthoai
        ws.cell(6, 41).value = ghoanthuetncn + mhoanthuetncn + fhoanthuetncn
        ws.cell(6, 42).value = gdatamung + mdatamung + fdatamung
        ws.cell(6, 43).value = gluongthuclinh + mluongthuclinh + fluongthuclinh
        row = row + indexxx
        ws.cell(row + 2, 2).font = ws.cell(row + 3, 3).font = ws.cell(row + 3, 30).font = Font(size=12,
                                                                                               name='Times New Roman',
                                                                                               bold=True)
        ws.cell(row + 2, 2).value = 'Ngày: '
        ws.cell(row + 2, 3).font = Font(size=12, name='Times New Roman')
        ws.cell(row + 2, 2).alignment = Alignment(horizontal='right')
        ws.cell(row + 3, 3).alignment = ws.cell(row + 3, 30).alignment = Alignment(horizontal='center')
        ws.cell(row + 2, 3).value = fields.datetime.now().date().strftime("%d/%m/%Y")
        ws.cell(row + 3, 3).value = 'NGƯỜI LẬP BẢNG'
        ws.cell(row + 3, 30).value = 'NGƯỜI PHÊ DUYỆT'
        self.__format_ws__(ws, cell_range='A2:AQ' + str(row + 1))
        for col_range in range(1, 44):
            for row_range in range(row + 2, row + 9):
                cell_title = ws.cell(row_range, col_range)
                cell_title.fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo Salary.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }

        # luongtd

    def get_excel_report_travel(self, month, year):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/travel.xlsx')
        ws = wb['Data']
        query = """
                    select *
                    from
                    (select 
                    he.x_code as ma_nv,
                    he."name" as ho_va_ten,
                    coalesce(sum(hwebf.amount),0) as thanh_tien,
                    '' as ghi_chu
                    from hr_work_entry hwe 
                    left join hr_employee he on he.id=hwe.employee_id 
                    left join hr_work_entry_biz_fee hwebf on hwebf.entry_id = hwe.id
                    where hwe.state ='validated'
                    and (DATE_PART('month',hwe.x_date)= {0})
                    and (DATE_PART('year',hwe.x_date)= {1})
                    group by
                    he.x_code ,he."name") as A
                    where A.thanh_tien!=0
                    """.format(month, year)
        self._cr.execute(query)
        lists = self._cr.dictfetchall()
        row = 5
        ws.cell(2, 3).value = str(month) + '-' + str(year)
        tong = 0.0
        for index, l in enumerate(lists):
            ws.cell(row, 1).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 2).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 3).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 4).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 5).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['ma_nv'] or ''
            ws.cell(row, 3).value = l['ho_va_ten'] or ''
            ws.cell(row, 4).number_format = '#,##0.00'
            ws.cell(row, 4).value = l['thanh_tien'] or ''
            tong += l['thanh_tien'] or 0.0
            ws.cell(row, 5).value = l['ghi_chu'] or ''
            index += 1
            row += 1
        row = row + 1
        A = 'A' + str(row) + ':C' + str(row)
        nyc = 'A' + str(row + 1) + ':B' + str(row + 1)
        tbp = 'C' + str(row + 1) + ':D' + str(row + 1)
        ws.merge_cells(A)
        ws.merge_cells(nyc)
        ws.merge_cells(tbp)
        ws.cell(row, 1).value = 'TOTAL'
        ws.cell(row, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 1, 1).value = 'Người yêu cầu'
        ws.cell(row + 1, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 1, 3).value = 'Trưởng bộ phận'
        ws.cell(row + 1, 3).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 1, 5).value = 'Tổng giám đốc'
        ws.cell(row + 1, 5).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 4).value = tong
        ws.cell(row, 4).number_format = '#,##0.00'
        ws.cell(row, 4).font = Font(size=12, name='Times New Roman', bold=True)
        self.__format_ws__(ws, cell_range='A5:E' + str(row))
        # utility_obj = self.env['hcsv.utility']
        # company_currency = self.env.user.company_id.currency_id
        # sumChu = utility_obj.convert_amount_to_words(amount=tong, currency=company_currency).capitalize()
        # ws.cell(row+1,4).value=sumChu

        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo Travel.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }

    def get_excel_report_balance(self, year):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/timeoffbalance.xlsx')
        ws = wb['Data']
        query = """
                    select
                          G.ho_ten,
                          G.ma_nhan_vien,
                          G.chuc_vu,
                          G.bo_phan,
                          G.ngay_bat_dau,
                          G.ngay_ket_thuc,
                          G.ngay_ky_hd_ct,
                          G.ton_phep_nam_truoc,
                          G.phep_cap_nam_nay,
                          G.tong_so_phep_duoc_huong,
                          G.ngay_nghi_t1,
                          G.ngay_nghi_t2,
                          G.ngay_nghi_t3,
                          G.ngay_nghi_t4,
                          G.ngay_nghi_t5,
                          G.ngay_nghi_t6,
                          G.ngay_nghi_t7,
                          G.ngay_nghi_t8,
                          G.ngay_nghi_t9,
                          G.ngay_nghi_t10,
                          G.ngay_nghi_t11,
                          G.ngay_nghi_t12,
                          G.tong_so_ngay_da_nghi,
                          case
                            when current_date::date > '{0}-03-31' then coalesce(G.phep_cap_nam_nay,0)-coalesce (G.tong_so_ngay_da_nghi,0)+coalesce (G.nghi_phep_nam_truoc_trong_nam_nay,0)
                            else coalesce(G.tong_so_phep_duoc_huong,0)-coalesce (G.tong_so_ngay_da_nghi,0)
                          end as so_ngay_phep_con_lai_nam_nay
                        from
                          (
                          select
                            he."name" as ho_ten,
                            he.x_code as ma_nhan_vien,
                            he.job_title as chuc_vu,
                            hd."name" as bo_phan,
                            he.x_onboard_date as ngay_bat_dau,
                            he.x_quit_date as ngay_ket_thuc,
                            A.ngay_ky_hd_ct,
                            coalesce (B.ton_phep_nam_truoc,0) as ton_phep_nam_truoc,
                            coalesce(C.phep_cap_nam_nay, 0) as phep_cap_nam_nay,
                            coalesce (B.ton_phep_nam_truoc,0) + coalesce(C.phep_cap_nam_nay, 0) as tong_so_phep_duoc_huong,
                            coalesce(E.ngay_nghi_t1 , 0) as ngay_nghi_t1,
                            coalesce(E.ngay_nghi_t2 , 0) as ngay_nghi_t2,
                            coalesce(E.ngay_nghi_t3 , 0) as ngay_nghi_t3,
                            coalesce(E.ngay_nghi_t4 , 0) as ngay_nghi_t4,
                            coalesce(E.ngay_nghi_t5 , 0) as ngay_nghi_t5,
                            coalesce(E.ngay_nghi_t6 , 0) as ngay_nghi_t6,
                            coalesce(E.ngay_nghi_t7 , 0) as ngay_nghi_t7,
                            coalesce(E.ngay_nghi_t8 , 0) as ngay_nghi_t8,
                            coalesce(E.ngay_nghi_t9 , 0) as ngay_nghi_t9,
                            coalesce(E.ngay_nghi_t10 , 0) as ngay_nghi_t10,
                            coalesce(E.ngay_nghi_t11 , 0) as ngay_nghi_t11,
                            coalesce(E.ngay_nghi_t12 , 0) as ngay_nghi_t12,
                            coalesce(E.ngay_nghi_t1 , 0)+ coalesce(E.ngay_nghi_t2 , 0)+ coalesce(E.ngay_nghi_t3 , 0)+ coalesce(E.ngay_nghi_t4 , 0)+ coalesce(E.ngay_nghi_t5 , 0)+ coalesce(E.ngay_nghi_t6 , 0)+ coalesce(E.ngay_nghi_t7 , 0)+ coalesce(E.ngay_nghi_t8 , 0)+ coalesce(E.ngay_nghi_t9 , 0)+ coalesce(E.ngay_nghi_t10 , 0)+ coalesce(E.ngay_nghi_t11 , 0)+ coalesce(E.ngay_nghi_t12 , 0) as tong_so_ngay_da_nghi,
                            coalesce(F.nghi_phep_nam_truoc_trong_nam_nay) as nghi_phep_nam_truoc_trong_nam_nay
                          from
                            hr_employee he
                          left join hr_department hd on
                            hd.id = he.department_id
                          left join hr_contract hc on
                            he.contract_id = hc.id
                          left join (
                            select
                              employee_id,
                              min(date_start) as ngay_ky_hd_ct
                            from
                              hr_contract hc
                            where
                              hc.x_contract_type not in ('hdtv')
                                and hc.state not in ('draft', 'cancel')
                              group by
                                employee_id ) as A on
                            A.employee_id = he.id
                          left join (
                            select
                              P1.employee_id,
                              coalesce(P1.tong_phep_nam_truoc, 0)-coalesce(P2.ngay_xin_nghi, 0) as ton_phep_nam_truoc
                            from
                              (
                              select
                                hla.employee_id,
                                sum(coalesce(hla.number_of_days , 0)) as tong_phep_nam_truoc
                              from
                                hr_leave_allocation hla
                              left join hr_leave_type hlt on
                                hla.holiday_status_id = hlt.id
                              where
                                hlt.active is true
                                and hlt.x_pay is true
                                and date_part('year', hlt.validity_start) = {0}-1
                                  and hla.state = 'validate'
                                group by
                                  hla.employee_id) as P1
                            left join (
                              select
                                hl.employee_id,
                                sum(hll.number_of_days) as ngay_xin_nghi
                              from
                                hr_leave_log hll
                              left join hr_leave hl on
                                hll.leave_id = hl.id
                              left join hr_leave_type hlt on
                                hl.holiday_status_id = hlt.id
                              where
                                hl.state = 'validate'
                                and date_part('year', hll."date") = {0}-1
                                  and hlt.active is true
                                  and hlt.validity_start is not null
                                  and hlt.x_pay is true
                                  and date_part('year', hlt.validity_start) = {0}-1
                                group by
                                  hl.employee_id) as P2 on
                              P1.employee_id = P2.employee_id) as B on
                            B.employee_id = he.id
                          left join (
                            select
                              hla.employee_id,
                              sum(coalesce(hla.number_of_days , 0)) as phep_cap_nam_nay
                            from
                              hr_leave_allocation hla
                            left join hr_leave_type hlt on
                              hla.holiday_status_id = hlt.id
                            where
                              hlt.active is true
                              and hlt.x_pay is true
                              and hlt.validity_start is not null
                              and date_part('year', hlt.validity_start) = {0}
                                and hla.state = 'validate'
                              group by
                                hla.employee_id) as C on
                            he.id = C.employee_id
                          left join (
                             select
                         employee_id,
                         sum(ngay_nghi_t1) as ngay_nghi_t1,
                         sum(ngay_nghi_t2) as ngay_nghi_t2,
                         sum(ngay_nghi_t3) as ngay_nghi_t3,
                         sum(ngay_nghi_t4) as ngay_nghi_t4,
                         sum(ngay_nghi_t5) as ngay_nghi_t5,
                         sum(ngay_nghi_t6) as ngay_nghi_t6,
                        sum(ngay_nghi_t7) as ngay_nghi_t7,
                         sum(ngay_nghi_t8) as ngay_nghi_t8,
                         sum(ngay_nghi_t9) as ngay_nghi_t9,
                         sum(ngay_nghi_t10) as ngay_nghi_t10,
                         sum(ngay_nghi_t11) as ngay_nghi_t11,
                         sum(ngay_nghi_t12) as ngay_nghi_t12
                        from
                         (select
                            hl.employee_id,
                            case
                           date_part('month', hll."date") when 1 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t1,
                            case
                           date_part('month', hll."date") when 2 then hll.number_of_days
                        
                           else 0
                            end as ngay_nghi_t2,
                            case
                           date_part('month', hll."date") when 3 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t3,
                            case
                           date_part('month', hll."date") when 4 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t4,
                            case
                           date_part('month', hll."date") when 5 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t5,
                            case
                           date_part('month', hll."date") when 6 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t6,
                            case
                           date_part('month', hll."date") when 7 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t7,
                            case
                           date_part('month', hll."date") when 8 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t8,
                            case
                           date_part('month', hll."date") when 9 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t9,
                            case
                           date_part('month', hll."date") when 10 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t10,
                            case
                           date_part('month', hll."date") when 11 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t11,
                            case
                           date_part('month', hll."date") when 12 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t12
                          from
                            hr_leave_log hll
                          left join hr_leave hl on
                            hll.leave_id = hl.id
                          left join hr_leave_type hlt on
                            hlt.id = hl.holiday_status_id
                          where
                            hlt.active is true
                            and hlt.x_pay is true
                            and date_part('year', hlt.validity_start)= {0} - 1
                           and hl.state = 'validate'
                         ) as XXX
                        group by XXX.employee_id
                             ) as D on
                            D.employee_id = he.id
                            left join (
                             select
                         employee_id,
                         sum(ngay_nghi_t1) as ngay_nghi_t1,
                         sum(ngay_nghi_t2) as ngay_nghi_t2,
                         sum(ngay_nghi_t3) as ngay_nghi_t3,
                         sum(ngay_nghi_t4) as ngay_nghi_t4,
                         sum(ngay_nghi_t5) as ngay_nghi_t5,
                         sum(ngay_nghi_t6) as ngay_nghi_t6,
                         sum(ngay_nghi_t7) as ngay_nghi_t7,
                         sum(ngay_nghi_t8) as ngay_nghi_t8,
                         sum(ngay_nghi_t9) as ngay_nghi_t9,
                         sum(ngay_nghi_t10) as ngay_nghi_t10,
                         sum(ngay_nghi_t11) as ngay_nghi_t11,
                         sum(ngay_nghi_t12) as ngay_nghi_t12
                        from
                         (select
                            hl.employee_id,
                            case
                           date_part('month', hll."date") when 1 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t1,
                            case
                           date_part('month', hll."date") when 2 then hll.number_of_days
                        
                           else 0
                            end as ngay_nghi_t2,
                            case
                           date_part('month', hll."date") when 3 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t3,
                            case
                           date_part('month', hll."date") when 4 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t4,
                            case
                           date_part('month', hll."date") when 5 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t5,
                            case
                           date_part('month', hll."date") when 6 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t6,
                            case
                           date_part('month', hll."date") when 7 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t7,
                            case
                           date_part('month', hll."date") when 8 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t8,
                            case
                           date_part('month', hll."date") when 9 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t9,
                            case
                           date_part('month', hll."date") when 10 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t10,
                            case
                           date_part('month', hll."date") when 11 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t11,
                            case
                           date_part('month', hll."date") when 12 then hll.number_of_days
                           else 0
                            end as ngay_nghi_t12
                          from
                            hr_leave_log hll
                          left join hr_leave hl on
                            hll.leave_id = hl.id
                          left join hr_leave_type hlt on
                            hlt.id = hl.holiday_status_id
                          where 1=1
                          	and (date_part('year', hlt.validity_start)= {0} or date_part('year', hlt.validity_start)= {0}-1)
                          	and hlt.validity_start is not null
                            and hlt.active is true
                            and hlt.x_pay is true
                            and date_part('year', hll."date")= {0}
                           and hl.state = 'validate'
                         ) as XXX
                        group by XXX.employee_id
                             ) as E on
                            E.employee_id = he.id
                            left join (
                             select
                         hl.employee_id ,
                         sum(hll.number_of_days) as nghi_phep_nam_truoc_trong_nam_nay
                         from hr_leave_log hll
                          left join hr_leave hl on hll.leave_id = hl.id
                          left join hr_leave_type hlt on hlt.id = hl.holiday_status_id
                          where
                            hlt.active is true
                            and hlt.x_pay is true
                            and hlt.validity_start is not null
                            and date_part('year', hlt.validity_start)= {0} - 1
                            and date_part('year', hll."date") = {0}
                           and hl.state = 'validate'
                        group by hl.employee_id
                             ) as F on
                            F.employee_id = he.id
                          where
                            he.active is true ) as G

                    """.format(year)
        self._cr.execute(query)
        lists = self._cr.dictfetchall()
        row = 4
        ws.cell(1, 13).value = 'BẢNG THEO DÕI NGÀY PHÉP NĂM ' + str(year)
        for index, l in enumerate(lists):
            ws.cell(row, 1).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 2).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 3).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 4).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 5).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 6).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 7).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 8).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 9).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 10).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 11).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 12).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 13).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 14).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 15).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 16).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 17).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 18).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 19).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 20).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 21).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 22).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 23).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 24).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['ma_nhan_vien'] or ''
            ws.cell(row, 3).value = l['ho_ten'] or ''
            ws.cell(row, 4).value = l['chuc_vu'] or ''
            ws.cell(row, 5).value = l['bo_phan'] or ''
            ws.cell(row, 6).value = l['ngay_bat_dau'] or ''
            ws.cell(row, 7).value = l['ngay_ky_hd_ct'] or ''
            ws.cell(row, 8).value = l['ton_phep_nam_truoc'] or ''
            ws.cell(row, 9).value = l['phep_cap_nam_nay'] or ''
            ws.cell(row, 10).value = l['tong_so_phep_duoc_huong'] or ''
            ws.cell(row, 11).value = l['ngay_nghi_t1'] or ''
            ws.cell(row, 12).value = l['ngay_nghi_t2'] or ''
            ws.cell(row, 13).value = l['ngay_nghi_t3'] or ''
            ws.cell(row, 14).value = l['ngay_nghi_t4'] or ''
            ws.cell(row, 15).value = l['ngay_nghi_t5'] or ''
            ws.cell(row, 16).value = l['ngay_nghi_t6'] or ''
            ws.cell(row, 17).value = l['ngay_nghi_t7'] or ''
            ws.cell(row, 18).value = l['ngay_nghi_t8'] or ''
            ws.cell(row, 19).value = l['ngay_nghi_t9'] or ''
            ws.cell(row, 20).value = l['ngay_nghi_t10'] or ''
            ws.cell(row, 21).value = l['ngay_nghi_t11'] or ''
            ws.cell(row, 22).value = l['ngay_nghi_t12'] or ''
            ws.cell(row, 23).value = l['tong_so_ngay_da_nghi'] or ''
            ws.cell(row, 24).value = l['so_ngay_phep_con_lai_nam_nay'] or ''
            index += 1
            row += 1
        self.__format_ws__(ws, cell_range='A4:Y' + str(row - 1))
        ws.cell(row + 1, 1).value = 'NOTE:'
        ws.cell(row + 2,
                2).value = '1. Tháng theo dõi tính theo bản chấm công (từ ngày 01 đến ngày cuối cùng của tháng)'
        ws.cell(row + 3,
                2).value = '2. Phép tồn được bảo lưu đến hết quý 1 năm nay (NV không nghỉ hết ngày phép của năm trước thì các ngày phép còn lại sẽ được chuyển sang năm nay và thời hạn được tính đến hết quý 1 năm nay)'
        ws.cell(row + 4,
                2).value = '3. Trường hợp có số ngày làm việc lẻ trong tháng thì số ngày làm việc lẻ đó được tính thời gian nghỉ hàng năm theo nguyên tắc sau đây:'
        ws.cell(row + 5, 2).value = '- Từ 15 ngày trở lên:  01 ngày phép'
        ws.cell(row + 6, 2).value = '- Từ đủ 07 ngày đến dưới 15 ngày: 0.5 ngày phép'
        ws.cell(row + 7, 2).value = '- Dưới 07 ngày: không được tính ngày nghỉ phép'
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo Balance.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }

    def get_excel_report_advance(self, date_from, date_to):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/advance.xlsx')
        ws = wb['Data']
        query = """
                    select 
                    he.x_code as ma_nv,
                    he."name" as ho_va_ten,
                    he.job_title as chuc_danh,
                    '' hinh_thuc_thanh_toan,
                    he.x_bank_account_holder as ho_ten_nguoi_huong,
                    he.x_bank_account as tai_khoan_huong_thu,
                    he.x_bank_name as ten_ngan_hang,
                    coalesce(hpo.amount,0) as tien_tam_ung,
                    hpo.note as ghi_chu
                    from hr_employee he 
                    left join hr_payroll_other hpo on hpo.employee_id =he.id 
                    where hpo.state ='approved' and hpo.categ_type ='advance'
                    and hpo."date" between '{0}' and '{1}'
                    """.format(date_from, date_to)
        self._cr.execute(query)
        lists = self._cr.dictfetchall()
        row = 5
        ws.cell(2, 5).value = str(date_from.strftime('%d-%m-%Y')) + ' đến ngày ' + str(date_to.strftime('%d-%m-%Y'))
        tong = 0.0
        for index, l in enumerate(lists):
            ws.cell(row, 1).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 2).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 3).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 4).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 5).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 6).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 7).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 8).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 9).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['ho_va_ten'] or ''
            ws.cell(row, 3).value = l['ma_nv'] or ''
            ws.cell(row, 4).value = l['chuc_danh'] or ''
            ws.cell(row, 5).value = l['tien_tam_ung'] or ''
            ws.cell(row, 5).number_format = '#,##0.00'
            ws.cell(row, 6).value = l['hinh_thuc_thanh_toan'] or ''
            ws.cell(row, 7).value = l['ho_ten_nguoi_huong'] or ''
            ws.cell(row, 8).value = l['tai_khoan_huong_thu'] or ''
            ws.cell(row, 9).value = l['ten_ngan_hang'] or ''
            tong += l['tien_tam_ung'] or 0.0
            index += 1
            row += 1
        self.__format_ws__(ws, cell_range='A5:I' + str(row))
        ws.cell(row, 2).value = 'Tổng'
        ws.cell(row, 2).number_format = '#,##0.00'
        ws.cell(row, 2).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 5).value = tong
        ws.cell(row, 5).number_format = '#,##0.00'
        ws.cell(row, 5).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 1, 2).value = 'Số tiền bằng chữ:'
        ws.cell(row + 1, 2).font = Font(size=12, name='Times New Roman', bold=True)
        utility_obj = self.env['hcsv.utility']
        company_currency = self.env.user.company_id.currency_id
        sumChu = utility_obj.convert_amount_to_words(amount=tong, currency=company_currency).capitalize()
        ws.cell(row + 1, 3).value = sumChu
        ws.cell(row + 1, 3).font = Font(size=12, name='Times New Roman', italic=True)
        ws.cell(row + 2, 2).value = date.today().strftime('%d-%m-%Y')
        ws.cell(row + 2, 2).font = Font(size=12, name='Times New Roman', italic=True)
        ws.cell(row + 3, 2).value = 'NGƯỜI LẬP BẢNG'
        ws.cell(row + 3, 2).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 3, 6).value = 'PHỤ TRÁCH KẾ TOÁN'
        ws.cell(row + 3, 6).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 3, 9).value = 'NGƯỜI DUYỆT'
        ws.cell(row + 3, 9).font = Font(size=12, name='Times New Roman', bold=True)
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo Advance.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }

    def get_excel_report_imprest(self, month, year):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/imprest.xlsx')
        ws = wb['Data']
        query = """
                    select A.ho_va_ten,
                    A.ma_nv,
                    A.chuc_danh,
                    sum(A.tien_cong)-sum(A.tien_tru) as tong_thu_nhap,
                    A.luong_thuc_linh
                    from
                    (select 
                    he."name" as ho_va_ten,
                    he.x_code as ma_nv,
                    he.job_title as chuc_danh,
                    hpl.code as ma,
                    case when hpl.code in ('TNTGCTT','THCKTNK','HTXX','HTTLBDC') then hpl.amount end as tien_cong,
                    case when hpl.code in ('BTLT') then hpl.amount end as tien_tru,
                    hp.x_amount_total as luong_thuc_linh
                    from hr_payslip hp 
                    left join hr_employee he on he.id=hp.employee_id 
                    left join hr_payslip_line hpl on hpl.slip_id =hp.id 
                    where hp.state ='done' and he.x_salary_hold is true
                    and date_part('month', hp.date_from) = {0}
                    and date_part('year', hp.date_from) = {1}
                    ) as A
                    group by
                    A.ho_va_ten,
                    A.ma_nv,
                    A.chuc_danh,
                    A.luong_thuc_linh
                    """.format(month, year)
        self._cr.execute(query)
        lists = self._cr.dictfetchall()
        row = 5
        ws.cell(2, 5).value = str(month) + '-' + str(year)
        tong_tn = 0.0
        tong_luong_tl = 0.0
        for index, l in enumerate(lists):
            ws.cell(row, 1).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 2).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 3).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 4).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 5).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 6).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['ho_va_ten'] or ''
            ws.cell(row, 3).value = l['ma_nv'] or ''
            ws.cell(row, 4).value = l['chuc_danh'] or ''
            ws.cell(row, 5).value = l['tong_thu_nhap'] or ''
            ws.cell(row, 5).number_format = '#,##0.00'
            ws.cell(row, 6).value = l['luong_thuc_linh'] or ''
            ws.cell(row, 6).number_format = '#,##0.00'
            tong_luong_tl += l['luong_thuc_linh'] or 0.0
            tong_tn += l['tong_thu_nhap'] or 0.0
            index += 1
            row += 1
        self.__format_ws__(ws, cell_range='A5:F' + str(row))
        A = 'A' + str(row) + ':D' + str(row)
        ws.merge_cells(A)
        ws.cell(row, 1).value = 'Tổng'
        ws.cell(row, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 5).value = tong_tn
        ws.cell(row, 5).number_format = '#,##0.00'
        ws.cell(row, 5).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 6).value = tong_luong_tl
        ws.cell(row, 6).number_format = '#,##0.00'
        ws.cell(row, 6).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 1, 2).value = 'Số tiền bằng chữ:'
        ws.cell(row + 1, 2).font = Font(size=12, name='Times New Roman', bold=True)
        utility_obj = self.env['hcsv.utility']
        company_currency = self.env.user.company_id.currency_id
        sumChu = utility_obj.convert_amount_to_words(amount=tong_luong_tl, currency=company_currency).capitalize()
        ws.cell(row + 1, 3).value = sumChu
        ws.cell(row + 1, 3).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 2, 2).value = date.today()
        ws.cell(row + 2, 2).font = Font(size=12, name='Times New Roman', italic=True)
        ws.cell(row + 3, 2).value = 'NGƯỜI LẬP BẢNG'
        ws.cell(row + 3, 2).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 3, 4).value = 'PHỤ TRÁCH KẾ TOÁN'
        ws.cell(row + 3, 4).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 3, 6).value = 'NGƯỜI DUYỆT'
        ws.cell(row + 3, 6).font = Font(size=12, name='Times New Roman', bold=True)
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo Imprest.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }

    def get_excel_report_gasoline(self, month, year):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '/../templates/gasoline.xlsx')
        ws = wb['Data']
        query = """
                    select 
                    he.x_code as ma_nv,
                    he."name" as ho_va_ten,
                    he.job_title as chuc_danh,
                    pp."name" as du_an_den,
                    coalesce (hc.x_gasoline_standard,0) as dinh_muc_thang,
                    A.amount as so_ngay_lam_trong_thang,
                    B.amount as so_ngay_cong_tieu_chuan,
                    (select price from hr_payroll_oil_price hpop where hpop.month='{0}' and hpop."year" ='{1}') as gia_xang,
                    case when B.amount=0 or B.amount is null then 0 else hc.x_gasoline_standard *coalesce (A.amount,0)/B.amount end as so_duoc_huong,
                    case when B.amount=0 or B.amount is null then 0 else hc.x_gasoline_standard *coalesce (A.amount,0)/B.amount*(select price from hr_payroll_oil_price hpop where hpop.month='{0}' and hpop."year" ='{1}') end as quy_ra_tien
                    from hr_employee he 
                    left join hr_payslip hp on hp.employee_id =he.id and {0} = DATE_PART('month',hp.date_from) and  {1}=DATE_PART('year',hp.date_from) and hp.state ='done' and hp.credit_note = false 
                    left join hr_contract hc on hc.id =hp.contract_id 
                    left join project_project pp on pp.id =he.x_project_id 
                    left join (select hpit.code,hpi.id,hpi.amount,hpi.payslip_id from hr_payslip_input hpi 
                    left join hr_payslip_input_type hpit on hpi.input_type_id =hpit.id ) as A on A.payslip_id=hp.id and A.code='OTHER_WORK_DAY_PAID'
                    left join (select hpit.code,hpi.id,hpi.amount,hpi.payslip_id from hr_payslip_input hpi 
                    left join hr_payslip_input_type hpit on hpi.input_type_id =hpit.id ) as B on B.payslip_id=hp.id and B.code='OTHER_WORK_DAY_THEORY'
                    where ({0} between DATE_PART('month',hp.date_from) and  DATE_PART('month',hp.date_from))
                    and ({1} between DATE_PART('year',hp.date_from) and  DATE_PART('year',hp.date_from))
                    and hc.x_gasoline_standard > 0 
                    """.format(month, year)
        self._cr.execute(query)
        lists = self._cr.dictfetchall()
        query2 = """  
              select price as gia_xang_tc from hr_payroll_oil_price hpop where hpop.month='{0}' and hpop."year" ='{1}';
              """.format(month, year)
        self._cr.execute(query2)
        list2 = self._cr.dictfetchall()

        def num_days_between(start, end, week_day):
            num_weeks, remainder = divmod((end - start).days, 7)
            if (week_day - start.weekday()) % 7 <= remainder:
                return num_weeks + 1
            else:
                return num_weeks

        end_date = calendar.monthrange(int(year), int(month))[1]
        d0 = date(int(year), int(month), 1)
        d1 = date(int(year), int(month), end_date)
        num_of_sunday = num_days_between(d0, d1, 6)
        num_of_days = (d1 - d0).days + 1
        num_tc = num_of_days - num_of_sunday
        a = calendar.monthrange(int(year), int(month))[1]
        row = 6
        ws.cell(2, 7).value = str(month) + '-' + str(year)
        for index, l2 in enumerate(list2):
            ws.cell(4, 7).value = l2['gia_xang_tc'] or ''
            ws.cell(4, 7).number_format = '#,##0.00'
            ws.cell(4, 7).font = Font(size=12, name='Times New Roman')
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()
        ws.cell(3, 7).value = num_tc or 0.0
        ws.cell(3, 7).number_format = '#,##0.00'
        tong_lit = 0.0
        tong_tien = 0.0
        for index, l in enumerate(lists):
            ws.cell(row, 1).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 2).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 3).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 4).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 5).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 6).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 7).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 8).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 9).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 10).font = Font(size=12, name='Times New Roman')
            ws.cell(row, 1).value = index + 1
            ws.cell(row, 2).value = l['ho_va_ten'] or ''
            ws.cell(row, 3).value = l['ma_nv'] or ''
            ws.cell(row, 4).value = l['chuc_danh'] or ''
            # ws.cell(row, 5).value = l['du_an_den'] or ''
            ws.cell(row, 5).value = l['dinh_muc_thang'] or ''
            ws.cell(row, 6).value = l['so_ngay_lam_trong_thang'] or ''
            ws.cell(row, 7).value = l['so_duoc_huong'] or ''
            ws.cell(row, 7).number_format = '#,##0.00'
            ws.cell(row, 8).value = l['quy_ra_tien'] or ''
            ws.cell(row, 8).number_format = '#,##0.00'
            ws.cell(row, 9).value = ''
            tong_lit += l['so_duoc_huong'] or 0.0
            tong_tien += l['quy_ra_tien'] or 0.0
            index += 1
            row += 1
        self.__format_ws__(ws, cell_range='A6:I' + str(row))
        A = 'A' + str(row) + ':F' + str(row)
        ws.merge_cells(A)
        ws.cell(row, 1).value = 'Tổng'
        ws.cell(row, 1).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 7).value = tong_lit
        ws.cell(row, 7).number_format = '#,##0.00'
        ws.cell(row, 7).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row, 8).value = tong_tien
        ws.cell(row, 8).number_format = '#,##0.00'
        ws.cell(row, 8).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 2, 2).value = date.today()
        ws.cell(row + 2, 2).font = Font(size=12, name='Times New Roman', italic=True)
        ws.cell(row + 4, 2).value = 'NGƯỜI LẬP BẢNG'
        ws.cell(row + 4, 2).font = Font(size=12, name='Times New Roman', bold=True)
        ws.cell(row + 4, 7).value = 'TỔNG GIÁM ĐỐC'
        ws.cell(row + 4, 7).font = Font(size=12, name='Times New Roman', bold=True)
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo Gasoline.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=%s&filename_field=name&field=datas&download=true&name=%s" % (
                attachment_id.id,
                attachment_id.name
            ),
            'target': 'new',
        }

    def _compute_input_days(self):
        if not self.date_from or not self.date_to:
            return []
        input_type_obj = self.env['hr.payslip.input.type'].sudo()
        inputs = []

        _date_from = max(self.date_from, self.contract_id.date_start)
        if not self.contract_id.date_end:
            _date_to = self.date_to
        else:
            _date_to = min(self.date_to, self.contract_id.date_end)

        is_saturday_half = self.contract_id.resource_calendar_id and self.contract_id.resource_calendar_id.full_time_required_hours == 44.0
        is_saturday_full = self.contract_id.resource_calendar_id and self.contract_id.resource_calendar_id.full_time_required_hours == 48.0
        is_hourly_wage = self.contract_id.structure_type_id.wage_type == 'hourly'

        # Số ngày làm việc lý thuyết trong tháng
        def num_days_between(start, end, week_day):
            num_weeks, remainder = divmod((end - start).days, 7)
            if (week_day - start.weekday()) % 7 <= remainder:
                return num_weeks + 1
            else:
                return num_weeks

        num_of_sunday = num_days_between(self.date_from, self.date_to, 6)
        num_of_saturday = num_days_between(self.date_from, self.date_to, 5)
        num_of_days = (self.date_to - self.date_from).days + 1
        theory_days = num_of_days
        _theory_days = num_of_days - num_of_sunday
        if is_saturday_full:
            theory_days = num_of_days - num_of_sunday
        elif is_saturday_half:
            theory_days = num_of_days - num_of_sunday - num_of_saturday * 0.5
        inputs.append((0, 0, {
            'amount': _theory_days,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_WORK_DAY_THEORY', 'Số ngày công lý thuyết')
        }))
        inputs.append((0, 0, {
            'amount': theory_days * 8,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_WORK_HOUR_THEORY', 'Số giờ công lý thuyết')
        }))

        # Số ngày công thực tế (đếm số ngày nhập chấm công)
        worked_days = self.env['hr.work.entry'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('x_date', '>=', self.date_from),
            ('x_date', '<=', self.date_to),
            ('x_line_ids', '!=', False),
            ('state', '=', 'validated'),
            ('work_entry_type_id', '=', self.env.ref('hr_work_entry.work_entry_type_attendance').id),
            '|', ('x_shift_id', '=', False), ('x_shift_id.is_leave', '!=', True)
        ])
        date2work_entries = {}
        for w in worked_days:
            date2work_entries[w.x_date] = w

        inputs.append((0, 0, {
            'amount': len(worked_days),
            'input_type_id': input_type_obj.get_type_by_code('OTHER_WORK_DAY_PAID', 'Số ngày công thực tế')
        }))

        # Số ngày nghỉ phép có tính lương
        paid_leaves = self.env['hr.leave.log'].sudo().search([
            ('leave_id.employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('leave_id.state', '=', 'validate'),
            ('leave_id.holiday_status_id.x_pay', '=', True),
        ])
        # Các mục nghỉ lễ trong tháng
        global_offs = self.env['hr.global.off'].sudo().search([
            ('active', '=', True),
            '|',
            '&', ('date_start', '>=', _date_from), ('date_start', '<=', _date_to),
            '&', ('date_end', '>=', _date_from), ('date_end', '<=', _date_to),
        ])
        # Số giờ công thực tế
        work_entry_hours_converted = self.env['hr.work.entry.line'].sudo().search([
            ('entry_id.employee_id', '=', self.employee_id.id),
            ('entry_id.x_date', '>=', self.date_from),
            ('entry_id.x_date', '<=', self.date_to),
            ('entry_id.state', '=', 'validated'),
        ])
        # Gộp giờ công quy đổi.
        # Với NV làm gói/khoán (không hưởng lương OT - x_ot_allowed = False):
        # giờ công quy đổi mỗi NGÀY tối đa = số giờ làm theo LỊCH LÀM VIỆC của ngày đó.
        #   - Thứ 2-6: tối đa 8h
        #   - Thứ 7: 4h (lịch 44h/tuần) / 8h (lịch 48h/tuần)
        #   - Chủ nhật: cap 8h (VẪN tính, đi làm CN quy về tối đa 8h - theo chính sách package)
        def _scheduled_hours(wdate, sat_half):
            wd = wdate.weekday()
            if wd == 6:        # Chủ nhật - cap 8h (vẫn tính)
                return 8
            if wd == 5:        # Thứ 7
                return 4 if sat_half else 8
            return 8           # Thứ 2 - Thứ 6

        if not self.contract_id.x_ot_allowed:
            def _is_global_off_date(d):
                return any(g.date_start <= d <= g.date_end for g in global_offs)

            daily_converted = {}  # x_date -> tổng hour_converted trong ngày (gộp các ca)
            for x in work_entry_hours_converted:
                wdate = x.entry_id.x_date
                # Ngày nghỉ lễ đã được cộng riêng ở global_off_paid_hours => bỏ qua
                if global_offs and _is_global_off_date(wdate):
                    continue
                daily_converted[wdate] = daily_converted.get(wdate, 0.0) + x.hour_converted
            hours_converted = sum(
                min(day_hours, _scheduled_hours(wdate, is_saturday_half))
                for wdate, day_hours in daily_converted.items()
            )
        else:
            hours_converted = sum(x.hour_converted for x in work_entry_hours_converted)
        # Số giờ công hỗ trợ đi lại
        work_allowance_hours_converted = self.env['hr.work.entry.allowance'].sudo().search([
            ('entry_id.employee_id', '=', self.employee_id.id),
            ('entry_id.x_date', '>=', self.date_from),
            ('entry_id.x_date', '<=', self.date_to),
            ('entry_id.state', '=', 'validated'),
        ])

        # Mỗi ngày nghỉ có tính lương được tính hệ số giờ = 100%
        for item in paid_leaves:
            hours_converted += 8.0 * item.number_of_days
        # Mỗi ngày nghỉ lễ trong tuần (ngày làm việc) được tính hệ số = 100% (không gồm những ngày có chấm công đi làm)
        global_off_paid_hours = 0.0
        for item in global_offs:
            date_start = max(item.date_start, _date_from)
            date_end = min(item.date_end, _date_to)
            days = (date_end - date_start).days + 1
            for i in range(days):
                date = date_start + relativedelta(days=i)
                if is_hourly_wage:  # Lương theo giờ
                    continue
                elif date.weekday() not in [5]:  # Ngày trong tuần hoặc chủ nhật => 8h
                    global_off_paid_hours += 8
                elif date.weekday() == 5:  # Thứ 7
                    if is_saturday_half:
                        global_off_paid_hours += 4
                    elif is_saturday_full:
                        global_off_paid_hours += 8
                # elif date in date2work_entries:  # Ngày nghỉ lễ có chấm công
                #     global_off_paid_hours += 8
        hours_converted += global_off_paid_hours

        # _logger.error('x0: ')
        # _logger.error(hours_converted)

        # Bù công nhập thủ công
        manual_hour_ids = self.env['hr.payroll.other.hour'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'approved'),
        ])
        total_manual_hours = sum(x.hour for x in manual_hour_ids)
        hours_converted += total_manual_hours

        # _logger.error('x1: ')
        # _logger.error(hours_converted)
        contracts = self.employee_id._get_contracts(self.date_from, self.date_from, ['open', 'close'])

        if not (_date_from > self.date_from and len(contracts) == 1) and self.employee_id.x_calendar_type == 'fix' and not self.contract_id.x_ot_allowed:
            _logger.error('x2: ')
            _logger.error(hours_converted)
            hours_converted = min(hours_converted, theory_days * 8)
        # Cộng giờ hỗ trợ đi lại sau khi đã tính max
        hours_converted += sum(x.hour for x in work_allowance_hours_converted)

        total_hour_converted = hours_converted
        if not (_date_from > self.date_from and len(contracts) == 1):
            inputs.append((0, 0, {
                'amount': total_hour_converted,
                'input_type_id': input_type_obj.get_type_by_code('OTHER_WORK_HOUR_CONVERTED', 'Số giờ công quy đổi')
            }))

        # Số ngày nghỉ cả ngày có tính lương
        count_leave_paid_full_day = 0
        for item in paid_leaves:
            if item.date in date2work_entries:
                continue
            count_leave_paid_full_day += item.number_of_days

        # Số ngày nghỉ bù / không việc
        # compensatory_days = self.env['hr.work.entry'].sudo().search_count([
        #     ('employee_id', '=', self.employee_id.id),
        #     ('x_date', '>=', self.date_from),
        #     ('x_date', '<=', self.date_to),
        #     ('state', '=', 'validated'),
        #     ('work_entry_type_id', '=', self.env.ref('hr_work_entry.work_entry_type_attendance').id),
        #     ('x_shift_id.code', '=', 'NB'),
        # ])
        # Số ngày xin nghỉ không lương
        unpaid_leaves = self.env['hr.leave.log'].sudo().search([
            ('leave_id.employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('leave_id.holiday_status_id.x_pay', '=', False),
            ('leave_id.state', '=', 'validate'),
        ])

        final_total_hour_converted = total_hour_converted

        # đơn giá theo giờ của hợp đồng hiện tại
        if self.contract_id.wage_type == 'hourly':
            wage_hour = self.contract_id.hourly_wage
        else:
            wage_total = self.contract_id.wage
            wage_hour = wage_total / (theory_days * 8)


        _total_hour_converted = 0
        if _date_from > self.date_from and len(contracts) == 1:
            # if len(contracts) != 1:
            #     raise ValidationError(_('Cannot identify last active contract for employee %s!') % self.employee_id.name)
            _is_saturday_half = contracts[0].resource_calendar_id and contracts[
                0].resource_calendar_id.full_time_required_hours == 44.0
            _is_saturday_full = contracts[0].resource_calendar_id and contracts[
                0].resource_calendar_id.full_time_required_hours == 48.0
            _total_hour_converted = 0
            # Số ngày nghỉ phép có tính lương
            _paid_leaves = self.env['hr.leave.log'].sudo().search([
                ('leave_id.employee_id', '=', self.employee_id.id),
                ('date', '>=', self.date_from),
                ('date', '<', _date_from),
                ('leave_id.state', '=', 'validate'),
                ('leave_id.holiday_status_id.x_pay', '=', True),
            ])
            # Các mục nghỉ lễ trong tháng
            if contracts[0].x_type_employee != '2':
                _global_offs = self.env['hr.global.off'].sudo().search([
                    ('active', '=', True),
                    '|',
                    '&', ('date_start', '>=', self.date_from), ('date_start', '<', _date_from),
                    '&', ('date_end', '>=', self.date_from), ('date_end', '<', _date_from),
                ])
            else:
                _global_offs = self.env['hr.global.off']
            # Số giờ công thực tế
            _work_entry_hours_converted = self.env['hr.work.entry.line'].sudo().search([
                ('entry_id.employee_id', '=', self.employee_id.id),
                ('entry_id.x_date', '>=', self.date_from),
                ('entry_id.x_date', '<', _date_from),
                ('entry_id.state', '=', 'validated'),
            ])

            def check_global_offs(work_entry, global_offs):
                result = True
                for g in global_offs:
                    if g.date_start <= work_entry.entry_id.x_date <= g.date_end:
                        return True
                    else:
                        result = False
                return result
            # Cùng quy tắc với nhánh chính: NV không hưởng lương OT thì giờ quy đổi mỗi ngày
            # tối đa = số giờ làm theo lịch (Thứ 7 = 4h/8h, Chủ nhật = 0h kể cả có chấm công).
            _hours_converted = 0
            if not contracts[0].x_ot_allowed:
                _daily_converted = {}  # x_date -> tổng hour_converted trong ngày
                for x in _work_entry_hours_converted:
                    wdate = x.entry_id.x_date
                    # Ngày nghỉ lễ đã cộng riêng => bỏ qua
                    if len(_global_offs) > 0 and check_global_offs(x, _global_offs):
                        continue
                    _daily_converted[wdate] = _daily_converted.get(wdate, 0.0) + x.hour_converted
                _hours_converted = sum(
                    min(day_hours, _scheduled_hours(wdate, _is_saturday_half))
                    for wdate, day_hours in _daily_converted.items()
                )
            else:
                _hours_converted = sum(x.hour_converted for x in _work_entry_hours_converted)
            # _hours_converted = sum(x.hour_converted for x in _work_entry_hours_converted)
            _work_allowance_hours_converted = self.env['hr.work.entry.allowance'].sudo().search([
                ('entry_id.employee_id', '=', self.employee_id.id),
                ('entry_id.x_date', '>=', self.date_from),
                ('entry_id.x_date', '<', _date_from),
                ('entry_id.state', '=', 'validated'),
            ])
            _hours_converted += sum(x.hour for x in _work_allowance_hours_converted)
            # Mỗi ngày nghỉ có tính lương được tính hệ số giờ = 100%
            for item in _paid_leaves:
                _hours_converted += 8.0 * item.number_of_days
            # Mỗi ngày nghỉ lễ trong tuần (ngày làm việc) được tính hệ số = 100% (không gồm những ngày có chấm công đi làm)
            _global_off_paid_hours = 0.0
            for item in _global_offs:
                _date_start = max(item.date_start, self.date_from)
                _date_end = min(item.date_end, _date_from - relativedelta(days=1))
                days = (_date_end - _date_start).days + 1
                for i in range(days):
                    _date = _date_start + relativedelta(days=i)
                    # if _date in date2work_entries:  # Ngày nghỉ lễ có chấm công => tính công theo chấm công
                    #     continue
                    # if _date.weekday() not in (5, 6):  # Ngày trong tuần => 8h
                    if _date.weekday() not in [5]:  # Ngày trong tuần hoặc chủ nhật => 8h
                        _global_off_paid_hours += 8
                    elif _date.weekday() == 5:  # Thứ 7
                        if _is_saturday_half:
                            _global_off_paid_hours += 4
                        elif _is_saturday_full:
                            _global_off_paid_hours += 8

            # Bù công nhập thủ công
            _manual_hour_ids = self.env['hr.payroll.other.hour'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', _date_from),
                ('state', '=', 'approved'),
            ])
            _total_manual_hours = sum(x.hour for x in _manual_hour_ids)
            _hours_converted += _total_manual_hours

            _total_hour_converted = _hours_converted + _global_off_paid_hours
            # đơn giá theo giờ của hợp đồng cũ
            if contracts[0].wage_type == 'hourly':
                _wage_hour = contracts[0].hourly_wage
            else:
                _wage_total = contracts[0].wage
                _wage_hour = _wage_total / (theory_days * 8)
            _wage = _wage_hour * _total_hour_converted
            total_hour_converted_ = total_hour_converted + _global_off_paid_hours
            if self.employee_id.x_calendar_type == 'fix' and not self.contract_id.x_ot_allowed:
                total_hour_converted_ = total_hour_converted - sum(x.hour for x in work_allowance_hours_converted) + _global_off_paid_hours
                total_hour_converted_ = min(total_hour_converted_, theory_days * 8)
                total_hour_converted_ += sum(x.hour for x in work_allowance_hours_converted)
            inputs.append((0, 0, {
                'amount': total_hour_converted_,
                'input_type_id': input_type_obj.get_type_by_code('OTHER_WORK_HOUR_CONVERTED', 'Số giờ công quy đổi')
            }))
            # Tổng lương
            wage = wage_hour * (total_hour_converted_ - _total_hour_converted) + _wage
            final_total_hour_converted = total_hour_converted_
        else:
            wage = wage_hour * total_hour_converted

        # Ngày làm việc cuối cùng trong kỳ = max(ngày chấm công cuối, ngày nghỉ phép CÓ
        # lương cuối). Dùng để cap GIỜ CÔNG TIÊU CHUẨN tính lương chính/KPI (NV nghỉ/không
        # làm đủ tháng). KHÔNG dùng cho bù công (giữ nguyên logic bù công cũ theo cả kỳ HĐ).
        _last_dates = [x.entry_id.x_date for x in work_entry_hours_converted if x.entry_id.x_date]
        _last_dates += [l.date for l in paid_leaves if l.date]
        _last_work_day = max(_last_dates) if _last_dates else self.date_to

        # Số giờ hỗ trợ lương bù công
        # đoạn code lặp lại này tính số ngày lý thuyết đi làm theo hợp đồng
        n_date_start = self.contract_id.date_start
        if _date_from > self.date_from and len(contracts) == 1:
            n_date_start = contracts[0].date_start
        n_date_from = max(n_date_start, self.date_from)
        n_date_to = self.date_to
        if self.contract_id.date_end:
            n_date_to = min(self.contract_id.date_end, self.date_to)

        n_sunday = num_days_between(n_date_from, n_date_to, 6)
        n_saturday = num_days_between(n_date_from, n_date_to, 5)
        n_days = (n_date_to - n_date_from).days + 1
        n_theory_days = n_days - n_sunday
        if is_saturday_half:
            n_theory_days -= n_saturday * 0.5
        # hours_support = (len(worked_days) + count_leave_paid_full_day + compensatory_days) * 8 - total_hour_converted
        hours_support = (n_theory_days - sum(x.number_of_days for x in unpaid_leaves)) * 8 - final_total_hour_converted
        if is_hourly_wage:
            hours_support = 0
        # if is_saturday_half:
        #     hours_support -= num_of_saturday * 4
        # hours_support *= 0.7
        inputs.append((0, 0, {
            'amount': max(hours_support, 0),
            'input_type_id': input_type_obj.get_type_by_code('OTHER_WORK_HOUR_SUPPORT', 'Số giờ hỗ trợ lương bù công')
        }))

        # ===== Tách thu nhập theo giờ thành 4 thành phần (bảng lương mới từ 01/07/2026) =====
        # Tổng 4 thành phần (khi điểm=1000) = 'wage' cũ (dòng gộp) -> net không đổi.
        standard_hours = theory_days * 8
        score = self._get_kpi_score()                              # điểm KPI, mặc định 1000

        # Tách thu nhập theo giờ thành base / KPI / OT / đi lại — TÁCH THEO TỪNG ĐOẠN HỢP
        # ĐỒNG. OT tính CẮT TRẦN TỪNG NGÀY: phần giờ quy đổi VƯỢT giờ lịch mỗi ngày (T2-6=8h,
        # T7=4/8h, CN=8h) -> lương ngoài giờ (chỉ NV hưởng OT). Giờ base = giờ làm quy đổi −
        # OT (đã gồm nghỉ phép/lễ có lương), cap ở standard_hours (208). Mẫu số base/KPI = 208
        # như mẫu gốc; đơn giá OT/đi lại theo HĐ của đoạn. NV 1 HĐ cả tháng -> 1 đoạn = cả kỳ.
        def _seg_income(converted, seg_travel, seg_start, seg_end, ct, rate):
            if ct.structure_type_id.wage_type == 'hourly':
                return 0.0, 0.0, 0.0, 0.0
            work = max(0.0, converted - seg_travel)
            sat_half = bool(ct.resource_calendar_id) and \
                ct.resource_calendar_id.full_time_required_hours == 44.0
            # OT = tổng phần VƯỢT giờ lịch MỖI NGÀY (Chủ nhật vẫn cho 8h vào base). NV package
            # (không hưởng OT) -> không tách OT theo ngày (giờ quy đổi đã cắt trần sẵn).
            per_day_ot = 0.0
            if ct.x_ot_allowed:
                daily = {}
                for x in work_entry_hours_converted:
                    d = x.entry_id.x_date
                    if d and seg_start <= d <= seg_end:
                        daily[d] = daily.get(d, 0.0) + x.hour_converted
                per_day_ot = sum(max(0.0, h - _scheduled_hours(d, sat_half))
                                 for d, h in daily.items())
            base_h = min(max(0.0, work - per_day_ot), standard_hours)
            ot_h = max(0.0, work - base_h)
            base_wage = ct.x_insurance_wage if ct.x_insurance_wage else max(0.0, ct.wage - ct.kpi_norm)
            base = (base_wage * base_h / standard_hours) if standard_hours else 0.0
            kpi = (ct.kpi_norm * base_h / standard_hours * (score / 1000.0)) if standard_hours else 0.0
            return base, kpi, rate * ot_h, rate * seg_travel

        travel_hours = sum(x.hour for x in work_allowance_hours_converted)
        if _date_from > self.date_from and len(contracts) == 1:
            # 2 hợp đồng trong tháng: đoạn HĐ trước [date_from, _date_from) tính theo lương
            # HĐ trước; đoạn HĐ hiện tại [_date_from, date_to] theo lương HĐ hiện tại.
            _prior_travel = sum(x.hour for x in _work_allowance_hours_converted)
            b1, k1, o1, t1 = _seg_income(
                _total_hour_converted, _prior_travel,
                self.date_from, _date_from - relativedelta(days=1),
                contracts[0], _wage_hour)
            b2, k2, o2, t2 = _seg_income(
                final_total_hour_converted - _total_hour_converted, travel_hours - _prior_travel,
                _date_from, self.date_to, self.contract_id, wage_hour)
            base_salary, kpi_salary, ot_salary, travel_salary = b1 + b2, k1 + k2, o1 + o2, t1 + t2
        else:
            base_salary, kpi_salary, ot_salary, travel_salary = _seg_income(
                final_total_hour_converted, travel_hours,
                max(self.contract_id.date_start, self.date_from), self.date_to,
                self.contract_id, wage_hour)

        # OTHER_WAGE_TOTAL nay = Lương chính thực tế (chỉ phần lương BH x hệ số)
        inputs.append((0, 0, {
            'amount': base_salary,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_WAGE_TOTAL', 'Lương chính thực tế')
        }))
        inputs.append((0, 0, {
            'amount': kpi_salary,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_KPI_SALARY', 'Lương KPI thực tế')
        }))
        inputs.append((0, 0, {
            'amount': ot_salary,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_OT_SALARY', 'Lương ngoài giờ')
        }))
        inputs.append((0, 0, {
            'amount': travel_salary,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_TRAVEL_SALARY', 'Lương hỗ trợ đi lại')
        }))

        return inputs

    def _compute_meal_support(self):
        """Tiền hỗ trợ ăn ca = định mức/suất x số ngày làm việc thực tế > 4h.

        - Chỉ áp dụng CBNV chính thức (x_type_employee='1') hoặc thử việc ('3').
        - Ngày thường: có số giờ làm > 4h = 1 suất.
        - Hợp đồng 44h/tuần: Thứ 7 VÀ Chủ nhật chỉ tính 1 suất khi giờ chấm công VÀO MÃ
          DỰ ÁN ĐÃ PHÂN LOẠI (project.x_project_type có dữ liệu) > 4h (không xét tổng
          giờ, không tính mã dự án chưa phân loại). Hợp đồng 48h: mọi ngày xét tổng giờ > 4h.
        - Định mức/suất lấy từ system param 'hr_payroll.meal_rate' (mặc định 40.000đ).
        """
        self.ensure_one()
        contract = self.contract_id
        if not contract or contract.x_type_employee not in ('1', '3'):
            return 0.0
        # Đơn giá/suất lấy theo BẢNG ĐƠN GIÁ ĂN CA (hr.meal.rate) theo kỳ tính lương;
        # không có bản ghi -> fallback param hr_payroll.meal_rate.
        rate = self.env['hr.meal.rate'].get_rate(self.date_from, self.company_id)
        is_44h = bool(contract.resource_calendar_id) and \
            contract.resource_calendar_id.full_time_required_hours == 44.0
        entries = self.env['hr.work.entry'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('x_date', '>=', self.date_from),
            ('x_date', '<=', self.date_to),
            ('state', '=', 'validated'),
            ('work_entry_type_id', '=', self.env.ref('hr_work_entry.work_entry_type_attendance').id),
            '|', ('x_shift_id', '=', False), ('x_shift_id.is_leave', '!=', True),
        ])
        meal_days = 0
        for e in entries:
            if is_44h and e.x_date.weekday() in (5, 6):
                # HĐ 44h, Thứ 7/Chủ nhật: tính khi giờ chấm công vào MÃ DỰ ÁN ĐÃ PHÂN
                # LOẠI (x_project_type có dữ liệu) > 4h.
                if sum(l.hour for l in e.x_line_ids if l.project_id.x_project_type) > 4:
                    meal_days += 1
            elif e.x_total_hours > 4:
                # Ngày thường (mọi HĐ) / HĐ 48h mọi ngày: tổng giờ làm > 4h.
                meal_days += 1
        return meal_days * rate

    def _compute_input_others(self):
        if not self.date_from or not self.date_to:
            return []
        input_type_obj = self.env['hr.payslip.input.type'].sudo()
        inputs = []
        #Điện thoại
        inputs.append((0, 0, {
            'amount': self.contract_id.x_allowance_phone,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_MOBILE', 'Hỗ trợ điện thoại')
        }))
        # Hỗ trợ ăn ca: 40k x số ngày làm > 4h (chỉ chính thức/thử việc)
        # Ăn ca miễn thuế TNCN toàn bộ -> KHÔNG cộng vào thu nhập chịu thuế (xem rule TTNCNPN),
        # nên không cần input riêng cho phần miễn thuế.
        meal_support = self._compute_meal_support()
        inputs.append((0, 0, {
            'amount': meal_support,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_MEAL_SUPPORT', 'Hỗ trợ ăn ca')
        }))
        # Thưởng hoặc các khoản thu nhập khác
        recs = self.env['hr.payroll.other'].search([
            ('state', '=', 'approved'),
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('categ_type', '=', 'bonus'),
        ])
        inputs.append((0, 0, {
            'amount': sum(recs.mapped('amount')) if recs else 0.0,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_BONUS', 'Thưởng hoặc các khoản thu nhập khác')
        }))

        # Các khoản thưởng nóng
        recs = self.env['hr.payroll.other'].search([
            ('state', '=', 'approved'),
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('categ_type', '=', 'instant_bonus'),
        ])
        inputs.append((0, 0, {
            'amount': sum(recs.mapped('amount')) if recs else 0.0,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_BONUS_INSTANT', 'Các khoản thưởng nóng')
        }))

        # Hỗ trợ xăng xe
        fuel_price = self.env['hr.payroll.oil.price'].search([
            ('month', '=', self.date_from.month),
            ('year', '=', self.date_from.year),
        ], limit=1)
        if not fuel_price:
            raise UserError(_('Please enter gas price for this pay period!'))
        inputs.append((0, 0, {
            'amount': fuel_price.price,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_GAS_PRICE', 'Giá xăng theo kỳ tính lương')
        }))

        # Bù/trừ lương tháng
        recs = self.env['hr.payroll.other'].search([
            ('state', '=', 'approved'),
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('categ_type', '=', 'fined'),
        ])
        inputs.append((0, 0, {
            'amount': sum(recs.mapped('amount')) if recs else 0.0,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_FINED', 'Bù/trừ lương tháng')
        }))

        # Tạm ứng
        recs = self.env['hr.payroll.other'].search([
            ('state', '=', 'approved'),
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('categ_type', '=', 'advance'),
        ])
        inputs.append((0, 0, {
            'amount': sum(recs.mapped('amount')) if recs else 0.0,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_ADVANCE', 'Tạm ứng')
        }))

        # Công tác phí
        recs = self.env['hr.work.entry.biz.fee'].sudo().search([
            ('entry_id.employee_id', '=', self.employee_id.id),
            ('entry_id.x_date', '>=', self.date_from),
            ('entry_id.x_date', '<=', self.date_to),
            ('entry_id.state', '=', 'validated'),
        ])
        biz_fee = sum(w.amount for w in recs)
        inputs.append((0, 0, {
            'amount': biz_fee or 0.0,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_BUSINESS_FEE', 'Công tác phí')
        }))

        # Hoàn thuế TNCN năm trước
        recs = self.env['hr.payroll.other'].search([
            ('state', '=', 'approved'),
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('categ_type', '=', 'tax_refund'),
        ])
        inputs.append((0, 0, {
            'amount': sum(recs.mapped('amount')) if recs else 0.0,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_TAX_RETURN', 'Hoàn thuế TNCN năm trước')
        }))

        # Số tiền giảm trừ thuế
        deduction_self = float(self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.deduction_self', 0.0))
        deduction_dependent = float(
            self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.deduction_dependent', 0.0))
        deduction_total = deduction_self + deduction_dependent * len(self.employee_id.x_depend_ids.filtered(lambda l: l.is_depend))
        inputs.append((0, 0, {
            'amount': deduction_total,
            'input_type_id': input_type_obj.get_type_by_code('OTHER_DEDUCTION_PERSONAL_TAX',
                                                             'Tổng mức giảm trừ thuế TNCN')
        }))

        return inputs

    def _compute_inputs(self):
        inputs = []
        # Reset computed inputs
        for line in self.input_line_ids.filtered(lambda l: l.input_type_id.x_readonly):
            inputs.append((2, line.id))

        inputs += self._compute_input_others()
        inputs += self._compute_input_days()

        self.input_line_ids = inputs

    @api.depends('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        super(Payslip, self)._onchange_employee()
        if (not self.employee_id) or (not self.date_from) or (not self.date_to) or not self.contract_id:
            return
        self._compute_inputs()

    @api.model
    def create(self, vals_list):
        employee_id = vals_list.get('employee_id')
        date_from = vals_list.get('date_from')
        date_to = vals_list.get('date_to')
        self._cr.execute(f'''select id from hr_work_entry where employee_id = {employee_id} and x_date between'{date_from}'and '{date_to}' and state not in ('validated', 'cancelled') ''')
        rec = self._cr.dictfetchall()
        if len(rec)>0:
           raise UserError('Không thể tạo phiếu lương vì vẫn còn phiếu chấm công chưa xác nhận')
        res = super(Payslip, self).create(vals_list)
        res._onchange_employee()
        return res

    def _get_new_worked_days_lines(self):
        return [(5, False, False)]


class PayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    x_readonly = fields.Boolean('Is Readonly?', related='input_type_id.x_readonly')

    @api.constrains('payslip_id', 'input_type_id', 'amount')
    def constrain_update_hot_bonus(self):
        hot_bonus_input_type_id = self.env['hr.payslip.input.type'].sudo().search([('code', '=', 'OTHER_BONUS_INSTANT')], limit=1)
        other_bonus_input_type_id = self.env['hr.payslip.input.type'].sudo().search([('code', '=', 'OTHER_BONUS')], limit=1)

        for r in self:
            if r.payslip_id and r.input_type_id:
                if hot_bonus_input_type_id and r.input_type_id.id == hot_bonus_input_type_id.id:
                    r.payslip_id.x_hot_bonus = r.amount
                if other_bonus_input_type_id and r.input_type_id.id == other_bonus_input_type_id.id:
                    r.payslip_id.x_other_bonus = r.amount


class PayslipInputType(models.Model):
    _inherit = 'hr.payslip.input.type'

    x_readonly = fields.Boolean('Is Readonly?', default=0, help="Auto compute data, cannot change by end-user")

    def get_type_by_code(self, code, name):
        res = self.search([('code', '=', code)])
        if res:
            return res[0].id
        else:
            res = self.create({
                'code': code,
                'name': name,
                'x_readonly': True
            })
            return res.id

    # def unlink(self):
    #     if any(r.x_readonly for r in self):
    #         raise UserError(_('Cannot delete system input types!'))
    #     return super(PayslipInputType, self).unlink()
    #
    # def write(self, vals):
    #     if any(r.x_readonly for r in self):
    #         raise UserError(_('Cannot edit system input types!'))
    #     return super(PayslipInputType, self).write(vals)
