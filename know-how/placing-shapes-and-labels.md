---
date: 2026-09-25
type: know-how
when: a figure renders at 1000×1000 instead of fitting its content, a shape you added is invisible, a label lands in the wrong place, or content sits against one edge of the canvas with dead space opposite
---

# Placing shapes and labels

The traps below are ordered by how often they bite. Each one costs a render cycle to
find and a second to fix.

## `fit()` goes outside the `with`

`Canvas.fit()` measures the shapes that have been added. Inside the context manager
nothing has been committed yet, so it silently does nothing and the document ships
at the default `width="1000" height="1000"`.

```python
with Canvas() as canvas:
    Rect(100, 60, stroke=Colors.Black)
canvas.fit(12)            # here, not inside
svg = str(canvas)
```

The symptom is a figure that renders enormous or that a layout engine scales down to
a postage stamp.

## A colour with no alpha is invisible

`Color(r, g, b, a)` defaults `a=0.0`. `Color(255, 0, 0)` is fully transparent red,
which renders as nothing at all and looks like the shape was never added.

Use `Colors.<Name>` or `tesserax.color.hex("#0891b2")`, both of which set alpha to 1,
and reach for `.transparent(0.15)` when you actually want a wash. The shape
constructors have the same default on `fill=`, which is why a `Rect` shows only its
stroke unless you pass a fill.

## `move_to` anchors at the centre

`Shape.move_to(target, anchor="center")`. Laying out a grid of cells by their
top-left corner needs `anchor="topleft"` explicitly, otherwise every cell is offset
by half its size and the grid looks half a cell out of register. The anchor names are
`top`, `bottom`, `left`, `right`, `center`, `topleft`, `topright`, `bottomleft`,
`bottomright`.

## Uniform scaling leaves dead space on one axis

A hand-rolled mapping from data coordinates to drawing coordinates has to scale both
axes by the same factor or the figure lies about angles and distances. `min(sx, sy)`
does that, and then the content fills one axis and sits against one edge of the
other. Centre it by distributing the slack:

```python
self.escala = min((ancho - 2 * margen) / dx, (alto - 2 * margen) / dy)
self.ox = (ancho - dx * self.escala) / 2
self.oy = (alto - dy * self.escala) / 2
```

The worked example is `Marco` in `repos/algos/Lectures/2026/figuras.py`.

## SVG y grows downward

Data with y increasing upward has to be flipped on the way in, and every label
offset written afterwards reads inverted. Decide the convention once, write it in the
module docstring, and put the flip in one helper rather than at each call site.

A consequence worth naming: a "rank in the y-order" is the reverse of the drawing
order, so sorting for a figure that shows ranks is `key=lambda i: -pts[i][1]`.

## A lambda closes over the variable, not its value

```python
lado = d2 ** 0.5 / 2
celda = lambda q: (int(q[0] // lado), int(q[1] // lado))
...
lado = nuevo_lado          # `celda` now uses the new value, no redefinition needed
```

This is usually what you want when a figure tracks a changing scale, and it is a bug
when you expected the old one. Redefining `celda` after every change is redundant.

## `Text(anchor=…)` does not align anything

`Text(..., anchor="end")` emits `text-anchor="end"`, and tesserax compensates the
group's `translate` for it, so the text's **bounds are identical** whatever the
anchor — measured: `end`, `start` and `middle` all give `x: 58.00 .. 142.00` for the
same string. `move_to(point)` then centres that box on the point. The net effect is
that `Text`'s own anchor is a no-op for positioning: every label is centred.

With a short label (`10⁰`, `×5`) the error is a few pixels and nobody notices. With a
long one it is half the string's width, and the label lands on top of the thing it
names.

The anchor that *does* align is `move_to`'s, which is a box anchor:

```python
_ANCHOR = {"middle": "center", "start": "left", "end": "right"}

def label(text, xy, anchor="middle", **kw):
    return Text(text, anchor="middle", **kw).move_to(xy, anchor=_ANCHOR[anchor])
```

With that, `end` ends the text at the point, `start` begins it there. Found by
conferencia-primos on 2026-09-25 after a legend sat on its own bar; the same bug was
live in two of the DAA figures and had been papered over by nudging coordinates,
which is what a miscentred label looks like from the outside.

## Labels collide, and only the render shows it

There is no collision detection. Two `Text` at nearby anchors overlap silently, and a
long label placed at a short segment's midpoint lands somewhere else entirely. For a
label whose natural position is crowded, offset it and draw a thin leader line back
to what it names:

```python
etq = Point(c.x + 26, c.y - 16)
Line(c, etq, stroke=color.transparent(0.45), width=0.7)
_txt(nombre, Point(etq.x, etq.y - 6), color=color)
```

Iterate on a contact sheet — one throwaway document that prints every figure in
sequence — rather than on the real document. Fixing collisions is most of the work
and it wants a three-second loop.
