
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleKeyAccountWizards(models.TransientModel):
    _name = "sale.key.account.wizards"
    _description = "Nhập tham số báo cáo khách hàng đang có hợp đồng"

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

    def action_report(self):
        current_year = self.year
        self._cr.execute("delete from sale_key_account where master_key = {key}".format(key=self.master_key))

        sql = f'''select  view_base.year_orderdate,
                            view_base.month_orderdate,
                            view_base.name_keyaccount,
                            sum(view_base.amount_untaxed) as amount_untaxed
                    from
                        (select extract ('year' from sale_order.date_order):: character varying as year_orderdate,
                                extract ('month' from sale_order.date_order) as month_orderdate,
                                sale_order.user_id as key_account,
                                (case when hr_employee_key.department_id = 4 then 'BOD' else res_users_key.login end) as name_keyaccount,
                                hr_employee_key.department_id as department_keyaccount,
                                hr_department_key.name as name_department_key,
                                sale_order.solution_maker,
                                res_users_sol.login as name_solutionmaker,
                                hr_employee_sol.department_id as department_solutionmaker,
                                hr_department_sol.name as name_department_sol,
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
                        left join hr_department as hr_department_key on hr_employee_key.department_id = hr_department_key.id
                        left join res_users as res_users_sol on sale_order.solution_maker = res_users_sol.id
                        left join hr_employee as hr_employee_sol on sale_order.solution_maker = hr_employee_sol.user_id
                        left join hr_department as hr_department_sol on hr_employee_sol.department_id = hr_department_sol.id
                        where sale_order.state = 'sale'
                        ) as view_base
                    where view_base.year_orderdate = '{current_year}' and amount_untaxed <> 0
                    group by view_base.year_orderdate, view_base.month_orderdate, view_base.name_keyaccount
                    order by view_base.year_orderdate, view_base.month_orderdate '''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        # tạo ra data cuối
        if len(recs_last)<=0:
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        # gom nhóm theo form báo cáo
        key_account=[]
        for rec in recs_last:
            if rec['name_keyaccount'] not in key_account:
                key_account.append(rec['name_keyaccount'])
        last_data={}
        for account in key_account:
            for line in recs_last:
                if line['name_keyaccount'] == account:
                    key_month = 't' + str(int(line['month_orderdate']))
                    if account not in last_data:
                        last_data[account]={key_month : round(line.get('amount_untaxed') or 0)}
                    else:
                        last_data[account][key_month] = round(line.get('amount_untaxed') or 0)
        # đổ dữ liệu
        for key,value in last_data.items():
            insert = '''INSERT INTO sale_key_account (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                          VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                      '''.format(key=self.master_key,
                                                 classification=key,
                                                 t1=value.get('t1') or 0,
                                                 t2=value.get('t2') or 0,
                                                 t3=value.get('t3') or 0,
                                                 t4=value.get('t4') or 0,
                                                 t5=value.get('t5') or 0,
                                                 t6=value.get('t6') or 0,
                                                 t7=value.get('t7') or 0,
                                                 t8=value.get('t8') or 0,
                                                 t9=value.get('t9') or 0,
                                                 t10=value.get('t10') or 0,
                                                 t11=value.get('t11') or 0,
                                                 t12=value.get('t12') or 0, )
            self._cr.execute(insert)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo doanh số theo nhân viên phụ trách',
            'view_mode': 'tree',
            'res_model': "sale.key.account",
            'context' : {'year': current_year},
            'view_id': self.env.ref('effective_management.sale_key_account_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }