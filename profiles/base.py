"""Contract shared by every analysis profile.

A profile module defines NAME and ANALYSES = {"count": Analysis, "boundary": Analysis, "cell": Analysis}.
Analysis.run(img, cfg) takes a BGR image and that analysis' config, and returns result(...).
"""
import statistics
from dataclasses import dataclass
from typing import Callable

# Kinds of tunable setting, besides (min, max, step) sliders and None (free number)
HSV = "hsv"    # <key>_lower / <key>_upper pair of [H, S, V]
BOOL = "bool"


@dataclass(frozen=True)
class Analysis:
    run: Callable
    settings: tuple  # (config key, i18n label key, (min, max, step) | HSV | BOOL | None) shown in Advanced Settings


class ModelUnavailable(Exception):
    """A profile's model cannot be loaded; args[0] is the i18n key of the message for the user."""


def result(images=(), cells=(), crops=(), summary=None, warning=None, **warning_args):
    """Uniform analysis output.

    images  : (file suffix, caption i18n key, BGR image, caption args) per result image
    cells   : per-cell records; each has "image", the suffix of the result image it is labelled on
    crops   : one image per cell (same order as cells), or empty
    summary : per-image summary fields
    warning : i18n key or None, formatted with warning_args
    """
    return {"images": list(images), "cells": list(cells), "crops": list(crops), "summary": summary or {},
            "warning": warning, "warning_args": warning_args}


# N/C denominator, set per profile by config `nc_denominator`. Both definitions appear in the literature;
# "cell" counts cytoplasm above/below the nucleus (cells are 3D), "cytoplasm" uses the 2D area outside it.
_NC_DENOMINATORS = {"cell": lambda nucleus, cell: cell, "cytoplasm": lambda nucleus, cell: cell - nucleus}


def nc_ratio(nucleus, cell, denominator):
    """Nucleus area ÷ whole cell area ("cell") or ÷ (cell − nucleus) area ("cytoplasm")."""
    return nucleus / max(_NC_DENOMINATORS[denominator](nucleus, cell), 1)


def means(records, fields):
    """mean_<field> of each field over the records (None when there are none)."""
    return {f"mean_{f}": statistics.mean(r[f] for r in records) if records else None for f in fields}
