# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window events module"""

from __future__ import annotations

__all__ = [
    "BuiltinEvent",
    "Event",
    "EventFactory",
    "EventFactoryError",
    "EventManager",
    "EventMeta",
    "JoyAxisMotionEvent",
    "JoyBallMotionEvent",
    "JoyButtonDownEvent",
    "JoyButtonEvent",
    "JoyButtonUpEvent",
    "JoyDeviceAddedEvent",
    "JoyDeviceRemovedEvent",
    "JoyHatMotionEvent",
    "KeyDownEvent",
    "KeyEvent",
    "KeyUpEvent",
    "MouseButtonDownEvent",
    "MouseButtonEvent",
    "MouseButtonUpEvent",
    "MouseEvent",
    "MouseMotionEvent",
    "MouseWheelEvent",
    "MusicEndEvent",
    "ScreenshotEvent",
    "TextEditingEvent",
    "TextEvent",
    "TextInputEvent",
    "UnknownEventTypeError",
    "UserEvent",
    "WindowEnterEvent",
    "WindowExposedEvent",
    "WindowFocusGainedEvent",
    "WindowFocusLostEvent",
    "WindowHiddenEvent",
    "WindowLeaveEvent",
    "WindowMaximizedEvent",
    "WindowMinimizedEvent",
    "WindowMovedEvent",
    "WindowResizedEvent",
    "WindowRestoredEvent",
    "WindowShownEvent",
    "WindowSizeChangedEvent",
    "WindowTakeFocusEvent",
]

import weakref
from abc import abstractmethod
from collections import defaultdict
from dataclasses import Field, asdict as dataclass_asdict, dataclass, field, fields
from enum import IntEnum, unique
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Final,
    Generic,
    Literal as L,
    Mapping,
    Sequence,
    SupportsInt,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

import pygame.constants as _pg_constants
from pygame.event import Event as _PygameEvent, custom_type as _pg_event_custom_type, event_name as _pg_event_name

from ..system.collections import ChainMapProxy, OrderedSet
from ..system.namespace import ClassNamespaceMeta
from ..system.object import Object, ObjectMeta, final
from ..system.utils.abc import isabstractclass
from ..system.utils.weakref import weakref_unwrap
from .keyboard import Keyboard
from .mouse import Mouse

if TYPE_CHECKING:
    from _typeshed import Self

    from ..audio.music import Music
    from ..graphics.surface import Surface

_T = TypeVar("_T")

_PYGAME_EVENT_TYPE: dict[SupportsInt, type[Event]] = {}
_ASSOCIATIONS: dict[type[Event], SupportsInt] = {}


