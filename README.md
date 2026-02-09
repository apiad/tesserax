# Tesserax: A Lightweight SVG Rendering Library

Tesserax is a modern Python 3.12 library designed for programmatic SVG generation with a focus on ease of use, layout management, and flexible geometric primitives. It is particularly well-suited for visualizing data structures, algorithms, and technical diagrams.

Beyond static diagrams, Tesserax now includes a **deterministic physics engine** and a **cinematic animation system**, making it a complete toolkit for scientific communication.

## Key Features

* **Rich Primitives**: Includes standard shapes (`Rect`, `Circle`) plus advanced procedural geometry like `Polyline` with smoothing and subdivision support.
* **Declarative Layouts**: Effortlessly arrange shapes in `Row`, `Column`, or `Grid` containers, or use algorithmic layouts like `Tree` and `Force`.
* **Smart Canvas**: Automatically fit the canvas viewport to the content with adjustable padding.
* **Anchor System**: Connect shapes using semantic anchors like `top`, `bottom`, `left`, `right`, and `center`.
* **Cinematic Animations**: Create complex motion graphics using a declarative, code-first API that supports keyframes, morphing, and warping.
* **Physics Simulation**: Bake high-precision rigid body simulations directly into your animations using the built-in `World` and `Body` primitives.

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

The following example demonstrates how to create a simple logo and highlights the most basic functionality of **Tesserax**.

```python
import math
from tesserax import Canvas, Square, Circle, Text, Polyline, Point, Group
from tesserax.layout import RowLayout

with Canvas() as canvas:
    # We use a top-level row layout
    with RowLayout(align="end") as logo:
        # Left Block
        r = Square(30, fill="green", stroke="none")

        # Center Text
        t = Text(
            "tesserax",
            size=48,
            font="sans-serif",
            fill="navyblue",
            anchor="middle",
            baseline="bottom",
        )

        # Right Circle
        c = Circle(20, fill="red", stroke="none")

    # Create the "Squiggly" Underline
    Polyline(
        [
            r.anchor("bottom").dy(10),
            c.anchor("bottom").dy(10),
        ],
        smoothness=1.0,
        stroke="black",
        marker_end="arrow",
    ).subdivide(5).apply(
        lambda p: p.dy(math.sin((p.x / logo.bounds().width * 20 + 5)) * 5)
    )

# Use fit() to frame the logo perfectly
canvas.fit(padding=10).display()
```

![](example.svg)


The `display()` method in the `Canvas` class is an IPython/Jupyter/Quarto compatible  shortcut to automatically include the rendered SVG (in all its beautiful vectorial glory) directly in a notebook. But you can also use `Canvas.save()` to generate a plain old, boring SVG file on this, and `str(canvas)` to get the actual SVG code as a plain string.

## Deep Dive: Beyond the Basics

Tesserax scales from simple scripts to complex simulations. Here is an overview of the advanced capabilities available.

### Geometric Primitives & Procedural Shapes

Tesserax provides a robust suite of atoms like `Rect`, `Circle`, `Ellipse`, and `Arrow`.

* **Polyline API**: The `Polyline` class supports `smoothing` (Bezier interpolation), `subdivision` (increasing resolution), and `simplification` (reducing vertices).
* **Path API**: For low-level control, use the `Path` class with standard SVG commands (`move_to`, `cubic_to`, `arc`).

### The Layout Engine

Forget manual pixel pushing. Tesserax offers a hierarchy of layout engines:

* **Standard Layouts**: `Row`, `Column`, and `Grid` automatically position elements based on gaps and alignment.
* **Hierarchical Layout**: Automatically draws Trees and Directed Acyclic Graphs (DAGs).
* **Force-Directed Layout**: Simulates physical forces to arrange arbitrary network graphs.

### Cinematic Animation

The animation system is designed for **storytelling**, not just movement.

* **Declarative API**: Compose animations using `parallel (|)` and `sequential (+)` operators.
* **Keyframes**: Define complex multi-stage timelines for any property (position, rotation, color).
* **Morphing & Warping**: Smoothly transform one shape into another or apply wave functions to geometry.

### Physics Engine

Tesserax includes a **baked physics engine** for high-precision rigid body simulations.

* **Deterministic**: Define a `World`, add `Body` objects, and apply `Field`s like Gravity or Drag.
* **Baked Playback**: The simulation is calculated upfront and converted into standard keyframes, allowing high-resolution physics (e.g., 1000 steps/sec) to play back smoothly at any framerate.
* **Interoperable**: Physics animations can be mixed and matched with standard tweens.

## Why Tesserax?

In the Python ecosystem, there is a clear divide between **data visualization** (plotting numbers) and **diagrammatic representation** (drawing concepts).

Tesserax is for **Scientific Drawing**---providing the low-level primitives needed for total layout authority.

Libraries like **Matplotlib** map data to charts. Tesserax maps concepts to geometry. Use Tesserax for the schematics, geometric proofs, and algorithmic walkthroughs in your papers.

**TikZ** is the industry standard for academic figures but uses a cryptic macro language. Tesserax brings that same "total-control" philosophy to **Python 3.12**, giving you coordinate-invariant precision with the power of Python's loops and types.

## Contribution

Tesserax is free as in both free beer and free speech. License is MIT.

Contributions are always welcomed! Fork, clone, and submit a pull request.
