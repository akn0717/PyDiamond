# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network abstract base socket module"""

from __future__ import annotations

__all__ = [
    "AbstractSocket",
    "AbstractTCPClientSocket",
    "AbstractTCPServerSocket",
    "AbstractTCPSocket",
    "AbstractUDPClientSocket",
    "AbstractUDPServerSocket",
    "AbstractUDPSocket",
    "IPv4SocketAddress",
    "IPv6SocketAddress",
    "ReceivedDatagram",
    "SocketMeta",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


from abc import abstractmethod
from typing import TYPE_CHECKING, Any, NamedTuple, TypeAlias, TypeVar

from ...system.non_copyable import NonCopyableMeta
from ...system.object import Object, ObjectMeta
from .constants import AddressFamily, ShutdownFlag


class IPv4SocketAddress(NamedTuple):
    host: str
    port: int


class IPv6SocketAddress(NamedTuple):
    host: str
    port: int
    flowinfo: int = 0
    scope_id: int = 0


SocketAddress: TypeAlias = IPv4SocketAddress | IPv6SocketAddress


class SocketMeta(NonCopyableMeta, ObjectMeta):
    pass


class AbstractSocket(Object, metaclass=SocketMeta):
    __slots__ = ()

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AbstractSocket")

    def __repr__(self) -> str:
        sock_family: AddressFamily = self.family
        if not self.is_open():
            return f"<{type(self).__name__} family={sock_family} closed>"
        sock_fd: int = self.fileno()
        laddr: tuple[Any, ...] = tuple(self.getsockname())
        return f"<{type(self).__name__} fd={sock_fd}, family={sock_family}, laddr={laddr}>"

    def __str__(self) -> str:
        return self.__repr__()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
        super().__del__()

    def __enter__(self: __Self) -> __Self:
        if not self.is_open():
            raise RuntimeError("Closed socket")
        return self

    def __exit__(self, *args: Any) -> None:
        if self.is_open():
            try:
                self.close()
            except Exception:

                from sys import stderr
                from traceback import print_exc

                print(f"Exception ignored in {AbstractSocket.__exit__}", file=stderr)
                print_exc()

    @abstractmethod
    def is_open(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def getsockname(self) -> SocketAddress:
        raise NotImplementedError

    @abstractmethod
    def getblocking(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def setblocking(self, flag: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def fileno(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def family(self) -> AddressFamily:
        raise NotImplementedError


class AbstractTCPSocket(AbstractSocket):
    __slots__ = ()

    @abstractmethod
    def shutdown(self, how: ShutdownFlag) -> None:
        raise NotImplementedError


class AbstractTCPServerSocket(AbstractTCPSocket):
    __slots__ = ()

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AbstractTCPServerSocket")

    @classmethod
    @abstractmethod
    def bind(
        cls: type[__Self],
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = ...,
        backlog: int | None = ...,
        dualstack_ipv6: bool = ...,
    ) -> __Self:
        raise NotImplementedError

    @abstractmethod
    def accept(self) -> tuple[AbstractTCPClientSocket, SocketAddress]:
        raise NotImplementedError

    @abstractmethod
    def listen(self, backlog: int) -> None:
        raise NotImplementedError


class AbstractTCPClientSocket(AbstractTCPSocket):
    __slots__ = ()

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AbstractTCPClientSocket")

    @classmethod
    @abstractmethod
    def connect(
        cls: type[__Self],
        address: tuple[str, int],
        *,
        timeout: float | None = ...,
        family: int | None = ...,
    ) -> __Self:
        raise NotImplementedError

    def __repr__(self) -> str:
        sock_family: AddressFamily = self.family
        if not self.is_open():
            return f"<{type(self).__name__} family={sock_family} closed>"
        sock_fd: int = self.fileno()
        laddr: tuple[Any, ...] = tuple(self.getsockname())
        raddr: tuple[Any, ...] | None = self.getpeername()
        if raddr is not None:
            raddr = tuple(raddr)
            return f"<{type(self).__name__} fd={sock_fd}, family={sock_family}, laddr={laddr}, raddr={raddr}>"
        return f"<{type(self).__name__} fd={sock_fd}, family={sock_family}, laddr={laddr}>"

    @abstractmethod
    def recv(self, bufsize: int, flags: int = ...) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def send(self, data: bytes, flags: int = ...) -> int:
        raise NotImplementedError

    @abstractmethod
    def getpeername(self) -> SocketAddress | None:
        raise NotImplementedError

    def is_connected(self) -> bool:
        return self.is_open() and self.getpeername() is not None

    @abstractmethod
    def reconnect(self, timeout: float | None = ...) -> None:
        raise NotImplementedError

    def try_reconnect(self, timeout: float | None = None) -> bool:
        try:
            self.reconnect(timeout)
        except OSError:
            pass
        return self.is_connected()


class ReceivedDatagram(NamedTuple):
    body: bytes
    sender: SocketAddress


class AbstractUDPSocket(AbstractSocket):
    __slots__ = ()

    @abstractmethod
    def recvfrom(self, flags: int = ...) -> ReceivedDatagram:
        raise NotImplementedError

    @abstractmethod
    def sendto(self, data: bytes, address: SocketAddress, flags: int = ...) -> int:
        raise NotImplementedError


class AbstractUDPServerSocket(AbstractUDPSocket):
    __slots__ = ()

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AbstractUDPServerSocket")

    @classmethod
    @abstractmethod
    def bind(
        cls: type[__Self],
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = ...,
    ) -> __Self:
        raise NotImplementedError


class AbstractUDPClientSocket(AbstractUDPSocket):
    __slots__ = ()

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AbstractUDPClientSocket")

    @classmethod
    @abstractmethod
    def create(cls: type[__Self], family: int = ...) -> __Self:
        raise NotImplementedError
