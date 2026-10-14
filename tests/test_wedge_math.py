import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "canvas-step-wedge"))
from wedge_math import (  # noqa: E402
    Rect, band_pixels, box_edges, gray_value, label_is_light, label_size, label_texts,
    layout, step_percents,
)


def test_twelve_even_steps_from_white_to_black():
    pcts = step_percents(12)
    assert pcts[0] == 0.0 and pcts[-1] == 100.0
    assert [gray_value(p) for p in pcts] == [
        255, 232, 209, 185, 162, 139, 116, 93, 70, 46, 23, 0]


def test_eleven_steps_are_exact_tens():
    assert [label_texts(p)[0] for p in step_percents(11)] == [
        "0%", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"]


@pytest.mark.parametrize("steps", [1, 41])
def test_step_range_is_2_to_40(steps):
    with pytest.raises(ValueError):
        step_percents(steps)


def test_boxes_share_the_width_within_one_pixel():
    edges = box_edges(1000, 12)
    assert edges[0] == 0 and edges[-1] == 1000
    widths = [b - a for a, b in zip(edges, edges[1:])]
    assert max(widths) - min(widths) <= 1


def test_default_layout_spacing_follows_box_size():
    lay = layout(600, 400, 12, 15, 15, 15, 1)
    assert lay.band_height == 45 and lay.canvas_height == 445
    first, last = lay.patches[0], lay.patches[-1]
    assert first.x == 1 and first.y == 16 and first.height == 13  # inside the 1px frame
    assert last.x + last.width == 599


def test_outline_dividers_are_the_outline_width():
    lay = layout(120, 10, 4, 20, 0, 0, 2)
    gaps = [b.x - (a.x + a.width) for a, b in zip(lay.patches, lay.patches[1:])]
    assert gaps == [2, 2, 2]
    assert lay.patches[0].x == 2 and lay.patches[-1].x + lay.patches[-1].width == 118


def test_outline_is_thinned_to_leave_room_for_the_patches():
    lay = layout(40, 10, 40, 15, 0, 0, 5)  # 1px-wide boxes: no room for any outline
    assert lay.outline == 0
    assert all(p.width >= 1 for p in lay.patches)


def test_no_outline():
    lay = layout(100, 10, 2, 10, 0, 0, 0)
    assert lay.patches == [Rect(0, 0, 50, 10), Rect(50, 0, 50, 10)]


def test_too_narrow_image_is_refused():
    with pytest.raises(ValueError, match="too narrow"):
        layout(10, 10, 12, 15, 15, 15, 1)


def test_band_pixels():
    lay = layout(4, 1, 2, 3, 1, 2, 0)  # 1 gap row, 3 strip rows, 2 margin rows
    px = band_pixels(lay, 2, (128, 128, 128))
    rows = [px[i * 12:(i + 1) * 12] for i in range(lay.band_height)]
    assert len(px) == 4 * 3 * 6
    assert rows[0] == bytes(12) and rows[4] == bytes(12) and rows[5] == bytes(12)
    assert rows[2] == bytes([255] * 6 + [0] * 6)  # white box, black box


def test_band_pixels_outline():
    lay = layout(9, 1, 2, 3, 0, 0, 1)
    px = band_pixels(lay, 2, (128, 0, 0))
    row = lambda i: [px[i * 27 + x * 3] for x in range(9)]  # red channel  # noqa: E731
    assert row(0) == [128] * 9                       # top frame
    assert row(1) == [128, 255, 255, 255, 255, 128, 0, 0, 128]  # frame, white, divider at 5, black
    assert row(2) == [128] * 9                       # bottom frame


def test_labels():
    assert label_texts(100) == ["100%", "100"]
    assert label_texts(100 / 11) == ["9%", "9"]
    assert label_size(15) == 6 and label_size(50) == 20 and label_size(1) == 1
    assert not label_is_light(0) and label_is_light(100)
