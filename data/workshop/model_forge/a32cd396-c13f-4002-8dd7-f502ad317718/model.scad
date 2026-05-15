```scad
// QA Camera Mount 1778870769286
// Rough parameter-driven concept model for hand refinement

$fn = 64;

// Parameters
base_len = 90;
base_wid = 40;
base_thk = 6;

riser_h = 35;
riser_thk = 8;

camera_pad_len = 30;
camera_pad_wid = 24;
camera_pad_thk = 4;

// Fasteners
hole_d = 4.5;
hole_edge_x = 12;
hole_edge_y = 10;
hole_spacing = 60;   // center-to-center along length
standoff_clear = 8;  // keep this zone open around fasteners

// Fit check
fit_check_margin = 0.5;

module rounded_plate(len, wid, thk, r=2) {
linear_extrude(height = thk)
offset(r = r)
offset(delta = -r)
square([len, wid], center = true);
}

module base_plate() {
difference() {
translate([0,0,base_thk/2])
rounded_plate(base_len, base_wid, base_thk, r=2);

// Mount holes, centered along length, offset from edges
for (x = [-hole_spacing/2, hole_spacing/2]) {
translate([x, 0, -0.5])
cylinder(h = base_thk + 1, d = hole_d);
}

// Optional clearance slot for access / tool reach
translate([0, 0, -0.5])
cube([hole_spacing - 2*standoff_clear, base_wid - 2*standoff_clear, base_thk + 1], center = true);
}
}

module riser() {
// Vertical support placed near one end of the base
translate([base_len/2 - riser_thk/2 - 8, 0, base_thk])
cube([riser_thk, base_wid - 10, riser_h], center = true);
}

module camera_pad() {
// Top pad projecting from riser
translate([
