# Plan: Animation Rendering Overhaul for High-Fidelity SVG

## Objective
The goal is to achieve high-fidelity animations with crisp borders and improved anti-aliasing by transitioning to the `resvg-python` engine, implementing a supersampling pipeline, and adding native support for modern formats like WebP and APNG.

## Architectural Impact
- **Rendering Engine:** Transition from `CairoSVG` to `resvg-py` for superior SVG spec compliance.
- **Unified Quality Control:** Introduction of a `quality` setting in the `Canvas` class.
- **Supersampling Pipeline:** Implementation of a "Render-High-Res, Downscale-to-Target" workflow using `Pillow`'s Lanczos filter.
- **Modern Format Support:** Support for 8-bit alpha transparency via WebP and APNG.

## File Operations

### Modified Files
- `pyproject.toml`: Add `resvg-py` and `Pillow` to dependencies.
- `src/tesserax/canvas.py`:
  - Add `quality` parameter to `Canvas.__init__`.
  - Update `save()` to support `resvg`, WebP/APNG, and supersampling.
  - Inject rendering hints into SVG output.
- `src/tesserax/animation.py`:
  - Update `Scene.capture()` and `Scene.save()` to use the new supersampling pipeline and modern formats.

## Step-by-Step Execution
1.  **Dependency Update:** Add `resvg-py` and `Pillow` to the `export` optional dependencies in `pyproject.toml`.
2.  **Canvas Quality Settings:** Implement a `quality` parameter in `Canvas` that controls an internal `_render_scale` (1x for draft, 2x for standard, 4x for retina).
3.  **Supersampling Pipeline:** In `Scene.capture()`, render the SVG at the higher scale using `resvg-py` and then downscale to the target dimensions using `Pillow`'s `LANCZOS` filter before storing the frame.
4.  **Modern Formats:** Update `save()` methods in both `Canvas` and `Animation`/`Scene` to handle `.webp` and `.apng` extensions, leveraging `imageio` and `resvg-py`.
5.  **GIF Optimization:** Ensure the GIF output uses the supersampled frames, which will significantly reduce the "bolding" effect caused by 1-bit transparency matting.

## Testing Strategy
- **Fidelity Comparison:** Compare "draft" vs "retina" outputs to verify reduced aliasing.
- **Format Verification:** Ensure valid WebP and APNG files are generated and playable in browsers.
- **Regression Testing:** Run existing test suites to ensure animation logic remains intact.
