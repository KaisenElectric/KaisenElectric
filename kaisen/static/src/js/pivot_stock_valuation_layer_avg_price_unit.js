/** @odoo-module **/

import { PivotModel } from "@web/views/pivot/pivot_model";

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