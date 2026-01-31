# Tesserax: A Lightweight SVG Rendering Library

Tesserax is a modern Python 3.12 library designed for programmatic SVG generation with a focus on ease of use, layout management, and flexible geometric primitives. It is particularly well-suited for visualizing data structures, algorithms, and technical diagrams.

## Key Features

* **Declarative Layouts**: Effortlessly arrange shapes in `Row` or `Column` containers with automatic alignment and spacing.
* **Anchor System**: Connect shapes using semantic anchors like `top`, `bottom`, `left`, `right`, and `center`.
* **Context Manager Support**: Use `with` statements to group shapes naturally within the code.
* **Smart Canvas**: Automatically fit the canvas viewport to the content with adjustable padding.
* **Rich Primitives**: Includes `Rect`, `Square`, `Circle`, `Ellipse`, `Line`, `Arrow`, and `Path`.

## Installation

```bash
pip install tesserax
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
        circle = Circle(20, fill="lightblue")
        rect = Rect(40, 40, fill="lightgrey")

    # Draw an arrow between the two shapes using anchors
    # .dx() provides a small offset for better visual spacing
    Arrow(
        circle.anchor("right").dx(5),
        rect.anchor("left").dx(-5)
    )

# Fit the viewport to the shapes and save
canvas.fit(padding=10).save("example.svg")
```

## Core Components

### 1. Primitives

All shapes support standard SVG attributes like `stroke` and `fill`.

* **Rect & Square**: Defined by width/height or a single size.
* **Circle & Ellipse**: Defined by radii.
* **Arrow**: A specialized line that automatically includes an arrowhead marker.
* **Path**: Supports a fluent API for complex paths using `move_to`, `line_to`, `cubic_to`, and `close`.

### 2. Layouts

Layouts automate the positioning of child elements:

* **Row**: Aligns shapes horizontally. Baselines can be set to `start`, `middle`, or `end`.
* **Column**: Aligns shapes vertically with `start`, `middle`, or `end` alignment.

### 3. Transforms

Every shape has a `Transform` object allowing for:

* **Translation**: `shape.translated(dx, dy)`.
* **Rotation**: `shape.rotated(degrees)`.
* **Scaling**: `shape.scaled(factor)`.

## Developer Information

Tesserax is built with modern Python 3.12 features, including:

* **Fully Typed**: Comprehensive type hinting for better IDE support and safety.
* **Deep Integration**: Utilizes `dataclasses` for points and transforms and `abc` for extensible shape definitions.
