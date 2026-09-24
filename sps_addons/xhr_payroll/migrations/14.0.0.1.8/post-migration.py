# -*- coding: utf-8 -*-
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Công thức thuế TNCN mới (bảng lương từ 01/07/2026) — khớp mẫu SALARY NEW:
#   Thu nhập chịu thuế = Tổng thu nhập tháng − ăn ca − lương ngoài giờ (OT).
# - Thu nhập chịu thuế gồm: base(TNTGCTT)+KPI(LKPI)+đi lại(LDL)
#   + thưởng khác(THCKTNK)+xăng(HTXX)-bù/trừ(BTLT)+bù công(HTTLBDC)+thưởng nóng(OTHER_BONUS_INSTANT).
# - KHÔNG chịu thuế: lương ngoài giờ (LNG/OT) và ăn ca (HTAC).
# - Giảm trừ: giảm trừ gia cảnh (OTHER_DEDUCTION_PERSONAL_TAX) + BHXH/YT/TN.
# - BỎ hẳn miễn thuế 15% phụ cấp nhà ở và trừ phụ cấp ăn trưa cũ (x_allowance_home/lunch).
TTNCNPN_PY = """
amount_total = (result_rules.TNTGCTT['total'] + result_rules.LKPI['total']
    + result_rules.LDL['total']
    + result_rules.THCKTNK['total'] + result_rules.HTXX['total'] - result_rules.BTLT['total']
    + result_rules.HTTLBDC['total'] + inputs.OTHER_BONUS_INSTANT.amount)
amount_tax = (amount_total - inputs.OTHER_DEDUCTION_PERSONAL_TAX.amount
    - result_rules.BHXH['total'] - result_rules.BHYT['total'] - result_rules.BHTN['total'])
if amount_tax > 100000000:
    result = amount_tax * 0.35 - 14500000
elif amount_tax > 60000000:
    result = amount_tax * 0.3 - 9500000
elif amount_tax > 30000000:
    result = amount_tax * 0.2 - 3500000
elif amount_tax > 10000000:
    result = amount_tax * 0.1 - 500000
elif amount_tax > 0:
    result = amount_tax * 0.05
else:
    result = 0
""".strip()


def migrate(cr, version):
    """Cập nhật công thức thuế TNCN (rule TTNCNPN) theo income tách mới + miễn thuế ăn ca."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    rules = env['hr.salary.rule'].search([('code', '=', 'TTNCNPN')])
    rules.write({'amount_python_compute': TTNCNPN_PY})
    _logger.info('[xhr_payroll] Cập nhật công thức thuế TNCN cho %s rule TTNCNPN.', len(rules))