class EventMeta(ObjectMeta):
    __associations: Final[dict[type[Event], SupportsInt]] = _ASSOCIATIONS
    __type: Final[dict[SupportsInt, type[Event]]] = _PYGAME_EVENT_TYPE

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="EventMeta")

    def __new__(
        mcs: type[__Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        model: bool = False,
        **kwargs: Any,
    ) -> __Self:
        try:
            Event
        except NameError:
            pass
        else:
            if not any(issubclass(b, Event) for b in bases):
                raise TypeError(f"{name!r} must inherit from Event")
            if concrete_events := [b for b in bases if issubclass(b, Event) and not b.is_model()]:
                concrete_events_qualnames = ", ".join(b.__qualname__ for b in concrete_events)
                raise TypeError(f"{name!r}: Events which are not model classes caught: {concrete_events_qualnames}")
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        setattr(cls, "_model_", bool(model))
        if not cls.is_model() and not issubclass(cls, BuiltinEvent):
            cls = final(cls)
            event_type: SupportsInt = _pg_event_custom_type()
            if event_type in EventFactory.pygame_type:  # Should not happen
                event_cls = EventFactory.pygame_type[event_type]
                raise SystemError(f"Event with type {_pg_event_name(int(event_type))!r} already exists: {event_cls}")
            event_cls = cast(type[Event], cls)
            mcs.__associations[event_cls] = event_type
            mcs.__type[event_type] = event_cls
        return cls

    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        if cls.is_model():
            raise TypeError("Event models are not instanciable")
        return super().__call__(*args, **kwds)

    def __setattr__(cls, __name: str, __value: Any) -> None:
        if __name in {"_model_"} and __name in vars(cls):
            raise AttributeError("Read-only attribute")
        return super().__setattr__(__name, __value)

    def __delattr__(cls, __name: str) -> None:
        if __name in {"_model_"}:
            raise AttributeError("Read-only attribute")
        return super().__delattr__(__name)

    def is_model(cls) -> bool:
        return bool(isabstractclass(cls) or getattr(cls, "_model_"))


_BUILTIN_PYGAME_EVENT_TYPE: dict[SupportsInt, type[Event]] = {}
_BUILTIN_ASSOCIATIONS: dict[type[Event], SupportsInt] = {}


@final
class _BuiltinEventMeta(EventMeta):
    __associations: Final[dict[type[Event], SupportsInt]] = _BUILTIN_ASSOCIATIONS  # type: ignore[misc]
    __type: Final[dict[SupportsInt, type[Event]]] = _BUILTIN_PYGAME_EVENT_TYPE  # type: ignore[misc]

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> _BuiltinEventMeta:
        try:
            BuiltinEvent
        except NameError:
            pass
        else:
            if all(event_type in mcs.__type for event_type in BuiltinEvent.Type):
                raise TypeError("Trying to create custom event from BuiltinEvent class")
            assert len(bases) == 1 and issubclass(bases[0], BuiltinEvent)
            cls = super().__new__(mcs, name, bases, namespace, **kwargs)
            assert not cls.is_model()
            event_type: Any = getattr(cls, "type")
            if isinstance(event_type, Field):
                event_type = event_type.default
            assert isinstance(event_type, BuiltinEvent.Type), f"Got {event_type!r}"
            assert event_type not in mcs.__type, f"{event_type!r} event already taken"
            event_cls = cast(type[BuiltinEvent], cls)
            mcs.__associations[event_cls] = event_type
            mcs.__type[event_type] = event_cls
            return cls
        return super().__new__(mcs, name, bases, namespace, **kwargs)

    def __setattr__(cls, __name: str, __value: Any) -> None:
        if __name in {"Type"}:
            raise AttributeError("Read-only attribute")
        return super().__setattr__(__name, __value)

    def __delattr__(cls, __name: str) -> None:
        if __name in {"Type"}:
            raise AttributeError("Read-only attribute")
        return super().__delattr__(__name)


class Event(Object, metaclass=EventMeta):
    __slots__ = ()

    @classmethod
    @abstractmethod
    def from_dict(cls: type[Self], event_dict: dict[str, Any]) -> Self:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


# TODO (3.11) dataclass_transform (PEP-681)
@dataclass(kw_only=True)
class BuiltinEvent(Event, metaclass=_BuiltinEventMeta, model=True):
    @unique
    class Type(IntEnum):
        # pygame's built-in events
        KEYDOWN = _pg_constants.KEYDOWN
        KEYUP = _pg_constants.KEYUP
        MOUSEMOTION = _pg_constants.MOUSEMOTION
        MOUSEBUTTONUP = _pg_constants.MOUSEBUTTONUP
        MOUSEBUTTONDOWN = _pg_constants.MOUSEBUTTONDOWN
        MOUSEWHEEL = _pg_constants.MOUSEWHEEL
        JOYAXISMOTION = _pg_constants.JOYAXISMOTION
        JOYBALLMOTION = _pg_constants.JOYBALLMOTION
        JOYHATMOTION = _pg_constants.JOYHATMOTION
        JOYBUTTONUP = _pg_constants.JOYBUTTONUP
        JOYBUTTONDOWN = _pg_constants.JOYBUTTONDOWN
        JOYDEVICEADDED = _pg_constants.JOYDEVICEADDED
        JOYDEVICEREMOVED = _pg_constants.JOYDEVICEREMOVED
        USEREVENT = _pg_constants.USEREVENT
        TEXTEDITING = _pg_constants.TEXTEDITING
        TEXTINPUT = _pg_constants.TEXTINPUT
        WINDOWSHOWN = _pg_constants.WINDOWSHOWN
        WINDOWHIDDEN = _pg_constants.WINDOWHIDDEN
        WINDOWEXPOSED = _pg_constants.WINDOWEXPOSED
        WINDOWMOVED = _pg_constants.WINDOWMOVED
        WINDOWRESIZED = _pg_constants.WINDOWRESIZED
        WINDOWSIZECHANGED = _pg_constants.WINDOWSIZECHANGED
        WINDOWMINIMIZED = _pg_constants.WINDOWMINIMIZED
        WINDOWMAXIMIZED = _pg_constants.WINDOWMAXIMIZED
        WINDOWRESTORED = _pg_constants.WINDOWRESTORED
        WINDOWENTER = _pg_constants.WINDOWENTER
        WINDOWLEAVE = _pg_constants.WINDOWLEAVE
        WINDOWFOCUSGAINED = _pg_constants.WINDOWFOCUSGAINED
        WINDOWFOCUSLOST = _pg_constants.WINDOWFOCUSLOST
        WINDOWTAKEFOCUS = _pg_constants.WINDOWTAKEFOCUS

        # PyDiamond's events
        MUSICEND = _pg_event_custom_type()
        SCREENSHOT = _pg_event_custom_type()

        def __repr__(self) -> str:
            return f"<{self.name} ({self.real_name}): {self.value}>"

        @property
        def real_name(self) -> str:
            return _pg_event_name(self)

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name in {"type"}:
            raise AttributeError("Read-only attribute")
        return super().__setattr__(__name, __value)

    def __delattr__(self, __name: str) -> None:
        if __name in {"type"}:
            raise AttributeError("Read-only attribute")
        return super().__delattr__(__name)

    @classmethod
    def from_dict(cls: type[Self], event_dict: dict[str, Any]) -> Self:
        event_fields: Sequence[str] = tuple(f.name for f in fields(cls))
        kwargs: dict[str, Any] = {k: event_dict[k] for k in filter(event_fields.__contains__, event_dict)}
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return dataclass_asdict(self)

    type: ClassVar[BuiltinEvent.Type] = field(init=False)


@final
@dataclass(kw_only=True)
class KeyDownEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.KEYDOWN]] = field(default=BuiltinEvent.Type.KEYDOWN, init=False)
    key: int
    mod: int
    unicode: str
    scancode: int


