# Test Suite for UsdLux

## Prerequisites

- Install Houdini
  - Apprentice editions will not work
  - Check RenderMan compatible versions:
    - RenderMan 26:
      - https://rmanwiki.pixar.com/display/RFH26/Installation+of+RenderMan+for+Houdini
      - > RenderMan for Houdini 26.0 supports: 20.0.653, 19.5.805, 19.0.720
      - > RenderMan for Houdini on Linux will only operate with the gcc9.3 houdini build.
  - Check Arnold compatible versions:
    - See below for download instructions, and check available builds
- Install RenderMan + RenderMan for Houdini
  - Register on pixar forums
    - https://renderman.pixar.com/forum/
  - Download:
    - https://renderman.pixar.com/install
- Install HtoA (Houdini to Arnold)
  - Purchase Arnold license, or sign up for free trial:
    - https://www.autodesk.com/products/arnold/overview
  - Download HtoA from [https://manage.autodesk.com/products/updates] (filter by "HtoA")

## Usage

### Automatically rendering all lights using hython
- Make sure the `bin` folder for houdini is on your `PATH`
- run `hython genhoudini.py`

### Manually rendering individual lights in Houdini GUI
- Open `luxtest.hip` in Houdini
- In the Solaris /stage pane, scroll down to the section corresponding to the
  lighting setup you wish to render:
  - distant
  - rect
  - sphere
  - disk
  - cylinder
  - dome
  - visible-rect
- Select the USD Render ROP corresponding to the renderer you wish to render
  - will be of format `render_{light}_{renderer}
  - ie, `render_rect_ris`
- In the parameters pane, click "Render to Disk"

## Renders repo

Result rendered images are available in a
[separate repo](https://github.com/pmolodo/luxtest_renders).  To add it to
this repo, first ensure "renders" subdir does not already exist, then from
the repo root, run:

```shell
git clone https://github.com/pmolodo/luxtest_renders renders
```