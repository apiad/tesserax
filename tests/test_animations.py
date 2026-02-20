import pytest
import math
from tesserax import Rect, Text, Polyline, Point, Colors, Circle
from tesserax.animation import (
    Animation,
    Sequence,
    Parallel,
    Transformed,
    Styled,
    Written,
    Morphed,
    NumericAnimation,
    KeyframeAnimation,
    Delayed,
    Wrapped,
    Scrambled,
    TrackAnimation,
    Following,
    ease_out,
    smooth,
)


class MockAnimation(Animation):
    def __init__(self, weight=1.0):
        super().__init__()
        self.weight(weight)
        self.updated_t = []

    def _update(self, t):
        self.updated_t.append(t)


def test_animation_basic():
    anim = MockAnimation()
    anim.begin()
    assert anim._started
    anim.update(0.5)
    assert anim.updated_t == [0.5]
    anim.finish()
    assert anim.updated_t == [0.5, 1.0]


def test_animation_fluent_api():
    anim = MockAnimation()
    anim.smoothed()
    assert anim.rate == smooth

    anim.weight(2.0)
    assert anim._weight == 2.0

    wrapped = anim.delayed(0.5)
    assert isinstance(wrapped, Animation)


def test_sequence():
    a1 = MockAnimation(weight=1.0)
    a2 = MockAnimation(weight=1.0)
    seq = Sequence(a1, a2)

    seq.begin()
    # At t=0.25, a1 should be at 0.5 (since it takes half the time)
    seq.update(0.25)
    assert a1.updated_t == [0.5]
    assert len(a2.updated_t) == 0

    # At t=0.75, a1 should be finished (1.0) and a2 at 0.5
    seq.update(0.75)
    assert a1.updated_t == [0.5, 1.0]
    assert a2.updated_t == [0.5]


def test_parallel():
    a1 = MockAnimation()
    a2 = MockAnimation()
    par = Parallel(a1, a2)

    par.begin()
    par.update(0.5)
    assert a1.updated_t == [0.5]
    assert a2.updated_t == [0.5]


def test_delayed_group():
    a1 = MockAnimation()
    a2 = MockAnimation()
    delay = Delayed(a1, a2, lag_ratio=0.5)
    delay.begin()

    delay.update(0.2)  # Only a1 active
    assert len(a1.updated_t) > 0
    assert len(a2.updated_t) == 0

    delay.update(0.5)  # Both active
    assert len(a1.updated_t) > 1
    assert len(a2.updated_t) > 0


def test_transformed_animation():
    r = Rect(10, 10)
    target = r.transform.copy().translate(100, 100)
    anim = Transformed(r, target)

    anim.begin()
    anim.update(0.5)
    assert r.transform.tx == 50
    assert r.transform.ty == 50
    anim.update(1.0)
    assert r.transform.tx == 100
    assert r.transform.ty == 100


def test_styled_animation():
    r = Rect(10, 10, fill=Colors.Black)
    anim = Styled(r, fill=Colors.White)

    anim.begin()
    anim.update(0.5)
    # Lerp between Black (0,0,0) and White (255,255,255)
    assert r.fill.r == 127 or r.fill.r == 128
    anim.update(1.0)
    assert r.fill == Colors.White


def test_written_animation():
    t = Text("Hello")
    anim = Written(t)

    anim.begin()
    anim.update(0.4)  # 2 chars
    assert t.content == "He"
    anim.update(1.0)
    assert t.content == "Hello"


def test_scrambled_animation():
    t = Text("Secret")
    anim = Scrambled(t, seed=42)
    anim.begin()
    anim.update(0.5)
    assert t.content.startswith("Sec")
    assert len(t.content) == 6
    assert t.content != "Secret"


def test_morphed_animation():
    p1 = Polyline([Point(0, 0), Point(10, 10)])
    target_pts = [Point(0, 0), Point(20, 20)]
    anim = Morphed(p1, target_pts)

    anim.begin()
    anim.update(0.5)
    assert p1.points[1] == Point(15, 15)
    anim.update(1.0)
    assert p1.points[1] == Point(20, 20)


