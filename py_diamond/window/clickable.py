# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Clickable objects module"""

from __future__ import annotations

__all__ = ["Clickable"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from enum import auto, unique
from operator import truth
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar
from weakref import WeakMethod

from ..audio.sound import Sound
from ..graphics.drawable import Drawable
from ..system.enum import AutoLowerNameEnum
from ..system.object import Object
from .cursor import AbstractCursor, SystemCursor
from .display import Window
from .event import BoundEventManager, Event, MouseButtonDownEvent, MouseButtonEvent, MouseButtonUpEvent, MouseMotionEvent
from .gui import SupportsFocus
from .mouse import Mouse
from .scene import Scene


class Clickable(Object):
    @unique
    class State(AutoLowerNameEnum):
        NORMAL = auto()
        DISABLED = auto()

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="Clickable")

    __default_focus_on_hover: ClassVar[bool] = False

    def __init__(
        self,
        master: Scene | Window,
        *,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: AbstractCursor | None = None,
        disabled_cursor: AbstractCursor | None = None,
        take_focus: bool = True,
        focus_on_hover: bool | None = None,
    ) -> None:
        self.__master: Scene | Window = master
        self.__scene: Scene | None
        if isinstance(master, Scene):
            self.__scene = master
        else:
            self.__scene = None
        self.__state: Clickable.State = Clickable.State.NORMAL
        self.__hover: bool = False
        self.__active: bool = False
        self.__active_only_on_hover: bool = True
        self.__hover_sound: Sound | None = None
        self.__click_sound: dict[Clickable.State, Sound | None] = dict.fromkeys(Clickable.State)
        self.__default_hover_cursor: dict[Clickable.State, AbstractCursor] = {
            Clickable.State.NORMAL: SystemCursor.HAND,
            Clickable.State.DISABLED: SystemCursor.NO,
        }
        self.__hover_cursor: dict[Clickable.State, AbstractCursor] = self.__default_hover_cursor.copy()
        if isinstance(hover_cursor, AbstractCursor):
            self.__hover_cursor[Clickable.State.NORMAL] = hover_cursor
        if isinstance(disabled_cursor, AbstractCursor):
            self.__hover_cursor[Clickable.State.DISABLED] = disabled_cursor
        if focus_on_hover is None:
            focus_on_hover = self.__default_focus_on_hover
        self.__focus_on_hover: bool = truth(focus_on_hover)

        self.state = state
        self.hover_sound = hover_sound
        self.click_sound = click_sound
        self.disabled_sound = disabled_sound
        self.__event: BoundEventManager[Any]
        self.__event = event = BoundEventManager(self)
        event.register_to_existing_manager(master.event)
        event.bind(MouseButtonDownEvent, WeakMethod(self.__handle_click_event))
        event.bind(MouseButtonUpEvent, WeakMethod(self.__handle_click_event))
        event.bind(MouseMotionEvent, WeakMethod(self.__handle_mouse_motion))
        event.bind_mouse_position(WeakMethod(self.__handle_mouse_position))
        if isinstance(self, SupportsFocus):
            self.focus.take(take_focus)

    @abstractmethod
    def invoke(self) -> None:
        raise NotImplementedError

    def play_hover_sound(self) -> None:
        if (hover_sound := self.__hover_sound) is not None:
            hover_sound.play()

    def play_click_sound(self) -> None:
        if (click_sound := self.__click_sound[self.__state]) is not None:
            click_sound.play()

    def get_default_cursor(self) -> AbstractCursor:
        return self.__default_hover_cursor[Clickable.State.NORMAL]

    def get_default_disabled_cursor(self) -> AbstractCursor:
        return self.__default_hover_cursor[Clickable.State.DISABLED]

    def set_cursor_to_default(self) -> None:
        self.__hover_cursor[Clickable.State.NORMAL] = self.__default_hover_cursor[Clickable.State.NORMAL]

    def set_disabled_cursor_to_default(self) -> None:
        self.__hover_cursor[Clickable.State.DISABLED] = self.__default_hover_cursor[Clickable.State.DISABLED]

    def set_active_only_on_hover(self, status: bool) -> None:
        self.__active_only_on_hover = truth(status)

    def set_focus_on_hover(self, status: bool) -> None:
        self.__focus_on_hover = focus_on_hover = truth(status)
        if isinstance(self, SupportsFocus):
            if focus_on_hover and self.hover:
                self.focus.set()

    @classmethod
    def set_default_focus_on_hover(cls, status: bool) -> None:
        cls.__default_focus_on_hover = truth(status)

    @classmethod
    def get_default_focus_on_hover(cls) -> bool:
        return cls.__default_focus_on_hover

    def __handle_click_event(self, event: MouseButtonEvent) -> bool:
        if isinstance(self, Drawable) and not self.is_shown():
            self.active = self.hover = False
            return False

        valid_click: bool = truth(self._valid_mouse_button(event.button) and self._mouse_in_hitbox(event.pos))

        match event:
            case MouseButtonDownEvent() if valid_click:
                self.active = True
                self._on_click_down(event)
                return True
            case MouseButtonDownEvent():
                self._on_click_out(event)
                return False
            case MouseButtonUpEvent() if self.active:
                self.active = False
                self._on_click_up(event)
                if not valid_click:
                    return False
                if isinstance(self, SupportsFocus):
                    self.focus.set()
                self.play_click_sound()
                self._on_hover()
                if self.state != Clickable.State.DISABLED:
                    self.invoke()
                return True
            case MouseButtonUpEvent():
                self.active = False
                return False
        return False

    def __handle_mouse_motion(self, event: MouseMotionEvent) -> None:
        self._on_mouse_motion(event)

    def __handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        if isinstance(self, Drawable) and not self.is_shown():
            self.hover = False
            return
        if isinstance(self, SupportsFocus) and self.focus.get_mode() == self.focus.Mode.KEY:
            return
        self.hover = hover = self._mouse_in_hitbox(mouse_pos)
        if hover or (not self.__active_only_on_hover and self.active):
            self.__hover_cursor[self.__state].set()

    def _focus_handle_event(self, event: Event) -> bool:
        return self.event.process_event(event)

    def _focus_update(self) -> None:
        if not self.__focus_on_hover:
            return
        if (
            self.hover
            and isinstance(self, SupportsFocus)
            and not self.focus.has()
            and self.focus.get_mode() == self.focus.Mode.MOUSE
        ):
            self.focus.set()

    def _valid_mouse_button(self, button: int) -> bool:
        return button == Mouse.Button.LEFT

    @abstractmethod
    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        raise NotImplementedError

    def _on_change_state(self) -> None:
        pass

    def _on_click_down(self, event: MouseButtonDownEvent) -> None:
        pass

    def _on_click_up(self, event: MouseButtonUpEvent) -> None:
        pass

    def _on_click_out(self, event: MouseButtonDownEvent) -> None:
        pass

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        pass

    def _on_hover(self) -> None:
        pass

    def _on_leave(self) -> None:
        pass

    def _on_active_set(self) -> None:
        pass

    @property
    def master(self) -> Scene | Window:
        return self.__master

    @property
    def window(self) -> Window:
        master: Scene | Window = self.__master
        if isinstance(master, Window):
            return master
        return master.window

    @property
    def scene(self) -> Scene | None:
        return self.__scene

    @property
    def event(self: __Self) -> BoundEventManager[__Self]:
        return self.__event

    @property
    def state(self) -> str:
        return str(self.__state.value)

    @state.setter
    def state(self, state: str) -> None:
        state = Clickable.State(state)
        if state == self.__state:
            return
        self.__state = state
        if self.hover:
            self._on_hover()
            if self.active:
                self._on_active_set()
        else:
            self._on_leave()
        self._on_change_state()

    @property
    def hover(self) -> bool:
        return self.__hover

    @hover.setter
    def hover(self, status: bool) -> None:
        status = truth(status)
        if status == self.__hover:
            return
        self.__hover = status
        if status is True:
            self.play_hover_sound()
            self._on_hover()
            if self.__focus_on_hover and isinstance(self, SupportsFocus):
                self.focus.set()
            if self.active:
                self._on_active_set()
        else:
            self._on_leave()

    @property
    def active(self) -> bool:
        return truth(self.__active and (self.hover or not self.__active_only_on_hover))

    @active.setter
    def active(self, status: bool) -> None:
        status = truth(status)
        if status == self.__active:
            return
        self.__active = status
        if self.active:
            self._on_active_set()

    @property
    def hover_sound(self) -> Sound | None:
        return self.__hover_sound

    @hover_sound.setter
    def hover_sound(self, sound: Sound | None) -> None:
        if sound is not None and not isinstance(sound, Sound):
            raise TypeError(f"sound must be a '{Sound.__module__}.{Sound.__name__}' object")
        self.__hover_sound = sound

    @property
    def click_sound(self) -> Sound | None:
        return self.__click_sound[Clickable.State.NORMAL]

    @click_sound.setter
    def click_sound(self, sound: Sound | None) -> None:
        if sound is not None and not isinstance(sound, Sound):
            raise TypeError(f"sound must be a '{Sound.__module__}.{Sound.__name__}' object")
        self.__click_sound[Clickable.State.NORMAL] = sound

    @property
    def disabled_sound(self) -> Sound | None:
        return self.__click_sound[Clickable.State.DISABLED]

    @disabled_sound.setter
    def disabled_sound(self, sound: Sound | None) -> None:
        if sound is not None and not isinstance(sound, Sound):
            raise TypeError(f"sound must be a '{Sound.__module__}.{Sound.__name__}' object")
        self.__click_sound[Clickable.State.DISABLED] = sound

    @property
    def hover_cursor(self) -> AbstractCursor:
        return self.__hover_cursor[Clickable.State.NORMAL]

    @hover_cursor.setter
    def hover_cursor(self, cursor: AbstractCursor) -> None:
        self.__hover_cursor[Clickable.State.NORMAL] = cursor

    @property
    def disabled_cursor(self) -> AbstractCursor:
        return self.__hover_cursor[Clickable.State.DISABLED]

    @disabled_cursor.setter
    def disabled_cursor(self, cursor: AbstractCursor) -> None:
        self.__hover_cursor[Clickable.State.DISABLED] = cursor
