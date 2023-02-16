from collections import defaultdict

from odoo.addons.stock_account.models.stock_move import StockMove as StockMoveAccount
from odoo.addons.stock.models.stock_move import StockMove
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import OrderedSet
from odoo.exceptions import UserError
from odoo import fields, _


def _create_in_svl(self, forced_quantity=None):
    """Create a `stock.valuation.layer` from `self`.

    :param forced_quantity: under some circunstances, the quantity to value is different than
        the initial demand of the move (Default value = None)
    """
    svl_vals_list = []
    for move in self:
        move = move.with_company(move.company_id)
        valued_move_lines = move._get_in_move_lines()
        valued_quantity = 0
        for valued_move_line in valued_move_lines:
            valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done,
                                                                                 move.product_id.uom_id)
        unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
        if move.product_id.cost_method == 'standard':
            unit_cost = move.product_id.standard_price
        svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
        # Kaisen: Changes start
        if move.location_dest_id.warehouse_id and move.product_id.cost_method == "fifowh":
            svl_vals.update({"warehouse_id": move.location_dest_id.warehouse_id.id})
        # Kaisen: Changes end
        svl_vals.update(move._prepare_common_svl_vals())
        if forced_quantity:
            svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
        svl_vals_list.append(svl_vals)
    return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

StockMoveAccount._create_in_svl = _create_in_svl

def _create_out_svl(self, forced_quantity=None):
    """Create a `stock.valuation.layer` from `self`.

    :param forced_quantity: under some circunstances, the quantity to value is different than
        the initial demand of the move (Default value = None)
    """
    svl_vals_list = []
    for move in self:
        move = move.with_company(move.company_id)
        valued_move_lines = move._get_out_move_lines()
        valued_quantity = 0
        for valued_move_line in valued_move_lines:
            valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done,
                                                                                 move.product_id.uom_id)
        if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
            continue
        # Kaisen: Changes start
        if move.location_id.warehouse_id and move.product_id.cost_method == "fifowh":
            warehouse_id = move.location_id.warehouse_id
        else:
            warehouse_id = None
        svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id, warehouse_id)
        # Kaisen: Changes end
        svl_vals.update(move._prepare_common_svl_vals())
        if forced_quantity:
            svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
        svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
        svl_vals_list.append(svl_vals)
    return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

StockMoveAccount._create_out_svl = _create_out_svl

def _action_done(self, cancel_backorder=False):
    # Init a dict that will group the moves by valuation type, according to `move._is_valued_type`.
    valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
    for move in self:
        if float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding):
            continue
        for valued_type in self._get_valued_types():
            if getattr(move, '_is_%s' % valued_type)():
                valued_moves[valued_type] |= move

    # AVCO application
    valued_moves['in'].product_price_update_before_done()

    res = super(StockMoveAccount, self)._action_done(cancel_backorder=cancel_backorder)

    # '_action_done' might have created an extra move to be valued
    for move in res - self:
        for valued_type in self._get_valued_types():
            if getattr(move, '_is_%s' % valued_type)():
                valued_moves[valued_type] |= move

    stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
    # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
    for valued_type in self._get_valued_types():
        todo_valued_moves = valued_moves[valued_type]
        if todo_valued_moves:
            todo_valued_moves._sanity_check_for_valuation()
            stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()

    stock_valuation_layers._validate_accounting_entries()
    stock_valuation_layers._validate_analytic_accounting_entries()

    stock_valuation_layers._check_company()

    # For every in move, run the vacuum for the linked product.
    # Kaisen: Changes start
    products_to_vacuum = {"general": self.env["product.product"], "warehouse": []}
    for move_id in valued_moves['in']:
        if move_id.product_id.cost_method == "fifowh":
            products_to_vacuum["warehouse"].append((move_id.location_dest_id.warehouse_id.id, move_id.product_id))
        else:
            products_to_vacuum["general"] |= move_id.product_id
    company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[0] or self.env.company
    for product_to_vacuum in products_to_vacuum["general"]:
        product_to_vacuum._run_fifo_vacuum(company)
    for id_warehouse, product_to_vacuum in products_to_vacuum["warehouse"]:
        product_to_vacuum._run_fifo_vacuum(company, id_warehouse)
    # Kaisen: Changes end
    return res

StockMoveAccount._action_done = _action_done

def _action_done(self, cancel_backorder=False):
    self.filtered(lambda move: move.state == 'draft')._action_confirm()  # MRP allows scrapping draft moves
    moves = self.exists().filtered(lambda x: x.state not in ('done', 'cancel'))
    moves_ids_todo = OrderedSet()

    # Cancel moves where necessary ; we should do it before creating the extra moves because
    # this operation could trigger a merge of moves.
    for move in moves:
        if move.quantity_done <= 0 and not move.is_inventory:
            if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0 or cancel_backorder:
                move._action_cancel()

    # Create extra moves where necessary
    for move in moves:
        if move.state == 'cancel' or (move.quantity_done <= 0 and not move.is_inventory):
            continue

        moves_ids_todo |= move._create_extra_move().ids

    moves_todo = self.browse(moves_ids_todo)
    moves_todo._check_company()
    # Split moves where necessary and move quants
    backorder_moves_vals = []
    for move in moves_todo:
        # To know whether we need to create a backorder or not, round to the general product's
        # decimal precision and not the product's UOM.
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
            # Need to do some kind of conversion here
            qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done, move.product_id.uom_id, rounding_method='HALF-UP')
            new_move_vals = move._split(qty_split)
            backorder_moves_vals += new_move_vals
    backorder_moves = self.env['stock.move'].create(backorder_moves_vals)
    # The backorder moves are not yet in their own picking. We do not want to check entire packs for those
    # ones as it could messed up the result_package_id of the moves being currently validated
    backorder_moves.with_context(bypass_entire_pack=True)._action_confirm(merge=False)
    if cancel_backorder:
        backorder_moves.with_context(moves_todo=moves_todo)._action_cancel()
    moves_todo.mapped('move_line_ids').sorted()._action_done()
    # Check the consistency of the result packages; there should be an unique location across
    # the contained quants.
    # Kaisen: Changes start
    for result_package in moves_todo\
            .mapped('move_line_ids.result_package_id')\
            .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1 and not p.product_packaging_id):
        # Kaisen: Changes end
        if len(result_package.quant_ids.filtered(lambda q: not float_is_zero(abs(q.quantity) + abs(q.reserved_quantity), precision_rounding=q.product_uom_id.rounding)).mapped('location_id')) > 1:
            raise UserError(
                _('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
    picking = moves_todo.mapped('picking_id')
    moves_todo.write({'state': 'done', 'date': fields.Datetime.now()})

    new_push_moves = moves_todo.filtered(lambda m: m.picking_id.immediate_transfer)._push_apply()
    if new_push_moves:
        new_push_moves._action_confirm()
    move_dests_per_company = defaultdict(lambda: self.env['stock.move'])
    for move_dest in moves_todo.move_dest_ids:
        move_dests_per_company[move_dest.company_id.id] |= move_dest
    for company_id, move_dests in move_dests_per_company.items():
        move_dests.sudo().with_company(company_id)._action_assign()

    # We don't want to create back order for scrap moves
    # Replace by a kwarg in master
    if self.env.context.get('is_scrap'):
        return moves_todo

    if picking and not cancel_backorder:
        backorder = picking._create_backorder()
        if any([m.state == 'assigned' for m in backorder.move_lines]):
            backorder._check_entire_pack()
    return moves_todo

StockMove._action_done = _action_done