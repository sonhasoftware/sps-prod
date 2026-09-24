# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    @api.constrains('state')
    def constrain_state_set_project_date(self):
        for r in self:
            if r.state != 'validated':
                self._cr.execute("update hr_work_entry set state=%s where id=%s", [r.state, r.id])
            else:
                for line in r.x_line_ids:
                    project_id = line.project_id
                    if not project_id:
                        continue
                    # Update project's end date
                    self._cr.execute('''
                        select y.x_date
                        from hr_work_entry_line x
                            inner join hr_work_entry y on x.entry_id=y.id
                        where x.project_id=%s
                        order by y.x_date desc, y.id desc
                        limit 1
                    ''', [project_id.id])
                    last_entry_id = self._cr.fetchone()
                    self._cr.execute("update project_project set x_date_end=%s where id=%s", [
                        last_entry_id[0] if last_entry_id else r.x_date,
                        project_id.id
                    ])

                    # Update project's start date
                    if not project_id.x_date_start:
                        self._cr.execute('''
                            select y.x_date
                            from hr_work_entry_line x
                                inner join hr_work_entry y on x.entry_id=y.id
                            where x.project_id=%s
                            order by y.x_date asc, y.id asc
                            limit 1
                        ''', [project_id.id])
                        first_entry_id = self._cr.fetchone()
                        self._cr.execute("update project_project set x_date_start=%s where id=%s", [
                            first_entry_id[0] if first_entry_id else r.x_date,
                            project_id.id
                        ])

                self._cr.execute("update hr_work_entry set state='validated' where id=%s", [r.id])
            (r.x_line_ids.mapped('project_id') | r.x_allowance_ids.mapped('project_id'))._load_member_info()
