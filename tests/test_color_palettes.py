import pytest
from tesserax.color import Colors, Color


def test_all_palettes():
    # Test that all static palette methods work and return colors
    palette_names = Colors.palettes()
    for name in palette_names:
        p = list(Colors.palette(name))
        assert len(p) > 0
        assert all(isinstance(c, Color) for c in p)


def test_all_colors_generator():
    all_colors = list(Colors.all())
    assert len(all_colors) > 100  # Should be many colors
    assert all(isinstance(c, Color) for c in all_colors)


def test_specific_palettes():
    # Smoke tests for a few specific ones
    assert len(list(Colors.pink_palette())) > 0
    assert len(list(Colors.red_palette())) > 0
    assert len(list(Colors.orange_palette())) > 0
    assert len(list(Colors.yellow_palette())) > 0
    assert len(list(Colors.brown_palette())) > 0
    assert len(list(Colors.green_palette())) > 0
    assert len(list(Colors.cyan_palette())) > 0
    assert len(list(Colors.blue_palette())) > 0
    assert len(list(Colors.purple_palette())) > 0
    assert len(list(Colors.white_palette())) > 0
    assert len(list(Colors.black_palette())) > 0
    assert len(list(Colors.extra_palette())) > 0