@final
@dataclass(kw_only=True)
class KeyUpEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.KEYUP]] = field(default=BuiltinEvent.Type.KEYUP, init=False)
    key: int
    mod: int


KeyEvent: TypeAlias = KeyDownEvent | KeyUpEvent


@final
@dataclass(kw_only=True)
class MouseButtonDownEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MOUSEBUTTONDOWN]] = field(default=BuiltinEvent.Type.MOUSEBUTTONDOWN, init=False)
    pos: tuple[int, int]
    button: int


@final
@dataclass(kw_only=True)
class MouseButtonUpEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MOUSEBUTTONUP]] = field(default=BuiltinEvent.Type.MOUSEBUTTONUP, init=False)
    pos: tuple[int, int]
    button: int


MouseButtonEvent: TypeAlias = MouseButtonDownEvent | MouseButtonUpEvent


@final
@dataclass(kw_only=True)
class MouseMotionEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MOUSEMOTION]] = field(default=BuiltinEvent.Type.MOUSEMOTION, init=False)
    pos: tuple[int, int]
    rel: tuple[int, int]
    buttons: tuple[bool, bool, bool]


@final
@dataclass(kw_only=True)
class MouseWheelEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MOUSEWHEEL]] = field(default=BuiltinEvent.Type.MOUSEWHEEL, init=False)
    flipped: bool
    x: int
    y: int


MouseEvent: TypeAlias = MouseButtonEvent | MouseWheelEvent | MouseMotionEvent


@final
@dataclass(kw_only=True)
class JoyAxisMotionEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYAXISMOTION]] = field(default=BuiltinEvent.Type.JOYAXISMOTION, init=False)
    instance_id: int
    axis: int
    value: float


@final
@dataclass(kw_only=True)
class JoyBallMotionEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYBALLMOTION]] = field(default=BuiltinEvent.Type.JOYBALLMOTION, init=False)
    instance_id: int
    ball: int
    rel: float


@final
@dataclass(kw_only=True)
class JoyHatMotionEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYHATMOTION]] = field(default=BuiltinEvent.Type.JOYHATMOTION, init=False)
    instance_id: int
    hat: int
    value: tuple[int, int]


@final
@dataclass(kw_only=True)
class JoyButtonDownEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYBUTTONDOWN]] = field(default=BuiltinEvent.Type.JOYBUTTONDOWN, init=False)
    instance_id: int
    button: int


@final
@dataclass(kw_only=True)
class JoyButtonUpEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYBUTTONUP]] = field(default=BuiltinEvent.Type.JOYBUTTONUP, init=False)
    instance_id: int
    button: int


JoyButtonEvent: TypeAlias = JoyButtonDownEvent | JoyButtonUpEvent


@final
@dataclass(kw_only=True)
class JoyDeviceAddedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYDEVICEADDED]] = field(default=BuiltinEvent.Type.JOYDEVICEADDED, init=False)
    device_index: int


@final
@dataclass(kw_only=True)
class JoyDeviceRemovedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYDEVICEREMOVED]] = field(default=BuiltinEvent.Type.JOYDEVICEREMOVED, init=False)
    instance_id: int


@final
@dataclass(kw_only=True)
class TextEditingEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.TEXTEDITING]] = field(default=BuiltinEvent.Type.TEXTEDITING, init=False)
    text: str
    start: int
    length: int


@final
@dataclass(kw_only=True)
class TextInputEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.TEXTINPUT]] = field(default=BuiltinEvent.Type.TEXTINPUT, init=False)
    text: str


TextEvent: TypeAlias = TextEditingEvent | TextInputEvent


@final
@dataclass(init=False)
class UserEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.USEREVENT]] = field(default=BuiltinEvent.Type.USEREVENT, init=False)
    code: int = 0

    def __init__(self, *, code: int = 0, **kwargs: Any) -> None:
        self.code = code
        self.__dict__.update(kwargs)

    if TYPE_CHECKING:

        def __getattr__(self, name: str, /) -> Any:  # Indicate dynamic attribute
            ...

    @classmethod
    def from_dict(cls, event_dict: dict[str, Any]) -> UserEvent:
        return cls(**event_dict)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@final
@dataclass(kw_only=True)
class WindowShownEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWSHOWN]] = field(default=BuiltinEvent.Type.WINDOWSHOWN, init=False)


@final
@dataclass(kw_only=True)
class WindowHiddenEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWHIDDEN]] = field(default=BuiltinEvent.Type.WINDOWHIDDEN, init=False)


@final
@dataclass(kw_only=True)
class WindowExposedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWEXPOSED]] = field(default=BuiltinEvent.Type.WINDOWEXPOSED, init=False)


@final
@dataclass(kw_only=True)
class WindowMovedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWMOVED]] = field(default=BuiltinEvent.Type.WINDOWMOVED, init=False)
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowResizedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWRESIZED]] = field(default=BuiltinEvent.Type.WINDOWRESIZED, init=False)
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowSizeChangedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWSIZECHANGED]] = field(default=BuiltinEvent.Type.WINDOWSIZECHANGED, init=False)
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowMinimizedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWMINIMIZED]] = field(default=BuiltinEvent.Type.WINDOWMINIMIZED, init=False)


