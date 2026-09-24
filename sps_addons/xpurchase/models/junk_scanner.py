# -*- coding: utf-8 -*-
"""Quét tham chiếu để tìm record "rác" (chưa được dùng ở đâu).

Logic dùng chung cho partner rác và sản phẩm rác: duyệt TOÀN BỘ cột Many2one và
bảng quan hệ Many2many trỏ tới model đích, gom tập id đang được tham chiếu thật sự
trong DB. Bỏ qua:
  - Model nhiễu kỹ thuật / cấu hình (theo excluded_prefixes: mail, ir, bus...).
  - Model SQL view (_auto = False) vì là dữ liệu dẫn xuất từ bảng gốc đã quét.
  - Model abstract / transient (wizard) vì không phải dữ liệu nghiệp vụ bền vững.
"""
import logging

_logger = logging.getLogger(__name__)

# Prefix model bỏ qua khi quét tham chiếu tới res.partner
PARTNER_EXCLUDED_PREFIXES = (
    'ir', 'mail', 'bus', 'calendar', 'website', 'iap', 'snailmail', 'sms',
    'rating', 'utm', 'link.tracker', 'phone_blacklist', 'mail_blacklist',
    'base_import', 'base.partner.merge', 'portal', 'res.config', 'res.lang',
    'res.partner',                       # link cấu trúc/tag/cha-con của chính partner
    'account.reconcile.model', 'account.transfer.model',  # cấu hình đối soát/chuyển khoản
)

# Prefix model bỏ qua khi quét tham chiếu tới product.product / product.template
PRODUCT_EXCLUDED_PREFIXES = (
    'ir', 'mail', 'bus', 'calendar', 'website', 'iap', 'snailmail', 'sms',
    'rating', 'utm', 'link.tracker', 'base_import', 'res.config',
    'product',   # link cấu trúc/biến thể/supplierinfo/pricelist/packaging của chính product
    'stock.location.route',   # cấu hình tuyến kho (Mua/Sản xuất/MTO) — gán mặc định cho
                              # gần như mọi SP, KHÔNG phải mua/bán/nhập thực tế
)


def scan_referenced_ids(env, relations, excluded_prefixes):
    """Trả về set id (thuộc các model trong ``relations``) đang được tham chiếu ở
    bất kỳ cột Many2one hoặc bảng Many2many nào trong DB, trừ các model nhiễu."""
    cr = env.cr
    Field = env['ir.model.fields'].sudo()
    referenced = set()

    def _is_excluded(model_name):
        return any(model_name == p or model_name.startswith(p + '.')
                   for p in excluded_prefixes)

    def _real_model(model_name):
        """Trả Model nếu là model bảng thật (không abstract/transient/SQL view)."""
        Model = env.get(model_name)
        if Model is None or Model._abstract or Model._transient or not Model._auto:
            return None
        return Model

    # ---- Many2one: cột FK trực tiếp ----
    m2o = Field.search([('ttype', '=', 'many2one'),
                        ('relation', 'in', relations), ('store', '=', True)])
    for f in m2o:
        if _is_excluded(f.model):
            continue
        Model = _real_model(f.model)
        if Model is None:
            continue
        table, column = Model._table, f.name
        cr.execute("""SELECT 1 FROM information_schema.columns
                      WHERE table_name = %s AND column_name = %s LIMIT 1""",
                   (table, column))
        if not cr.fetchone():
            continue
        try:
            with cr.savepoint():
                cr.execute('SELECT DISTINCT "%s" FROM "%s" WHERE "%s" IS NOT NULL'
                           % (column, table, column))
                referenced.update(r[0] for r in cr.fetchall())
        except Exception as e:
            _logger.warning('Junk scan bỏ qua m2o %s.%s: %s', f.model, column, e)

    # ---- Many2many: bảng quan hệ trung gian ----
    m2m = Field.search([('ttype', '=', 'many2many'),
                        ('relation', 'in', relations), ('store', '=', True)])
    for f in m2m:
        if _is_excluded(f.model):
            continue
        if _real_model(f.model) is None:
            continue
        rel_table, col2 = f.relation_table, f.column2
        if not rel_table or not col2:
            continue
        cr.execute("SELECT to_regclass(%s)", (rel_table,))
        if not cr.fetchone()[0]:
            continue
        try:
            with cr.savepoint():
                cr.execute('SELECT DISTINCT "%s" FROM "%s" WHERE "%s" IS NOT NULL'
                           % (col2, rel_table, col2))
                referenced.update(r[0] for r in cr.fetchall())
        except Exception as e:
            _logger.warning('Junk scan bỏ qua m2m %s.%s: %s', f.model, f.name, e)

    return referenced
