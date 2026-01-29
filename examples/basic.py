from tesserax import Canvas, Rect, Arrow, Circle
from tesserax.layout import Row

# Initialize a canvas for an array visualization
canvas = Canvas(width=400, height=200)

# Create two 'cells'
cell1 = Circle(20)
cell2 = Rect(40, 40)

layout = Row().add(cell1, cell2)

# Create a pointer using the bounds-to-bounds logic
ptr = Arrow(cell1.anchor("right"), cell2.anchor("left"))

# Add all to canvas
canvas.add(layout, ptr)

canvas.fit(10).save("quicksort_partition.svg")