@final
@dataclass(kw_only=True)
class WindowMaximizedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWMAXIMIZED]] = field(default=BuiltinEvent.Type.WINDOWMAXIMIZED, init=False)


@final
@dataclass(kw_only=True)
class WindowRestoredEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWRESTORED]] = field(default=BuiltinEvent.Type.WINDOWRESTORED, init=False)


@final
@dataclass(kw_only=True)
class WindowEnterEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWENTER]] = field(default=BuiltinEvent.Type.WINDOWENTER, init=False)


@final
@dataclass(kw_only=True)
class WindowLeaveEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWLEAVE]] = field(default=BuiltinEvent.Type.WINDOWLEAVE, init=False)


@final
@dataclass(kw_only=True)
class WindowFocusGainedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWFOCUSGAINED]] = field(default=BuiltinEvent.Type.WINDOWFOCUSGAINED, init=False)


@final
@dataclass(kw_only=True)
class WindowFocusLostEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWFOCUSLOST]] = field(default=BuiltinEvent.Type.WINDOWFOCUSLOST, init=False)


@final
@dataclass(kw_only=True)
class WindowTakeFocusEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWTAKEFOCUS]] = field(default=BuiltinEvent.Type.WINDOWTAKEFOCUS, init=False)


@final
@dataclass(kw_only=True)
class MusicEndEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MUSICEND]] = field(default=BuiltinEvent.Type.MUSICEND, init=False)
    finished: Music
    next: Music | None


@final
@dataclass(kw_only=True)
class ScreenshotEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.SCREENSHOT]] = field(default=BuiltinEvent.Type.SCREENSHOT, init=False)
    filepath: str
    screen: Surface

    def to_dict(self) -> dict[str, Any]:
        # dataclasses.as_dict() calls copy.deepcopy() but a Surface is not pickleable
        return {"filepath": self.filepath, "screen": self.screen}


def _check_event_types_association() -> None:
    if unbound_types := set(filter(lambda e: e not in _BUILTIN_PYGAME_EVENT_TYPE, BuiltinEvent.Type)):
        raise SystemError(
            f"The following events do not have an associated BuiltinEvent class: {', '.join(e.name for e in unbound_types)}"
        )


_check_event_types_association()

del _check_event_types_association


class EventFactoryError(Exception):
    pass


class UnknownEventTypeError(EventFactoryError):
    pass


class EventFactory(metaclass=ClassNamespaceMeta, frozen=True):
    associations: Final[Mapping[type[Event], SupportsInt]] = ChainMapProxy(_BUILTIN_ASSOCIATIONS, _ASSOCIATIONS)
    pygame_type: Final[Mapping[SupportsInt, type[Event]]] = ChainMapProxy(_BUILTIN_PYGAME_EVENT_TYPE, _PYGAME_EVENT_TYPE)

    NUMEVENTS: Final[int] = _pg_constants.NUMEVENTS

    @staticmethod
    def from_pygame_event(event: _PygameEvent, *, handle_user_events: bool = True) -> Event:
        try:
            event_cls: type[Event] = EventFactory.pygame_type[event.type]
        except KeyError as exc:
            if handle_user_events and BuiltinEvent.Type.USEREVENT < event.type < EventFactory.NUMEVENTS:
                return UserEvent.from_dict(event.__dict__ | {"code": event.type})
            raise UnknownEventTypeError(f"Unknown event with type {_pg_event_name(event.type)!r}") from exc
        return event_cls.from_dict(event.__dict__)

    @staticmethod
    def make_pygame_event(event: Event) -> _PygameEvent:
        assert not event.__class__.is_model()  # Should not happen but who knows...?
        event_dict = event.to_dict()
        event_dict.pop("type", None)
        event_type = EventFactory.associations[event.__class__]
        return _PygameEvent(int(event_type), event_dict)


_EventCallback: TypeAlias = Callable[[Event], bool | None]
_TE = TypeVar("_TE", bound=Event)

_MousePositionCallback: TypeAlias = Callable[[tuple[float, float]], Any]


