
import datetime as dt

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseCompareEffectiveWizards(models.TransientModel):
    _name = "purchase.compare.effective.wizards"
    _description = "Nhập tham số báo cáo so sánh hiệu quả mua hàng"

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
            "delete from purchase_compare_effective where master_key = {key}".format(key=self.master_key))
        #1.Tổng giá trị ngân sách & Tổng giá trị đã mua & Tổng hiệu quả mua hàng
        # Đồng bộ với sheet Efficiency của báo cáo báo giá mua hàng:
        # - Nguồn: purchase_order_line (mỗi PO line đếm 1 lần)
        # - SL: pol.product_qty (số lượng đặt mua)
        # - Filter: po.x_state in ('done','wait_license','to_late')
        #   (trùng với logic sheet Efficiency - chỉ ghi date_received cho các state này)
        sql_total = '''
            with data_total as (
                select extract('year' from pol.x_date_received)::character varying as year_createdate,
                       extract('month' from pol.x_date_received) as month_createdate,
                       sum(pol.product_qty * pol.x_budget_price) as total_dutoan,
                       round(sum(pol.product_qty * pol.price_unit)::numeric, 2) as total_thucte,
                       round((sum(pol.product_qty * pol.x_budget_price) - sum(pol.product_qty * pol.price_unit))::numeric, 2) as hieuquamuahang
                from purchase_order_line pol
                left join purchase_order po on po.id = pol.order_id
                where po.x_state in ('done', 'wait_license', 'to_late')
                  and pol.x_date_received is not null
                group by extract('year' from pol.x_date_received),
                         extract('month' from pol.x_date_received)
                order by extract('year' from pol.x_date_received),
                         extract('month' from pol.x_date_received)
            )
            select * from data_total where year_createdate = '{year}'
        '''.format(year=current_year)
        self._cr.execute(sql_total)
        recs_total = self._cr.dictfetchall()
        if not len(recs_total):
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        data_total = {
            'Tổng giá trị ngân sách': {},
            'Tổng giá trị đã mua': {},
            'Tổng hiệu quả mua hàng': {},
        }
        for line in recs_total:
            key_month = 't'+ str(int(line['month_createdate']))
            data_total['Tổng hiệu quả mua hàng'][key_month] = round(line['hieuquamuahang'])
            data_total['Tổng giá trị đã mua'][key_month] = round(line['total_thucte'])
            data_total['Tổng giá trị ngân sách'][key_month] = round(line['total_dutoan'])
        # --Negotiators: dùng partner.name của purchase_order.user_id (giống cột V "nguoi_dam_phan" trong sheet Efficiency)
        sql_dp = f'''
            with data_dp as (
                select extract('year' from pol.x_date_received)::character varying as year_createdate,
                       extract('month' from pol.x_date_received) as month_createdate,
                       coalesce(partner.name, 'Others') as negotiators_index,
                       (sum(pol.product_qty * pol.x_budget_price) - sum(pol.product_qty * pol.price_unit)) as hieuquamuahang
                from purchase_order_line pol
                left join purchase_order po on po.id = pol.order_id
                left join res_users users on users.id = po.user_id
                left join res_partner partner on partner.id = users.partner_id
                where po.x_state in ('done', 'wait_license', 'to_late')
                  and pol.x_date_received is not null
                group by extract('year' from pol.x_date_received),
                         extract('month' from pol.x_date_received),
                         coalesce(partner.name, 'Others')
                order by extract('year' from pol.x_date_received),
                         extract('month' from pol.x_date_received)
            )
            select * from data_dp where year_createdate = '{current_year}'
        '''
        self._cr.execute(sql_dp)
        recs_dp = self._cr.dictfetchall()
        data_dp ={}
        for line in recs_dp:
            key_month = 't' + str(int(line['month_createdate']))
            if line['negotiators_index'] not in data_dp:
                data_dp[line['negotiators_index']] = {key_month: round(line['hieuquamuahang'])}
            else:
                data_dp[line['negotiators_index']][key_month] = round(line['hieuquamuahang'])
        if 'Others' in data_dp:
            data_others = data_dp.pop('Others')
            data_dp['Others'] = data_others


        #--Estimators: dùng partner.name của sale_order.solution_maker (theo chuỗi PO → PA → project → sale_order)
        # Lưu ý: một PO line có thể map nhiều PA line → estimator có thể bị nhân lên (giữ nguyên hành vi cũ)
        sql_etimator = f'''
            with data_estimator as (
                select extract('year' from pol.x_date_received)::character varying as year_createdate,
                       extract('month' from pol.x_date_received) as month_createdate,
                       coalesce(partner_est.name, 'Others') as estimators_index,
                       (sum(pol.product_qty * pol.x_budget_price) - sum(pol.product_qty * pol.price_unit)) as hieuquamuahang
                from purchase_order_line pol
                left join purchase_order po on po.id = pol.order_id
                left join pa_line_po_line_ref ref on ref.po_line_id = pol.id
                left join purchase_requisition_line prl on prl.id = ref.pa_line_id
                left join purchase_requisition pr on pr.id = prl.requisition_id
                left join project_project proj on proj.id = pr.x_code_project_id
                left join sale_order so on so.id = proj.x_order_id
                left join res_users users_est on users_est.id = so.solution_maker
                left join res_partner partner_est on partner_est.id = users_est.partner_id
                where po.x_state in ('done', 'wait_license', 'to_late')
                  and pol.x_date_received is not null
                group by extract('year' from pol.x_date_received),
                         extract('month' from pol.x_date_received),
                         coalesce(partner_est.name, 'Others')
                order by extract('year' from pol.x_date_received),
                         extract('month' from pol.x_date_received)
            )
            select * from data_estimator where year_createdate = '{current_year}'
        '''
        self._cr.execute(sql_etimator)
        recs_estimator = self._cr.dictfetchall()
        data_estimator = {}
        for line in recs_estimator:
            key_month = 't' + str(int(line['month_createdate']))
            if line['estimators_index'] not in data_estimator:
                data_estimator[line['estimators_index']] = {key_month: round(line['hieuquamuahang'])}
            else:
                data_estimator[line['estimators_index']][key_month] = round(line['hieuquamuahang'])

        if 'Others' in data_estimator:
            data_others = data_estimator.pop('Others')
            data_estimator['Others'] = data_others

        for key,value in data_total.items():
            insert = '''INSERT INTO purchase_compare_effective (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
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
                                          t12=value.get('t12') or 0,)
            self._cr.execute(insert)
        insert_dp = '''INSERT INTO purchase_compare_effective (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                           VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                       '''.format(key=self.master_key,
                                                  classification='Người đàm phán',
                                                  t1= 0,
                                                  t2= 0,
                                                  t3=0,
                                                  t4=0,
                                                  t5= 0,
                                                  t6= 0,
                                                  t7=0,
                                                  t8= 0,
                                                  t9= 0,
                                                  t10= 0,
                                                  t11=0,
                                                  t12= 0, )
        self._cr.execute(insert_dp)
        for key,value in data_dp.items():
            insert = '''INSERT INTO purchase_compare_effective (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                               VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                           '''.format(key=self.master_key,
                                                      classification='......'+key,
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
        insert_du_toan = '''INSERT INTO purchase_compare_effective (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                                  VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                              '''.format(key=self.master_key,
                                                         classification='Người lập dự toán',
                                                         t1=0,
                                                         t2=0,
                                                         t3=0,
                                                         t4=0,
                                                         t5=0,
                                                         t6=0,
                                                         t7=0,
                                                         t8=0,
                                                         t9=0,
                                                         t10=0,
                                                         t11=0,
                                                         t12=0, )
        self._cr.execute(insert_du_toan)
        for key,value in data_estimator.items():
            insert = '''INSERT INTO purchase_compare_effective (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                              VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                          '''.format(key=self.master_key,
                                                     classification='......'+key,
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
            'name': 'Báo cáo hiệu quả mua hàng',
            'view_mode': 'tree',
            'res_model': 'purchase.compare.effective',
            'context' : {'year': current_year},
            'view_id': self.env.ref('effective_management.purchase_compare_effective_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }