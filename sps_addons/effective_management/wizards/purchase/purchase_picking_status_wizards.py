
import datetime as dt

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class PurchasePickingStatusWizards(models.TransientModel):
    _name = "purchase.picking.status.wizards"
    _description = "Nhập tham số báo cáo giao hàng"

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

    def _get_time_report(self):
        time_now = datetime(int(self.year), 12, 31)
        vals = {}
        for i in range(1, 13):
            vals.update({'m{}'.format(i): time_now - relativedelta(months=i - 1)})
        return vals

    def insert_tong(self,time):
        sql = ''' with so_hm_dat_hang as (
                           select  view_tongsohangmuc.year_dateorder as year_createdate,
                                    view_tongsohangmuc.month_dateorder as month_createdate,
                                    sum(view_tongsohangmuc.sohangmuc) as tongsohangmuc
                            from
                                (--Đếm số lượng hạng mục của PR có trạng thái: chính thức, đang thực hiện, hoàn thành, tạm hoãn
                                select 	extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                        extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                        purchase_requisition.ordering_date::date,
                                        view_soluonghangmuc.requisition_id,
                                        purchase_requisition.x_state,
                                        view_soluonghangmuc.sohangmuc
                                from
                                    (--Đếm số lượng hạng mục của PR: đếm số dòng prl_id của pr
                                    select 	purchase_requisition_line.requisition_id,
                                            count(purchase_requisition_line.id) as sohangmuc
                                    from purchase_requisition_line
                                    group by purchase_requisition_line.requisition_id 		 
                                    ) as view_soluonghangmuc
                                left join purchase_requisition on view_soluonghangmuc.requisition_id = purchase_requisition.id 
                                where purchase_requisition.x_state not in ('cancel', 'draft')
                                ) as view_tongsohangmuc
                            group by year_dateorder, month_dateorder
                            order by year_dateorder, month_dateorder ) 
                         SELECT
                            'Số hạng mục đặt hàng' AS classifine,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m1} and ptd.year_createdate = '{y1}' ) THEN tongsohangmuc ELSE 0 END ) AS jan,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m2} and ptd.year_createdate = '{y2}' ) THEN tongsohangmuc ELSE 0 END ) AS feb,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m3} and ptd.year_createdate = '{y3}' ) THEN tongsohangmuc ELSE 0 END ) AS mar,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m4} and ptd.year_createdate = '{y4}' ) THEN tongsohangmuc ELSE 0 END ) AS apr,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m5} and ptd.year_createdate = '{y5}' ) THEN tongsohangmuc ELSE 0 END ) AS may,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m6} and ptd.year_createdate = '{y6}' ) THEN tongsohangmuc ELSE 0 END ) AS jun,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m7} and ptd.year_createdate = '{y7}' ) THEN tongsohangmuc ELSE 0 END ) AS jul,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m8} and ptd.year_createdate = '{y8}' ) THEN tongsohangmuc ELSE 0 END ) AS aug,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m9} and ptd.year_createdate = '{y9}' ) THEN tongsohangmuc ELSE 0 END ) AS sep,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m10} and ptd.year_createdate = '{y10}' ) THEN tongsohangmuc ELSE 0 END ) AS oct,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m11} and ptd.year_createdate = '{y11}' ) THEN tongsohangmuc ELSE 0 END ) AS nov,
                            SUM ( CASE WHEN ( ptd.month_createdate = {m12} and ptd.year_createdate = '{y12}' ) THEN tongsohangmuc ELSE 0 END ) AS dev 
                        FROM
                            so_hm_dat_hang ptd
                        '''.format(m1=time['m12'].month, y1=time['m12'].year,
                                   m2=time['m11'].month, y2=time['m11'].year,
                                   m3=time['m10'].month, y3=time['m10'].year,
                                   m4=time['m9'].month, y4=time['m9'].year,
                                   m5=time['m8'].month, y5=time['m8'].year,
                                   m6=time['m7'].month, y6=time['m7'].year,
                                   m7=time['m6'].month, y7=time['m6'].year,
                                   m8=time['m5'].month, y8=time['m5'].year,
                                   m9=time['m4'].month, y9=time['m4'].year,
                                   m10=time['m3'].month, y10=time['m3'].year,
                                   m11=time['m2'].month, y11=time['m2'].year,
                                   m12=time['m1'].month, y12=time['m1'].year)
        self._cr.execute(sql)

        recs = self._cr.dictfetchall()
        for r in recs:
            insert = '''INSERT INTO purchase_picking_status (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                           VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                       '''.format(key=self.master_key,
                                                  classification=r['classifine'],
                                                  t1=r['jan'],
                                                  t2=r['feb'],
                                                  t3=r['mar'],
                                                  t4=r['apr'],
                                                  t5=r['may'],
                                                  t6=r['jun'],
                                                  t7=r['jul'],
                                                  t8=r['aug'],
                                                  t9=r['sep'],
                                                  t10=r['oct'],
                                                  t11=r['nov'],
                                                  t12=r['dev'], )
            self._cr.execute(insert)

    def insert_huy(self,time):
        sql_huy = ''' with so_hm_huy as (
                               select 	view_tong.year_dateorder as year_createdate,
                                        view_tong.month_dateorder as month_createdate,
                                        sum(view_tong.hangmuc_huy) as hangmuc_huy
                               from
                                    (select view_tongsohangmuc.year_dateorder,
                                            view_tongsohangmuc.month_dateorder,
                                            sum(view_tongsohangmuc.sohangmuc) as hangmuc_huy
                                    from
                                        (--Đếm số lượng hạng mục của PR có trạng thái Hủy
                                        select  purchase_requisition.create_date,
                                                extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                view_soluonghangmuc.requisition_id,
                                                purchase_requisition.x_state,
                                                view_soluonghangmuc.sohangmuc
                                        from
                                            (--Đếm số lượng hạng mục của PR: đếm số dòng prl_id của pr
                                            select 	purchase_requisition_line.requisition_id,
                                                    count(purchase_requisition_line.id) as sohangmuc
                                            from purchase_requisition_line 
                                            group by purchase_requisition_line.requisition_id 
                                            ) as view_soluonghangmuc
                                        left join purchase_requisition on view_soluonghangmuc.requisition_id = purchase_requisition.id 
                                        where purchase_requisition.x_state = 'cancel'
                                        ) as view_tongsohangmuc
                                    group by year_dateorder, month_dateorder
                                    
                                    union all 
                                    
                                    --Pending trên PO
                                    select 	view_abc.year_dateorder,
                                            view_abc.month_dateorder,
                                            count(view_abc.po_line_id) as hangmuc_huy
                                    from 
                                        (--Lấy các trường ... với điều kiện trạng thái của phiếu PO là Hủy, chưa nhận hàng và sản phẩm khác 'Làm tròn'
                                        select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                purchase_order.id as po_id,
                                                purchase_order_line.id as po_line_id,
                                                purchase_requisition.schedule_date,
                                                purchase_order_line.x_date_received,
                                                purchase_order_line.qty_received	
                                        from purchase_order_line 
                                        left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                        left join pa_line_po_line_ref on purchase_order_line.id = pa_line_po_line_ref.po_line_id
                                        left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                        left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                        where 	purchase_order.x_state = 'delay'
                                                and purchase_order_line.qty_received = 0
                                                and purchase_order_line.product_id not in (4747)
                                        ) as view_abc
                                    group by view_abc.year_dateorder, view_abc.month_dateorder
                                    ) as view_tong
                                group by view_tong.year_dateorder, view_tong.month_dateorder
                                order by view_tong.year_dateorder, view_tong.month_dateorder) 
                            SELECT
                               'Số hạng mục hủy' AS classifine,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m1} and ptd.year_createdate = '{y1}' ) THEN hangmuc_huy ELSE 0 END ) AS jan,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m2} and ptd.year_createdate = '{y2}' ) THEN hangmuc_huy ELSE 0 END ) AS feb,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m3} and ptd.year_createdate = '{y3}' ) THEN hangmuc_huy ELSE 0 END ) AS mar,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m4} and ptd.year_createdate = '{y4}' ) THEN hangmuc_huy ELSE 0 END ) AS apr,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m5} and ptd.year_createdate = '{y5}' ) THEN hangmuc_huy ELSE 0 END ) AS may,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m6} and ptd.year_createdate = '{y6}' ) THEN hangmuc_huy ELSE 0 END ) AS jun,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m7} and ptd.year_createdate = '{y7}' ) THEN hangmuc_huy ELSE 0 END ) AS jul,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m8} and ptd.year_createdate = '{y8}' ) THEN hangmuc_huy ELSE 0 END ) AS aug,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m9} and ptd.year_createdate = '{y9}' ) THEN hangmuc_huy ELSE 0 END ) AS sep,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m10} and ptd.year_createdate = '{y10}' ) THEN hangmuc_huy ELSE 0 END ) AS oct,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m11} and ptd.year_createdate = '{y11}' ) THEN hangmuc_huy ELSE 0 END ) AS nov,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m12} and ptd.year_createdate = '{y12}' ) THEN hangmuc_huy ELSE 0 END ) AS dev 
                           FROM
                               so_hm_huy ptd
                           '''.format(m1=time['m12'].month, y1=time['m12'].year,
                                      m2=time['m11'].month, y2=time['m11'].year,
                                      m3=time['m10'].month, y3=time['m10'].year,
                                      m4=time['m9'].month, y4=time['m9'].year,
                                      m5=time['m8'].month, y5=time['m8'].year,
                                      m6=time['m7'].month, y6=time['m7'].year,
                                      m7=time['m6'].month, y7=time['m6'].year,
                                      m8=time['m5'].month, y8=time['m5'].year,
                                      m9=time['m4'].month, y9=time['m4'].year,
                                      m10=time['m3'].month, y10=time['m3'].year,
                                      m11=time['m2'].month, y11=time['m2'].year,
                                      m12=time['m1'].month, y12=time['m1'].year)
        self._cr.execute(sql_huy)

        recs = self._cr.dictfetchall()
        for r in recs:
            insert_huy = '''INSERT INTO purchase_picking_status (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                              VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                          '''.format(key=self.master_key,
                                                     classification=r['classifine'],
                                                     t1=r['jan'],
                                                     t2=r['feb'],
                                                     t3=r['mar'],
                                                     t4=r['apr'],
                                                     t5=r['may'],
                                                     t6=r['jun'],
                                                     t7=r['jul'],
                                                     t8=r['aug'],
                                                     t9=r['sep'],
                                                     t10=r['oct'],
                                                     t11=r['nov'],
                                                     t12=r['dev'], )
            self._cr.execute(insert_huy)

    def insert_done_late(self,time):
        sql_done_late = ''' with so_hm_done_late as (
                                      select 	view_hangmuchoanthanh.year_dateorder as year_createdate_pa,
                                                view_hangmuchoanthanh.month_dateorder as month_createdate_pa,
                                                sum(view_hangmuchoanthanh.danhanhangtronghan_done) as danhanhangtronghan_done,
                                                sum(view_hangmuchoanthanh.danhanhangmuon_latearrival) as danhanhangmuon_latearrival
                                       from
                                            (--Hàng hóa lưu kho
                                            select  view_abc.year_dateorder,
                                                    view_abc.month_dateorder,
                                                    count(case when (view_abc.ngaynhapkhomuonnhat::date <= view_abc.schedule_date::date) and (view_abc.qty_done_pol >= view_abc.product_qty) then view_abc.po_line_id end) as danhanhangtronghan_done,
                                                    count(case when (view_abc.ngaynhapkhomuonnhat::date > view_abc.schedule_date::date) and (view_abc.qty_done_pol >= view_abc.product_qty) then view_abc.po_line_id end) as danhanhangmuon_latearrival
                                            from
                                                (select view_slgnhapkho.year_dateorder,
                                                        view_slgnhapkho.month_dateorder,
                                                        view_slgnhapkho.schedule_date,
                                                        view_ngaynhapkhomuonnhat.ngaynhapkhomuonnhat,
                                                        view_slgnhapkho.po_line_id,
                                                        view_slgnhapkho.pa_line_id,
                                                        view_slgnhapkho.product_qty,
                                                        view_slgnhapkho.qty_done_pol
                                                from
                                                    (select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                            extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                            purchase_requisition.schedule_date,
                                                            view_soluongnhaptheopo.po_line_id,
                                                            pa_line_po_line_ref.pa_line_id,
                                                            purchase_requisition_line.product_qty,
                                                            view_soluongnhaptheopo.qty_done_pol	
                                                    from
                                                        (select	view_base.purchase_line_id as po_line_id,
                                                                sum(view_base.qty_done_moveid) as qty_done_pol
                                                        from
                                                            (select view_qtydone_stockmoveline.move_id,
                                                                    view_qtydone_stockmoveline.qty_done_moveid,
                                                                    stock_move.picking_id,
                                                                    stock_move.purchase_line_id 
                                                            from 
                                                                (--Tính tổng số lượng đã nhận của move_id
                                                                select  move_id,
                                                                        sum(qty_done) as qty_done_moveid	
                                                                from stock_move_line
                                                                group by move_id
                                                                ) as view_qtydone_stockmoveline
                                                            left join stock_move on view_qtydone_stockmoveline.move_id = stock_move.id
                                                            where stock_move.purchase_line_id is not null
                                                            ) as view_base
                                                        left join stock_picking on view_base.picking_id = stock_picking.id 
                                                        left join purchase_order_line on view_base.purchase_line_id = purchase_order_line.id
                                                        group by view_base.purchase_line_id
                                                        ) as view_soluongnhaptheopo
                                                    left join pa_line_po_line_ref on view_soluongnhaptheopo.po_line_id = pa_line_po_line_ref.po_line_id
                                                    left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                                    left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                                    ) as view_slgnhapkho
                                                left join
                                                    (--Tính ngày nhập kho muộn nhất, tổng số lượng đã nhập của POL
                                                    select 	stock_move.purchase_line_id,
                                                            max(stock_picking.date_done)::date as ngaynhapkhomuonnhat,
                                                            sum(view_qtydone_stockmoveline.qty_done) as qty_done					
                                                    from stock_move	
                                                    left join 
                                                        (--Tính tổng số lượng đã nhận của move_id
                                                        select move_id,
                                                                sum(qty_done) as qty_done	
                                                        from stock_move_line
                                                        group by move_id
                                                        ) as view_qtydone_stockmoveline
                                                    on view_qtydone_stockmoveline.move_id = stock_move.id
                                                    left join stock_picking on stock_move.picking_id = stock_picking.id 
                                                    where stock_move.purchase_line_id is not null
                                                    group by stock_move.purchase_line_id 
                                                    ) as view_ngaynhapkhomuonnhat
                                                on view_slgnhapkho.po_line_id = view_ngaynhapkhomuonnhat.purchase_line_id
                                                ) as view_abc
                                            group by view_abc.year_dateorder, view_abc.month_dateorder
                                        
                                            union all 
                                            
                                            --Hàng hóa dịch vụ
                                            select  view_abc.year_dateorder,
                                                    view_abc.month_dateorder,
                                                    count(case when (view_abc.x_date_received::date <= view_abc.schedule_date::date) and (view_abc.qty_received >= view_abc.product_qty) then view_abc.po_line_id end) as danhanhangtronghan_done,
                                                    count(case when (view_abc.x_date_received::date > view_abc.schedule_date::date) and (view_abc.qty_received >= view_abc.product_qty) then view_abc.po_line_id end) as danhanhangmuon_latearrival
                                            from
                                                (--Lấy ra các trường ... với điều kiện loại sản phẩm là Dịch vụ, số lượng đã nhận > 0 và sản phẩm khác 'Làm tròn'
                                                select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                        extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                        purchase_order_line.id as po_line_id,
                                                        purchase_requisition.schedule_date,
                                                        purchase_order_line.x_date_received,
                                                        purchase_requisition_line.product_qty,
                                                        purchase_order_line.qty_received	
                                                from purchase_order_line 
                                                left join product_product on purchase_order_line.product_id = product_product.id 
                                                left join product_template on product_product.product_tmpl_id = product_template.id
                                                left join pa_line_po_line_ref on purchase_order_line.id = pa_line_po_line_ref.po_line_id
                                                left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                                left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                                where 	product_template.x_type = 'service'
                                                        and purchase_order_line.qty_received > 0
                                                        and purchase_order_line.product_id not in (4747)
                                                ) as view_abc
                                            group by view_abc.year_dateorder, view_abc.month_dateorder
                                            
                                            union all 
                                            
                                            --Exceptional: mua 1 phần rồi tạm hoãn, đưa về hoàn thành
                                            select 	view_abc.year_dateorder,
                                                    view_abc.month_dateorder,
                                                    count(case when view_abc.x_date_received::date <= view_abc.schedule_date::date then view_abc.po_line_id end) as danhanhangtronghan_done,
                                                    count(case when view_abc.x_date_received::date > view_abc.schedule_date::date then view_abc.po_line_id end) as danhanhangmuon_latearrival
                                            from 
                                                (--Lấy ra các trường ... với điều kiện trạng thái của PO là 'delay', số lượng nhận > 0 và sản phẩm khác 'Làm tròn' 
                                                select 	extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                        extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                        purchase_order.id,
                                                        purchase_order_line.id as po_line_id,
                                                        purchase_requisition.schedule_date,
                                                        purchase_order_line.x_date_received,
                                                        purchase_order_line.qty_received	
                                                from purchase_order_line 
                                                left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                                left join pa_line_po_line_ref on purchase_order_line.id = pa_line_po_line_ref.po_line_id
                                                left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                                left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                                where 	purchase_order.x_state = 'delay'
                                                        and purchase_order_line.qty_received > 0
                                                        and purchase_order_line.product_id not in (4747)
                                                ) as view_abc
                                            group by view_abc.year_dateorder, view_abc.month_dateorder
                                            ) as view_hangmuchoanthanh
                                        group by view_hangmuchoanthanh.year_dateorder, view_hangmuchoanthanh.month_dateorder
                                        order by view_hangmuchoanthanh.year_dateorder, view_hangmuchoanthanh.month_dateorder) 
                                    SELECT
                                       'Số hạng mục đã nhận hàng' AS classifine,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m1} and ptd.year_createdate_pa = '{y1}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS jan,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m2} and ptd.year_createdate_pa = '{y2}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS feb,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m3} and ptd.year_createdate_pa = '{y3}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS mar,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m4} and ptd.year_createdate_pa = '{y4}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS apr,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m5} and ptd.year_createdate_pa = '{y5}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS may,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m6} and ptd.year_createdate_pa = '{y6}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS jun,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m7} and ptd.year_createdate_pa = '{y7}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS jul,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m8} and ptd.year_createdate_pa = '{y8}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS aug,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m9} and ptd.year_createdate_pa = '{y9}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS sep,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m10} and ptd.year_createdate_pa = '{y10}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS oct,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m11} and ptd.year_createdate_pa = '{y11}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS nov,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m12} and ptd.year_createdate_pa = '{y12}' ) THEN danhanhangtronghan_done ELSE 0 END ) AS dev 
                                   FROM
                                       so_hm_done_late ptd
                                   Union all 
                                   SELECT
                                       'Số hạng mục đã nhận hàng, nhưng muộn' AS classifine,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m1} and ptd.year_createdate_pa = '{y1}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS jan,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m2} and ptd.year_createdate_pa = '{y2}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS feb,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m3} and ptd.year_createdate_pa = '{y3}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS mar,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m4} and ptd.year_createdate_pa = '{y4}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS apr,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m5} and ptd.year_createdate_pa = '{y5}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS may,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m6} and ptd.year_createdate_pa = '{y6}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS jun,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m7} and ptd.year_createdate_pa = '{y7}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS jul,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m8} and ptd.year_createdate_pa = '{y8}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS aug,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m9} and ptd.year_createdate_pa = '{y9}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS sep,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m10} and ptd.year_createdate_pa = '{y10}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS oct,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m11} and ptd.year_createdate_pa = '{y11}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS nov,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m12} and ptd.year_createdate_pa = '{y12}' ) THEN danhanhangmuon_latearrival ELSE 0 END ) AS dev 
                                   FROM
                                       so_hm_done_late ptd
                                   '''.format(m1=time['m12'].month, y1=time['m12'].year,
                                              m2=time['m11'].month, y2=time['m11'].year,
                                              m3=time['m10'].month, y3=time['m10'].year,
                                              m4=time['m9'].month, y4=time['m9'].year,
                                              m5=time['m8'].month, y5=time['m8'].year,
                                              m6=time['m7'].month, y6=time['m7'].year,
                                              m7=time['m6'].month, y7=time['m6'].year,
                                              m8=time['m5'].month, y8=time['m5'].year,
                                              m9=time['m4'].month, y9=time['m4'].year,
                                              m10=time['m3'].month, y10=time['m3'].year,
                                              m11=time['m2'].month, y11=time['m2'].year,
                                              m12=time['m1'].month, y12=time['m1'].year)
        self._cr.execute(sql_done_late)
        recs = self._cr.dictfetchall()
        for r in recs:
            insert_done_late = '''INSERT INTO purchase_picking_status (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                                      VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                                  '''.format(key=self.master_key,
                                                             classification=r['classifine'],
                                                             t1=r['jan'],
                                                             t2=r['feb'],
                                                             t3=r['mar'],
                                                             t4=r['apr'],
                                                             t5=r['may'],
                                                             t6=r['jun'],
                                                             t7=r['jul'],
                                                             t8=r['aug'],
                                                             t9=r['sep'],
                                                             t10=r['oct'],
                                                             t11=r['nov'],
                                                             t12=r['dev'], )
            self._cr.execute(insert_done_late)

    def insert_waite_license(self,time):
        sql_wait_license = ''' with so_hm_wait_license as (
                                       select 	view_hangmucchochungtu.year_dateorder as year_createdate_pa,
                                                view_hangmucchochungtu.month_dateorder as month_createdate_pa,
                                                sum(view_hangmucchochungtu.danhanhang_chochungtu) as danhanhang_chochungtu
                                        from
                                           (--Đã nhận hàng chờ chứng từ: Hàng hóa lưu kho
                                            select  view_abc.year_dateorder,
                                                    view_abc.month_dateorder,
                                                    count(view_abc.po_line_id) as danhanhang_chochungtu	
                                            from
                                                (select view_slgnhapkho.year_dateorder,
                                                        view_slgnhapkho.month_dateorder,
                                                        view_slgnhapkho.po_line_id,
                                                        view_slgnhapkho.pa_line_id,
                                                        view_slgnhapkho.product_qty,
                                                        view_slgnhapkho.qty_done_pol
                                                from
                                                    (select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                            extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                            purchase_requisition.schedule_date,
                                                            view_soluongnhaptheopo.po_line_id,
                                                            pa_line_po_line_ref.pa_line_id,
                                                            purchase_requisition_line.product_qty,
                                                            view_soluongnhaptheopo.qty_done_pol	
                                                    from
                                                        (select	view_base.purchase_line_id as po_line_id,
                                                                sum(view_base.qty_done_moveid) as qty_done_pol
                                                        from
                                                            (select view_qtydone_stockmoveline.move_id,
                                                                    view_qtydone_stockmoveline.qty_done_moveid,
                                                                    stock_move.picking_id,
                                                                    stock_move.purchase_line_id 
                                                            from 
                                                                (--Tính tổng số lượng đã nhận của move_id
                                                                select move_id,
                                                                        sum(qty_done) as qty_done_moveid	
                                                                from stock_move_line
                                                                group by move_id
                                                                ) as view_qtydone_stockmoveline
                                                            left join stock_move on view_qtydone_stockmoveline.move_id = stock_move.id
                                                            where stock_move.purchase_line_id is not null
                                                            ) as view_base
                                                        left join stock_picking on view_base.picking_id = stock_picking.id 
                                                        left join purchase_order_line on view_base.purchase_line_id = purchase_order_line.id
                                                        group by view_base.purchase_line_id
                                                        ) as view_soluongnhaptheopo
                                                    left join pa_line_po_line_ref on view_soluongnhaptheopo.po_line_id = pa_line_po_line_ref.po_line_id
                                                    left join purchase_order_line on pa_line_po_line_ref.po_line_id = purchase_order_line.id
                                                    left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                                    left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                                    left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                                    where 	view_soluongnhaptheopo.qty_done_pol >= purchase_requisition_line.product_qty
                                                            and purchase_order.x_license = false
                                                    ) as view_slgnhapkho
                                                ) as view_abc
                                            group by view_abc.year_dateorder, view_abc.month_dateorder
                                            
                                            union all
                                            
                                            --Đã nhận hàng chờ chứng từ: Hàng hóa dịch vụ
                                            select  view_abc.year_dateorder,
                                                    view_abc.month_dateorder,
                                                    count(view_abc.po_line_id) as danhanhang_chochungtu
                                            from
                                                (select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                        extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                        purchase_order.id,
                                                        purchase_order_line.id as po_line_id,
                                                        purchase_order_line.x_date_received,
                                                        purchase_requisition_line.product_qty,
                                                        purchase_order_line.qty_received	
                                                from purchase_order_line 
                                                left join product_product on purchase_order_line.product_id = product_product.id 
                                                left join product_template on product_product.product_tmpl_id = product_template.id
                                                left join pa_line_po_line_ref on purchase_order_line.id = pa_line_po_line_ref.po_line_id
                                                left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                                left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                                left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                                where 	product_template.x_type = 'service'
                                                        and purchase_order_line.qty_received > 0
                                                        and purchase_order_line.product_id not in (4747)
                                                        and purchase_order_line.qty_received >= purchase_requisition_line.product_qty
                                                        and purchase_order.x_license = false
                                                order by extract ('year' from purchase_requisition.create_date),extract ('month' from purchase_requisition.create_date)
                                                ) as view_abc
                                            group by view_abc.year_dateorder, view_abc.month_dateorder
                                            ) as view_hangmucchochungtu
                                        group by view_hangmucchochungtu.year_dateorder, view_hangmucchochungtu.month_dateorder
                                        order by view_hangmucchochungtu.year_dateorder, view_hangmucchochungtu.month_dateorder) 
                                    SELECT
                                       'Số hạng mục đã giao hàng, chờ chứng từ' AS classifine,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m1} and ptd.year_createdate_pa = '{y1}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS jan,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m2} and ptd.year_createdate_pa = '{y2}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS feb,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m3} and ptd.year_createdate_pa = '{y3}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS mar,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m4} and ptd.year_createdate_pa = '{y4}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS apr,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m5} and ptd.year_createdate_pa = '{y5}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS may,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m6} and ptd.year_createdate_pa = '{y6}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS jun,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m7} and ptd.year_createdate_pa = '{y7}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS jul,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m8} and ptd.year_createdate_pa = '{y8}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS aug,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m9} and ptd.year_createdate_pa = '{y9}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS sep,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m10} and ptd.year_createdate_pa = '{y10}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS oct,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m11} and ptd.year_createdate_pa = '{y11}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS nov,
                                       SUM ( CASE WHEN ( ptd.month_createdate_pa = {m12} and ptd.year_createdate_pa = '{y12}' ) THEN danhanhang_chochungtu ELSE 0 END ) AS dev 
                                   FROM
                                       so_hm_wait_license ptd
                                   '''.format(m1=time['m12'].month, y1=time['m12'].year,
                                              m2=time['m11'].month, y2=time['m11'].year,
                                              m3=time['m10'].month, y3=time['m10'].year,
                                              m4=time['m9'].month, y4=time['m9'].year,
                                              m5=time['m8'].month, y5=time['m8'].year,
                                              m6=time['m7'].month, y6=time['m7'].year,
                                              m7=time['m6'].month, y7=time['m6'].year,
                                              m8=time['m5'].month, y8=time['m5'].year,
                                              m9=time['m4'].month, y9=time['m4'].year,
                                              m10=time['m3'].month, y10=time['m3'].year,
                                              m11=time['m2'].month, y11=time['m2'].year,
                                              m12=time['m1'].month, y12=time['m1'].year)
        self._cr.execute(sql_wait_license)

        recs = self._cr.dictfetchall()
        for r in recs:
            insert_wait_license = '''INSERT INTO purchase_picking_status (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                                      VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                                  '''.format(key=self.master_key,
                                                             classification=r['classifine'],
                                                             t1=r['jan'],
                                                             t2=r['feb'],
                                                             t3=r['mar'],
                                                             t4=r['apr'],
                                                             t5=r['may'],
                                                             t6=r['jun'],
                                                             t7=r['jul'],
                                                             t8=r['aug'],
                                                             t9=r['sep'],
                                                             t10=r['oct'],
                                                             t11=r['nov'],
                                                             t12=r['dev'], )
            self._cr.execute(insert_wait_license)

    def insert_ongoing_delay(self, time):
        sql_ongoing_delay = ''' with so_hm_ongoing_delay as (
                                    select 	view_hangmucdangxuly.year_dateorder as year_createdate_pa,
                                            view_hangmucdangxuly.month_dateorder as month_createdate_pa,
                                            sum(view_hangmucdangxuly.ongoing) as ongoing,
                                            sum(view_hangmucdangxuly.delay) as delay
                                    from
                                        (--Hàng hóa lưu kho
                                        select  view_abc.year_dateorder,
                                                view_abc.month_dateorder,
                                                count(case when (view_abc.date_report <= view_abc.schedule_date::date) and (view_abc.qty_done_prl < view_abc.product_qty) then view_abc.po_line_id end) as ongoing,
                                                count(case when (view_abc.date_report > view_abc.schedule_date::date) and (view_abc.qty_done_prl < view_abc.product_qty) then view_abc.po_line_id end) as delay
                                        from
                                            (select view_slgnhapkho.year_dateorder,
                                                    view_slgnhapkho.month_dateorder,
                                                    view_slgnhapkho.schedule_date,
                                                    view_slgnhapkho.po_line_id,
                                                    view_slgnhapkho.pa_line_id,
                                                    coalesce(view_slgnhapkho.product_qty,0) as product_qty,
                                                    coalesce(view_slgnhapkho.qty_done_pol,0) as qty_done_pol,
                                                    coalesce(view_total_prl.qty_done_prl,0) as qty_done_prl,
                                                    (coalesce(view_total_prl.qty_done_prl,0) - coalesce(view_slgnhapkho.product_qty,0)) as chenhlech,
                                                    current_date as date_report
                                            from
                                                (select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                        extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                        purchase_requisition.schedule_date,
                                                        view_soluongnhaptheopo.po_line_id,
                                                        pa_line_po_line_ref.pa_line_id,
                                                        purchase_requisition_line.product_qty,
                                                        view_soluongnhaptheopo.qty_done_pol	
                                                from
                                                    (select	view_base.purchase_line_id as po_line_id,
                                                            sum(view_base.qty_done_moveid) as qty_done_pol
                                                    from
                                                        (select view_qtydone_stockmoveline.move_id,
                                                                view_qtydone_stockmoveline.qty_done_moveid,
                                                                stock_move.picking_id,
                                                                stock_move.purchase_line_id 
                                                        from 
                                                            (--Tính tổng số lượng đã nhận của move_id
                                                            select  stock_move_line.move_id,
                                                                    sum(stock_move_line.qty_done) as qty_done_moveid	
                                                            from stock_move_line
                                                            group by move_id
                                                            ) as view_qtydone_stockmoveline
                                                        left join stock_move on view_qtydone_stockmoveline.move_id = stock_move.id
                                                        where stock_move.purchase_line_id is not null
                                                        ) as view_base
                                                    left join stock_picking on view_base.picking_id = stock_picking.id 
                                                    left join purchase_order_line on view_base.purchase_line_id = purchase_order_line.id
                                                    group by view_base.purchase_line_id
                                                    ) as view_soluongnhaptheopo
                                                left join pa_line_po_line_ref on view_soluongnhaptheopo.po_line_id = pa_line_po_line_ref.po_line_id
                                                left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                                left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                                ) as view_slgnhapkho
                                            left join
                                                (--Tính ngày nhập kho muộn nhất, tổng số lượng đã nhập của POL
                                                select 	stock_move.purchase_line_id,
                                                        max(stock_picking.date_done)::date as ngaynhapkhomuonnhat,
                                                        sum(view_qtydone_stockmoveline.qty_done) as qty_done					
                                                from stock_move	
                                                left join 
                                                    (--Tính tổng số lượng đã nhận của move_id
                                                    select move_id,
                                                            sum(qty_done) as qty_done	
                                                    from stock_move_line
                                                    group by move_id
                                                    ) as view_qtydone_stockmoveline
                                                on view_qtydone_stockmoveline.move_id = stock_move.id
                                                left join stock_picking on stock_move.picking_id = stock_picking.id 
                                                where stock_move.purchase_line_id is not null
                                                group by stock_move.purchase_line_id 
                                                ) as view_ngaynhapkhomuonnhat
                                            on view_slgnhapkho.po_line_id = view_ngaynhapkhomuonnhat.purchase_line_id
                                            left join
                                                (select view_sum.year_dateorder,
                                                        view_sum.month_dateorder,
                                                        view_sum.pa_line_id,
                                                        sum(view_sum.qty_done_pol) as qty_done_prl
                                                from
                                                    (select view_slgnhapkho.year_dateorder,
                                                            view_slgnhapkho.month_dateorder,
                                                            view_slgnhapkho.schedule_date,
                                                            view_slgnhapkho.po_line_id,
                                                            view_slgnhapkho.pa_line_id,
                                                            view_slgnhapkho.product_qty,
                                                            view_slgnhapkho.qty_done_pol,
                                                            current_date as date_report
                                                    from
                                                        (select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                                extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                                purchase_requisition.schedule_date,
                                                                view_soluongnhaptheopo.po_line_id,
                                                                pa_line_po_line_ref.pa_line_id,
                                                                purchase_requisition_line.product_qty,
                                                                view_soluongnhaptheopo.qty_done_pol	
                                                        from
                                                            (select	view_base.purchase_line_id as po_line_id,
                                                                    sum(view_base.qty_done_moveid) as qty_done_pol
                                                            from
                                                                (select view_qtydone_stockmoveline.move_id,
                                                                        view_qtydone_stockmoveline.qty_done_moveid,
                                                                        stock_move.picking_id,
                                                                        stock_move.purchase_line_id 
                                                                from 
                                                                    (--Tính tổng số lượng đã nhận của move_id
                                                                    select  stock_move_line.move_id,
                                                                            sum(stock_move_line.qty_done) as qty_done_moveid	
                                                                    from stock_move_line
                                                                    group by move_id
                                                                    ) as view_qtydone_stockmoveline
                                                                left join stock_move on view_qtydone_stockmoveline.move_id = stock_move.id
                                                                where stock_move.purchase_line_id is not null
                                                                ) as view_base
                                                            left join stock_picking on view_base.picking_id = stock_picking.id 
                                                            left join purchase_order_line on view_base.purchase_line_id = purchase_order_line.id
                                                            group by view_base.purchase_line_id
                                                            ) as view_soluongnhaptheopo
                                                        left join pa_line_po_line_ref on view_soluongnhaptheopo.po_line_id = pa_line_po_line_ref.po_line_id
                                                        left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                                        left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                                        ) as view_slgnhapkho
                                                    left join
                                                        (--Tính ngày nhập kho muộn nhất, tổng số lượng đã nhập của POL
                                                        select 	stock_move.purchase_line_id,
                                                                max(stock_picking.date_done)::date as ngaynhapkhomuonnhat,
                                                                sum(view_qtydone_stockmoveline.qty_done) as qty_done					
                                                        from stock_move	
                                                        left join 
                                                            (--Tính tổng số lượng đã nhận của move_id
                                                            select move_id,
                                                                    sum(qty_done) as qty_done	
                                                            from stock_move_line
                                                            group by move_id
                                                            ) as view_qtydone_stockmoveline
                                                        on view_qtydone_stockmoveline.move_id = stock_move.id
                                                        left join stock_picking on stock_move.picking_id = stock_picking.id 
                                                        where stock_move.purchase_line_id is not null
                                                        group by stock_move.purchase_line_id 
                                                        ) as view_ngaynhapkhomuonnhat
                                                    on view_slgnhapkho.po_line_id = view_ngaynhapkhomuonnhat.purchase_line_id
                                                    ) as view_sum
                                                group by view_sum.year_dateorder, view_sum.month_dateorder, view_sum.pa_line_id
                                                ) as view_total_prl
                                            on view_slgnhapkho.pa_line_id = view_total_prl.pa_line_id
                                            ) as view_abc
                                        group by view_abc.year_dateorder, view_abc.month_dateorder
                                    
                                        union all 
                                        
                                        --Hàng hóa dịch vụ
                                        select  view_abc.year_dateorder,
                                                view_abc.month_dateorder,
                                                count(case when (view_abc.date_report <= view_abc.schedule_date::date) and (view_abc.total_received < view_abc.product_qty) then view_abc.po_line_id end) as ongoing,
                                                count(case when (view_abc.date_report > view_abc.schedule_date::date) and (view_abc.total_received < view_abc.product_qty) then view_abc.po_line_id end) as delay
                                        from
                                            (--Lấy ra các trường ... với điều kiện loại sản phẩm là Dịch vụ, số lượng đã nhận > 0 và sản phẩm khác 'Làm tròn'
                                            select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                    extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                    purchase_requisition_line.id as prl_id,
                                                    purchase_order_line.id as po_line_id,
                                                    purchase_requisition.schedule_date,
                                                    purchase_order_line.x_date_received,
                                                    coalesce(purchase_requisition_line.product_qty,0) as product_qty,
                                                    coalesce(purchase_order_line.qty_received,0) as pol_received,
                                                    coalesce(view_totalreceived.total_received,0) as total_received,
                                                    (coalesce(view_totalreceived.total_received,0) - coalesce(purchase_requisition_line.product_qty,0)) as chenhlech,
                                                    current_date as date_report
                                            from purchase_order_line 
                                            left join product_product on purchase_order_line.product_id = product_product.id 
                                            left join product_template on product_product.product_tmpl_id = product_template.id
                                            left join pa_line_po_line_ref on purchase_order_line.id = pa_line_po_line_ref.po_line_id
                                            left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                            left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                            left join 
                                                (select view_sum.year_dateorder,
                                                        view_sum.month_dateorder,
                                                        view_sum.prl_id,
                                                        sum(view_sum.qty_received) as total_received
                                                from
                                                    (select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                                            extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                                            purchase_requisition_line.id as prl_id,
                                                            purchase_order_line.id as po_line_id,
                                                            purchase_requisition.schedule_date,
                                                            purchase_order_line.x_date_received,
                                                            purchase_requisition_line.product_qty,
                                                            purchase_order_line.qty_received
                                                    from purchase_order_line 
                                                    left join product_product on purchase_order_line.product_id = product_product.id 
                                                    left join product_template on product_product.product_tmpl_id = product_template.id
                                                    left join pa_line_po_line_ref on purchase_order_line.id = pa_line_po_line_ref.po_line_id
                                                    left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                                    left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                                    where 	product_template.x_type = 'service'
                                                            and purchase_order_line.qty_received > 0
                                                            and purchase_order_line.product_id not in (4747)
                                                    ) as view_sum
                                                group by view_sum.year_dateorder, view_sum.month_dateorder, view_sum.prl_id
                                                ) as view_totalreceived
                                            on purchase_requisition_line.id = view_totalreceived.prl_id
                                            where 	product_template.x_type = 'service'
                                                    and purchase_order_line.qty_received > 0
                                                    and purchase_order_line.product_id not in (4747)
                                            ) as view_abc
                                        group by view_abc.year_dateorder, view_abc.month_dateorder
                                        ) as view_hangmucdangxuly
                                    group by view_hangmucdangxuly.year_dateorder, view_hangmucdangxuly.month_dateorder
                                    order by view_hangmucdangxuly.year_dateorder, view_hangmucdangxuly.month_dateorder ) 
                                       SELECT
                                          'Số hạng mục đang xử lý trong thời hạn' AS classifine,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m1} and ptd.year_createdate_pa = '{y1}' ) THEN ongoing ELSE 0 END ) AS jan,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m2} and ptd.year_createdate_pa = '{y2}' ) THEN ongoing ELSE 0 END ) AS feb,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m3} and ptd.year_createdate_pa = '{y3}' ) THEN ongoing ELSE 0 END ) AS mar,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m4} and ptd.year_createdate_pa = '{y4}' ) THEN ongoing ELSE 0 END ) AS apr,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m5} and ptd.year_createdate_pa = '{y5}' ) THEN ongoing ELSE 0 END ) AS may,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m6} and ptd.year_createdate_pa = '{y6}' ) THEN ongoing ELSE 0 END ) AS jun,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m7} and ptd.year_createdate_pa = '{y7}' ) THEN ongoing ELSE 0 END ) AS jul,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m8} and ptd.year_createdate_pa = '{y8}' ) THEN ongoing ELSE 0 END ) AS aug,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m9} and ptd.year_createdate_pa = '{y9}' ) THEN ongoing ELSE 0 END ) AS sep,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m10} and ptd.year_createdate_pa = '{y10}' ) THEN ongoing ELSE 0 END ) AS oct,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m11} and ptd.year_createdate_pa = '{y11}' ) THEN ongoing ELSE 0 END ) AS nov,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m12} and ptd.year_createdate_pa = '{y12}' ) THEN ongoing ELSE 0 END ) AS dev 
                                      FROM
                                          so_hm_ongoing_delay ptd
                                      Union all 
                                      SELECT
                                          'Số hạng mục giao hàng chậm' AS classifine,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m1} and ptd.year_createdate_pa = '{y1}' ) THEN delay ELSE 0 END ) AS jan,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m2} and ptd.year_createdate_pa = '{y2}' ) THEN delay ELSE 0 END ) AS feb,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m3} and ptd.year_createdate_pa = '{y3}' ) THEN delay ELSE 0 END ) AS mar,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m4} and ptd.year_createdate_pa = '{y4}' ) THEN delay ELSE 0 END ) AS apr,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m5} and ptd.year_createdate_pa = '{y5}' ) THEN delay ELSE 0 END ) AS may,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m6} and ptd.year_createdate_pa = '{y6}' ) THEN delay ELSE 0 END ) AS jun,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m7} and ptd.year_createdate_pa = '{y7}' ) THEN delay ELSE 0 END ) AS jul,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m8} and ptd.year_createdate_pa = '{y8}' ) THEN delay ELSE 0 END ) AS aug,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m9} and ptd.year_createdate_pa = '{y9}' ) THEN delay ELSE 0 END ) AS sep,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m10} and ptd.year_createdate_pa = '{y10}' ) THEN delay ELSE 0 END ) AS oct,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m11} and ptd.year_createdate_pa = '{y11}' ) THEN delay ELSE 0 END ) AS nov,
                                          SUM ( CASE WHEN ( ptd.month_createdate_pa = {m12} and ptd.year_createdate_pa = '{y12}' ) THEN delay ELSE 0 END ) AS dev 
                                      FROM
                                          so_hm_ongoing_delay ptd
                                      '''.format(m1=time['m12'].month, y1=time['m12'].year,
                                                 m2=time['m11'].month, y2=time['m11'].year,
                                                 m3=time['m10'].month, y3=time['m10'].year,
                                                 m4=time['m9'].month, y4=time['m9'].year,
                                                 m5=time['m8'].month, y5=time['m8'].year,
                                                 m6=time['m7'].month, y6=time['m7'].year,
                                                 m7=time['m6'].month, y7=time['m6'].year,
                                                 m8=time['m5'].month, y8=time['m5'].year,
                                                 m9=time['m4'].month, y9=time['m4'].year,
                                                 m10=time['m3'].month, y10=time['m3'].year,
                                                 m11=time['m2'].month, y11=time['m2'].year,
                                                 m12=time['m1'].month, y12=time['m1'].year)
        self._cr.execute(sql_ongoing_delay)
        recs = self._cr.dictfetchall()
        for r in recs:
            insert_ongoing_delay = '''INSERT INTO purchase_picking_status (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                                         VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                                     '''.format(key=self.master_key,
                                                                classification=r['classifine'],
                                                                t1=r['jan'],
                                                                t2=r['feb'],
                                                                t3=r['mar'],
                                                                t4=r['apr'],
                                                                t5=r['may'],
                                                                t6=r['jun'],
                                                                t7=r['jul'],
                                                                t8=r['aug'],
                                                                t9=r['sep'],
                                                                t10=r['oct'],
                                                                t11=r['nov'],
                                                                t12=r['dev'], )
            self._cr.execute(insert_ongoing_delay)

    def insert_pending(self,time):
        sql_pending = ''' with so_hm_pending as (
                                select  view_tongsohangmuc.year_dateorder as year_createdate,
                                        view_tongsohangmuc.month_dateorder as month_createdate,
                                        sum(view_tongsohangmuc.sohangmuc) as sohangmuc_vuongmac
                                from
                                    (select purchase_requisition.ordering_date,
                                            extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                            extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                            view_soluonghangmuc.requisition_id,
                                            purchase_requisition.x_state,
                                            view_soluonghangmuc.sohangmuc
                                    from
                                        (select purchase_requisition_line.requisition_id,
                                                count(purchase_requisition_line.id) as sohangmuc
                                        from purchase_requisition_line 
                                        group by purchase_requisition_line.requisition_id 
                                        ) as view_soluonghangmuc
                                        left join purchase_requisition on view_soluonghangmuc.requisition_id = purchase_requisition.id 
                                        where purchase_requisition.x_state = 'pause'
                                    ) as view_tongsohangmuc
                                group by year_dateorder, month_dateorder
                                order by year_dateorder, month_dateorder) 
                            SELECT
                               'Số hạng mục đang vướng mắc' AS classifine,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m1} and ptd.year_createdate = '{y1}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS jan,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m2} and ptd.year_createdate = '{y2}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS feb,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m3} and ptd.year_createdate = '{y3}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS mar,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m4} and ptd.year_createdate = '{y4}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS apr,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m5} and ptd.year_createdate = '{y5}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS may,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m6} and ptd.year_createdate = '{y6}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS jun,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m7} and ptd.year_createdate = '{y7}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS jul,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m8} and ptd.year_createdate = '{y8}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS aug,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m9} and ptd.year_createdate = '{y9}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS sep,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m10} and ptd.year_createdate = '{y10}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS oct,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m11} and ptd.year_createdate = '{y11}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS nov,
                               SUM ( CASE WHEN ( ptd.month_createdate = {m12} and ptd.year_createdate = '{y12}' ) THEN sohangmuc_vuongmac ELSE 0 END ) AS dev 
                           FROM
                               so_hm_pending ptd
                           '''.format(m1=time['m12'].month, y1=time['m12'].year,
                                      m2=time['m11'].month, y2=time['m11'].year,
                                      m3=time['m10'].month, y3=time['m10'].year,
                                      m4=time['m9'].month, y4=time['m9'].year,
                                      m5=time['m8'].month, y5=time['m8'].year,
                                      m6=time['m7'].month, y6=time['m7'].year,
                                      m7=time['m6'].month, y7=time['m6'].year,
                                      m8=time['m5'].month, y8=time['m5'].year,
                                      m9=time['m4'].month, y9=time['m4'].year,
                                      m10=time['m3'].month, y10=time['m3'].year,
                                      m11=time['m2'].month, y11=time['m2'].year,
                                      m12=time['m1'].month, y12=time['m1'].year)
        self._cr.execute(sql_pending)

        recs = self._cr.dictfetchall()
        for r in recs:
            insert_pending = '''INSERT INTO purchase_picking_status (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                              VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                          '''.format(key=self.master_key,
                                                     classification=r['classifine'],
                                                     t1=r['jan'],
                                                     t2=r['feb'],
                                                     t3=r['mar'],
                                                     t4=r['apr'],
                                                     t5=r['may'],
                                                     t6=r['jun'],
                                                     t7=r['jul'],
                                                     t8=r['aug'],
                                                     t9=r['sep'],
                                                     t10=r['oct'],
                                                     t11=r['nov'],
                                                     t12=r['dev'], )
            self._cr.execute(insert_pending)

    def action_report(self):
        time_line = self._get_time_report()
        self._cr.execute(
            "delete from purchase_picking_status where master_key = {key}".format(key=self.master_key))

        # số hạng mục đặt hàng
        self.insert_tong(time_line)
        # số hạng mục hủy
        self.insert_huy(time_line)
        # số hạng mục done và late
        self.insert_done_late(time_line)
        # số hạng mục đã giao chờ chứng từ
        self.insert_waite_license(time_line)
        # số hạng mục ongoing và delay
        self.insert_ongoing_delay(time_line)
        # số hạng mục pending
        self.insert_pending(time_line)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo tình trạng giao hàng',
            'view_mode': 'tree',
            'res_model': 'purchase.picking.status',
            'view_id': self.env.ref('effective_management.purchase_picking_status_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }