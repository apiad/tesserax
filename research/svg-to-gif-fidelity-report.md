# SVG to GIF Animation Fidelity Report

## Executive Summary
This report investigates the visual degradation—specifically the bolder, less crisp appearance of text and lines—when converting SVG animations to GIFs within the Tesserax library. The root cause of this fidelity loss is a combination of three factors: CairoSVG's reliance on sub-pixel anti-aliasing (which smears 1px lines across multiple pixels), the low default rasterization resolution (96 DPI), and the GIF format's inherent lack of an alpha channel (which forces semi-transparent anti-aliased edges to be matted against a solid background, creating a thickening effect). To resolve this, Tesserax can implement a supersampling workflow (rendering at a higher resolution and downscaling), migrate to a more modern rasterization engine like `resvg-python`, or adopt modern animation formats like WebP that natively support alpha transparency.

## Research Questions

### 1. How is the SVG-to-GIF conversion currently implemented in Tesserax?

**Overview of Findings:**
Tesserax uses CairoSVG (`>=2.8.2`) to rasterize SVG frames into PNGs at the default 96 DPI, with no explicit scaling. These PNGs are then decoded into NumPy arrays using ImageIO (`>=2.37.2`). Finally, `imageio.mimsave` (defaulting to the Pillow plugin for GIFs) assembles these frames into a GIF. There is no intermediate resizing or color space conversion, but there is a double-encoding step (SVG -> PNG -> raw pixels -> GIF). The GIF assembly relies on a global 256-color palette generated via the Median Cut algorithm with Floyd-Steinberg dithering.

**Detailed Research Asset:**
[question_1.md](svg-to-gif-fidelity/question_1.md)

#### 1.1: What are the specific settings (DPI, scaling) and library versions (CairoSVG, ImageIO) used during the SVG to PNG rasterization process?
- CairoSVG >= 2.8.2 and ImageIO >= 2.37.2.
- Frames are rasterized to PNG via `cairosvg.svg2png` using the default 96 DPI. No explicit scaling is applied.
- The default background color is white.

#### 1.2: How does `imageio.mimsave` assemble the PNG frames into a GIF, and what are its default color quantization settings?
- `imageio.mimsave` uses the Pillow plugin by default for GIFs.
- It employs a global 256-color palette generated via the Median Cut algorithm.
- Floyd-Steinberg dithering is used by default.

#### 1.3: Is there any intermediate processing of the frames (e.g., resizing, color space conversion) before GIF assembly?
- No explicit resizing or color conversion occurs.
- The pipeline involves decoding the PNG bytes into raw NumPy arrays before encoding them into the final GIF format.

### 2. Why do SVG paths and text appear bolder or thicker in the generated GIFs?

**Overview of Findings:**
The perception of bolder text and lines in the resulting GIFs is caused by a combination of Cairo's sub-pixel rendering approach, the GIF format's lack of true alpha transparency, and the low default DPI setting. CairoSVG does not snap paths to pixel boundaries as aggressively as modern browsers (like Skia), leading to "half-pixel" smearing where a 1px line spans two pixels. When the GIF is generated, these semi-transparent anti-aliased edge pixels are flattened against the white background because GIF only supports 1-bit transparency. This physically thickens the dark silhouette of lines and text. Finally, rasterizing at the default 96 DPI produces a low-resolution image where these aliasing artifacts are chunky and more visible on modern high-DPI displays.

**Detailed Research Asset:**
[question_2.md](svg-to-gif-fidelity/question_2.md)

#### 2.1: How does CairoSVG handle anti-aliasing and sub-pixel rendering compared to modern web browsers?
- CairoSVG (via Cairo) does not perform the same level of automatic pixel-snapping (hinting) as browser engines like Skia.
- This causes lines drawn on integer coordinates to be anti-aliased across adjacent pixels (the half-pixel problem), making them appear blurrier and thicker.

#### 2.2: How does the GIF format's lack of alpha channel (partial transparency) affect the perceived thickness of anti-aliased lines and text?
- GIF only supports 1-bit transparency (a pixel is either fully transparent or fully opaque).
- Anti-aliased edge pixels (which are semi-transparent grays) must be composited ("matted") against a solid background color (e.g., white) during conversion.
- This converts soft, transparent edges into solid, opaque pixels, widening the dark area and making paths look significantly bolder.

