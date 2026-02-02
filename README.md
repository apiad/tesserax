# Tesserax: A Lightweight SVG Rendering Library

Tesserax is a modern Python 3.12 library designed for programmatic SVG generation with a focus on ease of use, layout management, and flexible geometric primitives. It is particularly well-suited for visualizing data structures, algorithms, and technical diagrams.

> [**Read the full documentation**](https://apiad.github.io/tesserax).

## Key Features

* **Declarative Layouts**: Effortlessly arrange shapes in `Row` or `Column` containers with automatic alignment and spacing.
* **Anchor System**: Connect shapes using semantic anchors like `top`, `bottom`, `left`, `right`, and `center`.
* **Context Manager Support**: Use `with` statements to group shapes naturally within the code.
* **Smart Canvas**: Automatically fit the canvas viewport to the content with adjustable padding.
* **Rich Primitives**: Includes `Rect`, `Square`, `Circle`, `Ellipse`, `Line`, `Arrow`, and `Path`.

## Installation

Tesserax has zero dependencies (literally). It's 100% pure Python, and can be easily installed with `pip`:

```bash
pip install tesserax
```

Or if you're one of the cool kids, using `uv`:

```bash
uv add tesserax
```

If you want support for saving PNG files, install with the `export` extra:

```bash
pip install tesserax[export]
```

## Quick Start

The following example demonstrates how to create two shapes in a row and connect them with an arrow using the anchor system.

```python
from tesserax import Canvas, Rect, Arrow, Circle
from tesserax.layout import Row

# Initialize a canvas
with Canvas() as canvas:
    # Arrange a circle and a rectangle in a row with a 50px gap
    with Row(gap=50):
        circle = Circle(30, fill="#fee")
        rect = Rect(100, 60, fill="#eef")

    # Draw an arrow between the two shapes using anchors
    # .dx() provides a small offset for better visual spacing
    Arrow(
        circle.anchor("right").dx(5),
        rect.anchor("left").dx(-5)
    )

# Fit the viewport to the shapes and render
canvas.fit(padding=10).display()
```

The `display()` method in the `Canvas` class is an IPython/Jupyter/Quarto compatible  shortcut to automatically include the rendered SVG (in all its beautiful vectorial glory) directly in a notebook. But you can also use `Canvas.save()` to generate a plain old, boring SVG file on this, and `str(canvas)` to get the actual SVG code as a plain string.

## Core Components

Tesserax comes with all basic components you need to draw the spectrum of SVG shapes.
All shapes support standard SVG attributes like `stroke` and `fill`.

* **Rect & Square**: Defined by width/height or a single size.
* **Circle & Ellipse**: Defined by radii.
* **Groups**: For grouping shapes and applying transforms to them as a single shape.
* **Arrow**: A specialized line that automatically includes an arrowhead marker.
* **Path**: Supports a fluent API for complex paths using `move_to`, `line_to`, `cubic_to`, and `close`.

### Layouts

Layouts are a unique feature of Tesserax to automate the positioning of child elements. We currently have three layouts, but these are very easy to extend:

* **Row**: Aligns shapes horizontally. Baselines can be set to `start`, `middle`, or `end`.
* **Column**: Aligns shapes vertically with `start`, `middle`, or `end` alignment.
* **HierarchicalLayout**: Useful for drawing trees, DAGs, automata, etc.
* **ForceLayout**: Typically used to draw arbitrary graphs with a force-directed algorithm.

### Transforms

Every shape has a `Transform` object allowing for:

* **Translation**: `shape.translated(dx, dy)`.
* **Rotation**: `shape.rotated(degrees)`.
* **Scaling**: `shape.scaled(factor)`.

Groups of shapes also have their own transform, and this can be composed _ad-infinitum_ to create complex drawing.

## Why Tesserax?

In the Python ecosystem, there is a clear divide between **data visualization** (plotting numbers) and **diagrammatic representation** (drawing concepts). Tesserax is built for the latter.

It is designed for researchers, educators, and authors who need the geometric precision of a professional drafting tool combined with the power of a modern programming language.

### Tesserax vs. The Alternatives

#### Precision over Statistics

Libraries like **Matplotlib**, **Seaborn**, or **Altair** are designed to map data points to visual encodings (bars, lines, scatter points).

**The Difference**: Tesserax does not compete with these libraries because it does not render data graphs. You wouldn't use Tesserax to plot a CSV. Instead, Tesserax is for "the rest" of the figures in a paper: the schematics, the geometric proofs, the architectural diagrams, and the algorithmic walkthroughs where exact spatial relationships convey the meaning.

#### Control over Constraints

**Mermaid** and **Graphviz** are excellent for quickly rendering flowcharts using "black-box" layout engines.

**The Difference**: These tools sacrifice control for convenience. If you need an arrow to point exactly at the tangent of a rotated ellipse, or a shape to be sized exactly according to a geometric ratio, Mermaid cannot help you. Tesserax is for **Scientific Drawing**—providing the low-level primitives needed for total layout authority.

#### The "TikZ for Python" Philosophy

**TikZ** is the industry standard for academic figures, but it requires learning a specialized, often cryptic macro language.

**The Difference**: Tesserax brings the "low-level, total-control" philosophy of TikZ into **Python 3.12**. You get coordinate-invariant precision and semantic anchoring while using Python’s loops, logic, and types. We are building from the bottom up: starting with geometric atoms and moving toward high-level scientific abstractions (like automated neural network architectures or commutative diagrams) that maintain the ability to "drop down" and tweak a single pixel.

### The SVG Advantage

While TikZ is the gold standard for LaTeX-based PDF generation, it belongs to a "print-first" era. Tesserax leverages **SVG (Scalable Vector Graphics)** as its native format, offering a portability that TikZ cannot match without significant friction.

* **Native Web Rendering**: Tesserax figures are native SVGs. They render instantly in any browser, remain crisp at any zoom level, and can be embedded directly into HTML or Markdown (via Quarto) without conversion.
* **WYSIWYG Portability**: Converting TikZ to SVG for blog posts or online journals often results in broken fonts or misaligned elements. Because Tesserax *starts* with SVG, what you see in your development notebook is exactly what appears in your final PDF and your website.
* **Accessibility & Interaction**: Unlike static PDFs, Tesserax SVGs can include metadata and ARIA labels for screen readers. Since they are part of the DOM, they can also be styled with CSS or even animated for interactive educational content.
* **Perfect Print**: SVG is fully convertible to high-quality, vector-perfect PDF, meeting the highest standards for academic journals and book publishing.

## Contribution

Tesserax is free as in both free beer and free speech. License is MIT.

Contributions are always welcomed! Fork, clone, and submit a pull request.
