# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Any, Callable, Dict, Iterator, List, NoReturn, Optional, SupportsInt, Tuple, Union, overload
from enum import IntEnum

import pygame
import pygame.display
import pygame.event
import pygame.mixer

from pygame.surface import Surface
from pygame.rect import Rect
from pygame.time import Clock as PygameClock
from pygame.color import Color

from .drawable import Drawable
from .text import Text
from .colors import BLACK, WHITE
from .scene import Scene, SceneAlias
from .clock import Clock
from .surface import create_surface

EventType = SupportsInt
ColorInput = Union[Color, str, List[int], Tuple[int, int, int], Tuple[int, int, int, int]]


class WindowError(pygame.error):
    pass


class _SceneManager:
    def __init__(self, window: Window) -> None:
        self.__stack: List[Scene] = []
        self.__aliases: Dict[SceneAlias, Scene] = {}
        self.__window: Window = window

    def __iter__(self) -> Iterator[Scene]:
        return self.from_top_to_bottom()

    def __len__(self) -> int:
        return len(self.__stack)

    def __contains__(self, scene: Union[Scene, SceneAlias]) -> bool:
        if isinstance(scene, Scene):
            if scene.window is not self.__window:
                return False
            return scene in self.__stack
        return scene in self.__aliases

    def from_top_to_bottom(self) -> Iterator[Scene]:
        return iter(self.__stack)

    def from_bottom_to_top(self) -> Iterator[Scene]:
        return iter(reversed(self.__stack))

    def empty(self) -> bool:
        return not self.__stack

    def get(self, alias: SceneAlias) -> Scene:
        return self.__aliases[alias]

    def top(self) -> Optional[Scene]:
        return self.__stack[0] if self.__stack else None

    def index(self, scene: Union[Scene, SceneAlias]) -> int:
        if isinstance(scene, Scene):
            return self.__stack.index(scene)
        return self.__stack.index(self.get(scene))

    def clear(self, until: Optional[Union[Scene, SceneAlias]] = None) -> None:
        if until is None:
            self.__stack.clear()
            self.__aliases.clear()
            return
        if not isinstance(until, Scene):
            until = self.get(until)
        if until not in self:
            raise WindowError(f"{type(until).__name__} not stacked")
        while self.__stack[0] is not until:
            self.remove(self.__stack[0])

    def remove(self, scene: Union[Scene, SceneAlias]) -> None:
        alias: Optional[SceneAlias] = None
        if not isinstance(scene, Scene):
            alias = scene
            scene = self.get(alias)
        if scene.window is not self.__window:
            raise WindowError("Trying to remove a scene bound to an another window")
        try:
            self.__stack.remove(scene)
        except ValueError:
            pass
        finally:
            if alias is None:
                alias = self.__get_alias(scene)
            if alias is not None:
                self.__aliases.pop(alias)

    def push(self, scene: Union[Scene, SceneAlias], alias: Optional[SceneAlias] = None) -> None:
        if not isinstance(scene, Scene):
            alias = scene
            scene = self.get(scene)
        if scene.window is not self.__window:
            raise WindowError("Trying to push a scene bound to an another window")
        if alias is None:
            alias = self.__get_alias(scene)
        self.remove(scene)
        if any(type(stacked_scene) is type(scene) for stacked_scene in self):
            raise TypeError("A scene with the same type is stacked")
        self.__stack.insert(0, scene)
        if alias is not None:
            self.__set_alias(scene, alias)

    def __get_alias(self, scene: Scene) -> Optional[SceneAlias]:
        for alias, in_scene in self.__aliases.items():
            if in_scene is scene:
                return alias
        return None

    def __set_alias(self, scene: Scene, alias: SceneAlias) -> None:
        if alias in self.__aliases:
            raise ValueError(f"A scene uses this alias: {repr(alias)}")
        self.__aliases[alias] = scene


