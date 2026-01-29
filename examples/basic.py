from tesserax import Canvas, Rect, Arrow, Circle

# Initialize a canvas for an array visualization
canvas = Canvas(width=400, height=200)

# Create two 'cells'
cell1 = Circle(50, 80, 20)
cell2 = Rect(150, 80, 40, 40)

# Create a pointer using the bounds-to-bounds logic
ptr = Arrow(cell1.bounds().padded(5).right, cell2.bounds().padded(5).left)

# Add all to canvas
canvas.add(cell1, cell2, ptr)

canvas.fit(10).save("quicksort_partition.svg")
