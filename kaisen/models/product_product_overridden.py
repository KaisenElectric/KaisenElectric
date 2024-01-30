from odoo.addons.stock_account.models.product import ProductProduct
from odoo.tools import float_repr, float_is_zero


def _prepare_out_svl_vals(self, quantity, company, warehouse_id=None):
    """Prepare the values for a stock valuation layer created by a delivery.

    :param quantity: the quantity to value, expressed in `self.uom_id`
    :return: values to use in a call to create
    :rtype: dict
    """
    self.ensure_one()
    company_id = self.env.context.get('force_company', self.env.company.id)
    company = self.env['res.company'].browse(company_id)
    currency = company.currency_id
    # Quantity is negative for out valuation layers.
    quantity = -1 * quantity
    vals = {
        'product_id': self.id,
        'value': currency.round(quantity * self.standard_price),
        'unit_cost': self.standard_price,
        'quantity': quantity,
    }
    # Kaisen: Changes start
    if self.cost_method in ("average", "fifo", "fifowh"):
        fifo_vals = self._run_fifo(abs(quantity), company, warehouse_id)
        # Kaisen: Changes end
        vals['remaining_qty'] = fifo_vals.get('remaining_qty')
        # In case of AVCO, fix rounding issue of standard price when needed.
        if self.cost_method == 'average':
            rounding_error = currency.round(self.standard_price * self.quantity_svl - self.value_svl)
            if rounding_error:
                # If it is bigger than the (smallest number of the currency * quantity) / 2,
                # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                if abs(rounding_error) <= (abs(quantity) * currency.rounding) / 2:
                    vals['value'] += rounding_error
                    vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                        '+' if rounding_error > 0 else '',
                        float_repr(rounding_error, precision_digits=currency.decimal_places),
                        currency.symbol
                    )
        # Kaisen: Changes start
        if self.cost_method in ("fifo", "fifowh"):
            # Kaisen: Changes end
            vals.update(fifo_vals)
    return vals

ProductProduct._prepare_out_svl_vals = _prepare_out_svl_vals


def _run_fifo(self, quantity, company, warehouse_id=None):
    self.ensure_one()

    # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
    qty_to_take_on_candidates = quantity
    # Kaisen: Changes start
    candidates_domain = [
        ("product_id", "=", self.id),
        ("remaining_qty", ">", 0),
        ("company_id", "=", company.id),
    ]
    if warehouse_id:
        candidates_domain.append(("warehouse_id", "=", warehouse_id.id))
    candidates = self.env['stock.valuation.layer'].sudo().search(candidates_domain)
    # Kaisen: Changes end
    new_standard_price = 0
    tmp_value = 0  # to accumulate the value taken on the candidates
    for candidate in candidates:
        qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)

        candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
        new_standard_price = candidate_unit_cost
        value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
        value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
        new_remaining_value = candidate.remaining_value - value_taken_on_candidate

        candidate_vals = {
            'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
            'remaining_value': new_remaining_value,
        }

        candidate.write(candidate_vals)

        qty_to_take_on_candidates -= qty_taken_on_candidate
        tmp_value += value_taken_on_candidate

        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
            if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
                next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
                new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
            break

    # Update the standard price with the price of the last used candidate, if any.
    # Kaisen: Changes start
    if new_standard_price and self.cost_method in ("fifo", "fifowh"):
        # Kaisen: Changes end
        self.sudo().with_company(company.id).with_context(disable_auto_svl=True).standard_price = new_standard_price

    # If there's still quantity to value but we're out of candidates, we fall in the
    # negative stock use case. We chose to value the out move at the price of the
    # last out and a correction entry will be made once `_fifo_vacuum` is called.
    vals = {}
    if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
        vals = {
            'value': -tmp_value,
            'unit_cost': tmp_value / quantity,
        }
    else:
        assert qty_to_take_on_candidates > 0
        last_fifo_price = new_standard_price or self.standard_price
        negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
        tmp_value += abs(negative_stock_value)
        vals = {
            'remaining_qty': -qty_to_take_on_candidates,
            'value': -tmp_value,
            'unit_cost': last_fifo_price,
        }
    # Kaisen: Changes start
    if warehouse_id:
        vals["warehouse_id"] = warehouse_id.id
    # Kaisen: Changes end
    return vals

ProductProduct._run_fifo = _run_fifo

def _prepare_in_svl_vals(self, quantity, unit_cost):
    """Prepare the values for a stock valuation layer created by a receipt.

    :param quantity: the quantity to value, expressed in `self.uom_id`
    :param unit_cost: the unit cost to value `quantity`
    :return: values to use in a call to create
    :rtype: dict
    """
    self.ensure_one()
    company_id = self.env.context.get('force_company', self.env.company.id)
    company = self.env['res.company'].browse(company_id)
    vals = {
        'product_id': self.id,
        'value': company.currency_id.round(unit_cost * quantity),
        'unit_cost': unit_cost,
        'quantity': quantity,
    }
    # Kaisen: Changes start
    if self.cost_method in ("average", "fifo", "fifowh"):
        # Kaisen: Changes end
        vals['remaining_qty'] = quantity
        vals['remaining_value'] = vals['value']
    return vals

