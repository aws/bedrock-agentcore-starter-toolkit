from typing import Any, Dict, Union

class MemorySummary:
    """ A class representing a memory summary """
    def __init__(self, memory_summary: Dict[str, Any]):
        self._memory_summary = memory_summary
        
    def __getattr__(self, name: str) -> Any:
        """Provides direct access to memory summary fields as attributes"""
        return self._memory_summary.get(name)

    def __repr__(self):
        return self._memory_summary.__repr__()
        
    def __getitem__(self, key: str) -> Any:
        """Provides dictionary-style access to memory summary fields"""
        return self._memory_summary[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Provides dictionary-style access to memory summary fields with a default value"""
        return self._memory_summary.get(key, default)

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking if key exists"""
        return key in self._memory_summary

    def keys(self):
        """Return keys from the underlying dictionary"""
        return self._memory_summary.keys()

    def values(self):
        """Return values from the underlying dictionary"""
        return self._memory_summary.values()

    def items(self):
        """Return items from the underlying dictionary"""
        return self._memory_summary.items()
