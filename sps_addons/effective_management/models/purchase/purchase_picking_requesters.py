# -*- coding: utf-8 -*-


from odoo import api, fields, models,tools


class PurchasePickingRequesters(models.Model):
    _name = 'purchase.picking.requesters'
    _description = 'Báo cáo giao hàng theo người phụ trách dự án'
    _auto = False

    requestor = fields.Char('Người phụ trách')
    on_going = fields.Integer('Trong thời gian')
    pending = fields.Integer('Vướng mắc')
    delay = fields.Integer('Chậm giao hàng')

    @api.model
    def init(self):
        """ Event main report """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""CREATE VIEW {table} AS (
                    select 	
                            row_number() OVER () AS id,
                            view_tong.name_requestor as requestor,
                            sum(view_tong.hangmuc_pending) as pending,
                            sum(view_tong.hangmuc_ongoing) as on_going,
                            sum(view_tong.hangmuc_delay) as delay
                    from
                        (--Pending:
                        select  view_tongsohangmuc.name_requestor,
                                sum(view_tongsohangmuc.sohangmuc) as hangmuc_pending,
                                0 as hangmuc_ongoing,
                                0 as hangmuc_delay
                        from
                            (select purchase_requisition.create_date,
                                    view_soluonghangmuc.requisition_id,
                                    purchase_requisition.x_state,
                                    view_soluonghangmuc.sohangmuc,
                                    purchase_requisition.user_id,
                                    hr_employee.name as name_requestor
                            from
                                (select purchase_requisition_line.requisition_id,
                                        count(purchase_requisition_line.id) as sohangmuc
                                from purchase_requisition_line 
                                group by purchase_requisition_line.requisition_id 
                                ) as view_soluonghangmuc
                            left join purchase_requisition on view_soluonghangmuc.requisition_id = purchase_requisition.id 
                            left join res_users on purchase_requisition.user_id = res_users.id 
                            left join hr_employee on res_users.id = hr_employee.user_id 
                            where purchase_requisition.x_state = 'pause'
                            ) as view_tongsohangmuc
                        group by view_tongsohangmuc.name_requestor
                    
                        union all
                    
                        --Ongoing & Delay:
                        select 	view_hangmucdangxuly.name_requestor,
                                0 as hangmuc_pending,
                                sum(view_hangmucdangxuly.ongoing) as hangmuc_ongoing,
                                sum(view_hangmucdangxuly.delay) as hangmuc_delay
                        from
                            (--Hàng hóa lưu kho
                            select  view_abc.name_requestor,
                                    count(case when (view_abc.date_report <= view_abc.schedule_date::date) and (view_abc.qty_done_prl < view_abc.product_qty) then view_abc.po_line_id end) as ongoing,
                                    count(case when (view_abc.date_report > view_abc.schedule_date::date) and (view_abc.qty_done_prl < view_abc.product_qty) then view_abc.po_line_id end) as delay
                            from
                                (select view_slgnhapkho.year_dateorder,
                                        view_slgnhapkho.month_dateorder,
                                        view_slgnhapkho.name_requestor,
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
                                            purchase_requisition.user_id,
                                            hr_employee.name as name_requestor,
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
                                    left join res_users on purchase_requisition.user_id = res_users.id
                                    left join hr_employee on res_users.id = hr_employee.user_id 
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
                            group by view_abc.name_requestor
                        
                            union all 
                            
                            --Hàng hóa dịch vụ
                            select  view_abc.name_requestor,
                                    count(case when (view_abc.date_report <= view_abc.schedule_date::date) and (view_abc.total_received < view_abc.product_qty) then view_abc.po_line_id end) as ongoing,
                                    count(case when (view_abc.date_report > view_abc.schedule_date::date) and (view_abc.total_received < view_abc.product_qty) then view_abc.po_line_id end) as delay
                            from
                                (--Lấy ra các trường ... với điều kiện loại sản phẩm là Dịch vụ, số lượng đã nhận > 0 và sản phẩm khác 'Làm tròn'
                                select  extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                        extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                        purchase_requisition.user_id,
                                        hr_employee.name as name_requestor,
                                        purchase_requisition.schedule_date,
                                        purchase_requisition_line.id as prl_id,
                                        purchase_order_line.id as po_line_id,
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
                                left join res_users on purchase_requisition.user_id = res_users.id 
                                left join hr_employee on res_users.id = hr_employee.user_id 
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
                            group by view_abc.name_requestor
                            ) as view_hangmucdangxuly
                        group by view_hangmucdangxuly.name_requestor
                        ) as view_tong
                    where name_requestor is not null
                    group by view_tong.name_requestor
                    order by view_tong.name_requestor
                         )""".format(table=self._table))
