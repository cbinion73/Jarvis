```scad
// QA Camera Mount 1778871030009
// Rough parameter-driven stub for later hand refinement

$fn = 64;

// Parameters
base_len = 90;
base_wid = 40;
base_thk = 6;

riser_h = 35;
riser_thk = 10;
riser_setback = 10;

top_len = 30;
top_wid = 30;
top_thk = 6;

hole_d = 5.5;
hole_edge = 12;

fastener_clear_d = 12;

fit_tol = 0.25;

// Derived
riser_x = (base_len - riser_thk) / 2;
riser_y = base_wid - riser_setback - riser_thk;
hole_x1 = hole_edge;
hole_x2 = base_len - hole_edge;
hole_y = base_wid / 2;

// Main mount
module mount_body() {
union() {
// Base
cube([base_len, base_wid, base_thk]);

// Riser
translate([riser_x, riser_y, base_thk])
cube([riser_thk, riser_thk, riser_h]);

// Top pad
translate([
(base_len - top_len) / 2,
riser_y + (riser_thk - top_wid) / 2,
base_thk + riser_h
])
cube([top_len, top_wid, top_thk]);
}
}

// Fastener relief and hole pattern
module fastener_features() {
// Base holes
translate([hole_x1, hole_y, -1])
cylinder(h = base_thk + 2, d = hole_d);

translate([hole_x2, hole_y, -1])
cylinder(h = base_thk + 2, d = hole_d);

// Access clearances from underside
translate([hole_x1, hole_y, -1])
cylinder(h = base_thk + 3, d = fastener_clear_d);

translate([hole_x2, hole_y, -1])
cylinder(h = base_th
