from flask import current_app


def pricing_service(line_items):
    subtotal = 0.0
    item_cnt = 0
    for line_item in line_items:
        unit_price = line_item.unit_price
        qty = line_item.quantity

        item_cnt += qty
        subtotal += unit_price*qty

    tax_rate = current_app.config['TAX_RATE']
    flat_fee_price = current_app.config['FLAT_FEE']
    cost_fee_rate = current_app.config['COST_FEE']

    subtotal = round(subtotal, 2)
    taxes = round(subtotal * tax_rate, 2)

    flat_fee = flat_fee_price * item_cnt
    cost_fee = cost_fee_rate * subtotal
    fees = round(flat_fee + cost_fee, 2)

    total = subtotal + taxes + fees

    return total, subtotal, taxes, fees