class WindowCallback:
    def __init__(
        self,
        master: Union[Window, Scene],
        wait_time: float,
        callback: Callable[..., None],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        self.__master: Window
        self.__scene: Optional[Scene]
        if isinstance(master, Scene):
            self.__master = master.window
            self.__scene = master
        else:
            self.__master = master
            self.__scene = None

        self.__wait_time: float = wait_time
        self.__callback: Callable[..., None] = callback
        self.__args: Tuple[Any, ...] = args
        self.__kwargs: Dict[str, Any] = kwargs
        self.__clock = Clock(start=True)

    def __call__(self) -> None:
        if self.scene is not None and not self.scene.looping():
            return
        if self.__clock.elapsed_time(self.__wait_time, restart=False):
            self.__callback(*self.__args, **self.__kwargs)
            self.kill()

    def kill(self) -> None:
        self.__master.remove_window_callback(self)

    @property
    def scene(self) -> Optional[Scene]:
        return self.__scene


class WindowCallbackList(List[WindowCallback]):
    def process(self) -> None:
        if not self:
            return
        for callback in tuple(self):
            callback()


class _WindowTransition(IntEnum):
    SHOW = 1
    HIDE = 2


class Window:
    class Exit(BaseException):
        pass

    Config = Dict[str, Any]

    MIXER_FREQUENCY = 44100
    MIXER_SIZE = -16
    MIXER_CHANNELS = 2
    MIXER_BUFFER = 512
    DEFAULT_TITLE = "pygame window"
    DEFAULT_FRAMERATE = 60

    __main_window: bool = True

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        if not Window.__main_window:
            raise WindowError("Cannot have multiple open windows")
        Window.__main_window = False
        return super().__new__(cls)

    def __init__(self, title: Optional[str] = None, size: Tuple[int, int] = (0, 0), fullscreen: bool = False) -> None:
        if not pygame.get_init():
            pygame.mixer.pre_init(Window.MIXER_FREQUENCY, Window.MIXER_SIZE, Window.MIXER_CHANNELS, Window.MIXER_BUFFER)
            status: Tuple[int, int] = pygame.init()
            if status[1] > 0:
                raise WindowError(f"Error on pygame initialization: {status[1]} modules failed to load")
        elif pygame.mixer.get_init() is not None:
            pygame.mixer.quit()
            pygame.mixer.init(Window.MIXER_FREQUENCY, Window.MIXER_SIZE, Window.MIXER_CHANNELS, Window.MIXER_BUFFER)
            if pygame.mixer.get_init() is None:
                raise WindowError("Error on pygame initialization: pygame.mixer module failed to load")

        self.set_title(title)

        screen: Optional[Surface] = pygame.display.get_surface()
        if screen is None:
            if size[0] <= 0 or size[1] <= 0:
                size = (0, 0)
            flags: int = 0
            if fullscreen:
                flags |= pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
            screen = pygame.display.set_mode(size, flags=flags, depth=32)
        self.__surface: Surface = create_surface(screen.get_size())
        self.clear_all_events()

        self.__rect: Rect = self.__surface.get_rect()
        self.__main_clock: PygameClock = PygameClock()
        self.__framerate_update_clock: Clock = Clock(start=True)
        self.__framerate: int = 0
        self.__loop: bool = True
        self.__scenes: _SceneManager = _SceneManager(self)
        self.__callback_after: WindowCallbackList = WindowCallbackList()
        self.__callback_after_scenes: Dict[Scene, WindowCallbackList] = dict()
        self.__text_framerate: Text = Text(color=WHITE)
        self.__text_framerate.hide()
        self.__text_framerate.midtop = (self.centerx, self.top + 10)
        self.__actual_scene: Optional[Scene] = None
        self.__transition: _WindowTransition = _WindowTransition.SHOW

    def __del__(self) -> None:
        Window.__main_window = True
        print("Quit pygame")
        pygame.quit()

    def __contains__(self, scene: Union[Scene, SceneAlias]) -> bool:
        return scene in self.__scenes

    def set_title(self, title: Optional[str]) -> None:
        pygame.display.set_caption(title or Window.DEFAULT_TITLE)

    def iconify(self) -> bool:
        return bool(pygame.display.iconify())

    def mainloop(self) -> None:
        try:
            self.__loop = True
            while self.__loop:
                self.handle_events()
                self.update()
                self.draw_and_refresh()
        except Window.Exit:
            pass
        finally:
            self.__loop = False
            self.__callback_after.clear()
            self.__callback_after_scenes.clear()

    def close(self) -> NoReturn:
        self.__loop = False
        raise Window.Exit

    def is_open(self) -> bool:
        return self.__loop

    def clear(self, color: ColorInput = BLACK) -> None:
        self.__surface.fill(color)

    def refresh(self) -> None:
        screen: Surface = pygame.display.get_surface()
        screen.fill(BLACK)
        if self.text_framerate.is_shown():
            if not self.text_framerate.message or self.__framerate_update_clock.elapsed_time(200):
                self.text_framerate.message = f"{round(self.framerate)} FPS"
            self.text_framerate.draw_onto(self.__surface)
        screen.blit(self.__surface, (0, 0))
        pygame.display.flip()

        self.__framerate = Window.DEFAULT_FRAMERATE
        actual_scene: Optional[Scene] = self.__scenes.top()
        for scene in self.__scenes.from_bottom_to_top():
            f: int = scene.get_required_framerate()
            if f > 0:
                self.__framerate = f
                break
        if actual_scene is not None and actual_scene.require_busy_loop():
            self.__main_clock.tick_busy_loop(self.__framerate)
        else:
            self.__main_clock.tick(self.__framerate)

    def draw_screen(self) -> None:
        scene: Optional[Scene] = self.__update_actual_scene()
        if scene:
            if scene.master:
                scene.master.draw()
            else:
                self.clear(scene.background_color)
            scene.draw()

    def update(self) -> None:
        scene: Optional[Scene] = self.__update_actual_scene()
        if scene:
            scene.update()

    def draw_and_refresh(self) -> None:
        self.draw_screen()
        self.refresh()

    def draw(self, target: Drawable) -> None:
        try:
            target.draw_onto(self.__surface)
        except pygame.error:
            pass

    def handle_events(self, only_close_event: bool = False) -> None:
        self.__callback_after.process()
        actual_scene: Optional[Scene] = self.__update_actual_scene()
        if actual_scene and actual_scene in self.__callback_after_scenes:
            self.__callback_after_scenes[actual_scene].process()
        for scene in self.__callback_after_scenes:
            if scene not in self.__scenes:
                self.__callback_after_scenes.pop(scene)

        if only_close_event:
            self.__handle_only_close_event()
        else:
            self.__handle_all_events()

    def __handle_only_close_event(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()

    def __handle_all_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()

    def allow_only_event(self, *event_types: EventType) -> None:
        pygame.event.set_allowed(event_types)

    def allow_all_events(self) -> None:
        pygame.event.set_allowed(None)

    def clear_all_events(self) -> None:
        pygame.event.clear()

    def block_only_event(self, *event_types: EventType) -> None:
        pygame.event.set_blocked(event_types)

    def after(
        self, milliseconds: float, callback: Callable[..., None], scene: Optional[Scene] = None, *args: Any, **kwargs: Any
    ) -> WindowCallback:
        window_callback: WindowCallback
        if scene is not None:
            if scene.window is not self:
                raise WindowError("Assigning a task for a scene from an another window.")
            window_callback = WindowCallback(scene, milliseconds, callback, args, kwargs)
            if scene not in self.__callback_after_scenes:
                self.__callback_after_scenes[scene] = WindowCallbackList()
            self.__callback_after_scenes[scene].append(window_callback)
        else:
            window_callback = WindowCallback(self, milliseconds, callback, args, kwargs)
            self.__callback_after.append(window_callback)
        return window_callback

    def remove_window_callback(self, window_callback: WindowCallback) -> None:
        if window_callback.scene is not None:
            scene_callback_after: Optional[WindowCallbackList] = self.__callback_after_scenes.get(window_callback.scene)
            if scene_callback_after is None:
                return
            try:
                scene_callback_after.remove(window_callback)
            except ValueError:
                pass
            if not scene_callback_after:
                self.__callback_after_scenes.pop(window_callback.scene)
        else:
            try:
                self.__callback_after.remove(window_callback)
            except ValueError:
                pass

    def get_actual_scene(self) -> Optional[Scene]:
        return self.__scenes.top()

    def get_scene(self, scene: Union[Scene, SceneAlias]) -> Scene:
        if not isinstance(scene, Scene):
            return self.__scenes.get(scene)
        if scene.window is not self:
            raise WindowError(f"{type(scene).__name__}: Trying to get a scene bound to an another window")
        return scene

    @overload
    def start_scene(self, scene: Scene) -> None:
        ...

    @overload
    def start_scene(self, scene: Scene, new_alias: SceneAlias) -> None:
        ...

    @overload
    def start_scene(self, scene: SceneAlias) -> None:
        ...

    def start_scene(self, scene: Union[Scene, SceneAlias], new_alias: Optional[SceneAlias] = None) -> None:
        scene = self.get_scene(scene)
        if scene.looping():
            return
        transition: _WindowTransition = _WindowTransition.SHOW
        try:
            self.__scenes.clear(until=scene)
        except WindowError:
            self.__scenes.push(scene, new_alias)
        if self.__actual_scene is None or self.__actual_scene is scene:
            return
        if self.__actual_scene not in self.__scenes:
            transition = _WindowTransition.HIDE
        self.__transition = transition

    def stop_scene(self, scene: Union[Scene, SceneAlias]) -> None:
        self.__scenes.clear(until=scene)
        self.__scenes.remove(scene)
        self.__transition = _WindowTransition.HIDE

    def __update_actual_scene(self) -> Optional[Scene]:
        actual_scene: Optional[Scene] = self.get_actual_scene()
        if actual_scene is not self.__actual_scene:
            if actual_scene is None:
                if self.__actual_scene is not None:
                    self.__actual_scene.on_quit()
            elif self.__actual_scene is None:
                actual_scene.on_start_loop()
            else:
                self.__actual_scene.on_quit()
                if self.__actual_scene.transition is not None:
                    if self.__transition == _WindowTransition.SHOW:
                        self.__actual_scene.transition.show_new_scene(self.__actual_scene, actual_scene)
                    elif self.__transition == _WindowTransition.HIDE:
                        self.__actual_scene.transition.hide_actual_scene(self.__actual_scene, actual_scene)
                actual_scene.on_start_loop()
            self.__actual_scene = actual_scene
        return actual_scene

    @property
    def framerate(self) -> float:
        return self.__main_clock.get_fps()

    @property
    def text_framerate(self) -> Text:
        return self.__text_framerate

    @property
    def rect(self) -> Rect:
        return self.__rect.copy()

    @property
    def left(self) -> int:
        return self.__rect.left

    @property
    def right(self) -> int:
        return self.__rect.right

    @property
    def top(self) -> int:
        return self.__rect.top

    @property
    def bottom(self) -> int:
        return self.__rect.bottom

    @property
    def size(self) -> Tuple[int, int]:
        return self.__rect.size

    @property
    def width(self) -> int:
        return self.__rect.width

    @property
    def height(self) -> int:
        return self.__rect.height

    @property
    def center(self) -> Tuple[int, int]:
        return self.__rect.center

    @property
    def centerx(self) -> int:
        return self.__rect.centerx

    @property
    def centery(self) -> int:
        return self.__rect.centery

    @property
    def topleft(self) -> Tuple[int, int]:
        return self.__rect.topleft

    @property
    def topright(self) -> Tuple[int, int]:
        return self.__rect.topright

    @property
    def bottomleft(self) -> Tuple[int, int]:
        return self.__rect.bottomleft

    @property
    def bottomright(self) -> Tuple[int, int]:
        return self.__rect.bottomright

    @property
    def midtop(self) -> Tuple[int, int]:
        return self.__rect.midtop

    @property
    def midbottom(self) -> Tuple[int, int]:
        return self.__rect.midbottom

    @property
    def midleft(self) -> Tuple[int, int]:
        return self.__rect.midleft

    @property
    def midright(self) -> Tuple[int, int]:
        return self.__rect.midright
