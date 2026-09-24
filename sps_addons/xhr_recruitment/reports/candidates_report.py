from odoo import fields, api, models, tools


class CandidateReport(models.Model):
    _name = 'recruitment.candidate.report'
    _auto = False
    _description = 'Candidates Report'

    name = fields.Char(string='Vị trí')
    total = fields.Integer(string='Tổng hồ sơ')
    apply = fields.Integer(string='Số hồ sơ đạt')
    reject = fields.Integer(string='Số hồ sơ không đạt đạt')
    interview_pass = fields.Integer(string='KQ phỏng vấn tuyển')
    interview_fail = fields.Integer(string='KQ phỏng vấn loại')
    archived = fields.Integer(string='KQ phỏng vấn có thể phù hợp, lưu hồ sơ')
    reject_job = fields.Integer(string='Từ chối nhận việc')
    pending = fields.Integer(string='Đang xem xét')
    approved = fields.Integer(string='Đồng ý nhận việc')

    @api.model
    def init(self):
        """ Event main report """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute(""" CREATE VIEW {table} AS (
            select 
            row_number() OVER () AS id
            , hj.name as name
            , count(ha.id) as total
            , count(case when hrs.sequence > 0 then 1 end) as apply
            , count(case when hrs.sequence = 0 and ha.refuse_reason_id is not null then 1 end) as reject
            , count(case when hrs.sequence > 4 then 1 end) as interview_pass
            , count(case when hrs.sequence <= 2 and ha.refuse_reason_id is not null then 1 end) as interview_fail
            , count(case when ha.refuse_reason_id is not null then 1 end) as archived
            , count(case when ha.refuse_reason_id is not null and hrs.sequence = 5 then 1 end) as reject_job
            , count(case when hrs.sequence = 5 then 1 end) as pending
            , count(case when hrs.sequence = 6 then 1 end) as approved
            from hr_job hj
            left join hr_applicant ha 
            on hj .id = ha.job_id 
            left join hr_recruitment_stage hrs on ha.stage_id = hrs.id
            group by hj.name
        )""".format(table=self._table))