#### 2.3: Does the `dpi` scaling parameter in `cairosvg.svg2png` interact poorly with default line widths (`stroke-width`) or font weights when rasterizing?
- The default 96 DPI results in low-resolution rasterization.
- At 96 DPI, anti-aliasing artifacts take up a larger percentage of the stroke width compared to rendering at 2x or 3x DPI (like on a Retina screen), amplifying the bulky appearance.

### 3. What are the potential solutions or best practices to mitigate this?

**Overview of Findings:**
There are several strategies to mitigate the bolding effect. The most immediate fix is supersampling: rendering the SVG at a higher resolution (e.g., 2x or 4x scale) and downscaling the resulting raster frames using a high-quality filter (like Lanczos) before GIF assembly. Alternatively, switching the rendering engine from CairoSVG to `resvg-python` or a headless browser (Playwright) provides more accurate browser-like rendering. To bypass GIF's 1-bit transparency limitations entirely, Tesserax could support modern animated formats like APNG or WebP, which offer full 8-bit alpha channels. Finally, programmatic tweaks such as injecting `shape-rendering="geometricPrecision"` or slightly reducing `stroke-width` and `font-weight` prior to rasterization can help compensate for the GIF thickening effect.

**Detailed Research Asset:**
[question_3.md](svg-to-gif-fidelity/question_3.md)

#### 3.1: Can adjusting the rasterization resolution (e.g., higher DPI during `svg2png` and downscaling) improve crispness?
- Yes. Supersampling (rendering at 4x scale, then downsampling with a Lanczos filter) significantly improves anti-aliasing quality and reduces the chunky, bold appearance.

#### 3.2: Are there alternative pipelines (e.g., headless browsers like Playwright, or Resvg) that yield more accurate rasterization?
- `resvg-python` is a faster, more modern alternative to CairoSVG that handles edge cases better.
- Playwright (headless Chromium/WebKit) is the gold standard for visual fidelity as it uses actual browser rendering engines (Skia).

#### 3.3: Can we switch to or offer alternative animated formats (like APNG, WebP, or MP4) that support full alpha channels?
- APNG and WebP support full 8-bit alpha transparency and 24-bit color, eliminating the harsh matting artifacts of GIFs.
- MP4 (via `imageio-ffmpeg`) offers excellent compression for complex animations, though standard H.264 lacks alpha support.

#### 3.4: Are there specific SVG/CSS attributes (like `shape-rendering`) that can be injected to compensate?
- Injecting `shape-rendering="geometricPrecision"` and `text-rendering="optimizeLegibility"` can improve rendering intent.
- Programmatically "thinning" `stroke-width` or reducing `font-weight` (e.g., 700 to 600) right before rasterization can counter the GIF thickening effect.

## Conclusions
The visual discrepancy between native SVGs and generated GIFs in Tesserax is not a bug in the code, but an artifact of the rasterization and quantization pipeline. CairoSVG does not snap vectors to pixel grids as cleanly as modern browser engines. When these soft, anti-aliased paths are converted to a low-resolution (96 DPI) raster image and then subjected to GIF's 1-bit transparency limitations, the semi-transparent pixels on the edges of paths are forced into solid colors. This physically widens the dark silhouette of all strokes and text, resulting in the perceived "bolding" effect. The issue is exacerbated on high-DPI displays where the low-resolution artifacts become prominently visible.

## Recommendations

### Actionable Next Steps
1. **Implement Supersampling:** Modify `src/tesserax/animation.py` to optionally render frames via `cairosvg.svg2png` at 2x or 4x the target resolution (using the `scale` parameter), and then downsample the frames using Pillow's high-quality Lanczos filter before passing them to `imageio.mimsave`.
2. **Support Alternative Formats:** Add support for WebP or APNG output in the animation system. These formats support 8-bit alpha channels, which will instantly eliminate the matting/thickening artifacts inherent to GIF.
3. **Enhance Configuration:** Expose scaling and background color options directly in the `Animator.save()` or `Canvas.save()` APIs to give users control over the rasterization fidelity.

### Potential Follow-up Research
- **Engine Comparison:** Conduct a performance and fidelity benchmark comparing CairoSVG with `resvg-python` and headless Playwright to determine if Tesserax should deprecate CairoSVG for a more accurate rendering backend.
- **CSS Injection Optimization:** Investigate exactly how much `stroke-width` needs to be programmatically reduced to perfectly counter the GIF thickening effect for various font families and line weights.