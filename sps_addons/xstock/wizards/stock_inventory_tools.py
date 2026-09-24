# -*- coding: utf-8 -*-
from datetime import timedelta, date, datetime, time
import base64
import os
from io import BytesIO
import openpyxl
from openpyxl.styles import NamedStyle, Font, Border, Side
from openpyxl.writer.excel import save_virtual_workbook
from odoo import api, fields, models


class ReportStockTools(models.TransientModel):
    _name = 'stock.report.tools'
    _description = 'vậy Báo cáo tồn kho công cụ dụng cụ'

    year = fields.Integer('Năm', required=True, default=str(date.today().year))
    stock = fields.Many2one('stock.location', domain=[('usage', '=', 'internal'), ('x_name', '!=', 'kho cho mượn')])
    is_order = fields.Boolean('Cần đặt hàng', default=False)

    def action_report_stock_tools(self):
        location_ids = []
        if self.stock:
            location_ids.append(self.stock.id)
        else:
            rec = self.env['stock.location'].search([('usage', '=', 'internal'), ('x_name', '!=', 'kho cho mượn')])
            for r in rec:
                location_ids.append(r['id'])

        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '%s..%stemplates%sstock_report_tools(1).xlsx' % (os.sep, os.sep, os.sep))
        ws = wb['Sheet1']

        sql = '''SELECT pt.id, pt.standard_price as standard_price,pt.default_code, pt.name ten_san_pham,it.VALUE as don_vi, pt.x_product_company, pt.x_code_brand,
	                pt.description AS x_product_type, 
                    -- Nhập mua trong kỳ: CHỈ tính theo phiếu nhập (type_1 nhập mua, type_2 nhập lại
                    -- vật tư chuẩn, type_8 thu hồi vật tư thừa). Lũy kế tới hết 31/12 năm báo cáo.
                    -- Đã bỏ phần kiểm kê/move không phiếu (tồn đầu load qua điều chỉnh kiểm kê) vì
                    -- không phải nhập mua — nó thuộc tồn đầu, tính riêng ở cột giá trị (inv_adj).
                    coalesce(sum(case when (spt.x_type in ('type_1', 'type_2','type_8') and ((sm.date + interval '7 hours') ::date <= '{year}-12-31') and sl2.id in {stock} and
                               sm.picking_id is not null) THEN sml.qty_done END),0)
                    nhap_mua_trong_ki,
                    coalesce(sum(case when (spt.x_type = 'type_7' and ((sm.date + interval '7 hours') ::date <= '{year}-12-31') and sl1.usage='internal' and sl2.usage='internal' and 
                               sm.picking_id is not null  and (sl1.id in {stock} or sl2.id in {stock})) THEN sml.qty_done END) 
                    ,0) nhap_chuyen_kho,
                    coalesce(sum(case when (spt.x_type = 'type_6' and 
                               sm.picking_id is not null and ((sm.date + interval '7 hours') ::date <= '{year}-12-31') and sl2.id in {stock}) THEN sml.qty_done END),0) nhap_tra_lai,
                    coalesce(sum(case when (spt.x_type = 'type_4' and 
                               sm.picking_id is not null and ((sm.date + interval '7 hours') ::date <= '{year}-12-31') and sl1.id in {stock}) THEN sml.qty_done END),0) xuat_muon,
                    coalesce(sum(case when (spt.x_type = 'type_7' and 
                               sm.picking_id is not null and ((sm.date + interval '7 hours') ::date <= '{year}-12-31') and sl1.usage='internal' and sl2.usage='internal' and sl1.id in {stock}) THEN sml.qty_done END) 
                   ,0)as chuyen_kho,
                    coalesce(sum(case when ((spt.x_type = 'type_7' or (spt.x_type = 'type_9' or spt.sequence_code = 'HM') ) and 
                               sm.picking_id is not null and (sl2.x_name=coalesce('Kho hàng hỏng, hủy','') or sl2.location_type = 'damaged') and ((sm.date + interval '7 hours') ::date <= '{year}-12-31')) THEN sml.qty_done else 0 END),0)
                    + coalesce(sum(
                        case 
                            when (si.id is not null or (si.id is null and sp.id is null)) and ((sm.date + interval '7 hours') ::date <= '{year}-12-31') 
                                and sml.location_id in {stock} then sml.qty_done 
                                                else 0
                        end
                    ),0) as hong_mat_cu,
                    coalesce(sum(case when ((sm.date + interval '7 hours') ::date <= '{year}-12-31' and sl1.id in {stock}
                        and (sl2.location_type = 'damaged' or sl2.x_name='Kho hàng hỏng, hủy') and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ),0) as hong_mat,
                    pt.standard_price,
                    coalesce(sum(case when ((sm.date + interval '7 hours') ::date <= '{year}-12-31' and sl2.id in {stock} and sml.state = 'done') THEN sml.qty_done
                                     when ((sm.date + interval '7 hours') ::date <= '{year}-12-31' and sl1.id in {stock} and sml.state = 'done') THEN -sml.qty_done
                                     end
                    ),0) ton_kho,
                    coalesce(sum(case when ((sm.date + interval '7 hours') ::date <= '{year}-12-31' and sl1.id in {stock}
	                    and (sl2.name = 'Đang cho mượn' or sl2.x_name='kho cho mượn') and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) -  sum(case when ((sm.date + interval '7 hours') ::date <= '{year}-12-31' and sl2.id in {stock} 
	                    and (sl1.name = 'Đang cho mượn' or sl1.x_name='kho cho mượn') and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ),0)  cho_muon,
                    max(si.date) ngay_kiem_ke, 
                    sum(
                    case
                        when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-1-1' and '{year}-1-31' then
                            case
                                when sl1.id in {stock} then -sml.qty_done
                                when sl2.id in {stock} then sml.qty_done
                            end
                                                    else 0
                        end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-1-1' and '{year}-1-31' then
                                case
                                    when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0
                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst1,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date >= '{year}-2-1' and (sm.date + interval '7 hours') ::date < '{year}-3-1' then
                                case
                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date >= '{year}-2-1' and (sm.date + interval '7 hours') ::date < '{year}-3-1' then
                                case
																    when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0
                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst2,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-3-1' and '{year}-3-31' then
                                case
                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-3-1' and '{year}-3-31' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst3,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-4-1' and '{year}-4-30' then
                                case
                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-4-1' and '{year}-4-30' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst4,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-5-1' and '{year}-5-31' then
                                case

                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-5-1' and '{year}-5-31' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst5,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-6-1' and '{year}-6-30' then
                                case
                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-6-1' and '{year}-6-30' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst6,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-7-1' and '{year}-7-31' then
                                case
                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-7-1' and '{year}-7-31' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst7,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-8-1' and '{year}-8-31' then
                                case
                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-8-1' and '{year}-8-31' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst8,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-9-1' and '{year}-9-30' then
                                case
                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-9-1' and '{year}-9-30' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst9,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-10-1' and '{year}-10-31' then
                                case
                                    when sl1.id in {stock}then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-10-1' and '{year}-10-31' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst10,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-11-1' and '{year}-11-30' then
                                case
                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-11-1' and '{year}-11-30' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst11,
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-12-1' and '{year}-12-31' then
                                case
                                    when sl1.id in {stock} then -sml.qty_done
                                    when sl2.id in {stock} then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    + 
                    sum(
                        case
                            when sm.picking_id is not null and (sm.date + interval '7 hours') ::date BETWEEN'{year}-12-1' and '{year}-12-31' then
                                case
																when sl1.x_name=coalesce('kho cho mượn','') and sl2.x_name=coalesce('kho cho mượn','') then 0

                                    when sl1.x_name=coalesce('kho cho mượn','') then -sml.qty_done
                                    when sl2.x_name=coalesce('kho cho mượn','') then sml.qty_done
                                end
                                                            else 0
                            end
                    )
                    tst12,

                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-1-1' and '{year}-1-31' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt1,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date >='{year}-2-1' and (sm.date + interval '7 hours') ::date < '{year}-3-1' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt2,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-3-1' and '{year}-3-31' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt3,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-4-1' and '{year}-4-30' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt4,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-5-1' and '{year}-5-31' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt5,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-6-1' and '{year}-6-30' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt6,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-7-1' and '{year}-7-31' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt7,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-8-1' and '{year}-8-31' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt8,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-9-1' and '{year}-9-30' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt9,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-10-1' and '{year}-10-31' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt10,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-11-1' and '{year}-11-30' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt11,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date BETWEEN'{year}-12-1' and '{year}-12-31' and sl2.id in {stock}) THEN sml.qty_done * COALESCE ( ip.value_float, 0 )
                                     ELSE 0
                                     end
                    ) mtt12,
                    sum(case when (sm.picking_id is not null and spt.x_type in ('type_1', 'type_2','type_8') and (sm.date + interval '7 hours') ::date < '{year}-1-1' and sl2.id in {stock})
                                then sml.qty_done * coalesce(pt.standard_price, 0) else 0 end) amount_before,
                    coalesce(sum(case when ((spt.x_type = 'type_7' or spt.x_type = 'type_6') and (sm.date + interval '7 hours') ::date <= '{year_now}' and sm.picking_id is not null and (sl2.x_name=coalesce('Kho hàng hỏng, hủy','') or sl2.location_type = 'damaged')) 
                                THEN sml.qty_done*coalesce(ip.value_float,0) else 0 END),0)
                    + coalesce(sum(
                        case 
                            when (si.id is not null or (si.id is null and sp.id is null)) and (sm.date + interval '7 hours') ::date <= '{year_now}' and sml.location_id in {stock} 
                                then sml.qty_done * coalesce(sm.price_unit,0)
                                                else 0
                        end
                    ),0) broken_lose,
                    case when pt.x_manage_frequency then frequency.name else '-' end as tan_so_kiem_ke,

                    -- Thêm các trường tính qty_done từ supplier theo từng tháng
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-1-1' and '{year}-1-31' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                    ELSE 0
                    end) supplier_qty_t1,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-2-1' and '{year}-2-28' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t2,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-3-1' and '{year}-3-31' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t3,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-4-1' and '{year}-4-30' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t4,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-5-1' and '{year}-5-31' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t5,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-6-1' and '{year}-6-30' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t6,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-7-1' and '{year}-7-31' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t7,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-8-1' and '{year}-8-31' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t8,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-9-1' and '{year}-9-30' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t9,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-10-1' and '{year}-10-31' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t10,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-11-1' and '{year}-11-30' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t11,
                    sum(case when (sl1.usage = 'supplier' and (sm.date + interval '7 hours') ::date BETWEEN'{year}-12-1' and '{year}-12-31' 
                    and sml.location_id =4 and sml.state = 'done' and sml.location_dest_id  in {stock}
                    and DATE_PART('year', pol.x_date_received) = {year}
                    and DATE_PART('month', pol.x_date_received) = DATE_PART('month', sm.date + interval '7 hours')) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) supplier_qty_t12,

                    -- Thêm các trường tính tổng số mất hỏng theo từng tháng
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-1-1' and '{year}-1-31' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t1,
                    sum(case when ((sm.date + interval '7 hours') ::date >= '{year}-2-1' and (sm.date + interval '7 hours') ::date < '{year}-3-1'
                        and sml.location_dest_id = 18 and sml.state = 'done' and 
                        sml.location_id  in {stock}) THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t2,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-3-1' and '{year}-3-31' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t3,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-4-1' and '{year}-4-30' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t4,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-5-1' and '{year}-5-31' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t5,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-6-1' and '{year}-6-30' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t6,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-7-1' and '{year}-7-31' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t7,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-8-1' and '{year}-8-31' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t8,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-9-1' and '{year}-9-30' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t9,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-10-1' and '{year}-10-31' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t10,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-11-1' and '{year}-11-30' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t11,
                    sum(case when ((sm.date + interval '7 hours') ::date BETWEEN'{year}-12-1' and '{year}-12-31' and sml.location_id  in {stock}
                        and sml.location_dest_id = 18 and sml.state = 'done') THEN sml.qty_done
                                     ELSE 0
                                     end
                    ) damaged_qty_t12,

                    -- Thêm các trường lấy price_unit từ purchase_order_line theo từng tháng
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-1-1' and '{year}-1-31' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t1,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date >= '{year}-2-1' and (pol.x_date_received + interval '7 hours') ::date < '{year}-3-1' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t2,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-3-1' and '{year}-3-31' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t3,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-4-1' and '{year}-4-30' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t4,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-5-1' and '{year}-5-31' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t5,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-6-1' and '{year}-6-30' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t6,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-7-1' and '{year}-7-31' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t7,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-8-1' and '{year}-8-31' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t8,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-9-1' and '{year}-9-30' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t9,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-10-1' and '{year}-10-31' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t10,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-11-1' and '{year}-11-30' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t11,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-12-1' and '{year}-12-31' and pol.product_id = pp.id) THEN pol.price_unit
                                     ELSE 0
                                     end
                    ), 0) price_unit_t12,

                    -- Thêm các trường lấy amount từ account_tax theo từng tháng
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-1-1' and '{year}-1-31' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t1,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date >= '{year}-2-1' and (pol.x_date_received + interval '7 hours') ::date < '{year}-3-1' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t2,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-3-1' and '{year}-3-31' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t3,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-4-1' and '{year}-4-30' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t4,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-5-1' and '{year}-5-31' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t5,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-6-1' and '{year}-6-30' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t6,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-7-1' and '{year}-7-31' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t7,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-8-1' and '{year}-8-31' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t8,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-9-1' and '{year}-9-30' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t9,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-10-1' and '{year}-10-31' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t10,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-11-1' and '{year}-11-30' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t11,
                    coalesce(avg(case when ((pol.x_date_received + interval '7 hours') ::date BETWEEN'{year}-12-1' and '{year}-12-31' and pol.product_id = pp.id) THEN at.amount
                                     ELSE 0
                                     end
                    ), 0) tax_amount_t12

                FROM product_template pt
                    left join sale_frequency frequency on frequency.id = pt.x_frequency_id
                    LEFT JOIN uom_uom uu  ON uu.id = pt.uom_id
                    LEFT JOIN product_product pp  ON pt.id = pp.product_tmpl_id
                    LEFT JOIN stock_move_line sml ON pp.id = sml.product_id
                    LEFT JOIN stock_picking sp  ON sml.picking_id = sp.id
                    LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                    LEFT JOIN stock_move sm ON sm.id = sml.move_id
                    left join stock_location sl1 on sml.location_id=sl1.id
                    left join stock_location sl2 on sml.location_dest_id=sl2.id
                    left join stock_inventory si on sm.inventory_id=si.id
                    left join ir_property ip on ip.name = 'standard_price' and substring(ip.res_id,17,100)::int = pp.id
                    LEFT JOIN ir_translation it ON uu.NAME = it.src 
                    AND it.lang = 'vi_VN' 
                    AND it.NAME = 'uom.uom,name' and it.state = 'translated'
                    LEFT JOIN purchase_order_line pol ON pol.product_id = pp.id AND DATE_PART('year', pol.x_date_received) = {year}
                    LEFT JOIN purchase_order po ON pol.order_id = po.id
                    LEFT JOIN account_tax_purchase_order_line_rel polat ON polat.purchase_order_line_id = pol.id
                    LEFT JOIN account_tax at ON at.id = polat.account_tax_id
                    WHERE true 
                        and pt.x_type='product' 
                        and pt.active = 't'
                        and pt.x_product_type = 'tools'

                    GROUP BY pt.id, uu.name, it.VALUE, frequency.name
                '''.format(year=self.year, stock=tuple(location_ids + [0, 0]), year_now=date.today())
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()

        highlight = NamedStyle(name="highlight")
        highlight.font = Font(size=13)
        bd1 = Side(style='thin', color="000000")
        highlight.border = Border(left=bd1, top=bd1, right=bd1, bottom=bd1)

        highlight1 = NamedStyle(name='datetime', number_format='DD/MM/YYYY')
        highlight1.font = Font(size=13)
        bd1 = Side(style='thin', color="000000")
        highlight1.border = Border(left=bd1, top=bd1, right=bd1, bottom=bd1)

        # Nang cap code
        # Tìm kiếm tất cả các giao dịch kho từ Warehouse/Đang cho mượn	Warehouse/Kho hàng hỏng, hủy
        stock_move_line_to_17_ids = self.env['stock.move.line'].search(
            [('location_dest_id', '=', 17), ('state', '=', 'done')])
        stock_move_line_from_17_ids = self.env['stock.move.line'].search(
            [('location_id', '=', 17), ('state', '=', 'done')])

        product_to_17 = {}
        for sml in stock_move_line_to_17_ids:
            if sml.product_id.default_code not in product_to_17:
                product_to_17[sml.product_id.default_code] = sml.qty_done
            else:
                product_to_17[sml.product_id.default_code] += sml.qty_done

        product_from_17 = {}
        for sml in stock_move_line_from_17_ids:
            if sml.product_id.default_code not in product_from_17:
                product_from_17[sml.product_id.default_code] = sml.qty_done
            else:
                product_from_17[sml.product_id.default_code] += sml.qty_done

        # Cột "Hỏng/mất" = số lượng hàng VÀO kho hỏng (id=18) trừ số lượng RA khỏi kho hỏng (18),
        # tính cho từng sản phẩm. Đã gồm "Báo hỏng/mất CCDC" (kho cho mượn 17 -> 18).
        # Khi lọc 1 kho: chỉ tính move ra/vào 18 liên quan kho đó; nếu ra/vào lệch thì để âm (chấp nhận).
        # Báo hỏng từ kho cho mượn (17) chỉ gộp khi xem toàn bộ kho.
        damage_wh_ids = list(location_ids)
        if not self.stock:
            damage_wh_ids.append(17)
        damage_net_sql = '''
            SELECT pt.default_code AS code,
                COALESCE(SUM(mv.qin), 0) - COALESCE(SUM(mv.qout), 0) AS net
            FROM (
                SELECT product_id, location_id AS w, qty_done AS qin, 0 AS qout
                FROM stock_move_line WHERE location_dest_id = 18 AND state = 'done'
                UNION ALL
                SELECT product_id, location_dest_id AS w, 0 AS qin, qty_done AS qout
                FROM stock_move_line WHERE location_id = 18 AND state = 'done'
            ) mv
                JOIN product_product pp ON pp.id = mv.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE mv.w IN {wh}
                AND pt.x_type = 'product' AND pt.active = 't' AND pt.x_product_type = 'tools'
            GROUP BY pt.default_code
        '''.format(wh=tuple(damage_wh_ids + [0, 0]))
        self._cr.execute(damage_net_sql)
        hong_mat_by_code = {d['code']: (d['net'] or 0) for d in self._cr.dictfetchall()}

        stock_move_line_to_8_ids = self.env['stock.move.line'].search(
            [('location_dest_id', '=', 8), ('state', '=', 'done')])
        stock_move_line_from_8_ids = self.env['stock.move.line'].search(
            [('location_id', '=', 8), ('state', '=', 'done')])

        product_to_8 = {}
        for sml in stock_move_line_to_8_ids:
            if sml.product_id.default_code not in product_to_8:
                product_to_8[sml.product_id.default_code] = sml.qty_done
            else:
                product_to_8[sml.product_id.default_code] += sml.qty_done

        product_from_8 = {}
        for sml in stock_move_line_from_8_ids:
            if sml.product_id.default_code not in product_from_8:
                product_from_8[sml.product_id.default_code] = sml.qty_done
            else:
                product_from_8[sml.product_id.default_code] += sml.qty_done

        # Tính qty nhập kho từ kiểm kê / không qua picking (inventory_adj) vào kho được chọn,
        # chia theo: trước năm báo cáo (qty_before) và 12 tháng trong năm (qty_t1..qty_t12).
        # Tách query riêng để tránh JOIN nhân hàng với purchase_order_line ở SQL chính.
        # NET: kiểm kê VÀO kho (location_dest_id in stock) mang dấu +, kiểm kê RA khỏi kho
        # (location_id in stock) mang dấu -. Trước đây chỉ lấy chiều vào nên tồn đầu/nhập bị
        # thổi phồng (vd DELL-V3478: vào 12, ra 7 -> đúng phải là net 5, không phải 12).
        # Subquery mv ký dấu sẵn cho từng move line rồi mới gộp theo kỳ.
        inv_adj_sql = '''
            SELECT code,
                COALESCE(SUM(CASE WHEN d < '{year}-1-1' THEN nq ELSE 0 END), 0) AS qty_before,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 1  THEN nq ELSE 0 END), 0) AS qty_t1,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 2  THEN nq ELSE 0 END), 0) AS qty_t2,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 3  THEN nq ELSE 0 END), 0) AS qty_t3,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 4  THEN nq ELSE 0 END), 0) AS qty_t4,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 5  THEN nq ELSE 0 END), 0) AS qty_t5,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 6  THEN nq ELSE 0 END), 0) AS qty_t6,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 7  THEN nq ELSE 0 END), 0) AS qty_t7,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 8  THEN nq ELSE 0 END), 0) AS qty_t8,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 9  THEN nq ELSE 0 END), 0) AS qty_t9,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 10 THEN nq ELSE 0 END), 0) AS qty_t10,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 11 THEN nq ELSE 0 END), 0) AS qty_t11,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM d) = {year} AND EXTRACT(MONTH FROM d) = 12 THEN nq ELSE 0 END), 0) AS qty_t12
            FROM (
                SELECT pt.default_code AS code,
                    (sm.date + interval '7 hours')::date AS d,
                    CASE WHEN sml.location_dest_id IN {stock} THEN sml.qty_done
                         WHEN sml.location_id IN {stock} THEN -sml.qty_done
                         ELSE 0 END AS nq
                FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                    JOIN product_product pp ON sml.product_id = pp.id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    LEFT JOIN stock_picking sp ON sml.picking_id = sp.id
                    LEFT JOIN stock_inventory si ON sm.inventory_id = si.id
                WHERE sml.state = 'done'
                    AND (sml.location_dest_id IN {stock} OR sml.location_id IN {stock})
                    AND (si.id IS NOT NULL OR sp.id IS NULL)
                    AND pt.x_type = 'product' AND pt.active = 't' AND pt.x_product_type = 'tools'
            ) mv
            GROUP BY code
        '''.format(year=self.year, stock=tuple(location_ids + [0, 0]))
        self._cr.execute(inv_adj_sql)
        inv_adj_data = {row['code']: row for row in self._cr.dictfetchall()}

        # Hỏng/mất theo tháng (cột 31-42): net (hàng VÀO kho hỏng 18 − hàng RA khỏi 18) theo từng
        # tháng, đồng bộ với cách tính cột tổng "Hỏng/mất" (cột 13). Tính riêng để tránh 2 lỗi của
        # SQL chính: (1) lọc location_id in {stock} bỏ sót báo hỏng/mất CCDC từ kho cho mượn (17);
        # (2) JOIN purchase_order_line làm nhân dòng. Hàng ra khỏi 18 mang dấu âm (mv.q < 0).
        damage_month_sql = '''
            SELECT pt.default_code AS code,
                {month_cases}
            FROM (
                SELECT sml.product_id, sm.date + interval '7 hours' AS d, sml.qty_done AS q
                FROM stock_move_line sml JOIN stock_move sm ON sm.id = sml.move_id
                WHERE sml.state = 'done' AND sml.location_dest_id = 18 AND sml.location_id IN {wh}
                UNION ALL
                SELECT sml.product_id, sm.date + interval '7 hours' AS d, -sml.qty_done AS q
                FROM stock_move_line sml JOIN stock_move sm ON sm.id = sml.move_id
                WHERE sml.state = 'done' AND sml.location_id = 18 AND sml.location_dest_id IN {wh}
            ) mv
                JOIN product_product pp ON pp.id = mv.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE EXTRACT(YEAR FROM mv.d) = {year}
                AND pt.x_type = 'product' AND pt.active = 't' AND pt.x_product_type = 'tools'
            GROUP BY pt.default_code
        '''.format(
            month_cases=', '.join(
                "COALESCE(SUM(CASE WHEN EXTRACT(MONTH FROM mv.d) = %d "
                "THEN mv.q ELSE 0 END), 0) AS dmg_t%d" % (m, m) for m in range(1, 13)
            ),
            wh=tuple(damage_wh_ids + [0, 0]), year=self.year,
        )
        self._cr.execute(damage_month_sql)
        damage_month_data = {row['code']: row for row in self._cr.dictfetchall()}

        # HARD CODE theo yêu cầu: 2 sản phẩm Dell (template 5275 DELL-V3478, 5336 DELL-V3468)
        # nhập vào kho qua phiếu KIỂM KÊ nhưng bản chất là nhập mua. Cột "nhập mua trong kỳ" đã
        # bỏ toàn bộ move kiểm kê, nên cộng bù thủ công qty của đúng các move line chỉ định:
        #   sml 5678 (+2), 5944 (+3) -> DELL-V3478 (tmpl 5275)
        #   sml 5940 (+2)            -> DELL-V3468 (tmpl 5336)
        extra_nhap_mua_sml_ids = (5678, 5944, 5940)
        self._cr.execute('''
            SELECT pt.default_code AS code, COALESCE(SUM(sml.qty_done), 0) AS qty
            FROM stock_move_line sml
                JOIN product_product pp ON pp.id = sml.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE sml.id IN %s AND sml.state = 'done'
            GROUP BY pt.default_code
        ''', (extra_nhap_mua_sml_ids,))
        extra_nhap_mua = {r0['code']: (r0['qty'] or 0) for r0 in self._cr.dictfetchall()}

        # Tồn đầu kỳ (cột BD/56): số lượng nhập theo PHIẾU (type_1/2/8) trước năm báo cáo.
        # Tách query riêng để tránh fan-out do JOIN purchase_order_line ở SQL chính làm nhân dòng
        # qty_done (amount_before ở SQL chính bị nhân theo số dòng PO trong năm → giá trị sai).
        amount_before_sql = '''
            SELECT pt.default_code AS code,
                COALESCE(SUM(CASE WHEN spt.x_type IN ('type_1','type_2','type_8')
                                   AND (sm.date + interval '7 hours')::date < '{year}-1-1'
                                   AND sml.location_dest_id IN {stock}
                                  THEN sml.qty_done ELSE 0 END), 0) AS qty_phieu_before
            FROM stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
                JOIN stock_picking sp ON sml.picking_id = sp.id
                JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                JOIN product_product pp ON sml.product_id = pp.id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE sml.state = 'done'
                AND pt.x_type = 'product' AND pt.active = 't' AND pt.x_product_type = 'tools'
            GROUP BY pt.default_code
        '''.format(year=self.year, stock=tuple(location_ids + [0, 0]))
        self._cr.execute(amount_before_sql)
        phieu_before_data = {r0['code']: (r0['qty_phieu_before'] or 0) for r0 in self._cr.dictfetchall()}

        # Nhập từ NCC theo tháng (cột 19-30 và nửa "supplier" của cột giá trị 43-54): đếm hàng
        # thực nhận từ nhà cung cấp (loc 4 -> kho) theo NGÀY VỀ KHO THỰC TẾ (ngày move). Tách
        # query riêng, KHÔNG join purchase_order_line -> vừa khử fan-out (nhân dòng theo số PO
        # cùng tháng), vừa bỏ gate theo x_date_received (không phụ thuộc ngày ghi trên PO).
        supplier_qty_sql = '''
            SELECT pt.default_code AS code,
                {month_cases}
            FROM stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
                JOIN stock_location sl1 ON sml.location_id = sl1.id
                JOIN product_product pp ON sml.product_id = pp.id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE sml.state = 'done' AND sl1.usage = 'supplier' AND sml.location_id = 4
                AND sml.location_dest_id IN {stock}
                AND pt.x_type = 'product' AND pt.active = 't' AND pt.x_product_type = 'tools'
            GROUP BY pt.default_code
        '''.format(
            month_cases=', '.join(
                "COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM sm.date + interval '7 hours') = %d "
                "AND EXTRACT(MONTH FROM sm.date + interval '7 hours') = %d "
                "THEN sml.qty_done ELSE 0 END), 0) AS sq_t%d" % (self.year, m, m)
                for m in range(1, 13)
            ),
            stock=tuple(location_ids + [0, 0]),
        )
        self._cr.execute(supplier_qty_sql)
        supplier_qty_data = {row0['code']: row0 for row0 in self._cr.dictfetchall()}

        # Nhóm cột SỐ LƯỢNG 8-12: tính lại bằng ĐÚNG điều kiện như SQL chính nhưng ở query sạch
        # (không join purchase_order_line/account_tax) -> khử fan-out nhân dòng theo số PO trong năm.
        # Giữ nguyên semantics từng cột (không lọc state để khớp SQL chính; lũy kế <= {year}-12-31).
        # Cột 13/14/15 (hong_mat, ton_kho, cho_muon) đã tính sạch riêng ở Python nên không đụng.
        qty_cols_sql = '''
            SELECT pt.default_code AS code,
                COALESCE(SUM(CASE WHEN (spt.x_type IN ('type_1','type_2','type_8')
                    AND (sm.date + interval '7 hours')::date <= '{year}-12-31'
                    AND sl2.id IN {stock} AND sm.picking_id IS NOT NULL) THEN sml.qty_done END), 0) AS nhap_mua_trong_ki,
                COALESCE(SUM(CASE WHEN (spt.x_type = 'type_7'
                    AND (sm.date + interval '7 hours')::date <= '{year}-12-31'
                    AND sl1.usage = 'internal' AND sl2.usage = 'internal' AND sm.picking_id IS NOT NULL
                    AND (sl1.id IN {stock} OR sl2.id IN {stock})) THEN sml.qty_done END), 0) AS nhap_chuyen_kho,
                COALESCE(SUM(CASE WHEN (spt.x_type = 'type_6' AND sm.picking_id IS NOT NULL
                    AND (sm.date + interval '7 hours')::date <= '{year}-12-31'
                    AND sl2.id IN {stock}) THEN sml.qty_done END), 0) AS nhap_tra_lai,
                COALESCE(SUM(CASE WHEN (spt.x_type = 'type_4' AND sm.picking_id IS NOT NULL
                    AND (sm.date + interval '7 hours')::date <= '{year}-12-31'
                    AND sl1.id IN {stock}) THEN sml.qty_done END), 0) AS xuat_muon,
                COALESCE(SUM(CASE WHEN (spt.x_type = 'type_7' AND sm.picking_id IS NOT NULL
                    AND (sm.date + interval '7 hours')::date <= '{year}-12-31'
                    AND sl1.usage = 'internal' AND sl2.usage = 'internal'
                    AND sl1.id IN {stock}) THEN sml.qty_done END), 0) AS chuyen_kho
            FROM stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
                JOIN product_product pp ON sml.product_id = pp.id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN stock_picking sp ON sml.picking_id = sp.id
                LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                LEFT JOIN stock_location sl1 ON sml.location_id = sl1.id
                LEFT JOIN stock_location sl2 ON sml.location_dest_id = sl2.id
            WHERE pt.x_type = 'product' AND pt.active = 't' AND pt.x_product_type = 'tools'
            GROUP BY pt.default_code
        '''.format(year=self.year, stock=tuple(location_ids + [0, 0]))
        self._cr.execute(qty_cols_sql)
        qty_cols_data = {row0['code']: row0 for row0 in self._cr.dictfetchall()}

        row = 5
        x = 1
        for r in recs:
            inv_adj = inv_adj_data.get(r['default_code'], {}) or {}
            std_price = r.get('standard_price') or 0
            # Tồn đầu = (qty nhập theo phiếu trước năm + qty kiểm kê trước năm) * đơn giá chuẩn.
            # Dùng qty sạch (phieu_before_data + inv_adj) thay cho amount_before của SQL chính để
            # loại fan-out nhân dòng từ join purchase_order_line.
            r['amount_before'] = (phieu_before_data.get(r['default_code'], 0)
                                  + (inv_adj.get('qty_before') or 0)) * std_price
            # Ghi đè supplier_qty_tN bằng số sạch (đếm theo ngày về kho, không fan-out, không gate PO).
            sup = supplier_qty_data.get(r['default_code'], {}) or {}
            for _m in range(1, 13):
                r['supplier_qty_t%d' % _m] = sup.get('sq_t%d' % _m, 0) or 0
            # Ghi đè nhóm cột số lượng 8-12 bằng số sạch (khử fan-out). Cột 8 sau đó được cộng
            # thêm hard-code (extra_nhap_mua) ở dưới; cột 13/14/15 tính sạch riêng nên bỏ qua.
            qc = qty_cols_data.get(r['default_code'], {}) or {}
            for _k in ('nhap_mua_trong_ki', 'nhap_chuyen_kho', 'nhap_tra_lai', 'xuat_muon', 'chuyen_kho'):
                r[_k] = qc.get(_k, 0) or 0

            ws.cell(row, 1).value, ws.cell(row, 1).style = x, highlight
            ws.cell(row, 2).value, ws.cell(row, 2).style = r['default_code'], highlight
            ws.cell(row, 3).value, ws.cell(row, 3).style = r['ten_san_pham'], highlight
            ws.cell(row, 4).value, ws.cell(row, 4).style = r['don_vi'], highlight
            ws.cell(row, 5).value, ws.cell(row, 5).style = r['x_product_company'], highlight
            ws.cell(row, 6).value, ws.cell(row, 6).style = r['x_code_brand'], highlight
            ws.cell(row, 7).value, ws.cell(row, 7).style = r['x_product_type'], highlight
            r['nhap_mua_trong_ki'] = (r.get('nhap_mua_trong_ki') or 0) + extra_nhap_mua.get(r['default_code'], 0)
            ws.cell(row, 8).value, ws.cell(row, 8).style = r['nhap_mua_trong_ki'], highlight
            ws.cell(row, 9).value, ws.cell(row, 9).style = r['nhap_chuyen_kho'], highlight
            ws.cell(row, 10).value, ws.cell(row, 10).style = r['nhap_tra_lai'], highlight
            ws.cell(row, 11).value, ws.cell(row, 11).style = r['xuat_muon'], highlight
            ws.cell(row, 12).value, ws.cell(row, 12).style = r['chuyen_kho'], highlight
            # Hỏng/mất: net theo nguồn đã floor 0 ở mức (sản phẩm, kho), tính sẵn ở hong_mat_by_code.
            r['hong_mat'] = hong_mat_by_code.get(r['default_code'], 0)
            ws.cell(row, 13).value, ws.cell(row, 13).style = r['hong_mat'], highlight
            r['ton_kho'] = 0
            if r['default_code'] in product_to_8:
                r['ton_kho'] = r['ton_kho'] + product_to_8[r['default_code']]

            if r['default_code'] in product_from_8:
                r['ton_kho'] = r['ton_kho'] - product_from_8[r['default_code']]
            ws.cell(row, 14).value, ws.cell(row, 14).style = r['ton_kho'], highlight
            r['cho_muon'] = 0
            if r['default_code'] in product_to_17:
                r['cho_muon'] = r['cho_muon'] + product_to_17[r['default_code']]

            if r['default_code'] in product_from_17:
                r['cho_muon'] = r['cho_muon'] - product_from_17[r['default_code']]
            ws.cell(row, 15).value, ws.cell(row, 15).style = r['cho_muon'], highlight

            ws.cell(row, 16).value, ws.cell(row, 16).style = '=(N%s+O%s)' % (row, row), highlight

            # if r['default_code'] in product_lost_17_18:
            #     ws.cell(row, 13).value, ws.cell(row, 13).style = r['hong_mat'] + product_lost_17_18[r['default_code']], highlight
            # else:
            #     ws.cell(row, 13).value, ws.cell(row, 13).style = r['hong_mat'], highlight

            # ws.cell(row, 16).value, ws.cell(row, 16).style = '=(H%s-M%s)' % (row, row), highlight
            # tan so kiem ke
            ws.cell(row, 17).value, ws.cell(row, 17).style = r.get('tan_so_kiem_ke', '-'), highlight1

            ws.cell(row, 18).value, ws.cell(row, 18).style = r['ngay_kiem_ke'], highlight1

            ws.cell(row, 19).value, ws.cell(row, 19).style = r['supplier_qty_t1'], highlight
            ws.cell(row, 20).value, ws.cell(row, 20).style = r['supplier_qty_t2'], highlight
            ws.cell(row, 21).value, ws.cell(row, 21).style = r['supplier_qty_t3'], highlight
            ws.cell(row, 22).value, ws.cell(row, 22).style = r['supplier_qty_t4'], highlight
            ws.cell(row, 23).value, ws.cell(row, 23).style = r['supplier_qty_t5'], highlight
            ws.cell(row, 24).value, ws.cell(row, 24).style = r['supplier_qty_t6'], highlight
            ws.cell(row, 25).value, ws.cell(row, 25).style = r['supplier_qty_t7'], highlight
            ws.cell(row, 26).value, ws.cell(row, 26).style = r['supplier_qty_t8'], highlight
            ws.cell(row, 27).value, ws.cell(row, 27).style = r['supplier_qty_t9'], highlight
            ws.cell(row, 28).value, ws.cell(row, 28).style = r['supplier_qty_t10'], highlight
            ws.cell(row, 29).value, ws.cell(row, 29).style = r['supplier_qty_t11'], highlight
            ws.cell(row, 30).value, ws.cell(row, 30).style = r['supplier_qty_t12'], highlight

            # Hỏng/mất theo tháng: dùng dữ liệu tính sạch (đã gồm kho cho mượn 17, không bị nhân dòng PO)
            dmg = damage_month_data.get(r['default_code'], {}) or {}
            ws.cell(row, 31).value, ws.cell(row, 31).style = dmg.get('dmg_t1', 0), highlight
            ws.cell(row, 32).value, ws.cell(row, 32).style = dmg.get('dmg_t2', 0), highlight
            ws.cell(row, 33).value, ws.cell(row, 33).style = dmg.get('dmg_t3', 0), highlight
            ws.cell(row, 34).value, ws.cell(row, 34).style = dmg.get('dmg_t4', 0), highlight
            ws.cell(row, 35).value, ws.cell(row, 35).style = dmg.get('dmg_t5', 0), highlight
            ws.cell(row, 36).value, ws.cell(row, 36).style = dmg.get('dmg_t6', 0), highlight
            ws.cell(row, 37).value, ws.cell(row, 37).style = dmg.get('dmg_t7', 0), highlight
            ws.cell(row, 38).value, ws.cell(row, 38).style = dmg.get('dmg_t8', 0), highlight
            ws.cell(row, 39).value, ws.cell(row, 39).style = dmg.get('dmg_t9', 0), highlight
            ws.cell(row, 40).value, ws.cell(row, 40).style = dmg.get('dmg_t10', 0), highlight
            ws.cell(row, 41).value, ws.cell(row, 41).style = dmg.get('dmg_t11', 0), highlight
            ws.cell(row, 42).value, ws.cell(row, 42).style = dmg.get('dmg_t12', 0), highlight

            ws.cell(row, 43).value, ws.cell(row, 43).style = (r.get('supplier_qty_t1', 0) + (inv_adj.get('qty_t1') or 0)) * std_price, highlight
            ws.cell(row, 44).value, ws.cell(row, 44).style = (r.get('supplier_qty_t2', 0) + (inv_adj.get('qty_t2') or 0)) * std_price, highlight
            ws.cell(row, 45).value, ws.cell(row, 45).style = (r.get('supplier_qty_t3', 0) + (inv_adj.get('qty_t3') or 0)) * std_price, highlight
            ws.cell(row, 46).value, ws.cell(row, 46).style = (r.get('supplier_qty_t4', 0) + (inv_adj.get('qty_t4') or 0)) * std_price, highlight
            ws.cell(row, 47).value, ws.cell(row, 47).style = (r.get('supplier_qty_t5', 0) + (inv_adj.get('qty_t5') or 0)) * std_price, highlight
            ws.cell(row, 48).value, ws.cell(row, 48).style = (r.get('supplier_qty_t6', 0) + (inv_adj.get('qty_t6') or 0)) * std_price, highlight
            ws.cell(row, 49).value, ws.cell(row, 49).style = (r.get('supplier_qty_t7', 0) + (inv_adj.get('qty_t7') or 0)) * std_price, highlight
            ws.cell(row, 50).value, ws.cell(row, 50).style = (r.get('supplier_qty_t8', 0) + (inv_adj.get('qty_t8') or 0)) * std_price, highlight
            ws.cell(row, 51).value, ws.cell(row, 51).style = (r.get('supplier_qty_t9', 0) + (inv_adj.get('qty_t9') or 0)) * std_price, highlight
            ws.cell(row, 52).value, ws.cell(row, 52).style = (r.get('supplier_qty_t10', 0) + (inv_adj.get('qty_t10') or 0)) * std_price, highlight
            ws.cell(row, 53).value, ws.cell(row, 53).style = (r.get('supplier_qty_t11', 0) + (inv_adj.get('qty_t11') or 0)) * std_price, highlight
            ws.cell(row, 54).value, ws.cell(row, 54).style = (r.get('supplier_qty_t12', 0) + (inv_adj.get('qty_t12') or 0)) * std_price, highlight

            ws.cell(row, 55).value, ws.cell(row, 55).style = '=Sum(AQ%s:BB%s)' % (row, row), highlight
            ws.cell(row, 56).value, ws.cell(row, 56).style = r['amount_before'], highlight
            broken_lose = r.get('hong_mat', 0) * r.get('standard_price', 0)
            ws.cell(row, 57).value, ws.cell(row, 57).style = broken_lose, highlight
            ws.cell(row, 58).value, ws.cell(row, 58).style = '=(BC%s + BD%s -BE%s)' % (row, row, row), highlight

            x += 1
            row += 1
        ws.cell(1, 45).value = date.today()
        ws.cell(2, 45).value = date.today().year
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Báo cáo tồn kho công cụ dụng cụ',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/' + str(attachment_id.id) + '?download=true',
            'target': 'new',
        }
