import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EmployeeEffectiveWizards(models.TransientModel):
    _name = 'employee.effective.wizards'
    _description = 'Báo cáo hiệu quả nhân viên'

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
    year = fields.Selection(
        selection='years_selection',
        string="Năm",
        default=str(dt.datetime.now().year), required=True)
    employee_id = fields.Many2many('hr.employee', string="Nhân viên", required=True)

    def years_selection(self):
        y = dt.datetime.now().year
        year_list = []
        while y != 1939:
            year_list.append((str(y), str(y)))
            y -= 1
        return year_list

    def _should_insert_record(self, value_dict):
        """Kiểm tra xem có nên insert record hay không. Chỉ insert nếu ít nhất một giá trị t1-t12 khác 0."""
        for month in range(1, 13):
            key = f't{month}'
            if value_dict.get(key, 0) != 0:
                return True
        return False

    def chi_tieu_1(self, year, employee):
        filter = f'''where  view_base.year_orderdate = '{year}' '''
        if employee:
            filter += "and  view_base.key_account in %s" % str(tuple(employee + [0, 0]))
        sql = f'''  
                    WITH view_base as (select extract ('year' from sale_order.date_order):: character varying as year_orderdate,
                                                    extract ('month' from sale_order.date_order) as month_orderdate,
                                                    sale_order.id as so_id,
                                                    hr_employee_key.id as key_account,
                                                    hr_employee_key.name as name_keyaccount,
                                                    hr_employee_key.department_id as department_keyaccount,
                                                    hr_department_key.name as name_department_key,
                                                    hr_employee_sol.id as solution_maker,
                                                    hr_employee_sol.name as name_solutionmaker,
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
                                            and sale_order.id in (SELECT so.id
                                                        FROM sale_order so
                                                        INNER JOIN project_project pp ON so.id = pp.x_order_id
                                                        GROUP BY so.id, so.name
                                                        HAVING COUNT(pp.id) > 0
                                                           AND COUNT(pp.id) = COUNT(CASE WHEN pp.state = 'completed' THEN 1 END) )
                                            ),
                    tong_hop as (select  view_base.year_orderdate,
                                        view_base.month_orderdate,
                                        view_base.key_account,
                                        view_base.name_keyaccount,
                                        sum(view_base.amount_untaxed) as amount_untaxed
                                from view_base
                                {filter}
                                group by view_base.year_orderdate, view_base.month_orderdate, view_base.key_account, view_base.name_keyaccount
                                
                                union all 
                                
                                select  view_base.year_orderdate,
                                        13 month_orderdate,
                                        view_base.key_account,
                                        view_base.name_keyaccount,
                                        sum(view_base.amount_untaxed) as amount_untaxed
                                from view_base
                                {filter}
                                group by view_base.year_orderdate, view_base.key_account, view_base.name_keyaccount)
                    select * from tong_hop
'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        key_account = []
        for rec in recs_last:
            if rec['name_keyaccount'] not in key_account:
                key_account.append(rec['name_keyaccount'])

        data_sl = {}
        for account in key_account:
            for line in recs_last:
                if line['name_keyaccount'] == account:
                    key_month = 't' + str(int(line['month_orderdate']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '01 Tổng doanh thu'}
                        data_sl[account][key_month] = line.get('amount_untaxed') or 0
                    else:
                        data_sl[account][key_month] = line.get('amount_untaxed') or 0
        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                       VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                   '''.format(key=self.master_key,
                                                              classification=value.get('type'),
                                                              name=key,
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
                                                              t12=value.get('t12') or 0,
                                                              total=value.get('t13') or 0, )
            self._cr.execute(insert)

    def chi_tieu_2(self, year, employee):
        filter = f'''where so.state = 'sale'
                        and date_part('year', (so.date_order + interval'7 hour')::date) = {year} '''
        if employee:
            filter += "and he.id in %s" % str(tuple(employee + [0, 0]))
        sql = f''' 
        with view_tong as (select date_part('year', (so.date_order + interval'7 hour')::date) year_lastdate,
												date_part('month', (so.date_order + interval'7 hour')::date) month_lastdate,
												so.user_id key_account,
												he.name name_keyaccount,
												0 as fm_amount_untaxed,
												0 as m_amount_untaxed,
												so.amount_untaxed s_amount_untaxed
								from sale_order so 
								left join res_users ru on ru.id = so.user_id
								left join hr_employee he on he.user_id = ru.id
								{filter}),
        tong_hop as (select  view_tong.year_lastdate,
                                view_tong.month_lastdate,
                                view_tong.key_account,
                                view_tong.name_keyaccount,
                                sum(view_tong.fm_amount_untaxed) as fm_amount_untaxed,
                                sum(view_tong.m_amount_untaxed) as m_amount_untaxed,
                                sum(view_tong.s_amount_untaxed) as s_profitaftertax,
                                (sum(view_tong.m_amount_untaxed) + sum(view_tong.fm_amount_untaxed) + sum(view_tong.s_amount_untaxed)) as amount_untax
                    from  view_tong
                    group by view_tong.year_lastdate, view_tong.month_lastdate, 
                                            view_tong.key_account, view_tong.name_keyaccount	
                    union all
                    select  view_tong.year_lastdate,
                                    13 month_lastdate,
                                    view_tong.key_account,
                                    view_tong.name_keyaccount,
                                    sum(view_tong.fm_amount_untaxed) as fm_amount_untaxed,
                                    sum(view_tong.m_amount_untaxed) as m_amount_untaxed,
                                    sum(view_tong.s_amount_untaxed) as s_profitaftertax,
                                    (sum(view_tong.m_amount_untaxed) + sum(view_tong.fm_amount_untaxed) + sum(view_tong.s_amount_untaxed)) as amount_untax
                    from  view_tong
                    group by view_tong.year_lastdate, view_tong.key_account, view_tong.name_keyaccount	
            )
        select * from tong_hop
        order by year_lastdate, month_lastdate
                    '''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        key_account = []
        for rec in recs_last:
            if rec['name_keyaccount'] not in key_account:
                key_account.append(rec['name_keyaccount'])

        data_sl = {}
        for account in key_account:
            for line in recs_last:
                if line['name_keyaccount'] == account:
                    key_month = 't' + str(int(line['month_lastdate']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '02 Tổng doanh số Key Account'}
                        data_sl[account][key_month] = line.get('amount_untax') or 0
                    else:
                        data_sl[account][key_month] = line.get('amount_untax') or 0
        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                               VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                           '''.format(key=self.master_key,
                                                                      classification=value.get('type'),
                                                                      name=key,
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
                                                                      t12=value.get('t12') or 0,
                                                                      total=value.get('t13') or 0, )
            self._cr.execute(insert)

    def chi_tieu_3(self, year, employee):
        filter = f'''where so.state = 'sale'
                            and date_part('year', (so.date_order + interval'7 hour')::date) = {year} '''
        if employee:
            filter += "and he.id in %s" % str(tuple(employee + [0, 0]))
        sql = f'''  
with view_tong as (select date_part('year', (so.date_order + interval'7 hour')::date) year_lastdate,
												date_part('month', (so.date_order + interval'7 hour')::date) month_lastdate,
												so.solution_maker solution_maker,
												he.name name_solutionmaker,
												0 as fm_amount_untaxed,
												0 as m_amount_untaxed,
												so.amount_untaxed s_amount_untaxed
								from sale_order so 
								join res_users ru on ru.id = so.solution_maker
								join hr_employee he on he.user_id = ru.id
								{filter}),
tong_hop as (select  view_tong.year_lastdate,
						view_tong.month_lastdate,
						view_tong.solution_maker,
						view_tong.name_solutionmaker,
						sum(view_tong.fm_amount_untaxed) as fm_amount_untaxed,
						sum(view_tong.m_amount_untaxed) as m_amount_untaxed,
						sum(view_tong.s_amount_untaxed) as s_profitaftertax,
						(sum(view_tong.m_amount_untaxed) + sum(view_tong.fm_amount_untaxed) + sum(view_tong.s_amount_untaxed)) as amount_untax
		from  view_tong
		group by view_tong.year_lastdate, view_tong.month_lastdate, 
								view_tong.solution_maker, view_tong.name_solutionmaker	
		union all
		select  view_tong.year_lastdate,
						13 month_lastdate,
						view_tong.solution_maker,
						view_tong.name_solutionmaker,
						sum(view_tong.fm_amount_untaxed) as fm_amount_untaxed,
						sum(view_tong.m_amount_untaxed) as m_amount_untaxed,
						sum(view_tong.s_amount_untaxed) as s_profitaftertax,
						(sum(view_tong.m_amount_untaxed) + sum(view_tong.fm_amount_untaxed) + sum(view_tong.s_amount_untaxed)) as amount_untax
		from  view_tong
		group by view_tong.year_lastdate, view_tong.solution_maker, view_tong.name_solutionmaker	
)
select * from tong_hop
order by year_lastdate, month_lastdate
'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        key_account = []
        for rec in recs_last:
            if rec['name_solutionmaker'] not in key_account:
                key_account.append(rec['name_solutionmaker'])

        data_sl = {}
        for account in key_account:
            for line in recs_last:
                if line['name_solutionmaker'] == account:
                    key_month = 't' + str(int(line['month_lastdate']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '03 Tổng doanh số Solution Maker'}
                        data_sl[account][key_month] = line.get('amount_untax') or 0
                    else:
                        data_sl[account][key_month] = line.get('amount_untax') or 0
        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                       VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                                   '''.format(key=self.master_key,
                                                                              classification=value.get('type'),
                                                                              name=key,
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
                                                                              t12=value.get('t12') or 0,
                                                                              total=value.get('t13') or 0, )
            self._cr.execute(insert)

    def chi_tieu_4(self, year, employee):
        filter = f'''where hr_employee.id is not null and  extract ('year' from view_tinhtrangtuyendung.first_date_start) = {year} '''
        if employee:
            filter += "and    hr_employee.id in %s" % str(tuple(employee + [0, 0]))
        sql = f'''
WITH view_tinhtrangtuyendung as (select view_requestid.contract_id,
                                view_requestid.employee_id, 
                                view_requestid.employee_name,
                                view_requestid.date_start,
                                view_requestid.first_date_start,
                                view_requestid.x_cv_code,
                                view_requestid.recruit_rq_id,
                                hr_recruit_request.create_date,
                                hr_recruit_request.date_start as rr_date_start,
                                view_requestid.user_id
                        from
                            (select view_cvcode.contract_id,
                                    view_cvcode.employee_id, 
                                    view_cvcode.employee_name, 
                                    view_cvcode.date_start,
                                    view_cvcode.first_date_start,
                                    view_cvcode.x_cv_code,
                                    hr_applicant.recruit_rq_id,
                                    hr_applicant.user_id
                            from
                                (select view_base.contract_id,
                                        view_base.employee_id,
                                        hr_employee.name as employee_name,
                                        view_base.date_start,
                                        view_base.first_date_start,
                                        hr_employee.x_cv_code 
                                from
                                    (select hr_contract.id as contract_id,
                                            hr_contract.employee_id, 		
                                            hr_contract.date_start,
                                            view_firstdatestart.first_date_start
                                    from hr_contract
                                    left join
                                        (select employee_id, 
                                                min(date_start) as first_date_start
                                        from hr_contract 
                                        group by employee_id
                                        order by employee_id 
                                        ) as view_firstdatestart		
                                    on hr_contract.employee_id = view_firstdatestart.employee_id
                                    where date_start = first_date_start
                                    order by employee_id
                                    ) as view_base
                                left join hr_employee on view_base.employee_id = hr_employee.id
                                ) as view_cvcode
                            left join hr_applicant on view_cvcode.x_cv_code = hr_applicant.id
                            ) as view_requestid
                        left join hr_recruit_request on hr_recruit_request.id = view_requestid.recruit_rq_id
                        ),
tong_hop as (
                select extract ('year' from view_tinhtrangtuyendung.first_date_start)::character varying as year_firstdate,
                                extract ('month' from view_tinhtrangtuyendung.first_date_start)::integer as month_firstdate,
                                hr_employee.id as nguoi_tuyen_id,
                                hr_employee.name as nguoi_tuyen,
                                count(view_tinhtrangtuyendung.contract_id) as quantity_datuyen
                from view_tinhtrangtuyendung
                left join hr_employee on view_tinhtrangtuyendung.user_id = hr_employee.user_id 
                {filter}
                group by year_firstdate, month_firstdate, hr_employee.id, hr_employee.name
                union all
                select extract ('year' from view_tinhtrangtuyendung.first_date_start)::character varying as year_firstdate,
                                13 as month_firstdate,
                                hr_employee.id as nguoi_tuyen_id,
                                hr_employee.name as nguoi_tuyen,
                                count(view_tinhtrangtuyendung.contract_id) as quantity_datuyen
                from view_tinhtrangtuyendung
                left join hr_employee on view_tinhtrangtuyendung.user_id = hr_employee.user_id 
                {filter}
                group by year_firstdate, hr_employee.id, hr_employee.name)
select * from tong_hop'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        key_account = []
        for rec in recs_last:
            if rec['nguoi_tuyen'] not in key_account:
                key_account.append(rec['nguoi_tuyen'])

        data_sl = {}
        for account in key_account:
            for line in recs_last:
                if line['nguoi_tuyen'] == account:
                    key_month = 't' + str(int(line['month_firstdate']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '04 Tổng số lượng nhân sự đã tuyển'}
                        data_sl[account][key_month] = line.get('quantity_datuyen') or 0
                    else:
                        data_sl[account][key_month] = line.get('quantity_datuyen') or 0
        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                              VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                                          '''.format(key=self.master_key,
                                                                                     classification=value.get('type'),
                                                                                     name=key,
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
                                                                                     t12=value.get('t12') or 0,
                                                                                     total=value.get('t13') or 0, )
            self._cr.execute(insert)

    def chi_tieu_5(self, year, employee):
        user_ids = []
        if employee:
            employee = self.env['hr.employee'].browse(employee)
            user_ids = employee.mapped('user_id.id')
        user_ids_str = ','.join(str(uid) for uid in user_ids)  # Chuyển thành chuỗi cách nhau bằng dấu phẩy
        sql_domain_user_ids = f"({user_ids_str})"
        sql = """
        
        with tinh_trang_tuyen_dung as 
                        (select view_reportrecruitmentsatus.year_datestart as year_create,
                                view_reportrecruitmentsatus.month_datestart as month_create,
                                view_reportrecruitmentsatus.nguoituyendung,
                                sum(view_reportrecruitmentsatus.quantity_yeucautuyendung) as quantity_yeucautuyendung,
                                sum(view_reportrecruitmentsatus.quantity_cancel) as quantity_cancel,
                                sum(view_reportrecruitmentsatus.datuyen_tronghan) as datuyen_tronghan,
                                sum(view_reportrecruitmentsatus.datuyen_quahan) as datuyen_quahan,
                                sum(view_reportrecruitmentsatus.chuatuyen_tronghan) as chuatuyen_tronghan,
                                sum(view_reportrecruitmentsatus.chuatuyen_quahan) as chuatuyen_quahan
                        from
                            (select view_slgyeucautuyendung.year_datestart,
                                    view_slgyeucautuyendung.month_datestart,
                                    view_slgyeucautuyendung.nguoituyendung,
                                    (sum(case when view_slgyeucautuyendung.state not in ('draft','canceled') then view_slgyeucautuyendung.quantity else 0 end) + sum(case when view_slgyeucautuyendung.state = 'canceled' then view_slgyeucautuyendung.quantity_datuyen else 0 end)) as quantity_yeucautuyendung,
                                    (sum(case when view_slgyeucautuyendung.state = 'canceled' and view_slgyeucautuyendung.quantity_datuyen = 0 then view_slgyeucautuyendung.quantity else 0 end) + sum(case when view_slgyeucautuyendung.state = 'canceled' and view_slgyeucautuyendung.quantity_datuyen > 0 then view_slgyeucautuyendung.quantity_chuatuyen else 0 end)) as quantity_cancel,
                                    0 as datuyen_tronghan,
                                    0 as datuyen_quahan,
                                    0 as chuatuyen_tronghan,
                                    0 as chuatuyen_quahan
                            from
                                (select hr_recruit_request.id as request_id,
                                        hr_recruit_request.state,
                                        hr_recruit_request.create_date,
                                        hr_recruit_request.date_start,
                                        extract ('year' from hr_recruit_request.date_start)::character varying as year_datestart,
                                        extract ('month' from hr_recruit_request.date_start) as month_datestart,
                                        current_date,
                                        hr_recruit_request.quantity,
                                        coalesce(view_ungviendatuyen.quantity_datuyen,0) as quantity_datuyen,
                                        (hr_recruit_request.quantity - coalesce(view_ungviendatuyen.quantity_datuyen,0)) as quantity_chuatuyen,
                                        coalesce(view_ungviendatuyen.nguoituyendung) as nguoituyendung
                                from hr_recruit_request 	
                                left join 
                                    (select view_tinhtrangtuyendung.recruit_rq_id,
                                            count(contract_id) as quantity_datuyen,
                                            max(view_tinhtrangtuyendung.nguoituyendung) as nguoituyendung
                                    from
                                        (select view_requestid.contract_id,
                                                view_requestid.employee_id, 
                                                view_requestid.employee_name,
                                                view_requestid.date_start,
                                                view_requestid.first_date_start,
                                                view_requestid.x_cv_code,
                                                view_requestid.recruit_rq_id,
                                                view_requestid.nguoituyendung,
                                                hr_recruit_request.create_date,
                                                hr_recruit_request.date_start as rr_date_start
                                        from
                                            (select view_cvcode.contract_id,
                                                    view_cvcode.employee_id, 
                                                    view_cvcode.employee_name, 
                                                    view_cvcode.date_start,
                                                    view_cvcode.first_date_start,
                                                    view_cvcode.x_cv_code,
                                                    hr_applicant.recruit_rq_id,
                                                    hr_emp_recruiter.name as nguoituyendung 
                                            from
                                                (select view_base.contract_id,
                                                        view_base.employee_id,
                                                        hr_employee.name as employee_name,
                                                        view_base.date_start,
                                                        view_base.first_date_start,
                                                        hr_employee.x_cv_code 
                                                from
                                                    (select hr_contract.id as contract_id,
                                                            hr_contract.employee_id, 		
                                                            hr_contract.date_start,
                                                            view_firstdatestart.first_date_start
                                                    from hr_contract
                                                    left join
                                                        (select employee_id, 
                                                                min(date_start) as first_date_start
                                                        from hr_contract 
                                                        where state in ('open', 'close')
                                                        group by employee_id
                                                        order by employee_id 
                                                        ) as view_firstdatestart		
                                                    on hr_contract.employee_id = view_firstdatestart.employee_id
                                                    where date_start = first_date_start
                                                    and hr_contract.state in ('open', 'close')
                                                    order by employee_id
                                                    ) as view_base
                                                left join hr_employee on view_base.employee_id = hr_employee.id
                                                ) as view_cvcode
                                            left join hr_applicant on view_cvcode.x_cv_code = hr_applicant.id
                                            left join hr_employee as hr_emp_recruiter on hr_applicant.user_id = hr_emp_recruiter.user_id
                                            where hr_applicant.user_id in {sql_domain_user_ids}
                                            and hr_emp_recruiter.name is not null
                                            ) as view_requestid
                                        left join hr_recruit_request on hr_recruit_request.id = view_requestid.recruit_rq_id
                                        order by contract_id
                                        ) as view_tinhtrangtuyendung
                                    group by view_tinhtrangtuyendung.recruit_rq_id
                                    ) as view_ungviendatuyen
                                on hr_recruit_request.id = view_ungviendatuyen.recruit_rq_id
                                order by request_id desc
                                ) as view_slgyeucautuyendung
                            group by view_slgyeucautuyendung.year_datestart, view_slgyeucautuyendung.month_datestart, view_slgyeucautuyendung.nguoituyendung
                            
                            union all 
                            
                            select 	view_quantitydatuyen.year_datestart,
                                    view_quantitydatuyen.month_datestart,
                                    view_quantitydatuyen.nguoituyendung,
                                    0 as quantity_yeucautuyendung,
                                    0 as quantity_cancel,
                                    count(case when view_quantitydatuyen.date_start <= view_quantitydatuyen.rr_date_start then 1 end) as datuyen_tronghan,
                                    count(case when view_quantitydatuyen.date_start > view_quantitydatuyen.rr_date_start then 1 end) as datuyen_quahan,
                                    0 as chuatuyen_tronghan,
                                    0 as chuatuyen_quahan
                            from
                                (select hr_recruit_request.create_date,
                                        hr_recruit_request.date_start as date_onboard,
                                        extract ('year' from hr_recruit_request.date_start)::character varying as year_datestart,
                                        extract ('month' from hr_recruit_request.date_start) as month_datestart,	
                                        view_requestid.contract_id,
                                        view_requestid.employee_id, 
                                        view_requestid.employee_name,
                                        view_requestid.date_start,
                                        view_requestid.first_date_start,
                                        view_requestid.x_cv_code,
                                        view_requestid.recruit_rq_id,
                                        view_requestid.nguoituyendung,	
                                        hr_recruit_request.date_start as rr_date_start
                                from
                                    (select view_cvcode.contract_id,
                                            view_cvcode.employee_id, 
                                            view_cvcode.employee_name, 
                                            view_cvcode.date_start,
                                            view_cvcode.first_date_start,
                                            view_cvcode.x_cv_code,
                                            hr_applicant.recruit_rq_id,
                                            hr_emp_recruiter.name as nguoituyendung 
                                    from
                                        (select view_base.contract_id,
                                                view_base.employee_id,
                                                hr_employee.name as employee_name,
                                                view_base.date_start,
                                                view_base.first_date_start,
                                                hr_employee.x_cv_code 
                                        from
                                            (select hr_contract.id as contract_id,
                                                    hr_contract.employee_id, 		
                                                    hr_contract.date_start,
                                                    view_firstdatestart.first_date_start
                                            from hr_contract
                                            left join
                                                (select employee_id, 
                                                        min(date_start) as first_date_start
                                                from hr_contract 
                                                where state in ('open', 'close')
                                                group by employee_id
                                                order by employee_id 
                                                ) as view_firstdatestart		
                                            on hr_contract.employee_id = view_firstdatestart.employee_id
                                            where date_start = first_date_start
                                            and hr_contract.state in ('open', 'close')
                                            order by employee_id
                                            ) as view_base
                                        left join hr_employee 
                                        on view_base.employee_id = hr_employee.id
                                        ) as view_cvcode
                                    left join hr_applicant on view_cvcode.x_cv_code = hr_applicant.id
                                    left join hr_employee as hr_emp_recruiter on hr_applicant.user_id = hr_emp_recruiter.user_id
                                    where hr_applicant.user_id in {sql_domain_user_ids}
                                    and hr_emp_recruiter.name is not null
                                    ) as view_requestid
                                left join hr_recruit_request on hr_recruit_request.id = view_requestid.recruit_rq_id
                                order by contract_id
                                ) as view_quantitydatuyen
                            group by view_quantitydatuyen.year_datestart, view_quantitydatuyen.month_datestart, view_quantitydatuyen.nguoituyendung
                            ) as view_reportrecruitmentsatus
                        where view_reportrecruitmentsatus.nguoituyendung is not null
                        group by view_reportrecruitmentsatus.year_datestart, view_reportrecruitmentsatus.month_datestart, view_reportrecruitmentsatus.nguoituyendung
                        order by view_reportrecruitmentsatus.year_datestart, view_reportrecruitmentsatus.month_datestart, view_reportrecruitmentsatus.nguoituyendung)
                select
                4 as sequence,
                'Tỉ lệ hoàn thành (Done/Requested %)' as name,
                hrt.nguoituyendung,
                case when sum(case when (hrt.month_create = 1) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 1) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 1) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t1,
                case when sum(case when (hrt.month_create = 2) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 2) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 2) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t2,
                case when sum(case when (hrt.month_create = 3) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 3) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 3) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t3,
                case when sum(case when (hrt.month_create = 4) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 4) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 4) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t4,
                case when sum(case when (hrt.month_create = 5) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 5) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 5) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t5,
                case when sum(case when (hrt.month_create = 6) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 6) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 6) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t6,
                case when sum(case when (hrt.month_create = 7) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 7) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 7) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t7,
                case when sum(case when (hrt.month_create = 8) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 8) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 8) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t8,
                case when sum(case when (hrt.month_create = 9) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 9) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 9) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t9,
                case when sum(case when (hrt.month_create = 10) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 10) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 10) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t10,
                case when sum(case when (hrt.month_create = 11) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 11) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 11) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t11,
                case when sum(case when (hrt.month_create = 12) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                     then round((sum(case when (hrt.month_create = 12) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 12) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100), 2)
                     else 0 end as t12,
                round(
                    (
                        coalesce((case when sum(case when (hrt.month_create = 1) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 1) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 1) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 2) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 2) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 2) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 3) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 3) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 3) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 4) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 4) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 4) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 5) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 5) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 5) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 6) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 6) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 6) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 7) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 7) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 7) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 8) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 8) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 8) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 9) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 9) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 9) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 10) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 10) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 10) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 11) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 11) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 11) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0) +
                        coalesce((case when sum(case when (hrt.month_create = 12) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end) > 0 
                                      then (sum(case when (hrt.month_create = 12) and (hrt.year_create = '{year}') then hrt.datuyen_tronghan end)::numeric / sum(case when (hrt.month_create = 12) and (hrt.year_create = '{year}') then hrt.quantity_yeucautuyendung end)::numeric * 100)
                                      else 0 end), 0)
                    ) / 12.0, 2
                ) as total
                from tinh_trang_tuyen_dung hrt
                where hrt.nguoituyendung is not null
                group by hrt.nguoituyendung
                order by sequence, hrt.nguoituyendung 
        """.format(year=year, sql_domain_user_ids=sql_domain_user_ids)
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        for value in recs_last:
            # Kiểm tra xem có ít nhất một giá trị t1-t12 khác 0
            has_non_zero = any(value.get(f't{i}') or 0 != 0 for i in range(1, 13))
            if not has_non_zero:
                continue
            type = '05 Tỉ lệ tuyển đúng hạn(%)'
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                                      VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                                                  '''.format(key=self.master_key,
                                                                                             classification=type,
                                                                                             name=value.get(
                                                                                                 'nguoituyendung'),
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
                                                                                             t12=value.get('t12') or 0,
                                                                                             total=value.get(
                                                                                                 'total') or 0, )
            self._cr.execute(insert)
        return

    def chi_tieu_6(self, year, employee):
        user_ids = []
        if employee:
            employee = self.env['hr.employee'].browse(employee)
            user_ids = employee.mapped('user_id.id')
        user_ids_str = ','.join(str(uid) for uid in user_ids)  # Chuyển thành chuỗi cách nhau bằng dấu phẩy
        sql_domain_user_ids = f"({user_ids_str})"
        sql = """
        with hieu_qua_tuyen_dung as 
            (select view_tong.year_datestart as year_createdate,
                    view_tong.month_datestart as month_createdate,
                    view_tong.applicant_user_id,
                    sum(view_tong.income_value)*12 as ngansachtuyendung,
                    sum(view_tong.wage_actual)*12 as ngansachthucte,
                    sum(view_tong.income_value)*12 - sum(view_tong.wage_actual)*12 as hieuquatuyendung
            from 
                (select hr_recruit_request.id as request_id,
                        hr_recruit_request.create_date::date as ngaytaoyeucau,
                        hr_recruit_request.date_start as ngaybatdaulamviec,
                        hr_recruit_request.quantity as soluongtuyen,
                        hr_recruit_request.state as request_state,
                        hr_employee.id as employee_id,
                        hr_employee.name as employee_name,
                        hr_applicant.user_id as applicant_user_id,
                        view_firstcontract.datestart as ngayhopdongdautien,
                        extract ('year' from view_firstcontract.datestart)::character varying as year_datestart,
                        extract ('month' from view_firstcontract.datestart) as month_datestart,
                        view_ngaynhanluongcuoi.ngaynhanluongcuoi as date_endcontract,
                        hr_recruit_request.income_value,
                        view_wage_actual.wage_actual,
                        (case when view_ngaynhanluongcuoi.ngaynhanluongcuoi - view_firstcontract.datestart >= 365 then 1 else 0 end) as dieukienhople
                from hr_employee
                left join hr_applicant on hr_employee.x_cv_code = hr_applicant.id 
                left join hr_recruit_request on hr_applicant.recruit_rq_id = hr_recruit_request.id
                left join 
                    (--Ngay ky hop dong dau tien cua nhan vien
                    select 	hr_contract.employee_id,
                            min(hr_contract.date_start) as datestart
                    from hr_contract 
                    where hr_contract.state not in ('cancel', 'draft')
                    group by employee_id
                    ) as view_firstcontract
                on hr_employee.id = view_firstcontract.employee_id
                left join 
                    (--Luong thuc te cua nhan vien
                    select 	view_firstcontract.employee_id,
                            view_firstcontract.datestart,
                            hr_contract.id as contract_id,
                            (hr_contract.wage + hr_contract.x_allowance_phone) as wage_actual
                    from
                        (select hr_contract.employee_id,
                                min(hr_contract.date_start) as datestart
                        from hr_contract 
                        where hr_contract.state not in ('cancel', 'draft') and x_contract_type not in ('hdtv','hddv')
                        group by employee_id
                        ) as view_firstcontract
                    left join hr_contract on view_firstcontract.employee_id = hr_contract.employee_id and view_firstcontract.datestart = hr_contract.date_start
                    where hr_contract.state not in ('cancel', 'draft')
                    ) as view_wage_actual
                on hr_employee.id = view_wage_actual.employee_id
                left join 
                    (--Ngay ket thuc hop dong
                    select  view_base.employee_id,
                            (case when current_date < view_base.ngaynhanluongcuoi then current_date else view_base.ngaynhanluongcuoi end) as ngaynhanluongcuoi
                    from
                        (select hr_contract.employee_id,
                                max(hr_contract.date_end) as ngaynhanluongcuoi
                        from hr_contract 
                        where hr_contract.state not in ('cancel', 'draft')
                        group by hr_contract.employee_id
                        ) as view_base
                    ) as view_ngaynhanluongcuoi
                on hr_employee.id = view_ngaynhanluongcuoi.employee_id
                ) as view_tong
            where view_tong.dieukienhople = 1
            group by view_tong.year_datestart, view_tong.month_datestart, view_tong.applicant_user_id
            order by view_tong.year_datestart, view_tong.month_datestart, view_tong.applicant_user_id)
            
            -- Chỉ lấy giá trị "Hiệu quả tuyển dụng" cho năm {year} với user_id và tên nhân viên
            select
            3 as sequence,
            'Hiệu quả tuyển dụng' as name,
            ert.applicant_user_id,
                         he.name as nguoituyendung,
             sum(case when ert.month_createdate = '1' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t1,
             sum(case when ert.month_createdate = '2' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t2,
             sum(case when ert.month_createdate = '3' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t3,
             sum(case when ert.month_createdate = '4' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t4,
             sum(case when ert.month_createdate = '5' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t5,
             sum(case when ert.month_createdate = '6' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t6,
             sum(case when ert.month_createdate = '7' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t7,
             sum(case when ert.month_createdate = '8' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t8,
             sum(case when ert.month_createdate = '9' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t9,
             sum(case when ert.month_createdate = '10' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t10,
             sum(case when ert.month_createdate = '11' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t11,
             sum(case when ert.month_createdate = '12' and ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as t12,
             sum(case when ert.year_createdate = '{year}' then ert.hieuquatuyendung end) as total
            from hieu_qua_tuyen_dung ert
            left join hr_employee he on ert.applicant_user_id = he.user_id
            where ert.applicant_user_id is not null and ert.applicant_user_id in {sql_domain_user_ids}
            group by ert.applicant_user_id, he.name
            order by ert.applicant_user_id; 
        """.format(year=str(int(year) - 1), sql_domain_user_ids=sql_domain_user_ids)
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        for value in recs_last:
            # Kiểm tra xem có ít nhất một giá trị t1-t12 khác 0
            has_non_zero = any(value.get(f't{i}') or 0 != 0 for i in range(1, 13))
            if not has_non_zero:
                continue
            type = '06 Tổng hiệu quả tuyển dụng'
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                                     VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                                                 '''.format(key=self.master_key,
                                                                                            classification=type,
                                                                                            name=value.get(
                                                                                                'nguoituyendung'),
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
                                                                                            t12=value.get('t12') or 0,
                                                                                            total=value.get(
                                                                                                'total') or 0, )
            self._cr.execute(insert)

    def chi_tieu_7(self, year, employee):
        filter = f'''where  view_tong.year_datereceived = '{year}' '''
        if employee:
            filter += "and   view_tong.negotiators_id in %s" % str(tuple(employee + [0, 0]))
        sql = f'''
WITH view_tong as (select extract ('year' from purchase_order_line.x_date_received):: character varying as year_datereceived,
                                extract ('month' from purchase_order_line.x_date_received) as month_datereceived,
                                purchase_requisition.id as pa_id,
                                purchase_requisition.name as pa_name,
                                purchase_order.id as po_id,
                                purchase_order.name as po_name,
                                purchase_order_line.id as po_line_id,
                                purchase_order.date_order::date,
                                purchase_order_line.x_date_received::date,
                                account_move_line.id as move_line_id,
                                account_move_line.move_id,
                                hr_employee_negotiators.id as negotiators_id,
                                res_users_negotiators.login as negotiators,
                                hr_employee_negotiators.name as negotiators_index,
                                view_user_active.contract_id as contract_negotiators,
                                view_user_active.department_id as department_negotiators,
                                hr_employee_estimators.id as estimators_id,
                                res_users_estimators.login as estimators,
                                hr_employee_estimators.name as estimators_index,
                                view_user_active_2.contract_id as contract_estimators,
                                view_user_active_2.department_id as department_estimators,
                                purchase_order_line.product_id,
                                product_template.name as product_name,
                                purchase_order_line.qty_received,
                                purchase_order_line.x_budget_price,
                                (case when purchase_order_line.x_budget_price <= 0 then purchase_order_line.price_unit
                                      else purchase_order_line.x_budget_price 
                                      end
                                ) as x_budget_price_after,
                                purchase_order_line.price_unit,
                                purchase_order_line.price_tax,
                                purchase_order_line.price_subtotal,
                                (case when purchase_order_line.x_budget_price <= 0 then purchase_order_line.price_subtotal
                                      else purchase_order_line.x_budget_price * purchase_order_line.qty_received
                                      end
                                ) as giatri_dutoan,
                                (purchase_order_line.price_unit * purchase_order_line.qty_received) as giatri_thucte
                        from account_move_line 
                        left join purchase_order_line on account_move_line.purchase_line_id = purchase_order_line.id			--Lấy ra purchase_order_line.order_id
                        left join purchase_order on purchase_order_line.order_id = purchase_order.id							--Lấy ra purchase_order.create_date
                        left join res_users as res_users_negotiators on purchase_order.user_id = res_users_negotiators.id		--Lấy ra res_users.login
                        left join hr_employee as hr_employee_negotiators on res_users_negotiators.id = hr_employee_negotiators.user_id 
                        left join pa_line_po_line_ref on purchase_order_line.id = pa_line_po_line_ref.po_line_id 				--Lấy ra pa_line_po_line_ref.pa_line_id 
                        left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id 	--Lấy ra purchase_requisition_line.requisition_id 
                        left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id	--Lấy ra purchase_requisition.id
                        left join project_project on purchase_requisition.x_code_project_id = project_project.id 				--Lấy ra project_project.x_order_id
                        left join sale_order on project_project.x_order_id = sale_order.id 										--Lấy ra sale_order.solution_maker
                        left join res_users as res_users_estimators on sale_order.solution_maker = res_users_estimators.id		--Lấy ra res_users.login
                        left join hr_employee as hr_employee_estimators on res_users_estimators.id = hr_employee_estimators.user_id 
                        left join product_product on purchase_order_line.product_id = product_product.id 
                        left join product_template on product_product.product_tmpl_id = product_template.id
                        left join
                            (select res_users.id as user_id,
                                    res_users.login,
                                    view_employee_active.contract_id,
                                    view_employee_active.department_id
                            from res_users
                            left join 
                                (select hr_employee.user_id  as employee_id,
                                        view_contract_open.id as contract_id,
                                        hr_employee.department_id 
                                 from hr_employee 
                                 left join 
                                    (select hr_contract.id,
                                            hr_contract.employee_id
                                    from hr_contract
                                    where hr_contract.state = 'open'
                                    ) as view_contract_open
                                 on hr_employee.id = view_contract_open.employee_id
                                ) as view_employee_active
                            on res_users.id = view_employee_active.employee_id
                            ) as view_user_active
                        on res_users_negotiators.id = view_user_active.user_id
                        left join
                            (select res_users.id as user_id,
                                    res_users.login,
                                    view_employee_active.contract_id,
                                    view_employee_active.department_id
                            from res_users
                            left join 
                                (select hr_employee.user_id  as employee_id,
                                        view_contract_open.id as contract_id,
                                        hr_employee.department_id 
                                 from hr_employee 
                                 left join 
                                    (select hr_contract.id,
                                            hr_contract.employee_id
                                    from hr_contract
                                    where hr_contract.state = 'open'
                                    ) as view_contract_open
                                 on hr_employee.id = view_contract_open.employee_id
                                ) as view_employee_active
                            on res_users.id = view_employee_active.employee_id
                            ) as view_user_active_2
                        on res_users_estimators.id = view_user_active_2.user_id
                        where account_move_line.move_id in --Tìm bút toán đối ứng phát sinh công nợ tăng
                            (select account_move_line.move_id --Tìm bút toán phát sinh công nợ
                            from account_move_line 
                            where 	account_move_line.parent_state in ('draft', 'posted')
                                    and account_move_line.account_id = 77	
                                    and account_move_line.credit > 0
                            ) 
                            and account_move_line.debit > 0
                            and account_move_line.purchase_line_id is not null
                            and purchase_order_line.product_id not in (4747)
                        order by purchase_order.create_date
                        ),
tong_hop as (select view_tong.year_datereceived,
                    view_tong.month_datereceived::integer,
                    view_tong.negotiators_id,
                    view_tong.negotiators_index,
                    sum(view_tong.giatri_thucte) as giatri_thucte
            from view_tong
            {filter}
            group by view_tong.year_datereceived, view_tong.month_datereceived, 
                    view_tong.negotiators_id, view_tong.negotiators_index
            union all 
            select 	view_tong.year_datereceived,
                    13 month_datereceived,
                    view_tong.negotiators_id,
                    view_tong.negotiators_index,
                    sum(view_tong.giatri_thucte) as giatri_thucte
            from view_tong
            {filter}
            group by view_tong.year_datereceived, view_tong.negotiators_id, view_tong.negotiators_index)
select * from tong_hop'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        key_account = []
        for rec in recs_last:
            if rec['negotiators_index'] not in key_account:
                key_account.append(rec['negotiators_index'])

        data_sl = {}
        for account in key_account:
            for line in recs_last:
                if line['negotiators_index'] == account:
                    key_month = 't' + str(int(line['month_datereceived']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '07 Tổng giá trị đã mua hàng'}
                        data_sl[account][key_month] = line.get('giatri_thucte') or 0
                    else:
                        data_sl[account][key_month] = line.get('giatri_thucte') or 0
        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                             VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                                         '''.format(key=self.master_key,
                                                                                    classification=value.get('type'),
                                                                                    name=key,
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
                                                                                    t12=value.get('t12') or 0,
                                                                                    total=value.get('t13') or 0, )
            self._cr.execute(insert)

    def chi_tieu_8(self, year, employee):
        filter = f'''and view_base.employee_id is not null and view_base.year_dateorder = '{year}' '''
        if employee:
            filter += "and    view_base.employee_id in %s" % str(tuple(employee + [0, 0]))
        sql = f'''
WITH view_base as (
                        --Hạng mục hoàn thành trong hạn & quá hạn theo po_line
                        select 	view_hangmuchoanthanh.year_dateorder,
                                view_hangmuchoanthanh.month_dateorder,
                                view_hangmuchoanthanh.employee_id,
                                view_hangmuchoanthanh.employee_name,
                                sum(view_hangmuchoanthanh.danhanhangtronghan_done)+sum(view_hangmuchoanthanh.danhanhangmuon_latearrival) as tongsohangmuc,
                                sum(view_hangmuchoanthanh.danhanhangtronghan_done) as danhanhangtronghan_done,
                                sum(view_hangmuchoanthanh.danhanhangmuon_latearrival) as danhanhangmuon_latearrival
                        from
                            (--Hàng hóa lưu kho
                            select  view_abc.year_dateorder,
                                    view_abc.month_dateorder,
                                    view_abc.employee_id,
                                    view_abc.employee_name,
                                    count(case when (view_abc.ngaynhapkhomuonnhat::date <= view_abc.schedule_date::date) and (view_abc.qty_done_pol >= view_abc.product_qty) then view_abc.po_line_id end) as danhanhangtronghan_done,
                                    count(case when (view_abc.ngaynhapkhomuonnhat::date > view_abc.schedule_date::date) and (view_abc.qty_done_pol >= view_abc.product_qty) then view_abc.po_line_id end) as danhanhangmuon_latearrival
                            from
                                (select view_slgnhapkho.year_dateorder,
                                        view_slgnhapkho.month_dateorder,
                                        view_slgnhapkho.schedule_date,
                                        view_ngaynhapkhomuonnhat.ngaynhapkhomuonnhat,
                                        view_slgnhapkho.po_line_id,
                                        view_slgnhapkho.pa_line_id,
                                        view_slgnhapkho.product_qty,
                                        view_slgnhapkho.qty_done_pol,
                                        view_slgnhapkho.employee_id,
                                        view_slgnhapkho.employee_name
                                from
                                    (select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                            extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                            purchase_requisition.schedule_date,
                                            view_soluongnhaptheopo.po_line_id,
                                            purchase_order.user_id,
                                            hr_employee.id as employee_id,
                                            hr_employee.name as employee_name,
                                            pa_line_po_line_ref.pa_line_id,
                                            purchase_requisition_line.product_qty,
                                            view_soluongnhaptheopo.qty_done_pol	
                                    from
                                        (select	view_base.purchase_line_id as po_line_id,
                                                sum(view_base.qty_done_moveid) as qty_done_pol
                                        from
                                            (select view_qtydone_stockmoveline.move_id,
                                                    view_qtydone_stockmoveline.qty_done_moveid,
                                                    stock_move.picking_id,
                                                    stock_move.purchase_line_id 
                                            from 
                                                (--Tính tổng số lượng đã nhận của move_id
                                                select  move_id,
                                                        sum(qty_done) as qty_done_moveid	
                                                from stock_move_line
                                                group by move_id
                                                ) as view_qtydone_stockmoveline
                                            left join stock_move on view_qtydone_stockmoveline.move_id = stock_move.id
                                            where stock_move.purchase_line_id is not null
                                            ) as view_base
                                        left join stock_picking on view_base.picking_id = stock_picking.id 
                                        left join purchase_order_line on view_base.purchase_line_id = purchase_order_line.id
                                        group by view_base.purchase_line_id
                                        ) as view_soluongnhaptheopo
                                    left join pa_line_po_line_ref on view_soluongnhaptheopo.po_line_id = pa_line_po_line_ref.po_line_id
                                    left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                    left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                    left join purchase_order_line on view_soluongnhaptheopo.po_line_id = purchase_order_line.id
                                    left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                    left join res_users on purchase_order.user_id = res_users.id
                                    left join hr_employee on res_users.id = hr_employee.user_id
                                    ) as view_slgnhapkho
                                left join
                                    (--Tính ngày nhập kho muộn nhất, tổng số lượng đã nhập của POL
                                    select 	stock_move.purchase_line_id,
                                            max(stock_picking.date_done)::date as ngaynhapkhomuonnhat,
                                            sum(view_qtydone_stockmoveline.qty_done) as qty_done					
                                    from stock_move	
                                    left join 
                                        (--Tính tổng số lượng đã nhận của move_id
                                        select move_id,
                                                sum(qty_done) as qty_done	
                                        from stock_move_line
                                        group by move_id
                                        ) as view_qtydone_stockmoveline
                                    on view_qtydone_stockmoveline.move_id = stock_move.id
                                    left join stock_picking on stock_move.picking_id = stock_picking.id 
                                    where stock_move.purchase_line_id is not null
                                    group by stock_move.purchase_line_id 
                                    ) as view_ngaynhapkhomuonnhat
                                on view_slgnhapkho.po_line_id = view_ngaynhapkhomuonnhat.purchase_line_id
                                ) as view_abc
                            group by view_abc.year_dateorder, view_abc.month_dateorder, view_abc.employee_id, view_abc.employee_name
                        
                            union all 
                            
                            --Hàng hóa dịch vụ
                            select  view_abc.year_dateorder,
                                    view_abc.month_dateorder,
                                    view_abc.employee_id,
                                    view_abc.employee_name,
                                    count(case when (view_abc.x_date_received::date <= view_abc.schedule_date::date) and (view_abc.qty_received >= view_abc.product_qty) then view_abc.po_line_id end) as danhanhangtronghan_done,
                                    count(case when (view_abc.x_date_received::date > view_abc.schedule_date::date) and (view_abc.qty_received >= view_abc.product_qty) then view_abc.po_line_id end) as danhanhangmuon_latearrival
                            from
                                (--Lấy ra các trường ... với điều kiện loại sản phẩm là Dịch vụ, số lượng đã nhận > 0 và sản phẩm khác 'Làm tròn'
                                select extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                        extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                        purchase_order_line.id as po_line_id,
                                        purchase_requisition.schedule_date,
                                        purchase_order_line.x_date_received,
                                        purchase_requisition_line.product_qty,
                                        purchase_order_line.qty_received,
                                        purchase_order.user_id,
                                        hr_employee.id as employee_id,
                                        hr_employee.name as employee_name
                                from purchase_order_line 
                                left join product_product on purchase_order_line.product_id = product_product.id 
                                left join product_template on product_product.product_tmpl_id = product_template.id
                                left join pa_line_po_line_ref on purchase_order_line.id = pa_line_po_line_ref.po_line_id
                                left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                left join res_users on purchase_order.user_id = res_users.id
                                left join hr_employee on res_users.id = hr_employee.user_id
                                where 	product_template.x_type = 'service'
                                        and purchase_order_line.qty_received > 0
                                        and purchase_order_line.product_id not in (4747)
                                ) as view_abc
                            group by view_abc.year_dateorder, view_abc.month_dateorder, view_abc.employee_id, view_abc.employee_name
                            
                            union all 
                            
                            --Exceptional: mua 1 phần rồi tạm hoãn, đưa về hoàn thành
                            select 	view_abc.year_dateorder,
                                    view_abc.month_dateorder,
                                    view_abc.employee_id,
                                    view_abc.employee_name,
                                    count(case when view_abc.x_date_received::date <= view_abc.schedule_date::date then view_abc.po_line_id end) as danhanhangtronghan_done,
                                    count(case when view_abc.x_date_received::date > view_abc.schedule_date::date then view_abc.po_line_id end) as danhanhangmuon_latearrival
                            from 
                                (--Lấy ra các trường ... với điều kiện trạng thái của PO là 'delay', số lượng nhận > 0 và sản phẩm khác 'Làm tròn' 
                                select 	extract ('year' from purchase_requisition.ordering_date):: character varying as year_dateorder,
                                        extract ('month' from purchase_requisition.ordering_date) as month_dateorder,
                                        purchase_order.id,
                                        purchase_order.user_id,
                                        hr_employee.id as employee_id,
                                        hr_employee.name as employee_name,
                                        purchase_order_line.id as po_line_id,
                                        purchase_requisition.schedule_date,
                                        purchase_order_line.x_date_received,
                                        purchase_order_line.qty_received	
                                from purchase_order_line 
                                left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                left join res_users on purchase_order.user_id = res_users.id
                                left join hr_employee on res_users.id = hr_employee.user_id
                                left join pa_line_po_line_ref on purchase_order_line.id = pa_line_po_line_ref.po_line_id
                                left join purchase_requisition_line on pa_line_po_line_ref.pa_line_id = purchase_requisition_line.id
                                left join purchase_requisition on purchase_requisition_line.requisition_id = purchase_requisition.id
                                where 	purchase_order.x_state = 'delay'
                                        and purchase_order_line.qty_received > 0
                                        and purchase_order_line.product_id not in (4747)
                                ) as view_abc
                            group by view_abc.year_dateorder, view_abc.month_dateorder, view_abc.employee_id, view_abc.employee_name
                            ) as view_hangmuchoanthanh
                        group by view_hangmuchoanthanh.year_dateorder, view_hangmuchoanthanh.month_dateorder, view_hangmuchoanthanh.employee_id, view_hangmuchoanthanh.employee_name
                        ),
tong_hop as (select 	view_base.year_dateorder, --Năm đặt hàng
                            view_base.month_dateorder::integer, --Tháng đặt hàng
                            view_base.employee_id, --ID nhân viên
                            view_base.employee_name, --Tên nhân viên
                    --		sum(view_base.tongsohangmuc) as tongsohangmuc,
                    --		sum(view_base.danhanhangtronghan_done) as danhanhangtronghan_done,
                    --		sum(view_base.danhanhangmuon_latearrival) as danhanhangmuon_latearrival,
                            sum(view_base.danhanhangtronghan_done)*100/sum(view_base.tongsohangmuc) as tylehangmucdapungtiendo	--Tỷ lệ hạng mục đáp ứng tiến độ 
                    from view_base
                    where view_base.month_dateorder is not null 
                            {filter}
                    group by view_base.year_dateorder, view_base.month_dateorder, view_base.employee_id, view_base.employee_name
                    union all 
                    select 	view_base.year_dateorder, --Năm đặt hàng
                            13 month_dateorder, --Tháng đặt hàng
                            view_base.employee_id, --ID nhân viên
                            view_base.employee_name, --Tên nhân viên
                    --		sum(view_base.tongsohangmuc) as tongsohangmuc,
                    --		sum(view_base.danhanhangtronghan_done) as danhanhangtronghan_done,
                    --		sum(view_base.danhanhangmuon_latearrival) as danhanhangmuon_latearrival,
                            sum(view_base.danhanhangtronghan_done)*100/sum(view_base.tongsohangmuc) as tylehangmucdapungtiendo	--Tỷ lệ hạng mục đáp ứng tiến độ 
                    from view_base
                    where view_base.month_dateorder is not null 
						    {filter}
                    group by view_base.year_dateorder, view_base.employee_id, view_base.employee_name)
select * from tong_hop'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        key_account = []
        for rec in recs_last:
            if rec['employee_name'] not in key_account:
                key_account.append(rec['employee_name'])

        data_sl = {}
        for account in key_account:
            for line in recs_last:
                if line['employee_name'] == account:
                    key_month = 't' + str(int(line['month_dateorder']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '08 Tỉ lệ hạng mục mua hàng trong tiến độ(%)'}
                        data_sl[account][key_month] = round(line.get('tylehangmucdapungtiendo', 0), 2)
                    else:
                        data_sl[account][key_month] = round(line.get('tylehangmucdapungtiendo', 0), 2)
        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                                    VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                                                '''.format(key=self.master_key,
                                                                                           classification=value.get(
                                                                                               'type'),
                                                                                           name=key,
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
                                                                                           t12=value.get('t12') or 0,
                                                                                           total=value.get(
                                                                                               't13') or 0, )
            self._cr.execute(insert)

    def chi_tieu_9(self, year, employee):
        filter = f'''where  view_tong.year_datereceived = '{year}' '''
        if employee:
            filter += "and   view_tong.negotiators_id in %s" % str(tuple(employee + [0, 0]))
        # Đồng bộ với báo cáo so sánh hiệu quả mua hàng (purchase.compare.effective.wizards):
        # - Nguồn: purchase_order_line (mỗi PO line đếm 1 lần), KHÔNG đi qua account_move_line
        # - SL: pol.product_qty (số lượng đặt mua), KHÔNG dùng số lượng trên hóa đơn
        # - Dự toán/Thực tế: product_qty * x_budget_price / price_unit (dùng thẳng x_budget_price, không fallback)
        # - Filter: po.x_state in ('done','wait_license','to_late') and x_date_received is not null
        # - KHÔNG join pa_line_po_line_ref (tránh fan-out nhân đôi giá trị cho người đàm phán)
        # Giữ join hr_employee để vẫn lọc/hiển thị theo nhân viên (negotiators_id / negotiators_index).
        sql = f'''
WITH view_tong as (select extract ('year' from purchase_order_line.x_date_received):: character varying as year_datereceived,
                                   extract ('month' from purchase_order_line.x_date_received) as month_datereceived,
                                   hr_employee_negotiators.id as negotiators_id,
                                   hr_employee_negotiators.name as negotiators_index,
                                   (purchase_order_line.product_qty * purchase_order_line.x_budget_price) as giatri_dutoan,
                                   (purchase_order_line.product_qty * purchase_order_line.price_unit) as giatri_thucte
                           from purchase_order_line
                           left join purchase_order on purchase_order_line.order_id = purchase_order.id							--Lấy ra purchase_order.user_id / x_state
                           left join res_users as res_users_negotiators on purchase_order.user_id = res_users_negotiators.id		--Lấy ra res_users.login
                           left join hr_employee as hr_employee_negotiators on res_users_negotiators.id = hr_employee_negotiators.user_id
                           where purchase_order.x_state in ('done', 'wait_license', 'to_late')
                               and purchase_order_line.x_date_received is not null
                           ),
tong_hop as (select view_tong.year_datereceived,
                     view_tong.month_datereceived::integer,
                     view_tong.negotiators_id,
                     view_tong.negotiators_index,
                     (sum(view_tong.giatri_dutoan) - sum(view_tong.giatri_thucte)) as hieuquamuahang
             from view_tong
             {filter}
             group by view_tong.year_datereceived, view_tong.month_datereceived, 
                                view_tong.negotiators_id, view_tong.negotiators_index
            union all 
            select 	view_tong.year_datereceived,
                     13 month_datereceived,
                     view_tong.negotiators_id,
                     view_tong.negotiators_index,
                     (sum(view_tong.giatri_dutoan) - sum(view_tong.giatri_thucte)) as hieuquamuahang
             from view_tong
             {filter}
             group by view_tong.year_datereceived, view_tong.negotiators_id, view_tong.negotiators_index)
select * from tong_hop'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        key_account = []
        for rec in recs_last:
            if rec['negotiators_index'] not in key_account:
                key_account.append(rec['negotiators_index'])

        data_sl = {}
        for account in key_account:
            for line in recs_last:
                if line['negotiators_index'] == account:
                    key_month = 't' + str(int(line['month_datereceived']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '09 Tổng hiệu quả mua hàng'}
                        data_sl[account][key_month] = line.get('hieuquamuahang') or 0
                    else:
                        data_sl[account][key_month] = line.get('hieuquamuahang') or 0
        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                                       VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                                                   '''.format(key=self.master_key,
                                                                                              classification=value.get(
                                                                                                  'type'),
                                                                                              name=key,
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
                                                                                              t12=value.get('t12') or 0,
                                                                                              total=value.get(
                                                                                                  't13') or 0, )
            self._cr.execute(insert)

    def chi_tieu_10(self, year, employee):
        """10 Tổng giá trị dự toán các dự án đã quản lý.

        Dùng chung _completed_project_months (nguồn project.project.
        _project_completion_dates) để đồng nhất ngày/tháng hoàn thành với
        chi_tieu_11 và project.sum.value.labor.action_report.
        """
        month_map = self._completed_project_months(year)
        if not month_map:
            return
        projects = self.env['project.project'].browse(list(month_map.keys()))
        emp_filter = set(employee) if employee else None
        HrEmp = self.env['hr.employee'].with_context(active_test=False)
        data_sl = {}  # employee_name -> {'type':..., 't1'..'t12': val}

        for project in projects:
            if not project.user_id:
                continue
            leader_emp = HrEmp.search(
                [('user_id', '=', project.user_id.id)], order='id', limit=1)
            if not leader_emp:
                continue
            if emp_filter is not None and leader_emp.id not in emp_filter:
                continue
            month = month_map.get(project.id)
            if not month:
                continue
            total_estimate_cost = (project.x_cost_estimate or 0) + (project.x_material_estimate_total or 0)
            key_month = 't%d' % month
            d = data_sl.setdefault(leader_emp.name, {'type': '10 Tổng giá trị dự toán các dự án đã quản lý'})
            d[key_month] = d.get(key_month, 0) + total_estimate_cost

        # Tính tổng cả năm (t13)
        for value in data_sl.values():
            value['t13'] = sum(value.get('t%d' % m, 0) for m in range(1, 13))

        for key, value in data_sl.items():
            key = key.replace("'", "''")
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                                              VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                                                          '''.format(
                key=self.master_key,
                classification=value.get('type'),
                name=key,
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
                t12=value.get('t12') or 0,
                total=value.get('t13') or 0)
            self._cr.execute(insert)

    def chi_tieu_11(self, year, employee):
        """11 Tổng hiệu quả các dự án đã quản lý (leader).

        Mỗi dự án hoàn thành trong năm: cộng FULL diff vào leader (user_id) của
        dự án. Dùng chung _completed_project_months + _project_diff để đồng nhất
        cách chọn dự án / tháng / công thức diff với 11.1, 11.2 và
        project.efficiency.reward.line.
        """
        month_map = self._completed_project_months(year)
        if not month_map:
            return
        projects = self.env['project.project'].browse(list(month_map.keys()))
        emp_filter = set(employee) if employee else None
        data = {}  # emp_id -> {'name', 'months': {month: diff}}

        def _acc(emp_id, name, month, val):
            d = data.get(emp_id)
            if not d:
                d = {'name': name, 'months': {}}
                data[emp_id] = d
            if month:
                d['months'][month] = d['months'].get(month, 0.0) + val

        for project in projects:
            if not project.user_id:
                continue
            # active_test=False: leader đã nghỉ (archived) vẫn được ghi nhận.
            leader_emp = self.env['hr.employee'].with_context(active_test=False).search(
                [('user_id', '=', project.user_id.id)], order='id', limit=1)
            if not leader_emp:
                continue
            diff = self._project_diff(project)
            month = month_map.get(project.id, 0)
            _acc(leader_emp.id, leader_emp.name, month, diff)

        for emp_id, d in data.items():
            if emp_filter is not None and emp_id not in emp_filter:
                continue
            months = d['months']
            value = {'t%d' % m: months.get(m, 0.0) for m in range(1, 13)}
            if not self._should_insert_record(value):
                continue
            name = (d['name'] or '').replace("'", "''")
            insert = '''INSERT INTO employee_effective_value (master_key, classification, name, t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                        VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})'''.format(
                key=self.master_key,
                classification='11 Tổng hiệu quả các dự án đã quản lý',
                name=name,
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
                t12=value.get('t12') or 0,
                total=sum(months.values()))
            self._cr.execute(insert)

    def _completed_project_months(self, year):
        """{project_id: completion_month} các dự án đã hoàn thành trong năm.

        Dùng NGUỒN CHUNG project.project._project_completion_dates (đồng nhất mọi
        báo cáo): dự án archive+completed coi là hoàn thành kể cả không phát sinh
        chi phí; ngày = nguồn -> x_date_end -> x_date_plan_end; None thì bỏ qua.
        """
        year = int(year)
        comp = self.env['project.project']._project_completion_dates()
        return {pid: d.month for pid, d in comp.items() if d and d.year == year}

    def _project_participants(self, project):
        """{employee_id: employee_name} người tham gia dự án (leader + technician).

        Leader = user_id (luôn tính); technician = wage_cost_ids có work_hour > 0.
        Mỗi nhân viên 1 lần (nếu vừa leader vừa technician thì chỉ 1).
        """
        participants = {}
        if project.user_id:
            leader_emp = self.env['hr.employee'].search(
                [('user_id', '=', project.user_id.id)], limit=1)
            if leader_emp:
                participants[leader_emp.id] = leader_emp.name
        for wc in project.wage_cost_ids:
            if wc.employee_id and (wc.work_hour or 0) > 0:
                participants.setdefault(wc.employee_id.id, wc.employee_id.name)
        return participants

    @staticmethod
    def _project_diff(project):
        """diff = dự toán - chi phí thực tế - khấu hao CCDC - chi phí IV
        + điều chỉnh TNDN (doanh thu IV - phí mua hàng không HĐ).

        Phải đồng nhất với project.efficiency.detail._compute_diff để 11.1/11.2
        khớp với bảng phụ project.efficiency.reward.line.
        """
        return ((project.x_cost_estimate or 0)
                + (project.x_material_estimate_total or 0)
                - (project.wage_cost_total or 0)
                - (project.actual_costs or 0)
                - (project.iv_costs_total or 0)
                - (project.total_depreciation_cost or 0)
                + (project.invoice_processing_profit or 0)
                - (project.no_invoice_extra_cost or 0))

    # Tỷ lệ thưởng CỐ ĐỊNH cho người hỗ trợ dự án (không theo customer.rate).
    _SUPPORTER_PCT = 5.0

    def _reward_rate_maps(self, projects):
        """(rate_map code->%, sat_map project_id->code) cho tập dự án.

        sat_map lấy rate ĐGHQ chính thức/dự án (xác định) — dùng chung logic với
        báo cáo thưởng (project.efficiency.detail.wizards) để 11.1/11.2 khớp
        project.efficiency.reward.line khi 1 dự án có nhiều đánh giá.
        """
        rate_map = {r.code: r.rate
                    for r in self.env['customer.rate'].search([]) if r.code}
        sat_map = self.env['customer.satisfaction'].official_rate_code_map(
            projects.ids)
        return rate_map, sat_map

    def _max_customer_rate(self):
        """Tỷ lệ thưởng cao nhất (%) trong customer.rate; rỗng -> 100."""
        rates = [r.rate for r in self.env['customer.rate'].search([]) if r.rate]
        return max(rates) if rates else 100.0

    def _project_member_contributions(self, project, rate_map, sat_map):
        """[(emp_id, name, role, hiệu_quả, thưởng), ...] của 1 dự án cho MỌI vai
        trò — đồng nhất với project.efficiency.reward.line:

        - Leader (user_id):        hiệu quả = full diff,       thưởng = pool.
        - Technician (wage_cost):  hiệu quả = diff × ratio,    thưởng = pool × ratio.
        - Supporter (project_supporter_id): hiệu quả = full diff, thưởng = diff × 5%.
        pool = diff × rate% (rate theo customer.rate, mặc định 5% khi chưa đánh giá),
        chỉ khi diff > 0. Bỏ dòng technician trùng leader. role ∈
        {'leader','technician','supporter'} để caller cap thưởng RIÊNG từng vai trò.
        """
        diff = self._project_diff(project)
        code = sat_map.get(project.id, '')
        pct = 5.0 if not code else rate_map.get(code, 0.0)
        pool = diff * pct / 100.0 if diff > 0 else 0.0

        # active_test=False: leader có thể đã nghỉ (hr.employee archived) nhưng vẫn
        # được ghi nhận; order='id' cho xác định khi user có nhiều bản ghi.
        leader_emp = (self.env['hr.employee'].with_context(active_test=False).search(
            [('user_id', '=', project.user_id.id)], order='id', limit=1)
            if project.user_id else self.env['hr.employee'])
        leader_user_id = project.user_id.id if project.user_id else False

        out = []
        if leader_emp:
            out.append((leader_emp.id, leader_emp.name, 'leader', diff, pool))

        tech_hours = {}
        for wc in project.wage_cost_ids:
            if not wc.employee_id:
                continue
            rec = tech_hours.setdefault(wc.employee_id.id, [wc.employee_id, 0.0])
            rec[1] += wc.work_hour or 0.0
        total_hours = sum(h for _, h in tech_hours.values())
        for emp, hours in tech_hours.values():
            if hours <= 0:
                continue
            # Bỏ dòng technician của chính leader (so theo USER — robust khi leader
            # có nhiều / đã archive bản ghi hr.employee, tránh thưởng 2 lần).
            if leader_user_id and emp.user_id.id == leader_user_id:
                continue
            ratio = hours / total_hours if total_hours else 0.0
            out.append((emp.id, emp.name, 'technician', diff * ratio, pool * ratio))

        supporter = project.project_supporter_id
        if supporter:
            # Dự án hiệu quả âm KHÔNG tính thưởng (=0, không âm). Hiệu quả (arg 3)
            # vẫn = full diff nên âm vẫn kéo tổng hiệu quả (cap 11.2).
            sup_reward = diff * self._SUPPORTER_PCT / 100.0 if diff > 0 else 0.0
            out.append((supporter.id, supporter.name, 'supporter', diff, sup_reward))
        return out

    def chi_tieu_11_1(self, year, employee):
        """11.1 Tổng hiệu quả các dự án đã tham gia.

        Mỗi nhân viên: Σ hiệu quả theo phần tham gia của các dự án người đó tham
        gia, GỒM cả dự án lỗ (diff < 0). Leader (user_id) và supporter
        (project_supporter_id) hưởng FULL diff (100%); technician chia diff theo
        tỷ trọng work_hour. KHÔNG áp cap.
        """
        month_map = self._completed_project_months(year)
        if not month_map:
            return
        projects = self.env['project.project'].browse(list(month_map.keys()))
        emp_filter = set(employee) if employee else None
        data = {}  # emp_id -> {'name', 'months': {month: hiệu_quả}}

        def _acc(emp_id, name, month, val):
            d = data.get(emp_id)
            if not d:
                d = {'name': name, 'months': {}}
                data[emp_id] = d
            if month:
                d['months'][month] = d['months'].get(month, 0.0) + val

        rate_map, sat_map = self._reward_rate_maps(projects)
        for project in projects:
            # Loại dự án CHƯA PHÂN LOẠI (x_project_type trống) — overhead/nội bộ,
            # không dồn hiệu quả cho người tham gia. Các dự án còn lại CỘNG DỒN
            # CẢ lãi lẫn lỗ (không lọc theo dấu diff / dự toán).
            if not project.x_project_type:
                continue
            month = month_map.get(project.id, 0)
            # Hiệu quả theo phần tham gia (leader full, technician theo ratio,
            # supporter full) — dùng chung _project_member_contributions.
            for emp_id, name, _role, eff, _reward in self._project_member_contributions(
                    project, rate_map, sat_map):
                _acc(emp_id, name, month, eff)

        for emp_id, d in data.items():
            if emp_filter is not None and emp_id not in emp_filter:
                continue
            months = d['months']
            value = {'t%d' % m: months.get(m, 0.0) for m in range(1, 13)}
            if not self._should_insert_record(value):
                continue
            name = (d['name'] or '').replace("'", "''")
            insert = '''INSERT INTO employee_effective_value (master_key, classification, name, t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                        VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})'''.format(
                key=self.master_key,
                classification='11 Tổng hiệu quả các dự án đã tham gia',
                name=name,
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
                t12=value.get('t12') or 0,
                total=sum(months.values()))
            self._cr.execute(insert)

    def chi_tieu_11_2(self, year, employee):
        """11.2 Thưởng hiệu quả dự án.

        Thưởng/dự án: leader hưởng full pool, technician chia pool theo work_hour,
        supporter = diff × 5% (pool = diff × rate% khi diff > 0).

        Thưởng đề xuất/nhân viên/năm = TỔNG cap RIÊNG TỪNG VAI TRÒ (mỗi chức danh
        một mốc), KHÔNG gộp chung 1 cap 20%:
          - Phụ trách (leader) + Thành viên (technician): MIN(Σ thưởng vai trò,
            Σ hiệu quả vai trò × tỷ lệ thưởng cao nhất - max customer.rate 20%);
          - Hỗ trợ (supporter): MIN(Σ thưởng, Σ hiệu quả × 5%).
          - Vai trò lỗ ròng (Σ hiệu quả ≤ 0) -> 0 (không âm).
        Khớp đúng E(PM)+E(Technician)+E(Supporter) và sheet E trong file Excel.

        Các tháng GIỮ NGUYÊN thưởng thô (mọi vai trò); chỉ cột TỔNG áp cap. Nhân
        viên lỗ ròng VẪN hiện (chỉ bỏ dòng không có thưởng tháng nào).
        """
        month_map = self._completed_project_months(year)
        if not month_map:
            return
        projects = self.env['project.project'].browse(list(month_map.keys()))
        rate_map, sat_map = self._reward_rate_maps(projects)
        max_rate = self._max_customer_rate()
        sup_rate = self._SUPPORTER_PCT

        emp_filter = set(employee) if employee else None
        # emp_id -> {'name', 'months': {month: Σ thưởng mọi vai trò},
        #            'leader'/'technician'/'supporter': [Σ hiệu quả, Σ thưởng]}
        data = {}

        def _rec(emp_id, name):
            d = data.get(emp_id)
            if not d:
                d = {'name': name, 'months': {},
                     'leader': [0.0, 0.0], 'technician': [0.0, 0.0],
                     'supporter': [0.0, 0.0]}
                data[emp_id] = d
            return d

        for project in projects:
            # Loại dự án CHƯA PHÂN LOẠI (x_project_type trống) — đồng nhất 11.1 và
            # reward.line. Dự án còn lại: hiệu quả (cho cap) và thưởng đều CỘNG DỒN
            # CẢ lãi lẫn lỗ.
            if not project.x_project_type:
                continue
            month = month_map.get(project.id, 0)
            for emp_id, name, role, eff, reward in self._project_member_contributions(
                    project, rate_map, sat_map):
                d = _rec(emp_id, name)
                if month:
                    d['months'][month] = d['months'].get(month, 0.0) + reward
                d[role][0] += eff
                d[role][1] += reward

        for emp_id, d in data.items():
            if emp_filter is not None and emp_id not in emp_filter:
                continue
            months = d['months']
            # Cap RIÊNG từng vai trò rồi cộng lại; vai trò lỗ ròng -> 0.
            le, lr = d['leader']
            te, tr = d['technician']
            se, sr = d['supporter']
            capped_total = (
                (min(lr, le * max_rate / 100.0) if le > 0 else 0.0)
                + (min(tr, te * max_rate / 100.0) if te > 0 else 0.0)
                + (min(sr, se * sup_rate / 100.0) if se > 0 else 0.0))
            value = {'t%d' % m: months.get(m, 0.0) for m in range(1, 13)}
            if not self._should_insert_record(value):
                continue
            name = (d['name'] or '').replace("'", "''")
            insert = '''INSERT INTO employee_effective_value (master_key, classification, name, t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                        VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})'''.format(
                key=self.master_key,
                classification='11.1 Thưởng hiệu quả dự án',
                name=name,
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
                t12=value.get('t12') or 0,
                total=capped_total)
            self._cr.execute(insert)

    def chi_tieu_12(self, year, employee):
        if employee:
            employee = ','.join(str(uid) for uid in employee)  # Chuyển thành chuỗi cách nhau bằng dấu phẩy
            employee = f"({employee})"
        sql = """
            select  
                result.employee_id,
                he.name as ten_nhan_vien,
            
                count(result.source_id) as so_luong_phieu_tong,
            
                sum(case when extract(month from result.report_date) = 1 then 1 else 0 end) as t1,
                sum(case when extract(month from result.report_date) = 2 then 1 else 0 end) as t2,
                sum(case when extract(month from result.report_date) = 3 then 1 else 0 end) as t3,
                sum(case when extract(month from result.report_date) = 4 then 1 else 0 end) as t4,
                sum(case when extract(month from result.report_date) = 5 then 1 else 0 end) as t5,
                sum(case when extract(month from result.report_date) = 6 then 1 else 0 end) as t6,
                sum(case when extract(month from result.report_date) = 7 then 1 else 0 end) as t7,
                sum(case when extract(month from result.report_date) = 8 then 1 else 0 end) as t8,
                sum(case when extract(month from result.report_date) = 9 then 1 else 0 end) as t9,
                sum(case when extract(month from result.report_date) = 10 then 1 else 0 end) as t10,
                sum(case when extract(month from result.report_date) = 11 then 1 else 0 end) as t11,
                sum(case when extract(month from result.report_date) = 12 then 1 else 0 end) as t12,
            
                (
                    sum(case when extract(month from result.report_date) = 1 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 2 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 3 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 4 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 5 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 6 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 7 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 8 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 9 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 10 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 11 then 1 else 0 end) +
                    sum(case when extract(month from result.report_date) = 12 then 1 else 0 end)
                ) as total
            
            from (
                -- 🟢 Phiếu đã có trong customer_satisfaction
                select
                    ser.employee_id,
                    cs.id as source_id,
                    cs.report_date
                from customer_satisfaction cs
                left join satisfaction_employee_ref ser on ser.satisfaction_id = cs.id
                left join project_project project on project.id = cs.project_id
                where ser.employee_id is not null
                  and cs.rate_id is not null 
                  and extract(year from cs.report_date) = {year}
                  and project.export_satisfaction_report = true
            
                union all
            
                -- 🟣 Phiếu từ project_project (chưa có customer_satisfaction)
                select
                    he.id as employee_id,
                    project.id as source_id,
                    project.x_report_date as report_date
                from project_project project
                left join res_users ru on ru.id = project.user_id
                left join hr_employee he on he.user_id = ru.id
                where project.export_satisfaction_report = true
                  and project.x_rate_id is not null
                  and project.x_report_date is not null
                  and extract(year from project.x_report_date) = {year}
                  and not exists (
                      select 1
                      from customer_satisfaction satis
                      where satis.project_id = project.id
                        and extract(year from satis.report_date) = {year}
                  )
            ) as result
            left join hr_employee he on he.id = result.employee_id
            where result.employee_id in {employee}
            group by result.employee_id, he.name
            order by result.employee_id
        """.format(year=year, employee=employee)
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        for value in recs_last:
            # Kiểm tra xem có ít nhất một giá trị t1-t12 khác 0
            has_non_zero = any(value.get(f't{i}') or 0 != 0 for i in range(1, 13))
            if not has_non_zero:
                continue
            type = '12 Tổng số phiếu'
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                       VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                   '''.format(key=self.master_key,
                                                              classification=type,
                                                              name=value.get('ten_nhan_vien'),
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
                                                              t12=value.get('t12') or 0,
                                                              total=value.get('total') or 0, )
            self._cr.execute(insert)

        # SQL lấy số phiếu hài lòng (code S,E) 
        sql_hai_long = """
        select  
            result.employee_id,
            he.name as ten_nhan_vien,
        
            count(result.source_id) as so_luong_phieu_tong,
        
            sum(case when extract(month from result.report_date) = 1 then 1 else 0 end) as t1,
            sum(case when extract(month from result.report_date) = 2 then 1 else 0 end) as t2,
            sum(case when extract(month from result.report_date) = 3 then 1 else 0 end) as t3,
            sum(case when extract(month from result.report_date) = 4 then 1 else 0 end) as t4,
            sum(case when extract(month from result.report_date) = 5 then 1 else 0 end) as t5,
            sum(case when extract(month from result.report_date) = 6 then 1 else 0 end) as t6,
            sum(case when extract(month from result.report_date) = 7 then 1 else 0 end) as t7,
            sum(case when extract(month from result.report_date) = 8 then 1 else 0 end) as t8,
            sum(case when extract(month from result.report_date) = 9 then 1 else 0 end) as t9,
            sum(case when extract(month from result.report_date) = 10 then 1 else 0 end) as t10,
            sum(case when extract(month from result.report_date) = 11 then 1 else 0 end) as t11,
            sum(case when extract(month from result.report_date) = 12 then 1 else 0 end) as t12,
        
            (
                sum(case when extract(month from result.report_date) = 1 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 2 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 3 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 4 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 5 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 6 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 7 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 8 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 9 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 10 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 11 then 1 else 0 end) +
                sum(case when extract(month from result.report_date) = 12 then 1 else 0 end)
            ) as total
        
        from (
            select
                ser.employee_id,
                cs.id as source_id,
                cs.report_date
            from customer_satisfaction cs
            left join customer_rate cr on cr.id = cs.rate_id 
            left join satisfaction_employee_ref ser on ser.satisfaction_id = cs.id
            left join project_project project on project.id = cs.project_id
            where ser.employee_id is not null
              and cs.rate_id is not null 
              and extract(year from cs.report_date) = {year}
              and cr.code in ('S','E')
              and project.export_satisfaction_report = true
        
            union all
        
            select
                he.id as employee_id,
                project.id as source_id,
                project.x_report_date as report_date
            from project_project project
            left join res_users ru on ru.id = project.user_id
            left join hr_employee he on he.user_id = ru.id
            left join customer_rate cr on cr.id = project.x_rate_id
            where project.export_satisfaction_report = true
              and project.x_rate_id is not null
              and cr.code in ('S','E')
              and project.x_report_date is not null
              and extract(year from project.x_report_date) = {year}
              and not exists (
                  select 1
                  from customer_satisfaction satis
                  where satis.project_id = project.id
                    and extract(year from satis.report_date) = {year}
              )
        ) as result
        left join hr_employee he on he.id = result.employee_id
        where result.employee_id in {employee}
        group by result.employee_id, he.name
        order by result.employee_id
        """.format(year=year, employee=employee)

        combined_sql = """
        WITH 
        phieu_hai_long AS (
            {sql_hai_long}
        ),
        tong_phieu AS (
            {sql_tong}
        )
        SELECT 
            hl.employee_id,
            hl.ten_nhan_vien,
            -- Số phiếu hài lòng
            hl.t1 as hl_t1, hl.t2 as hl_t2, hl.t3 as hl_t3, hl.t4 as hl_t4, 
            hl.t5 as hl_t5, hl.t6 as hl_t6, hl.t7 as hl_t7, hl.t8 as hl_t8,
            hl.t9 as hl_t9, hl.t10 as hl_t10, hl.t11 as hl_t11, hl.t12 as hl_t12, 
            hl.total as hl_total,
            -- Tổng số phiếu  
            tp.t1 as tp_t1, tp.t2 as tp_t2, tp.t3 as tp_t3, tp.t4 as tp_t4,
            tp.t5 as tp_t5, tp.t6 as tp_t6, tp.t7 as tp_t7, tp.t8 as tp_t8,
            tp.t9 as tp_t9, tp.t10 as tp_t10, tp.t11 as tp_t11, tp.t12 as tp_t12,
            tp.total as tp_total,
            -- Tỉ lệ hài lòng (%)
            CASE WHEN tp.t1 > 0 THEN ROUND((hl.t1::decimal / tp.t1 * 100), 2) ELSE 0 END as t1_percent,
            CASE WHEN tp.t2 > 0 THEN ROUND((hl.t2::decimal / tp.t2 * 100), 2) ELSE 0 END as t2_percent,
            CASE WHEN tp.t3 > 0 THEN ROUND((hl.t3::decimal / tp.t3 * 100), 2) ELSE 0 END as t3_percent,
            CASE WHEN tp.t4 > 0 THEN ROUND((hl.t4::decimal / tp.t4 * 100), 2) ELSE 0 END as t4_percent,
            CASE WHEN tp.t5 > 0 THEN ROUND((hl.t5::decimal / tp.t5 * 100), 2) ELSE 0 END as t5_percent,
            CASE WHEN tp.t6 > 0 THEN ROUND((hl.t6::decimal / tp.t6 * 100), 2) ELSE 0 END as t6_percent,
            CASE WHEN tp.t7 > 0 THEN ROUND((hl.t7::decimal / tp.t7 * 100), 2) ELSE 0 END as t7_percent,
            CASE WHEN tp.t8 > 0 THEN ROUND((hl.t8::decimal / tp.t8 * 100), 2) ELSE 0 END as t8_percent,
            CASE WHEN tp.t9 > 0 THEN ROUND((hl.t9::decimal / tp.t9 * 100), 2) ELSE 0 END as t9_percent,
            CASE WHEN tp.t10 > 0 THEN ROUND((hl.t10::decimal / tp.t10 * 100), 2) ELSE 0 END as t10_percent,
            CASE WHEN tp.t11 > 0 THEN ROUND((hl.t11::decimal / tp.t11 * 100), 2) ELSE 0 END as t11_percent,
            CASE WHEN tp.t12 > 0 THEN ROUND((hl.t12::decimal / tp.t12 * 100), 2) ELSE 0 END as t12_percent,
            CASE WHEN tp.total > 0 THEN ROUND((hl.total::decimal / tp.total * 100), 2) ELSE 0 END as total_percent
        FROM phieu_hai_long hl
        LEFT JOIN tong_phieu tp ON hl.employee_id = tp.employee_id
        """.format(sql_hai_long=sql_hai_long, sql_tong=sql)

        self._cr.execute(combined_sql)
        recs_combined = self._cr.dictfetchall()

        # Sử dụng bulk insert để tối ưu hiệu suất
        insert_values = []

        for value in recs_combined:
            # Insert số lượng hài lòng (dùng hl_t1, hl_t2, ...) - chỉ insert nếu có ít nhất một giá trị khác 0
            hl_values = {f't{i}': value.get(f'hl_t{i}') or 0 for i in range(1, 13)}
            if any(hl_values[f't{i}'] != 0 for i in range(1, 13)):
                insert_values.append(
                    "({key}, '12_1 Số phiếu hài lòng', '{name}', {t1}, {t2}, {t3}, {t4}, {t5}, {t6}, {t7}, {t8}, {t9}, {t10}, {t11}, {t12}, {total})".format(
                        key=self.master_key,
                        name=value.get('ten_nhan_vien'),
                        t1=value.get('hl_t1') or 0,
                        t2=value.get('hl_t2') or 0,
                        t3=value.get('hl_t3') or 0,
                        t4=value.get('hl_t4') or 0,
                        t5=value.get('hl_t5') or 0,
                        t6=value.get('hl_t6') or 0,
                        t7=value.get('hl_t7') or 0,
                        t8=value.get('hl_t8') or 0,
                        t9=value.get('hl_t9') or 0,
                        t10=value.get('hl_t10') or 0,
                        t11=value.get('hl_t11') or 0,
                        t12=value.get('hl_t12') or 0,
                        total=value.get('hl_total') or 0
                    ))

            # Insert tỉ lệ hài lòng (%) - dùng tỉ lệ đã tính đúng - chỉ insert nếu có ít nhất một giá trị khác 0
            percent_values = {f't{i}': value.get(f't{i}_percent') or 0 for i in range(1, 13)}
            if any(percent_values[f't{i}'] != 0 for i in range(1, 13)):
                insert_values.append(
                    "({key}, '12_2 Tỉ lệ hài lòng(%)', '{name}', {t1}, {t2}, {t3}, {t4}, {t5}, {t6}, {t7}, {t8}, {t9}, {t10}, {t11}, {t12}, {total})".format(
                        key=self.master_key,
                        name=value.get('ten_nhan_vien'),
                        t1=value.get('t1_percent') or 0,
                        t2=value.get('t2_percent') or 0,
                        t3=value.get('t3_percent') or 0,
                        t4=value.get('t4_percent') or 0,
                        t5=value.get('t5_percent') or 0,
                        t6=value.get('t6_percent') or 0,
                        t7=value.get('t7_percent') or 0,
                        t8=value.get('t8_percent') or 0,
                        t9=value.get('t9_percent') or 0,
                        t10=value.get('t10_percent') or 0,
                        t11=value.get('t11_percent') or 0,
                        t12=value.get('t12_percent') or 0,
                        total=value.get('total_percent') or 0
                    ))

        if insert_values:
            bulk_insert = '''INSERT INTO employee_effective_value (master_key, classification, name, t1, t2, t3, t4, t5,
                                                                   t6, t7, t8, t9, t10, t11, t12,
                                                                   total) VALUES {}'''.format(', '.join(insert_values))
            self._cr.execute(bulk_insert)

    def chi_tieu_13(self, year, employee):
        filter = f'''where view_base.year_chamcong = '{year}' '''
        if employee:
            filter += "and   view_base.employee_id in %s" % str(tuple(employee + [0, 0]))

        # Truy vấn dữ liệu theo tháng
        sql = f'''  
                        WITH view_base as (--Cham cong
                        select  view_detail.year_chamcong,
                                view_detail.month_chamcong,
                                view_detail.x_resource_type,
                                view_detail.employee_id,
                                view_detail.name_employee,
                                sum(view_detail.hour) as hour,
                                sum(view_detail.hour_project) as hour_project
                        from
                            (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                    extract ('month' from hr_work_entry.x_date) as month_chamcong,
                                    hr_work_entry_line.entry_id,
                                    hr_work_entry_line.id as wrl_id,
                                    hr_work_entry_line.project_id,
                                    (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                    hr_work_entry.employee_id,
                                    hr_employee.name as name_employee,
                                    hr_employee.x_resource_type,
                                    hr_work_entry.x_date,
                                    hr_work_entry_line.hour, 
                                    (case when project_project.x_project_type in ('service', 'maintainance', 'operation') then hr_work_entry_line.hour else 0 end) as hour_project
                            from hr_work_entry_line
                            left join hr_work_entry on hr_work_entry_line.entry_id = hr_work_entry.id
                            left join project_project on hr_work_entry_line.project_id = project_project.id
                            left join hr_employee on hr_work_entry.employee_id = hr_employee.id and hr_employee.active = True
                            ) as view_detail
                        group by view_detail.year_chamcong, view_detail.month_chamcong, view_detail.x_resource_type, view_detail.employee_id, view_detail.name_employee
                        ),
                        view_sogiohotroluongbuducong as (--So gio ho tro luong bu du cong
                        select  extract ('year' from hr_payslip.date_from):: character varying as year_payslip,
                                extract ('month' from hr_payslip.date_from) as month_payslip,
                                hr_payslip.id,
                                hr_payslip.employee_id,
                                hr_payslip_input.amount as sogiohotroluongbuducong
                        from hr_payslip
                        left join hr_payslip_input on hr_payslip.id = hr_payslip_input.payslip_id 
                        where hr_payslip_input.input_type_id = 13
                        ),
                        view_trocapdilai as (--So gio tro cap di lai
                        select	view_detail.year_chamcong,
                                view_detail.month_chamcong,
                                view_detail.employee_id,
                                view_detail.name_employee,
                                sum(view_detail.hour) as sogiotrocapdilai,
                                sum(view_detail.sogiotrocapdilai_project) as sogiotrocapdilai_project
                        from
                            (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                    extract ('month' from hr_work_entry.x_date) as month_chamcong,
                                    hr_work_entry.x_date,
                                    hr_work_entry_allowance.entry_id,
                                    hr_work_entry_allowance.id as allowance_id,
                                    hr_work_entry_allowance.project_id,
                                    project_project.name as project_name,
                                    (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                    hr_work_entry.employee_id,
                                    hr_employee.name as name_employee,
                                    hr_employee.x_resource_type,
                                    hr_work_entry_allowance.hour,
                                    (case when project_project.x_project_type in ('service', 'maintainance', 'operation') then hr_work_entry_allowance.hour else 0 end) as sogiotrocapdilai_project
                            from hr_work_entry_allowance
                            left join hr_work_entry on hr_work_entry_allowance.entry_id = hr_work_entry.id
                            left join project_project on hr_work_entry_allowance.project_id = project_project.id
                            left join hr_employee on hr_work_entry.employee_id = hr_employee.id and hr_employee.active = True
                            ) as view_detail
                        group by view_detail.year_chamcong, view_detail.month_chamcong, view_detail.employee_id, view_detail.name_employee)
                        select  view_base.year_chamcong,
                                view_base.month_chamcong::integer,
                                view_base.employee_id,
                                view_base.name_employee,
                                (case 	when view_base.x_resource_type = 'seniorengsub' then 'Kỹ sư/ Giám sát cao cấp'
                                                when view_base.x_resource_type = 'engsub' then 'Kỹ sư/ Giám sát'
                                                when view_base.x_resource_type = 'teamleader' then 'Trưởng nhóm'
                                                when view_base.x_resource_type = 'technician' then 'Kỹ thuật viên'
                                                when view_base.x_resource_type = 'internship' then 'Thực tập sinh'
                                                else 'others' end
                                ) as x_resource_type,
                                coalesce(view_trocapdilai.sogiotrocapdilai_project,0) as sogiotrocapdilai_project,
                                coalesce(view_trocapdilai.sogiotrocapdilai,0) as sogiotrocapdilai,
                                coalesce(view_base.hour_project,0) as sogiochamcong_project,
                                coalesce(view_base.hour,0) as sogiochamcong,
                                coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0) as sogiohotroluongbuducong,
                                (coalesce(view_base.hour_project,0) + coalesce(view_trocapdilai.sogiotrocapdilai_project,0)) as hour_project,
                                (coalesce(view_trocapdilai.sogiotrocapdilai,0) + coalesce(view_base.hour,0) + coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0)) as sogioquydoi,
                                round(((coalesce(view_base.hour_project,0) + coalesce(view_trocapdilai.sogiotrocapdilai_project,0))/(coalesce(view_base.hour,0) + coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0) + coalesce(view_trocapdilai.sogiotrocapdilai,0))*100)::numeric,2) as hieuqua
                        from view_base
                        left join view_sogiohotroluongbuducong on (view_base.year_chamcong = view_sogiohotroluongbuducong.year_payslip 
                                                                    and view_base.month_chamcong = view_sogiohotroluongbuducong.month_payslip 
                                                                    and view_base.employee_id = view_sogiohotroluongbuducong.employee_id)
                        left join view_trocapdilai on (view_base.year_chamcong = view_trocapdilai.year_chamcong 
                                                        and view_base.month_chamcong = view_trocapdilai.month_chamcong 
                                                        and view_base.employee_id = view_trocapdilai.employee_id)
                        {filter}
                        order by view_base.year_chamcong, view_base.month_chamcong, view_base.x_resource_type, view_base.name_employee'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return

        # Truy vấn tính tổng năm
        sql_total = f'''
            WITH view_base as (--Cham cong
                                    select  view_detail.year_chamcong,
                                            view_detail.x_resource_type,
                                            view_detail.employee_id,
                                            view_detail.name_employee,
                                            sum(view_detail.hour) as hour,
                                            sum(view_detail.hour_project) as hour_project
                                    from
                                        (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                                hr_work_entry_line.entry_id,
                                                hr_work_entry_line.id as wrl_id,
                                                hr_work_entry_line.project_id,
                                                (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                                hr_work_entry.employee_id,
                                                hr_employee.name as name_employee,
                                                hr_employee.x_resource_type,
                                                hr_work_entry.x_date,
                                                hr_work_entry_line.hour, 
                                                (case when project_project.x_project_type in ('service', 'maintainance', 'operation') then hr_work_entry_line.hour else 0 end) as hour_project
                                        from hr_work_entry_line
                                        left join hr_work_entry on hr_work_entry_line.entry_id = hr_work_entry.id
                                        left join project_project on hr_work_entry_line.project_id = project_project.id
                                        left join hr_employee on hr_work_entry.employee_id = hr_employee.id and hr_employee.active = True
                                        ) as view_detail
                                    group by view_detail.year_chamcong, view_detail.x_resource_type, view_detail.employee_id, view_detail.name_employee
                                    ),
            view_sogiohotroluongbuducong as (--So gio ho tro luong bu du cong
                                    select  extract ('year' from hr_payslip.date_from):: character varying as year_payslip,
                                            hr_payslip.employee_id,
                                            sum(hr_payslip_input.amount) as sogiohotroluongbuducong
                                    from hr_payslip
                                    left join hr_payslip_input on hr_payslip.id = hr_payslip_input.payslip_id 
                                    where hr_payslip_input.input_type_id = 13
                                    group by extract ('year' from hr_payslip.date_from):: character varying, hr_payslip.employee_id
                                    ),
            view_trocapdilai as (--So gio tro cap di lai
                                    select	view_detail.year_chamcong,
                                            view_detail.employee_id,
                                            view_detail.name_employee,
                                            sum(view_detail.hour) as sogiotrocapdilai,
                                            sum(view_detail.sogiotrocapdilai_project) as sogiotrocapdilai_project
                                    from
                                        (select extract ('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                                hr_work_entry.x_date,
                                                hr_work_entry_allowance.entry_id,
                                                hr_work_entry_allowance.id as allowance_id,
                                                hr_work_entry_allowance.project_id,
                                                project_project.name as project_name,
                                                (case when project_project.x_project_type is null then 'others' else project_project.x_project_type end) as x_project_type,
                                                hr_work_entry.employee_id,
                                                hr_employee.name as name_employee,
                                                hr_employee.x_resource_type,
                                                hr_work_entry_allowance.hour,
                                                (case when project_project.x_project_type in ('service', 'maintainance', 'operation') then hr_work_entry_allowance.hour else 0 end) as sogiotrocapdilai_project
                                        from hr_work_entry_allowance
                                        left join hr_work_entry on hr_work_entry_allowance.entry_id = hr_work_entry.id
                                        left join project_project on hr_work_entry_allowance.project_id = project_project.id
                                        left join hr_employee on hr_work_entry.employee_id = hr_employee.id and hr_employee.active = True
                                        ) as view_detail
                                    group by view_detail.year_chamcong, view_detail.employee_id, view_detail.name_employee)
            select  view_base.year_chamcong,
                    view_base.employee_id,
                    view_base.name_employee,
                    (case 	when view_base.x_resource_type = 'seniorengsub' then 'Kỹ sư/ Giám sát cao cấp'
                                    when view_base.x_resource_type = 'engsub' then 'Kỹ sư/ Giám sát'
                                    when view_base.x_resource_type = 'teamleader' then 'Trưởng nhóm'
                                    when view_base.x_resource_type = 'technician' then 'Kỹ thuật viên'
                                    when view_base.x_resource_type = 'internship' then 'Thực tập sinh'
                                    else 'others' end
                    ) as x_resource_type,
                    round(((coalesce(view_base.hour_project,0) + coalesce(view_trocapdilai.sogiotrocapdilai_project,0))/(coalesce(view_base.hour,0) + coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong,0) + coalesce(view_trocapdilai.sogiotrocapdilai,0))*100)::numeric,2) as hieuqua
            from view_base
            left join view_sogiohotroluongbuducong on view_base.year_chamcong = view_sogiohotroluongbuducong.year_payslip and view_base.employee_id = view_sogiohotroluongbuducong.employee_id
            left join view_trocapdilai on view_base.year_chamcong = view_trocapdilai.year_chamcong and view_base.employee_id = view_trocapdilai.employee_id
            {filter}
            order by view_base.year_chamcong, view_base.x_resource_type, view_base.name_employee'''

        self._cr.execute(sql_total)
        recs_total = self._cr.dictfetchall()

        key_account = []
        for rec in recs_last:
            if rec['name_employee'] not in key_account:
                key_account.append(rec['name_employee'])

        data_sl = {}
        # Xử lý dữ liệu theo tháng (làm tròn giống action_report)
        for account in key_account:
            for line in recs_last:
                if line['name_employee'] == account:
                    key_month = 't' + str(int(line['month_chamcong']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '13 Hiệu suất lao động'}
                        data_sl[account][key_month] = round(line.get('hieuqua') or 0)
                    else:
                        data_sl[account][key_month] = round(line.get('hieuqua') or 0)

        # Xử lý dữ liệu tổng năm (tính đúng theo logic action_report và làm tròn)
        for account in key_account:
            for line in recs_total:
                if line['name_employee'] == account:
                    data_sl[account]['total'] = round(line.get('hieuqua') or 0)
                    break

        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12, total)
                                                              VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                          '''.format(key=self.master_key,
                                                                     classification=value.get('type'),
                                                                     name=key,
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
                                                                     t12=value.get('t12') or 0,
                                                                     total=value.get('total') or 0)
            self._cr.execute(insert)

    def chi_tieu_14(self, year, employee):
        filter_employee = ''
        if employee:
            filter_employee += "and  he.id in %s" % str(tuple(employee + [0, 0]))
        sql = '''SELECT he.id, he.name as name,
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
                                 then sml.qty_done * svl.unit_cost else 0 end) as t13
                FROM res_users ru
                        LEFT JOIN hr_employee he  ON ru.id = he.user_id 
                        LEFT JOIN stock_picking sp ON ru.id = sp.x_payer_id
                        LEFT JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                        LEFT JOIN stock_move_line sml ON sml.picking_id = sp.id
                        LEFT JOIN stock_move sm ON sm.id = sml.move_id
                        left join stock_valuation_layer svl on svl.stock_move_id = sm.id 
                        LEFT JOIN product_product pp ON pp.id = sml.product_id
                        left join product_template pt on pt.id = pp.product_tmpl_id 
                WHERE pt.x_type='product'
                        AND pt.x_product_type = 'supplies' 
                        AND pt.x_supplies_type != 'labor_protection' 
                        AND sp.state='done'
                        and ru.active = 't'
                        and spt.id = 9
                        and pt.default_code in ('KM3M', 'KLGLT', 'KMND', 'GTPU', 'GTS')
                        and he.id is not null 
                        {filter}
                GROUP BY he.id, he.name'''.format(year=year, filter=filter_employee)
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        for r in recs_last:
            # Kiểm tra xem có ít nhất một giá trị t1-t12 khác 0
            has_non_zero = any((r.get(f't{i}') or 0) != 0 for i in range(1, 13))
            if not has_non_zero:
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                   VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                               '''.format(key=self.master_key,
                                                                          classification='14 Tổng giá trị vật tư thu hồi tái sử dụng',
                                                                          name=r['name'],
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
                                                                          total=r['t13'] or 0)
            self._cr.execute(insert)

    def chi_tieu_15(self, year, employee):
        filter_employee = ''
        if employee:
            filter_employee += "and  he.id in %s" % str(tuple(employee + [0, 0]))
        sql = '''SELECT he.id, he.name , 
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
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-12-1' and '{year}-12-31' then sml.qty_done * svl.unit_cost else 0  end) t12,
                
                sum(case when spt.x_type = 'type_3' and sp.x_receiver_id = ru.id and sm.date::date BETWEEN '{year}-1-1' and '{year}-12-31' then sml.qty_done * svl.unit_cost  else 0 end)
                - sum(case when spt.x_type = 'type_2' and sp.x_payer_id = ru.id and sm.date::date BETWEEN '{year}-1-1' and '{year}-12-31' then sml.qty_done * svl.unit_cost else 0  end) t13
                
                FROM res_users ru 
                        LEFT JOIN hr_employee he  ON ru.id = he.user_id 
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
                        and ru.active = 't'
                        {filter}
                GROUP BY he.id, he.name'''.format(year=year, filter=filter_employee)
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        for r in recs_last:
            # Kiểm tra xem có ít nhất một giá trị t1-t12 khác 0
            has_non_zero = any((r.get(f't{i}') or 0) != 0 for i in range(1, 13))
            if not has_non_zero:
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                           VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                                       '''.format(key=self.master_key,
                                                                                  classification='15 Tổng chi phí đồng phục',
                                                                                  name=r['name'],
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
                                                                                  total=r['t13'] or 0)
            self._cr.execute(insert)

    def chi_tieu_16(self, year, employee):
        filter_employee = ''
        if employee:
            filter_employee += "and  he.id in %s" % str(tuple(employee + [0, 0]))
        sql = """
            SELECT
                'Total Value' as metric,
                he.name as tennhanvien,
                he.id as idnv,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 1 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t1,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 2 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t2,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 3 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t3,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 4 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t4,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 5 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t5,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 6 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t6,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 7 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t7,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 8 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t8,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 9 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t9,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 10 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t10,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 11 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t11,
                SUM(CASE WHEN EXTRACT(MONTH FROM sp.date_done) = 12 THEN sml.qty_done * svl.unit_cost ELSE 0 END) as t12,
                SUM(sml.qty_done * svl.unit_cost) as total
            FROM stock_picking as sp
            LEFT JOIN res_users ru ON sp.x_payer_id = ru.id
            LEFT JOIN stock_location sl ON sl.id = sp.location_dest_id AND sl.name ilike 'Kho hàng hỏng, hủy'
            LEFT JOIN stock_move_line as sml ON sml.picking_id = sp.id
            LEFT JOIN product_product as pp ON pp.id = sml.product_id
            LEFT JOIN product_template as pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN hr_employee as he on he.user_id = sp.x_receiver_id
            left join stock_move as sm on sm.id = sml.move_id
            left join stock_valuation_layer svl on svl.stock_move_id = sm.id 
            WHERE ru.login = 'HM'
                {filter_employee}
                AND EXTRACT(YEAR FROM sp.date_done) = {year}
                and sp.state = 'done'
                and pt.x_type = 'product'
                 and  pt.x_product_type = 'tools'
                and sp.picking_type_id in (SELECT id FROM stock_picking_type WHERE x_type in ('type_7','type_6'))
                 and ru.active = 't'
            GROUP BY he.name, he.id
            ORDER BY  he.name,he.id
                    """.format(year=year, filter_employee=filter_employee)

        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        for r in recs_last:
            # Kiểm tra xem có ít nhất một giá trị t1-t12 khác 0
            has_non_zero = any((r.get(f't{i}') or 0) != 0 for i in range(1, 13))
            if not has_non_zero:
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                           VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                       '''.format(key=self.master_key,
                                                                  classification='16 Tổng giá trị hao mòn thuộc kho',
                                                                  name=r['tennhanvien'],
                                                                  t1=r['t1'],
                                                                  t2=r['t2'],
                                                                  t3=r['t3'],
                                                                  t4=r['t4'],
                                                                  t5=r['t5'],
                                                                  t6=r['t6'],
                                                                  t7=r['t7'],
                                                                  t8=r['t8'],
                                                                  t9=r['t9'],
                                                                  t10=r['t10'],
                                                                  t11=r['t11'],
                                                                  t12=r['t12'],
                                                                  total=r['total'], )
            self._cr.execute(insert)

    def chi_tieu_17(self, year, employee):
        filter_employee = ''
        if employee:
            filter_employee += "and  he.id in %s" % str(tuple(employee + [0, 0]))
        sql = '''SELECT  he.id ,he."name" ,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date < '{year}-01-01')	then sml.qty_done * svl.unit_cost ELSE 0 END) as amount_before,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-01-01' and '{year}-01-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as jan,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date >= '{year}-02-01' and sp.date_done ::date < '{year}-03-01')	then sml.qty_done * svl.unit_cost ELSE 0 END) as feb,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-03-01' and '{year}-03-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as mar,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-04-01' and '{year}-04-30')	then sml.qty_done * svl.unit_cost ELSE 0 END) as apr,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-05-01' and '{year}-05-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as may,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-06-01' and '{year}-06-30')	then sml.qty_done * svl.unit_cost ELSE 0 END) as jun,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-07-01' and '{year}-07-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as jul,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-08-01' and '{year}-08-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as aug,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-09-01' and '{year}-09-30')	then sml.qty_done * svl.unit_cost ELSE 0 END) as sep,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-10-01' and '{year}-10-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as oct,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-11-01' and '{year}-11-30')	then sml.qty_done * svl.unit_cost ELSE 0 END) as nov,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-12-01' and '{year}-12-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as dec,
                                 sum(case when (sp.x_payer_id = ru.id and sp.date_done ::date BETWEEN '{year}-01-01' and '{year}-12-31')	then sml.qty_done * svl.unit_cost ELSE 0 END) as total
                         FROM stock_move sm 
                             LEFT JOIN stock_move_line sml on sm.id = sml.move_id
                             LEFT JOIN stock_picking sp on sml.picking_id = sp.id 
                             LEFT JOIN res_users ru on sp.x_receiver_id = ru.id or sp.x_payer_id = ru.id
                             INNER JOIN hr_employee he  on ru.id = he.user_id  
                             LEFT JOIN product_product pp on sml.product_id = pp.id
                             LEFT JOIN product_template pt on pp.product_tmpl_id = pt.id
                             left join stock_valuation_layer svl on svl.stock_move_id = sm.id 
                         WHERE sp.state = 'done' 
                             and sp.picking_type_id in (SELECT id FROM stock_picking_type WHERE x_type in ('type_7','type_6'))
                             and sp.location_dest_id in (SELECT id  from stock_location WHERE x_name = 'Kho hàng hỏng, hủy')
                             and pt.x_type = 'product' 
                             and sm.id not in (SELECT origin_returned_move_id FROM stock_move WHERE origin_returned_move_id is not null)
                             and  pt.x_product_type = 'tools'
                             and ru.active = 't'
                             {filter}
                         GROUP BY  he.id,he.name'''.format(year=year, filter=filter_employee)
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        for r in recs_last:
            # Kiểm tra xem có ít nhất một giá trị t1-t12 khác 0 (chi_tieu_17 sử dụng jan, feb, ... thay vì t1, t2, ...)
            month_keys = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            has_non_zero = any((r.get(key) or 0) != 0 for key in month_keys)
            if not has_non_zero:
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                                   VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                               '''.format(key=self.master_key,
                                                                          classification='17 Tổng giá trị CCDC hỏng mất thuộc cá nhân',
                                                                          name=r['name'],
                                                                          t1=r['jan'],
                                                                          t2=r['feb'],
                                                                          t3=r['mar'],
                                                                          t4=r['apr'],
                                                                          t5=r['may'],
                                                                          t6=r['jun'],
                                                                          t7=r['jul'],
                                                                          t8=r['aug'],
                                                                          t9=r['sep'],
                                                                          t10=r['oct'],
                                                                          t11=r['nov'],
                                                                          t12=r['dec'],
                                                                          total=r['total'], )
            self._cr.execute(insert)

    def chi_tieu_18(self, year, employee):
        filter = f'''where  view_detail.year_training = '{year}' '''
        if employee:
            filter += "and  view_detail.trainer_id in %s" % str(tuple(employee + [0, 0]))
        sql = f'''  
WITH view_detail as (select hr_training_result_line.id,
                                extract ('year' from hr_training_result_line.date)::character varying as year_training,
                                extract ('month' from hr_training_result_line.date) as month_training,
                                hr_training_result_line.date,
                                hr_training_result_line.training_item_id,
                                hr_training_item.name as training_item_name,
                                hr_training_result_line.trainer_id,
                                trainer.name as trainer_name,
                                hr_training_result_line.trainee_id,
                                trainee.name as trainee_name,
                                hr_training_result_line.result::numeric
                        from hr_training_result_line
                        left join hr_employee as trainer on hr_training_result_line.trainer_id = trainer.id 
                        left join hr_employee as trainee on hr_training_result_line.trainee_id = trainee.id 
                        left join hr_training_item on hr_training_result_line.training_item_id = hr_training_item.id
                        where hr_training_result_line.date >= '2021-01-01'
                        ),
tong_hop as (select  view_detail.year_training,
                    view_detail.month_training::integer,
                    view_detail.trainer_id,
                    view_detail.trainer_name,
                    count(view_detail.training_item_id) as so_hang_muc_dao_tao,
                    sum(view_detail.result) as result,
                    round(sum(view_detail.result)/count(view_detail.training_item_id)::numeric,2) as kqtb
            from view_detail
            {filter}
            group by view_detail.year_training, view_detail.month_training,view_detail.trainer_id, view_detail.trainer_name
            union all 
            select  view_detail.year_training,
                    13 month_training,
                    view_detail.trainer_id,
                    view_detail.trainer_name,
                    count(view_detail.training_item_id) as so_hang_muc_dao_tao,
                    sum(view_detail.result) as result,
                    round(sum(view_detail.result)/count(view_detail.training_item_id)::numeric,2) as kqtb
            from view_detail
            {filter}
            group by view_detail.year_training, view_detail.trainer_id, view_detail.trainer_name)
select * from tong_hop'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        key_account = []
        for rec in recs_last:
            if rec['trainer_name'] not in key_account:
                key_account.append(rec['trainer_name'])

        data_sl = {}
        for account in key_account:
            for line in recs_last:
                if line['trainer_name'] == account:
                    key_month = 't' + str(int(line['month_training']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '18_1 Số hạng mục đào tạo đồng nghiệp'}
                        data_sl[account][key_month] = line.get('so_hang_muc_dao_tao') or 0
                    else:
                        data_sl[account][key_month] = line.get('so_hang_muc_dao_tao') or 0
        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                            '''.format(key=self.master_key,
                                                       classification=value.get('type'),
                                                       name=key,
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
                                                       t12=value.get('t12') or 0,
                                                       total=value.get('t13') or 0, )
            self._cr.execute(insert)

        # data_kq = {}
        # for account in key_account:
        #     for line in recs_last:
        #         if line['trainer_name'] == account:
        #             key_month = 't' + str(int(line['month_training']))
        #             if account not in data_kq:
        #                 data_kq[account] = {'type': '18_1 Kết quả đào tạo'}
        #                 data_kq[account][key_month] = line.get('result') or 0
        #             else:
        #                 data_kq[account][key_month] = line.get('result') or 0
        # for key, value in data_kq.items():
        #     insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
        #                                         VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
        #                                     '''.format(key=self.master_key,
        #                                                classification=value.get('type'),
        #                                                name=key,
        #                                                t1=value.get('t1') or 0,
        #                                                t2=value.get('t2') or 0,
        #                                                t3=value.get('t3') or 0,
        #                                                t4=value.get('t4') or 0,
        #                                                t5=value.get('t5') or 0,
        #                                                t6=value.get('t6') or 0,
        #                                                t7=value.get('t7') or 0,
        #                                                t8=value.get('t8') or 0,
        #                                                t9=value.get('t9') or 0,
        #                                                t10=value.get('t10') or 0,
        #                                                t11=value.get('t11') or 0,
        #                                                t12=value.get('t12') or 0,
        #                                                total=value.get('t13') or 0, )
        #     self._cr.execute(insert)

        data_tb = {}
        for account in key_account:
            for line in recs_last:
                if line['trainer_name'] == account:
                    key_month = 't' + str(int(line['month_training']))
                    if account not in data_tb:
                        data_tb[account] = {'type': '18_2 Kết quả tb'}
                        data_tb[account][key_month] = line.get('kqtb') or 0
                    else:
                        data_tb[account][key_month] = line.get('kqtb') or 0
        for key, value in data_tb.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                       VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                                   '''.format(key=self.master_key,
                                                              classification=value.get('type'),
                                                              name=key,
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
                                                              t12=value.get('t12') or 0,
                                                              total=value.get('t13') or 0, )
            self._cr.execute(insert)

    def chi_tieu_19(self, year, employee):
        filter = f'''where  view_detail.year_training = '{year}' '''
        if employee:
            filter += "and  view_detail.trainee_id in %s" % str(tuple(employee + [0, 0]))
        sql = f'''  
WITH view_detail as (select hr_training_result_line.id,
                                extract ('year' from hr_training_result_line.date)::character varying as year_training,
                                extract ('month' from hr_training_result_line.date) as month_training,
                                hr_training_result_line.date,
                                hr_training_result_line.training_item_id,
                                hr_training_item.name as training_item_name,
                                hr_training_result_line.trainer_id,
                                trainer.name as trainer_name,
                                hr_training_result_line.trainee_id,
                                trainee.name as trainee_name,
                                hr_training_result_line.result::numeric
                        from hr_training_result_line
                        left join hr_employee as trainer on hr_training_result_line.trainer_id = trainer.id 
                        left join hr_employee as trainee on hr_training_result_line.trainee_id = trainee.id 
                        left join hr_training_item on hr_training_result_line.training_item_id = hr_training_item.id
                        where hr_training_result_line.date >= '2021-01-01'
                        ),
tong_hop as (select  view_detail.year_training,
                    view_detail.month_training,
                    view_detail.trainee_id,
                    view_detail.trainee_name,
                    count(view_detail.training_item_id) as so_hang_muc_dao_tao,
                    sum(view_detail.result) as result,
                    round(sum(view_detail.result)/count(view_detail.training_item_id)::numeric,2) as kqtb
            from view_detail
            {filter}       
            group by view_detail.year_training, view_detail.month_training,view_detail.trainee_id, view_detail.trainee_name
            union all 
            select  view_detail.year_training,
                    13 month_training,
                    view_detail.trainee_id,
                    view_detail.trainee_name,
                    count(view_detail.training_item_id) as so_hang_muc_dao_tao,
                    sum(view_detail.result) as result,
                    round(sum(view_detail.result)/count(view_detail.training_item_id)::numeric,2) as kqtb
            from view_detail
            {filter}       
            group by view_detail.year_training, view_detail.trainee_id, view_detail.trainee_name)
select * from tong_hop'''
        self._cr.execute(sql)
        recs_last = self._cr.dictfetchall()
        if len(recs_last) <= 0:
            return
        key_account = []
        for rec in recs_last:
            if rec['trainee_name'] not in key_account:
                key_account.append(rec['trainee_name'])

        data_sl = {}
        for account in key_account:
            for line in recs_last:
                if line['trainee_name'] == account:
                    key_month = 't' + str(int(line['month_training']))
                    if account not in data_sl:
                        data_sl[account] = {'type': '19_1 Số hạng mục đào tạo'}
                        data_sl[account][key_month] = line.get('so_hang_muc_dao_tao') or 0
                    else:
                        data_sl[account][key_month] = line.get('so_hang_muc_dao_tao') or 0
        for key, value in data_sl.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                          VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                      '''.format(key=self.master_key,
                                                 classification=value.get('type'),
                                                 name=key,
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
                                                 t12=value.get('t12') or 0,
                                                 total=value.get('t13') or 0, )
            self._cr.execute(insert)

        # data_kq = {}
        # for account in key_account:
        #     for line in recs_last:
        #         if line['trainee_name'] == account:
        #             key_month = 't' + str(int(line['month_training']))
        #             if account not in data_kq:
        #                 data_kq[account] = {'type': '19_1 Kết quả đào tạo'}
        #                 data_kq[account][key_month] = line.get('result') or 0
        #             else:
        #                 data_kq[account][key_month] = line.get('result') or 0
        # for key, value in data_kq.items():
        #     insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
        #                                   VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
        #                               '''.format(key=self.master_key,
        #                                          classification=value.get('type'),
        #                                          name=key,
        #                                          t1=value.get('t1') or 0,
        #                                          t2=value.get('t2') or 0,
        #                                          t3=value.get('t3') or 0,
        #                                          t4=value.get('t4') or 0,
        #                                          t5=value.get('t5') or 0,
        #                                          t6=value.get('t6') or 0,
        #                                          t7=value.get('t7') or 0,
        #                                          t8=value.get('t8') or 0,
        #                                          t9=value.get('t9') or 0,
        #                                          t10=value.get('t10') or 0,
        #                                          t11=value.get('t11') or 0,
        #                                          t12=value.get('t12') or 0,
        #                                          total=value.get('t13') or 0, )
        #     self._cr.execute(insert)

        data_tb = {}
        for account in key_account:
            for line in recs_last:
                if line['trainee_name'] == account:
                    key_month = 't' + str(int(line['month_training']))
                    if account not in data_tb:
                        data_tb[account] = {'type': '19_2 Kết quả tb'}
                        data_tb[account][key_month] = line.get('kqtb') or 0
                    else:
                        data_tb[account][key_month] = line.get('kqtb') or 0
        for key, value in data_tb.items():
            if not self._should_insert_record(value):
                continue
            insert = '''INSERT INTO employee_effective_value (master_key, classification,name ,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,total)
                                                 VALUES ({key},'{classification}','{name}',{t1},{t2},{t3},{t4},{t5},{t6},{t7},{t8},{t9},{t10},{t11},{t12},{total})
                                             '''.format(key=self.master_key,
                                                        classification=value.get('type'),
                                                        name=key,
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
                                                        t12=value.get('t12') or 0,
                                                        total=value.get('t13') or 0, )
            self._cr.execute(insert)

    def action_report(self):
        current_year = self.year
        employee_id = self.employee_id.ids
        self._cr.execute(
            "delete from employee_effective_value where master_key = {key}".format(key=self.master_key))

        self.chi_tieu_1(current_year, employee_id)
        self.chi_tieu_2(current_year, employee_id)
        self.chi_tieu_3(current_year, employee_id)
        self.chi_tieu_4(current_year, employee_id)
        self.chi_tieu_5(current_year, employee_id)
        self.chi_tieu_6(current_year, employee_id)
        self.chi_tieu_7(current_year, employee_id)
        self.chi_tieu_8(current_year, employee_id)
        self.chi_tieu_9(current_year, employee_id)
        self.chi_tieu_10(current_year, employee_id)
        # Ẩn "11 Tổng hiệu quả các dự án đã quản lý" (leader) theo yêu cầu:
        # 11.1 hiển thị thành "11", 11.2 thành "11.1".
        # self.chi_tieu_11(current_year, employee_id)
        self.chi_tieu_11_1(current_year, employee_id)
        self.chi_tieu_11_2(current_year, employee_id)
        self.chi_tieu_12(current_year, employee_id)
        self.chi_tieu_13(current_year, employee_id)
        self.chi_tieu_14(current_year, employee_id)
        self.chi_tieu_15(current_year, employee_id)
        self.chi_tieu_16(current_year, employee_id)
        self.chi_tieu_17(current_year, employee_id)
        self.chi_tieu_18(current_year, employee_id)
        self.chi_tieu_19(current_year, employee_id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo hiệu quả nhân viên ',
            'view_mode': 'tree',
            'res_model': "employee.effective.value",
            'context': {'year': current_year,
                        'search_default_classification': 1},
            'view_id': self.env.ref('effective_management.employee_effective_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',

        }
