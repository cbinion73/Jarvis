module qa_camera_mount_1778434790444(
base_len=90,
base_wid=40,
base_thk=6,
riser_h=35,
riser_thk=6,
riser_wid=40,
mount_hole_d=5.5,
mount_hole_edge_x=12,
mount_hole_edge_y=12,
mount_hole_spacing_x=66,
mount_hole_spacing_y=16,
clearance=0.5
){
difference() {
union() {
cube([base_len, base_wid, base_thk], center=false);

translate([0, 0, base_thk])
cube([riser_thk, riser_wid, riser_h], center=false);
}

// Base mounting holes, kept accessible from above
for (x = [mount_hole_edge_x, mount_hole_edge_x + mount_hole_spacing_x])
for (y = [mount_hole_edge_y, mount_hole_edge_y + mount_hole_spacing_y])
translate([x, y, -1])
cylinder(h=base_thk + 2, d=mount_hole_d, $fn=48);

// Optional access relief behind riser for fastener tool clearance
translate([riser_thk - clearance, 0, base_thk + 4])
cube([clearance + 8, riser_wid, riser_h - 4], center=false);
}
}

// Printable fit-check block, separate and thin
module qa_camera_mount_1778434790444_fit_check(
base_len=90,
base_wid=40,
base_thk=6,
riser_h=35,
riser_thk=6,
fit_check_thk=2,
fit_check_margin=1
){
difference() {
union() {
cube([base_len, base_wid, fit_check_thk], center=false);
translate([0, 0
