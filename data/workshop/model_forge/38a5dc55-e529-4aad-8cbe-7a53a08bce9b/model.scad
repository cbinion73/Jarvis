```scad
// QA Camera Mount 1778436944997
// Rough parameter-driven stub for later hand refinement.

part_name = "QA Camera Mount 1778436944997";

base_len = 90;
base_wid = 40;
base_thk = 6;

riser_h = 35;
wall_thk = 5;

mount_hole_d = 5.5;
mount_hole_edge_x = 12;
mount_hole_edge_y = 12;

camera_plate_len = 40;
camera_plate_wid = 30;
camera_plate_thk = 4;

camera_hole_d = 3.5;
camera_hole_spacing_x = 20;
camera_hole_spacing_y = 12;

fastener_clear_radius = 10;
corner_r = 4;
fit_check_tolerance = 0.3;

module rounded_plate(l, w, t, r) {
linear_extrude(height=t)
offset(r=r)
square([l-2*r, w-2*r], center=true);
}

module fastener_clearance(x, y, h, r) {
translate([x, y, 0])
cylinder(h=h, r=r, $fn=48);
}

difference() {
union() {
// Base plate
translate([0, 0, 0])
rounded_plate(base_len, base_wid, base_thk, corner_r);

// Vertical riser, centered along base width, placed near one end
translate([base_len/2 - wall_thk/2, 0, base_thk])
cube([wall_thk, base_wid, riser_h], center=true);

// Camera plate at top of riser
translate([base_len/2 + camera_plate_thk/2, 0, base_thk + riser_h - camera_plate_wid/2])
rotate([0, 90, 0])
rounded_plate(camera_plate_len, camera_plate_wid, camera_plate_thk, 2);
}

// Mounting holes in base, kept clear of
