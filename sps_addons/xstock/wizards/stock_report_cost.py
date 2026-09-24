# -*- coding: utf-8 -*-

from datetime import timedelta, date, datetime
import base64

import os
from io import BytesIO
import openpyxl
from openpyxl.styles import NamedStyle, Font, Border, Side
from openpyxl.writer.excel import save_virtual_workbook
from odoo import api, fields, models


class StockReportCost(models.TransientModel):
    _name = 'stock.report.cost'
    _description = "Báo cáo chi phí nhân viên về đồng phục"

    year = fields.Char('Năm', default=int(date.today().year))
    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)

    def action_report_stock_cost(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(
            dir_path + '%s..%stemplates%sstock_report_cost.xlsx' % (os.sep, os.sep, os.sep))
        ws = wb['Sheet1']

        highlight = NamedStyle(name="highlight")
        highlight.font = Font(size=13)
        bd1 = Side(style='thin', color="000000")
        highlight.border = Border(left=bd1, top=bd1, right=bd1, bottom=bd1)

        highlight1 = NamedStyle(name='datetime', number_format='DD/MM/YYYY')
        highlight1.font = Font(size=13)
        bd1 = Side(style='thin', color="000000")
        highlight1.border = Border(left=bd1, top=bd1, right=bd1, bottom=bd1)
        self._cr.execute(
            "delete from stock_report_value_cost where master_key = {key}".format(key=self.master_key))
        sql = '''
            SELECT
                'a' as title,
                'New' as login,
                'Nhập mới' as name,
                sum(case when spt.x_type ='type_1' and sm.date::date < '{year}-01-01' then sml.qty_done * svl.unit_cost else 0 end) as before,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-01-01' and '{year}-01-31' then sml.qty_done * svl.unit_cost else 0 end) as t1,
                sum(case when spt.x_type ='type_1' and sm.date::date >= '{year}-02-01' and sm.date::date < '{year}-03-01' then sml.qty_done * svl.unit_cost else 0 end) as t2,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-03-01' and '{year}-03-31' then sml.qty_done * svl.unit_cost else 0 end) as t3,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-04-01' and '{year}-04-30' then sml.qty_done * svl.unit_cost else 0 end) as t4,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-05-01' and '{year}-05-31' then sml.qty_done * svl.unit_cost else 0 end) as t5,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-06-01' and '{year}-06-30' then sml.qty_done * svl.unit_cost else 0 end) as t6,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-07-01' and '{year}-07-31' then sml.qty_done * svl.unit_cost else 0 end) as t7,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-08-01' and '{year}-08-31' then sml.qty_done * svl.unit_cost else 0 end) as t8,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-09-01' and '{year}-09-30' then sml.qty_done * svl.unit_cost else 0 end) as t9,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-10-01' and '{year}-10-31' then sml.qty_done * svl.unit_cost else 0 end) as t10,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-11-01' and '{year}-11-30' then sml.qty_done * svl.unit_cost else 0 end) as t11,
                sum(case when spt.x_type ='type_1' and sm.date::date between '{year}-12-01' and '{year}-12-31' then sml.qty_done * svl.unit_cost else 0 end) as t12,
                sum(case when spt.x_type ='type_1' and sm.date::date < '{year}-12-31' then sml.qty_done * svl.unit_cost else 0 end) as after
                FROM product_template pt
                LEFT JOIN uom_uom uu  ON uu.id = pt.uom_id
                                LEFT JOIN product_product pp  ON pt.id = pp.product_tmpl_id
                                LEFT JOIN stock_move_line sml ON pp.id = sml.product_id
                                LEFT JOIN stock_picking sp  ON sml.picking_id = sp.id
                                LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                                LEFT JOIN stock_move sm ON sm.id = sml.move_id
                                left join stock_valuation_layer svl on svl.stock_move_id = sm.id 
                                left join stock_location sl1 on sml.location_id=sl1.id
                                left join stock_location sl2 on sml.location_dest_id=sl2.id
                                left join ir_property ip on ip.name = 'standard_price' and substring(ip.res_id,17,100)::int = pp.id
                WHERE pt.x_product_type = 'supplies'
                and pt.x_type = 'product' 
                and pt.x_supplies_type = 'labor_protection'
                and sp.state='done'
                
        union
                        
        SELECT 
                'b' as title,
                'Return' as login,
                'Nhập trả lại' as name,
                sum(case when spt.x_type ='type_2' and sm.date::date < '{year}-01-01' then sml.qty_done * svl.unit_cost else 0 end) as before,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-01-01' and '{year}-01-31' then sml.qty_done * svl.unit_cost else 0 end) as t1,
                sum(case when spt.x_type ='type_2' and sm.date::date >= '{year}-02-01' and sm.date::date < '{year}-03-01' then sml.qty_done * svl.unit_cost else 0 end) as t2,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-03-01' and '{year}-03-31' then sml.qty_done * svl.unit_cost else 0 end) as t3,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-04-01' and '{year}-04-30' then sml.qty_done * svl.unit_cost else 0 end) as t4,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-05-01' and '{year}-05-31' then sml.qty_done * svl.unit_cost else 0 end) as t5,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-06-01' and '{year}-06-30' then sml.qty_done * svl.unit_cost else 0 end) as t6,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-07-01' and '{year}-07-31' then sml.qty_done * svl.unit_cost else 0 end) as t7,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-08-01' and '{year}-08-31' then sml.qty_done * svl.unit_cost else 0 end) as t8,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-09-01' and '{year}-09-30' then sml.qty_done * svl.unit_cost else 0 end) as t9,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-10-01' and '{year}-10-31' then sml.qty_done * svl.unit_cost else 0 end) as t10,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-11-01' and '{year}-11-30' then sml.qty_done * svl.unit_cost else 0 end) as t11,
                sum(case when spt.x_type ='type_2' and sm.date::date between '{year}-12-01' and '{year}-12-31' then sml.qty_done * svl.unit_cost else 0 end) as t12,
                sum(case when spt.x_type ='type_2' and sm.date::date < '{year}-12-31' then sml.qty_done * svl.unit_cost else 0 end) as afterunion
        FROM product_template pt
                LEFT JOIN uom_uom uu  ON uu.id = pt.uom_id
                LEFT JOIN product_product pp  ON pt.id = pp.product_tmpl_id
                LEFT JOIN stock_move_line sml ON pp.id = sml.product_id
                LEFT JOIN stock_picking sp  ON sml.picking_id = sp.id
                LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                LEFT JOIN stock_move sm ON sm.id = sml.move_id
                left join stock_valuation_layer svl on svl.stock_move_id = sm.id
                left join stock_location sl1 on sml.location_id=sl1.id
                left join stock_location sl2 on sml.location_dest_id=sl2."id"
                left join ir_property ip on ip.name = 'standard_price' and substring(ip.res_id,17,100)::int = pp.id
        WHERE pt.x_product_type = 'supplies'
                and pt.x_type = 'product' 
                and pt.x_supplies_type = 'labor_protection'
                and sp.state='done'
                                        
        union 
                        
        SELECT 
                'c' as title,
                'Cancel' as login,
                'Huỷ' as name,
                sum(case when spt.x_type ='type_7' and sm.date::date < '{year}-01-01' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as before,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-01-01' and '{year}-01-31' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t1,
                sum(case when spt.x_type ='type_7' and sm.date::date >= '{year}-02-01' and sm.date::date < '{year}-03-01' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t2,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-03-01' and '{year}-03-31' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t3,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-04-01' and '{year}-04-30' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t4,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-05-01' and '{year}-05-31' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t5,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-06-01' and '{year}-06-30' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t6,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-07-01' and '{year}-07-31' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t7,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-08-01' and '{year}-08-31' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t8,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-09-01' and '{year}-09-30' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t9,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-10-01' and '{year}-10-31' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t10,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-11-01' and '{year}-11-30' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t11,
                sum(case when spt.x_type ='type_7' and sm.date::date between '{year}-12-01' and '{year}-12-31' and sl2.x_name = 'Kho hỏng mất' then sml.qty_done * svl.unit_cost else 0 end) as t12,
                sum(case when spt.x_type ='type_7' and sm.date::date < '{year}-12-31' then sml.qty_done * svl.unit_cost else 0 end) as after
        FROM product_template pt
        LEFT JOIN uom_uom uu  ON uu.id = pt.uom_id
                LEFT JOIN product_product pp  ON pt.id = pp.product_tmpl_id
                LEFT JOIN stock_move_line sml ON pp.id = sml.product_id
                LEFT JOIN stock_picking sp  ON sml.picking_id = sp.id
                LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                LEFT JOIN stock_move sm ON sm.id = sml.move_id
                left join stock_valuation_layer svl on svl.stock_move_id = sm.id 
                left join stock_location sl1 on sml.location_id=sl1.id
                left join stock_location sl2 on sml.location_dest_id=sl2.id
                left join ir_property ip on ip.name = 'standard_price' and substring(ip.res_id,17,100)::int = pp.id
        WHERE pt.x_product_type = 'supplies'
                and pt.x_type = 'product' 
                and pt.x_supplies_type = 'labor_protection'
                and sp.state='done' 
        ORDER BY title
            '''.format(year=self.year)
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()
        x = 1
        for r in recs:
            insert = '''INSERT INTO stock_report_value_cost (master_key,index ,login,name,amount_bf,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                        VALUES ({key},{index},'{login}','{name}',{amount_bf},{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                    '''.format(key=self.master_key,
                                               index=x,
                                               login=r['login'],
                                               name=r['name'],
                                               amount_bf=r['before'] or 0,
                                               t1=r['t1'] or 0,
                                               t2=r['t2'] or 0,
                                               t3=r['t3'] or 0,
                                               t4=r['t4'] or 0,
                                               t5=r['t5'] or 0,
                                               t6=r['t6'] or 0,
                                               t7=r['t7'] or 0,
                                               t8=r['t8'] or 0,
                                               t9=r['t9'] or 0,
                                               t10=r['t10'] or 0,
                                               t11=r['t11'] or 0,
                                               t12=r['t12'] or 0)
            x += 1
            self._cr.execute(insert)
        sql1 = '''
                SELECT ru.login, rp.name , 
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date < '{year}-1-1' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date < '{year}-1-1' then sml.qty_done * svl.unit_cost else 0  end) amount_before,
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-1-1' and '{year}-1-31' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-1-1' and '{year}-1-31' then sml.qty_done * svl.unit_cost else 0  end) t1,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-2-1' and '{year}-2-28' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-2-1' and '{year}-2-28' then sml.qty_done * svl.unit_cost else 0  end) t2,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-3-1' and '{year}-3-31' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-1-1' and '{year}-3-31' then sml.qty_done * svl.unit_cost else 0  end) t3,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-4-1' and '{year}-4-30' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-4-1' and '{year}-4-30' then sml.qty_done * svl.unit_cost else 0  end) t4,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-5-1' and '{year}-5-31' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-5-1' and '{year}-5-31' then sml.qty_done * svl.unit_cost else 0  end) t5,
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-6-1' and '{year}-6-30' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-6-1' and '{year}-6-30' then sml.qty_done * svl.unit_cost else 0  end) t6,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-7-1' and '{year}-7-31' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-7-1' and '{year}-7-31' then sml.qty_done * svl.unit_cost else 0  end) t7,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-8-1' and '{year}-8-31' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-8-1' and '{year}-8-31' then sml.qty_done * svl.unit_cost else 0  end) t8,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-9-1' and '{year}-9-30' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-9-1' and '{year}-9-30' then sml.qty_done * svl.unit_cost else 0  end) t9,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-10-1' and '{year}-10-31' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-10-1' and '{year}-10-31' then sml.qty_done * svl.unit_cost else 0  end) t10,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-11-1' and '{year}-11-30' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-11-1' and '{year}-11-30' then sml.qty_done * svl.unit_cost else 0  end) t11,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-12-1' and '{year}-12-31' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-12-1' and '{year}-12-31' then sml.qty_done * svl.unit_cost else 0  end) t12
                
                FROM res_users ru 
                        LEFT JOIN res_partner rp ON ru.partner_id = rp.id
                        LEFT JOIN stock_picking sp ON ru.id = sp.x_receiver_id or ru.id = sp.x_payer_id
                        LEFT JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                        LEFT JOIN stock_move_line sml ON sml.picking_id = sp.id
                        LEFT JOIN stock_move sm ON sm.id = sml.move_id
                        left join stock_valuation_layer svl on svl.stock_move_id = sm.id 
                        LEFT JOIN product_product pp ON pp.id = sml.product_id
                        LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE pt.x_product_type = 'supplies'
                        and pt.x_type = 'product' 
                        and pt.x_supplies_type = 'labor_protection'
                        and sp.state='done' 
                GROUP BY ru.login, rp.name'''.format(year=self.year)
        self._cr.execute(sql1)
        recs1 = self._cr.dictfetchall()
        x = 4
        for r in recs1:
            insert = '''INSERT INTO stock_report_value_cost (master_key, index, login,name,amount_bf,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                                    VALUES ({key},{index},'{login}','{name}',{amount_bf},{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                                '''.format(key=self.master_key,
                                                           index=x,
                                                           login=r['login'],
                                                           name=r['name'],
                                                           amount_bf=r['amount_before'] or 0,
                                                           t1=r['t1'] or 0,
                                                           t2=r['t2'] or 0,
                                                           t3=r['t3'] or 0,
                                                           t4=r['t4'] or 0,
                                                           t5=r['t5'] or 0,
                                                           t6=r['t6'] or 0,
                                                           t7=r['t7'] or 0,
                                                           t8=r['t8'] or 0,
                                                           t9=r['t9'] or 0,
                                                           t10=r['t10'] or 0,
                                                           t11=r['t11'] or 0,
                                                           t12=r['t12'] or 0)
            self._cr.execute(insert)
            x += 1

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo chi phí nhân viên về đồng phục',
            'view_mode': 'tree',
            'res_model': 'stock.report.value.cost',
            'view_id': self.env.ref('xstock.stock_value_report_view').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'current',
        }
