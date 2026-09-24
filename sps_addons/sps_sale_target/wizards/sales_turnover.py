from odoo import _, api, fields, models


class SalesTurnOverWizard(models.TransientModel):
    _name = "sale.turnover.wiz"
    _description = "Sale TurnOver Wizard"

    report_year = fields.Integer(
        string="Year",
        required=True,
        default=fields.Date.today().year
    )

    def ok(self):
        self.ensure_one()
        form_data = self.read()[0],
        create_user = self.env.user
        data = {
            "form_data": form_data,
            "create_user": create_user,
            "report_data": self._query_all()
        }
        return self.env.ref('sps_sale_target.sale_turnover_report_xlsx').report_action(
            self, data=data
        )

    def _query_all(self):
        self.ensure_one()
        query = """
SELECT
	month,
	SUM(total_untaxed_sent) AS untaxed_sent,
	SUM(total_untaxed_failed) AS untaxed_failed,
	SUM(total_untaxed_signed) AS untaxed_signed,
	SUM(total_operation) AS operation,
	SUM(total_service_maintainance) AS service_maintainance,
	SUM(turn_over_target) AS turnover_target
FROM (SELECT
		DATE_PART('month', date_order)::INT AS month,
		SUM(amount_untaxed) AS total_untaxed_sent,
		0 AS total_untaxed_failed,
		0 AS total_untaxed_signed,
		0 AS total_operation,
		0 AS total_service_maintainance,
		0 AS turn_over_target
	FROM sale_order
	WHERE EXTRACT('year' FROM date_order)::INT = %(year)s
	GROUP BY date_part('month', date_order)
	UNION ALL
	SELECT
		DATE_PART('month', date_order)::INT AS month,
		0 AS total_untaxed_sent,
		SUM(amount_untaxed) AS total_untaxed_failed,
		0 AS total_untaxed_signed,
		0 AS total_operation,
		0 AS total_service_maintainance,
		0 AS turn_over_target
	FROM sale_order
	WHERE state = 'cancel' AND EXTRACT('year' FROM date_order)::INT = %(year)s
	GROUP BY date_part('month', date_order)
	UNION ALL
	SELECT
		DATE_PART('month', date_order)::INT AS month,
		0 AS total_untaxed_sent,
		0 AS total_untaxed_failed,
		SUM(amount_untaxed) AS total_untaxed_signed,
		0 AS total_operation,
		0 AS total_service_maintainance,
		0 AS turn_over_target
	FROM sale_order
	WHERE state NOT IN ('draft', 'cancel') AND EXTRACT('year' FROM date_order)::INT = %(year)s
	GROUP BY date_part('month', date_order)
	UNION ALL
	SELECT
		DATE_PART('month', date_order)::INT AS month,
		0 AS total_untaxed_sent,
		0 AS total_untaxed_failed,
		0 AS total_untaxed_signed,
		SUM(amount_untaxed) AS total_operation,
		0 AS total_service_maintainance,
		0 AS turn_over_target
	FROM sale_order
	WHERE state NOT IN ('draft', 'cancel') AND project_type = 'operation' AND EXTRACT('year' FROM date_order)::INT = %(year)s
	GROUP BY date_part('month', date_order)
	UNION ALL
	SELECT
		DATE_PART('month', date_order)::INT AS month,
		0 AS total_untaxed_sent,
		0 AS total_untaxed_failed,
		0 AS total_untaxed_signed,
		0 AS total_operation,
		SUM(amount_untaxed) AS total_service_maintainance,
		0 AS turn_over_target
	FROM sale_order
	WHERE state NOT IN ('draft', 'cancel') AND project_type != 'operation' AND EXTRACT('year' FROM date_order)::INT = %(year)s
	GROUP BY date_part('month', date_order)
	UNION ALL
	SELECT
		CAST(target_month AS INT) AS month,
		0 AS total_untaxed_sent,
		0 AS total_untaxed_failed,
		0 AS total_untaxed_signed,
		0 AS total_operation,
		0 AS total_service_maintainance,
		sale_target AS turn_over_target
	FROM sale_target WHERE target_year = %(year)s) AS sq
GROUP BY month;
        """
        self._cr.execute(query, {"year": self.report_year})
        return self._cr.dictfetchall()
