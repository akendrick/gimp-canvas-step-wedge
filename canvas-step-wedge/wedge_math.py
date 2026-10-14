"""Step wedge layout and pixels for Canvas Step Wedge, kept free of any GIMP
dependency so it can be unit-tested.

Steps are evenly spaced in ink %: step 1 is 0% (paper white), the last step
100% (solid black). Gray values are standard 8-bit sRGB, so a 50% step is
gray 128 (the convention ChartThrob uses for its patches).

The wedge sits in a black band added below the image:

    +---------------------------+  <- old bottom edge of the image
    |  gap                      |
    | +----+----+----+---+----+ |  <- strip: one box per step, full width
    | | 0% | 9% |18% |...|100%| |     (outline frame + dividers)
    | +----+----+----+---+----+ |
    |  bottom margin            |
    +---------------------------+
"""
from typing import List, NamedTuple, Sequence, Tuple

MIN_STEPS, MAX_STEPS, DEFAULT_STEPS = 2, 40, 12
DEFAULT_BOX = 15
LABEL_SCALE = 0.40  # label text size as a fraction of the box height
BAND_RGB = (0, 0, 0)

RGB = Tuple[int, int, int]


def round_half_up(value: float) -> int:
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)


def step_percents(steps: int) -> List[float]:
    """Ink % of each step, 0 .. 100 evenly spaced."""
    if not MIN_STEPS <= steps <= MAX_STEPS:
        raise ValueError(f"steps must be {MIN_STEPS}..{MAX_STEPS}")
    return [100.0 * i / (steps - 1) for i in range(steps)]


def gray_value(percent: float) -> int:
    """8-bit sRGB gray for an ink %: 0% -> 255 (white), 100% -> 0 (black)."""
    return round_half_up(255 - 255 * percent / 100.0)


def label_texts(percent: float) -> List[str]:
    """Label candidates, longest first; the first that fits its box is used."""
    whole = round_half_up(percent)
    return [f"{whole}%", str(whole)]


def label_is_light(percent: float) -> bool:
    """White text on dark patches, black on light ones (as in ChartThrob)."""
    return gray_value(percent) < 128


def label_size(box: int) -> int:
    """Label font size in pixels: about 40% of the box height."""
    return max(1, round_half_up(box * LABEL_SCALE))


class Rect(NamedTuple):
    x: int
    y: int
    width: int
    height: int


class Layout(NamedTuple):
    width: int            # image width = band width
    image_height: int
    gap: int
    box: int
    margin: int
    outline: int          # outline width actually used (may be reduced to fit)
    patches: List[Rect]   # inside the outline, in band coordinates

    @property
    def band_height(self) -> int:
        return self.gap + self.box + self.margin

    @property
    def canvas_height(self) -> int:
        return self.image_height + self.band_height


def box_edges(width: int, steps: int) -> List[int]:
    """x positions of the step boundaries, 0 .. width. Boxes share the width
    as evenly as whole pixels allow: no two differ by more than 1px."""
    return [round_half_up(i * width / steps) for i in range(steps + 1)]


def layout(width: int, image_height: int, steps: int, box: int, gap: int,
           margin: int, outline: int) -> Layout:
    """Where everything goes. The outline is a frame of `outline` px around
    the strip plus `outline` px dividers between boxes (all inside the strip,
    so the strip stays exactly `box` px tall). It is thinned if it would
    leave a patch less than 1px wide or tall."""
    if width < steps:
        raise ValueError(f"The image is {width}px wide: too narrow for {steps} steps "
                         "(each box needs at least 1px).")
    if box < 1:
        raise ValueError("The box size must be at least 1px.")
    edges = box_edges(width, steps)
    narrowest = min(b - a for a, b in zip(edges, edges[1:]))
    outline = max(0, min(outline, (box - 1) // 2, (narrowest - 1) // 2))
    half = outline // 2
    patches = []
    for i in range(steps):
        left = outline if i == 0 else edges[i] - half + outline
        right = width - outline if i == steps - 1 else edges[i + 1] - half
        patches.append(Rect(left, gap + outline, right - left, box - 2 * outline))
    return Layout(width, image_height, gap, box, margin, outline, patches)


def band_pixels(lay: Layout, steps: int, outline_rgb: Sequence[int]) -> bytes:
    """The whole band as R'G'B' u8 rows: black, with the strip drawn in it
    (outline colour everywhere in the strip, then each patch on top)."""
    width = lay.width
    black_row = bytes(BAND_RGB) * width
    outline_row = bytes(outline_rgb[:3]) * width
    patch_row = bytearray(outline_row)
    for rect, pct in zip(lay.patches, step_percents(steps)):
        g = gray_value(pct)
        patch_row[rect.x * 3:(rect.x + rect.width) * 3] = bytes((g, g, g)) * rect.width
    frame = lay.outline
    strip = outline_row * frame + bytes(patch_row) * (lay.box - 2 * frame) + outline_row * frame
    return black_row * lay.gap + strip + black_row * lay.margin