ProductProduct._prepare_in_svl_vals = _prepare_in_svl_vals

def _run_fifo_vacuum(self, company=None, id_warehouse=None):
    """Compensate layer valued at an estimated price with the price of future receipts
    if any. If the estimated price is equals to the real price, no layer is created but
    the original layer is marked as compensated.

    :param company: recordset of `res.company` to limit the execution of the vacuum
    """
    self.ensure_one()
    if company is None:
        company = self.env.company
    # Kaisen: Changes start
    svls_to_vacuum_domain = [
        ('product_id', '=', self.id),
        ('remaining_qty', '<', 0),
        ('stock_move_id', '!=', False),
        ('company_id', '=', company.id),
    ]
    if id_warehouse:
        svls_to_vacuum_domain.append(("warehouse_id", "=", id_warehouse))
    svls_to_vacuum = self.env['stock.valuation.layer'].sudo().search(svls_to_vacuum_domain, order = 'create_date, id')
    # Kaisen: Changes end
    if not svls_to_vacuum:
        return

    as_svls = []

    domain = [
        ('company_id', '=', company.id),
        ('product_id', '=', self.id),
        ('remaining_qty', '>', 0),
        ('create_date', '>=', svls_to_vacuum[0].create_date),
    ]
    # Kaisen: Changes start
    if id_warehouse:
        domain.append(("warehouse_id", "=", id_warehouse))
    # Kaisen: Changes end
    all_candidates = self.env['stock.valuation.layer'].sudo().search(domain)

    for svl_to_vacuum in svls_to_vacuum:
        # We don't use search to avoid executing _flush_search and to decrease interaction with DB
        candidates = all_candidates.filtered(
            lambda r: r.create_date > svl_to_vacuum.create_date
                      or r.create_date == svl_to_vacuum.create_date
                      and r.id > svl_to_vacuum.id
        )
        if not candidates:
            break
        qty_to_take_on_candidates = abs(svl_to_vacuum.remaining_qty)
        qty_taken_on_candidates = 0
        tmp_value = 0
        for candidate in candidates:
            qty_taken_on_candidate = min(candidate.remaining_qty, qty_to_take_on_candidates)
            qty_taken_on_candidates += qty_taken_on_candidate

            candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
            new_remaining_value = candidate.remaining_value - value_taken_on_candidate

            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': new_remaining_value
            }
            candidate.write(candidate_vals)
            if not (candidate.remaining_qty > 0):
                all_candidates -= candidate

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate
            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                break

        # Get the estimated value we will correct.
        remaining_value_before_vacuum = svl_to_vacuum.unit_cost * qty_taken_on_candidates
        new_remaining_qty = svl_to_vacuum.remaining_qty + qty_taken_on_candidates
        corrected_value = remaining_value_before_vacuum - tmp_value
        svl_to_vacuum.write({
            'remaining_qty': new_remaining_qty,
        })

        # Don't create a layer or an accounting entry if the corrected value is zero.
        if svl_to_vacuum.currency_id.is_zero(corrected_value):
            continue

        corrected_value = svl_to_vacuum.currency_id.round(corrected_value)
        move = svl_to_vacuum.stock_move_id
        vals = {
            'product_id': self.id,
            'value': corrected_value,
            'unit_cost': 0,
            'quantity': 0,
            'remaining_qty': 0,
            'stock_move_id': move.id,
            'company_id': move.company_id.id,
            'description': 'Revaluation of %s (negative inventory)' % move.picking_id.name or move.name,
            'stock_valuation_layer_id': svl_to_vacuum.id,
        }
        vacuum_svl = self.env['stock.valuation.layer'].sudo().create(vals)

        if self.valuation != 'real_time':
            continue
        as_svls.append((vacuum_svl, svl_to_vacuum))

    # If some negative stock were fixed, we need to recompute the standard price.
    product = self.with_company(company.id)
    if product.cost_method == 'average' and not float_is_zero(product.quantity_svl, precision_rounding=self.uom_id.rounding):
        product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl})

    self.env['stock.valuation.layer'].browse(x[0].id for x in as_svls)._validate_accounting_entries()

    for vacuum_svl, svl_to_vacuum in as_svls:
        self._create_fifo_vacuum_anglo_saxon_expense_entry(vacuum_svl, svl_to_vacuum)

ProductProduct._run_fifo_vacuum = _run_fifo_vacuum