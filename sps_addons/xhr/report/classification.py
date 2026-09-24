from collections import OrderedDict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from reportlab import xrange
from odoo import fields, api, models, tools


class ClassificationReport(models.Model):
    _name = 'report.classification.monthly'
    _auto = False
    _description = 'Classification Monthly'

    name = fields.Char()
    type_employee = fields.Selection([
        ('employee', 'Employee'), ('intern', 'Intern')
    ], string='Type Employee')
    m1 = fields.Integer()
    m2 = fields.Integer()
    m3 = fields.Integer()
    m4 = fields.Integer()
    m5 = fields.Integer()
    m6 = fields.Integer()
    m7 = fields.Integer()
    m8 = fields.Integer()
    m9 = fields.Integer()
    m10 = fields.Integer()
    m11 = fields.Integer()
    m12 = fields.Integer()
    ratio = fields.Float(compute='_compute_ratio')
    total = fields.Integer(compute='_compute_total')

    def _compute_ratio(self):
        data = self.env['report.classification.monthly'].read_group([], fields=[
                                                                        'm1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12', 'total'
                                                                    ],
                                                                    groupby=['name'], lazy=False)
        dict_total = {}
        for i in data:
            dict_total.update({i['name']: i['m1'] + i['m2'] + i['m3'] + i['m4'] + i['m5'] + i['m6'] + i['m7'] + i['m8'] + i['m9'] + i['m10'] + i['m11'] + i['m12']})

        for i in self:
            i.ratio = "{:.2f}".format(round((i.total/dict_total[i.name])*100, 1) if dict_total[i.name] > 0 else 0)

    def _compute_total(self):
        for i in self:
            i.total = i.m1 + i.m2 + i.m3 + i.m4 + i.m5 + i.m6 + i.m7 + i.m8 + i.m9 + i.m10 + i.m11 + i.m12

    def _prepare_value_month(self):
        vals = {}
        time_now = datetime.now()
        start_time = time_now - relativedelta(years=1)
        list_month = OrderedDict(
            ((start_time + timedelta(_)).strftime(r"%b-%y"), None) for _ in xrange((time_now - start_time).days)).keys()
        list_month = list(list_month)
        for v in range(1, 13):
            vals.update({'m%s' % (v): list_month[v]})
        return vals

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        label = self._prepare_value_month()
        res = super(ClassificationReport, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                toolbar=toolbar,
                                                                submenu=submenu)
        if view_type == 'tree':
            fields = res.get('fields')
            if fields:
                res['fields']['m1']['string'] = label['m1']
                res['fields']['m2']['string'] = label['m2']
                res['fields']['m3']['string'] = label['m3']
                res['fields']['m4']['string'] = label['m4']
                res['fields']['m5']['string'] = label['m5']
                res['fields']['m6']['string'] = label['m6']
                res['fields']['m7']['string'] = label['m7']
                res['fields']['m8']['string'] = label['m8']
                res['fields']['m9']['string'] = label['m9']
                res['fields']['m10']['string'] = label['m10']
                res['fields']['m11']['string'] = label['m11']
                res['fields']['m12']['string'] = label['m12']
        return res

    def _get_time_report(self):
        time_now = datetime.now()
        vals = {}
        for i in range(1, 13):
            vals.update({'m{}'.format(i): time_now - relativedelta(months=i - 1)})
        return vals

    @api.model
    def init(self):
        time = self._get_time_report()
        """ Event main report """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute(""" CREATE VIEW {table} AS (
        with fn as (
        select 
            dc.x_block_id,
            dc.x_employee_type as type_employee,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1)
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1)
                                ))
                and he.active = 't') as m1,
(select count(distinct he.id)
    from hr_employee he
    join hr_department hd on hd.id = he.department_id
    where  dc.x_block_id = hd.x_block_id 
                    and he.x_employee_type = dc.x_employee_type
                    and (
                        select 
                                (To_date(
                                concat_ws(
                                        '-',
                                        '1',
                                        (case when extract(month from current_date)+1-11 <= 0 
                                                    then 12+extract(month from current_date)+1-11 
                                                    else extract(month from current_date)+1-11 end),
                                        (case when extract(month from current_date)+1-11 <= 0 
                                                    then extract(year from current_date)-1 
                                                    else extract(year from current_date) end)),
                                        'DD-MM-YYYY') -1) + interval '1 months'
                        ) > x_onboard_date 
                        and 
                        (x_quit_date is null 
                            or x_quit_date > 
                            (select 
                                (To_date(
                                concat_ws(
                                        '-',
                                        '1',
                                        (case when extract(month from current_date)+1-11 <= 0 
                                                    then 12+extract(month from current_date)+1-11 
                                                    else extract(month from current_date)+1-11 end),
                                        (case when extract(month from current_date)+1-11 <= 0 
                                                    then extract(year from current_date)-1 
                                                    else extract(year from current_date) end)),
                                        'DD-MM-YYYY') -1) + interval '1 months'
                                    ))
                    and he.active = 't') as m2,
            (select count(distinct he.id)
                from hr_employee he
                join hr_department hd on hd.id = he.department_id
                where  dc.x_block_id = hd.x_block_id 
                    and he.x_employee_type = dc.x_employee_type
                    and (
                        select 
                                (To_date(
                                concat_ws(
                                        '-',
                                        '1',
                                        (case when extract(month from current_date)+1-11 <= 0 
                                                    then 12+extract(month from current_date)+1-11 
                                                    else extract(month from current_date)+1-11 end),
                                        (case when extract(month from current_date)+1-11 <= 0 
                                                    then extract(year from current_date)-1 
                                                    else extract(year from current_date) end)),
                                        'DD-MM-YYYY') -1) + interval '2 months'
                        ) > x_onboard_date 
                        and 
                        (x_quit_date is null 
                            or x_quit_date > 
                            (select 
                                (To_date(
                                concat_ws(
                                        '-',
                                        '1',
                                        (case when extract(month from current_date)+1-11 <= 0 
                                                    then 12+extract(month from current_date)+1-11 
                                                    else extract(month from current_date)+1-11 end),
                                        (case when extract(month from current_date)+1-11 <= 0 
                                                    then extract(year from current_date)-1 
                                                    else extract(year from current_date) end)),
                                        'DD-MM-YYYY') -1) + interval '2 months'
                                    ))
                    and he.active = 't') as m3,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '3 months'
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '3 months'
                                ))
                and he.active = 't') as m4,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '4 months'
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '4 months'
                                ))
                and he.active = 't') as m5,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '5 months'
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '5 months'
                                ))
                and he.active = 't') as m6,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '6 months'
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '6 months'
                                ))
                and he.active = 't') as m7,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '7 months'
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '7 months'
                                ))
                and he.active = 't') as m8,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '8 months'
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '8 months'
                                ))
                and he.active = 't') as m9,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '9 months'
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '9 months'
                                ))
                and he.active = 't') as m10,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '10 months'
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '10 months'
                                ))
                and he.active = 't') as m11,
            (select count(distinct he.id)
            from hr_employee he
            join hr_department hd on hd.id = he.department_id
            where  dc.x_block_id = hd.x_block_id 
                and he.x_employee_type = dc.x_employee_type
                and (
                    select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '11 months'
                    ) > x_onboard_date 
                    and 
                    (x_quit_date is null 
                        or x_quit_date > 
                        (select 
                            (To_date(
                            concat_ws(
                                    '-',
                                    '1',
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then 12+extract(month from current_date)+1-11 
                                                else extract(month from current_date)+1-11 end),
                                    (case when extract(month from current_date)+1-11 <= 0 
                                                then extract(year from current_date)-1 
                                                else extract(year from current_date) end)),
                                    'DD-MM-YYYY') -1) + interval '11 months'
                                ))
                and he.active = 't') as m12
        from 
            (select distinct e.x_employee_type, d.x_block_id
                from hr_employee e
                join hr_department d on d.id = e.department_id
                join hr_department_block b on b.id = d.x_block_id
                where e.active = 't') as dc
        order by dc.x_block_id,dc.x_employee_type
        )
        select row_number() OVER () AS id,hdb."name" ,fn.* from fn left join hr_department_block hdb on hdb.id=fn.x_block_id
        )""".format(
            table=self._table,
            m1=time['m12'].month, y1=time['m12'].year,
            m2=time['m11'].month, y2=time['m11'].year,
            m3=time['m10'].month, y3=time['m10'].year,
            m4=time['m9'].month, y4=time['m9'].year,
            m5=time['m8'].month, y5=time['m8'].year,
            m6=time['m7'].month, y6=time['m7'].year,
            m7=time['m6'].month, y7=time['m6'].year,
            m8=time['m5'].month, y8=time['m5'].year,
            m9=time['m4'].month, y9=time['m4'].year,
            m10=time['m3'].month, y10=time['m3'].year,
            m11=time['m2'].month, y11=time['m2'].year,
            m12=time['m1'].month, y12=time['m1'].year
        ))
