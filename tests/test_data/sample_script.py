#!/usr/bin/env python3
"""Sample Python script for testing file upload functionality."""

def hello(name: str = "World") -> str:
    """Say hello to someone.
    
    Args:
        name: The name of the person to greet
        
    Returns:
        A greeting message
    """
    return f"Hello, {name}!"

def add_numbers(a: int, b: int) -> int:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The sum of a and b
    """
    return a + b

def calculate_area(length: float, width: float) -> float:
    """Calculate the area of a rectangle.
    
    Args:
        length: Length of the rectangle
        width: Width of the rectangle
        
    Returns:
        The area of the rectangle
    """
    return length * width

if __name__ == "__main__":
    print(hello())
    print(f"2 + 3 = {add_numbers(2, 3)}")
    print(f"Area of 5x3 rectangle = {calculate_area(5.0, 3.0)}")
