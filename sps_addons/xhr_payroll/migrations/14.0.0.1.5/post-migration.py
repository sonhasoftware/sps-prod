# -*- coding: utf-8 -*-
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

MEAL_RULE_CODE = 'HTAC'
MEAL_PY = (
    "# Hỗ trợ ăn ca (40k/suất x số ngày làm > 4h), tính ở input OTHER_MEAL_SUPPORT\n"
    "result = inputs.OTHER_MEAL_SUPPORT.amount if inputs.OTHER_MEAL_SUPPORT else 0.0"
)


def migrate(cr, version):
    """Tạo salary rule 'Hỗ trợ ăn ca' (HTAC) cho các cấu trúc lương.

    Cấu trúc lương được tạo qua UI (không có xmlid) nên rule được tạo bằng code,
    idempotent: chỉ tạo cho structure có rule chính TNTGCTT mà CHƯA có rule HTAC.
    Category ALW -> cộng vào lương thực lĩnh (net).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    Rule = env['hr.salary.rule']
    alw = env['hr.salary.rule.category'].search([('code', '=', 'ALW')], limit=1)
    if not alw:
        _logger.warning('[xhr_payroll] Không tìm thấy category ALW, bỏ qua tạo rule HTAC.')
        return

    # Các structure có rule lương chính (loại trừ structure không dùng)
    struct_ids = Rule.search([('code', '=', 'TNTGCTT')]).mapped('struct_id')
    created = 0
    for struct in struct_ids:
        exists = Rule.search([('code', '=', MEAL_RULE_CODE), ('struct_id', '=', struct.id)], limit=1)
        if exists:
            continue
        Rule.create({
            'name': 'Hỗ trợ ăn ca',
            'code': MEAL_RULE_CODE,
            'category_id': alw.id,
            'struct_id': struct.id,
            'sequence': 3,
            'appears_on_payslip': True,
            'condition_select': 'none',
            'amount_select': 'code',
            'amount_python_compute': MEAL_PY,
        })
        created += 1
    _logger.info('[xhr_payroll] Tạo rule HTAC (Hỗ trợ ăn ca) cho %s cấu trúc lương.', created)
