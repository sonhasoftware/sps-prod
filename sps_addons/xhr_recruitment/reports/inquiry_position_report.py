from odoo import fields, models, api, tools


class InquiryPositionReport(models.Model):
    _name = 'recruitment.inquiry.position.report'
    _auto = False
    _description = 'Inquiry Position Report'

    name = fields.Char()
    ongoing = fields.Integer(string='Trong thời hạn')
    delay = fields.Integer(string='Quá hạn')

    @api.model
    def init(self):
        """ Event main report """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute(""" CREATE VIEW {table} AS (
                select 
                row_number() OVER () AS id
                , name as name
                , coalesce (sum((quantity_ongoing - ongoing)), 0) as ongoing
                , coalesce (sum((quantity_delay - delay)), 0) as delay
                from (
                select 
                hj.name
                , (case when hrr.state = 'doing' then hrr.quantity end) as quantity_ongoing
                , (case when hrr.state = 'over_deadline' then hrr.quantity end) as quantity_delay
                , count(case when hrs.sequence = 6 and hrr.date_start >= ha.date_last_stage_update then 1 end) as ongoing
                , count(case when hrs.sequence = 6 and hrr.date_start < ha.date_last_stage_update then 1 end) as delay
                from hr_job hj
                left join hr_recruit_request hrr 
                on hj.id = hrr.job_id 
                left join hr_applicant ha 
                on ha.recruit_rq_id = hrr.id
                left join hr_recruitment_stage hrs 
                on ha.stage_id = hrs.id
                group by hj.name, hrr.quantity, hrr.date_start, ha.date_last_stage_update, hrr.state
                ) mt group by mt.name
            )""".format(table=self._table))