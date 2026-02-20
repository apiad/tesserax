import pytest
import math
from tesserax.color import Color, Colors, rgb, hls, hsv, hex, red, green, blue, gray


def test_color_init():
    c = Color(255, 128, 0, 1.0)
    assert c.r == 255
    assert c.g == 128
    assert c.b == 0
    assert c.a == 1.0
    assert str(c) == "rgba(255,128,0,1.0)"


def test_color_properties():
    c = Colors.Red  # rgb(255, 0, 0)
    assert c.lightness == 0.5
    assert c.hue == 0.0
    assert c.saturation == 1.0
    assert c.value == 1.0


def test_color_manipulation():
    c = Colors.Red
    c2 = c.transparent(0.5)
    assert c2.a == 0.5

    c3 = c.darker(0.5)
    assert c3.r == 127 or c3.r == 128

    c4 = c.lighter(0.5)
    assert c4.r == 255
    assert c4.g == 127 or c4.g == 128


def test_color_lerp():
    c1 = Colors.Black
    c2 = Colors.White
    mid = c1.lerp(c2, 0.5, space="rgb")
    assert mid.r == 127 or mid.r == 128
    assert mid.g == 127 or mid.g == 128
    assert mid.b == 127 or mid.b == 128


def test_color_spaces():
    # rgb to values
    r, g, b = rgb(Colors.Red)
    assert r == 1.0 and g == 0.0 and b == 0.0

    # values to color
    c = rgb(1.0, 0.0, 0.0)
    assert c == Colors.Red

    # hex
    assert hex(Colors.Red) == "#ff0000"
    assert hex("#ff0000") == Colors.Red
    assert hex("ff0000") == Colors.Red
    assert hex("#f00") == Colors.Red


def test_shorthands():
    # shade(0.5) returns the color itself
    assert red(0.5) == Colors.Red
    assert green(0.5) == Colors.Green
    assert blue(0.5) == Colors.Blue
    assert gray(0.5) == Colors.Gray


def test_colors_class():
    assert Colors.get("Red") == Colors.Red
    assert Colors.get("red") == Colors.Red
    assert Colors.get_name(Colors.Red) == "Red"

    with pytest.raises(ValueError):
        Colors.get("NonExistentColor")


def test_palettes():
    p = list(Colors.basic_palette())
    assert len(p) > 0
    assert Colors.Red in p

    p2 = list(Colors.palette("pink"))
    assert len(p2) > 0

    with pytest.raises(ValueError):
        Colors.palette("nonexistent")


def test_color_arithmetic():
    c1 = Color(100, 100, 100, 0.5)
    c2 = Color(50, 50, 50, 0.2)

    added = c1 + c2
    assert added.r == 150
    assert math.isclose(added.a, 0.7)

    subbed = c1 - c2
    assert subbed.r == 50

    mulled = c1 * 2
    assert mulled.r == 200


def test_color_advanced_manipulation():
    # Start with Blue
    c = Colors.Blue

    # Redshift it towards red (hue 0.0)
    rs = c.redshift(1.0)
    assert math.isclose(rs.hue, 0.0, abs_tol=1e-5)

    # Blueshift Red towards blue (hue 0.66...)
    c2 = Colors.Red
    bs = c2.blueshift(1.0)
    assert bs.hue > 0.6

    sat = Colors.Gray.saturated(1.0)
    assert sat.saturation == 1.0
