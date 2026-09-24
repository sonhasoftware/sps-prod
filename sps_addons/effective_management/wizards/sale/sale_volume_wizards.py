
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleVolumeWizards(models.TransientModel):
    _name = "sale.volume.wizards"
    _description = "Nhập tham số báo cáo doanh số kì mới"

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
            "delete from sale_volume where master_key = {key}".format(key=self.master_key))
        sql = f''' select 	view_so.year_orderdate,
                            view_so.month_orderdate,
                            view_so.so_total,
                            sale_target.sale_target,
                            view_so.so_fm,
                            view_so.so_ms
                    from
                        (select view_base.year_orderdate,
                                view_base.month_orderdate,
                                (sum(case when view_base.project_type = 'operation' then view_base.amount_untaxed else 0 end) + sum(case when (view_base.project_type = 'maintainance' or view_base.project_type = 'service')then view_base.amount_untaxed else 0 end)) as so_total,
                                sum(case when view_base.project_type = 'operation' then view_base.amount_untaxed else 0 end) as so_fm,
                                sum(case when (view_base.project_type = 'maintainance' or view_base.project_type = 'service')then view_base.amount_untaxed else 0 end) as so_ms
                        from
                            (select extract ('year' from sale_order.date_order) as year_orderdate,
                                    extract ('month' from sale_order.date_order):: character varying as month_orderdate,
                                    sale_order.id as so_id,
                                    sale_order.date_order,
                                    sale_order.state as order_state,
                                    sale_order.project_type,
                                    sale_order.amount_untaxed
                            from sale_order
                            where sale_order.state in ('sale','done')
                            ) as view_base
                        group by view_base.year_orderdate, view_base.month_orderdate
                        ) as view_so
                    left join sale_target on view_so.year_orderdate = sale_target.target_year and view_so.month_orderdate = sale_target.target_month
                    where year_orderdate  = {current_year} 
                    order by month_orderdate'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        # tạo ra data cuối
        if len(recs_last)<0:
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        # gom nhóm theo form báo cáo
        last_data={
            'Tổng doanh số mục tiêu': {},
            'Giá trị báo giá đã ký': {},
            'Giá trị báo giá quản lý vận hành đã ký': {},
            'Giá trị báo giá bảo trì & dịch vụ đã ký': {},
        }
        for line in recs_last:
            key_month = 't'+ str(int(line['month_orderdate']))
            last_data['Tổng doanh số mục tiêu'][key_month] = round(line.get('sale_target') or 0)
            last_data['Giá trị báo giá đã ký'][key_month] = round(line.get('so_total')or 0)
            last_data['Giá trị báo giá quản lý vận hành đã ký'][key_month] = round(line.get('so_fm')or 0)
            last_data['Giá trị báo giá bảo trì & dịch vụ đã ký'][key_month] = round(line.get('so_ms')or 0)
        # đổ dữ liệu
        for key,value in last_data.items():
            insert = '''INSERT INTO sale_volume (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
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
            'name': 'Báo cáo doanh số kì mới',
            'view_mode': 'tree',
            'res_model': "sale.volume",
            'context' : {'year': current_year},
            'view_id': self.env.ref('effective_management.sale_volume_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }