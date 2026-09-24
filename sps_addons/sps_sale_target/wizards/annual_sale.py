from odoo import _, api, fields, models


class AnnualSaleReportWiz(models.TransientModel):
    _name = 'annual.sale.report'
    _description = 'Annual Sale Report Wizard'

    year = fields.Integer(
        string="Year",
        required=True,
        default=fields.Date.today().year,
        readonly=True
    )

    def ok(self):
        self.ensure_one()
        create_user = self.env.user
        data = {
            "create_user": create_user,
            "report_data": self._query_all()
        }
        return self.env.ref('sps_sale_target.annual_sale_report_xlsx').report_action(
            self, data=data
        )

    def _query_all(self):
        self.ensure_one()
        query = """
SELECT
	year,
	SUM(total_amount) AS amount,
	SUM(total_profit) AS profit,
	SUM(total_sale_target) AS sale_target
FROM (SELECT
        DATE_PART('year', create_date)::INT AS year,
        SUM(amount_untaxed) AS total_amount,
        SUM(profit_after_tax) AS total_profit,
        0 AS total_sale_target
    FROM sale_order
    WHERE state NOT IN ('cancel', 'draft')
        AND DATE_PART('year', create_date)::INT BETWEEN %(start_year)s AND %(end_year)s 
    GROUP BY 1
    UNION ALL
    SELECT
        target_year AS year,
        0 AS total_amount,
        0 AS total_profit,
        SUM(sale_target) AS total_sale_target
    FROM sale_target
    WHERE target_year BETWEEN %(start_year)s AND %(end_year)s
    GROUP BY 1) AS s_q
GROUP BY 1
        """
        self._cr.execute(query, {
            "start_year": self.year - 5,
            "end_year": self.year + 4
        })
        return self._cr.dictfetchall()