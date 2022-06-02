# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""OrderedWeakSet module"""

from __future__ import annotations

__all__ = ["OrderedWeakSet"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import TYPE_CHECKING, Any, Iterator, Sequence
from weakref import ReferenceType, WeakSet, ref

if not TYPE_CHECKING:  # Too many type errors :)
    from _weakrefset import _IterationGuard
else:
    from typing import ContextManager

    class _IterationGuard(ContextManager["_IterationGuard"]):
        def __init__(self, weakcontainer: WeakSet[Any]) -> None:
            ...

        def __enter__(self) -> _IterationGuard:
            ...

        def __exit__(self, *args: Any) -> None:
            ...


from ._orderedset import OrderedSet


class OrderedWeakSet(WeakSet, Sequence):  # type: ignore[type-arg]
    def __init__(self, data: Any = None):
        super().__init__()
        self.data: OrderedSet = OrderedSet()  # Replace underlying set by an OrderedSet instance
        self._pending_removals: list[ReferenceType[object]]  # Private attribute from WeakSet
        if data is not None:
            self.update(data)

    if TYPE_CHECKING:

        def _commit_removals(self) -> None:  # Private method from WeakSet
            ...

    def __getitem__(self, index: int | slice) -> Any | OrderedWeakSet:
        if self._pending_removals:
            self._commit_removals()
        if isinstance(index, slice):
            with _IterationGuard(self):
                return self.__class__((item for itemref in self.data[index] if (item := itemref()) is not None))  # type: ignore[operator, union-attr]
        try:
            if isinstance(index, str):  # type: ignore[unreachable]
                raise TypeError
            index = int(index)
        except TypeError:
            msg = f"indices must be integers or slices, not {type(index).__name__}"
            raise TypeError(msg) from None
        if index < 0:
            index += len(self)
            if index < 0:
                raise IndexError("index out of range")
        while (obj := self.data[index]()) is None:  # type: ignore[operator]
            index += 1
        return obj

    def __delitem__(self, index: int) -> None:
        if isinstance(index, slice):  # type: ignore[unreachable]
            raise TypeError("Slice are not accepted")
        self.discard(self[index])

    def __reversed__(self) -> Iterator[object]:
        with _IterationGuard(self):
            for itemref in reversed(self.data):
                item = itemref()
                if item is not None:
                    # Caveat: the iterator will keep a strong reference to
                    # `item` until it is resumed or closed.
                    yield item

    def count(self, value: Any) -> int:
        return 1 if value in self else 0

    def index(self, value: Any, *args: Any, **kwargs: Any) -> int:
        if self._pending_removals:
            self._commit_removals()
        return self.data.index(ref(value), *args, **kwargs)
