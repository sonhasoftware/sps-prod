
import datetime as dt

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleSignedIncentiveWizards(models.TransientModel):
    _name = "sale.signed.incentive.wizards"
    _description = "Thống kê hợp đồng đã ký"

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
        self._cr.execute(
            "delete from sale_signed_incentive where master_key = {key}".format(key=self.master_key))
        #1.Key_account
        sql_key_account =f''' with data_ka as (
                        select  view_base.year_orderdate,
                                view_base.month_orderdate,
                                view_base.name_keyaccount,
                                sum(case when view_base.project_type = 'operation' then view_base.profit_after_tax  else 0 end) as fm_profitaftertax,
                                sum(case when view_base.project_type = 'maintainance' then view_base.profit_after_tax  else 0 end) as m_profitaftertax,
                                sum(case when view_base.project_type = 'service' then view_base.profit_after_tax  else 0 end) as s_profitaftertax,
                                ((sum(case when view_base.project_type = 'operation' then view_base.profit_after_tax  else 0 end) + sum(case when view_base.project_type = 'maintainance' then view_base.profit_after_tax  else 0 end))*10/100 + sum(case when view_base.project_type = 'service' then view_base.profit_after_tax  else 0 end)*6/100) as thuongdukien_keyaccount
                        from
                            (select extract ('year' from sale_order.date_order)::character varying as year_orderdate,
                                    extract ('month' from sale_order.date_order) as month_orderdate,
                                    sale_order.user_id as key_account,
                                    (case when hr_employee_key.department_id = 4 then 'BOD' else hr_employee_key.name end) as name_keyaccount,
                                    hr_employee_key.department_id as department_keyaccount,
                                    sale_order.solution_maker,
                                    (case when hr_employee_sol.department_id = 4 then 'BOD' else hr_employee_sol.name end)as name_solutionmaker,
                                    hr_employee_sol.department_id as department_solutionmaker,
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
                            left join res_users as res_users_sol on sale_order.solution_maker = res_users_sol.id
                            left join hr_employee as hr_employee_sol on sale_order.solution_maker = hr_employee_sol.user_id
                            where sale_order.state = 'sale' and hr_employee_key.department_id <> 4
                            ) as view_base
                        where view_base.year_orderdate = '{current_year}'
                        group by view_base.year_orderdate, view_base.month_orderdate, view_base.name_keyaccount
                        order by view_base.year_orderdate, view_base.month_orderdate)
                        select * from data_ka 
                        where year_orderdate = '{current_year}' and (fm_profitaftertax <> 0 or m_profitaftertax <>0 or s_profitaftertax<>0 )
                        '''
        self._cr.execute(sql_key_account)
        recs_key_account = self._cr.dictfetchall()
        if not len(recs_key_account):
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        key_account = []
        for rec in recs_key_account:
            if rec['name_keyaccount'] not in key_account:
                key_account.append(rec['name_keyaccount'])
        data_key_account = {
        }
        for account in key_account:
            data_key_account.update({
                account + '_Tổng lợi nhuận HĐ quản lý vận hành mới': {},
                account + '_Tổng lợi nhuận HĐ bảo trì mới': {},
                account + '_Tổng lợi nhuận HĐ dịch vụ': {},
                account + '_Giá trị thưởng dự kiến': {}
            })
        for account in key_account:
            for line in recs_key_account:
                if line['name_keyaccount'] == account:
                    key_month = 't' + str(int(line['month_orderdate']))
                    data_key_account[account + '_Tổng lợi nhuận HĐ quản lý vận hành mới'][key_month] = round(line['fm_profitaftertax'])
                    data_key_account[account + '_Tổng lợi nhuận HĐ bảo trì mới'][key_month] = round(line['m_profitaftertax'])
                    data_key_account[account + '_Tổng lợi nhuận HĐ dịch vụ'][key_month] = round(line['s_profitaftertax'])
                    data_key_account[account + '_Giá trị thưởng dự kiến'][key_month] = round(line['thuongdukien_keyaccount'])
        # --B. SOLUTION MAKER:
        sql_sm=f''' with data_sm as ( 
                    select  view_base.year_orderdate,
                            view_base.month_orderdate,
                            view_base.name_solutionmaker,
                            sum(case when view_base.project_type = 'operation' then view_base.profit_after_tax  else 0 end) as fm_profitaftertax,
                            sum(case when view_base.project_type = 'maintainance' then view_base.profit_after_tax  else 0 end) as m_profitaftertax,
                            sum(case when view_base.project_type = 'service' then view_base.profit_after_tax  else 0 end) as s_profitaftertax,
                            ((sum(case when view_base.project_type = 'operation' then view_base.profit_after_tax  else 0 end) + sum(case when view_base.project_type = 'maintainance' then view_base.profit_after_tax  else 0 end))*5/100 + sum(case when view_base.project_type = 'service' then view_base.profit_after_tax  else 0 end)*4/100) as thuongdukien_solutionmaker
                    from
                        (select extract ('year' from sale_order.date_order):: character varying as year_orderdate,
                                extract ('month' from sale_order.date_order) as month_orderdate,
                                sale_order.user_id as key_account,
                                (case when hr_employee_key.department_id = 4 then 'BOD' else hr_employee_key.name end) as name_keyaccount,
                                hr_employee_key.department_id as department_keyaccount,
                                sale_order.solution_maker,
                                (case when hr_employee_sol.department_id = 4 then 'BOD' else hr_employee_sol.name end)as name_solutionmaker,
                                hr_employee_sol.department_id as department_solutionmaker,
                                sale_order.id as so_id,
                                sale_order.x_contract_status,
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
                        left join res_users as res_users_sol on sale_order.solution_maker = res_users_sol.id
                        left join hr_employee as hr_employee_sol on sale_order.solution_maker = hr_employee_sol.user_id
                        where sale_order.state = 'sale' and hr_employee_sol.department_id <> 4
                        ) as view_base
                    group by view_base.year_orderdate, view_base.month_orderdate, view_base.name_solutionmaker
                    order by view_base.year_orderdate, view_base.month_orderdate)
                    select * from data_sm 
                    where year_orderdate = '{current_year}' and (fm_profitaftertax <> 0 or m_profitaftertax <>0 or s_profitaftertax<>0 ) 
                    '''
        self._cr.execute(sql_sm)
        recs_sm = self._cr.dictfetchall()
        if not len(recs_sm):
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        solution_maker = []
        for rec in recs_sm:
            if rec['name_solutionmaker'] not in solution_maker:
                solution_maker.append(rec['name_solutionmaker'])
        data_solution_maker = {}
        for maker in solution_maker:
            data_solution_maker.update({
                maker + '_Tổng lợi nhuận HĐ quản lý vận hành mới': {},
                maker + '_Tổng lợi nhuận HĐ bảo trì mới': {},
                maker + '_Tổng lợi nhuận HĐ dịch vụ': {},
                maker + '_Giá trị thưởng dự kiến': {}
            })
        for maker in solution_maker:
            for line in recs_sm:
                if line['name_solutionmaker'] == maker:
                    key_month = 't' + str(int(line['month_orderdate']))
                    data_solution_maker[maker + '_Tổng lợi nhuận HĐ quản lý vận hành mới'][key_month] = round(line['fm_profitaftertax'])
                    data_solution_maker[maker + '_Tổng lợi nhuận HĐ bảo trì mới'][key_month] = round(line['m_profitaftertax'])
                    data_solution_maker[maker + '_Tổng lợi nhuận HĐ dịch vụ'][key_month] = round(line['s_profitaftertax'])
                    data_solution_maker[maker + '_Giá trị thưởng dự kiến'][key_month] = round(line['thuongdukien_solutionmaker'])


        #C. ESTIMATED GROSS INCENTIVE:
        sql_gross = f''' with data_gross as (
                        select 	view_tong.year_orderdate,
                                view_tong.month_orderdate,
                                view_tong.name_employee,
                                sum(view_tong.thuongdukien) as thuongdukien
                        from
                            (--Key Account
                            select  view_base.year_orderdate,
                                    view_base.month_orderdate,
                                    view_base.name_keyaccount as name_employee,
                                    ((sum(case when view_base.project_type = 'operation' then view_base.profit_after_tax else 0 end) + sum(case when view_base.project_type = 'maintainance' then view_base.profit_after_tax else 0 end))*10/100 + sum(case when view_base.project_type = 'service' then view_base.profit_after_tax else 0 end)*6/100) as thuongdukien
                            from
                                (select extract ('year' from sale_order.date_order):: character varying as year_orderdate,
                                        extract ('month' from sale_order.date_order) as month_orderdate,
                                        sale_order.user_id as key_account,
                                        (case when hr_employee_key.department_id = 4 then 'BOD' else hr_employee_key.name end) as name_keyaccount,
                                        hr_employee_key.department_id as department_keyaccount,
                                        sale_order.solution_maker,
                                        (case when hr_employee_sol.department_id = 4 then 'BOD' else hr_employee_sol.name end)as name_solutionmaker,
                                        hr_employee_sol.department_id as department_solutionmaker,
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
                                left join res_users as res_users_sol on sale_order.solution_maker = res_users_sol.id
                                left join hr_employee as hr_employee_sol on sale_order.solution_maker = hr_employee_sol.user_id
                                where sale_order.state = 'sale' and hr_employee_key.department_id <> 4
                                ) as view_base
                            group by view_base.year_orderdate, view_base.month_orderdate, view_base.name_keyaccount
                            
                            union all
                            
                            select 	view_base.year_orderdate,
                                    view_base.month_orderdate,
                                    view_base.name_solutionmaker as name_employee,
                                    ((sum(case when view_base.project_type = 'operation' then view_base.profit_after_tax else 0 end) + sum(case when view_base.project_type = 'maintainance' then view_base.profit_after_tax else 0 end))*5/100 + sum(case when view_base.project_type = 'service' then view_base.profit_after_tax else 0 end)*4/100) as thuongdukien
                            from
                                (select extract ('year' from sale_order.date_order):: character varying as year_orderdate,
                                        extract ('month' from sale_order.date_order) as month_orderdate,
                                        sale_order.user_id as key_account,
                                        (case when hr_employee_key.department_id = 4 then 'BOD' else hr_employee_key.name end) as name_keyaccount,
                                        hr_employee_key.department_id as department_keyaccount,
                                        sale_order.solution_maker,
                                        (case when hr_employee_sol.department_id = 4 then 'BOD' else hr_employee_sol.name end)as name_solutionmaker,
                                        hr_employee_sol.department_id as department_solutionmaker,
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
                                left join res_users as res_users_sol on sale_order.solution_maker = res_users_sol.id
                                left join hr_employee as hr_employee_sol on sale_order.solution_maker = hr_employee_sol.user_id
                                where sale_order.state = 'sale' and hr_employee_sol.department_id <> 4
                                ) as view_base
                            group by view_base.year_orderdate, view_base.month_orderdate, view_base.name_solutionmaker
                            ) as view_tong
                        group by view_tong.year_orderdate, view_tong.month_orderdate, view_tong.name_employee
                        order by view_tong.year_orderdate, view_tong.month_orderdate, view_tong.name_employee)
                        select * from data_gross 
                        where year_orderdate = '{current_year}' and thuongdukien<>0 
                        '''
        self._cr.execute(sql_gross)
        recs_gross = self._cr.dictfetchall()
        if len(recs_gross) <= 0:
            raise UserError("Hiện không có dữ liệu cho báo cáo")
        # gom nhóm theo form báo cáo
        employees = []
        for rec in recs_gross:
            if rec['name_employee'] not in employees:
                employees.append(rec['name_employee'])
        data_gross = {}
        for employee in employees:
            for line in recs_gross:
                if line['name_employee'] == employee:
                    key_month = 't' + str(int(line['month_orderdate']))
                    if employee not in data_gross:
                        data_gross[employee] = {key_month: round(line.get('thuongdukien') or 0)}
                    else:
                        data_gross[employee][key_month] = round(line.get('thuongdukien') or 0)

        insert_ka = '''INSERT INTO sale_signed_incentive (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                                 VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                             '''.format(key=self.master_key,
                                                        classification='A. KEY ACCOUNTS',
                                                        t1=sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 1) or 0,
                                                        t2= sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 2) or 0,
                                                        t3=sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 3) or 0,
                                                        t4= sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 4) or 0,
                                                        t5=sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 5) or 0,
                                                        t6= sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 6) or 0,
                                                        t7=sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 7) or 0,
                                                        t8=sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 8) or 0,
                                                        t9=sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 9) or 0,
                                                        t10=sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 10) or 0,
                                                        t11=sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 11) or 0,
                                                        t12=sum(item['thuongdukien_keyaccount'] for item in recs_key_account if item.get('month_orderdate') == 12) or 0, )
        self._cr.execute(insert_ka)
        for key,value in data_key_account.items():
            insert_ka_data = '''INSERT INTO sale_signed_incentive (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                   VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                               '''.format(key=self.master_key,
                                          classification= '...'+ key,
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
                                          t12=value.get('t12') or 0,)
            self._cr.execute(insert_ka_data)
        insert_sm = '''INSERT INTO sale_signed_incentive (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                           VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                       '''.format(key=self.master_key,
                                                  classification='B. SOLUTION MAKER',
                                                  t1= sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 1) or 0,
                                                  t2= sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 2) or 0,
                                                  t3=sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 3) or 0,
                                                  t4= sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 4) or 0,
                                                  t5= sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 5) or 0,
                                                  t6= sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 6) or 0,
                                                  t7=sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 7) or 0,
                                                  t8= sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 8) or 0,
                                                  t9= sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 9) or 0,
                                                  t10= sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 10) or 0,
                                                  t11=sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 11) or 0,
                                                  t12=sum(item['thuongdukien_solutionmaker'] for item in recs_sm if item.get('month_orderdate') == 12) or  0, )
        self._cr.execute(insert_sm)
        for key,value in data_solution_maker.items():
            insert_sm_data = '''INSERT INTO sale_signed_incentive (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                               VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                           '''.format(key=self.master_key,
                                                      classification='......'+key,
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
            self._cr.execute(insert_sm_data)
        insert_gi = '''INSERT INTO sale_signed_incentive (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                                  VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                              '''.format(key=self.master_key,
                                                         classification='C. ESTIMATED GROSS INCENTIVE',
                                                         t1=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 1) or 0,
                                                         t2=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 2) or 0,
                                                         t3=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 3) or 0,
                                                         t4=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 4)or 0,
                                                         t5=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 5)or 0,
                                                         t6=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 6)or 0,
                                                         t7=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 7)or 0,
                                                         t8=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 8)or 0,
                                                         t9=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 9)or 0,
                                                         t10=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 10)or 0,
                                                         t11=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 11)or 0,
                                                         t12=sum(item['thuongdukien'] for item in recs_gross if item.get('month_orderdate') == 12)or 0, )
        self._cr.execute(insert_gi)
        for key,value in data_gross.items():
            insert_gross_data = '''INSERT INTO sale_signed_incentive (master_key, classification ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12)
                                              VALUES ({key},'{classification}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12})
                                          '''.format(key=self.master_key,
                                                     classification='......'+key,
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
            self._cr.execute(insert_gross_data)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo thống kê các dự án đã ký',
            'view_mode': 'tree',
            'res_model': 'sale.signed.incentive',
            'context' : {'year': current_year},
            'view_id': self.env.ref('effective_management.sale_signed_incentive_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }