# SVG-to-GIF Conversion Implementation in Tesserax

This document provides a detailed technical analysis of the current SVG-to-GIF conversion process within the Tesserax codebase, focusing on library versions, rasterization settings, and assembly logic.

## 1. Library Versions and Dependencies

The core libraries used for SVG processing and animation assembly are specified in the `pyproject.toml` file under the `export` optional dependencies:

- **CairoSVG**: `>=2.8.2`
- **ImageIO**: `>=2.37.2` (includes the `[ffmpeg]` extra for video encoding support)

## 2. SVG to PNG Rasterization Process

The rasterization of SVG frames into PNG images occurs in the `Scene.capture` method within `src/tesserax/animation.py`.

### 2.1 Rasterization Settings
The implementation uses `cairosvg.svg2png` with the following parameters:
- **`bytestring`**: The SVG content is encoded as a UTF-8 byte string (`svg.encode("utf-8")`).
- **`background_color`**: Uses the `self.background` property of the `Scene` instance (which defaults to `"white"`).

### 2.2 DPI and Scaling
- **DPI**: There is no explicit `dpi` setting passed to `cairosvg.svg2png`. Consequently, CairoSVG uses its default resolution of **96 DPI**.
- **Scaling**: No `scale`, `output_width`, or `output_height` parameters are explicitly set. The resulting PNG dimensions are determined by the internal dimensions (width/height attributes or viewBox) defined in the SVG's root element.

## 3. GIF Assembly and Encoding

The assembly of PNG frames into a GIF file is handled by the `Scene.save` method.

### 3.1 Assembly Workflow
1. **Frame Collection**: Raw PNG byte strings are stored in `self._frames` during the capture phase.
2. **Decoding**: In `Scene.save`, these PNG bytes are read into memory using `imageio.imread(io.BytesIO(f))`, converting each frame into a NumPy array.
3. **Assembly**: The list of arrays is passed to `imageio.mimsave(dest, images, format="gif", **kwargs)`.

### 3.2 `imageio.mimsave` Default Behavior
- **Plugin**: By default, `imageio` (version 2.37.2+) prioritizes the **Pillow** plugin for GIF encoding. Although `imageio-ffmpeg` is a dependency, it is typically used for video formats (like `.mp4`) unless `plugin="ffmpeg"` or `plugin="pyav"` is explicitly requested.
- **FPS**: The frame rate is set via `kwargs["fps"] = self.fps`.
- **Looping**: For GIFs, `kwargs["loop"] = 0` is set, ensuring the animation loops infinitely.

### 3.3 Color Quantization and Encoding Settings
Since the Pillow plugin is used for GIF encoding:
- **Color Depth**: It uses a standard 8-bit (256-color) palette.
- **Quantization**: By default, Pillow uses the **Median Cut** algorithm to reduce the color space of the input frames.
- **Dithering**: Pillow typically applies **Floyd-Steinberg dithering** unless configured otherwise (which is not done in Tesserax).
- **Compression**: The output is compressed using the standard LZW algorithm for GIFs.

## 4. Intermediate Processing

Based on the inspection of `src/tesserax/animation.py`:

- **Resizing**: No resizing or scaling is performed on the images after rasterization and before GIF assembly.
- **Color Space Conversion**: No explicit color space conversions (e.g., RGB to Grayscale or custom ICC profiles) are applied.
- **Double Encoding**: There is a "double encoding" overhead where SVG is first encoded to PNG bytes, then decoded back to NumPy arrays, and finally re-encoded into the GIF format.
- **Processing Logic**: The frames are passed directly from `imageio.imread` to `imageio.mimsave` without any modification to the pixel data.

---

### Key Findings for Optimization
- The reliance on default 96 DPI might lead to low-resolution GIFs if the SVG dimensions are small.
- The use of the default Pillow quantizer (Median Cut) without custom palette generation can result in color banding or artifacts in complex animations.
- The double encoding (PNG to NumPy to GIF) introduces minor performance overhead but ensures that `imageio` works with standard pixel buffers.
