# -*- coding: utf-8 -*-
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# (code, tên, input code) — các dòng thu nhập tách ra từ dòng gộp cũ. Category GROSS.
NEW_RULES = [
    ('LKPI', 'Lương KPI thực tế', 'OTHER_KPI_SALARY'),
    ('LNG', 'Lương ngoài giờ', 'OTHER_OT_SALARY'),
    ('LDL', 'Lương hỗ trợ đi lại', 'OTHER_TRAVEL_SALARY'),
]


def migrate(cr, version):
    """Tách dòng gộp 'Thu nhập theo giờ công thực tế' thành 4 thành phần.

    - Đổi tên rule TNTGCTT (đọc OTHER_WAGE_TOTAL, nay = lương chính thực tế).
    - Thêm rule LKPI / LNG / LDL (đọc OTHER_KPI_SALARY / OTHER_OT_SALARY / OTHER_TRAVEL_SALARY),
      category GROSS -> cộng vào lương thực lĩnh. Idempotent theo (code, struct).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    Rule = env['hr.salary.rule']
    gross = env['hr.salary.rule.category'].search([('code', '=', 'GROSS')], limit=1)
    if not gross:
        _logger.warning('[xhr_payroll] Không tìm thấy category GROSS, bỏ qua tách dòng lương.')
        return

    base_rules = Rule.search([('code', '=', 'TNTGCTT')])
    base_rules.write({'name': 'Lương chính thực tế'})
    struct_ids = base_rules.mapped('struct_id')

    created = 0
    for struct in struct_ids:
        for code, name, input_code in NEW_RULES:
            if Rule.search([('code', '=', code), ('struct_id', '=', struct.id)], limit=1):
                continue
            Rule.create({
                'name': name,
                'code': code,
                'category_id': gross.id,
                'struct_id': struct.id,
                'sequence': 1,
                'appears_on_payslip': True,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute':
                    "result = inputs.%s.amount if inputs.%s else 0.0" % (input_code, input_code),
            })
            created += 1
    _logger.info('[xhr_payroll] Tách dòng lương: đổi tên TNTGCTT + tạo %s rule mới.', created)
