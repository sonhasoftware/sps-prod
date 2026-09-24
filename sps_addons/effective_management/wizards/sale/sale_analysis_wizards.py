
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAnalysisWizards(models.TransientModel):
    _name = "sale.analysis.wizards"
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
            "delete from sale_analysis where master_key = {key}".format(key=self.master_key))
        sql = f'''
                    select  view_base.year_orderdate,
                            view_base.month_orderdate,
                            sum(view_base.amount_untaxed) as total_amountuntaxed1,
                            (sum(case when view_base.project_type = 'operation' then view_base.amount_untaxed else 0 end) + sum(case when view_base.project_type = 'maintainance' then view_base.amount_untaxed else 0 end) + sum(case when view_base.project_type = 'service' then view_base.amount_untaxed else 0 end)) as total_amountuntaxed2,
                            sum(case when view_base.project_type = 'operation' then view_base.amount_untaxed else 0 end) as fm_amountuntaxed,
                            sum(case when view_base.project_type = 'maintainance' then view_base.amount_untaxed else 0 end) as m_amountuntaxed,
                            sum(case when view_base.project_type = 'service' then view_base.amount_untaxed else 0 end) as s_amountuntaxed,
                            sum(view_base.overheadcost_value) as overheadcost_value,
                            (case when sum(view_base.amount_untaxed)<>0 then (sum(view_base.overheadcost_value)/sum(view_base.amount_untaxed)*100) else 0 end) as overheadcost_percent,
                            sum(view_base.profit_after_tax) as profitaftertax_value,
                            (case when sum(view_base.amount_untaxed)<>0 then (sum(view_base.profit_after_tax)/sum(view_base.amount_untaxed)*100) else 0 end) as profitaftertax_percent
                    from
                        (select extract ('year' from sale_order.date_order):: character varying as year_orderdate,
                                extract ('month' from sale_order.date_order) as month_orderdate,
                                sale_order.user_id as key_account,
                                sale_order.solution_maker,
                                sale_order.id as so_id,
                                sale_order.date_order,
                                sale_order.state as order_state,
                                sale_order.project_type,
                                sale_order.overhead_cost,
                                sale_order.amount_untaxed,
                                ((sale_order.overhead_cost * sale_order.amount_untaxed)/100) as overheadcost_value,
                                sale_order.profit_after_tax 
                        from sale_order
                        where sale_order.state in ('sale', 'done')
                        ) as view_base
                    where year_orderdate = '{current_year}'
                    group by view_base.year_orderdate, view_base.month_orderdate
                    order by view_base.year_orderdate, view_base.month_orderdate'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        # tạo ra data cuối
        if len(recs_last)<0:
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        # gom nhóm theo form báo cáo
        last_data={
            'Tổng giá trị báo giá được ký': {},
            'Quản lý vận hành': {},
            'Bảo trì': {},
            'Dịch vụ': {},
            'Chi phí GT và QL': {},
            'Chi phí GT và QL (%)': {},
            'Lợi nhuận': {},
            'Lợi nhuận (%)': {},
        }
        for line in recs_last:
            key_month = 't'+ str(int(line['month_orderdate']))
            last_data['Tổng giá trị báo giá được ký'][key_month] = round(line.get('total_amountuntaxed2') or 0)
            last_data['Quản lý vận hành'][key_month] = round(line.get('fm_amountuntaxed')or 0)
            last_data['Bảo trì'][key_month] = round(line.get('m_amountuntaxed')or 0)
            last_data['Dịch vụ'][key_month] = round(line.get('s_amountuntaxed')or 0)
            last_data['Chi phí GT và QL'][key_month] = round(line.get('overheadcost_value')or 0)
            last_data['Chi phí GT và QL (%)'][key_month] = round(line.get('overheadcost_percent'),2)or 0
            last_data['Lợi nhuận'][key_month] = round(line.get('profitaftertax_value')or 0)
            last_data['Lợi nhuận (%)'][key_month] = round(line.get('profitaftertax_percent'),2)or 0
        # đổ dữ liệu
        for key,value in last_data.items():
            insert = '''INSERT INTO sale_analysis (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
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
            'name': 'Báo cáo phân tích kinh doanh',
            'view_mode': 'tree',
            'res_model': "sale.analysis",
            'context' : {'year': current_year},
            'view_id': self.env.ref('effective_management.sale_analysis_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }