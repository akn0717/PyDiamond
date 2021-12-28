# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's graphics module"""

__all__ = [
    "AbstractCircleShape",
    "AbstractRectangleShape",
    "AbstractShape",
    "AnimatedSprite",
    "BLACK",
    "BLUE",
    "BLUE_DARK",
    "BLUE_LIGHT",
    "BooleanCheckBox",
    "Button",
    "COMPILED_SURFACE_EXTENSION",
    "CYAN",
    "CheckBox",
    "CircleShape",
    "Color",
    "CrossShape",
    "DiagonalCrossShape",
    "Drawable",
    "DrawableGroup",
    "Entry",
    "Font",
    "GRAY",
    "GRAY_DARK",
    "GRAY_LIGHT",
    "GREEN",
    "GREEN_DARK",
    "GREEN_LIGHT",
    "GradientShape",
    "HorizontalGradientShape",
    "HorizontalMultiColorShape",
    "Image",
    "ImageButton",
    "ImmutableColor",
    "LayeredGroup",
    "LayeredSpriteGroup",
    "MAGENTA",
    "MetaButton",
    "MetaCheckBox",
    "MetaDrawable",
    "MetaEntry",
    "MetaShape",
    "MetaTDrawable",
    "MetaText",
    "MetaThemedObject",
    "MetaThemedShape",
    "MetaTransformable",
    "MultiColorShape",
    "NoTheme",
    "ORANGE",
    "OutlinedShape",
    "PURPLE",
    "PlusCrossShape",
    "PolygonShape",
    "ProgressBar",
    "RED",
    "RED_DARK",
    "RED_LIGHT",
    "RadialGradientShape",
    "Rect",
    "RectangleShape",
    "Renderer",
    "Scale",
    "SingleColorShape",
    "Sprite",
    "SpriteGroup",
    "SquaredGradientShape",
    "Surface",
    "SurfaceRenderer",
    "SysFont",
    "TDrawable",
    "TRANSPARENT",
    "Text",
    "TextImage",
    "ThemeNamespace",
    "ThemeType",
    "ThemedObject",
    "TransformAnimation",
    "Transformable",
    "VerticalGradientShape",
    "VerticalMultiColorShape",
    "WHITE",
    "YELLOW",
    "abstract_theme_class",
    "create_surface",
    "load_image",
    "save_image",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import copyreg
import os
import typing

import pygame

if pygame.version.vernum < (2, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.0'")

############ Surface pickling register ############
copyreg.pickle(
    pygame.surface.Surface,
    lambda s, serializer=pygame.image.tostring, deserializer=pygame.image.fromstring: (  # type: ignore
        deserializer,
        (serializer(s, "ARGB"), s.get_size(), "ARGB"),
    ),
)

############ Cleanup ############
del os, typing, pygame, copyreg


############ Package initialization ############
from .button import Button, ImageButton, MetaButton
from .checkbox import BooleanCheckBox, CheckBox, MetaCheckBox
from .color import (
    BLACK,
    BLUE,
    BLUE_DARK,
    BLUE_LIGHT,
    CYAN,
    GRAY,
    GRAY_DARK,
    GRAY_LIGHT,
    GREEN,
    GREEN_DARK,
    GREEN_LIGHT,
    MAGENTA,
    ORANGE,
    PURPLE,
    RED,
    RED_DARK,
    RED_LIGHT,
    TRANSPARENT,
    WHITE,
    YELLOW,
    Color,
    ImmutableColor,
)
from .drawable import Drawable, DrawableGroup, LayeredGroup, MetaDrawable, MetaTDrawable, TDrawable
from .entry import Entry, MetaEntry
from .font import Font, SysFont
from .gradients import (
    GradientShape,
    HorizontalGradientShape,
    HorizontalMultiColorShape,
    MultiColorShape,
    RadialGradientShape,
    SquaredGradientShape,
    VerticalGradientShape,
    VerticalMultiColorShape,
)
from .image import Image
from .progress import ProgressBar
from .rect import Rect
from .renderer import Renderer, SurfaceRenderer
from .scale import Scale
from .shape import (
    AbstractCircleShape,
    AbstractRectangleShape,
    AbstractShape,
    CircleShape,
    CrossShape,
    DiagonalCrossShape,
    MetaShape,
    MetaThemedShape,
    OutlinedShape,
    PlusCrossShape,
    PolygonShape,
    RectangleShape,
    SingleColorShape,
)
from .sprite import AnimatedSprite, LayeredSpriteGroup, Sprite, SpriteGroup
from .surface import COMPILED_SURFACE_EXTENSION, Surface, create_surface, load_image, save_image
from .text import MetaText, Text, TextImage
from .theme import MetaThemedObject, NoTheme, ThemedObject, ThemeNamespace, ThemeType, abstract_theme_class
from .transformable import MetaTransformable, Transformable

# Put it here to avoid circular import with 'window' module
from .animation import TransformAnimation  # isort:skip
