

def toML(amount, units):
    if units == 'ml':
        return amount
    if units == 'oz':
        return amount * 29.5735
    raise ValueError('unknown units: ' + units)
    
def convertUnits(fromAmount, fromUnits, toUnits):
    amount = toML(fromAmount, fromUnits)
    if toUnits == 'ml':
        return amount
    if toUnits == 'oz':
        return amount / 29.5735
    raise ValueError('unknown units: ' + toUnits)
        