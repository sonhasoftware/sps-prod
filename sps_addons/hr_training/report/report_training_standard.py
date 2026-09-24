from odoo import models, fields, api


class ReportTrainingStandard(models.TransientModel):
    _name = 'report.training.standard'
    _description = 'Standard'

    employee_id = fields.Many2one('hr.employee')
    department_id = fields.Many2one('hr.department')
    report_lines = fields.One2many('report.training.standard.line', 'standard_id')

    def get_report(self):
        sql = """
            select 
            he.x_code as x_code,
            he.name as name,
            hd.name as department,
            hj.name as job_title, 
            hti.name as training_item,
            htc.name as category,
            htir.result_require as require,
            htr1.training_date as date,
            he2.name as trainer,
            htr1.document_name as document_name,
            htr1.result1 as result
        from hr_employee he
        left join hr_training_item_require htir on htir.job_id = he.job_id
        and (htir.job_department_id  = he.department_id or htir.job_department_id is null)
        left join hr_job hj on hj.id = he.job_id
        left join hr_department hd on hd.id = he.department_id
        left join hr_training_item hti on hti.id = htir.item_id
        left join hr_training_categ htc on htc.id = hti.categ_id
        left join 
                (select 
                    htr.trainee_id,
                    htrl.training_item_id,
                    max(htrl.trainer_id) trainer_id,
                    max(htrl.document_name) document_name,
                    max(htr.date) as training_date,
                    max(htrl.result) as result1
                from hr_training_result htr
                left join hr_training_result_line htrl on htrl.master_id = htr.id
                where htrl.result is not null and htrl.result != '0'
                group by 	htr.trainee_id,htrl.training_item_id
                ) htr1 
            on htr1.trainee_id = he.id and htr1.training_item_id = hti.id
        left join hr_employee he2 on he2.id = htr1.trainer_id
        where he.active = true
        """
        if self.employee_id:
            sql += ' and he.id = {}'.format(self.employee_id.id)
        if self.department_id:
            sql += ' and hd.id = {}'.format(self.department_id.id)
        self.env.cr.execute(sql)
        data = self.env.cr.dictfetchall()
        for item in data:
            item.update({'standard_id': self.id})
        data_old = self.env['report.training.standard.line'].search([('standard_id', '=', self.id)])
        if data_old:
            data_old.unlink()
        self.env['report.training.standard.line'].create(data)
        pass


class ReportTrainingStandardLine(models.TransientModel):
    _name = 'report.training.standard.line'
    _description = 'Standard line'

    x_code = fields.Char()
    name = fields.Char()
    department = fields.Char()
    job_title = fields.Char()
    training_item = fields.Char()
    category = fields.Char()
    require = fields.Char()
    date = fields.Date()
    trainer = fields.Char()
    document_name = fields.Char()
    result = fields.Char()
    standard_id = fields.Many2one('report.training.standard')

    def name_get(self):
        return [(record.id, "%s:%s" % (self._name, record.value)) for record in self]