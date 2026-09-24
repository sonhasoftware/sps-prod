# -*- coding: utf-8 -*-

from datetime import timedelta, date, datetime
import base64
import datetime as dt
import os
from io import BytesIO
import openpyxl
from openpyxl.styles import NamedStyle, Font, Border, Side
from openpyxl.writer.excel import save_virtual_workbook
from openpyxl.utils import get_column_letter
from odoo import api, fields, models


class StockSuppliesReport(models.TransientModel):
    _name = 'stock.supplies.report'
    _description = 'Báo cáo hiệu suất sử dụng vật tư'

    year = fields.Selection(
        selection='years_selection',
        string="Năm",
        default=str(dt.datetime.now().year), required=True)
    product_ids = fields.Many2many('product.product', string='Sản phẩm', domain=[('x_type', '=', 'product'),('x_product_type', '=', 'supplies')])

    def years_selection(self):
        y = dt.datetime.now().year
        year_list = []
        while y != 1939:
            year_list.append((str(y), str(y)))
            y -= 1
        return year_list

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)

    def action_report_stock(self):
        time_param = self.env['ir.config_parameter'].sudo().get_param('time_param_reuser')
        time = time_param if time_param else '2025-07-01'

        filter_product = ""
        if self.product_ids:
            a = self.product_ids.ids
            filter_product = "and pp.id in " + str(tuple(a + [0, 0]))

        current_year = self.year
        self._cr.execute(
            "delete from stock_supplies_rp where master_key = {key}".format(key=self.master_key))
        sql1 = '''
                SELECT 'New' as shortname, 'Nhập mới' as fullname,
                    sum(case when sm.date::date between '{year}-01-01' and '{year}-01-31' then sml.qty_done*svl.unit_cost else 0 end) as t1,
                    sum(case when extract(month from sm.date) = 2 and extract(year from sm.date) = {year} then sml.qty_done*svl.unit_cost else 0 end) as t2,
                    sum(case when sm.date::date between '{year}-03-01' and '{year}-03-31' then sml.qty_done*svl.unit_cost else 0 end) as t3,
                    sum(case when sm.date::date between '{year}-04-01' and '{year}-04-30' then sml.qty_done*svl.unit_cost else 0 end) as t4,
                    sum(case when sm.date::date between '{year}-05-01' and '{year}-05-31' then sml.qty_done*svl.unit_cost else 0 end) as t5,
                    sum(case when sm.date::date between '{year}-06-01' and '{year}-06-30' then sml.qty_done*svl.unit_cost else 0 end) as t6,			
                    sum(case when sm.date::date between '{year}-07-01' and '{year}-07-31' then sml.qty_done*svl.unit_cost else 0 end) as t7,
                    sum(case when sm.date::date between '{year}-08-01' and '{year}-08-31' then sml.qty_done*svl.unit_cost else 0 end) as t8,
                    sum(case when sm.date::date between '{year}-09-01' and '{year}-09-30' then sml.qty_done*svl.unit_cost else 0 end) as t9,
                    sum(case when sm.date::date between '{year}-10-01' and '{year}-10-31' then sml.qty_done*svl.unit_cost else 0 end) as t10,
                    sum(case when sm.date::date between '{year}-11-01' and '{year}-11-30' then sml.qty_done*svl.unit_cost else 0 end) as t11,
                    sum(case when sm.date::date between '{year}-12-01' and '{year}-12-31' then sml.qty_done*svl.unit_cost else 0 end) as t12,
                    sum(case when sm.date::date between '{year}-01-01' and '{year}-12-31' then sml.qty_done*svl.unit_cost else 0 end) as total
                FROM product_template pt
                    LEFT JOIN uom_uom uu  ON uu.id = pt.uom_id
                    LEFT JOIN product_product pp  ON pt.id = pp.product_tmpl_id
                    LEFT JOIN stock_move_line sml ON pp.id = sml.product_id
                    LEFT JOIN project_project pp2 ON pp2.id = sml.x_from_the_project_id
                    LEFT JOIN stock_picking sp  ON sml.picking_id = sp.id
                    LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                    LEFT JOIN stock_move sm ON sm.id = sml.move_id
                    left join stock_valuation_layer svl on svl.stock_move_id = sm.id 
                    left join stock_location sl1 on sml.location_id=sl1.id
                    left join stock_location sl2 on sml.location_dest_id=sl2."id"
                    left join ir_property ip on ip.name = 'standard_price' and substring(ip.res_id,17,100)::int = pp.id
                WHERE pt.x_type='product'
                    AND pt.x_product_type = 'supplies' 
                    AND pt.x_supplies_type != 'labor_protection' 
                    AND sp.state='done' 
                    AND spt.x_type ='type_1'
                    AND ((sp.date_done <= '{time}') or 
                    (sp.date_done > '{time}' AND ((pp2.name not ilike 'REUSE%' AND pp2.name !~* 'RE[0-9][0-9]') or pp2.name is null)))
                    {product_id}

                UNION all

                SELECT 'Return' as shortname, 'Nhập trả lại' as fullname,
                    sum(case when sm.date::date between '{year}-01-01' and '{year}-01-31' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t1,
                    sum(case when extract(month from sm.date) = 2 and extract(year from sm.date) = {year} and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t2,
                    sum(case when sm.date::date between '{year}-03-01' and '{year}-03-31' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t3,
                    sum(case when sm.date::date between '{year}-04-01' and '{year}-04-30' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t4,
                    sum(case when sm.date::date between '{year}-05-01' and '{year}-05-31' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t5,
                    sum(case when sm.date::date between '{year}-06-01' and '{year}-06-30' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t6,			
                    sum(case when sm.date::date between '{year}-07-01' and '{year}-07-31' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t7,
                    sum(case when sm.date::date between '{year}-08-01' and '{year}-08-31' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t8,
                    sum(case when sm.date::date between '{year}-09-01' and '{year}-09-30' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t9,
                    sum(case when sm.date::date between '{year}-10-01' and '{year}-10-31' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t10,
                    sum(case when sm.date::date between '{year}-11-01' and '{year}-11-30' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t11,
                    sum(case when sm.date::date between '{year}-12-01' and '{year}-12-31' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t12,
                    sum(case when sm.date::date between '{year}-01-01' and '{year}-12-31' and spt.x_type='type_2' then sml.qty_done*svl.unit_cost else 0 end) as total
                FROM product_template pt
                    LEFT JOIN uom_uom uu  ON uu.id = pt.uom_id
                    LEFT JOIN product_product pp  ON pt.id = pp.product_tmpl_id
                    LEFT JOIN stock_move_line sml ON pp.id = sml.product_id
                    LEFT JOIN project_project pp2 ON pp2.id = sml.x_from_the_project_id
                    LEFT JOIN stock_picking sp  ON sml.picking_id = sp.id
                    LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                    LEFT JOIN stock_move sm ON sm.id = sml.move_id
                    left join stock_valuation_layer svl on svl.stock_move_id = sm.id 
                    left join stock_location sl1 on sml.location_id=sl1.id
                    left join stock_location sl2 on sml.location_dest_id=sl2."id"
                    left join ir_property ip on ip.name = 'standard_price' and substring(ip.res_id,17,100)::int = pp.id
                WHERE pt.x_type='product'
                    AND pt.x_product_type = 'supplies' 
                    AND pt.x_supplies_type != 'labor_protection' 
                    AND sp.state='done'
                     AND ((sp.date_done <= '{time}') or 
                    (sp.date_done > '{time}' AND (pp2.name ilike 'REUSE%' OR pp2.name ~* 'RE[0-9][0-9]')))
                    {product_id}

                UNION all
                SELECT 'Del' as shortname, 'Hủy' as fullname,
                    sum(case when sm.date::date between '{year}-01-01' and '{year}-01-31' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t1,
                    sum(case when extract(month from sm.date) = 2 and extract(year from sm.date) = {year} and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t2,
                    sum(case when sm.date::date between '{year}-03-01' and '{year}-03-31' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t3,
                    sum(case when sm.date::date between '{year}-04-01' and '{year}-04-30' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t4,
                    sum(case when sm.date::date between '{year}-05-01' and '{year}-05-31' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t5,
                    sum(case when sm.date::date between '{year}-06-01' and '{year}-06-30' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t6,
                    sum(case when sm.date::date between '{year}-07-01' and '{year}-07-31' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t7,
                    sum(case when sm.date::date between '{year}-08-01' and '{year}-08-31' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t8,
                    sum(case when sm.date::date between '{year}-09-01' and '{year}-09-30' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t9,
                    sum(case when sm.date::date between '{year}-10-01' and '{year}-10-31' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t10,
                    sum(case when sm.date::date between '{year}-11-01' and '{year}-11-30' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t11,
                    sum(case when sm.date::date between '{year}-12-01' and '{year}-12-31' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as t12,
                    sum(case when sm.date::date between '{year}-01-01' and '{year}-12-31' and spt.x_type ='type_7' and sl2.x_name = 'Kho hàng hỏng, hủy' then sml.qty_done * svl.unit_cost else 0 end) as total
                FROM product_template pt
                    LEFT JOIN uom_uom uu  ON uu.id = pt.uom_id
                    LEFT JOIN product_product pp  ON pt.id = pp.product_tmpl_id
                    LEFT JOIN stock_move_line sml ON pp.id = sml.product_id
                    LEFT JOIN project_project pp2 ON pp2.id = sml.x_from_the_project_id
                    LEFT JOIN stock_picking sp  ON sml.picking_id = sp.id
                    LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                    LEFT JOIN stock_move sm ON sm.id = sml.move_id
                    left join stock_valuation_layer svl on svl.stock_move_id = sm.id 
                    left join stock_location sl1 on sml.location_id=sl1.id
                    left join stock_location sl2 on sml.location_dest_id=sl2."id"
                    left join ir_property ip on ip.name = 'standard_price' and substring(ip.res_id,17,100)::int = pp.id
                WHERE  pt.x_type='product'
                    AND pt.x_product_type = 'supplies' 
                    AND pt.x_supplies_type != 'labor_protection' 
                    AND sp.state='done'
                    AND ((sp.date_done <= '{time}') or 
                    (sp.date_done > '{time}' AND pp2.name ilike 'REUSE%' OR pp2.name ~* 'RE[0-9][0-9]'))
                    {product_id}

        '''.format(year=current_year, product_id=filter_product, time=time)
        self._cr.execute(sql1)
        recs = self._cr.dictfetchall()
        x = 1
        for r in recs:
            insert = '''INSERT INTO stock_supplies_rp (master_key,index,login,name,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                VALUES ({key},{index},'{login}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                '''.format(key=self.master_key,
                                           index=x,
                                           login=r['shortname'] or '',
                                           name=r['fullname'] or '',
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
                                           t12=r['t12'] or 0,
                                           # total=r['total']
                                           )
            self._cr.execute(insert)
            x += 1

        sql2 = '''
                    SELECT ru.login, rp.name ,
                        sum(case when sm.date::date between '{year}-01-01' and '{year}-01-31' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t1,
                        sum(case when extract(month from sm.date) = 2 and extract(year from sm.date) = {year}
                                        and spt.x_type ='type_2' then sml.qty_done*svl.unit_cost else 0 end) as t2,
                        sum(case when sm.date::date between '{year}-03-01' and '{year}-03-31' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t3,
                        sum(case when sm.date::date between '{year}-04-01' and '{year}-04-30' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t4,
                        sum(case when sm.date::date between '{year}-05-01' and '{year}-05-31' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t5,
                        sum(case when sm.date::date between '{year}-06-01' and '{year}-06-30' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t6,
                        sum(case when sm.date::date between '{year}-07-01' and '{year}-07-31' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t7,
                        sum(case when sm.date::date between '{year}-08-01' and '{year}-08-31' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t8,
                        sum(case when sm.date::date between '{year}-09-01' and '{year}-09-30' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t9,
                        sum(case when sm.date::date between '{year}-10-01' and '{year}-10-31' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t10,
                        sum(case when sm.date::date between '{year}-11-01' and '{year}-11-30' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t11,
                        sum(case when sm.date::date between '{year}-12-01' and '{year}-12-31' and spt.x_type ='type_2'
                                         then sml.qty_done*svl.unit_cost else 0 end) as t12,
                        sum(case when sm.date::date between '{year}-01-01' and '{year}-12-31' and spt.x_type ='type_2'
                                 then sml.qty_done * svl.unit_cost else 0 end) as total
                FROM res_users ru
                        LEFT JOIN res_partner rp ON ru.partner_id = rp.id
                        LEFT JOIN hr_employee he ON he.user_id = ru.id
                        LEFT JOIN stock_picking sp ON ru.id = sp.x_payer_id
                        LEFT JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                        LEFT JOIN stock_move_line sml ON sml.picking_id = sp.id
                        LEFT JOIN project_project pp2 ON pp2.id = sml.x_from_the_project_id
                        LEFT JOIN stock_move sm ON sm.id = sml.move_id
                        left join stock_valuation_layer svl on svl.stock_move_id = sm.id
                        LEFT JOIN product_product pp ON pp.id = sml.product_id
                        left join product_template pt on pt.id = pp.product_tmpl_id
                WHERE pt.x_type='product'
                        AND pt.x_product_type = 'supplies'
                        AND pt.x_supplies_type != 'labor_protection'
                        AND sp.state='done'
                        AND he.id IS NOT NULL
                        AND ((sp.date_done <= '{time}') or
                    (sp.date_done > '{time}' AND (pp2.name ilike 'REUSE%' OR pp2.name ~* 'RE[0-9][0-9]')))
                        {product_id}
                GROUP BY ru.login, rp.name
                '''.format(year=current_year, product_id=filter_product, time=time)
        self._cr.execute(sql2)
        recs1 = self._cr.dictfetchall()
        x = 4
        for r in recs1:
            insert = '''INSERT INTO stock_supplies_rp (master_key, index , login,name,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                                    VALUES ({key},{index},'{login}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                                '''.format(key=self.master_key,
                                                           index=x,
                                                           login=r['login'] or '',
                                                           name=r['name'] or '',
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
                                                           t12=r['t12'] or 0,
                                                           # total=r['total']
                                                           )
            self._cr.execute(insert)
            x += 1
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo hiệu suất tái sử dụng vật tư',
            'view_mode': 'tree',
            'res_model': 'stock.supplies.rp',
            'view_id': self.env.ref('xstock.stock_supplies_report_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'current',
        }
