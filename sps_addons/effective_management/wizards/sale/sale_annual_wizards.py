
import datetime as dt

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class SaleAnnualWizards(models.TransientModel):
    _name = "sale.annual.wizards"
    _description = "Nhập tham số báo cáo "

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
    year = fields.Integer(
        string='Năm bắt đầu',
        default=lambda self: datetime.now().year - 10
    )

    def _get_time_report(self):
        time_now = datetime.now()
        vals = {}
        start_year = self.year
        for i in range(0,10):
            vals.update({'m{}'.format(i + 1): start_year + i})
        return vals

    def tang_truong(self,data):
        new_data = {}
        for key, value in data.items():
            if key != 'classifine':
                new_data[key] = value
        growth_data = {'classifine' : 'Tăng trưởng doanh số (%)'}
        for key in new_data:
            if key == 'y1':
                growth_data[key] = 0.0  # Không có dữ liệu trước đó nên tăng trưởng là 0.
            else:
                previous_value = new_data['y' + str(int(key[1:]) - 1)]  # Giá trị trước đó
                current_value = new_data[key]  # Giá trị hiện tại
                growth = ((current_value - previous_value) / previous_value)*100 if previous_value != 0 and current_value !=0 else 0
                growth_data[key] = growth
        return growth_data

    def insert_muc_tieu(self,time):
        sql = '''SELECT
                       'Doanh số mục tiêu' AS classifine,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y1}'  ) THEN sale_target  ELSE 0 END ) AS y1,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y2}'  ) THEN sale_target ELSE 0 END ) AS y2,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y3}'  ) THEN sale_target ELSE 0 END ) AS y3,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y4}') THEN sale_target ELSE 0 END ) AS y4,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y5}' ) THEN sale_target ELSE 0 END ) AS y5,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y6}' ) THEN sale_target ELSE 0 END ) AS y6,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y7}' ) THEN sale_target ELSE 0 END ) AS y7,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y8}' ) THEN sale_target ELSE 0 END ) AS y8,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y9}'  ) THEN sale_target ELSE 0 END ) AS y9,
                       SUM ( CASE WHEN ( CAST(target_year  AS VARCHAR) = '{y10}' ) THEN sale_target ELSE 0 END ) AS y10
                    FROM
                           sale_target st 
                        '''.format( y1=time['m1'],
                                    y2=time['m2'],
                                    y3=time['m3'],
                                    y4=time['m4'],
                                    y5=time['m5'],
                                    y6=time['m6'],
                                    y7=time['m7'],
                                    y8=time['m8'],
                                    y9=time['m9'],
                                    y10=time['m10'] )
        self._cr.execute(sql)

        recs = self._cr.dictfetchall()
        for r in recs:
            insert = '''INSERT INTO sale_annual (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10)
                                           VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10})
                                       '''.format(key=self.master_key,
                                                  classification=r['classifine'],
                                                  t1=r['y1'],
                                                  t2=r['y2'],
                                                  t3=r['y3'],
                                                  t4=r['y4'],
                                                  t5=r['y5'],
                                                  t6=r['y6'],
                                                  t7=r['y7'],
                                                  t8=r['y8'],
                                                  t9=r['y9'],
                                                  t10=r['y10'] )
            self._cr.execute(insert)

    def insert_doanh_so(self,time):
        sql_doanh_so = ''' with data_doanh_so as (
                            select  view_base.year_orderdate as year_dateend,
                                    sum(view_base.amount_untaxed) as doanhso
                            from
                                (select extract ('year' from sale_order.date_order)::character varying as year_orderdate,
                                        extract ('month' from sale_order.date_order) as month_orderdate,
                                        sale_order.id as so_id,
                                        sale_order.date_order,
                                        sale_order.state as order_state,
                                        sale_order.project_type,
                                        sale_order.overhead_cost,
                                        sale_order.amount_untaxed,
                                        ((sale_order.overhead_cost * sale_order.amount_untaxed)/100) as overheadcost_value,
                                        sale_order.profit_after_tax 
                                from sale_order
                                left join res_users as res_users_key on sale_order.user_id = res_users_key.id
                                left join hr_employee as hr_employee_key on sale_order.user_id = hr_employee_key.user_id
                                left join res_users as res_users_sol on sale_order.solution_maker = res_users_sol.id
                                left join hr_employee as hr_employee_sol on sale_order.solution_maker = hr_employee_sol.user_id
                                where sale_order.state = 'sale'
                                ) as view_base
                            group by view_base.year_orderdate
                            order by view_base.year_orderdate) 
                            SELECT
                               'Tổng doanh số đạt được' AS classifine,
                               SUM (  CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y1}' ) THEN doanhso ELSE 0 END ) AS y1,
                               SUM (  CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y2}' ) THEN doanhso ELSE 0 END ) AS y2,
                               SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y3}' ) THEN doanhso ELSE 0 END ) AS y3,
                               SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y4}' ) THEN doanhso ELSE 0 END ) AS y4,
                               SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y5}' ) THEN doanhso ELSE 0 END ) AS y5,
                               SUM (  CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y6}' ) THEN doanhso ELSE 0 END ) AS y6,
                               SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y7}' ) THEN doanhso ELSE 0 END ) AS y7,
                               SUM (  CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y8}' ) THEN doanhso ELSE 0 END ) AS y8,
                               SUM (  CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y9}' ) THEN doanhso ELSE 0 END ) AS y9,
                               SUM (  CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y10}' ) THEN doanhso ELSE 0 END ) AS y10
                           FROM
                               data_doanh_so
                           '''.format( y1=time['m1'],
                                    y2=time['m2'],
                                    y3=time['m3'],
                                    y4=time['m4'],
                                    y5=time['m5'],
                                    y6=time['m6'],
                                    y7=time['m7'],
                                    y8=time['m8'],
                                    y9=time['m9'],
                                    y10=time['m10'] )
        self._cr.execute(sql_doanh_so)
        recs = self._cr.dictfetchall()
        data = recs[0]
        ty_le = self.tang_truong(data)
        for r in recs:
            insert = '''INSERT INTO sale_annual (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10)
                                           VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10})
                                       '''.format(key=self.master_key,
                                                  classification=r['classifine'],
                                                  t1=r['y1'],
                                                  t2=r['y2'],
                                                  t3=r['y3'],
                                                  t4=r['y4'],
                                                  t5=r['y5'],
                                                  t6=r['y6'],
                                                  t7=r['y7'],
                                                  t8=r['y8'],
                                                  t9=r['y9'],
                                                  t10=r['y10'])
            self._cr.execute(insert)
        insert_ty_le = '''INSERT INTO sale_annual (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10)
                                                       VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10})
                                                   '''.format(key=self.master_key,
                                                              classification=ty_le['classifine'],
                                                              t1=ty_le['y1'],
                                                              t2=ty_le['y2'],
                                                              t3=ty_le['y3'],
                                                              t4=ty_le['y4'],
                                                              t5=ty_le['y5'],
                                                              t6=ty_le['y6'],
                                                              t7=ty_le['y7'],
                                                              t8=ty_le['y8'],
                                                              t9=ty_le['y9'],
                                                              t10=ty_le['y10'])
        self._cr.execute(insert_ty_le)

    def insert_loi_nhuan(self,time):
        sql_loi_nhuan = ''' with data_loi_nhuan as (
                                        select  view_base.year_orderdate as year_dateend,
                                                sum(view_base.profit_after_tax) as lnst,
                                                round((sum(view_base.profit_after_tax)/sum(view_base.amount_untaxed))*100::numeric, 2) as tyleln	
                                        from
                                            (select extract ('year' from sale_order.date_order)::character varying as year_orderdate,
                                                    extract ('month' from sale_order.date_order) as month_orderdate,
                                                    sale_order.id as so_id,
                                                    sale_order.date_order,
                                                    sale_order.state as order_state,
                                                    sale_order.project_type,
                                                    sale_order.overhead_cost,
                                                    sale_order.amount_untaxed,
                                                    ((sale_order.overhead_cost * sale_order.amount_untaxed)/100) as overheadcost_value,
                                                    sale_order.profit_after_tax 
                                            from sale_order
                                            left join res_users as res_users_key on sale_order.user_id = res_users_key.id
                                            left join hr_employee as hr_employee_key on sale_order.user_id = hr_employee_key.user_id
                                            left join res_users as res_users_sol on sale_order.solution_maker = res_users_sol.id
                                            left join hr_employee as hr_employee_sol on sale_order.solution_maker = hr_employee_sol.user_id
                                            where sale_order.state = 'sale'
                                            ) as view_base
                                        group by view_base.year_orderdate
                                        order by view_base.year_orderdate) 
                                    SELECT
                                       'Lợi nhuận sau thuế thu nhập doanh nghiệp' AS classifine,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y1}' ) THEN lnst ELSE 0 END ) AS y1,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y2}' ) THEN lnst ELSE 0 END ) AS y2,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y3}' ) THEN lnst ELSE 0 END ) AS y3,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y4}' ) THEN lnst ELSE 0 END ) AS y4,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y5}' ) THEN lnst ELSE 0 END ) AS y5,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y6}' ) THEN lnst ELSE 0 END ) AS y6,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y7}' ) THEN lnst ELSE 0 END ) AS y7,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y8}' ) THEN lnst ELSE 0 END ) AS y8,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y9}' ) THEN lnst ELSE 0 END ) AS y9,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y10}' ) THEN lnst ELSE 0 END ) AS y10
                                    FROM
                                       data_loi_nhuan
                                   Union all 
                                   SELECT
                                       'Tỉ lệ lợi nhuận (%)' AS classifine,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y1}' ) THEN tyleln ELSE 0 END ) AS y1,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y2}' ) THEN tyleln ELSE 0 END ) AS y2,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y3}' ) THEN tyleln ELSE 0 END ) AS y3,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y4}' ) THEN tyleln ELSE 0 END ) AS y4,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y5}' ) THEN tyleln ELSE 0 END ) AS y5,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y6}' ) THEN tyleln ELSE 0 END ) AS y6,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y7}' ) THEN tyleln ELSE 0 END ) AS y7,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y8}' ) THEN tyleln ELSE 0 END ) AS y8,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y9}' ) THEN tyleln ELSE 0 END ) AS y9,
                                       SUM ( CASE WHEN ( CAST(year_dateend  AS VARCHAR) = '{y10}' ) THEN tyleln ELSE 0 END ) AS y10
                                   FROM
                                       data_loi_nhuan
                                   '''.format( y1=time['m1'],
                                    y2=time['m2'],
                                    y3=time['m3'],
                                    y4=time['m4'],
                                    y5=time['m5'],
                                    y6=time['m6'],
                                    y7=time['m7'],
                                    y8=time['m8'],
                                    y9=time['m9'],
                                    y10=time['m10'] )
        self._cr.execute(sql_loi_nhuan)
        recs = self._cr.dictfetchall()
        for r in recs:
            insert_loi_nhuan = '''INSERT INTO sale_annual (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10)
                                           VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10})
                                       '''.format(key=self.master_key,
                                                  classification=r['classifine'],
                                                  t1=r['y1'],
                                                  t2=r['y2'],
                                                  t3=r['y3'],
                                                  t4=r['y4'],
                                                  t5=r['y5'],
                                                  t6=r['y6'],
                                                  t7=r['y7'],
                                                  t8=r['y8'],
                                                  t9=r['y9'],
                                                  t10=r['y10'])
            self._cr.execute(insert_loi_nhuan)

    def action_report(self):
        time_line = self._get_time_report()
        self._cr.execute(
            "delete from sale_annual where master_key = {key}".format(key=self.master_key))

        # doanh số mục tiêu
        self.insert_muc_tieu(time_line)
        # Doanh số đạt đc
        self.insert_doanh_so(time_line)
        # Lợi nhuận và tỷ lệ
        self.insert_loi_nhuan(time_line)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo doanh số năm',
            'view_mode': 'tree',
            'res_model': 'sale.annual',
            'view_id': self.env.ref('effective_management.sale_annual_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',
            'context': {'year': self.year}
        }