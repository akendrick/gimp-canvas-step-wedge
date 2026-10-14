# Canvas Step Wedge (GIMP 3 plugin)

[![tests](https://github.com/akendrick/gimp-canvas-step-wedge/actions/workflows/tests.yml/badge.svg)](https://github.com/akendrick/gimp-canvas-step-wedge/actions/workflows/tests.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Grows the canvas and adds a gray step wedge along the bottom of the image:
**Colors → Canvas Step Wedge...**

```
+-------------------------------------+
|                                     |
|               image                 |  unchanged
|                                     |
+-------------------------------------+
|  gap (black)                        |
| +-----+-----+-----+-----+-----+---+ |
| | 0%  | 9%  | 18% | 27% | ... |100| |  boxes share the full width
| +-----+-----+-----+-----+-----+---+ |
|  bottom margin (black)              |
+-------------------------------------+
```

The canvas is extended downward. The image layers are not changed, and the
new black band, with the wedge drawn on it, goes on its own **Step Wedge**
layer. The whole thing is one undo step.

## Options

| Option | Meaning |
|---|---|
| **Steps** | Number of boxes, 2–40 (default 12). Evenly spaced in ink %: step 1 is 0% (white), the last is 100% (black). 12 steps are about 9.1% apart; 11 steps give exact 10% steps, and 21 give exact 5% steps. Grays are standard 8-bit sRGB values, so 50% is gray 128. |
| **Box size (px)** | Height of the boxes (default 15). The boxes always share the full image width, differing by at most 1px when it doesn't divide evenly. |
| **Spacing = box size** | On by default: the gap above the wedge and the margin below it both equal the box size, so the wedge never touches the image or the canvas edge. Turn it off to set them yourself. |
| **Gap (px)** | Black space between the bottom of the image and the wedge. |
| **Bottom margin (px)** | Black space below the wedge. |
| **Outline colour** | Colour of the frame around the wedge and the dividers between boxes (default 50% gray, so both the white and the black box have a visible edge). |
| **Outline width (px)** | Default 1. Set it to 0 for no outline. If the boxes are too small for the width you ask for, it is thinned so every box keeps at least 1px of gray. |
| **Labels** | On by default. Each box's ink % is printed inside it at about 40% of the box height, in white on dark boxes and black on light ones (as in ChartThrob). In a narrow box "100%" becomes "100"; if a label still doesn't fit it is left off and you're told. |

At the default 15px box the labels are only 6px tall, which is fine on
screen but too small to read in print. Use a larger box size (e.g. 40–60px)
for printed wedges.

Works on RGB and grayscale images (convert indexed images with **Image →
Mode → RGB** first). On a grayscale image a coloured outline is converted to
its gray equivalent.

## Install

Needs **GIMP 3.0 or newer**. It was developed and tested only on GIMP 3.2.4
on macOS. It uses only the Python that ships with GIMP.

Download `canvas-step-wedge-<version>.zip` from the
[latest release](https://github.com/akendrick/gimp-canvas-step-wedge/releases/latest)
and unzip it.

**macOS and Linux:** from the unzipped folder run `./scripts/install.sh`, then
restart GIMP. `./scripts/install.sh --uninstall` removes it.

**By hand (any OS, including Windows):** copy the whole `canvas-step-wedge`
folder into your GIMP plug-ins folder, which is listed in **Edit →
Preferences → Folders → Plug-ins**. Typical locations:

| OS | Plug-ins folder |
|---|---|
| macOS | `~/Library/Application Support/GIMP/3.x/plug-ins/` |
| Linux | `~/.config/GIMP/3.x/plug-ins/` |
| Windows | `%APPDATA%\GIMP\3.x\plug-ins\` |

On macOS and Linux, then run
`chmod +x canvas-step-wedge/canvas-step-wedge.py`. Restart GIMP.

## Development

```bash
scripts/install.sh --link       # symlink the working copy into GIMP
python -m pytest tests          # layout and pixel maths, no GIMP needed
scripts/run_integration.sh      # real canvas/pixel checks in headless GIMP
scripts/build_release.sh        # build dist/canvas-step-wedge-<version>.zip
```

Note: GIMP 3.2.4 loses colour argument defaults after a plugin registers.
They arrive as black, and GIMP's own Foggify plugin shows the same thing. So
on its first run the plugin replaces a black outline colour with the intended
50% gray, once; see `_apply_first_run_defaults()`.

## License

[MIT](LICENSE) © 2026 akendrick. Issues and pull requests are welcome at
<https://github.com/akendrick/gimp-canvas-step-wedge>.
