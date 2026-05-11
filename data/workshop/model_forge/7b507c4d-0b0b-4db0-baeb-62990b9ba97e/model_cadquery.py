import cadquery as cq

outer_dia = 18.0
inner_dia = 8.0
length = 12.0

result = cq.Workplane("XY").circle(outer_dia / 2).extrude(length).faces(">Z").workplane().hole(inner_dia)
show_object(result, name="axle-spacer")
