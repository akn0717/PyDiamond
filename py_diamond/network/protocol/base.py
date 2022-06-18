# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract base network packet protocol module"""

from __future__ import annotations

__all__ = [
    "AbstractNetworkProtocol",
    "GenericNetworkProtocolWrapper",
    "ValidationError",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from typing import Any, Generic, TypeVar

from ...system.object import Object, final


class ValidationError(Exception):
    pass


class AbstractNetworkProtocol(Object):
    @abstractmethod
    def serialize(self, packet: Any) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        raise NotImplementedError


_P = TypeVar("_P", bound=AbstractNetworkProtocol)


class GenericNetworkProtocolWrapper(Generic[_P]):
    def __init__(self, protocol: _P) -> None:
        super().__init__()
        assert isinstance(protocol, AbstractNetworkProtocol)
        self.__protocol: _P = protocol

    @property
    @final
    def protocol(self) -> _P:
        return self.__protocol
