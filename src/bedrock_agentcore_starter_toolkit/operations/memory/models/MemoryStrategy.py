from typing import Any, Dict

class MemoryStrategy:
    """ A class representing a memory strategy """
    def __init__(self, memory_strategy: Dict[str, Any]):
        self._memory_strategy = memory_strategy
        
    def __getattr__(self, name: str) -> Any:
        """Provides direct access to memory strategy fields as attributes"""
        return self._memory_strategy.get(name)

    def __repr__(self):
        return self._memory_strategy.__repr__()
        
    def __getitem__(self, key: str) -> Any:
        """Provides dictionary-style access to memory strategy fields"""
        return self._memory_strategy[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Provides dictionary-style access to memory strategy fields with a default value"""
        return self._memory_strategy.get(key, default)

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking if key exists"""
        return key in self._memory_strategy

    def keys(self):
        """Return keys from the underlying dictionary"""
        return self._memory_strategy.keys()

    def values(self):
        """Return values from the underlying dictionary"""
        return self._memory_strategy.values()

    def items(self):
        """Return items from the underlying dictionary"""
        return self._memory_strategy.items()