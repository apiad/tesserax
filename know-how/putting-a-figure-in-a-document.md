---
date: 2026-09-25
type: know-how
when: embedding a tesserax figure in a scriptorium document, a Quarto page or a notebook; the SVG shows up as literal text; or `import tesserax` fails under an externally-managed Python
---

# Putting a figure in a document

`str(canvas)` is a complete SVG document. Every integration below is a way of getting
that string to the right place; there is no figure protocol to implement.

## scriptorium

A code block's stdout is spliced into the document and re-parsed as Markdown, and raw
HTML passes through verbatim as one atomic unit. So a block that prints the SVG is a
figure.

````markdown
---
execute:
  interpreters:
    python: ["uv", "run", "--quiet", "--with", "tesserax", "python", "-"]
---

```{python echo=false output=asis}
from tesserax import Canvas, Rect, Colors
with Canvas() as canvas:
    Rect(120, 70, stroke=Colors.Black)
canvas.fit(12)
print(f'<figure id="fig-caja">{canvas}<figcaption>A box.</figcaption></figure>')
```
````

- **`output=asis`** is required. The default is `output=code`, which escapes stdout
  into a `<pre>` and prints the SVG source as literal text on the page. That is the
  symptom people report first.
- **`echo=false`** hides the drawing code, which is rarely what the reader wants.
- Wrapping in `<figure>` + `<figcaption>` lets CSS counters number the figures and
  resolve `@fig-` cross-references. No scriptorium theme numbers figures: `base`
  styles `figure` and `figcaption`, and `book`'s `a.ref-fig` renders the caption
  text plus a page number rather than a figure number. The counter rules to copy
  are in `repos/algos/know-how/ilustrando-una-conferencia.md`.

## Jupyter and Quarto

`Canvas` implements `_repr_svg_`, so returning the canvas as a cell's last expression
renders it inline with no extra call. `canvas.display()` does the same explicitly,
which is what every example in `docs/*.qmd` uses.

## Externally-managed Python (PEP 668)

On a distribution that marks the system interpreter externally managed, `pip install
tesserax` refuses and `--break-system-packages` is the wrong answer. `uv run --with
tesserax python -` resolves the package into a cached ephemeral environment;
measured startup with a warm cache is 0.13 s per invocation, which is cheap enough to
pay once per code block.

For a project that imports a local figure module as well, the document's working
directory is where the document lives, so `sys.path.insert(0, os.path.abspath(".."))`
reaches a sibling directory without an absolute path.

## Sizing in the page

The SVG carries the `width`/`height` that `fit()` computed, in user units that a
renderer treats as px. To let a wide figure shrink to the text column rather than
overflow it:

```css
figure svg { display: block; margin: 0 auto; max-width: 100%; height: auto; }
```

Without `display: block` the figure sits on the text baseline and the caption
alignment does not apply to it.

## Charts: the y axis starts at zero

`Chart` builds a `LinearScale` whose y domain is `(0, max)`. That is right for bars
and wrong for anything spanning orders of magnitude: a series from 0.004 to 3.0
collapses onto the axis. There is no log scale.

For a log-log plot, compute the decades and draw the axes with `Line`, `Polyline` and
`Text`. It is about forty lines and you control the tick labels. The worked example is
`grafica_log_log` in `repos/algos/Lectures/2026/figuras.py`.

`Chart` is the right tool when the x channel is categorical: `BandScale` distributes
the groups and `.encode(color=...)` picks distinct colours from the built-in palette.
