module rounded_plate_2d(len, wid, r){
offset(r = r)
offset(delta = -r)
square([len, wid], center = false);
}

module bench_bracket(){
linear_extrude(height = thickness)
difference(){
union(){
// Main mounting strip
rounded_plate_2d(sheet_length, plate_width, corner_radius);

// Simple bent-leg placeholders for later refinement
translate([hole_spacing/2 - flange_length/2, -leg_length])
rounded_plate_2d(flange_length, plate_width, corner_radius);
}

// Mounting holes, preserved spacing
translate([end_margin, plate_width/2, -1])
cylinder(h = thickness + 2, d = hole_diameter, $fn = 48);
translate([end_margin + hole_spacing, plate_width/2, -1])
cylinder(h = thickness + 2, d = hole_diameter, $fn = 48);

// Drainage hole near low point, away from primary fasteners
translate([sheet_length/2, drain_offset_from_bend, -1])
cylinder(h = thickness + 2, d = drain_hole_diameter, $fn = 32);
}
}

bench_bracket();
