# -*- coding: utf-8 -*-
import datetime as dt

from odoo import api, fields, models, _
from odoo.http import request


class EmployeeDamageValuePopup(models.Model):
    _name = 'employee.damage.value.popup'

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

    def action_report_stock(self):
        current_year = self.year
        self._cr.execute(
            "delete from employee_damage_value_report where master_key = {key}".format(key=self.master_key))
        sql = '''
                 SELECT
                     ru.login,
                     rp.name,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date < '{year}-01-01')	then sml.qty_done * svl.unit_cost ELSE 0 END) as amount_before,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-01-01' and '{year}-01-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as jan,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date >= '{year}-02-01' and sp.date_done ::date < '{year}-03-01')	then sml.qty_done * svl.unit_cost ELSE 0 END) as feb,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-03-01' and '{year}-03-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as mar,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-04-01' and '{year}-04-30')	then sml.qty_done * svl.unit_cost ELSE 0 END) as apr,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-05-01' and '{year}-05-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as may,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-06-01' and '{year}-06-30')	then sml.qty_done * svl.unit_cost ELSE 0 END) as jun,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-07-01' and '{year}-07-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as jul,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-08-01' and '{year}-08-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as aug,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-09-01' and '{year}-09-30')	then sml.qty_done * svl.unit_cost ELSE 0 END) as sep,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-10-01' and '{year}-10-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as oct,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-11-01' and '{year}-11-30')	then sml.qty_done * svl.unit_cost ELSE 0 END) as nov,
                     sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-12-01' and '{year}-12-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as dec,
                     case when ru.active = 't' then ' ' else 'Nghỉ việc' end as user_state
                 FROM stock_move sm
                     LEFT JOIN stock_move_line sml on sm.id = sml.move_id
                     LEFT JOIN stock_picking sp on sml.picking_id = sp.id
                     LEFT JOIN res_users ru on sp.x_receiver_id = ru.id or sp.x_payer_id = ru.id
                     INNER JOIN res_partner rp on ru.partner_id = rp.id
                     LEFT JOIN product_product pp on sml.product_id = pp.id
                     LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
                     left join stock_valuation_layer svl on svl.stock_move_id = sm.id
                 WHERE sp.state = 'done'
                     and sp.picking_type_id in (SELECT id FROM stock_picking_type WHERE x_type in ('type_7','type_6'))
                     and sp.location_dest_id in (SELECT id  from stock_location WHERE x_name = 'Kho hàng hỏng, hủy')
                     and pt.x_type = 'product'
                     and sm.id not in (SELECT origin_returned_move_id FROM stock_move WHERE origin_returned_move_id is not null)
                     and  pt.x_product_type = 'tools'
                 GROUP BY  ru.id,rp.name
             '''.format(year=current_year)
        # print(sql)
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()
        x = 1
        for r in recs:
            insert = '''INSERT INTO employee_damage_value_report (master_key, index , login,name,amount_bf,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,remark)
                            VALUES ({key},{index},'{login}','{name}',{amount_bf},{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},'{remark}')
                        '''.format(key=self.master_key,
                                   index=x,
                                   login=r['login'],
                                   name=r['name'],
                                   amount_bf=r['amount_before'] or 0.0,
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
                                   t12=r['dec'],
                                   remark=r['user_state'] or 'Null')
            self._cr.execute(insert)
            x += 1

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo giá trị tổn thất liên quan tới nhân viên',
            'view_mode': 'tree',
            'res_model': 'employee.damage.value.report',
            'view_id': self.env.ref('xstock.employee_damage_value_report_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'current',

        }
