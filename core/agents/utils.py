from typing import TypeVar, Any, Type, cast, List

T = TypeVar('T')

def items_of_type(items: List[Any], t: Type[T]) -> List[T]:
    return [x for x in items if isinstance(x, t)]

def cast_items(items: List[Any], t: Type[T]) -> List[T]:
    # Only keep instances of t, then cast to satisfy the type checker
    return [cast(T, x) for x in items if isinstance(x, t)]