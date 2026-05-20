module rounded_plate_2d(len=110, w=30, r=4) {
offset(r=r)
square([len-2*r, w-2*r], center=false);
}

module bracket_flat() {
difference() {
// Main mounting strip
linear_extrude(height=thickness)
rounded_plate_2d(len=hole_spacing + 2*edge_margin, w=plate_width, r=corner_radius);

// Mounting holes, centered on width
for (x = [edge_margin, edge_margin + hole_spacing]) {
translate([x, plate_width/2, -1])
cylinder(h=thickness+2, d=hole_dia, $fn=48);
}

// Drainage hole near low point / center of non-hole region
translate([(hole_spacing + 2*edge_margin)/2, drain_offset, -1])
cylinder(h=thickness+2, d=drain_dia, $fn=32);
}
}

module bracket_bent_mockup() {
// Simple bend placeholder for later hand refinement.
// Replace with true sheet-metal bend logic or a swept solid if needed.
union() {
bracket_flat();
translate([0, plate_width, 0])
rotate([90, 0, 0])
translate([0, 0, 0])
linear_extrude(height=thickness)
rounded_plate_2d(len=hole_spacing + 2*edge_margin, w=plate_width, r=corner_radius);
}
}

bracket_flat();
