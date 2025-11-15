from typing import List, Dict

def add_numbers(x: int, y: int) -> int:
    return x + y

def process_string(text: str) -> str:
    return text.upper()

# Type errors that mypy will catch
def problematic_function():
    # Error: incompatible types
    result = add_numbers("hello", 123)  # str passed to int parameter
    
    # Error: wrong return type
    return "not an int"  # should return int

# More type errors
def more_errors(data: List[str]) -> Dict[str, int]:
    # Error: accessing list with wrong type
    numbers: List[int] = ["1", "2", "3"]  # strings in int list
    
    # Error: incompatible assignment
    text: str = 123  # int assigned to str variable
    
    # Error: wrong dictionary value type
    return {"count": "not a number"}  # str instead of int

# Call the functions to trigger errors
bad_result = problematic_function()
more_data = more_errors(["a", "b", "c"])