from typing import TypeVar

T = TypeVar("T")


def require(value: T | None) -> T:
    """
    Ensures a state attribute is not None.
    
    Args:
        value: The attribute value (possibly None).
    
    Returns:
        The value, guaranteed to be non-None.
    
    Raises:
        NullStateAttributeError: If the value is None.
    """
    if value is None:
        raise ValueError('Expected value to not be None.')
    return value
