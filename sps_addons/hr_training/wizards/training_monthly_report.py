from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class TrainingMonthlyReportWizard(models.TransientModel):
    _name = 'training.monthly.report.wizard'
    _description = 'Training Monthly Report Wizard'

    year = fields.Selection(
        selection='_get_year_selection',
        string='Năm',
        required=True,
        default=lambda self: str(fields.Date.context_today(self).year),
    )

    def _get_year_selection(self):
        current_year = fields.Date.context_today(self).year
        end_year = current_year - 10
        return [(str(year), str(year)) for year in range(current_year, end_year - 1, -1)]

    def action_open_report_monthly(self):
        self.ensure_one()
        year = int(self.year)
        report_model = self.env['report.training.monthly.line'].sudo()
        report_model.sudo()._create_or_replace_view(year)
        action = self.env["ir.actions.act_window"]._for_xml_id('hr_training.action_report_hr_training_monthly_line')
        action_context = action.get('context') or {}
        if isinstance(action_context, str):
            action_context = safe_eval(action_context)
        combined_context = dict(self.env.context)
        combined_context.update(action_context)
        combined_context.update({'year': year})
        action['context'] = combined_context
        return action

    def action_open_report_trainers(self):
        self.ensure_one()
        year = int(self.year)
        report_model = self.env['report.trainers'].sudo()
        report_model._create_or_replace_view(year)
        action = self.env["ir.actions.act_window"]._for_xml_id('hr_training.action_report_hr_training_trainers')
        action_context = action.get('context') or {}
        if isinstance(action_context, str):
            action_context = safe_eval(action_context)
        combined_context = dict(self.env.context)
        combined_context.update(action_context)
        combined_context.update({'year': year})
        action['context'] = combined_context
        return action


