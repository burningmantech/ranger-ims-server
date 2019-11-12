# -*- test-case-name: ranger-ims-server.ext.test.test_frozendict -*-
"""
Frozen dictionary
"""

from collections.abc import Mapping as MappingABC
from typing import Any, Iterator, List, Mapping

from attr import attrib, attrs


__all__ = (
    "FrozenDict"
)


@attrs(frozen=True, auto_attribs=True, kw_only=True, eq=False)
class FrozenDict(MappingABC):
    """
    Frozen dictionary.
    """

    @classmethod
    def fromMapping(cls, mapping: Mapping) -> "FrozenDict":
        """
        Create a FrozenDict from a Mapping.
        """
        return cls(map_=mapping)


    _map_: Mapping
    _hash: List[int] = attrib(init=False, factory=list)


    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._map_}>"


    def __getitem__(self, key: Any) -> Any:
        return self._map_[key]


    def __iter__(self) -> Iterator[Any]:
        return iter(self._map_)


    def __len__(self) -> int:
        return len(self._map_)


    def __contains__(self, key: Any) -> bool:
        return key in self._map_


    def __hash__(self) -> int:
        if not self._hash:
            hashValue = 0
            for key, value in self._map_.items():
                hashValue ^= hash((key, value))

            self._hash.append(hashValue)

        return self._hash[0]


    def copy(self) -> "FrozenDict":
        """
        See Mapping.copy.
        """
        return self.__class__(map_=self._map_)
