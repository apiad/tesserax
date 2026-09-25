# tesserax

A pure-Python SVG generator for scientific diagrams, charts and technical
illustrations. Shapes, layouts, anchors, a keyframe animation system and a
deterministic physics engine compose into a `Canvas` whose `str()` is an SVG
document. Zero runtime dependencies; the `export` extra adds PNG/PDF.

It is for someone who wants a figure to be *computed* rather than drawn: a diagram
whose positions come from the data or the algorithm it illustrates, in a document or
a notebook that regenerates it on every build. If you want to draw by hand, use a
vector editor.

This file changes when the goals change. Nothing in it should be made false by a
commit that adds code or content.

## What done means

A change is done when `make all` passes: `ruff format`, `ruff check`, and the test
suite with coverage over `src/tesserax`. A new primitive, layout or mark ships with
tests. A change that alters rendered output ships with the `examples/` or `docs/`
page that shows it, because the ground truth of a visual artifact includes the
visual: render it and look at it.

The public API is what `src/tesserax/__init__.py` re-exports. Anything else is
internal and may move.

## Where everything lives

| tier | holds |
|---|---|
| `AGENTS.md` | this file: what tesserax is, what done means, where things live |
| `README.md` | the user-facing tour and quick start |
| `docs/*.qmd` | the rendered documentation, one page per subsystem |
| `know-how/*.md` | one procedure per job, with its traps |
| `makefile` | every mechanical check |
| module docstrings, `CHANGELOG.md`, git | everything else |

`TASKS.md` holds the roadmap. `GEMINI.md` holds harness-specific instructions for
the Gemini CLI and says nothing about this repo.

## Working here

```bash
make all                              # format, lint, test — the gate
make test                             # pytest with coverage
make lint                             # ruff, plus `rift check` if rift is installed
grep -m1 -H '^when:' know-how/*.md    # the know-how menu
```

`.rift.yaml` holds the checks on these docs, at `severity: warning`, so they report
without failing the build. Each rule carries its reason in a comment above it.

Read the know-how doc whose `when:` matches the job before starting.
