#!/usr/bin/env python3
"""
Good code example that passes all quality checks.

This module demonstrates proper Python coding practices including:
- Type hints
- Docstrings
- Proper error handling
- Clean code structure
"""

from typing import Any, Dict, List


def calculate_average(numbers: List[float]) -> float:
    """
    Calculate the average of a list of numbers.
    
    Args:
        numbers: List of numeric values
        
    Returns:
        The arithmetic mean of the input numbers
        
    Raises:
        ValueError: If the input list is empty
    """
    if not numbers:
        raise ValueError("Cannot calculate average of empty list")
    
    return sum(numbers) / len(numbers)


def process_data(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input data and return processed results.
    
    Args:
        input_dict: Input dictionary with various data types
        
    Returns:
        Processed dictionary with normalized values
    """
    result = {}
    
    for field, value in input_dict.items():
        if isinstance(value, str):
            result[field] = value.strip().lower()
        elif isinstance(value, (int, float)):
            result[field] = float(value)
        else:
            result[field] = str(value)
    
    return result


def main() -> None:
    """Main function demonstrating usage of the module."""
    # Example usage
    numbers = [1.0, 2.5, 3.7, 4.2]
    avg = calculate_average(numbers)
    print(f"Average: {avg:.2f}")
    
    data = {"label": "  TEST  ", "value": 42, "active": True}
    processed = process_data(data)
    print(f"Processed: {processed}")


if __name__ == "__main__":
    main()