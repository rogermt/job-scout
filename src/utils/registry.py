from typing import Dict, Callable, TypeVar, Any

T = TypeVar("T")


class Registry:
    def __init__(self):
        self._registry: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str):
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            self._registry[name] = func
            return func

        return decorator

    def get(self, name: str) -> Callable[..., Any]:
        return self._registry[name]

    def __contains__(self, name: str) -> bool:
        return name in self._registry


# Global instance (module-level, not singleton)
registry = Registry()
