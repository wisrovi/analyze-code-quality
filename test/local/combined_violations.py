def complex_function(data, options=None):
    result = []
    temp = []
    
    if options is None:
        options = {}
    
    for item in data:
        if item.get('type') == 'A':
            if options.get('process_a', True):
                if item.get('value') > 0:
                    temp.append(item['value'] * 2)
                elif item.get('value') < 0:
                    temp.append(item['value'] * -1)
                else:
                    temp.append(0)
        elif item.get('type') == 'B':
            if options.get('process_b', True):
                if item.get('status') == 'active':
                    temp.append(item['value'] + 10)
                elif item.get('status') == 'inactive':
                    temp.append(item['value'] - 5)
                else:
                    temp.append(item['value'])
        else:
            if options.get('process_other', False):
                temp.append(item.get('value', 0))
    
    for val in temp:
        if val > 100:
            result.append(val * 0.9)
        elif val < 0:
            result.append(abs(val))
        else:
            result.append(val)
    
    return sorted(result, reverse=True)