# -*- coding: utf-8 -*-
import datetime as dt

from odoo import api, fields, models, tools
from odoo.http import request


class StockReportDetailPopupWizard(models.TransientModel):
    _name = 'stock.report.detail.popup.wizard'

    product_ids = fields.Many2many('product.product', string='Sản phẩm')
    #
    # @api.model
    # def init(self):
    #     """ Event main report """
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self._cr.execute("""CREATE VIEW {table} AS (
    #             select
    #                 row_number() OVER () AS id,
    #                 case when sp.id is null then 'Kiểm kê kho' else coalesce(it.value,spt."name") end as picking_type,
    #                 cast(sm.date + interval '7 hours' as date) as move_date,
    #                 case when sp.id is not null then sp."name" else si."name" end as entry_name,
    #                 pt.default_code as product_code,
    #                 pt."name" as product_name,
    #                 case when pt.x_product_type = 'tools' then 'Công cụ dụng cụ' else 'Vật tư' end as product_type,
    #                 coalesce(it2.value,uu."name") as uom_name,
    #                 coalesce(spl."name",'') as serial,
    #                 coalesce(sl."name",'') as location_name,
    #                 coalesce(sl2."name",'') as location_dest_name,
    #                 coalesce(pp2."name",'') as from_project,
    #                 coalesce(pp3."name",'') as to_project,
    #                 case when sm.picking_id is not null then rp."name" else rp2."name" end as create_user,
    #                 case when spt.x_type in ('type_1','type_3','type_4') then '' else coalesce(rp3."name",'') end as payer_name,
    #                 case when spt.x_type in ('type_2','type_6','type_8') then '' else coalesce(rp4."name",'') end as receiver_name,
    #                 sml.qty_done as quantity,
    #                 coalesce(case when spt.code = 'internal' or spt.code is null then ip.value_float else svl.unit_cost end,0) as price_unit,
    #                 sml.qty_done * coalesce(case when spt.code = 'internal' or spt.code is null then ip.value_float else svl.unit_cost end,0) as value
    #             from stock_move_line sml
    #             left join stock_move sm on sm.id = sml.move_id
    #             left join stock_picking sp on sp.id = sm.picking_id and sm.picking_id is not null and sp.state = 'done'
    #             left join stock_inventory si on si.id = sm.inventory_id and sm.inventory_id is not null and si.state = 'done'
    #             left join stock_picking_type spt on spt.id = sp.picking_type_id
    #             left join product_product pp on pp.id = sml.product_id
    #             left join product_template pt on pt.id = pp.product_tmpl_id
    #             left join uom_uom uu on uu.id = sml.product_uom_id
    #             left join stock_production_lot spl on spl.id = sml.lot_id
    #             left join stock_location sl on sl.id = sml.location_id and sl."usage" in ('internal','inventory') and sl.parent_path like '1/7/%'
    #             left join stock_location sl2 on sl2.id = sml.location_dest_id and sl2."usage" in ('internal','inventory') and sl2.parent_path like '1/7/%'
    #             left join ir_translation it on it."name" = 'stock.picking.type,name' and it.lang = 'vi_VN' and it.src = spt."name"
    #             left join ir_translation it2 on it2."name" = 'uom.uom,name' and it2.lang = 'vi_VN' and it2.src = uu."name"
    #             left join project_project pp2 on pp2.id = sml.x_from_the_project_id
    #             left join project_project pp3 on pp3.id = sml.x_to_the_project_id
    #             left join res_users ru on ru.id = sp.create_uid and sm.picking_id is not null
    #             left join res_partner rp on rp.id = ru.partner_id
    #             left join res_users ru2 on ru2.id = si.create_uid and sm.inventory_id is not null
    #             left join res_partner rp2 on rp2.id = ru2.partner_id
    #             left join res_users ru3 on ru3.id = sp.x_payer_id and sm.picking_id is not null
    #             left join res_partner rp3 on rp3.id = ru3.partner_id
    #             left join res_users ru4 on ru4.id = sp.x_receiver_id and sm.picking_id is not null
    #             left join res_partner rp4 on rp4.id = ru4.partner_id
    #             left join stock_valuation_layer svl on svl.stock_move_id = sm.id
    #             left join ir_property ip on ip."name" = 'standard_price' and left(ip.res_id,15) = 'product.product' and cast(substring(ip.res_id,17,100) as int) = pp.id
    #             where (sp.id is not null or si.id is not null)
    #             order by sm."date", product_code, from_project, to_project, receiver_name, payer_name, serial)""".format(table=self._table))

    def _generate_data(self):
        product_ids = self.product_ids.ids
        filter = ''
        if len(product_ids) > 0:
            filter += "and  pp.id in %s" % str(tuple(product_ids + [0, 0]))
        sql = f'''  
                    select
                    row_number() OVER () AS id,
                    case when sp.id is null then 'Kiểm kê kho' else coalesce(it.value,spt."name") end as picking_type,
                    cast(sm.date + interval '7 hours' as date) as move_date,
                    case when sp.id is not null then sp."name" else si."name" end as entry_name,
                    pt.default_code as product_code,
                    pt."name" as product_name,
                    case when pt.x_product_type = 'tools' then 'Công cụ dụng cụ' else 'Vật tư' end as product_type,
                    coalesce(it2.value,uu."name") as uom_name,
                    coalesce(spl."name",'') as serial,
                    coalesce(sl."name",'') as location_name,
                    coalesce(sl2."name",'') as location_dest_name,
                    coalesce(pp2."name",'') as from_project,
                    coalesce(pp3."name",'') as to_project,
                    case when sm.picking_id is not null then rp."name" else rp2."name" end as create_user,
                    case when spt.x_type in ('type_1','type_3','type_4') then '' else coalesce(rp3."name",'') end as payer_name,
                    case when spt.x_type in ('type_2','type_6','type_8') then '' else coalesce(rp4."name",'') end as receiver_name,
                    sml.qty_done as quantity,
                    coalesce(case when spt.code = 'internal' or spt.code is null then ip.value_float else svl.unit_cost end,0) as price_unit,
                    sml.qty_done * coalesce(case when spt.code = 'internal' or spt.code is null then ip.value_float else svl.unit_cost end,0) as value
                from stock_move_line sml
                left join stock_move sm on sm.id = sml.move_id
                left join stock_picking sp on sp.id = sm.picking_id and sm.picking_id is not null and sp.state = 'done'
                left join stock_inventory si on si.id = sm.inventory_id and sm.inventory_id is not null and si.state = 'done'
                left join stock_picking_type spt on spt.id = sp.picking_type_id
                left join product_product pp on pp.id = sml.product_id
                left join product_template pt on pt.id = pp.product_tmpl_id
                left join uom_uom uu on uu.id = sml.product_uom_id
                left join stock_production_lot spl on spl.id = sml.lot_id
                left join stock_location sl on sl.id = sml.location_id and sl."usage" in ('internal','inventory') and sl.parent_path like '1/7/%'
                left join stock_location sl2 on sl2.id = sml.location_dest_id and sl2."usage" in ('internal','inventory') and sl2.parent_path like '1/7/%'
                left join ir_translation it on it."name" = 'stock.picking.type,name' and it.lang = 'vi_VN' and it.src = spt."name"
                left join ir_translation it2 on it2."name" = 'uom.uom,name' and it2.lang = 'vi_VN' and it2.src = uu."name"
                left join project_project pp2 on pp2.id = sml.x_from_the_project_id
                left join project_project pp3 on pp3.id = sml.x_to_the_project_id
                left join res_users ru on ru.id = sp.create_uid and sm.picking_id is not null
                left join res_partner rp on rp.id = ru.partner_id
                left join res_users ru2 on ru2.id = si.create_uid and sm.inventory_id is not null
                left join res_partner rp2 on rp2.id = ru2.partner_id
                left join res_users ru3 on ru3.id = sp.x_payer_id and sm.picking_id is not null
                left join res_partner rp3 on rp3.id = ru3.partner_id
                left join res_users ru4 on ru4.id = sp.x_receiver_id and sm.picking_id is not null
                left join res_partner rp4 on rp4.id = ru4.partner_id
                left join stock_valuation_layer svl on svl.stock_move_id = sm.id
                left join ir_property ip on ip."name" = 'standard_price' and left(ip.res_id,15) = 'product.product' and cast(substring(ip.res_id,17,100) as int) = pp.id
                where (sp.id is not null or si.id is not null)
                {filter}
                order by sm."date", product_code, from_project, to_project, receiver_name, payer_name, serial'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        for value in recs_last:
            insert = '''INSERT INTO stock_report_detail_popup_clone 
                                (master_key, picking_type, move_date, entry_name, product_code,
                                product_name, product_type, uom_name, serial, location_name,
                                location_dest_name, from_project, to_project, create_user, 
                                payer_name, receiver_name, quantity, price_unit, value)
                        VALUES ({master_key}, '{picking_type}', '{move_date}', '{entry_name}', '{product_code}', 
                                '{product_name}', '{product_type}', '{uom_name}', '{serial}', '{location_name}', 
                                '{location_dest_name}', '{from_project}', '{to_project}', '{create_user}', 
                                '{payer_name}', '{receiver_name}', {quantity}, {price_unit}, {value})
                                                   '''.format(master_key=self.env.user.id,
                                                              picking_type=value.get('picking_type'),
                                                              move_date=value.get('move_date'),
                                                              entry_name=value.get('entry_name'),
                                                              product_code=value.get('product_code'),
                                                              product_name=value.get('product_name'),
                                                              product_type=value.get('product_type'),
                                                              uom_name=value.get('uom_name'),
                                                              serial=value.get('serial'),
                                                              location_name=value.get('location_name'),
                                                              location_dest_name=value.get('location_dest_name'),
                                                              from_project=value.get('from_project'),
                                                              to_project=value.get('to_project'),
                                                              create_user=value.get('create_user'),
                                                              payer_name=value.get('payer_name'),
                                                              receiver_name=value.get('receiver_name'),
                                                              quantity=value.get('quantity') or 0,
                                                              price_unit=value.get('price_unit') or 0,
                                                              value=value.get('value') or 0, )
            self._cr.execute(insert)

    def action_report(self):
        self._cr.execute("delete from stock_report_detail_popup_clone where master_key = {key} or master_key is null".format(key=self.env.user.id))
        self._generate_data()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo chi tiết hoạt động kho',
            'view_mode': 'tree',
            'res_model': "stock.report.detail.popup.clone",
            'domain': [('master_key', '=', self.env.user.id)],
            'view_id': self.env.ref('xstock.stock_report_detail_popup_clone_view').id,
            'target': 'main',

        }