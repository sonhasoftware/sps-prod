odoo.define('xpruchase/static/js/list_editable_renderer.js', function (require) {
"use strict";
var ListRenderer = require('web.ListRenderer');
var core = require('web.core');
var _t = core._t;

ListRenderer.include({
    _renderHeader: function () {
            var $thead = this._super.apply(this, arguments);
            if (this.addTrashIcon) {
                $thead.find('tr').prepend($('<th>', {class: 'o_list_record_remove_header'}));
            }
            return $thead;
        },
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);
        if (this.addTrashIcon) {
            var $icon = this.isMany2Many ?
                $('<button>', {'class': 'fa fa-times', 'name': 'unlink', 'aria-label': _t('Unlink row ') + (index + 1)}) :
                $('<button>', {'class': 'fa fa-trash-o', 'name': 'delete', 'aria-label': _t('Delete row ') + (index + 1)});
            var $td = $('<td>', {class: 'o_list_record_remove'}).prepend($icon);
            $row.prepend($td);
        }
        return $row;
        },
    });
});