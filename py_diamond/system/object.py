# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Object/ObjectMeta module"""

from __future__ import annotations

__all__ = ["Object", "ObjectMeta", "final", "override"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta
from functools import cached_property
from itertools import chain
from operator import truth
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Sequence, TypeVar, overload

from typing_extensions import final

# from .utils import isabstractmethod

_T = TypeVar("_T")


def _iter_keeping_former(iterable: Iterable[_T], *, reverse: bool = True) -> Iterator[tuple[_T, Sequence[_T]]]:
    l: tuple[_T, ...] = ()
    for elem in iterable:
        yield elem, l
        if reverse:
            l = (elem,) + l
        else:
            l = l + (elem,)
    del l


class ObjectMeta(ABCMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="ObjectMeta")

    __finalmethods__: frozenset[str]

    def __new__(
        metacls: type[__Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> __Self:
        # Verify final bases
        final_bases: list[type]
        if final_bases := list(filter(lambda base: getattr(base, "__final__", False), bases)):
            raise TypeError(
                f"{name!r}: Base classes marked as final class: {', '.join(base.__qualname__ for base in final_bases)}"
            )

        # Verify conflict for final methods in multiple inheritance
        bases_final_methods_dict: dict[type, list[str]] = {base: list(getattr(base, "__finalmethods__", ())) for base in bases}
        bases_final_methods_set: list[str] = list(chain.from_iterable(bases_final_methods_dict.values()))

        # conflict_final_methods: dict[str, list[type]] = {
        #     method: bases_list
        #     for method in bases_final_methods_set
        #     if len(
        #         (
        #             bases_list := [
        #                 base
        #                 for actual_base, previous_bases in _iter_keeping_former(bases)
        #                 if method in bases_final_methods_dict.get(actual_base, [])
        #                 for base in chain((actual_base,), previous_bases)
        #                 if base is actual_base
        #                 or (
        #                     hasattr(base, method)
        #                     and not isabstractmethod(getattr(base, method))
        #                     and (getattr(actual_base, method) is not getattr(base, method))
        #                 )
        #             ]
        #         )
        #     )
        #     > 1
        # }

        # if conflict_final_methods:
        #     conflict_message = ", ".join(
        #         f"{method} in {tuple(b.__qualname__ for b in bases)}" for method, bases in conflict_final_methods.items()
        #     )
        #     raise TypeError(f"{name!r}: Final methods conflict between base classes: {conflict_message}")

        # Verify final override
        if final_methods_overriden := list(filter(bases_final_methods_set.__contains__, namespace)):
            raise TypeError(f"{name!r}: These attributes would override final methods: {', '.join(final_methods_overriden)}")

        # Verify override() decorator usage
        method_that_must_override: frozenset[str] = frozenset(
            attr_name for attr_name, attr_obj in namespace.items() if ObjectMeta.__must_override(attr_obj)
        )
        if method_that_will_not_override := list(
            filter(lambda name: not any(hasattr(b, name) for b in bases), method_that_must_override)
        ):
            raise TypeError(f"{name!r}: These methods will not override base method: {', '.join(method_that_will_not_override)}")

        # Retrieve final methods from namespace
        cls_final_methods: frozenset[str] = frozenset(
            chain(
                bases_final_methods_set,
                (attr_name for attr_name, attr_obj in namespace.items() if ObjectMeta.__is_final_override(attr_obj)),
            )
        )

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)
        cls.__finalmethods__ = frozenset(
            filter(lambda attr_name: ObjectMeta.__is_final_override(getattr(cls, attr_name, None)), cls_final_methods)
        )

        return cls

    @staticmethod
    def __must_override(obj: Any) -> bool:
        return truth(ObjectMeta.__check_attr(obj, "__mustoverride__"))

    @staticmethod
    def __is_final_override(obj: Any) -> bool:
        return truth(ObjectMeta.__check_attr(obj, "__final__"))

    @staticmethod
    def __check_attr(obj: Any, attr: str) -> bool:
        if getattr(obj, attr, False):
            return True
        match obj:
            case property(fget=fget, fset=fset, fdel=fdel):
                return any(getattr(func, attr, False) for func in (fget, fset, fdel))
            case classmethod(__func__=func) | staticmethod(__func__=func) | cached_property(func=func):
                return True if getattr(func, attr, False) else False
            case _:
                return False


class Object(metaclass=ObjectMeta):
    __slots__ = ()

    def __del__(self) -> None:
        pass


@overload
def override(f: _T, /) -> _T:
    ...


@overload
def override(*, final: bool = False) -> Callable[[_T], _T]:
    ...


def override(f: Any = ..., /, *, final: bool = False) -> Any:
    final = bool(final)

    def apply_markers(f: Any) -> None:
        setattr(f, "__mustoverride__", True)
        setattr(f, "__final__", final)

    def decorator(f: Any) -> Any:
        match f:
            case property(fget=fget, fset=fset, fdel=fdel):
                for func in (fget, fset, fdel):
                    if callable(func):
                        apply_markers(func)
            case classmethod(__func__=func) | staticmethod(__func__=func) | cached_property(func=func):
                apply_markers(f)
                apply_markers(func)
            case type():
                raise TypeError("override() must not decorate classes")
            case _ if not callable(f) and not hasattr(f, "__get__"):
                raise TypeError("override() must only decorate functions and descriptors")
            case _:
                apply_markers(f)
        return f

    return decorator if f is Ellipsis else decorator(f)
