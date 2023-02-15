def migrate(cr, version):
    cr.execute("""
        UPDATE stock_valuation_layer SET warehouse_id = tab.warehouse FROM (
        SELECT wh.id AS warehouse, svl.id AS svl_id FROM stock_valuation_layer svl 
        JOIN stock_move sm ON sm.id = svl.stock_move_id
        JOIN stock_location sl ON sl.id = sm.location_dest_id 
        JOIN stock_warehouse wh ON wh.id = sl.warehouse_id
        ) AS tab
        WHERE stock_valuation_layer.id = tab.svl_id;    
    """)

    cr.execute("""
            UPDATE ir_property SET value_text = 'fifowh' FROM (
            SELECT ip.id AS property_id, ip.value_text  FROM ir_model_fields imf
            JOIN ir_property ip ON ip.fields_id = imf.id
            WHERE imf.name = 'property_cost_method' AND ip.value_text = 'fifo'
            ) AS tab
            WHERE ir_property.id = tab.property_id;
    """)
