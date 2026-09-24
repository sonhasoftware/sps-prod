
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleQuantityWizards(models.TransientModel):
    _name = "sale.quantity.wizards"
    _description = "Nhập tham số báo cáo khách hàng đang có hợp đồng"

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
        self._cr.execute("delete from sale_quantity where master_key = {key}".format(key=self.master_key))

        sql = f''' select  view_base.year_orderdate,
                            view_base.month_orderdate,
                            count(view_base.so_id) as sodaky_quantity
                    from
                        (select extract ('year' from sale_order.date_order):: character varying as year_orderdate,
                                extract ('month' from sale_order.date_order) as month_orderdate,
                                sale_order.id as so_id,
                                sale_order.date_order,
                                sale_order.state as order_state,
                                sale_order.project_type
                        from sale_order
                        where sale_order.state in ('sale', 'done')
                        ) as view_base
                    where view_base.year_orderdate = '{current_year}'
                    group by view_base.year_orderdate, view_base.month_orderdate
                    order by view_base.year_orderdate, view_base.month_orderdate'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        # tạo ra data cuối
        if len(recs_last)<=0:
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        # gom nhóm theo form báo cáo
        last_data={
            'Số lượng báo giá được ký': {},
        }
        for line in recs_last:
            key_month = 't'+ str(int(line['month_orderdate']))
            last_data['Số lượng báo giá được ký'][key_month] = round(line.get('sodaky_quantity') or 0)
        # đổ dữ liệu
        for key,value in last_data.items():
            insert = '''INSERT INTO sale_quantity (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                          VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
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
                                                 total = value.get('t1',0) + value.get('t2',0) + value.get('t3',0) + value.get('t4',0) + value.get('t5',0)  + value.get('t6',0) +value.get('t7',0) + value.get('t8',0) + value.get('t9',0) +value.get('t10', 0) + value.get('11',0)  + value.get('12',0))
            self._cr.execute(insert)
        sql_kh = '''select 	sum(view_tong.Thang1) as Thang1,
                            sum(view_tong.Thang2) as Thang2,
                            sum(view_tong.Thang3) as Thang3,
                            sum(view_tong.Thang4) as Thang4,
                            sum(view_tong.Thang5) as Thang5,
                            sum(view_tong.Thang6) as Thang6,
                            sum(view_tong.Thang7) as Thang7,
                            sum(view_tong.Thang8) as Thang8,
                            sum(view_tong.Thang9) as Thang9,
                            sum(view_tong.Thang10) as Thang10,
                            sum(view_tong.Thang11) as Thang11,
                            sum(view_tong.Thang12) as Thang12,
                            sum(case when (view_tong.Thang1 + view_tong.Thang2 + view_tong.Thang3 + view_tong.Thang4 + view_tong.Thang5 + view_tong.Thang6 + view_tong.Thang7 + view_tong.Thang8 + view_tong.Thang9 + view_tong.Thang10 + view_tong.Thang11 + view_tong.Thang12 > 0) then 1 else 0 end) as total_year
                    from
                        (select view_chitiet.partner_id,
                                view_chitiet.partner_name,
                                (case when (make_date(extract('year' from current_date)::integer, 1, 31) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 1, 31) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang1,
                                (case when (make_date(extract('year' from current_date)::integer, 2, 28) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 2, 28) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang2,
                                (case when (make_date(extract('year' from current_date)::integer, 3, 31) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 3, 31) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang3,
                                (case when (make_date(extract('year' from current_date)::integer, 4, 30) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 4, 30) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang4,
                                (case when (make_date(extract('year' from current_date)::integer, 5, 31) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 5, 31) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang5,
                                (case when (make_date(extract('year' from current_date)::integer, 6, 30) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 6, 30) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang6,
                                (case when (make_date(extract('year' from current_date)::integer, 7, 31) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 7, 31) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang7,
                                (case when (make_date(extract('year' from current_date)::integer, 8, 31) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 8, 31) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang8,
                                (case when (make_date(extract('year' from current_date)::integer, 9, 30) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 9, 30) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang9,
                                (case when (make_date(extract('year' from current_date)::integer, 10, 31) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 10, 31) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang10,
                                (case when (make_date(extract('year' from current_date)::integer, 11, 30) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 11, 30) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang11,
                                (case when (make_date(extract('year' from current_date)::integer, 12, 31) < view_chitiet.date_start) or (make_date(extract('year' from current_date)::integer, 12, 31) - 365 > view_chitiet.date_end) then 0 else 1 end) as Thang12
                        from 
                            (select view_ngaybatdauthucte.partner_id,
                                    res_partner.name as partner_name,
                                    view_ngaybatdauthucte.date_order::date as date_start,
                                    (case when view_ngayketthucthucte.last_date is null then current_date else view_ngayketthucthucte.last_date end) as date_end
                            from 
                                (--Ngày bắt đầu thực tế
                                select 	sale_order.partner_id,
                                        min(sale_order.date_order)::date as date_order
                                from sale_order
                                where sale_order.state in ('sale', 'done')
                                group by sale_order.partner_id 
                                ) as view_ngaybatdauthucte
                            left join
                                (--Ngày đóng dự án
                                select	view_lastdate.partner_id,
                                        max(view_lastdate.last_date) as last_date
                                from
                                    (select view_closeproject.partner_id,
                                            max(view_closeproject.x_date_end) as last_date
                                    from 
                                        (select project_project.x_order_id,
                                                project_project.id as pp_id,
                                                project_project.active,
                                                project_project.state,
                                                sale_order.partner_id,
                                                project_project.x_date_end 
                                        from project_project 
                                        left join sale_order on project_project.x_order_id = sale_order.id
                                        where project_project.x_order_id is not null
                                        ) as view_closeproject
                                    where view_closeproject.active = false and view_closeproject.state = 'completed'
                                    group by view_closeproject.partner_id
                                    
                                    union all
                                    
                                    --Ngày chấm công muộn nhất
                                    select  project_project.partner_id,
                                            max(hr_work_entry.x_date) as last_date
                                    from hr_work_entry_line 
                                    left join hr_work_entry on hr_work_entry_line.entry_id = hr_work_entry.id
                                    left join project_project on hr_work_entry_line.project_id = project_project.id
                                    where project_project.active = false and project_project.state = 'completed'
                                    group by project_project.partner_id
                                    
                                    union all
                                    
                                    --Ngày chi tiền cuối cùng
                                    select  project_project.partner_id,
                                            max(view_base.last_date) as last_date
                                    from
                                        (select view_chitiet.project,
                                            max(view_chitiet.payment_date) as last_date
                                    from
                                        (select account_payment.id as payment_id,
                                                account_payment.partner_id,
                                                account_payment.create_date::date as payment_createdate,
                                                account_payment.payment_type,
                                                account_payment.x_code_money,
                                                account_payment.amount,
                                                account_payment.x_origin_advance_id,
                                                account_advance.date_advance,
                                                account_advance.license_type as license_advance,
                                                account_advance.po_id,
                                                pol_1.x_project_id,
                                                pol_1.price_subtotal,
                                                purchase_order.amount_untaxed,
                                                account_advance.amount_total as tam_ung,
                                                (case when purchase_order.amount_untaxed > 0 then (account_advance.amount_total/purchase_order.amount_untaxed)*pol_1.price_subtotal else 0 end) as tam_ung_pol,
                                                account_payment.x_origin_repay_id,
                                                account_advance_repay.date_repay,
                                                account_advance_repay.license_type as license_repay,
                                                account_repay_line.project_id,
                                                account_repay_line.amount_untaxed as hoan_ung,
                                                account_payment.x_origin_move_id,
                                                pol_2.x_project_id,
                                                account_move.x_license_type as license_move,
                                                account_move.amount_total,
                                                account_move_line.price_subtotal,
                                                (case when account_move.amount_total > 0 then (account_payment.amount/account_move.amount_total)*account_move_line.price_subtotal else 0 end) as thanh_toan_cong_no,
                                                (case when account_payment.x_origin_advance_id is not null then account_advance.date_advance
                                                     when account_payment.x_origin_repay_id is not null then account_advance_repay.date_repay
                                                     else account_payment.create_date end
                                                )::date as payment_date,
                                                view_project.project_id as project_thanhtoantructiep,
                                                (case when account_payment.x_origin_advance_id is not null then pol_1.x_project_id
                                                      when account_payment.x_origin_repay_id is not null then account_repay_line.project_id
                                                      when account_payment.x_origin_move_id is not null then pol_2.x_project_id
                                                      else view_project.project_id end
                                                ) as project
                                        from account_payment
                                        left join account_advance on account_payment.x_origin_advance_id = account_advance.id 
                                        left join purchase_order on account_advance.po_id = purchase_order.id
                                        left join purchase_order_line as pol_1 on account_advance.po_id = pol_1.order_id 
                                        left join account_advance_repay on account_payment.x_origin_repay_id = account_advance_repay.id 
                                        left join account_repay_line on account_advance_repay.id = account_repay_line.account_repay_id 
                                        left join account_move on account_payment.x_origin_move_id = account_move.id
                                        left join account_move_line on account_move.id = account_move_line.move_id and account_move_line.price_subtotal > 0
                                        left join purchase_order_line as pol_2 on account_move_line.purchase_line_id = pol_2.id
                                        left join payment_line on account_payment.id = payment_line.payment_id 
                                        left join
                                            (select view_base.x_order_id,
                                                    max(project_project.id) as project_id
                                            from
                                                  (select project_project.x_order_id,
                                                          max(project_project.x_date_end) as x_date_end
                                                from project_project 
                                                where project_project.x_date_end < current_date
                                                group by project_project.x_order_id
                                                )  as view_base
                                            left join project_project on view_base.x_date_end = project_project.x_date_end and view_base.x_order_id = project_project.x_order_id
                                            group by view_base.x_order_id
                                            ) as view_project
                                        on payment_line.x_sale_project_id = view_project.x_order_id
                                        where account_payment.payment_type = 'outbound'
                                              and account_payment.partner_id <> 1
                                              and account_payment.destination_account_id = 77
                                              and account_payment.x_code_money <> 39
                                        ) as view_chitiet
                                        group by view_chitiet.project
                                        ) as view_base
                                        left join project_project on view_base.project = project_project.id
                                        group by project_project.partner_id 
                                    ) as view_lastdate
                                group by view_lastdate.partner_id
                                ) as view_ngayketthucthucte
                            on view_ngaybatdauthucte.partner_id = view_ngayketthucthucte.partner_id
                        left join res_partner on view_ngaybatdauthucte.partner_id = res_partner.id
                        where view_ngaybatdauthucte.partner_id not in (1, 1880) 
                        ) as view_chitiet
                        ) as view_tong'''
        self._cr.execute(sql_kh)
        recs_kh = self._cr.dictfetchall()
        for r in recs_kh:
            insert_kh = '''INSERT INTO sale_quantity (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                      VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                  '''.format(key=self.master_key,
                                                             classification='TỔNG SỐ KHÁCH HÀNG',
                                                             t1=r['thang1'],
                                                             t2=r['thang2'],
                                                             t3=r['thang3'],
                                                             t4=r['thang4'],
                                                             t5=r['thang5'],
                                                             t6=r['thang6'],
                                                             t7=r['thang7'],
                                                             t8=r['thang8'],
                                                             t9=r['thang9'],
                                                             t10=r['thang10'],
                                                             t11=r['thang11'],
                                                             t12=r['thang12'],
                                                             total= r['total_year'],)
            self._cr.execute(insert_kh)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo khách hàng đang có hợp đồng',
            'view_mode': 'tree',
            'res_model': "sale.quantity",
            'context' : {'year': current_year},
            'view_id': self.env.ref('effective_management.sale_quantity_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }