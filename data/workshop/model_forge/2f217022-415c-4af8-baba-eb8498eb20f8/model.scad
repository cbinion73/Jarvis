module qa_camera_mount_1779127447579(
base_l=90,
base_w=40,
base_t=6,
riser_h=35,
riser_t=8,
corner_r=3,
mount_hole_d=4.5,
mount_hole_edge_x=12,
mount_hole_edge_y=10,
riser_hole_d=5.2,
riser_hole_z=18,
riser_from_end=14,
fastener_access_clearance=10
){
difference(){
union(){
// Base plate
linear_extrude(height=base_t)
offset(r=corner_r)
square([base_l-2*corner_r, base_w-2*corner_r], center=false);

// Riser block, centered on width, offset from one end
translate([riser_from_end, (base_w-riser_t)/2, base_t])
cube([riser_t, riser_t, riser_h], center=false);
}

// Base mounting holes, kept clear of riser access zone
for (x = [mount_hole_edge_x, base_l - mount_hole_edge_x])
for (y = [mount_hole_edge_y, base_w - mount_hole_edge_y])
translate([x, y, -0.5])
cylinder(h=base_t+1, d=mount_hole_d, $fn=48);

// Riser through-hole, centered for camera or adapter fastener
translate([riser_from_end + riser_t/2, base_w/2, base_t + riser_hole_z])
rotate([90,0,0])
cylinder(h=base_w + 2*fastener_access_clearance, d=riser_hole_d, center=true, $fn=48);
}
}

// Printable fit-check: 1.2 mm slice around the riser and one base hole zone
module qa_camera_mount_fit_check(){
intersection(){
qa_camera_mount_1779127447579();
