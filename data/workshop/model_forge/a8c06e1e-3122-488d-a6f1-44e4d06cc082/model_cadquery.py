import cadquery as cq

height = 145.0
width = 82.0
depth = 54.0
base_height = 12.0
thickness = 5.0
creative_profile = "organic-reconstruction"

# Custom-form concept generated from Forge Concept Studio.
# Use this as a starting point for refinement, not as final industrial geometry.
result = cq.Workplane("XY").ellipse(width * 0.24, depth * 0.2).extrude(base_height)
show_object(result, name="recovered-shell-study")
