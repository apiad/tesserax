# Changelog

All notable changes to this project will be documented in this file.

## [0.11.0] - 2026-03-03
### Added
- Integrated the Gemini CLI framework for advanced AI-driven repository management.
- Overhauled the animation rendering system with a new high-fidelity pipeline.
- Added a `quality` parameter to `Canvas` supporting `draft`, `standard`, and `retina` resolutions.
- Introduced supersampling (render-high, downscale-low using Lanczos filtering) for crisp raster edges.
- Added native support for modern animated formats: **WebP** and **APNG** (addressing GIF fidelity limitations).
- Integrated `resvg-py` as the primary high-performance SVG-to-raster engine.
- Added declarative charting module documentation and gallery.

### Fixed
- Resolved multiple linting issues including unused imports and ambiguous variable names.
- Fixed a critical `AttributeError` in `Chart.transition` relating to `LinearScale` properties.
- Updated `Rect` and `Circle` constructors to properly handle `opacity` parameters.
- Improved explicit re-exports in the core package for better IDE/tooling compatibility.

## [0.10.1] - 2026-02-21
