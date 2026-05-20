module qa_camera_mount_1779128797605() {
difference() {
union() {
cube([base_len, base_wid, base_thk], center=false);
translate([riser_offset, 0, base_thk])
cube([riser_thk, base_wid, riser_h], center=false);
}

// Base fastener access holes
translate([hole_x1, hole_y, -1])
cylinder(h=base_thk + 2, d=hole_d, center=false, $fn=48);
translate([hole_x2, hole_y, -1])
cylinder(h=base_thk + 2, d=hole_d, center=false, $fn=48);

// Keep riser face open for camera hardware access / adjustment
translate([riser_offset - fastener_clearance, edge_margin, base_thk + edge_margin])
cube([riser_thk + 2*fastener_clearance, base_wid - 2*edge_margin, riser_h - 2*edge_margin], center=false);
}
}

module fit_check() {
// Printable fit-check envelope only: verifies envelope and access zones without full hardware detail
color("lightgray")
cube([base_len, base_wid, base_thk], center=false);

color("orange")
translate([riser_offset, 0, base_thk])
cube([riser_thk, base_wid, min(riser_h, 10)], center=false);

color("red")
translate([hole_x1, hole_y, 0])
cylinder(h=base_thk + 1, d=hole_d, center=false, $fn=32);
color("red")
translate([hole_x2, hole_y, 0])
cylinder(h=base_thk + 1, d=hole_d, center=false, $fn=32);
}

qa_camera_mount_1779128797605();
if (printable_fit_check) fit_check();
