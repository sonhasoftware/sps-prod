/** @odoo-module **/

odoo.define('account_saving.list_renderer_extension', function (require) {
    'use strict';

    var ListRenderer = require('web.ListRenderer');
    var core = require('web.core');
    var _t = core._t;

    ListRenderer.include({
        /**
         * Override _renderGroupRow to handle custom aggregate values for cash flow report
         * @override
         */
        _renderGroupRow: function (group, groupLevel) {
            var cells = [];

            var name = group.value === undefined ? _t('Undefined') : group.value;
            var groupBy = this.state.groupedBy[groupLevel];
            if (group.fields[groupBy.split(':')[0]].type !== 'boolean') {
                name = name || _t('Undefined');
            }
            var $th = $('<th>')
                .addClass('o_group_name')
                .attr('tabindex', -1)
                .text(name + ' (' + group.count + ')');
            var $arrow = $('<span>')
                .css('padding-left', 2 + (groupLevel * 20) + 'px')
                .css('padding-right', '5px')
                .addClass('fa');
            if (group.count > 0) {
                $arrow.toggleClass('fa-caret-right', !group.isOpen)
                    .toggleClass('fa-caret-down', group.isOpen);
            }
            $th.prepend($arrow);
            cells.push($th);

            var aggregateKeys = Object.keys(group.aggregateValues);
            var aggregateValues = _.mapObject(group.aggregateValues, function (value) {
                return { value: value };
            });
            var fieldName = null;
            var self = this;

            // Collect all RPC promises
            var rpcPromises = [];
            var keysToUpdate = [];

            for (var key in aggregateValues) {
                var field = this.state.fields[key];
                if (key.match(/^t\d+$/) && group.value === 'Tiền tồn cuối kỳ') {
                    console.log('Found Tiền tồn cuối kỳ group, processing field: ' + key);
                    keysToUpdate.push(key);
                    // Create promise for each RPC call
                    (function(currentKey) {
                        var promise = self._rpc({
                            model: 'cash.flow.view_report',
                            method: 'get_custom_aggregate_values',
                            args: [
                                'cash.flow.report.detail',  // model_name
                                [],  // domain
                                'parent_2',  // group_by
                                [currentKey],  // fields
                                group.value  // group_value
                            ]
                        }).then(function(result) {
                            return {key: currentKey, result: result};
                        }).catch(function(error) {
                            console.error('Error calling get_custom_aggregate_values for field ' + currentKey + ':', error);
                            return {key: currentKey, result: null};
                        });
                        rpcPromises.push(promise);
                    })(key);
                }
            }

            // Wait for all RPC promises to complete before rendering
            if (rpcPromises.length > 0) {
                Promise.all(rpcPromises).then(function(results) {
                    // Update aggregateValues with results from server
                    results.forEach(function(item) {
                        if (item && item.result && item.key) {
                            aggregateValues[item.key] = {value: item.result};
                        }
                    });

                    // Now render the aggregate cells with updated values
                    var aggregateCells = self._renderAggregateCells(aggregateValues);
                    console.log('Updated aggregateValues:', aggregateValues);

                    // Continue with the rest of the rendering logic
                    self._continueRenderGroupHeader(group, aggregateValues, aggregateCells, cells, $th, groupBy, aggregateKeys);
                }).catch(function(error) {
                    console.error('Error waiting for RPC promises:', error);
                    // Fallback to original rendering
                    var aggregateCells = self._renderAggregateCells(aggregateValues);
                    self._continueRenderGroupHeader(group, aggregateValues, aggregateCells, cells, $th, groupBy, aggregateKeys);
                });

                // Return early, the rest will be handled in the promise callback
                return $('<tr>').addClass('o_group_header_loading');
            }

            var aggregateCells = this._renderAggregateCells(aggregateValues);
            console.log(aggregateValues);
            var firstAggregateIndex = _.findIndex(this.columns, function (column) {
                return column.tag === 'field' && _.contains(aggregateKeys, column.attrs.name);
            });
            var colspanBeforeAggregate;
            if (firstAggregateIndex !== -1) {
                // if there are aggregates, the first $th goes until the first
                // aggregate then all cells between aggregates are rendered
                colspanBeforeAggregate = firstAggregateIndex;
                var lastAggregateIndex = _.findLastIndex(this.columns, function (column) {
                    return column.tag === 'field' && _.contains(aggregateKeys, column.attrs.name);
                });
                cells = cells.concat(aggregateCells.slice(firstAggregateIndex, lastAggregateIndex + 1));
                var colSpan = this.columns.length - 1 - lastAggregateIndex;
                if (colSpan > 0) {
                    cells.push($('<th>').attr('colspan', colSpan));
                }
            } else {
                var colN = this.columns.length;
                colspanBeforeAggregate = colN > 1 ? colN - 1 : 1;
                if (colN > 1) {
                    cells.push($('<th>'));
                }
            }
            if (this.hasSelectors) {
                colspanBeforeAggregate += 1;
            }
            $th.attr('colspan', colspanBeforeAggregate);

            if (group.isOpen && !group.groupedBy.length && (group.count > group.data.length)) {
                const lastCell = cells[cells.length - 1][0];
                this._renderGroupPager(group, lastCell);
            }
            if (group.isOpen && this.groupbys[groupBy]) {
                var $buttons = this._renderGroupButtons(group, this.groupbys[groupBy]);
                if ($buttons.length) {
                    var $buttonSection = $('<div>', {
                        class: 'o_group_buttons',
                    }).append($buttons);
                    $th.append($buttonSection);
                }
            }
            return $('<tr>')
                .addClass('o_group_header')
                .toggleClass('o_group_open', group.isOpen)
                .toggleClass('o_group_has_content', group.count > 0)
                .data('group', group)
                .append(cells);
        },

        /**
         * Continue rendering group header after RPC promises complete
         * @private
         */
        _continueRenderGroupHeader: function(group, aggregateValues, aggregateCells, cells, $th, groupBy, aggregateKeys) {
            var firstAggregateIndex = _.findIndex(this.columns, function (column) {
                return column.tag === 'field' && _.contains(aggregateKeys, column.attrs.name);
            });
            var colspanBeforeAggregate;
            if (firstAggregateIndex !== -1) {
                // if there are aggregates, the first $th goes until the first
                // aggregate then all cells between aggregates are rendered
                colspanBeforeAggregate = firstAggregateIndex;
                var lastAggregateIndex = _.findLastIndex(this.columns, function (column) {
                    return column.tag === 'field' && _.contains(aggregateKeys, column.attrs.name);
                });
                cells = cells.concat(aggregateCells.slice(firstAggregateIndex, lastAggregateIndex + 1));
                var colSpan = this.columns.length - 1 - lastAggregateIndex;
                if (colSpan > 0) {
                    cells.push($('<th>').attr('colspan', colSpan));
                }
            } else {
                var colN = this.columns.length;
                colspanBeforeAggregate = colN > 1 ? colN - 1 : 1;
                if (colN > 1) {
                    cells.push($('<th>'));
                }
            }
            if (this.hasSelectors) {
                colspanBeforeAggregate += 1;
            }
            $th.attr('colspan', colspanBeforeAggregate);

            if (group.isOpen && !group.groupedBy.length && (group.count > group.data.length)) {
                const lastCell = cells[cells.length - 1][0];
                this._renderGroupPager(group, lastCell);
            }
            if (group.isOpen && this.groupbys[groupBy]) {
                var $buttons = this._renderGroupButtons(group, this.groupbys[groupBy]);
                if ($buttons.length) {
                    var $buttonSection = $('<div>', {
                        class: 'o_group_buttons',
                    }).append($buttons);
                    $th.append($buttonSection);
                }
            }
            
            // Replace the loading row with the actual content
            var $existingRow = this.$el.find('.o_group_header_loading');
            if ($existingRow.length) {
                var $newRow = $('<tr>')
                    .addClass('o_group_header')
                    .toggleClass('o_group_open', group.isOpen)
                    .toggleClass('o_group_has_content', group.count > 0)
                    .data('group', group)
                    .append(cells);
                $existingRow.replaceWith($newRow);
            }
        },
    });

    return {
        ListRenderer: ListRenderer,
    };
}); 