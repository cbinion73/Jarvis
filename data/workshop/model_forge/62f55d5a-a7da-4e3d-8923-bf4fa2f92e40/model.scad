module rounded_plate(len, wid, thk, r){
linear_extrude(height = thk)
offset(r = r)
offset(delta = -r)
square([len, wid], center = true);
}

module hole(x, y, d, thk){
translate([x, y, -1])
cylinder(h = thk + 2, d = d, $fn = 48);
}

module bracket(){
difference(){
union(){
// Simplified L-bracket envelope for later refinement
translate([0, 0, 0])
rounded_plate(150 + 2*end_margin, plate_width, thickness, corner_r);

translate([0, 0, thickness])
rotate([0, 90, 0])
rounded_plate(bracket_leg, plate_width, thickness, corner_r);
}

// Mounting holes, preserved spacing
hole(-hole_spacing/2, 0, hole_dia, thickness);
hole( hole_spacing/2, 0, hole_dia, thickness);

// Drainage holes near low points
hole(0, -plate_width/4, drain_dia, thickness);
hole(0,  plate_width/4, drain_dia, thickness);

// Bend relief approximation
translate([0, 0, thickness/2])
cube([bend_relief, bend_radius, thickness + 2], center = true);
}
}

bracket();
