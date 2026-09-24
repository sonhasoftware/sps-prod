# -*- coding: utf-8 -*-

from odoo import models, fields


class CashReport(models.Model):
    _name = 'cash.popup'
    _description = 'Báo cáo Sổ quỹ tiền mặt'

    journal_ids = fields.Many2many('account.journal', string='Sổ nhật ký', domain=[('type', '=', 'cash')])
    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)

    def loai_bo_apostrophe(self,chuoi):
        chuoi_moi = ""
        for ky_tu in chuoi:
            if ky_tu != "'":
                chuoi_moi += ky_tu
        return chuoi_moi

    def action_cash_popup(self):

        filter_journal = ""
        if self.journal_ids:
            a = self.journal_ids.ids
            filter_journal = "and aj.id in " + str(tuple(a + [0, 0]))
        else:
            filter_journal = "and aj.type = 'cash' "

        self._cr.execute(
            "delete from cash_report where master_key = {key}".format(key=self.master_key))
        sql = '''
            select 
                ngay,
                nguoi_nhan,
                ten_khach_hang,
                dien_giai,
                so3.name as ma_du_an,
                chung_tu,
                ma_khoan_tien,
                kieu_thanh_toan,
                chi,
                thu,
                ghi_chu,
                so_chung_tu
            from 
                (select 
                    amx.date as ngay,
                    case when ru.id is not null then coalesce(rp.name,'') else coalesce(ap.x_receiver,'') end as nguoi_nhan,
                    case when ru.id is not null then coalesce(rc.name,'') else coalesce(rp.name,rc.name) end as ten_khach_hang,
                    coalesce(amx.ref,'') as dien_giai,
                    case	
                        when aa.id is not null and pd.id is not null then pd.code_project  
                        when aa.id is not null and pd.id is null and aa."type" = 'supplier' then po_rate.so_id
                        when aar.id is not null then prd.main_project 
                        when am.id is not null and pd.id is not null then pd.code_project 
                        when am.id is not null and pd.id is null then am.x_order_id 
                        when so.id is not null then so.id 
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is not null and ap.is_internal_transfer is false and ap.x_pay_cost is false then pd.code_project 
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and ap.is_internal_transfer is false and ap.x_pay_cost is true then pl.x_sale_project_id  
                        else null
                    end as ma_du_an,
                    coalesce(ap.x_license_type,'') as chung_tu,
                    coalesce(cm.code_money,'') as ma_khoan_tien,
                    coalesce(aj.name,'') as kieu_thanh_toan,
                    case	
                        when aa.id is not null and pd.id is not null then pd.amount_total  
                        when aa.id is not null and pd.id is null and aa."type" = 'supplier' then po_rate.pol_so_rate*ap.amount  
                        when aa.id is not null and pd.id is null and aa."type" = 'internal' then ap.amount 
                        when aar.id is not null and ap.payment_type = 'outbound' then prd.amount_repay 
                        when am.id is not null and pd.id is not null and ap.payment_type = 'outbound' then pd.amount_total 
                        when am.id is not null and pd.id is null and ap.payment_type = 'outbound' then ap.amount  
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is not null and ap.x_pay_cost is false and ap.payment_type = 'outbound' then pd.amount_total
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is null and ap.x_pay_cost is false and ap.payment_type = 'outbound' then ap.amount 
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and ap.x_pay_cost is true and ap.payment_type = 'outbound' then pl.amount
                        else 0
                    end as chi,
                    case	
                        when aar.id is not null and ap.payment_type = 'inbound' then prd.amount_repay 
                        when am.id is not null and pd.id is not null and ap.payment_type = 'inbound' then pd.amount_total 
                        when am.id is not null and pd.id is null and ap.payment_type = 'inbound' then ap.amount 
                        when so.id is not null then ap.amount 
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is not null and ap.x_pay_cost is false and ap.payment_type = 'inbound' then pd.amount_total
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is null and ap.x_pay_cost is false and ap.payment_type = 'inbound' then ap.amount 
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and ap.x_pay_cost is true and ap.payment_type = 'inbound' then pl.amount 
                        else 0
                    end as thu,
                    coalesce(ap.x_note,'') as ghi_chu,
                    coalesce(amx.name,'') as so_chung_tu
                from account_payment ap 
                left join account_move amx on amx.payment_id = ap.id 
                left join account_journal aj on aj.id = amx.journal_id 
                left join res_partner rp on ap.partner_id = rp.id
                left join res_users ru on ap.partner_id = ru.partner_id
                left join res_company rc on 1 = 1 and rc.id=1
                left join code_money cm on cm.id = ap.x_code_money 
                left join project_detail pd on pd.payment_id = ap.id and ap.is_internal_transfer is false and ap.x_pay_cost is false
                left join account_advance aa on aa.id = ap.x_origin_advance_id 
                left join 
                    (
                        select 
                            po.id as po_id,
                            so2.id as so_id,
                            case when po.amount_total = 0 then 0 else sum(pol.price_total)/po.amount_total end as pol_so_rate
                        from purchase_order po 
                        left join purchase_order_line pol on pol.order_id = po.id
                        left join project_project pp on pp.id = pol.x_project_id 
                        left join sale_order so2 on so2.id = pp.x_order_id 
                        group by po.id,so2.id,po.amount_total
                    ) as po_rate on ap.x_origin_advance_id is not null and pd.id is null and aa.type = 'supplier' and aa.po_id = po_rate.po_id
                left join account_advance_repay aar on aar.id = ap.x_origin_repay_id 
                left join project_repay_detail prd on prd.payment_id = ap.id and ap.x_origin_repay_id is not null
                left join account_move am on am.id = ap.x_origin_move_id 
                left join sale_order so on so.id = ap.x_origin_so_id 
                left join payment_line pl on pl.payment_id = ap.id and ap.x_pay_cost is true and aa.id is null and aar.id is null and am.id is null and so.id is null
                where amx.state = 'posted' {journal_id}
                )X
            left join sale_order so3 on so3.id = X.ma_du_an
            order by X.ngay,X.so_chung_tu
        '''.format(journal_id=filter_journal)
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()
        x = 1
        luy_ke = 0.0
        for r in recs:
            du_moi = round(r['thu']) - round(r['chi']) +luy_ke
            insert = '''INSERT INTO cash_report (master_key,number_license,date,receive_or_pay,name,explain,code_project,
                                                type_license,code,type,thu,chi,so_du,note)
                              VALUES ({key},'{number_license}','{date}','{receive_or_pay}','{name}','{explain}','{code_project}',
                              '{type_license}','{code}','{type}',{thu},{chi},{so_du},'{note}')
                                    '''.format(key=self.master_key,
                                               number_license=r['so_chung_tu'],
                                               date=r['ngay'],
                                               receive_or_pay=r['nguoi_nhan'],
                                               name=r['ten_khach_hang'],
                                               explain=self.loai_bo_apostrophe(r['dien_giai']) or '',
                                               code_project=r['ma_du_an'] or '',
                                               type_license=r['chung_tu'],
                                               code=r['ma_khoan_tien'],
                                               type=r['kieu_thanh_toan'],
                                               thu=round(r['thu']),
                                               chi=round(r['chi']),
                                               so_du=du_moi,
                                               note=r['ghi_chu'])
            self._cr.execute(insert)
            x += 1
            luy_ke = du_moi
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo Sổ quỹ tiền mặt',
            'view_mode': 'tree',
            'res_model': 'cash.report',
            'view_id': self.env.ref('account_saving.cash_report_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'current',
            'limit': 10000000

        }
