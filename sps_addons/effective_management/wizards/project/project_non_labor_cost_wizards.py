# -*- coding: utf-8 -*-
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectNonLaborCostWizards(models.TransientModel):
    _name = "project.non.labor.cost.wizards"
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

    def remove_single_quote(self,input_string):
        # Sử dụng phương thức replace() để thay thế ký tự "'" bằng chuỗi rỗng ""
        result = input_string.replace("'", "")
        return result

    def action_report(self):
        current_year = self.year
        self._cr.execute(
            "delete from project_non_labor_cost where master_key = {key}".format(key=self.master_key))
        sql = f''' select 	project_closed.pp_id_report,
                            project_closed.pp_name_report,
                            project_closed.pp_label_report,
                            project_closed.last_date,
                            sum(coalesce(view_estimate.budget,0)) as budget,
                            ((sum(coalesce(view_estimate.budget,0)) - sum(coalesce(view_actual.chi_cohoadon,0)) - sum(coalesce(view_actual.chi_IV,0))) * 20/100) as chiphithue_TNDN,
                            (sum(coalesce(view_actual.chi_cohoadon,0)) + sum(coalesce(view_actual.chi_khonghoadon,0)) + sum(coalesce(view_actual.chixuly_IV,0)) + sum(coalesce(view_actual.chi_IV,0)) - sum(coalesce(view_actual.thu_IV,0)) - sum(coalesce(view_actual.thu_RRM,0))) as chiphithucte ,
                            (sum(coalesce(view_estimate.budget,0)) - sum(coalesce(view_actual.chi_cohoadon,0)) - sum(coalesce(view_actual.chi_khonghoadon,0)) - sum(coalesce(view_actual.chixuly_IV,0)) - sum(coalesce(view_actual.chi_IV,0)) + sum(coalesce(view_actual.thu_IV,0)) + sum(coalesce(view_actual.thu_RRM,0))) as chenhlech,
                            (case when (sum(coalesce(view_estimate.budget,0)) - sum(coalesce(view_actual.chi_cohoadon,0)) - sum(coalesce(view_actual.chi_khonghoadon,0)) - sum(coalesce(view_actual.chixuly_IV,0)) - sum(coalesce(view_actual.chi_IV,0)) + sum(coalesce(view_actual.thu_IV,0)) + sum(coalesce(view_actual.thu_RRM,0))) >= 0 then 'Profit' else 'Loss' end) as hieuqua
                    from
                        (--Project Closed
                        select  view_mergeproject.pp_id,
                                view_mergeproject.pp_name,
                                view_mergeproject.x_merge_project_id,
                                view_mergeproject.project_detail as pp_id_report,
                                project_project.name as pp_name_report,
                                project_project.label_tasks as pp_label_report,
                                hr_employee.name as leader,
                                (case when project_project.x_project_type = 'maintainance' then 'Maintenance'
                                     when project_project.x_project_type = 'service' then 'Services'
                                     when project_project.x_project_type = 'opration' then 'Facility Management'
                                end) as x_project_type,
                                project_project.active,
                                view_ngayketthucthucte.last_date
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
                        where project_project.active is false and view_ngayketthucthucte.last_date is not null
                        ) as project_closed
                    left join
                        (--DU TOAN
                        select 	view_detail.pp_id,
                                view_detail.pp_name,
                                view_detail.pp_label,
                                sum(view_detail.amount_total) as budget
                        from
                            (select project_project.id as pp_id,
                                    project_project.name as pp_name,
                                    project_project.label_tasks as pp_label,
                                    material_estimate.product_id,
                                    product_template.name as product_name,
                                    material_estimate.amount as quantity,
                                    material_estimate.unit_price,
                                    (material_estimate.amount * material_estimate.unit_price) as amount_total
                            from project_project 
                            left join material_estimate on project_project.id = material_estimate.material_id 
                            left join product_product on material_estimate.product_id = product_product.id
                            left join product_template on product_product.product_tmpl_id = product_template.id
                            ) as view_detail
                        group by view_detail.pp_id, view_detail.pp_name, view_detail.pp_label
                        ) as view_estimate
                    on project_closed.pp_id = view_estimate.pp_id
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
                        where  view_detail.nhomchiphi = 'Non-Labor Cost'
                                and (view_detail.payment_type = 'outbound' or (view_detail.payment_type = 'inbound' and view_detail.x_code_money in (40,42)))
                        group by view_detail.project, view_detail.pp_name
                        ) as view_actual
                    on project_closed.pp_id = view_actual.project
                    where extract(year from project_closed.last_date) = {current_year}
                    group by project_closed.last_date, project_closed.pp_id_report, project_closed.pp_name_report, project_closed.pp_label_report '''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last)<0:
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        for r in recs_last:
            insert = '''INSERT INTO project_non_labor_cost (master_key, project_code ,project_name,date_close,budget,expenses,expenses_company)
                                          VALUES ({key},'{project_code}','{project_name}','{date_close}',{budget},{expenses},{expenses_company})
                                      '''.format(key=self.master_key,
                                                 project_code=self.remove_single_quote(r['pp_name_report']),
                                                 project_name=self.remove_single_quote(r['pp_label_report']),
                                                 date_close=str(r.get('last_date')) or 'Null' ,
                                                 budget=r['budget'] ,
                                                 expenses=r['chiphithucte'],
                                                 expenses_company=r['chiphithue_tndn'],)
            try:
                self._cr.execute(insert)
            except:
                print(insert)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo hiệu quả chi phí ngoài nhân công',
            'view_mode': 'tree',
            'res_model': "project.non.labor.cost",
            'context' : {'year': current_year},
            'view_id': self.env.ref('effective_management.project_non_labor_cost_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }