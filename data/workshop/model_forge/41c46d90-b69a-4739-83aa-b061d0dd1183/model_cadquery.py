import cadquery as cq

width = 30.0
thickness = 8.0
spacing = 150.0
leg_a = 82.5
leg_b = 70.0
hole_dia = 8.5
edge_margin = 12.0

leg1 = cq.Workplane("XY").box(leg_a, width, thickness, centered=(False, True, False))
leg2 = cq.Workplane("YZ").box(width, leg_b, thickness, centered=(True, False, False))
result = leg1.union(leg2.translate((0, 0, thickness)))
result = result.faces(">Z").workplane().center(edge_margin, 0).hole(hole_dia).center(spacing, 0).hole(hole_dia)
result = result.faces(">X").workplane().center(0, edge_margin).hole(hole_dia)
show_object(result, name="garden-bench-bracket")
