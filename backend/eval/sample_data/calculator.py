"""A tiny sample module used to verify code indexing and retrieval."""


def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b


def fibonacci(n: int) -> int:
    """Return the n-th Fibonacci number using simple iteration."""
    prev, curr = 0, 1
    for _ in range(n):
        prev, curr = curr, prev + curr
    return prev
