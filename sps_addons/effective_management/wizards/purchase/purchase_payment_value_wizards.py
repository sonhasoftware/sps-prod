
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchasePaymentValueWizards(models.TransientModel):
    _name = "purchase.payment.value.wizards"
    _description = "Nhập tham số báo cáo tình trạng thanh toán"

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

    def view_report(self):
        current_year = self.year
        self._cr.execute(
            "delete from purchase_payment_value where master_key = {key}".format(key=self.master_key))
        sql = f''' with all_data as(
                    select 	view_congno.year_order,
                            view_congno.month_order,
                            round(coalesce(view_payment.giatridathanhtoan,0)::numeric,2) as giatridathanhtoan,
                            round(view_congno.total_budget - coalesce(view_payment.giatridathanhtoan,0)::numeric,2) as chuathanhtoan_dutoan,
                            round(view_congno.total_actual - coalesce(view_payment.giatridathanhtoan,0)::numeric,2) as chuathanhtoan_thucte
                    from
                        (select view_tong.year_order,
                                view_tong.month_order,
                                round(sum(view_tong.total_budget)::numeric,0) as total_budget,
                                round(sum(view_tong.total_actual)::numeric,0) as total_actual
                        from 
                            (select extract ('year' from view_giatri.date_order):: character varying as year_order,
                                    extract ('month' from view_giatri.date_order) as month_order,
                                    view_giatri.date_order,
                                    view_giatri.po_id,
                                    view_giatri.pol_id,
                                    view_giatri.product_qty,
                                    view_giatri.price_budget,
                                    view_giatri.price_actual,
                                    (case when view_giatri.price_budget > 0 then view_giatri.price_budget * view_giatri.product_qty * (1 + view_giatri.tax_rate) else view_giatri.price_subtotal + view_giatri.price_tax end) as total_budget,
                                    (view_giatri.price_subtotal + view_giatri.price_tax) as total_actual
                            from
                                (select view_base.po_id,
                                        view_base.pol_id,
                                        view_base.date_order,
                                        view_base.product_qty,
                                        (case when (view_base.x_budget_price = 0 or view_base.x_budget_price is null) then view_base.price_unit else view_base.x_budget_price end) as price_budget,
                                        view_base.price_unit as price_actual,
                                        view_base.price_tax,
                                        view_base.price_subtotal,
                                        (case when view_base.price_subtotal > 0 then view_base.price_tax/view_base.price_subtotal else 0 end) as tax_rate
                                from
                                    (select purchase_order_line.order_id as po_id,
                                            purchase_order_line.id as pol_id,
                                            purchase_order.date_order::date,
                                            (case when (purchase_order.x_state = 'delay' and purchase_order_line.qty_received > 0) then purchase_order_line.qty_received else purchase_order_line.product_qty end) as product_qty,
                                            purchase_order_line.qty_received,
                                            purchase_order_line.x_budget_price,
                                            purchase_order_line.price_unit,
                                            purchase_order.x_state,
                                            purchase_order_line.price_tax,
                                            purchase_order_line.price_subtotal,
                                            (case 
                                                when purchase_order.x_state = 'draft' then true
                                                when (purchase_order.x_state = 'delay' and purchase_order_line.qty_received = 0) then true 
                                                else false 
                                                end	
                                            ) as pol_exceptional
                                    from purchase_order_line 
                                    left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                    ) as view_base
                                where pol_exceptional = false 
                                ) as view_giatri
                            ) as view_tong											
                        group by view_tong.year_order, view_tong.month_order
                        ) as view_congno
                    left join 
                        (--Giá trị đã thanh toán
                        select  view_base.year_order,
                                view_base.month_order,
                                sum(view_base.giatridatamung + view_base.thanhtoan_po) as giatridathanhtoan
                        from
                            (select extract ('year' from purchase_order.date_order):: character varying as year_order,
                                    extract ('month' from purchase_order.date_order) as month_order,
                                    purchase_order.id as po_id,
                                    account_move.id as move_id,
                                    sum(account_payment.amount) as giatridatamung,
                                    0 as thanhtoan_po
                            from account_advance
                            left join account_payment on account_advance.id = account_payment.x_origin_advance_id 
                            left join account_move on account_payment.id = account_move.payment_id 
                            left join purchase_order on account_advance.po_id = purchase_order.id
                            where 	account_advance.state not in ('completed') 
                                    and account_move.state = 'posted' 
                                    and account_advance.po_id is not null
                            group by year_order, month_order, purchase_order.id, account_move.id
                            
                            union all
                            
                            select 	extract ('year' from purchase_order.date_order)::character varying as year_order,
                                    extract ('month' from purchase_order.date_order) as month_order,
                                    view_detailpayment.po_id,
                                    view_detailpayment.move_id,
                                    0 as giatridatamung,
                                    view_detailpayment.thanhtoan_po
                            from 
                                (select view_congnophatsinh.move_id,
                                        view_congnophatsinh.order_id as po_id,
                                        view_congnophatsinh.debit,
                                        view_congnophatsinh.tongcongno,
                                        view_congnophatsinh.thue,
                                        view_congnophatsinh.thuethanhphan,
                                        view_congnophatsinh.giatripo_partial,
                                        view_giatrithanhtoantheohdon.debit as giatridathanhtoan,
                                        view_congnophatsinh.tylecongno * view_giatrithanhtoantheohdon.debit / 100 as thanhtoan_po,
                                        view_congnophatsinh.tylecongno
                                from
                                    (select view_base1.move_id,
                                            view_base1.order_id,
                                            view_base1.debit,
                                            view_base2.tongcongno,
                                            coalesce(view_base3.debit,0) as thue,
                                            (case when view_base2.tongcongno - coalesce(view_base3.debit,0)> 0  then (coalesce(view_base3.debit,0)/(view_base2.tongcongno - coalesce(view_base3.debit,0)))*view_base1.debit else 0 end) as thuethanhphan,
                                            view_base1.debit + (case when view_base2.tongcongno - coalesce(view_base3.debit,0)> 0  then (coalesce(view_base3.debit,0)/(view_base2.tongcongno - coalesce(view_base3.debit,0)))*view_base1.debit else 0 end) as giatripo_partial,
                                            (case when view_base2.tongcongno > 0 then round(((view_base1.debit + (case when view_base2.tongcongno - coalesce(view_base3.debit,0)> 0  then (coalesce(view_base3.debit,0)/(view_base2.tongcongno - coalesce(view_base3.debit,0)))*view_base1.debit else 0 end))/view_base2.tongcongno)*100::numeric,2) else 0 end) as tylecongno
                                    from
                                        (select account_move_line.move_id,
                                                purchase_order.id as order_id,
                                                sum(account_move_line.debit) as debit
                                        from account_move_line 
                                        left join purchase_order_line on account_move_line.purchase_line_id = purchase_order_line.id
                                        left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                        where account_move_line.move_id in --Tìm bút toán đối ứng phát sinh công nợ tăng
                                            (select account_move_line.move_id --Tìm bút toán phát sinh công nợ
                                            from account_move_line 
                                            where 	account_move_line.parent_state = 'posted' 
                                                    and account_move_line.account_id = 77	
                                                    and account_move_line.credit > 0
                                            ) 
                                            and account_move_line.debit > 0
                                            and (account_move_line.purchase_line_id is not null	or account_move_line.tax_line_id is not null)
                                        group by account_move_line.move_id, purchase_order.id
                                        ) as view_base1
                                    left join
                                        (select account_move_line.move_id,
                                                sum(account_move_line.debit) as tongcongno
                                        from account_move_line 
                                        left join purchase_order_line on account_move_line.purchase_line_id = purchase_order_line.id
                                        left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                        where account_move_line.move_id in --Tìm bút toán đối ứng phát sinh công nợ tăng
                                            (select account_move_line.move_id --Tìm bút toán phát sinh công nợ
                                            from account_move_line 
                                            where 	account_move_line.parent_state = 'posted' 
                                                    and account_move_line.account_id = 77	
                                                    and account_move_line.credit > 0
                                            ) 
                                            and account_move_line.debit > 0
                                            and (account_move_line.purchase_line_id is not null	or account_move_line.tax_line_id is not null)
                                        group by account_move_line.move_id
                                        ) as view_base2
                                    on 	view_base1.move_id = view_base2.move_id
                                    left join 
                                        (select account_move_line.move_id,
                                                purchase_order.id as order_id,
                                                sum(account_move_line.debit) as debit
                                        from account_move_line 
                                        left join purchase_order_line on account_move_line.purchase_line_id = purchase_order_line.id
                                        left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                        where account_move_line.move_id in --Tìm bút toán đối ứng phát sinh công nợ tăng
                                            (select account_move_line.move_id --Tìm bút toán phát sinh công nợ
                                            from account_move_line 
                                            where 	account_move_line.parent_state = 'posted' 
                                                    and account_move_line.account_id = 77	
                                                    and account_move_line.credit > 0
                                            ) 
                                            and account_move_line.debit > 0
                                            and (account_move_line.purchase_line_id is not null	or account_move_line.tax_line_id is not null)
                                        group by account_move_line.move_id, purchase_order.id
                                        ) as view_base3
                                    on 	view_base1.move_id = view_base3.move_id and view_base3.order_id is null
                                    ) as view_congnophatsinh
                                left join
                                    (select account_payment.x_origin_move_id,
                                            sum(account_move_line.debit) as debit				
                                    from account_move_line
                                    inner join account_payment on account_move_line.move_id = account_payment.move_id
                                    where 	account_move_line.debit > 0 
                                            and account_move_line.account_id = 77
                                            and account_payment.payment_type = 'outbound'
                                            and account_payment.partner_type = 'supplier'
                                            and account_payment.x_origin_move_id is not null
                                    group by account_payment.x_origin_move_id
                                    ) as view_giatrithanhtoantheohdon
                                on view_congnophatsinh.move_id = view_giatrithanhtoantheohdon.x_origin_move_id
                                where view_giatrithanhtoantheohdon.debit is not null and view_congnophatsinh.order_id is not null
                                ) as view_detailpayment
                                left join purchase_order on view_detailpayment.po_id = purchase_order.id
                            order by po_id, move_id
                            ) as view_base
                        group by view_base.year_order, view_base.month_order
                        ) as view_payment
                    on view_congno.year_order = view_payment.year_order and view_congno.month_order = view_payment.month_order)
                    select * from all_data where year_order = '{current_year}'
                    '''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        # tạo ra data cuối
        if len(recs_last) < 0:
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        # gom nhóm theo form báo cáo
        last_data = {
            'Giá trị đã thanh toán': {},
            'Giá trị chưa thanh toán(Theo đơn giá thực tế)': {},
            'Giá trị chưa thanh toán(Theo đơn giá dự toán)': {},
        }
        for line in recs_last:
            key_month = 't' + str(int(line['month_order']))
            last_data['Giá trị đã thanh toán'][key_month] = round(line['giatridathanhtoan'])
            last_data['Giá trị chưa thanh toán(Theo đơn giá thực tế)'][key_month] = round(line['chuathanhtoan_thucte'])
            last_data['Giá trị chưa thanh toán(Theo đơn giá dự toán)'][key_month] = round(line['chuathanhtoan_dutoan'])
        # đổ dữ liệu
        for key, value in last_data.items():
            insert = '''INSERT INTO purchase_payment_value (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                                  VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
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
                                                         t12=value.get('t12') or 0, )
            self._cr.execute(insert)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo tình trạng thanh toán',
            'view_mode': 'tree',
            'res_model': 'purchase.payment.value',
            'context': {'year': current_year},
            'view_id': self.env.ref('effective_management.purchase_payment_value_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }

    # def action_report(self):
    #     current_year = self.year
    #     self._cr.execute(
    #         "delete from purchase_payment_value where master_key = {key}".format(key=self.master_key))
    #     # tính công nợ phát sinh
    #     sql = '''
    #               select  view_congnophatsinh.*,
    #                       view_giatrithanhtoantheohdon.debit as giatridathanhtoan
    #               from
    #                   (select account_move_line.move_id,
    #                           purchase_order.id as order_id,
    #                           purchase_order.create_date,
    #                           sum(account_move_line.debit) as debit
    #                   from account_move_line
    #                   left join purchase_order_line on account_move_line.purchase_line_id = purchase_order_line.id
    #                   left join purchase_order on purchase_order_line.order_id = purchase_order.id
    #                   where account_move_line.move_id in --Tìm bút toán đối ứng phát sinh công nợ tăng
    #                       (select account_move_line.move_id --Tìm bút toán phát sinh công nợ
    #                       from account_move_line
    #                       where 	account_move_line.parent_state = 'posted'
    #                               and account_move_line.account_id = 77
    #                               and account_move_line.credit > 0
    #                       )
    #                       and account_move_line.debit > 0
    #                       and (account_move_line.purchase_line_id is not null	or account_move_line.tax_line_id is not null)
    #                       and purchase_order.id is not null
    #                   group by account_move_line.move_id, purchase_order.id,purchase_order.create_date
    #                   ) as view_congnophatsinh
    #               left join
    #                   (select account_payment.x_origin_move_id,
    #                           sum(account_move_line.debit) as debit
    #                   from account_move_line
    #                   inner join account_payment on account_move_line.move_id = account_payment.move_id
    #                   where 	account_move_line.debit > 0
    #                           and account_move_line.account_id = 77
    #                           and account_payment.payment_type = 'outbound'
    #                           and account_payment.partner_type = 'supplier'
    #                           and account_payment.x_origin_move_id is not null
    #                   group by account_payment.x_origin_move_id
    #                   ) as view_giatrithanhtoantheohdon
    #               on view_congnophatsinh.move_id = view_giatrithanhtoantheohdon.x_origin_move_id
    #               where view_giatrithanhtoantheohdon.debit is not null
    #               order by move_id, order_id
    #               '''
    #     self._cr.execute(sql)
    #     recs = self._cr.dictfetchall()
    #     # nhóm theo bút toán
    #     data_invoice = {}
    #     data_payment = {}
    #     for r in recs:
    #         if r['move_id'] not in data_invoice:
    #             data_invoice[r['move_id']] = {
    #                 r['order_id']: {'debit': r['debit'], 'order_date': r['create_date']},
    #                 'payment': r['giatridathanhtoan']
    #             }
    #         else:
    #             if not r['order_id']:
    #                 data_invoice[r['move_id']].update({'tax': r['debit']})
    #             else:
    #                 data_invoice[r['move_id']].update(
    #                     {
    #                         r['order_id']: {'debit': r['debit'], 'order_date': r['create_date']}
    #                     }
    #                 )
    #     # tính giá trị đã thanh toán theo từng PO
    #     for key, value in data_invoice.items():
    #         payment_value = value['payment']
    #         for k, v in value.items():
    #             if k == 'payment' or k == 'tax':
    #                 continue
    #             else:
    #                 if k not in data_payment:
    #                     data_payment[k] = {
    #                         'month': v['order_date'].date().month,
    #                         'year': v['order_date'].date().year,
    #                         'payment_done': v['debit'] if payment_value >= v['debit'] else payment_value
    #                     }
    #                 else:
    #                     data_payment[k]['payment_done'] += v['debit']
    #             payment_value -= v['debit']
    #
    #     # print(data_payment)
    #     # tính giá trị tạm ứng theo từng PO
    #     sql_tu = ''' select purchase_order.id as po_id,
    #                           sum(account_payment.amount) as giatridatamung
    #                    from account_advance
    #                    left join account_payment on account_advance.id = account_payment.x_origin_advance_id
    #                    left join account_move on account_payment.id = account_move.payment_id
    #                    left join purchase_order on account_advance.po_id = purchase_order.id
    #                    where 	account_advance.state not in ('completed','cancel')
    #                           and account_move.state = 'posted'
    #                           and account_advance.po_id is not null
    #                    group by purchase_order.id'''
    #     self._cr.execute(sql_tu)
    #     recs_tu = self._cr.dictfetchall()
    #     # cộng thêm giá trị tạm ứng cho PO
    #     for r_tu in recs_tu:
    #         if r_tu['po_id'] in data_payment:
    #             data_payment[r_tu['po_id']]['payment_done'] += r_tu['giatridatamung']
    #         else:
    #             continue
    #     # print(data_payment)
    #     # tính giá trị cần thanh toán theo thực tế và dự toán
    #     sql_price = f'''with data_price as(
    #                   select 	view_tong.year_order,
    #                           view_tong.month_order,
    #                           round(sum(view_tong.total_budget)::numeric,0) as total_budget,
    #                           round(sum(view_tong.total_actual)::numeric,0) as total_actual
    #                   from
    #                       (select extract ('year' from view_giatri.date_order):: character varying as year_order,
    #                               extract ('month' from view_giatri.date_order) as month_order,
    #                               view_giatri.date_order,
    #                               view_giatri.po_id,
    #                               view_giatri.pol_id,
    #                               view_giatri.product_qty,
    #                               view_giatri.price_budget,
    #                               view_giatri.price_actual,
    #                               (case when view_giatri.price_budget > 0 then view_giatri.price_budget*view_giatri.product_qty else view_giatri.price_subtotal end) as total_budget,
    #                               view_giatri.price_subtotal as total_actual
    #                       from
    #                           (select view_base.po_id,
    #                                   view_base.pol_id,
    #                                   view_base.date_order,
    #                                   view_base.product_qty,
    #                                   (case when (view_base.x_budget_price = 0 or view_base.x_budget_price is null) then view_base.price_unit else view_base.x_budget_price end) as price_budget,
    #                                   view_base.price_unit as price_actual,
    #                                   view_base.price_tax,
    #                                   view_base.price_subtotal
    #                           from
    #                               (select purchase_order_line.order_id as po_id,
    #                                       purchase_order_line.id as pol_id,
    #                                       purchase_order.date_order::date,
    #                                       (case when (purchase_order.x_state = 'delay' and purchase_order_line.qty_received > 0) then purchase_order_line.qty_received else purchase_order_line.product_qty end) as product_qty,
    #                                       purchase_order_line.qty_received,
    #                                       purchase_order_line.x_budget_price,
    #                                       purchase_order_line.price_unit,
    #                                       purchase_order.x_state,
    #                                       purchase_order_line.price_tax,
    #                                       purchase_order_line.price_subtotal,
    #                                       (case
    #                                           when purchase_order.x_state = 'draft' then true
    #                                           when (purchase_order.x_state = 'delay' and purchase_order_line.qty_received = 0) then true
    #                                           else false
    #                                           end
    #                                       ) as pol_exceptional
    #                               from purchase_order_line
    #                               left join purchase_order on purchase_order_line.order_id = purchase_order.id
    #                               ) as view_base
    #                           where pol_exceptional = false
    #                           ) as view_giatri
    #                       ) as view_tong
    #                   group by view_tong.year_order, view_tong.month_order
    #                   order by view_tong.year_order, view_tong.month_order)
    #                       select data_price.year_order ,
    #                               data_price.month_order,
    #                               sum(data_price.total_budget) as giatridutoan,
    #                               sum(data_price.total_actual) as giatrithucte,
    #                               0 as giatrithanhtoan
    #                       from data_price
    #                       where data_price.year_order = '{current_year}'
    #                       group by data_price.year_order, data_price.month_order
    #                       order by data_price.year_order, data_price.month_order'''
    #     self._cr.execute(sql_price)
    #     recs_last = self._cr.dictfetchall()
    #     # tạo ra data cuối
    #     if len(recs_last) > 0:
    #         for rec in recs_last:
    #             for value in data_payment.values():
    #                 if value['month'] == rec['month_order'] and str(value['year']) == rec['year_order']:
    #                     rec['giatrithanhtoan'] += value['payment_done']
    #                     rec['giatrithucte'] -= value['payment_done']
    #                     rec['giatridutoan'] -= value['payment_done']
    #                 else:
    #                     continue
    #     else:
    #         raise UserError("Hiện không có dữ liệu cho báo cáo")
    #     # gom nhóm theo form báo cáo
    #     last_data = {
    #         'Giá trị đã thanh toán': {},
    #         'Giá trị chưa thanh toán(Theo đơn giá thực tế)': {},
    #         'Giá trị chưa thanh toán(Theo đơn giá dự toán)': {},
    #     }
    #     for line in recs_last:
    #         key_month = 't' + str(int(line['month_order']))
    #         last_data['Giá trị đã thanh toán'][key_month] = round(line['giatrithanhtoan'])
    #         last_data['Giá trị chưa thanh toán(Theo đơn giá thực tế)'][key_month] = round(line['giatrithucte'])
    #         last_data['Giá trị chưa thanh toán(Theo đơn giá dự toán)'][key_month] = round(line['giatridutoan'])
    #     # đổ dữ liệu
    #     for key, value in last_data.items():
    #         insert = '''INSERT INTO purchase_payment_value (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
    #                                         VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
    #                                     '''.format(key=self.master_key,
    #                                                classification=key,
    #                                                t1=value.get('t1') or 0,
    #                                                t2=value.get('t2') or 0,
    #                                                t3=value.get('t3') or 0,
    #                                                t4=value.get('t4') or 0,
    #                                                t5=value.get('t5') or 0,
    #                                                t6=value.get('t6') or 0,
    #                                                t7=value.get('t7') or 0,
    #                                                t8=value.get('t8') or 0,
    #                                                t9=value.get('t9') or 0,
    #                                                t10=value.get('t10') or 0,
    #                                                t11=value.get('t11') or 0,
    #                                                t12=value.get('t12') or 0, )
    #         self._cr.execute(insert)
    #         # print(insert)
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Báo cáo tình trạng thanh toán',
    #         'view_mode': 'tree',
    #         'res_model': 'purchase.payment.value',
    #         'context': {'year': current_year},
    #         'view_id': self.env.ref('effective_management.purchase_payment_value_tree').id,
    #         'domain': [('master_key', '=', self.master_key)],
    #         'target': 'main',
    #
    #     }