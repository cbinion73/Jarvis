module qa_camera_mount_1778435662790(
base_len=90,
base_wid=40,
base_thk=6,
riser_h=35,
riser_thk=8,
camera_pad_wid=24,
camera_pad_thk=6,
camera_pad_len=30,
hole_d=5.5,
hole_edge_x=12,
hole_edge_y=10,
hole_spacing_x=66,
hole_spacing_y=20,
standoff_clearance=8,
fit_check_clearance=0.5,
bend_relief=2
){
difference() {
union() {
// Base plate
cube([base_len, base_wid, base_thk], center=false);

// Riser, placed toward rear to keep front access clear
translate([base_len - riser_thk, (base_wid - camera_pad_wid)/2, base_thk])
cube([riser_thk, camera_pad_wid, riser_h], center=false);

// Camera pad extending upward from riser
translate([base_len - riser_thk - camera_pad_len, (base_wid - camera_pad_wid)/2, base_thk + riser_h - camera_pad_thk])
cube([camera_pad_len, camera_pad_wid, camera_pad_thk], center=false);
}

// Mounting holes in base, laid out for access from above
for (x = [hole_edge_x, hole_edge_x + hole_spacing_x])
for (y = [hole_edge_y, hole_edge_y + hole_spacing_y])
translate([x, y, -0.1])
cylinder(h=base_thk + 0.2, d=hole_d, center=false, $fn=48);

// Clearance notch near riser to preserve tool access
translate([base_len - riser_thk - standoff_clearance, (base_wid - 14)/2, 0])
cube([standoff_clearance + 0.1,
