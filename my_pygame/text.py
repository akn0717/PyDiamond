# -*- coding: Utf-8 -*

from __future__ import annotations

import os.path

from typing import Dict, List, Optional, Tuple, Union
from enum import Enum, unique
from textwrap import wrap
from operator import truth

import pygame.transform

from pygame.font import Font, SysFont, get_default_font
from pygame.color import Color
from pygame.surface import Surface

from .drawable import ThemedDrawable
from .colors import BLACK
from .theme import Theme
from .surface import create_surface

_TextFont = Union[Font, Tuple[Optional[str], int]]


class Text(ThemedDrawable):
    @unique
    class Justify(str, Enum):
        LEFT = "left"
        RIGHT = "right"
        CENTER = "center"

    def __init__(
        self,
        message: str = "",
        *,
        font: Optional[_TextFont] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        color: Color = BLACK,
        wrap: int = 0,
        justify: Union[str, Justify] = "left",
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        theme: Optional[Theme] = None,
    ) -> None:
        super().__init__()
        self.__update: bool = True
        self.__str: str = str()
        self.__wrap: int = 0
        self.__font: Font = Text.create_font(None)
        self.__custom_font: Dict[int, Font] = dict()
        self.__color: Color = BLACK
        self.__justify: Text.Justify = Text.Justify.LEFT
        self.__shadow_offset: Tuple[float, float] = (0, 0)
        self.__shadow_color = BLACK
        self.__default_image: Surface = create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.set_font(font, bold=bold, italic=italic, underline=underline)
        self.message = message
        self.color = color
        self.wrap = wrap
        self.justify = Text.Justify(justify)
        self.shadow = (shadow_x, shadow_y)
        self.shadow_color = shadow_color

    def draw_onto(self, surface: Surface) -> None:
        self.__update_surface()
        surface.blit(self.__image, self.topleft)

    def to_surface(self) -> Surface:
        self.__update_surface()
        return self.__image.copy()

    def get_local_size(self) -> Tuple[float, float]:
        self.__update_surface()
        return self.__default_image.get_size()

    def get_size(self) -> Tuple[float, float]:
        self.__update_surface()
        return self.__image.get_size()

    @staticmethod
    def create_font(
        font: Optional[_TextFont], bold: Optional[bool] = None, italic: Optional[bool] = None, underline: Optional[bool] = None
    ) -> Font:
        obj: Font
        if isinstance(font, (tuple, list)):
            if font[0] is not None and os.path.isfile(font[0]):
                obj = Font(*font)
                if bold is not None:
                    obj.set_bold(bold)
                if italic is not None:
                    obj.set_italic(italic)
            else:
                font_family: str = font[0] if font[0] is not None and font[0] else get_default_font()
                obj = SysFont(font_family, font[1], bold=truth(bold), italic=truth(italic))
        elif isinstance(font, Font):
            obj = font
            if bold is not None:
                obj.set_bold(bold)
            if italic is not None:
                obj.set_italic(italic)
        else:
            obj = SysFont(get_default_font(), 15, bold=truth(bold), italic=truth(italic))
        if underline is not None:
            obj.set_underline(underline)
        return obj

    def set_font(
        self,
        font: Optional[_TextFont],
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
    ) -> None:
        self.__font = Text.create_font(font, bold=bold, italic=italic, underline=underline)
        self.__need_update()

    def set_custom_line_font(self, index: int, font: Font) -> None:
        if index < 0:
            raise ValueError(f"Negative index: {index}")
        self.__custom_font[index] = Text.create_font(font)
        self.__need_update()

    def remove_custom_line_font(self, index: int) -> None:
        if index < 0:
            raise ValueError(f"Negative index: {index}")
        self.__custom_font.pop(index, None)
        self.__need_update()

    def __need_update(self) -> None:
        self.__update = True

    def __update_surface(self) -> None:
        if self.__update:
            self.__update = False
            center: Tuple[float, float] = self.center
            self.__default_image = self.__render_text()
            self._apply_rotation_scale()
            self.center = center

    def _apply_rotation_scale(self) -> None:
        self.__image = pygame.transform.rotozoom(self.__default_image, self.angle, self.scale)

    def __render_text(self, *, drawing_shadow: bool = False) -> Surface:
        render_lines: List[Surface] = list()
        render_width: float = 0
        render_height: float = 0
        text: Surface
        for index, line in enumerate(self.message.splitlines()):
            font = self.__custom_font.get(index, self.font)
            render = font.render(line, True, self.color if not drawing_shadow else self.shadow_color)
            render_width = max(render_width, render.get_width())
            render_height += render.get_height()
            render_lines.append(render)
        if not render_lines:
            return create_surface((0, 0))
        if len(render_lines) == 1:
            text = render_lines[0]
        else:
            text = create_surface((render_width, render_height))
            text_rect = text.get_rect()
            y = 0
            justify_parameters = {
                Text.Justify.LEFT: {"left": text_rect.left},
                Text.Justify.RIGHT: {"right": text_rect.right},
                Text.Justify.CENTER: {"centerx": text_rect.centerx},
            }
            params = justify_parameters[self.justify]
            for render in render_lines:
                text.blit(render, render.get_rect(**params, y=y))
                y += render.get_height()
        if drawing_shadow:
            return text
        shadow_x, shadow_y = self.shadow
        if shadow_x == 0 and shadow_y == 0:
            return text
        shadow_text: Surface = self.__render_text(drawing_shadow=True)
        render_width += abs(shadow_x)
        render_height += abs(shadow_y)
        render = create_surface((render_width, render_height))

        text_x: float = 0
        text_y: float = 0

        if shadow_x < 0:
            text_x = -shadow_x
            shadow_x = 0
        if shadow_y < 0:
            text_y = -shadow_y
            shadow_y = 0

        render.blit(shadow_text, (shadow_x, shadow_y))
        render.blit(text, (text_x, text_y))

        return render

    @property
    def font(self) -> Font:
        return self.__font

    @font.setter
    def font(self, font: Font) -> None:
        self.set_font(font)

    @property
    def message(self) -> str:
        return self.__str

    @message.setter
    def message(self, string: str) -> None:
        if string != self.__str:
            self.__str = "\n".join(wrap(string, width=self.__wrap)) if self.__wrap > 0 else string
            self.__need_update()

    @property
    def wrap(self) -> int:
        return self.__wrap

    @wrap.setter
    def wrap(self, value: int) -> None:
        value = max(int(value), 0)
        if value != self.__wrap:
            self.__wrap = value
            self.__str = "\n".join(wrap(self.__str, width=self.__wrap)) if self.__wrap > 0 else self.__str
            self.__need_update()

    @property
    def justify(self) -> Justify:
        return self.__justify

    @justify.setter
    def justify(self, justify: Justify) -> None:
        justify = Text.Justify(justify)
        if justify != self.__justify:
            self.__justify = justify
            self.__need_update()

    @property
    def color(self) -> Color:
        return self.__color

    @color.setter
    def color(self, color: Color) -> None:
        color = Color(color)
        if color != self.__color:
            self.__color = color
            self.__need_update()

    @property
    def shadow(self) -> Tuple[float, float]:
        return self.__shadow_offset

    @shadow.setter
    def shadow(self, pos: Tuple[float, float]) -> None:
        if self.__shadow_offset != pos:
            self.__shadow_offset = pos
            self.__need_update()

    @property
    def shadow_x(self) -> float:
        return self.shadow[0]

    @shadow_x.setter
    def shadow_x(self, shadow_x: float) -> None:
        self.shadow = (shadow_x, self.shadow_y)

    @property
    def shadow_y(self) -> float:
        return self.shadow[1]

    @shadow_y.setter
    def shadow_y(self, shadow_y: float) -> None:
        self.shadow = (self.shadow_x, shadow_y)

    @property
    def shadow_color(self) -> Color:
        return self.__shadow_color

    @shadow_color.setter
    def shadow_color(self, color: Color) -> None:
        self.__shadow_color = Color(color)
        if self.__shadow_color != color:
            self.__shadow_color = color
            self.__need_update()
