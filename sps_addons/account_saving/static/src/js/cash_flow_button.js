/** @odoo-module **/

odoo.define('account_saving.cash_flow_button', function (require) {
    'use strict';

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;

    var CashFlowListController = ListController.extend({
        events: _.extend({}, ListController.prototype.events, {
            'click .custom_action_button': '_onCustomButtonClick',
        }),

        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                var $customButton = $('<button type="button" class="btn btn-primary custom_action_button">' +
                    '<i class="fa fa-cogs"/> Preview báo cáo</button>');
                this.$buttons.prepend($customButton);
            }
        },
        _onCustomButtonClick: function (params) {
        var self = this;

        // Gọi trực tiếp action wizard
        var action = {
            type: 'ir.actions.act_window',
            name: 'Chọn năm báo cáo',
            res_model: 'cash.flow.preview.wizard',
            view_mode: 'form',
            target: 'new',
            views: [[false, 'form']],
            context: {}
        };

        self.do_action(action, {
            on_close: function () {
                console.log('Wizard closed, reloading...');
                self.trigger_up('reload', { keepChanges: true });
            },
        });
    },

    });

    var CashFlowListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: CashFlowListController,
        }),
    });

    viewRegistry.add('cash_flow_tree', CashFlowListView);

    return {
        CashFlowListController: CashFlowListController,
        CashFlowListView: CashFlowListView,
    };
}); 