class EventManager:

    __slots__ = (
        "__event_handler_dict",
        "__key_pressed_handler_dict",
        "__key_released_handler_dict",
        "__mouse_button_pressed_handler_dict",
        "__mouse_button_released_handler_dict",
        "__mouse_pos_handler_list",
        "__other_manager_list",
        "__priority_callback",
        "__priority_manager",
        "__weakref__",
    )

    def __init__(self) -> None:
        self.__event_handler_dict: dict[type[Event], OrderedSet[_EventCallback]] = dict()
        self.__key_pressed_handler_dict: dict[Keyboard.Key, Callable[[KeyDownEvent], Any]] = dict()
        self.__key_released_handler_dict: dict[Keyboard.Key, Callable[[KeyUpEvent], Any]] = dict()
        self.__mouse_button_pressed_handler_dict: dict[Mouse.Button, Callable[[MouseButtonDownEvent], Any]] = dict()
        self.__mouse_button_released_handler_dict: dict[Mouse.Button, Callable[[MouseButtonUpEvent], Any]] = dict()
        self.__mouse_pos_handler_list: OrderedSet[_MousePositionCallback] = OrderedSet()
        self.__other_manager_list: OrderedSet[EventManager] = OrderedSet()
        self.__priority_callback: dict[type[Event], _EventCallback] = dict()
        self.__priority_manager: dict[type[Event], EventManager] = dict()

    def __del__(self) -> None:
        self.unbind_all()

    @overload
    @staticmethod
    def __bind(
        handler_dict: dict[type[Event], OrderedSet[_EventCallback]],
        key: type[Event],
        callback: Callable[[_TE], bool | None],
    ) -> None:
        ...

    @overload
    @staticmethod
    def __bind(handler_dict: dict[_T, OrderedSet[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        ...

    @staticmethod
    def __bind(handler_dict: dict[_T, OrderedSet[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        try:
            handler_list: OrderedSet[_EventCallback] = handler_dict[key]
        except KeyError:
            handler_dict[key] = handler_list = OrderedSet()
        handler_list.add(cast(_EventCallback, callback))

    @overload
    @staticmethod
    def __unbind(
        handler_dict: dict[type[Event], OrderedSet[_EventCallback]],
        key: type[Event],
        callback: Callable[[_TE], bool | None],
    ) -> None:
        ...

    @overload
    @staticmethod
    def __unbind(handler_dict: dict[_T, OrderedSet[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        ...

    @staticmethod
    def __unbind(handler_dict: dict[_T, OrderedSet[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        handler_dict[key].remove(cast(_EventCallback, callback))

    @staticmethod
    def __bind_single(handler_dict: dict[_T, Callable[[_TE], Any]], key: _T, callback: Callable[[_TE], Any]) -> None:
        if key in handler_dict:
            if handler_dict[key] is not callback:
                raise ValueError(f"Conflict when setting {key!r}: a callback is already registered")
            return
        handler_dict[key] = callback

    @staticmethod
    def __unbind_single(handler_dict: dict[_T, Callable[[_TE], Any]], key: _T) -> None:
        del handler_dict[key]

    def bind(self, event_cls: type[_TE], callback: Callable[[_TE], bool | None]) -> None:
        if not issubclass(event_cls, Event):
            raise TypeError("Invalid argument")
        if event_cls.is_model():
            raise TypeError("Cannot assign events to event models")
        EventManager.__bind(self.__event_handler_dict, event_cls, callback)

    def unbind(self, event_cls: type[_TE], callback_to_remove: Callable[[_TE], bool | None]) -> None:
        if not issubclass(event_cls, Event):
            raise TypeError("Invalid argument")
        if event_cls.is_model():
            raise TypeError("Cannot assign events to event models")
        EventManager.__unbind(self.__event_handler_dict, event_cls, callback_to_remove)
        for event_type in tuple(
            event_type
            for event_type, priority_callback in self.__priority_callback.items()
            if priority_callback is callback_to_remove
        ):
            self.__priority_callback.pop(event_type)

    def unbind_all(self) -> None:
        self.__event_handler_dict.clear()
        self.__key_pressed_handler_dict.clear()
        self.__key_released_handler_dict.clear()
        self.__mouse_button_pressed_handler_dict.clear()
        self.__mouse_button_released_handler_dict.clear()
        self.__mouse_pos_handler_list.clear()
        self.__priority_callback.clear()
        self.__priority_manager.clear()

    def bind_key(self, key: Keyboard.Key, callback: Callable[[KeyEvent], Any]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    def bind_key_press(self, key: Keyboard.Key, callback: Callable[[KeyDownEvent], Any]) -> None:
        EventManager.__bind_single(self.__key_pressed_handler_dict, Keyboard.Key(key), callback)

    def bind_key_release(self, key: Keyboard.Key, callback: Callable[[KeyUpEvent], Any]) -> None:
        EventManager.__bind_single(self.__key_released_handler_dict, Keyboard.Key(key), callback)

    def unbind_key(self, key: Keyboard.Key) -> None:
        self.unbind_key_press(key)
        self.unbind_key_release(key)

    def unbind_key_press(self, key: Keyboard.Key) -> None:
        EventManager.__unbind_single(self.__key_pressed_handler_dict, Keyboard.Key(key))

    def unbind_key_release(self, key: Keyboard.Key) -> None:
        EventManager.__unbind_single(self.__key_released_handler_dict, Keyboard.Key(key))

    def bind_mouse_button(self, button: Mouse.Button, callback: Callable[[MouseButtonEvent], Any]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    def bind_mouse_button_press(self, button: Mouse.Button, callback: Callable[[MouseButtonDownEvent], Any]) -> None:
        EventManager.__bind_single(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback)

    def bind_mouse_button_release(self, button: Mouse.Button, callback: Callable[[MouseButtonUpEvent], Any]) -> None:
        EventManager.__bind_single(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback)

    def unbind_mouse_button(self, button: Mouse.Button) -> None:
        self.unbind_mouse_button_press(button)
        self.unbind_mouse_button_release(button)

    def unbind_mouse_button_press(self, button: Mouse.Button) -> None:
        EventManager.__unbind_single(self.__mouse_button_pressed_handler_dict, Mouse.Button(button))

    def unbind_mouse_button_release(self, button: Mouse.Button) -> None:
        EventManager.__unbind_single(self.__mouse_button_released_handler_dict, Mouse.Button(button))

    def bind_mouse_position(self, callback: _MousePositionCallback) -> None:
        mouse_pos_handler_list: OrderedSet[_MousePositionCallback] = self.__mouse_pos_handler_list
        mouse_pos_handler_list.add(callback)

    def unbind_mouse_position(self, callback_to_remove: _MousePositionCallback) -> None:
        mouse_pos_handler_list: OrderedSet[_MousePositionCallback] = self.__mouse_pos_handler_list
        mouse_pos_handler_list.remove(callback_to_remove)

    def bind_event_manager(self, manager: EventManager) -> None:
        if manager is self:
            raise ValueError("Trying to add yourself")
        other_manager_list: OrderedSet[EventManager] = self.__other_manager_list
        other_manager_list.add(manager)

    def unbind_event_manager(self, manager: EventManager) -> None:
        other_manager_list: OrderedSet[EventManager] = self.__other_manager_list
        other_manager_list.remove(manager)
        for event_type in tuple(
            event_type for event_type, priority_manager in self.__priority_manager.items() if priority_manager is manager
        ):
            self.__priority_manager.pop(event_type)

    def process_event(self, event: Event) -> bool:
        event_type: type[Event] = type(event)

        priority_manager: EventManager | None = self.__priority_manager.get(event_type)
        if priority_manager is not None:
            if priority_manager.process_event(event):
                return True
            del self.__priority_manager[event_type]

        for manager in self.__other_manager_list:
            if manager is not priority_manager and manager.process_event(event):
                self.__priority_manager[event_type] = manager
                return True

        # mypy does not handle isinstance() with TypeAlias of UnionTypes yet
        if isinstance(event, KeyEvent):  # type: ignore[arg-type,misc]
            if self.__handle_key_event(event):  # type: ignore[arg-type]
                return True
        elif isinstance(event, MouseButtonEvent):  # type: ignore[arg-type,misc]
            if self.__handle_mouse_event(event):  # type: ignore[arg-type]
                return True

        priority_callback: _EventCallback | None = self.__priority_callback.get(event_type)
        if priority_callback is not None:
            if priority_callback(event):
                return True
            del self.__priority_callback[event_type]

        event_dict: dict[type[Event], OrderedSet[_EventCallback]] = self.__event_handler_dict
        for callback in event_dict.get(event_type, ()):
            if callback is not priority_callback and callback(event):
                self.__priority_callback[event_type] = callback
                return True
        return False

    def handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        for manager in self.__other_manager_list:
            manager.handle_mouse_position(mouse_pos)
        for callback in self.__mouse_pos_handler_list:
            callback(mouse_pos)

    def __handle_key_event(self, event: KeyEvent) -> bool:
        try:
            key = Keyboard.Key(event.key)
        except ValueError:
            return False
        match event:
            case KeyDownEvent() if key in self.__key_pressed_handler_dict:
                self.__key_pressed_handler_dict[key](event)
                return True
            case KeyUpEvent() if key in self.__key_released_handler_dict:
                self.__key_released_handler_dict[key](event)
                return True
        return False

    def __handle_mouse_event(self, event: MouseButtonEvent) -> bool:
        try:
            mouse_button = Mouse.Button(event.button)
        except ValueError:
            return False
        match event:
            case MouseButtonDownEvent() if mouse_button in self.__mouse_button_pressed_handler_dict:
                self.__mouse_button_pressed_handler_dict[mouse_button](event)
                return True
            case MouseButtonUpEvent() if mouse_button in self.__mouse_button_released_handler_dict:
                self.__mouse_button_released_handler_dict[mouse_button](event)
                return True
        return False


_U = TypeVar("_U")
_V = TypeVar("_V")

_CallbackRegistry: TypeAlias = weakref.WeakKeyDictionary[Callable[..., Any], Callable[..., Any]]


class BoundEventManager(Generic[_T]):
    __slots__ = (
        "__ref",
        "__manager",
        "__any_callbacks",
        "__key_press_callbacks",
        "__key_release_callbacks",
        "__mouse_press_callbacks",
        "__mouse_release_callbacks",
        "__mouse_position_callbacks",
        "__weakref__",
    )

    def __init__(self, obj: _T) -> None:
        def unbind_all(_: Any, /, selfref: weakref.ReferenceType[BoundEventManager[_T]] = weakref.ref(self)) -> None:
            self = selfref()
            if self is not None:
                self.unbind_all()

        self.__ref: weakref.ReferenceType[_T] = weakref.ref(obj, unbind_all)
        self.__manager: EventManager = EventManager()
        self.__any_callbacks: defaultdict[Any, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__key_press_callbacks: defaultdict[Keyboard.Key, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__key_release_callbacks: defaultdict[Keyboard.Key, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__mouse_press_callbacks: defaultdict[Mouse.Button, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__mouse_release_callbacks: defaultdict[Mouse.Button, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__mouse_position_callbacks: _CallbackRegistry = weakref.WeakKeyDictionary()

    def __del__(self) -> None:
        self.unbind_all()

    def register_to_existing_manager(self, manager: EventManager | BoundEventManager[Any]) -> None:
        return manager.bind_event_manager(self.__manager)

    def unregister_from_existing_manager(self, manager: EventManager | BoundEventManager[Any]) -> None:
        return manager.unbind_event_manager(self.__manager)

    def __bind(
        self,
        manager_bind: Callable[[_U, Callable[[Event], _V]], None],
        key: _U,
        callback: weakref.WeakMethod[Callable[[_TE], _V]] | Callable[[_T, _TE], _V],
        callback_register: defaultdict[_U, _CallbackRegistry],
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):
            callback = self._get_method_func_from_weak_method(callback)

        method_callback = cast(Callable[[_T, Event], _V], callback)

        if method_callback in callback_register[key]:
            return

        def event_callback(event: Event, /, selfref: weakref.ReferenceType[_T] = self.__ref) -> Any:
            self = selfref()
            if self is None:
                return None
            return method_callback(self, event)

        manager_bind(key, event_callback)
        callback_register[key][method_callback] = event_callback

    @overload
    def bind(self, event_cls: type[_TE], callback: weakref.WeakMethod[Callable[[_TE], bool | None]]) -> None:
        ...

    @overload
    def bind(self, event_cls: type[_TE], callback: Callable[[_T, _TE], bool | None]) -> None:
        ...

    def bind(
        self,
        event_cls: type[_TE],
        callback: weakref.WeakMethod[Callable[[_TE], bool | None]] | Callable[[_T, _TE], bool | None],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind,
            key=event_cls,
            callback=callback,
            callback_register=self.__any_callbacks,
        )

    @overload
    def unbind(self, event_cls: type[_TE], callback_to_remove: weakref.WeakMethod[Callable[[_TE], bool | None]]) -> None:
        ...

    @overload
    def unbind(self, event_cls: type[_TE], callback_to_remove: Callable[[_T, _TE], bool | None]) -> None:
        ...

    def unbind(
        self,
        event_cls: type[_TE],
        callback_to_remove: weakref.WeakMethod[Callable[[_TE], bool | None]] | Callable[[_T, _TE], bool | None],
    ) -> None:
        if isinstance(callback_to_remove, weakref.WeakMethod):
            callback_to_remove = self._get_method_func_from_weak_method(callback_to_remove)
        event_callback = self.__any_callbacks[event_cls].pop(callback_to_remove)
        return self.__manager.unbind(event_cls, event_callback)

    def unbind_all(self) -> None:
        self.__manager.unbind_all()
        self.__any_callbacks.clear()
        self.__key_press_callbacks.clear()
        self.__key_release_callbacks.clear()
        self.__mouse_press_callbacks.clear()
        self.__mouse_release_callbacks.clear()
        self.__mouse_position_callbacks.clear()

    @overload
    def bind_key(self, key: Keyboard.Key, callback: weakref.WeakMethod[Callable[[KeyEvent], Any]]) -> None:
        ...

    @overload
    def bind_key(self, key: Keyboard.Key, callback: Callable[[_T, KeyEvent], Any]) -> None:
        ...

    def bind_key(self, key: Keyboard.Key, callback: Callable[..., Any]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    @overload
    def bind_key_press(self, key: Keyboard.Key, callback: weakref.WeakMethod[Callable[[KeyDownEvent], Any]]) -> None:
        ...

    @overload
    def bind_key_press(self, key: Keyboard.Key, callback: Callable[[_T, KeyDownEvent], Any]) -> None:
        ...

    def bind_key_press(
        self,
        key: Keyboard.Key,
        callback: weakref.WeakMethod[Callable[[KeyDownEvent], Any]] | Callable[[_T, KeyDownEvent], Any],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_key_press,
            key=key,
            callback=callback,
            callback_register=self.__key_press_callbacks,
        )

    @overload
    def bind_key_release(self, key: Keyboard.Key, callback: weakref.WeakMethod[Callable[[KeyUpEvent], Any]]) -> None:
        ...

    @overload
    def bind_key_release(self, key: Keyboard.Key, callback: Callable[[_T, KeyUpEvent], Any]) -> None:
        ...

    def bind_key_release(
        self,
        key: Keyboard.Key,
        callback: weakref.WeakMethod[Callable[[KeyUpEvent], Any]] | Callable[[_T, KeyUpEvent], Any],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_key_release,
            key=key,
            callback=callback,
            callback_register=self.__key_release_callbacks,
        )

    def unbind_key(self, key: Keyboard.Key) -> None:
        self.unbind_key_press(key)
        self.unbind_key_release(key)

    def unbind_key_press(self, key: Keyboard.Key) -> None:
        self.__manager.unbind_key_press(key)
        self.__key_press_callbacks[key].clear()

    def unbind_key_release(self, key: Keyboard.Key) -> None:
        self.__manager.unbind_key_release(key)
        self.__key_release_callbacks[key].clear()

    @overload
    def bind_mouse_button(self, button: Mouse.Button, callback: weakref.WeakMethod[Callable[[MouseButtonEvent], Any]]) -> None:
        ...

    @overload
    def bind_mouse_button(self, button: Mouse.Button, callback: Callable[[_T, MouseButtonEvent], Any]) -> None:
        ...

    def bind_mouse_button(self, button: Mouse.Button, callback: Callable[..., Any]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    @overload
    def bind_mouse_button_press(
        self, button: Mouse.Button, callback: weakref.WeakMethod[Callable[[MouseButtonDownEvent], Any]]
    ) -> None:
        ...

    @overload
    def bind_mouse_button_press(self, button: Mouse.Button, callback: Callable[[_T, MouseButtonDownEvent], Any]) -> None:
        ...

    def bind_mouse_button_press(
        self,
        button: Mouse.Button,
        callback: weakref.WeakMethod[Callable[[MouseButtonDownEvent], Any]] | Callable[[_T, MouseButtonDownEvent], Any],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_mouse_button_press,
            key=button,
            callback=callback,
            callback_register=self.__mouse_press_callbacks,
        )

    @overload
    def bind_mouse_button_release(
        self, button: Mouse.Button, callback: weakref.WeakMethod[Callable[[MouseButtonUpEvent], Any]]
    ) -> None:
        ...

    @overload
    def bind_mouse_button_release(self, button: Mouse.Button, callback: Callable[[_T, MouseButtonUpEvent], Any]) -> None:
        ...

    def bind_mouse_button_release(
        self,
        button: Mouse.Button,
        callback: weakref.WeakMethod[Callable[[MouseButtonUpEvent], Any]] | Callable[[_T, MouseButtonUpEvent], Any],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_mouse_button_release,
            key=button,
            callback=callback,
            callback_register=self.__mouse_release_callbacks,
        )

    def unbind_mouse_button(self, button: Mouse.Button) -> None:
        self.unbind_mouse_button_press(button)
        self.unbind_mouse_button_release(button)

    def unbind_mouse_button_press(self, button: Mouse.Button) -> None:
        self.__manager.unbind_mouse_button_press(button)
        self.__mouse_press_callbacks[button].clear()

    def unbind_mouse_button_release(self, button: Mouse.Button) -> None:
        self.__manager.unbind_mouse_button_release(button)
        self.__mouse_release_callbacks[button].clear()

    @overload
    def bind_mouse_position(self, callback: weakref.WeakMethod[Callable[[tuple[float, float]], Any]]) -> None:
        ...

    @overload
    def bind_mouse_position(self, callback: Callable[[_T, tuple[float, float]], Any]) -> None:
        ...

    def bind_mouse_position(
        self, callback: weakref.WeakMethod[Callable[[tuple[float, float]], Any]] | Callable[[_T, tuple[float, float]], Any]
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):
            callback = self._get_method_func_from_weak_method(callback)

        method_callback = cast(Callable[[_T, tuple[float, float]], Any], callback)

        if method_callback in self.__mouse_position_callbacks:
            return

        def mouse_position_callback(mouse_pos: tuple[float, float], /, selfref: weakref.ReferenceType[_T] = self.__ref) -> Any:
            self = selfref()
            if self is None:
                return None
            return method_callback(self, mouse_pos)

        self.__manager.bind_mouse_position(mouse_position_callback)
        self.__mouse_position_callbacks[method_callback] = mouse_position_callback

    @overload
    def unbind_mouse_position(self, callback_to_remove: weakref.WeakMethod[Callable[[tuple[float, float]], Any]]) -> None:
        ...

    @overload
    def unbind_mouse_position(self, callback_to_remove: Callable[[_T, tuple[float, float]], Any]) -> None:
        ...

    def unbind_mouse_position(
        self,
        callback_to_remove: weakref.WeakMethod[Callable[[tuple[float, float]], Any]] | Callable[[_T, tuple[float, float]], Any],
    ) -> None:
        if isinstance(callback_to_remove, weakref.WeakMethod):
            callback_to_remove = self._get_method_func_from_weak_method(callback_to_remove)
        mouse_position_callback = self.__mouse_position_callbacks.pop(callback_to_remove)
        return self.__manager.unbind_mouse_position(mouse_position_callback)

    def bind_event_manager(self, manager: EventManager | BoundEventManager[Any]) -> None:
        if isinstance(manager, BoundEventManager):
            manager = manager.__manager
        return self.__manager.bind_event_manager(manager)

    def unbind_event_manager(self, manager: EventManager | BoundEventManager[Any]) -> None:
        if isinstance(manager, BoundEventManager):
            manager = manager.__manager
        return self.__manager.unbind_event_manager(manager)

    def process_event(self, event: Event) -> bool:
        return self.__manager.process_event(event)

    def handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        return self.__manager.handle_mouse_position(mouse_pos)

    def _get_method_func_from_weak_method(self, weak_method: weakref.WeakMethod[Any]) -> Callable[..., Any]:
        method = weak_method()
        if method is None:
            raise ReferenceError("Dead reference")
        if not hasattr(method, "__self__") or not hasattr(method, "__func__"):
            raise TypeError("Not a method-like object")
        if method.__self__ is not (obj := self.__self__):
            raise ValueError(f"{method.__self__!r} is not {obj!r}")
        callback: Callable[..., Any] = method.__func__
        del obj, method
        return callback

    @property
    def __self__(self) -> _T:
        return weakref_unwrap(self.__ref)


del _pg_constants, _BuiltinEventMeta
del _ASSOCIATIONS, _PYGAME_EVENT_TYPE, _BUILTIN_ASSOCIATIONS, _BUILTIN_PYGAME_EVENT_TYPE
