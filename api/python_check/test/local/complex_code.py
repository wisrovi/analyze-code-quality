def complex_function(n):
    if n < 0:
        return "negative"
    elif n == 0:
        return "zero"
    elif n == 1:
        return "one"
    elif n == 2:
        return "two"
    elif n == 3:
        return "three"
    elif n == 4:
        return "four"
    elif n == 5:
        return "five"
    else:
        return "other"

def another_complex_function(x, y, z):
    result = 0
    if x > 0:
        if y > 0:
            if z > 0:
                result = x + y + z
            else:
                result = x + y
        else:
            if z > 0:
                result = x + z
            else:
                result = x
    else:
        if y > 0:
            if z > 0:
                result = y + z
            else:
                result = y
        else:
            if z > 0:
                result = z
            else:
                result = 0
    return result