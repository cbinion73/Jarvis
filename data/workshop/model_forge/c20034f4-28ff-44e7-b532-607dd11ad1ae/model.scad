module rounded_plate(len=90, wid=40, thk=6, r=3) {
linear_extrude(height=thk)
offset(r=r)
offset(delta=-r)
square([len, wid], center=true);
}

module mount_base() {
difference() {
rounded_plate(base_len, base_wid, base_thk, corner_r);

for (x = [-mount_hole_span/2, mount_hole_span/2]) {
translate([x, 0, -0.1])
cylinder(h=base_thk+0.2, d=mount_hole_d, $fn=48);
}
}
}

module riser_block() {
translate([0, 0, base_thk])
difference() {
translate([0, 0, 0])
cube([riser_thk, base_wid - 2*wall, riser_h], center=true);

// Fastener access slot through riser face
translate([0, 0, camera_hole_z])
rotate([0, 90, 0])
cube([access_slot_l, access_slot_w, riser_thk + 2], center=true);

// Camera mounting hole
translate([0, 0, camera_hole_z])
rotate([0, 90, 0])
cylinder(h=riser_thk + 2, d=camera_hole_d, $fn=48);
}
}

module qa_camera_mount() {
union() {
mount_base();
translate([base_len/2 - riser_thk/2 - wall, 0, 0])
riser_block();
}
}

qa_camera_mount();

module fit_check() {
difference() {
translate([0, 0, 0])
cube([base_len + 2*fit_clearance, base_wid + 2*fit_clearance, base_th