def test_numeric_animation():
    class Obj:
        def __init__(self):
            self.val = 0.0

    o = Obj()
    anim = NumericAnimation(o, "val", 100.0)
    anim.begin()
    anim.update(0.5)
    assert o.val == 50.0


def test_keyframe_animation():
    r = Rect(10, 10)
    # Animate tx with easing
    anim = KeyframeAnimation(r, tx={0.5: (50, ease_out), 1.0: 200})

    anim.begin()
    # At t=0.25 (halfway to first keyframe)
    # Local t = 0.5. Eased t = 0.5 * (2 - 0.5) = 0.75
    # tx = 0 + (50 - 0) * 0.75 = 37.5
    anim.update(0.25)
    assert math.isclose(r.transform.tx, 37.5)


def test_track_animation():
    target = Rect(10, 10).translated(100, 100)
    follower = Circle(5)
    anim = TrackAnimation(follower, target)
    anim.begin()

    anim.update(0.5)  # Track doesn't care about t really, it snaps every update
    assert follower.transform.tx == 100
    assert follower.transform.ty == 100


def test_following_animation():
    class PathWithPointAt:
        def point_at(self, t):
            return Point(t * 100, 0)

    path = PathWithPointAt()
    shape = Circle(5)
    anim = Following(shape, path)
    anim.begin()

    anim.update(0.5)
    assert shape.transform.tx == 50.0


def test_easing_functions():
    from tesserax.animation import linear, smooth, ease_out, ease_in_out_cubic

    assert linear(0.5) == 0.5
    assert 0 < smooth(0.5) < 1
    assert 0 < ease_out(0.5) < 1
    assert 0 < ease_in_out_cubic(0.5) < 1


def test_animator_all_methods():
    r = Rect(10, 10)
    # Just call them to ensure coverage
    r.animate.translate(10, 10)
    r.animate.rotate(1)
    r.animate.scale(2)
    r.animate.property("width", 5)
    r.animate.custom(lambda o, t: None)
    r.animate.keyframes(tx={1.0: 100})

    # Styled
    r.animate.fill(Colors.Red)
    r.animate.stroke(Colors.Blue)
    r.animate.opacity(0.5)
    r.animate.style(width=2.0)

    # Text
    t = Text("Hello")
    t.animate.write()
    t.animate.scramble()

    # Polyline
    p = Polyline([Point(0, 0), Point(10, 10)])
    p.animate.morph(p.clone())
    p.animate.warp(lambda pt, t: pt)


def test_scene_rendering(tmp_path):
    from tesserax import Canvas, Rect
    from tesserax.animation import Scene

    c = Canvas()
    with c:
        Rect(10, 10)

    s = Scene(c, fps=10)
    s.capture()
    assert len(s._frames) == 1

    # Mocking imageio save to avoid dependencies issues in test env if any
    # but let's try a simple wait/play
    s.wait(0.1)  # 1 frame
    assert len(s._frames) == 2


def test_wait_animation():
    from tesserax.animation import Wait, Sequence

    w = Wait(weight=5.0)
    assert w._weight == 5.0
    w.begin()
    w.update(0.5)  # Should not crash


def test_following_animation_rotation():
    class PathWithPointAt:
        def point_at(self, t):
            return Point(t * 100, t * 100)

    path = PathWithPointAt()
    shape = Circle(5)
    # With rotate_along=True
    anim = Following(shape, path, rotate_along=True)
    anim.begin()
    anim.update(0.5)
    # Diagonal path should have approx 45 degree rotation (0.785 rad)
    assert math.isclose(shape.transform.rotation, math.pi / 4, abs_tol=0.1)


def test_animation_extra_coverage():
    from tesserax.animation import Wait, Parallel

    # Parallel start/update
    a1 = MockAnimation()
    p = Parallel(a1)
    p.begin()
    p.update(0.5)
    assert a1.updated_t == [0.5]

    # Wait update
    w = Wait()
    w.begin()
    w.update(0.5)

    # KeyframeAnimation logic
    r = Rect(10, 10)
    k = KeyframeAnimation(r, tx={0.0: 0, 1.0: 100})
    k.begin()
    k.update(0.0)
    assert r.transform.tx == 0
    k.update(1.0)
    assert r.transform.tx == 100


