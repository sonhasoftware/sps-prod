import datetime as dt

from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError


class PurchaseTrackingSupplierWizards(models.TransientModel):
    _name = "purchase.tracking.supplier.wizards"
    _description = "Nhập tham số báo cáo theo dõi NCC"

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)

    date_from = fields.Date("Từ ngày", required='True')
    date_to = fields.Date("Đến ngày", required='True')

    @api.model
    def default_get(self, field):
        res = super(PurchaseTrackingSupplierWizards, self).default_get(field)
        today = date.today()
        last_year = today.year - 1
        default_date_from = datetime(last_year, today.month, today.day)
        default_date_to = today
        res.update({
            'date_from': default_date_from,
            'date_to': default_date_to
        })
        return res

    def action_report(self):
        self._cr.execute(
            "delete from purchase_tracking_supplier where master_key = {key}".format(key=self.master_key))
        sql = f''' 
                select res_partner.name  as supplier,
                    sum(account_move_line.debit) as amount
                from account_move_line 
                    left join purchase_order_line on account_move_line.purchase_line_id = purchase_order_line.id
                    left join purchase_order on purchase_order_line.order_id = purchase_order.id
                    left join res_partner  on purchase_order.partner_id = res_partner.id
                where account_move_line.move_id in 
                    (select account_move_line.move_id 
                    from account_move_line 
                    where 	account_move_line.parent_state = 'posted' 
                            and account_move_line.account_id = 77	
                            and account_move_line.credit > 0
                    ) 
                    and account_move_line.debit > 0
                    and account_move_line.purchase_line_id is not null	
                    and account_move_line.date between '{self.date_from}' and '{self.date_to}' 
                group by supplier
                order by amount desc ;
                '''
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()
        x = 1
        for r in recs:
            insert = '''INSERT INTO purchase_tracking_supplier (master_key ,index,supplier,amount)
                                   VALUES ({key},{index},'{supplier}',{amount})
                               '''.format(key=self.master_key,
                                          index=x,
                                          supplier=r['supplier'],
                                          amount=r['amount'])
            self._cr.execute(insert)
            x += 1
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo theo dõi nhà cung cấp',
            'view_mode': 'tree',
            'res_model': 'purchase.tracking.supplier',
            'view_id': self.env.ref('effective_management.purchase_tracking_supplier_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }
