module rounded_rect_2d(w, h, r){
offset(r = r) offset(delta = -r) square([w - 2*r, h - 2*r], center = true);
}

module bracket_2d(plate_width=30, hole_spacing=150, hole_diameter=9, edge_margin=15, drain_slot_width=6, drain_slot_length=14, corner_radius=4){
total_length = hole_spacing + 2*edge_margin;
difference(){
rounded_rect_2d(total_length, plate_width, corner_radius);

for (x = [-hole_spacing/2, hole_spacing/2]){
translate([x, 0])
circle(d = hole_diameter, $fn = 48);
}

translate([0, 0])
square([drain_slot_length, drain_slot_width], center = true);
}
}

module bracket_profile(thickness=8, bend_radius=12, bend_relief=3){
// Rough side-profile placeholder for a bent bracket.
// Intended for manual refinement into a true formed profile.
union(){
square([thickness, 40], center = false);
translate([thickness, 40 - bend_radius])
circle(r = bend_radius, $fn = 48);
translate([thickness + bend_radius, 40])
square([60, thickness], center = false);
}
}

linear_extrude(height = thickness)
bracket_2d();