def test_animation_errors():
    r = Rect(10, 10)
    anim = Transformed(r, r.transform)
    with pytest.raises(TypeError, match="begin"):
        anim.update(0.5)

    o = {}
    anim2 = NumericAnimation(o, "no_attr", 100)
    with pytest.raises(AttributeError):
        anim2.begin()

    with pytest.raises(AttributeError):
        KeyframeAnimation(r, non_existent={1.0: 10}).begin()


def test_animation_operators_extra():
    a1 = MockAnimation(weight=1.0)
    rep = a1 * 2.0
    assert rep.relative_weight == 1.0  # Wrapped child weight

    # Sequential merge
    from tesserax.animation import Sequence

    seq1 = MockAnimation() | MockAnimation()
    seq2 = seq1 | MockAnimation()
    assert len(seq2.children) == 3

    # Parallel merge
    from tesserax.animation import Parallel

    par1 = MockAnimation() + MockAnimation()
    par2 = par1 + MockAnimation()
    assert len(par2.children) == 3


def test_sequence_empty():
    from tesserax.animation import Sequence

    s = Sequence()
    s.begin()
    s.update(0.5)  # Should not crash


def test_parallel_begin_finish():
    from tesserax.animation import Parallel

    a1 = MockAnimation()
    p = Parallel(a1)
    p.finish()
    assert a1._started


def test_delayed_branch_coverage():
    from tesserax.animation import Delayed

    a1 = MockAnimation()
    # 0 weight or empty
    d = Delayed()
    d.update(0.5)

    d2 = Delayed(a1, lag_ratio=0.5)
    d2.begin()
    d2.update(0.5)


def test_animation_reversed_extra():
    a = MockAnimation()
    rev = a.reversed()
    rev.begin()
    rev.update(0.0)
    assert math.isclose(a.updated_t[0], 1.0)
    rev.update(1.0)
    assert math.isclose(a.updated_t[1], 0.0)


def test_linear_scale_zero_division():
    from tesserax.chart import LinearScale

    s = LinearScale((10, 10), (0, 100))
    assert s.map(10) == 0
    assert s.map(20) == 0


def test_animation_delayed_ratio():
    a = MockAnimation()
    # delay_ratio = 0.5
    d = a.delayed(0.5)
    d.begin()
    # Wrapped._start calls child.begin(), which might trigger update(0) or similar
    # Let's clear it
    a.updated_t = []
    d.update(0.2)  # local t = 0
    # In current implementation, if t < delay_ratio, rated lambda returns 0,
    # so a.update(0) IS called.
    assert len(a.updated_t) == 1
    assert a.updated_t[0] == 0.0
    d.update(0.75)  # local t = (0.75 - 0.5) / 0.5 = 0.5
    assert math.isclose(a.updated_t[1], 0.5)


def test_animation_operators():
    a1 = MockAnimation(weight=1.0)
    a2 = MockAnimation(weight=1.0)

    seq = a1 | a2  # Sequence
    from tesserax.animation import Sequence

    assert isinstance(seq, Sequence)
    assert len(seq.children) == 2

    par = a1 + a2  # Parallel
    from tesserax.animation import Parallel

    assert isinstance(par, Parallel)
    assert len(par.children) == 2

    rep = a1 * 3.0  # Repeating
    from tesserax.animation import Wrapped

    assert isinstance(rep, Wrapped)


def test_animation_pad():
    a = MockAnimation(weight=1.0)
    padded = a.pad(before=1.0, after=2.0)
    # Total weight = 1.0 (before) + 1.0 (a) + 2.0 (after) = 4.0
    from tesserax.animation import Sequence

    assert isinstance(padded, Sequence)
    assert len(padded.children) == 3
    # Checkpoints: 1/4, 2/4, 4/4
    assert padded.checkpoints == [0.25, 0.5, 1.0]
