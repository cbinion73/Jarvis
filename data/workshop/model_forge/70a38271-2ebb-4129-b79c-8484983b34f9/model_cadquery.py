import cadquery as cq

height = 160.0
width = 70.0
depth = 60.0
base_height = 12.0
thickness = 6.0
creative_profile = "display-prop"

# Custom-form concept generated from Forge Concept Studio.
# Use this as a starting point for refinement, not as final industrial geometry.
result = cq.Workplane("XY").ellipse(width * 0.24, depth * 0.2).extrude(base_height)
show_object(result, name="ceremonial-shelf-totem")
