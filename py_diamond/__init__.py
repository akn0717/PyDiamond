# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond engine is a game engine inteded to game developers in Python language.
The framework uses the popular pygame library (https://github.com/pygame/pygame/).
"""

__all__ = []  # type: list[str]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__credits__ = ["Francis Clairicia-Rose-Claire-Josephine"]
__license__ = "GNU GPL v3.0"
__version__ = "1.0.0"
__maintainer__ = "Francis Clairicia-Rose-Claire-Josephine"
__email__ = "clairicia.rcj.francis@gmail.com"
__status__ = "Development"

import os
import sys

############ Environment initialization ############
if sys.version_info < (3, 10):
    raise ImportError("This framework must be ran with python >= 3.10 (actual={}.{}.{})".format(*sys.version_info[0:3]))

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # Must be set before importing pygame
if os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] not in ("0", "1"):
    raise ValueError("Invalid value for 'PYGAME_HIDE_SUPPORT_PROMPT' environment variable")
if os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] == "0":
    os.environ.pop("PYGAME_HIDE_SUPPORT_PROMPT")

############ Package initialization ############
import py_diamond.audio
import py_diamond.graphics
import py_diamond.math
import py_diamond.network
import py_diamond.resource
import py_diamond.system
import py_diamond.window

############ Cleanup ############
del os, sys, py_diamond
