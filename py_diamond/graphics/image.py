# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Image module"""

from __future__ import annotations

__all__ = ["Image"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import TYPE_CHECKING, overload

from pygame.transform import rotate as _surface_rotate, rotozoom as _surface_rotozoom, smoothscale as _surface_smoothscale

from .color import Color
from .drawable import TDrawable
from .rect import Rect
from .surface import Surface, create_surface, load_image, save_image

if TYPE_CHECKING:
    from .renderer import AbstractRenderer


class Image(TDrawable):

    __slots__ = (
        "__default_image",
        "__image",
        "__smooth_scale",
    )

    @overload
    def __init__(self) -> None:
        ...

    @overload
    def __init__(self, image: Surface, *, copy: bool = True, width: float | None = None, height: float | None = None) -> None:
        ...

    @overload
    def __init__(self, image: str, *, width: float | None = None, height: float | None = None) -> None:
        ...

    def __init__(
        self,
        image: Surface | str | None = None,
        *,
        copy: bool = True,
        width: float | None = None,
        height: float | None = None,
    ) -> None:
        super().__init__()
        if image is None:
            image = create_surface((0, 0))

        self.__default_image: Surface
        self.__image: Surface
        self.__smooth_scale: bool = False

        if isinstance(image, Surface):
            self.__default_image = image.copy() if copy else image
            self.__image = self.__default_image.copy()
        else:
            self.__default_image = Surface((0, 0))
            self.__image = self.__default_image.copy()
            self.load(image)
        if width is not None and height is not None:
            self.scale_to_size((width, height))
        elif width is not None:
            self.scale_to_width(width)
        elif height is not None:
            self.scale_to_height(height)
        self.topleft = (0, 0)

    def draw_onto(self, target: AbstractRenderer) -> None:
        image: Surface = self.__image
        topleft: tuple[float, float] = self.topleft
        target.draw(image, topleft)

    def get(self, apply_rotation_scale: bool = False) -> Surface:
        if apply_rotation_scale:
            return self.__image.copy()
        return self.__default_image.copy()

    def set(self, image: Surface, copy: bool = True) -> None:
        center: tuple[float, float] = self.center
        self.__default_image = image.copy() if copy else image
        self.apply_rotation_scale()
        self.center = center

    def fill(self, color: Color, rect: Rect | None = None) -> None:
        mask = create_surface(self.__default_image.get_size() if rect is None else rect.size)
        mask.fill(color)
        self.__default_image.blit(mask, rect or (0, 0))
        self.apply_rotation_scale()

    def load(self, file: str) -> None:
        center: tuple[float, float] = self.center
        self.__default_image = load_image(file)
        self.apply_rotation_scale()
        self.center = center

    def save(self, file: str) -> None:
        save_image(self.__image, file)

    def get_local_size(self) -> tuple[float, float]:
        return self.__default_image.get_size()

    def get_size(self) -> tuple[float, float]:
        return self.__image.get_size()

    def use_smooth_scale(self, status: bool) -> None:
        former_state: bool = self.__smooth_scale
        self.__smooth_scale = actual_state = bool(status)
        if former_state != actual_state:
            self.apply_rotation_scale()

    def _apply_both_rotation_and_scale(self) -> None:
        angle: float = self.angle
        scale: float = self.scale
        image: Surface = self.__default_image

        if not self.__smooth_scale:
            self.__image = _surface_rotozoom(image, angle, scale)
        else:
            if scale != 1:
                w, h = self.get_local_size()
                w = round(w * scale)
                h = round(h * scale)
                image = _surface_smoothscale(image, (w, h))
            self.__image = _surface_rotate(image, angle)

    def _apply_only_rotation(self) -> None:
        angle: float = self.angle
        image: Surface = self.__default_image
        self.__image = _surface_rotate(image, angle)

    def _apply_only_scale(self) -> None:
        scale: float = self.scale
        image: Surface = self.__default_image

        if not self.__smooth_scale:
            self.__image = _surface_rotozoom(image, 0, scale)
        elif scale != 1:
            w, h = self.get_local_size()
            w = round(w * scale)
            h = round(h * scale)
            image = _surface_smoothscale(image, (w, h))
