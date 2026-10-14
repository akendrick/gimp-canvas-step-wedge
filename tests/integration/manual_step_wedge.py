"""Runs inside headless GIMP (scripts/run_integration.sh); not collected by pytest.

Adds the wedge to plain images and checks the canvas, the layer and the
pixels, then runs the registered procedure through the PDB.
"""
import importlib.util
import os
import sys

ROOT = os.environ["WEDGE_ROOT"]
spec = importlib.util.spec_from_file_location(
    "canvas_step_wedge_plugin", ROOT + "/canvas-step-wedge/canvas-step-wedge.py")
csw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(csw)
sys.path.insert(0, ROOT + "/canvas-step-wedge")
import wedge_math as wm  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def new_image(w, h, base=Gimp.ImageBaseType.RGB, fill="#ffffff"):
    image = Gimp.Image.new(w, h, base)
    t = Gimp.ImageType.GRAY_IMAGE if base == Gimp.ImageBaseType.GRAY else Gimp.ImageType.RGB_IMAGE
    layer = Gimp.Layer.new(image, "bg", w, h, t, 100.0, Gimp.LayerMode.NORMAL)
    image.insert_layer(layer, None, 0)
    Gimp.context_push()
    Gimp.context_set_foreground(Gegl.Color.new(fill))
    layer.edit_fill(Gimp.FillType.FOREGROUND)
    Gimp.context_pop()
    return image


def pixel(drawable, x, y):
    """R'G'B' u8 at x, y in the drawable's own coordinates."""
    return tuple(drawable.get_buffer().get(
        Gegl.Rectangle.new(x, y, 1, 1), 1.0, "R'G'B' u8", Gegl.AbyssPolicy.CLAMP))


# --- Defaults on an RGB image ------------------------------------------
image = new_image(600, 400)
warnings = []
wedge = csw.add_step_wedge(image, warnings=warnings)
check(warnings == [], warnings)
check((image.get_width(), image.get_height()) == (600, 445), "canvas grows by gap+box+margin")
check([l.get_name() for l in image.get_layers()] == ["Step Wedge", "bg"],
      [l.get_name() for l in image.get_layers()])
check(wedge.get_offsets()[1:] == (0, 400), f"wedge layer below the image: {wedge.get_offsets()}")
check((wedge.get_width(), wedge.get_height()) == (600, 45), "band size")
bg = image.get_layers()[1]
check((bg.get_width(), bg.get_height()) == (600, 400), "image layer unchanged")
check(pixel(bg, 300, 200) == (255, 255, 255), "image pixels unchanged")

lay = wm.layout(600, 400, 12, 15, 15, 15, 1)
check(pixel(wedge, 300, 5) == (0, 0, 0), "black gap")
check(pixel(wedge, 300, 40) == (0, 0, 0), "black bottom margin")
check(pixel(wedge, 0, 22) == (128, 128, 128), "outline frame on the left")
check(pixel(wedge, 300, 15) == (128, 128, 128), "outline frame along the top")
for rect, pct in zip(lay.patches, wm.step_percents(12)):
    g = wm.gray_value(pct)
    corner = pixel(wedge, rect.x, rect.y)  # labels are centred, corners stay clear
    check(corner == (g, g, g), f"step {pct:.0f}% is gray {g}, got {corner}")
    divider = pixel(wedge, rect.x + rect.width, rect.y)
    check(divider == (128, 128, 128), f"divider after {pct:.0f}%: {divider}")

# Labels are merged in: dark text on the white box, light text on the black one.
first, last = lay.patches[0], lay.patches[-1]
def values(rect):
    data = wedge.get_buffer().get(Gegl.Rectangle.new(rect.x, rect.y, rect.width, rect.height),
                                  1.0, "Y' u8", Gegl.AbyssPolicy.NONE)
    return set(data)
# (At the default 6px the text is antialiased, so it is gray, not solid.)
check(min(values(first)) < 215, f"a dark label in the 0% box: {min(values(first))}")
check(max(values(last)) > 40, f"a light label in the 100% box: {max(values(last))}")
check(len(image.get_layers()) == 2, "text layers merged into the wedge")
image.delete()

# --- Options: no labels, own spacing, thick coloured outline, gray image --
image = new_image(400, 100, Gimp.ImageBaseType.GRAY, "#808080")
red = Gegl.Color.new("black")
red.set_rgba(1.0, 0.0, 0.0, 1.0)
wedge = csw.add_step_wedge(image, steps=5, box=30, gap=4, margin=6, outline_color=red,
                           outline=3, labels=False)
check(image.get_height() == 140, f"100 + 4 + 30 + 6, got {image.get_height()}")
check(pixel(wedge, 200, 2) == (0, 0, 0), "gap")
check(pixel(wedge, 1, 20)[0] == pixel(wedge, 1, 20)[1], "gray image: outline converted to gray")
lay = wm.layout(400, 100, 5, 30, 4, 6, 3)
centre = lay.patches[2]
check(pixel(wedge, centre.x + centre.width // 2, centre.y + centre.height // 2) == (128, 128, 128),
      "no label: 50% box is plain gray 128")
image.delete()

# --- Narrow boxes: labels that cannot fit are left off, with a warning --
image = new_image(80, 50)
warnings = []
csw.add_step_wedge(image, steps=40, box=15, warnings=warnings)
check(len(warnings) == 1 and "did not fit" in warnings[0], warnings)
image.delete()

# --- Too narrow for the steps at all ------------------------------------
image = new_image(10, 10)
try:
    csw.add_step_wedge(image, steps=12)
    check(False, "should refuse")
except ValueError as exc:
    check("too narrow" in str(exc), str(exc))
check(image.get_height() == 10, "canvas untouched when refused")
image.delete()

# --- The registered procedure, with its own defaults --------------------
image = new_image(240, 60)
proc = Gimp.get_pdb().lookup_procedure("python-fu-canvas-step-wedge")
config = proc.create_config()
config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
config.set_property("image", image)
result = proc.run(config)
check(result.index(0) == Gimp.PDBStatusType.SUCCESS, "procedure runs")
check(image.get_height() == 105, f"default 15 + 15 + 15 band, got {image.get_height()}")
wedge = image.get_layers()[0]
check(pixel(wedge, 0, 22) == (128, 128, 128),
      f"default outline is 50% gray on first run, got {pixel(wedge, 0, 22)}")
image.delete()

# Leading newline: GIMP can print an update notice with no line break of its
# own, which would otherwise glue itself onto this marker line.
print("\nSTEP_WEDGE_PASSED")
