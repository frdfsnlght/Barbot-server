

def toML(amount, units):
    if units == 'ml':
        return amount
    if units == 'oz':
        return amount * 29.5735
    raise ValueError('unknown units: ' + units)
    
   