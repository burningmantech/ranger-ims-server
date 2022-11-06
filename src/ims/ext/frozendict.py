# -*- test-case-name: ranger-ims-server.ext.test.test_frozendict -*-
"""
Frozen dictionary
"""

from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Mapping as MappingABC
from typing import Any, TypeVar

from attrs import field, frozen


__all__ = "FrozenDict"


_Key = TypeVar("_Key")
_Value = TypeVar("_Value")


@frozen(kw_only=True, eq=False)
class FrozenDict(MappingABC[_Key, _Value]):
    """
    Frozen dictionary.
    """

    @classmethod
    def fromMapping(
        cls, mapping: Mapping[_Key, _Value]
    ) -> "FrozenDict[_Key, _Value]":
        """
        Create a FrozenDict from a Mapping.
        """
        return cls(map_=mapping)

    _map_: Mapping[_Key, _Value]
    _hash: list[int] = field(init=False, factory=list)

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

    def copy(self) -> "FrozenDict[_Key, _Value]":
        """
        See Mapping.copy.
        """
        return self.__class__(map_=self._map_)
