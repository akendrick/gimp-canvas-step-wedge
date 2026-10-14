#!/usr/bin/env python3
"""Canvas Step Wedge -- GIMP 3 plugin that grows the canvas and adds a gray
step wedge along the bottom of the image.

Colors > Canvas Step Wedge...

The canvas is extended downward (the image itself is not changed) and the
new area is a black band on its own "Step Wedge" layer, holding a row of gray
boxes from 0% (white) to 100% (black) in even ink-% steps across the full
image width, as in ChartThrob's step wedge.

Options:
  Steps (2-40)         Number of boxes (default 12: 0%, 9%, 18% ... 100%).
  Box size (px)        Height of the boxes (default 15).
  Spacing = box size   Gap above and margin below the wedge both follow the
                       box size (default on). Turn off to set them yourself:
    Gap (px)           Black space between the image and the wedge.
    Bottom margin (px) Black space below the wedge.
  Outline colour       Frame and dividers around the boxes (default 50% gray,
  Outline width (px)   1px; 0 for none) so white and black boxes stay visible.
  Labels               Ink % in each box, about 40% of the box height, white
                       on dark boxes and black on light ones (default on).

Install: scripts/install.sh. By hand, this folder (named like this file) must
sit in GIMP's plug-ins directory and this file must be executable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import gi

gi.require_version("Gimp", "3.0")
gi.require_version("Gegl", "0.4")
gi.require_version("Babl", "0.1")
from gi.repository import Babl, Gegl, Gimp, GLib, GObject  # noqa: E402

from wedge_math import (  # noqa: E402
    DEFAULT_BOX, DEFAULT_STEPS, MAX_STEPS, MIN_STEPS, band_pixels, label_is_light,
    label_size, label_texts, layout, step_percents,
)

__version__ = "0.1.0"


def N_(message):
    return message


def _(message):
    return GLib.dgettext(None, message)


PROC_NAME = "python-fu-canvas-step-wedge"
LAYER_NAME = "Step Wedge"
DEFAULT_OUTLINE = "#808080"  # 50% gray
FONT_CANDIDATES = ("Arial Regular", "Arial", "Helvetica Regular", "Sans-serif")


def _rgb8(color):
    return list(color.get_bytes(Babl.format("R'G'B' u8")).get_data())[:3]


def _gray(value):
    """A Gegl.Color for an 8-bit sRGB gray. set_rgba() alone would be linear
    light; see ChartThrob's _gray_color()."""
    color = Gegl.Color.new("black")
    v = value / 255.0
    color.set_rgba_with_space(v, v, v, 1.0, Babl.format("R'G'B'A float"))
    return color


def _find_font():
    for name in FONT_CANDIDATES:
        font = Gimp.Font.get_by_name(name)
        if font is not None:
            return font
    return None


def add_step_wedge(image, steps=DEFAULT_STEPS, box=DEFAULT_BOX, gap=None, margin=None,
                   outline_color=None, outline=1, labels=True, warnings=None):
    """Grow the canvas and add the wedge, as one undo step. `gap` and
    `margin` default to the box size. Returns the "Step Wedge" layer. Any
    message the user should see (labels that did not fit) is appended to
    `warnings` when given."""
    gap = box if gap is None else gap
    margin = box if margin is None else margin
    if outline_color is None:
        outline_color = _gray(128)
    lay = layout(image.get_width(), image.get_height(), steps, box, gap, margin, outline)

    image.undo_group_start()
    try:
        image.resize(lay.width, lay.canvas_height, 0, 0)  # layers keep their place
        layer_type = (Gimp.ImageType.GRAY_IMAGE
                      if image.get_base_type() == Gimp.ImageBaseType.GRAY
                      else Gimp.ImageType.RGB_IMAGE)
        layer = Gimp.Layer.new(image, LAYER_NAME, lay.width, lay.band_height,
                               layer_type, 100.0, Gimp.LayerMode.NORMAL)
        image.insert_layer(layer, None, 0)
        layer.set_offsets(0, lay.image_height)
        buffer = layer.get_buffer()
        buffer.set(Gegl.Rectangle.new(0, 0, lay.width, lay.band_height), "R'G'B' u8",
                   band_pixels(lay, steps, _rgb8(outline_color)))
        buffer.flush()
        layer.update(0, 0, lay.width, lay.band_height)
        if labels:
            layer = _draw_labels(image, layer, lay, steps, warnings)
        return layer
    finally:
        image.undo_group_end()


def _draw_labels(image, layer, lay, steps, warnings):
    """Centre an ink-% label in each patch and merge it into the wedge
    layer. "100%" falls back to "100" in a narrow box; if even that does not
    fit, that label is left off and a warning is added."""
    font = _find_font()
    if font is None:
        if warnings is not None:
            warnings.append("No usable font was found, so the labels were left off.")
        return layer
    size = label_size(lay.box)
    skipped = 0
    for rect, pct in zip(lay.patches, step_percents(steps)):
        text_layer = None
        for text in label_texts(pct):
            text_layer = Gimp.TextLayer.new(image, text, font, size, Gimp.Unit.pixel())
            image.insert_layer(text_layer, None, image.get_item_position(layer))
            if text_layer.get_width() <= rect.width and text_layer.get_height() <= rect.height + 2:
                break
            image.remove_layer(text_layer)
            text_layer = None
        if text_layer is None:
            skipped += 1
            continue
        text_layer.set_color(_gray(255 if label_is_light(pct) else 0))
        text_layer.set_offsets(
            rect.x + (rect.width - text_layer.get_width()) // 2,
            lay.image_height + rect.y + (rect.height - text_layer.get_height()) // 2,
        )
        layer = image.merge_down(text_layer, Gimp.MergeType.CLIP_TO_BOTTOM_LAYER)
    if skipped and warnings is not None:
        warnings.append(
            f"{skipped} of {steps} labels did not fit in their boxes and were left off. "
            "Use a larger box size, fewer steps or a wider image.")
    return layer


