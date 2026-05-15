import cadquery as cq

height = 140.0
width = 70.0
depth = 45.0
base_height = 10.0
thickness = 10.0
creative_profile = "split-ribbon"

# Custom-form concept generated from Forge Concept Studio.
# Use this as a starting point for refinement, not as final industrial geometry.
result = cq.Workplane("XY").ellipse(width * 0.24, depth * 0.2).extrude(base_height)
show_object(result, name="twin-wake")
