# -*- coding: utf-8 -*-
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectManagerLaborCostWizards(models.TransientModel):
    _name = "project.manager.labor.cost.wizards"
    _description = "Nhập tham số non_labor"

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
            "delete from project_manager_labor_cost where master_key = {key}".format(key=self.master_key))
        sql = f''' select  view_detail.year_lastdate,
                            view_detail.month_lastdate,
                            view_detail.leader as name_leader,
                            view_detail.departmentblock_name,
                            sum(coalesce(view_detail.hieuqua,0)) as hieuqua,
                            sum(coalesce(view_detail.dukienthuong,0)) as hamtrunggian
                    from
                        (select extract('year' from view_projectclosed.last_date)::character varying as year_lastdate,
                                extract('month' from view_projectclosed.last_date) as month_lastdate,
                                view_projectclosed.last_date,
                                view_projectclosed.pp_id_report,
                                view_projectclosed.pp_name_report,
                                view_projectclosed.pp_label_report,
                                view_projectclosed.x_project_type,
                                view_projectclosed.active,
                                view_projectclosed.leader,
                                view_projectclosed.departmentblock_name,
                                view_rate.chisohailong,
                                customer_rate.rate,
                                coalesce(view_budget.amount_budget,0) as amount_budget,
                                coalesce(view_expenses_checkin.actual_labor,0) as chekin_labor,
                                (coalesce(view_expenses_payment.chi_cohoadon,0) + coalesce(view_expenses_payment.chi_khonghoadon,0) + coalesce(view_expenses_payment.chixuly_IV,0) + coalesce(view_expenses_payment.chi_IV,0) - coalesce(view_expenses_payment.thu_IV,0) - coalesce(view_expenses_payment.thu_RRM,0))as payment_labor,
                                (case when ((coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - coalesce(view_expenses_payment.chi_cohoadon,0) - coalesce(view_expenses_payment.chi_IV,0)) * 20/100) > 0 then ((coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - coalesce(view_expenses_payment.chi_cohoadon,0) - coalesce(view_expenses_payment.chi_IV,0)) * 20/100) else 0 end) as chiphithue_tndn,
                                (coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - (coalesce(view_expenses_payment.chi_cohoadon,0) + coalesce(view_expenses_payment.chi_khonghoadon,0) + coalesce(view_expenses_payment.chixuly_IV,0) + coalesce(view_expenses_payment.chi_IV,0) - coalesce(view_expenses_payment.thu_IV,0) - coalesce(view_expenses_payment.thu_RRM,0)) - (case when ((coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - coalesce(view_expenses_payment.chi_cohoadon,0) - coalesce(view_expenses_payment.chi_IV,0)) * 20/100) > 0 then ((coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - coalesce(view_expenses_payment.chi_cohoadon,0) - coalesce(view_expenses_payment.chi_IV,0)) * 20/100) else 0 end)) as hieuqua,
                                (case when (coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - (coalesce(view_expenses_payment.chi_cohoadon,0) + coalesce(view_expenses_payment.chi_khonghoadon,0) + coalesce(view_expenses_payment.chixuly_IV,0) + coalesce(view_expenses_payment.chi_IV,0) - coalesce(view_expenses_payment.thu_IV,0) - coalesce(view_expenses_payment.thu_RRM,0)) - (case when ((coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - coalesce(view_expenses_payment.chi_cohoadon,0) - coalesce(view_expenses_payment.chi_IV,0)) * 20/100) > 0 then ((coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - coalesce(view_expenses_payment.chi_cohoadon,0) - coalesce(view_expenses_payment.chi_IV,0)) * 20/100) else 0 end)) > 0 then ((coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - (coalesce(view_expenses_payment.chi_cohoadon,0) + coalesce(view_expenses_payment.chi_khonghoadon,0) + coalesce(view_expenses_payment.chixuly_IV,0) + coalesce(view_expenses_payment.chi_IV,0) - coalesce(view_expenses_payment.thu_IV,0) - coalesce(view_expenses_payment.thu_RRM,0)) - (case when ((coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - coalesce(view_expenses_payment.chi_cohoadon,0) - coalesce(view_expenses_payment.chi_IV,0)) * 20/100) > 0 then ((coalesce(view_budget.amount_budget,0) - coalesce(view_expenses_checkin.actual_labor,0) - coalesce(view_expenses_payment.chi_cohoadon,0) - coalesce(view_expenses_payment.chi_IV,0)) * 20/100) else 0 end)) * customer_rate.rate/100) else 0 end) as dukienthuong
                        from
                            (--Detail Project Closed
                            select	view_base.pp_id_report,
                                    view_base.pp_name_report,
                                    view_base.pp_label_report,
                                    view_base.x_project_type,
                                    view_base.leader,
                                    view_base.departmentblock_name,
                                    view_base.active,
                                    view_base.last_date,
                                    sum(view_base.count_pp_report) as count_pp_report
                            from
                                (select view_mergeproject.pp_id,
                                        view_mergeproject.pp_name,
                                        view_mergeproject.x_merge_project_id,
                                        view_mergeproject.project_detail as pp_id_report,
                                        project_project.name as pp_name_report,
                                        project_project.label_tasks as pp_label_report,
                                        project_project.x_project_type,
                                        hr_employee.name as leader,
                                        hr_department_block.name as departmentblock_name,
                                        project_project.active,
                                        view_ngayketthucthucte.last_date,
                                        1 as count_pp_report
                                from
                                    (--Dự án gộp
                                    select  project_project.x_order_id,
                                            project_project.id as pp_id,
                                            project_project.name as pp_name,
                                            project_project.x_project_type,
                                            project_project.x_order_line_id,
                                            project_project.is_merge_project,
                                            project_project.x_merge_project_id,
                                            view_subproject.merge_project_id,
                                            (case when view_subproject.merge_project_id is not null then view_subproject.merge_project_id else project_project.id end) as project_detail
                                    from project_project
                                    left join 
                                        (
                                        select sub_project_project.* 
                                        from sub_project_project
                                        where sub_project_project.merge_project_id is not null
                                        ) as view_subproject
                                    on project_project.id = view_subproject.sub_project_id 
                                    where project_project.is_merge_project is not true
                                    ) as view_mergeproject
                                left join project_project on view_mergeproject.project_detail = project_project.id
                                left join res_users on project_project.user_id = res_users.id
                                left join hr_employee on res_users.id = hr_employee.user_id 
                                left join hr_department on hr_employee.department_id = hr_department.id
                                left join hr_department_block on hr_department.x_block_id = hr_department_block.id 
                                left join
                                    (--Ngày kết thúc thực tế theo pp
                                    select 	view_lastdate.pp_id,
                                            max(view_lastdate.last_date::date) as last_date
                                    from
                                        (--Ngày nhận báo cáo
                                        select 	view_closeproject.pp_id,
                                                max(case when view_closeproject.x_report_date is not null then view_closeproject.x_report_date else '1900-01-01' end) as last_date
                                        from 
                                            (select project_project.x_order_id,
                                                    project_project.id as pp_id,
                                                    project_project.active,
                                                    project_project.state,
                                                    sale_order.partner_id,
                                                    project_project.x_report_date  
                                            from project_project 
                                            left join sale_order on project_project.x_order_id = sale_order.id
                                            ) as view_closeproject
                                        where view_closeproject.active = false and view_closeproject.state not in ('canceled')
                                        group by view_closeproject.pp_id
                                        
                                        union all
                                        
                                        --Ngày chấm công muộn nhất
                                        select 	project_project.id as pp_id,
                                                max(case when hr_work_entry.x_date is not null then hr_work_entry.x_date else '1900-01-01' end) as last_date
                                        from hr_work_entry_line 
                                        left join hr_work_entry on hr_work_entry_line.entry_id = hr_work_entry.id
                                        left join project_project on hr_work_entry_line.project_id = project_project.id
                                        where project_project.active = false and project_project.state not in ('canceled')
                                        group by project_project.id
                                        
                                        union all
                                        
                                        --Ngày chi tiền cuối cùng
                                        select  view_chitiet.project,
                                                max(view_chitiet.payment_date) as payment_date
                                        from
                                            (select account_payment.id as payment_id,
                                                    account_payment.partner_id,
                                                    account_payment.payment_type,
                                                    account_payment.x_code_money,
                                                    account_payment.amount,
                                                    account_payment.x_origin_advance_id,
                                                    account_advance.license_type as license_advance,
                                                    account_advance.po_id,
                                                    pol_1.x_project_id,
                                                    pol_1.price_subtotal,
                                                    pol_1.x_cost_type_id as x_cost_type_id_tamung,
                                                    purchase_order.amount_untaxed,
                                                    account_advance.amount_total as tam_ung,
                                                    (case when purchase_order.amount_untaxed > 0 then (account_advance.amount_total/purchase_order.amount_untaxed)*pol_1.price_subtotal else 0 end) as tam_ung_pol,
                                                    account_payment.x_origin_repay_id,
                                                    account_advance_repay.license_type as license_repay,
                                                    account_repay_line.project_id,
                                                    account_repay_line.amount_untaxed as hoan_ung,
                                                    account_repay_line.cost_type_id as cost_type_id_hoanung,
                                                    account_payment.x_origin_move_id,
                                                    po_2.id as po_id_congno,
                                                    pol_2.x_project_id,
                                                    pol_2.x_cost_type_id as x_cost_type_id_congno,
                                                    acm_1.x_license_type as license_move,
                                                    acm_1.amount_total,
                                                    account_move_line.price_subtotal,
                                                    (case when acm_1.amount_total > 0 then (account_payment.amount/acm_1.amount_total)*account_move_line.price_subtotal else 0 end) as thanh_toan_cong_no,
                                                    (case when account_payment.x_pay_cost is true then payment_line.project_id else project_detail.project_id end) as project_id_tttt,
                                                    (case when account_payment.x_pay_cost is true then payment_line.cost_type_id else project_detail.cost_type_id end) as cost_type_id_tttt,
                                                    (case when account_payment.x_pay_cost is true then payment_line.amount else project_detail.amount_total end) as amount_total_tttt,
                                                    acm_2.date as payment_date,
                                                    (case when account_payment.x_origin_advance_id is not null then pol_1.x_project_id
                                                          when account_payment.x_origin_repay_id is not null then account_repay_line.project_id
                                                          when account_payment.x_origin_move_id is not null then pol_2.x_project_id
                                                          else (case when account_payment.x_pay_cost is true then payment_line.project_id else project_detail.project_id end) end
                                                    ) as project,
                                                    (case when account_payment.x_origin_advance_id is not null then pol_1.x_cost_type_id
                                                          when account_payment.x_origin_repay_id is not null then account_repay_line.cost_type_id
                                                          when account_payment.x_origin_move_id is not null then pol_2.x_cost_type_id
                                                          else (case when account_payment.x_pay_cost is true then payment_line.cost_type_id else project_detail.cost_type_id end) end
                                                    ) as phanloaichiphi
                                            from account_payment
                                            left join account_advance on account_payment.x_origin_advance_id = account_advance.id 
                                            left join purchase_order on account_advance.po_id = purchase_order.id
                                            left join purchase_order_line as pol_1 on account_advance.po_id = pol_1.order_id 
                                            left join account_advance_repay on account_payment.x_origin_repay_id = account_advance_repay.id 
                                            left join account_repay_line on account_advance_repay.id = account_repay_line.account_repay_id 
                                            left join account_move as acm_1 on account_payment.x_origin_move_id = acm_1.id
                                            left join account_move_line on acm_1.id = account_move_line.move_id and account_move_line.price_subtotal > 0
                                            left join purchase_order_line as pol_2 on account_move_line.purchase_line_id = pol_2.id
                                            left join purchase_order as po_2 on pol_2.order_id = po_2.id
                                            left join payment_line on account_payment.id = payment_line.payment_id and (account_payment.x_origin_advance_id is null and account_payment.x_origin_repay_id is null and account_payment.x_origin_move_id is null)
                                            left join project_detail on account_payment.id = project_detail.payment_id and (account_payment.x_origin_advance_id is null and account_payment.x_origin_repay_id is null and account_payment.x_origin_move_id is null)
                                            left join account_move as acm_2 on account_payment.move_id = acm_2.id
                                            where account_payment.payment_type = 'outbound'
                                                  and account_payment.partner_id <> 1
                                                  and account_payment.destination_account_id = 77
                                                  and account_payment.x_code_money <> 39
                                            ) as view_chitiet
                                        group by view_chitiet.project
                                        ) as view_lastdate
                                    group by view_lastdate.pp_id
                                    ) as view_ngayketthucthucte
                                on view_mergeproject.project_detail = view_ngayketthucthucte.pp_id
                                where project_project.active is false and view_ngayketthucthucte.last_date is not null
                                ) as view_base
                            group by view_base.pp_id_report, view_base.pp_name_report, view_base.pp_label_report, view_base.x_project_type, view_base.leader, view_base.departmentblock_name, view_base.active, view_base.last_date
                            ) as view_projectclosed
                        left join
                            (--DU TOAN
                            select  view_budget_detail.pp_id_report,
                                    sum(coalesce(view_budget_detail.amount_budget,0)) as amount_budget
                            from 
                                (--Detail: Labor-Cost
                                select  view_mergeproject.pp_id,
                                        view_mergeproject.pp_name,
                                        view_mergeproject.x_merge_project_id,
                                        view_mergeproject.project_detail as pp_id_report,
                                        project_project.name as pp_name_report,
                                        project_project.label_tasks as pp_label_report,
                                        (case when project_project.x_project_type = 'maintainance' then 'Maintenance'
                                             when project_project.x_project_type = 'service' then 'Services'
                                             when project_project.x_project_type = 'opration' then 'Facility Management'
                                        end) as x_project_type,
                                        project_project.active,
                                        view_ngayketthucthucte.last_date,
                                        hr_employee.name as leader,
                                        view_detail.x_resource_type,
                                        view_detail.amount as amount_budget
                                from
                                    (--Dự án gộp
                                    select  project_project.x_order_id,
                                            project_project.id as pp_id,
                                            project_project.name as pp_name,
                                            project_project.x_project_type,
                                            project_project.x_order_line_id,
                                            project_project.is_merge_project,
                                            project_project.x_merge_project_id,
                                            view_subproject.merge_project_id,
                                            (case when view_subproject.merge_project_id is not null then view_subproject.merge_project_id else project_project.id end) as project_detail
                                    from project_project
                                    left join 
                                        (
                                        select sub_project_project.* 
                                        from sub_project_project
                                        where sub_project_project.merge_project_id is not null
                                        ) as view_subproject
                                    on project_project.id = view_subproject.sub_project_id 
                                    where project_project.is_merge_project is not true
                                    ) as view_mergeproject
                                left join project_project on view_mergeproject.project_detail = project_project.id
                                left join res_users on project_project.user_id = res_users.id
                                left join hr_employee on res_users.id = hr_employee.user_id 
                                left join
                                    (--Ngày kết thúc thực tế theo pp
                                    select 	view_lastdate.pp_id,
                                            max(view_lastdate.last_date::date) as last_date
                                    from
                                        (--Ngày nhận báo cáo
                                        select 	view_closeproject.pp_id,
                                                max(case when view_closeproject.x_report_date is not null then view_closeproject.x_report_date else '1900-01-01' end) as last_date
                                        from 
                                            (select project_project.x_order_id,
                                                    project_project.id as pp_id,
                                                    project_project.active,
                                                    project_project.state,
                                                    sale_order.partner_id,
                                                    project_project.x_report_date  
                                            from project_project 
                                            left join sale_order on project_project.x_order_id = sale_order.id
                                            ) as view_closeproject
                                        where view_closeproject.active = false and view_closeproject.state not in ('canceled')
                                        group by view_closeproject.pp_id
                                        
                                        union all
                                        
                                        --Ngày chấm công muộn nhất
                                        select 	project_project.id as pp_id,
                                                max(case when hr_work_entry.x_date is not null then hr_work_entry.x_date else '1900-01-01' end) as last_date
                                        from hr_work_entry_line 
                                        left join hr_work_entry on hr_work_entry_line.entry_id = hr_work_entry.id
                                        left join project_project on hr_work_entry_line.project_id = project_project.id
                                        where project_project.active = false and project_project.state not in ('canceled')
                                        group by project_project.id
                                        
                                        union all
                                        
                                        --Ngày chi tiền cuối cùng
                                        select  view_chitiet.project,
                                                max(view_chitiet.payment_date) as payment_date
                                        from
                                            (select account_payment.id as payment_id,
                                                    account_payment.partner_id,
                                                    account_payment.payment_type,
                                                    account_payment.x_code_money,
                                                    account_payment.amount,
                                                    account_payment.x_origin_advance_id,
                                                    account_advance.license_type as license_advance,
                                                    account_advance.po_id,
                                                    pol_1.x_project_id,
                                                    pol_1.price_subtotal,
                                                    pol_1.x_cost_type_id as x_cost_type_id_tamung,
                                                    purchase_order.amount_untaxed,
                                                    account_advance.amount_total as tam_ung,
                                                    (case when purchase_order.amount_untaxed > 0 then (account_advance.amount_total/purchase_order.amount_untaxed)*pol_1.price_subtotal else 0 end) as tam_ung_pol,
                                                    account_payment.x_origin_repay_id,
                                                    account_advance_repay.license_type as license_repay,
                                                    account_repay_line.project_id,
                                                    account_repay_line.amount_untaxed as hoan_ung,
                                                    account_repay_line.cost_type_id as cost_type_id_hoanung,
                                                    account_payment.x_origin_move_id,
                                                    po_2.id as po_id_congno,
                                                    pol_2.x_project_id,
                                                    pol_2.x_cost_type_id as x_cost_type_id_congno,
                                                    acm_1.x_license_type as license_move,
                                                    acm_1.amount_total,
                                                    account_move_line.price_subtotal,
                                                    (case when acm_1.amount_total > 0 then (account_payment.amount/acm_1.amount_total)*account_move_line.price_subtotal else 0 end) as thanh_toan_cong_no,
                                                    (case when account_payment.x_pay_cost is true then payment_line.project_id else project_detail.project_id end) as project_id_tttt,
                                                    (case when account_payment.x_pay_cost is true then payment_line.cost_type_id else project_detail.cost_type_id end) as cost_type_id_tttt,
                                                    (case when account_payment.x_pay_cost is true then payment_line.amount else project_detail.amount_total end) as amount_total_tttt,
                                                    acm_2.date as payment_date,
                                                    (case when account_payment.x_origin_advance_id is not null then pol_1.x_project_id
                                                          when account_payment.x_origin_repay_id is not null then account_repay_line.project_id
                                                          when account_payment.x_origin_move_id is not null then pol_2.x_project_id
                                                          else (case when account_payment.x_pay_cost is true then payment_line.project_id else project_detail.project_id end) end
                                                    ) as project,
                                                    (case when account_payment.x_origin_advance_id is not null then pol_1.x_cost_type_id
                                                          when account_payment.x_origin_repay_id is not null then account_repay_line.cost_type_id
                                                          when account_payment.x_origin_move_id is not null then pol_2.x_cost_type_id
                                                          else (case when account_payment.x_pay_cost is true then payment_line.cost_type_id else project_detail.cost_type_id end) end
                                                    ) as phanloaichiphi
                                            from account_payment
                                            left join account_advance on account_payment.x_origin_advance_id = account_advance.id 
                                            left join purchase_order on account_advance.po_id = purchase_order.id
                                            left join purchase_order_line as pol_1 on account_advance.po_id = pol_1.order_id 
                                            left join account_advance_repay on account_payment.x_origin_repay_id = account_advance_repay.id 
                                            left join account_repay_line on account_advance_repay.id = account_repay_line.account_repay_id 
                                            left join account_move as acm_1 on account_payment.x_origin_move_id = acm_1.id
                                            left join account_move_line on acm_1.id = account_move_line.move_id and account_move_line.price_subtotal > 0
                                            left join purchase_order_line as pol_2 on account_move_line.purchase_line_id = pol_2.id
                                            left join purchase_order as po_2 on pol_2.order_id = po_2.id
                                            left join payment_line on account_payment.id = payment_line.payment_id and (account_payment.x_origin_advance_id is null and account_payment.x_origin_repay_id is null and account_payment.x_origin_move_id is null)
                                            left join project_detail on account_payment.id = project_detail.payment_id and (account_payment.x_origin_advance_id is null and account_payment.x_origin_repay_id is null and account_payment.x_origin_move_id is null)
                                            left join account_move as acm_2 on account_payment.move_id = acm_2.id
                                            where account_payment.payment_type = 'outbound'
                                                  and account_payment.partner_id <> 1
                                                  and account_payment.destination_account_id = 77
                                                  and account_payment.x_code_money <> 39
                                            ) as view_chitiet
                                        group by view_chitiet.project
                                        ) as view_lastdate
                                    group by view_lastdate.pp_id
                                    ) as view_ngayketthucthucte
                                on view_mergeproject.project_detail = view_ngayketthucthucte.pp_id
                                left join
                                    (--Du toan: detail
                                    select  project_project.id as project_id,
                                            project_project.x_merge_project_id,
                                            project_estimate.product_id,
                                            (case 	when product_template.x_resource_type = 'seniorengsub' then 'Kỹ sư/ Giám sát cao cấp'
                                                    when product_template.x_resource_type = 'engsub' then 'Kỹ sư/ Giám sát'
                                                    when product_template.x_resource_type = 'teamleader' then 'Trưởng nhóm'
                                                    when product_template.x_resource_type = 'technician' then 'Kỹ thuật viên'
                                                    when product_template.x_resource_type = 'internship' then 'Thực tập sinh'
                                                    else 'others' end
                                            ) as x_resource_type,
                                            product_template.name as product_name,
                                            project_estimate.quantity,
                                            project_estimate.price_unit,
                                            project_estimate.amount 
                                    from project_project 
                                    left join project_estimate on project_project.id = project_estimate.project_id  
                                    left join product_product on project_estimate.product_id = product_product.id 
                                    left join product_template on product_product.product_tmpl_id = product_template.id
                                    ) as view_detail
                                on view_mergeproject.pp_id = view_detail.project_id
                                ) as view_budget_detail
                            group by view_budget_detail.pp_id_report
                            ) as view_budget
                        on view_projectclosed.pp_id_report = view_budget.pp_id_report 
                        left join
                            (--THUC TE: Chấm công
                            select  view_detail.pp_id_report,
                                    view_detail.pp_name_report,
                                    sum(coalesce(view_detail.actual_labor,0)) as actual_labor
                            from 
                                (--Detail: Actual Labor-Cost
                                select  view_checkin.year_chamcong,
                                        view_checkin.month_chamcong,
                                        view_checkin.pp_id,
                                        view_checkin.pp_name,
                                        view_checkin.is_merge_project,
                                        view_checkin.x_merge_project_id,
                                        view_checkin.pp_id_report,
                                        view_checkin.pp_name_report,
                                        view_checkin.pp_label_report,
                                        view_checkin.employee_id,
                                        view_checkin.name_employee,
                                        (case 	when hr_employee.x_resource_type = 'seniorengsub' then 'Kỹ sư/ Giám sát cao cấp'
                                                when hr_employee.x_resource_type = 'engsub' then 'Kỹ sư/ Giám sát'
                                                when hr_employee.x_resource_type = 'teamleader' then 'Trưởng nhóm'
                                                when hr_employee.x_resource_type = 'technician' then 'Kỹ thuật viên'
                                                when hr_employee.x_resource_type = 'internship' then 'Thực tập sinh'
                                                else 'others' end
                                        ) as x_resource_type,
                                        view_checkin.hour_converted,
                                        view_dongianhanvien.don_gia,
                                        (view_checkin.hour_converted * view_dongianhanvien.don_gia) as actual_labor
                                from
                                    (--Detail: Cham cong theo du an
                                    select view_checkin.year_chamcong,
                                            view_checkin.month_chamcong,
                                            view_mergeproject.pp_id,
                                            view_mergeproject.pp_name,
                                            view_mergeproject.is_merge_project,
                                            view_mergeproject.x_merge_project_id,
                                            view_mergeproject.project_detail as pp_id_report,
                                            project_project.name as pp_name_report,
                                            project_project.label_tasks as pp_label_report,
                                            view_checkin.employee_id,
                                            view_checkin.name_employee,
                                            view_checkin.hour_converted
                                    from
                                        (--Dự án gộp
                                        select  project_project.x_order_id,
                                                project_project.id as pp_id,
                                                project_project.name as pp_name,
                                                project_project.x_project_type,
                                                project_project.active,
                                                project_project.state,
                                                project_project.x_order_line_id,
                                                project_project.is_merge_project,
                                                project_project.x_merge_project_id,
                                                view_subproject.merge_project_id,
                                                (case when view_subproject.merge_project_id is not null then view_subproject.merge_project_id else project_project.id end) as project_detail,
                                                project_project.x_date_plan_start,
                                                project_project.x_rate
                                        from project_project
                                        left join 
                                            (
                                            select sub_project_project.* 
                                            from sub_project_project
                                            where sub_project_project.merge_project_id is not null
                                            ) as view_subproject
                                        on project_project.id = view_subproject.sub_project_id 
                                        ) as view_mergeproject
                                    left join project_project on view_mergeproject.project_detail = project_project.id
                                    left join
                                        (--Gio cong quy doi theo du an chi tiet
                                        select  view_base.year_chamcong,
                                                view_base.month_chamcong,
                                                view_base.project_id,
                                                view_base.employee_id,
                                                view_base.name_employee,
                                                sum(view_base.hour_converted) as hour_converted
                                        from
                                            (--So gio quy doi cham cong
                                            select	view_detail.year_chamcong,
                                                    view_detail.month_chamcong,
                                                    view_detail.project_id,
                                                    view_detail.employee_id,
                                                    view_detail.name_employee,
                                                    sum(view_detail.hour_converted) as hour_converted
                                            from
                                                (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                                        extract ('month' from hr_work_entry.x_date) as month_chamcong,
                                                        hr_work_entry.x_date,
                                                        hr_work_entry_line.entry_id,
                                                        hr_work_entry_line.id as wrl_id,
                                                        hr_work_entry_line.project_id,
                                                        project_project.name as project_name,
                                                        (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                                        hr_work_entry.employee_id,
                                                        hr_employee.name as name_employee,
                                                        hr_employee.x_resource_type,
                                                        hr_work_entry_line.hour,
                                                        (case when project_project.x_project_type in ('service', 'maintainance', 'operation') then hr_work_entry_line.hour else 0 end) as hour_project,
                                                        hr_work_entry_line.hour_converted 
                                                from hr_work_entry_line
                                                left join hr_work_entry on hr_work_entry_line.entry_id = hr_work_entry.id
                                                left join project_project on hr_work_entry_line.project_id = project_project.id
                                                left join hr_employee on hr_work_entry.employee_id = hr_employee.id
                                                where extract('year' from hr_work_entry_line.create_date) > 2021
                                                ) as view_detail
                                            group by view_detail.year_chamcong, view_detail.month_chamcong, view_detail.project_id, view_detail.employee_id, view_detail.name_employee
                                            
                                            union all
                                            
                                            --So gio tro cap di lai
                                            select	view_detail.year_chamcong,
                                                    view_detail.month_chamcong,
                                                    view_detail.project_id,
                                                    view_detail.employee_id,
                                                    view_detail.name_employee,
                                                    sum(view_detail.hour) as hour_converted
                                            from
                                                (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                                        extract ('month' from hr_work_entry.x_date) as month_chamcong,
                                                        hr_work_entry.x_date,
                                                        hr_work_entry_allowance.entry_id,
                                                        hr_work_entry_allowance.id as allowance_id,
                                                        hr_work_entry_allowance.project_id,
                                                        project_project.name as project_name,
                                                        (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                                                hr_work_entry.employee_id,
                                                                hr_employee.name as name_employee,
                                                                hr_employee.x_resource_type,
                                                                hr_work_entry_allowance.hour
                                                from hr_work_entry_allowance
                                                left join hr_work_entry on hr_work_entry_allowance.entry_id = hr_work_entry.id
                                                left join project_project on hr_work_entry_allowance.project_id = project_project.id
                                                left join hr_employee on hr_work_entry.employee_id = hr_employee.id
                                                ) as view_detail
                                            group by view_detail.year_chamcong, view_detail.month_chamcong, view_detail.project_id, view_detail.employee_id, view_detail.name_employee
                                            ) as view_base
                                        group by view_base.year_chamcong, view_base.month_chamcong, view_base.project_id, view_base.employee_id, view_base.name_employee
                                        ) as view_checkin
                                    on view_mergeproject.pp_id = view_checkin.project_id
                                    ) as view_checkin
                                left join
                                    (--Don gia nhan vien
                                    select  view_wage.year_datefrom,
                                            view_wage.month_datefrom,
                                            view_wage.employee_id,
                                            view_wage.payslip_id,
                                            view_wage.payslip_name,
                                            view_wage.struct_id,
                                            view_wage.struct_name,
                                            view_wage.thu_nhap_theo_gio_cong_thuc_te,
                                            view_wage.thuong_hoac_cac_khoan_thu_nhap_khac,
                                            view_wage.ho_tro_xang_xe,
                                            view_wage.bu_tru_luong_thang,
                                            view_wage.ho_tro_tien_luong_bu_du_cong,
                                            view_wage.bao_hiem_xa_hoi,
                                            view_wage.bao_hiem_y_te,
                                            view_wage.bao_hiem_that_nghiep,
                                            view_wage.tam_ung,
                                            view_wage.cong_tac_phi,
                                            view_wage.hoan_thue_TNCN_nam_truoc,
                                            view_wage.thue_TTCN_phai_nop,
                                            view_wage.ho_tro_dien_thoai,
                                            view_wage.dong_phuc_nu_van_phong,
                                            view_wage.dong_phuc_ky_thuat,
                                            view_wage.dong_phuc_van_phong_senior,
                                            view_wage.kham_suc_khoe_senior,
                                            view_wage.kham_suc_khoe_nhan_vien,
                                            view_wage.kham_suc_khoe_bo_sung_nu,
                                            view_wage.thuong_ngay_le,
                                            view_wage.du_lich_tiec_cuoi_nam,
                                            view_wage.BHXH_DN,
                                            view_wage.BHYT_DN,
                                            view_wage.BHTN_DN,
                                            view_wage.cong_doan,
                                            view_wage.wage13permonth,
                                            view_wage.luong_theo_gio,
                                            (view_wage.thu_nhap_theo_gio_cong_thuc_te - view_wage.bu_tru_luong_thang + view_wage.ho_tro_xang_xe + view_wage.cong_tac_phi + view_wage.ho_tro_tien_luong_bu_du_cong + view_wage.ho_tro_dien_thoai + view_wage.wage13permonth + view_wage.cong_doan + view_wage.du_lich_tiec_cuoi_nam + view_wage.thuong_ngay_le + view_wage.dong_phuc_nu_van_phong + view_wage.dong_phuc_ky_thuat + view_wage.dong_phuc_van_phong_senior + view_wage.kham_suc_khoe_senior + view_wage.kham_suc_khoe_nhan_vien + view_wage.kham_suc_khoe_bo_sung_nu + view_wage.BHXH_DN + view_wage.BHYT_DN + view_wage.BHTN_DN) as total,
                                            view_wage.gio_cong_quy_doi,
                                            view_wage.gio_bu_cong,
                                            view_wage.gio_cong_ly_thuyet,
                                            view_wage.he_so_phan_bo,
                                            coalesce(view_global_off.global_off,0) as global_off,
                                            coalesce(view_leave.leave_days,0) as leave_days,	
                                            (coalesce(view_global_off.global_off,0) + coalesce(view_leave.leave_days,0)) * 8 as hours_off,
                                            (case when view_wage.struct_id <> 7 then (view_wage.gio_cong_quy_doi - (coalesce(view_global_off.global_off,0) + coalesce(view_leave.leave_days,0))*8) else view_wage.gio_cong_quy_doi end) as so_gio_cong_tinh_don_gia,
                                            (case 	when round(case when view_wage.struct_id <> 7 then (view_wage.gio_cong_quy_doi - (coalesce(view_global_off.global_off,0) + coalesce(view_leave.leave_days,0))*8) else view_wage.gio_cong_quy_doi end) > 0 
                                                    then round(((view_wage.thu_nhap_theo_gio_cong_thuc_te - view_wage.bu_tru_luong_thang + view_wage.ho_tro_xang_xe + view_wage.cong_tac_phi + view_wage.ho_tro_tien_luong_bu_du_cong + view_wage.ho_tro_dien_thoai + view_wage.wage13permonth + view_wage.cong_doan + view_wage.du_lich_tiec_cuoi_nam + view_wage.thuong_ngay_le + view_wage.dong_phuc_nu_van_phong + view_wage.dong_phuc_ky_thuat + view_wage.dong_phuc_van_phong_senior + view_wage.kham_suc_khoe_senior + view_wage.kham_suc_khoe_nhan_vien + view_wage.kham_suc_khoe_bo_sung_nu + view_wage.BHXH_DN + view_wage.BHYT_DN + view_wage.BHTN_DN)/(case when view_wage.struct_id <> 7 then (view_wage.gio_cong_quy_doi - (coalesce(view_global_off.global_off,0) + coalesce(view_leave.leave_days,0))*8) else view_wage.gio_cong_quy_doi end))::numeric,2) 
                                                    else 0 end) as don_gia
                                    from
                                        (select view_payslip.year_datefrom,
                                                view_payslip.month_datefrom,
                                                view_payslip.employee_id,
                                                view_payslip.contract_id,
                                                view_payslip.payslip_id,
                                                view_payslip.payslip_name,
                                                view_payslip.struct_id,
                                                view_payslip.struct_name,
                                                view_payslip.thu_nhap_theo_gio_cong_thuc_te,
                                                view_payslip.thuong_hoac_cac_khoan_thu_nhap_khac,
                                                view_payslip.ho_tro_xang_xe,
                                                view_payslip.bu_tru_luong_thang,
                                                view_payslip.ho_tro_tien_luong_bu_du_cong,
                                                view_payslip.bao_hiem_xa_hoi,
                                                view_payslip.bao_hiem_y_te,
                                                view_payslip.bao_hiem_that_nghiep,
                                                view_payslip.tam_ung,
                                                view_payslip.cong_tac_phi,
                                                view_payslip.hoan_thue_TNCN_nam_truoc,
                                                view_payslip.thue_TTCN_phai_nop,
                                                view_payslip.ho_tro_dien_thoai,
                                                (coalesce(view_otherexpenses.dong_phuc_nu_van_phong,0)) as dong_phuc_nu_van_phong,
                                                (coalesce(view_otherexpenses.dong_phuc_ky_thuat,0)) as dong_phuc_ky_thuat,
                                                (coalesce(view_otherexpenses.dong_phuc_van_phong_senior,0)) as dong_phuc_van_phong_senior,
                                                (coalesce(view_otherexpenses.kham_suc_khoe_senior,0)) as kham_suc_khoe_senior,
                                                (coalesce(view_otherexpenses.kham_suc_khoe_nhan_vien,0)) as kham_suc_khoe_nhan_vien,
                                                (coalesce(view_otherexpenses.kham_suc_khoe_bo_sung_nu,0)) as kham_suc_khoe_bo_sung_nu,
                                                (coalesce(view_otherexpenses.thuong_ngay_le,0)) as thuong_ngay_le,
                                                (coalesce(view_otherexpenses.du_lich_tiec_cuoi_nam,0)) as du_lich_tiec_cuoi_nam,
                                                (case when (view_payslip.struct_id = 6 and (view_giocongquydoi.gio_cong_quy_doi + view_giobucong.gio_bu_cong)/8 >= 14) then view_wagecontract.BHXH_DN else 0 end) as BHXH_DN,
                                                (case when (view_payslip.struct_id = 6 and (view_giocongquydoi.gio_cong_quy_doi + view_giobucong.gio_bu_cong)/8 >= 14) then view_wagecontract.BHYT_DN else 0 end) as BHYT_DN,
                                                (case when (view_payslip.struct_id = 6 and (view_giocongquydoi.gio_cong_quy_doi + view_giobucong.gio_bu_cong)/8 >= 14) then view_wagecontract.BHTN_DN else 0 end) as BHTN_DN,
                                                (case when (view_payslip.struct_id = 6 and (view_giocongquydoi.gio_cong_quy_doi + view_giobucong.gio_bu_cong)/8 >= 14) then view_wagecontract.cong_doan else 0 end) as cong_doan,
                                                ((case 	when (view_giocongquydoi.gio_cong_quy_doi + view_giobucong.gio_bu_cong)/view_gioconglythuyet.gio_cong_ly_thuyet >= 1 then 1 else (view_giocongquydoi.gio_cong_quy_doi + view_giobucong.gio_bu_cong)/view_gioconglythuyet.gio_cong_ly_thuyet end) * (case when view_payslip.struct_id <> 7 then view_wagecontract.wage13permonth else view_wagecontract.wage13permonth_hour*view_gioconglythuyet.gio_cong_ly_thuyet end)) as wage13permonth,
                                                view_wagecontract.wage13permonth_hour*12 as luong_theo_gio,
                                                view_giocongquydoi.gio_cong_quy_doi,
                                                view_giobucong.gio_bu_cong,
                                                view_gioconglythuyet.gio_cong_ly_thuyet,
                                                view_hoursperday.hours_per_day,
                                                (case when (view_giocongquydoi.gio_cong_quy_doi + view_giobucong.gio_bu_cong)/view_gioconglythuyet.gio_cong_ly_thuyet >= 1 then 1 else (view_giocongquydoi.gio_cong_quy_doi + view_giobucong.gio_bu_cong)/view_gioconglythuyet.gio_cong_ly_thuyet end) as he_so_phan_bo
                                        from 
                                            (--Payslip
                                            select	view_detail.year_datefrom,
                                                    view_detail.month_datefrom,
                                                    view_detail.payslip_id,
                                                    view_detail.payslip_name,
                                                    view_detail.employee_id,
                                                    view_detail.struct_id,
                                                    view_detail.struct_name,
                                                    view_detail.contract_id,
                                                    sum(coalesce(view_detail.thu_nhap_theo_gio_cong_thuc_te,0)) as thu_nhap_theo_gio_cong_thuc_te,
                                                    sum(coalesce(view_detail.thuong_hoac_cac_khoan_thu_nhap_khac,0)) as thuong_hoac_cac_khoan_thu_nhap_khac,
                                                    sum(coalesce(view_detail.ho_tro_xang_xe,0)) as ho_tro_xang_xe,
                                                    sum(coalesce(view_detail.bu_tru_luong_thang,0)) as bu_tru_luong_thang,
                                                    sum(coalesce(view_detail.ho_tro_tien_luong_bu_du_cong,0)) as ho_tro_tien_luong_bu_du_cong,
                                                    sum(coalesce(view_detail.bao_hiem_xa_hoi,0)) as bao_hiem_xa_hoi,
                                                    sum(coalesce(view_detail.bao_hiem_y_te,0)) as bao_hiem_y_te,
                                                    sum(coalesce(view_detail.bao_hiem_that_nghiep,0)) as bao_hiem_that_nghiep,
                                                    sum(coalesce(view_detail.tam_ung,0)) as tam_ung,
                                                    sum(coalesce(view_detail.cong_tac_phi,0)) as cong_tac_phi,
                                                    sum(coalesce(view_detail.hoan_thue_TNCN_nam_truoc,0)) as hoan_thue_TNCN_nam_truoc,
                                                    sum(coalesce(view_detail.thue_TTCN_phai_nop,0)) as thue_TTCN_phai_nop,
                                                    sum(coalesce(view_detail.ho_tro_dien_thoai,0)) as ho_tro_dien_thoai
                                            from
                                                (select extract ('year' from hr_payslip_line.date_from)::character varying as year_datefrom,
                                                        extract ('month' from hr_payslip_line.date_from) as month_datefrom,
                                                        hr_payslip.id as payslip_id,
                                                        hr_payslip.name as payslip_name,
                                                        hr_payslip_line.employee_id,
                                                        hr_payslip.struct_id,
                                                        hr_payroll_structure.name as struct_name,
                                                        hr_payslip.contract_id,
                                                        hr_payslip_line.total,
                                                        (case when hr_payslip_line.code = 'TNTGCTT' then hr_payslip_line.total else 0 end) as thu_nhap_theo_gio_cong_thuc_te,
                                                        (case when hr_payslip_line.code = 'THCKTNK' then hr_payslip_line.total else 0 end) as thuong_hoac_cac_khoan_thu_nhap_khac,
                                                        (case when hr_payslip_line.code = 'HTXX' then hr_payslip_line.total else 0 end) as ho_tro_xang_xe,
                                                        (case when hr_payslip_line.code = 'BTLT' then hr_payslip_line.total else 0 end) as bu_tru_luong_thang,
                                                        (case when hr_payslip_line.code = 'HTTLBDC' then hr_payslip_line.total else 0 end) as ho_tro_tien_luong_bu_du_cong,
                                                        (case when hr_payslip_line.code = 'BHXH' then hr_payslip_line.total else 0 end) as bao_hiem_xa_hoi,
                                                        (case when hr_payslip_line.code = 'BHYT' then hr_payslip_line.total else 0 end) as bao_hiem_y_te,
                                                        (case when hr_payslip_line.code = 'BHTN' then hr_payslip_line.total else 0 end) as bao_hiem_that_nghiep,
                                                        (case when hr_payslip_line.code = 'TU' then hr_payslip_line.total else 0 end) as tam_ung,
                                                        (case when hr_payslip_line.code = 'CTP' then hr_payslip_line.total else 0 end) as cong_tac_phi,
                                                        (case when hr_payslip_line.code = 'HTTNCNNT' then hr_payslip_line.total else 0 end) as hoan_thue_TNCN_nam_truoc,
                                                        (case when hr_payslip_line.code = 'TTNCNPN' then hr_payslip_line.total else 0 end) as thue_TTCN_phai_nop,
                                                        (case when hr_payslip_line.code = 'HTDT' then hr_payslip_line.total else 0 end) as ho_tro_dien_thoai
                                                from hr_payslip_line
                                                left join hr_payslip on hr_payslip_line.slip_id = hr_payslip.id
                                                left join hr_payroll_structure on hr_payslip.struct_id = hr_payroll_structure.id
                                                ) as view_detail
                                            group by view_detail.year_datefrom, view_detail.month_datefrom, view_detail.payslip_id, view_detail.payslip_name, view_detail.employee_id, view_detail.contract_id, view_detail.struct_id, view_detail.struct_name
                                            ) as view_payslip
                                        left join
                                            (--Other expenses
                                            select  view_detail.employee_id,
                                                    view_detail.start_year,
                                                    view_detail.end_year,
                                                    sum(coalesce(view_detail.dong_phuc_nu_van_phong/12,0)) as dong_phuc_nu_van_phong,
                                                    sum(coalesce(view_detail.dong_phuc_ky_thuat/12,0)) as dong_phuc_ky_thuat,
                                                    sum(coalesce(view_detail.dong_phuc_van_phong_senior/12,0)) as dong_phuc_van_phong_senior,
                                                    sum(coalesce(view_detail.kham_suc_khoe_senior/12,0)) as kham_suc_khoe_senior,
                                                    sum(coalesce(view_detail.kham_suc_khoe_nhan_vien/12,0)) as kham_suc_khoe_nhan_vien,
                                                    sum(coalesce(view_detail.kham_suc_khoe_bo_sung_nu/12,0)) as kham_suc_khoe_bo_sung_nu, 
                                                    sum(coalesce(view_detail.thuong_ngay_le/12,0)) as thuong_ngay_le,
                                                    sum(coalesce(view_detail.du_lich_tiec_cuoi_nam/12,0)) as du_lich_tiec_cuoi_nam
                                            from
                                                (select hr_employee.id as employee_id,
                                                        hr_employee.job_id,
                                                        hr_employee.job_title,
                                                        hr_employee.gender,
                                                        view_emp_otherexp.start_year,
                                                        view_emp_otherexp.end_year,
                                                        view_emp_otherexp.price,
                                                        (case when view_emp_otherexp.expenses_id = 1 then view_emp_otherexp.price else 0 end) as dong_phuc_nu_van_phong,
                                                        (case when view_emp_otherexp.expenses_id = 2 then view_emp_otherexp.price else 0 end) as dong_phuc_ky_thuat,
                                                        (case when view_emp_otherexp.expenses_id = 4 then view_emp_otherexp.price else 0 end) as dong_phuc_van_phong_senior,
                                                        (case when view_emp_otherexp.expenses_id = 5 then view_emp_otherexp.price else 0 end) as kham_suc_khoe_senior,
                                                        (case when view_emp_otherexp.expenses_id = 6 then view_emp_otherexp.price else 0 end) as kham_suc_khoe_nhan_vien,
                                                        (case when view_emp_otherexp.expenses_id = 7 then view_emp_otherexp.price else 0 end) as kham_suc_khoe_bo_sung_nu,
                                                        (case when view_emp_otherexp.expenses_id = 8 then view_emp_otherexp.price else 0 end) as thuong_ngay_le,
                                                        (case when view_emp_otherexp.expenses_id = 9 then view_emp_otherexp.price else 0 end) as du_lich_tiec_cuoi_nam
                                                from hr_employee		
                                                left join 
                                                    (select view_otherexp.start_year,
                                                            view_otherexp.end_year,
                                                            view_otherexp.expenses_id,
                                                            view_otherexp.detail,
                                                            view_otherexp.job_id,
                                                            view_otherexp.job_name,
                                                            view_otherexp.gender,
                                                            view_gender.value,
                                                            view_otherexp.price
                                                    from
                                                        (select other_expenses.start_year::character varying,
                                                                other_expenses.end_year::character varying,
                                                                other_expenses.id as expenses_id,
                                                                other_expenses.detail,
                                                                hr_job.id as job_id,
                                                                hr_job.name as job_name,
                                                                (case when other_expenses.gender is null then '0' else other_expenses.gender end) as gender,
                                                                other_expenses.price
                                                        from other_expenses
                                                        left join hr_job_other_expenses_rel on other_expenses.id = hr_job_other_expenses_rel.other_expenses_id  
                                                        left join hr_job on hr_job_other_expenses_rel.hr_job_id = hr_job.id
                                                        ) as view_otherexp
                                                    left join
                                                        (select '0' as keyvalue,
                                                                'male' as value
                                                        union all 
                                                        select  '0' as keyvalue,
                                                                'female' as value
                                                        union all 		
                                                        select  'male' as keyvalue,
                                                                'male' as value		
                                                        union all 
                                                        select  'female' as keyvalue,
                                                                'female' as value		
                                                        ) as view_gender		
                                                    on view_otherexp.gender = view_gender.keyvalue	
                                                    ) as view_emp_otherexp	
                                                on hr_employee.job_id = view_emp_otherexp.job_id and hr_employee.gender = view_emp_otherexp.value
                                                ) as view_detail
                                            group by view_detail.start_year, view_detail.end_year, view_detail.employee_id	
                                            ) as view_otherexpenses
                                        on view_payslip.employee_id = view_otherexpenses.employee_id and (view_payslip.year_datefrom >= view_otherexpenses.start_year and view_payslip.year_datefrom <= view_otherexpenses.end_year)
                                        left join
                                            (--Luong thang 13, BHXH_DN, BHYT_DN, BHTN_DN, cong_doan
                                            select hr_payslip.id as payslip_id,
                                                    hr_payslip.contract_id,
                                                    coalesce(hr_contract.wage,0) as wage,
                                                    coalesce(hr_contract.hourly_wage,0) as hourly_wage,
                                                    coalesce(hr_contract.x_insurance_wage,0) as x_insurance_wage,
                                                    coalesce(hr_contract.x_insurance_wage*0.175,0) as BHXH_DN,
                                                    coalesce(hr_contract.x_insurance_wage*0.03,0) as BHYT_DN,
                                                    coalesce(hr_contract.x_insurance_wage*0.01,0) as BHTN_DN,
                                                    coalesce(hr_contract.x_insurance_wage*0.02,0) as cong_doan,
                                                    coalesce(hr_contract.wage/12,0) as wage13permonth,
                                                    coalesce(hr_contract.hourly_wage/12,0) as wage13permonth_hour
                                            from hr_payslip 
                                            left join hr_contract on hr_payslip.contract_id = hr_contract.id
                                            ) as view_wagecontract
                                        on view_payslip.payslip_id = view_wagecontract.payslip_id
                                        left join 
                                            (--So gio cong quy doi
                                            select view_base.payslip_id,
                                                    sum(view_base.gio_cong_quy_doi) as gio_cong_quy_doi
                                            from
                                                (select hr_payslip_input.id as ininput_id,
                                                        hr_payslip_input.payslip_id,
                                                        (case when hr_payslip_input.input_type_id = 12 then hr_payslip_input.amount else 0 end) as gio_cong_quy_doi
                                                from hr_payslip_input
                                                ) as view_base
                                            group by view_base.payslip_id	
                                            ) as view_giocongquydoi
                                        on view_payslip.payslip_id = view_giocongquydoi.payslip_id 
                                        left join 
                                            (--So gio ho tro luong bu cong
                                            select view_base.payslip_id,
                                                    sum(view_base.gio_bu_cong) as gio_bu_cong
                                            from
                                                (select hr_payslip_input.id as ininput_id,
                                                        hr_payslip_input.payslip_id,
                                                        (case when hr_payslip_input.input_type_id = 13 then hr_payslip_input.amount else 0 end) as gio_bu_cong
                                                from hr_payslip_input
                                                ) as view_base
                                            group by view_base.payslip_id	
                                            ) as view_giobucong
                                        on view_payslip.payslip_id = view_giobucong.payslip_id 
                                        left join 
                                            (--So gio lam viec/ Ngay: 44h or 48h
                                            select	hr_contract.id as contract_id,
                                                    resource_calendar.hours_per_day 
                                            from hr_contract
                                            left join resource_calendar on hr_contract.resource_calendar_id  = resource_calendar.id
                                            ) as view_hoursperday
                                        on view_payslip.contract_id = view_hoursperday.contract_id
                                        left join 
                                            (--So gio cong ly thuyet
                                            select  view_base.payslip_id,
                                                    sum(view_base.gio_cong_ly_thuyet) as gio_cong_ly_thuyet
                                            from
                                                (select hr_payslip_input.id as ininput_id,
                                                        hr_payslip_input.payslip_id,
                                                        (case when hr_payslip_input.input_type_id = 15 then hr_payslip_input.amount else 0 end) as gio_cong_ly_thuyet
                                                from hr_payslip_input
                                                ) as view_base
                                            group by view_base.payslip_id	
                                            ) as view_gioconglythuyet
                                        on view_payslip.payslip_id = view_gioconglythuyet.payslip_id
                                        ) as view_wage
                                    left join		
                                        (--Global off: Nghi le
                                        select  view_detail_dayoff.year_off,
                                                view_detail_dayoff.month_off,
                                                sum(view_detail_dayoff.days_off) as global_off
                                        from 
                                            (select	view_globaloff.id,
                                                    view_globaloff.name,
                                                    view_globaloff.active,
                                                    view_globaloff.date_start,
                                                    view_globaloff.date_end,
                                                    view_globaloff.number_of_days,
                                                    view_globaloff.month_start,
                                                    view_globaloff.month_end,
                                                    view_globaloff.start_of_end_month,
                                                    view_globaloff.days_of_end_month,
                                                    view_globaloff.flag,
                                                    view_month.value,
                                                    (case when view_globaloff.flag = '0' then number_of_days 
                                                         when view_globaloff.flag = '1' and view_month.value = '0' then view_globaloff.number_of_days - view_globaloff.days_of_end_month
                                                         when view_globaloff.flag = '1' and view_month.value = '1' then view_globaloff.days_of_end_month
                                                         else 0 end 
                                                    ) as days_off,
                                                    (case when view_month.value = '0' then view_globaloff.month_start else view_globaloff.month_end end) as month_off,
                                                    extract ('year' from view_globaloff.date_end)::character varying as year_off
                                            from
                                                (select hr_global_off.id,
                                                        hr_global_off.name,
                                                        hr_global_off.active,
                                                        hr_global_off.date_start,
                                                        hr_global_off.date_end,
                                                        hr_global_off.number_of_days,
                                                        extract ('month' from hr_global_off.date_start) as month_start,
                                                        extract ('month' from hr_global_off.date_end) as month_end,
                                                        (case when extract ('month' from hr_global_off.date_start) <> extract ('month' from hr_global_off.date_end) then '1' else '0' end) as flag,
                                                        make_date(extract('year' from hr_global_off.date_end)::integer, extract ('month' from hr_global_off.date_end)::integer, 1) as start_of_end_month,
                                                        (hr_global_off.date_end - make_date(extract('year' from date_end)::integer, extract ('month' from hr_global_off.date_end)::integer, 1) + 1) as days_of_end_month
                                                from hr_global_off
                                                ) as view_globaloff
                                            left join
                                                (select '1' as keyvalue,
                                                        '1' as value
                                                union all 
                                                select  '1' as keyvalue,
                                                        '0' as value
                                                union all 		
                                                select  '0' as keyvalue,
                                                        '0' as value	
                                                ) as view_month
                                            on view_globaloff.flag = view_month.keyvalue
                                            where view_globaloff.active is true
                                            ) as view_detail_dayoff
                                            group by view_detail_dayoff.year_off, view_detail_dayoff.month_off
                                        ) as view_global_off
                                    on view_wage.year_datefrom = view_global_off.year_off and view_wage.month_datefrom = view_global_off.month_off
                                    left join
                                        (--Days off: Nghi phep, Nghi ket hon, Nghi tang gia, Nghi bu le
                                        select  view_detail.year_off,
                                                view_detail.month_off,
                                                view_detail.employee_id,
                                                sum(view_detail.days_off) as leave_days
                                        from
                                            (select view_base.leave_id,
                                                    view_base.employee_id,
                                                    view_base.date_from,
                                                    view_base.date_to,
                                                    view_base.number_of_days,
                                                    view_base.month_from,
                                                    view_base.month_to,
                                                    view_base.flag,
                                                    view_month.value, 
                                                    view_base.days_of_end_month,
                                                    (case when view_base.flag = '0' then number_of_days 
                                                         when view_base.flag = '1' and view_month.value = '0' then view_base.number_of_days - view_base.days_of_end_month
                                                         when view_base.flag = '1' and view_month.value = '1' then view_base.days_of_end_month
                                                         else 0 end 
                                                    ) as days_off,
                                                    (case when view_month.value = '0' then view_base.month_from else view_base.month_to end) as month_off,
                                                    extract ('year' from view_base.date_to)::character varying as year_off
                                            from
                                                (select hr_leave.id as leave_id,
                                                        hr_leave.state as leave_state,
                                                        hr_leave.holiday_status_id,
                                                        hr_leave_type.name as leave_name,
                                                        hr_leave.employee_id,
                                                        hr_leave.department_id,
                                                        hr_leave.date_from::date,
                                                        hr_leave.date_to::date,
                                                        hr_leave.number_of_days,
                                                        extract ('month' from hr_leave.date_from) as month_from,
                                                        extract ('month' from hr_leave.date_to) as month_to,
                                                        (case when extract ('month' from hr_leave.date_from) <> extract ('month' from hr_leave.date_to) then '1' else '0' end) as flag,
                                                        make_date(extract('year' from hr_leave.date_to)::integer, extract ('month' from hr_leave.date_to)::integer, 1) as start_of_end_month,
                                                        (hr_leave.date_to::date - make_date(extract('year' from hr_leave.date_to)::integer, extract ('month' from hr_leave.date_to)::integer, 1) + 1) as days_of_end_month
                                                from hr_leave
                                                left join hr_leave_type on hr_leave.holiday_status_id = hr_leave_type.id
                                                where hr_leave_type.code in ('NP', 'KH', 'TG', 'NBL')
                                                ) as view_base
                                            left join
                                                (select '1' as keyvalue,
                                                        '1' as value
                                                union all 
                                                select  '1' as keyvalue,
                                                        '0' as value
                                                union all 		
                                                select  '0' as keyvalue,
                                                        '0' as value	
                                                ) as view_month
                                            on view_base.flag = view_month.keyvalue
                                            ) as view_detail
                                        group by view_detail.year_off, view_detail.month_off, view_detail.employee_id
                                        ) as view_leave
                                    on view_wage.year_datefrom = view_leave.year_off and view_wage.month_datefrom = view_leave.month_off and view_wage.employee_id = view_leave.employee_id
                                    order by view_wage.year_datefrom desc, view_wage.month_datefrom desc
                                    ) as view_dongianhanvien
                                on view_checkin.employee_id = view_dongianhanvien.employee_id and  view_checkin.year_chamcong = view_dongianhanvien.year_datefrom and view_checkin.month_chamcong = view_dongianhanvien.month_datefrom
                                left join hr_employee on view_checkin.employee_id = hr_employee.id
                                ) as view_detail
                            group by view_detail.pp_id_report, view_detail.pp_name_report
                        ) as view_expenses_checkin
                        on view_projectclosed.pp_id_report = view_expenses_checkin.pp_id_report
                        left join 
                            (--THUC TE: theo phiếu chi
                            select  view_mergeproject.project_detail as pp_id_report,
                                    project_project.name as pp_name_report,
                                    sum(coalesce(view_payment_pp.chi_cohoadon,0)) as chi_cohoadon,
                                    sum(coalesce(view_payment_pp.chi_khonghoadon,0)) as chi_khonghoadon,
                                    sum(coalesce(view_payment_pp.chixuly_IV,0)) as chixuly_IV,
                                    sum(coalesce(view_payment_pp.chi_IV,0)) as chi_IV,
                                    sum(coalesce(view_payment_pp.thu_IV,0)) as thu_IV,
                                    sum(coalesce(view_payment_pp.thu_RRM,0)) as thu_RRM
                            from
                                (--Dự án gộp
                                select  project_project.id as pp_id,
                                        project_project.name as pp_name,
                                        project_project.x_project_type,
                                        project_project.active,
                                        project_project.state,
                                        project_project.x_order_line_id,
                                        project_project.is_merge_project,
                                        project_project.x_merge_project_id,
                                        view_subproject.merge_project_id,
                                        (case when view_subproject.merge_project_id is not null then view_subproject.merge_project_id else project_project.id end) as project_detail
                                from project_project
                                left join 
                                    (
                                    select sub_project_project.* 
                                    from sub_project_project
                                    where sub_project_project.merge_project_id is not null
                                    ) as view_subproject
                                on project_project.id = view_subproject.sub_project_id 
                                ) as view_mergeproject
                            left join project_project on view_mergeproject.project_detail = project_project.id
                            left join		
                                (--THUC TE
                                select	view_detail.project,
                                        view_detail.pp_name,
                                        sum(view_detail.tam_ung_pol_untax) as tam_ung,
                                        sum(view_detail.hoan_ung) as hoan_ung,
                                        sum(view_detail.thanh_toan_cong_no) as thanh_toan_cong_no,
                                        sum(view_detail.amount_total_tttt) as amount_total_tttt,
                                        sum(view_detail.cost * view_detail.he_so) as total,
                                        sum(view_detail.chi_cohoadon) as chi_cohoadon,
                                        sum(view_detail.chi_khonghoadon) as chi_khonghoadon,
                                        sum(view_detail.chixuly_IV) as chixuly_IV,
                                        sum(view_detail.chi_IV) as chi_IV,
                                        sum(view_detail.thu_IV) as thu_IV,
                                        sum(view_detail.thu_RRM) as thu_RRM		
                                from 
                                    (select	view_chitiet.*,	
                                            cost_type.cost_category,
                                            (case when view_chitiet.payment_type = 'inbound' then -1 else 1 end) as he_so,
                                            (case when view_chitiet.phanloaichiphi in (42,24,25) then 'Labor Cost' else 'Non-Labor Cost' end) as nhomchiphi,
                                            project_project.name as pp_name,
                                            (view_chitiet.tam_ung_pol_untax + view_chitiet.hoan_ung + view_chitiet.thanh_toan_cong_no + view_chitiet.amount_total_tttt) as cost,
                                            (case when (view_chitiet.payment_type = 'outbound' and view_chitiet.x_license_type = 'tax' and view_chitiet.x_code_money <> 38) then (view_chitiet.tam_ung_pol_untax + view_chitiet.hoan_ung + view_chitiet.thanh_toan_cong_no + view_chitiet.amount_total_tttt) else 0 end) as chi_cohoadon,
                                            (case when (view_chitiet.payment_type = 'outbound' and view_chitiet.x_license_type = 'internal' and (view_chitiet.x_code_money <> 38 and view_chitiet.phanloaichiphi <> 16)) then (view_chitiet.tam_ung_pol_untax + view_chitiet.hoan_ung + view_chitiet.thanh_toan_cong_no + view_chitiet.amount_total_tttt) else 0 end) as chi_khonghoadon,
                                            (case when (view_chitiet.payment_type = 'outbound' and view_chitiet.x_license_type = 'internal' and (view_chitiet.x_code_money = 38 and view_chitiet.phanloaichiphi = 16)) then (view_chitiet.tam_ung_pol_untax + view_chitiet.hoan_ung + view_chitiet.thanh_toan_cong_no + view_chitiet.amount_total_tttt) else 0 end) as chixuly_IV,
                                            (case when (view_chitiet.payment_type = 'outbound' and view_chitiet.x_license_type = 'tax' and view_chitiet.x_code_money = 38) then (view_chitiet.tam_ung_pol_untax + view_chitiet.hoan_ung + view_chitiet.thanh_toan_cong_no + view_chitiet.amount_total_tttt) else 0 end) as chi_IV,
                                            (case when (view_chitiet.payment_type = 'inbound' and view_chitiet.x_code_money = 42) then (view_chitiet.tam_ung_pol_untax + view_chitiet.hoan_ung + view_chitiet.thanh_toan_cong_no + view_chitiet.amount_total_tttt) else 0 end) as thu_IV,
                                            (case when (view_chitiet.payment_type = 'inbound' and view_chitiet.x_code_money = 40) then (view_chitiet.tam_ung_pol_untax + view_chitiet.hoan_ung + view_chitiet.thanh_toan_cong_no + view_chitiet.amount_total_tttt) else 0 end) as thu_RRM
                                    from
                                        (select account_payment.id as payment_id,
                                                acm_2.name as payment_name,
                                                account_payment.partner_id,
                                                res_partner.name as partner_name,
                                                account_payment.payment_type,
                                                account_payment.x_code_money,
                                                account_payment.x_license_type,
                                                code_money.code_money,
                                                code_money.content as code_money_content,
                                                account_payment.amount,
                                                account_payment.x_origin_advance_id,
                                                account_advance.number as advance_name,
                                                account_advance.license_type as license_advance,
                                                account_advance.po_id,
                                                po_1.name as po_advance_name,
                                                pol_1.x_project_id as x_project_id_tamung,
                                                pol_1.price_subtotal,
                                                pol_1.x_cost_type_id as x_cost_type_id_tamung,
                                                po_1.amount_total as po_total,
                                                coalesce(account_advance.amount_total,0) as tam_ung,
                                                (case when po_1.amount_untaxed > 0 then (pol_1.price_subtotal/po_1.amount_total)*account_advance.amount_total else 0 end) as tam_ung_pol_untax,
                                                account_payment.x_origin_repay_id,
                                                account_advance_repay.number_ballot as repay_name,
                                                account_advance_repay.license_type as license_repay,
                                                account_repay_line.project_id,
                                                coalesce(account_repay_line.amount_untaxed,0) as hoan_ung,
                                                account_repay_line.cost_type_id as cost_type_id_hoanung,
                                                account_payment.x_origin_move_id,
                                                acm_1.name as x_origin_move_name,
                                                po_2.id as po_id_congno,
                                                po_2.name as po_name_congno,
                                                pol_2.x_project_id as x_project_id_congno,
                                                pol_2.x_cost_type_id as x_cost_type_id_congno,
                                                acm_1.x_license_type as license_move,
                                                acm_1.amount_total,
                                                account_move_line.price_subtotal,
                                                (case when acm_1.amount_total > 0 then (account_move_line.price_subtotal/acm_1.amount_total)*account_payment.amount else 0 end) as thanh_toan_cong_no,
                                                (case when account_payment.x_pay_cost is true then payment_line.project_id else project_detail.project_id end) as project_id_tttt,
                                                (case when account_payment.x_pay_cost is true then payment_line.cost_type_id else project_detail.cost_type_id end) as cost_type_id_tttt,
                                                coalesce((case when account_payment.x_pay_cost is true then payment_line.amount else project_detail.amount_total end),0) as amount_total_tttt,
                                                acm_2.date as payment_date,
                                                (case when account_payment.x_origin_advance_id is not null then pol_1.x_project_id
                                                      when account_payment.x_origin_repay_id is not null then account_repay_line.project_id
                                                      when account_payment.x_origin_move_id is not null then pol_2.x_project_id
                                                      else (case when account_payment.x_pay_cost is true then payment_line.project_id else project_detail.project_id end) end
                                                ) as project,
                                                (case when account_payment.x_origin_advance_id is not null then pol_1.x_cost_type_id
                                                      when account_payment.x_origin_repay_id is not null then account_repay_line.cost_type_id
                                                      when account_payment.x_origin_move_id is not null then pol_2.x_cost_type_id
                                                      else (case when account_payment.x_pay_cost is true then payment_line.cost_type_id else project_detail.cost_type_id end) end
                                                ) as phanloaichiphi
                                        from account_payment
                                        left join account_advance on account_payment.x_origin_advance_id = account_advance.id 
                                        left join purchase_order as po_1 on account_advance.po_id = po_1.id
                                        left join purchase_order_line as pol_1 on account_advance.po_id = pol_1.order_id 
                                        left join account_advance_repay on account_payment.x_origin_repay_id = account_advance_repay.id 
                                        left join account_repay_line on account_advance_repay.id = account_repay_line.account_repay_id 
                                        left join account_move as acm_1 on account_payment.x_origin_move_id = acm_1.id
                                        left join account_move_line on acm_1.id = account_move_line.move_id and account_move_line.price_subtotal > 0
                                        left join purchase_order_line as pol_2 on account_move_line.purchase_line_id = pol_2.id
                                        left join purchase_order as po_2 on pol_2.order_id = po_2.id
                                        left join payment_line on account_payment.id = payment_line.payment_id and (account_payment.x_origin_advance_id is null and account_payment.x_origin_repay_id is null and account_payment.x_origin_move_id is null)
                                        left join project_detail on account_payment.id = project_detail.payment_id and (account_payment.x_origin_advance_id is null and account_payment.x_origin_repay_id is null and account_payment.x_origin_move_id is null)
                                        left join account_move as acm_2 on account_payment.move_id = acm_2.id
                                        left join res_partner on account_payment.partner_id = res_partner.id 
                                        left join code_money on account_payment.x_code_money = code_money.id
                                        where account_payment.partner_id <> 1
                                              and account_payment.destination_account_id = 77
                                              and account_payment.x_code_money <> 39
                                        ) as view_chitiet
                                    left join project_project on view_chitiet.project = project_project.id 
                                    left join cost_type on view_chitiet.phanloaichiphi = cost_type.id
                                    ) as view_detail
                                where  view_detail.nhomchiphi = 'Labor Cost'
                                        and (view_detail.payment_type = 'outbound' or (view_detail.payment_type = 'inbound' and view_detail.x_code_money in (40,42)))
                                group by view_detail.project, view_detail.pp_name
                                ) as view_payment_pp
                            on view_mergeproject.pp_id = view_payment_pp.project 
                            group by view_mergeproject.project_detail, project_project.name
                        ) as view_expenses_payment
                        on view_projectclosed.pp_id_report = view_expenses_payment.pp_id_report 
                        left join 
                            (--Muc do hai long
                            select  view_detail.project_id_repport,
                                    (case   when min(view_detail.chisohailong) = 0 then 'D'
                                            when min(view_detail.chisohailong) = 1 then 'A'
                                            when min(view_detail.chisohailong) = 2 then 'S'
                                            when min(view_detail.chisohailong) = 3 then 'E'
                                            end
                                    )as chisohailong
                            from
                                (select project_project.id as pp_id,
                                        project_project.x_merge_project_id,
                                        (case when customer_rate.code is null then 'A' else customer_rate.code end) as x_rate,
                                        (case 	when customer_rate.code = 'D' then 0
                                                when (project_project.x_rate_id is null or customer_rate.code = 'A') then 1
                                                when customer_rate.code = 'S' then 2
                                                when customer_rate.code = 'E' then 3
                                        end
                                        ) as chisohailong,
                                        (case when project_project.x_merge_project_id is not null then project_project.x_merge_project_id else project_project.id end) as project_id_repport
                                from project_project
                                left join customer_rate on project_project.x_rate_id = customer_rate.id
                                ) as view_detail
                            group by view_detail.project_id_repport
                            ) as view_rate
                        on view_projectclosed.pp_id_report = view_rate.project_id_repport
                        left join customer_rate on view_rate.chisohailong = customer_rate.code
                        where view_projectclosed.x_project_type is not null
                        ) as view_detail
                    where view_detail.year_lastdate = '{current_year}'
                    group by view_detail.year_lastdate, view_detail.month_lastdate, view_detail.leader, view_detail.departmentblock_name'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        # tạo ra data cuối
        if len(recs_last)<0:
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        # gom nhóm theo form báo cáo
        key_account = ['Không xác định']
        for rec in recs_last:
            if rec.get('name_leader') and rec['name_leader'] not in key_account:
                key_account.append(rec['name_leader'])
        last_data = {}

        for account in key_account:
            driff = 0
            driff_tg = 0
            for line in recs_last:
                if line['name_leader'] == account:
                    key_month = 't' + str(int(line['month_lastdate']))
                    if account not in last_data:
                        last_data[account] = {key_month: round(line.get('hieuqua') or 0)}
                    else:
                        last_data[account][key_month] = round(line.get('hieuqua') or 0)
                    driff += round(line.get('hamtrunggian') or 0)
                if not line.get('name_leader'):
                    key_month = 't' + str(int(line['month_lastdate']))
                    if 'Không xác định' not in last_data:
                        last_data['Không xác định'] = {key_month: round(line.get('hieuqua') or 0)}
                    else:
                        last_data['Không xác định'][key_month] = round(line.get('hieuqua') or 0)
                    driff_tg += round(line.get('hamtrunggian') or 0)
            if account == 'Không xác định' :
                last_data[account]['trung_gian'] = driff_tg
            else:last_data[account]['trung_gian'] = driff
        # đổ dữ liệu
        for key,value in last_data.items():
            insert = '''INSERT INTO project_manager_labor_cost (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,driff)
                                          VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{driff})
                                      '''.format(key=self.master_key,
                                                 classification=key,
                                                 t1=value.get('t1') or 0,
                                                 t2=value.get('t2') or 0,
                                                 t3=value.get('t3') or 0,
                                                 t4=value.get('t4') or 0,
                                                 t5=value.get('t5') or 0,
                                                 t6=value.get('t6') or 0,
                                                 t7=value.get('t7') or 0,
                                                 t8=value.get('t8') or 0,
                                                 t9=value.get('t9') or 0,
                                                 t10=value.get('t10') or 0,
                                                 t11=value.get('t11') or 0,
                                                 t12=value.get('t12') or 0,
                                                 driff = value.get('trung_gian',0))
            self._cr.execute(insert)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo hiệu quả quản lý chi phí nhân công',
            'view_mode': 'tree',
            'res_model': "project.manager.labor.cost",
            'context' : {'year': current_year},
            'view_id': self.env.ref('effective_management.project_manager_labor_cost_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }