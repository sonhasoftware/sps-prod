# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.base.models.ir_actions import IrActions as BaseIrActions
from odoo.exceptions import MissingError, AccessError
from collections import defaultdict


def get_bindings(self, model_name):
    """
    Mặc định, các server actions được hiển thị ở khối "Actions",
    phần chỉnh sửa này thêm thuộc tính x_print_menu, nếu True thì action sẽ hiển thị ở khối "Print"
    để gọi các action đặc thù cho việc in báo cáo mà không cần trình bày dưới dạng các Button hay đặt trong "Actions"
    """
    """ Retrieve the list of actions bound to the given model.

       :return: a dict mapping binding types to a list of dict describing
                actions, where the latter is given by calling the method
                ``read`` on the action record.
    """
    # DLE P19: Need to flush before doing the SELECT, which act as a search.
    # Test `test_bindings`
    self.flush()
    cr = self.env.cr
    query = """ SELECT a.id, a.type, case when (a.x_print_menu is null or a.x_print_menu = 'f') then a.binding_type else 'report' end as binding_type
                FROM ir_actions a, ir_model m
                WHERE a.binding_model_id=m.id AND m.model=%s
                ORDER BY a.id """
    cr.execute(query, [model_name])
    IrModelAccess = self.env['ir.model.access']

    # discard unauthorized actions, and read action definitions
    result = defaultdict(list)
    user_groups = self.env.user.groups_id
    for action_id, action_model, binding_type in cr.fetchall():
        try:
            action = self.env[action_model].sudo().browse(action_id)
            action_groups = getattr(action, 'groups_id', ())
            action_model = getattr(action, 'res_model', False)
            if action_groups and not action_groups & user_groups:
                # the user may not perform this action
                continue
            if action_model and not IrModelAccess.check(action_model, mode='read', raise_exception=False):
                # the user won't be able to read records
                continue
            result[binding_type].append(action.read()[0])
        except (AccessError, MissingError):
            continue

    # sort actions by their sequence if sequence available
    if result.get('action'):
        result['action'] = sorted(result['action'], key=lambda vals: vals.get('sequence', 0))
    return result


BaseIrActions.get_bindings = get_bindings


class IrActions(models.Model):
    _inherit = 'ir.actions.actions'

    x_print_menu = fields.Boolean('Show in print', default=False, copy=False,
                                  help='Set True if this action should show in Print section')
