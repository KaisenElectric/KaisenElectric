/** @odoo-module **/

import {PivotModel} from "@web/views/pivot/pivot_model";
import LegacyPivotModel from "@web/legacy/js/views/pivot/pivot_model";
import {patch} from "web.utils";
import Domain from 'web.Domain';


const _getGroupSubdivision = PivotModel.prototype._getGroupSubdivision;

Object.defineProperty(PivotModel.prototype, "_getGroupSubdivision", {
  value: async function (group, rowGroupBy, colGroupBy, config) {
    let result = await _getGroupSubdivision.call(this, group, rowGroupBy, colGroupBy, config);
    if (config.metaData.resModel == "stock.valuation.layer") {
        result.subGroups.forEach( x => x.average_unit_value = x.value / (x.quantity || 1))
    }
    return result;
  }
});

patch(LegacyPivotModel.prototype, "kaisen.KaisenLegacyPivotModel", {
  _prepareData: function (group, groupSubdivisions) {
    var self = this;

    var groupRowValues = group.rowValues;
    var groupRowLabels = [];
    var rowSubTree = this.rowGroupTree;
    var root;
    if (groupRowValues.length) {
      rowSubTree = this._findGroup(this.rowGroupTree, groupRowValues);
      root = rowSubTree.root;
      groupRowLabels = root.labels;
    }

    var groupColValues = group.colValues;
    var groupColLabels = [];
    if (groupColValues.length) {
      root = this._findGroup(this.colGroupTree, groupColValues).root;
      groupColLabels = root.labels;
    }

    groupSubdivisions.forEach(function (groupSubdivision) {
      groupSubdivision.subGroups.forEach(function (subGroup) {
        if (self.modelName === "stock.valuation.layer") {
          subGroup.average_unit_value = subGroup.value / (subGroup.quantity || 1)
        }
        var rowValues = groupRowValues.concat(self._getGroupValues(subGroup, groupSubdivision.rowGroupBy));
        var rowLabels = groupRowLabels.concat(self._getGroupLabels(subGroup, groupSubdivision.rowGroupBy));

        var colValues = groupColValues.concat(self._getGroupValues(subGroup, groupSubdivision.colGroupBy));
        var colLabels = groupColLabels.concat(self._getGroupLabels(subGroup, groupSubdivision.colGroupBy));

        if (!colValues.length && rowValues.length) {
          self._addGroup(self.rowGroupTree, rowLabels, rowValues);
        }
        if (colValues.length && !rowValues.length) {
          self._addGroup(self.colGroupTree, colLabels, colValues);
        }

        var key = JSON.stringify([rowValues, colValues]);
        var originIndex = groupSubdivision.group.originIndex;

        if (!(key in self.measurements)) {
          self.measurements[key] = self.data.origins.map(function () {
            return self._getMeasurements({});
          });
        }
        self.measurements[key][originIndex] = self._getMeasurements(subGroup);

        if (!(key in self.counts)) {
          self.counts[key] = self.data.origins.map(function () {
            return 0;
          });
        }
        self.counts[key][originIndex] = subGroup.__count;

        if (!(key in self.groupDomains)) {
          self.groupDomains[key] = self.data.origins.map(function () {
            return Domain.FALSE_DOMAIN;
          });
        }
        // if __domain is not defined this means that we are in the
        // case where
        // groupSubdivision.rowGroupBy = groupSubdivision.rowGroupBy = []
        if (subGroup.__domain) {
          self.groupDomains[key][originIndex] = subGroup.__domain;
        }
      });
    });

    if (this.data.sortedColumn) {
      this.sortRows(this.data.sortedColumn, rowSubTree);
    }
  },
});
