part_name = "QA Camera Mount 1778435312197";

base_len = 90;
base_wid = 40;
base_thk = 6;

riser_h = 35;
riser_thk = 6;
riser_wid = 28;

hole_d = 5.2;
hole_edge_x = 12;
hole_edge_y = 10;
hole_spacing_x = 66;
hole_spacing_y = 20;

corner_r = 3;
clearance = 0.6;

module rounded_plate(l, w, t, r=2) {
linear_extrude(height=t)
offset(r=r)
square([l - 2*r, w - 2*r], center=false);
}

module base_body() {
difference() {
rounded_plate(base_len, base_wid, base_thk, corner_r);

translate([hole_edge_x, hole_edge_y, -0.1])
cylinder(h=base_thk + 0.2, d=hole_d, $fn=48);

translate([hole_edge_x + hole_spacing_x, hole_edge_y, -0.1])
cylinder(h=base_thk + 0.2, d=hole_d, $fn=48);
}
}

module riser_body() {
translate([base_len - riser_thk, (base_wid - riser_wid)/2, base_thk])
cube([riser_thk, riser_wid, riser_h], center=false);
}

module qa_camera_mount() {
union() {
base_body();
riser_body();
}
}

module fit_check() {
// Printable envelope check, laid flat for easy inspection.
difference() {
cube([base_len + 2*clearance, base_wid + 2*clearance, base_thk + riser_h + 2*clearance], center=false);
translate([clearance, clearance, clearance]) qa_camera_mount();
}
}

// Main part
qa_camera_mount();

// Uncomment for fit-check export:
// translate([0, base_wid + 15, 0]) fit_check();
