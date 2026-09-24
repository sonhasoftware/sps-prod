# -*- coding: utf-8 -*-

from odoo import models, fields


class CashReport(models.Model):
    _name = 'cash.debt.popup'
    _description = 'Báo cáo tổng hợp công nợ khách hàng / nhà cung cấp'

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
    from_date = fields.Date(string="Ngày bắt đầu")
    to_date = fields.Date(string="Ngày kết thúc")
    account_ids = fields.Many2many('account.account', string='Tài khoản')

    def action_cash_debt_popup(self):
        self._cr.execute(
            "delete from report_debit where master_key = {key}".format(key=self.master_key))
        accounts = self.env['account.account'].search([('reconcile', '=', True)]).ids
        filter_account = "and aa.id in %s" % str(tuple(accounts))
        if self.account_ids:
            filter_account = "and aa.id in %s" % str(tuple(self.account_ids.ids+[0,0]))
        sql = """
                select 
                    all_data.ma_kh,
                    all_data.ten_kh,
                    all_data.ma_tk as code,
                    all_data.partner_id,
                    case when sum(all_data.debit_dau_ky - all_data.credit_dau_ky) < 0 then 0 else sum(all_data.debit_dau_ky - all_data.credit_dau_ky) end as no_dk,
                    case when sum(all_data.debit_dau_ky - all_data.credit_dau_ky) < 0 then sum(all_data.credit_dau_ky - all_data.debit_dau_ky) else 0 end as co_dk,
                    sum(all_data.debit_trong_ky) as no_tk,
                    sum(all_data.credit_trong_ky) as co_tk,
                    case when sum(all_data.debit - all_data.credit) < 0 then 0 else sum(all_data.debit - all_data.credit) end as no_ck,
                    case when sum(all_data.debit - all_data.credit) < 0 then sum(all_data.credit - all_data.debit) else 0 end as co_ck
                from 
                    (
                        select
                            rp.ref as ma_kh,
                            rp.name as ten_kh,
                            aa.code as ma_tk,
                            rp.id as partner_id,
                            case when am.date < '{from_date}' then aml.debit else 0 end as debit_dau_ky,
                            case when am.date < '{from_date}' then aml.credit else 0 end as credit_dau_ky,
                            case when am.date between '{from_date}' and '{to_date}' then aml.debit else 0 end as debit_trong_ky,
                            case when am.date between '{from_date}' and '{to_date}' then aml.credit else 0 end as credit_trong_ky,
                            aml.debit as debit,
                            aml.credit as credit
                        from account_move_line aml
                        left join account_move am ON aml.move_id = am.id
                        left join account_account aa on aml.account_id = aa.id
                        left join sale_order so on aml.x_sale_project_id = so.id
                        left join res_partner rp on aml.partner_id = rp.id
                        where am.state = 'posted'
                            and am.date::date <= '{to_date}'
                            and aa.reconcile is true
                            and rp.id is not null
                            {filter_account}
                    ) as all_data
                group by all_data.ma_kh, all_data.ten_kh, all_data.ma_tk, all_data.partner_id
                 """.format(to_date=self.to_date, from_date=self.from_date,filter_account = filter_account)
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()
        x = 1
        for r in recs:
            insert = '''INSERT INTO report_debit 
                            (master_key,stt,code,name,tk,first_debit,first_credit,debt,credit,last_debit,last_credit,date_from,date_to,partner_id)
                                VALUES ({master_key},{stt},'{code}','{name}','{tk}',{first_debit},
                                {first_credit},{debt},{credit},{last_debit},{last_credit},'{date_from}','{date_to}',{partner_id})                
            '''.format(master_key=self.master_key,
                       stt=x,
                       code=r['ma_kh'] or '',
                       name=r['ten_kh'] or '',
                       tk=r['code'] or '',
                       first_debit=r['no_dk'] or 0,
                       first_credit=r['co_dk'] or 0,
                       debt=r['no_tk'] or 0,
                       credit=r['co_tk'] or 0,
                       last_debit=r['no_ck'] or 0,
                       last_credit=r['co_ck'] or 0,
                       date_from=self.from_date or '',
                       date_to=self.to_date or '',
                       partner_id=r['partner_id'] or 'null'
                       )
            self._cr.execute(insert)
            x += 1
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo tổng hợp công nợ khách hàng / nhà cung cấp',
            'view_mode': 'tree',
            'res_model': 'report.debit',
            'view_id': self.env.ref('account_saving.report_debit_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'self',

        }
