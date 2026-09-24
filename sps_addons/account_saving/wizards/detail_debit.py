# -*- coding: utf-8 -*-

from odoo import models, fields


class DetailDebitPopup(models.Model):
    _name = 'detail.debit.popup'
    _description = 'Báo cáo chi tiết công nợ khách hàng / nhà cung cấp'

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
    partner_id = fields.Many2one('res.partner', string='Tên khách hàng/NCC', required='True')
    date_from = fields.Date('Từ ngày', required=1)
    date_to = fields.Date('Đến ngày', required=1)


    def action_detail_debit_popup(self):
        filter_partner = ""
        if self.partner_id:
            filter_partner = "and rp.id = " + str(self.partner_id.id)
        else:
            filter_partner = ''
            
        self._cr.execute(
            "delete from detail_debit where master_key = {key}".format(key=self.master_key))
        sql = '''
        -- Trong kỳ
            select 
                * 
            from
                (
                    SELECT 1 stt,
                            am.date::date as ngayvaoso, 
                            am.name as mabt,
                            am.ref as diengiai, 
                            aml.debit as debit,
                            aml.credit as credit,
                            so.name as ma_du_an
                    FROM account_move_line aml
                    left JOIN account_move am ON aml.move_id = am.id
                    left JOIN account_account aa on aml.account_id = aa.id
                    LEFT JOIN sale_order so on aml.x_sale_project_id = so.id
                    LEFT JOIN res_partner rp on aml.partner_id = rp.id
                    WHERE am.state = 'posted'
                    AND am.date::date between '{date_from}' and '{date_to}'
                    and aa.reconcile is true
                    {filter_partner}
                    order by am.date::date
                )A
             
            UNION all
            
            -- Đầu kỳ
            SELECT 2 stt,
                    null::date ngayvaoso,
                    '' mabt, 
                    'Số dư đầu kỳ' as diengiai, 
                    case
                        when (sum(aml.debit) - sum(aml.credit)) > 0 then sum(aml.debit) - sum(aml.credit)
                        else 0 end  as debit,
                    case
                        when (sum(aml.debit) - sum(aml.credit)) < 0 then sum(aml.credit) - sum(aml.debit)
                        else 0 end  as credit,
                    '' as ma_du_an
            FROM account_move_line aml
            left JOIN account_move am ON aml.move_id = am.id
            LEFT JOIN sale_order so on aml.x_sale_project_id = so.id
            LEFT JOIN res_partner rp on aml.partner_id = rp.id
            left join account_account aa on aa.id = aml.account_id 
            WHERE am.state = 'posted'
            and aa.reconcile is true
            AND am.date::date < '{date_from}'
            {filter_partner}
            
            UNION ALL
            
            -- cộng phát sinh
            SELECT 3 stt,
                    null::date ngayvaoso,
                    '' mabt, 
                    'Tổng số phát sinh trong kỳ' diengiai, 
                    sum(aml.debit) as debit,
                    sum(aml.credit) as credit,
                    '' as ma_du_an
            FROM account_move_line aml
            left JOIN account_move am ON aml.move_id = am.id
            left JOIN account_account aa on aml.account_id = aa.id
            LEFT JOIN sale_order so on aml.x_sale_project_id = so.id
            LEFT JOIN res_partner rp on aml.partner_id = rp.id
            WHERE am.state = 'posted'
            and aa.reconcile is true
            AND am.date::date between '{date_from}' and '{date_to}'
            {filter_partner}
            
            UNION ALL
            
            -- Cuối kỳ
            SELECT 4 stt,
                    null::date ngayvaoso,
                    '' mabt, 
                    'Số dư cuối kỳ' diengiai, 
                    case
                        when (sum(aml.debit) - sum(aml.credit)) > 0 then sum(aml.debit) - sum(aml.credit)
                        else 0 end  as debit,
                    case
                        when (sum(aml.debit) - sum(aml.credit)) < 0 then abs(sum(aml.debit) - sum(aml.credit))
                        else 0 end  as credit,
                    '' ma_du_an
            FROM account_move_line aml
            left JOIN account_move am ON aml.move_id = am.id
            left join account_account aa on aa.id = aml.account_id 
            LEFT JOIN sale_order so on aml.x_sale_project_id = so.id
            LEFT JOIN res_partner rp on aml.partner_id = rp.id
            WHERE am.state = 'posted'
            and aa.reconcile is true
            AND am.date::date <= '{date_to}'
            {filter_partner}
        '''.format(filter_partner=filter_partner, date_from=self.date_from, date_to=self.date_to)
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()
        x = 1
        for r in recs:
            insert = '''INSERT INTO detail_debit (master_key,index,date,number,explain,debt,credit,code)
                                        VALUES ({key},{index},'{date}','{number}','{explain}',{debt},{credit},'{code}')
                                    '''.format(key=self.master_key,
                                               index=x,
                                               date=r['ngayvaoso'] if r['ngayvaoso'] else '',
                                               number=r['mabt'] or '',
                                               explain=r['diengiai'] or '',
                                               # tk=r['tkdoiung'] or '',
                                               debt=r['debit'] or 0,
                                               credit=r['credit'] or 0,
                                               code=r['ma_du_an'] or '', )
            self._cr.execute(insert)
            x += 1
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo chi tiết công nợ khách hàng / nhà cung cấp',
            'view_mode': 'tree',
            'res_model': 'detail.debit',
            'view_id': self.env.ref('account_saving.detail_debit_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'current',
        }
