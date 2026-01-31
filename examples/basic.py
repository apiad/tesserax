from tesserax import Canvas, Rect, Arrow, Circle
from tesserax.layout import Row

# Initialize a canvas for an array visualization
with Canvas() as canvas:
    # Create two objects in a row layout
    with Row(gap=50):
        circle = Circle(20)
        rect = Rect(40, 40)

    # Create a pointer using the bounds-to-bounds logic
    ptr = Arrow(circle.anchor("right").dx(5), rect.anchor("left").dx(-5))

canvas.fit(10).save("quicksort_partition.svg")
