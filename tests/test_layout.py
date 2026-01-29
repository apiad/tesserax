from tesserax.base import Rect
from tesserax.layout import Row, Column


def test_row_layout_spacing() -> None:
    """Verifies that Row correctly positions shapes with a gap."""
    r1 = Rect(10, 10)
    r2 = Rect(10, 10)

    # Arrange two 10x10 rects with a 5px gap
    Row([r1, r2], gap=5)

    # r1 should be at x=0
    # r2 should be at x = width(r1) + gap = 15
    assert r1.transform.tx == 0
    assert r2.transform.tx == 15


def test_column_alignment() -> None:
    """Verifies that Column correctly aligns shapes of different widths."""
    r1 = Rect(20, 10)
    r2 = Rect(10, 10)

    # Align to the 'end' (right side)
    Column([r1, r2], align="end")

    # r1 is max width (20), so tx=0
    # r2 is width 10, needs to move right by 10 to align 'end'
    assert r1.transform.tx == 0
    assert r2.transform.tx == 10