def _apply_first_run_defaults(config):
    """GIMP 3.2.4 loses colour argument defaults after registration (they
    arrive as black -- GIMP's own Foggify plugin shows the same), and a black
    outline would vanish against the black band. So the first time the
    plugin runs, a black outline colour is taken to mean "no default
    arrived" and replaced with the intended 50% gray. A marker file in the
    GIMP profile makes this happen only once; after that GIMP's remembered
    last-used values apply, and black can be chosen deliberately."""
    marker = os.path.join(Gimp.directory(), "canvas-step-wedge.defaults-applied")
    if os.path.exists(marker):
        return
    if _rgb8(config.get_property("outline-color")) == [0, 0, 0]:
        config.set_property("outline-color", Gegl.Color.new(DEFAULT_OUTLINE))
    try:
        with open(marker, "w") as f:
            f.write("Canvas Step Wedge: first-run colour defaults applied.\n")
    except OSError:
        pass


def canvas_step_wedge_run(procedure, run_mode, image, drawables, config, data):
    _apply_first_run_defaults(config)
    if run_mode == Gimp.RunMode.INTERACTIVE:
        gi.require_version("GimpUi", "3.0")
        from gi.repository import GimpUi

        GimpUi.init(PROC_NAME)
        dialog = GimpUi.ProcedureDialog(procedure=procedure, config=config)
        dialog.fill(["steps", "box-size", "match-box", "gap", "margin",
                     "outline-color", "outline-width", "labels"])
        # Gap and margin are only set by hand when they don't follow the box.
        dialog.set_sensitive("gap", True, config, "match-box", True)
        dialog.set_sensitive("margin", True, config, "match-box", True)
        if not dialog.run():
            dialog.destroy()
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())
        dialog.destroy()

    box = config.get_property("box-size")
    match = config.get_property("match-box")
    warnings = []
    try:
        add_step_wedge(
            image,
            steps=config.get_property("steps"),
            box=box,
            gap=box if match else config.get_property("gap"),
            margin=box if match else config.get_property("margin"),
            outline_color=config.get_property("outline-color"),
            outline=config.get_property("outline-width"),
            labels=config.get_property("labels"),
            warnings=warnings,
        )
    except ValueError as exc:
        Gimp.message(str(exc))
        return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR,
                                           GLib.Error(str(exc)))
    Gimp.displays_flush()
    if warnings:
        Gimp.message("\n".join(warnings))
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


class CanvasStepWedgePlugIn(Gimp.PlugIn):
    def do_set_i18n(self, procname):
        return True, "gimp30-python", None

    def do_query_procedures(self):
        return [PROC_NAME]

    def do_create_procedure(self, name):
        if name != PROC_NAME:
            return None

        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, canvas_step_wedge_run, None
        )
        procedure.set_image_types("RGB*, GRAY*")
        procedure.set_sensitivity_mask(
            Gimp.ProcedureSensitivityMask.DRAWABLE
            | Gimp.ProcedureSensitivityMask.DRAWABLES
        )
        procedure.set_documentation(
            _("Grow the canvas and add a gray step wedge below the image"),
            _("Extends the canvas downward and adds a black band, on its own "
              "'Step Wedge' layer, holding gray boxes from 0% (white) to 100% "
              "(black) in even steps across the full image width, with optional "
              "outlines and ink-% labels. The image itself is not changed."),
            name,
        )
        procedure.set_menu_label(_("Canvas Step Wedge..."))
        procedure.set_attribution(
            f"Canvas Step Wedge plugin {__version__}", "MIT License", "2026")
        procedure.add_menu_path("<Image>/Colors")

        procedure.add_int_argument(
            "steps", _("_Steps"),
            _("Number of gray boxes, from 0% (white) to 100% (black) in even steps"),
            MIN_STEPS, MAX_STEPS, DEFAULT_STEPS, GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "box-size", _("_Box size (px)"), _("Height of the gray boxes in pixels"),
            1, 2000, DEFAULT_BOX, GObject.ParamFlags.READWRITE,
        )
        procedure.add_boolean_argument(
            "match-box", _("Spacing = box si_ze"),
            _("Make the gap above the wedge and the margin below it the same as "
              "the box size. Turn off to set them yourself."),
            True, GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "gap", _("_Gap (px)"),
            _("Black space between the bottom of the image and the wedge"),
            0, 10000, DEFAULT_BOX, GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "margin", _("Bottom _margin (px)"),
            _("Black space below the wedge, so it does not touch the canvas edge"),
            0, 10000, DEFAULT_BOX, GObject.ParamFlags.READWRITE,
        )
        procedure.add_color_argument(
            "outline-color", _("_Outline colour"),
            _("Colour of the frame and dividers around the boxes"),
            False, Gegl.Color.new(DEFAULT_OUTLINE), GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "outline-width", _("Outline _width (px)"),
            _("Width of the frame and dividers; 0 for no outline. Thinned "
              "automatically if the boxes are too small for it."),
            0, 50, 1, GObject.ParamFlags.READWRITE,
        )
        procedure.add_boolean_argument(
            "labels", _("_Labels"),
            _("Print each box's ink % inside it, about 40% of the box height"),
            True, GObject.ParamFlags.READWRITE,
        )
        return procedure


if __name__ == "__main__":
    # Guarded so the module can be imported (e.g. by tests) without starting
    # Gimp.main()'s wire-protocol handshake.
    Gimp.main(CanvasStepWedgePlugIn.__gtype__, sys.argv)
