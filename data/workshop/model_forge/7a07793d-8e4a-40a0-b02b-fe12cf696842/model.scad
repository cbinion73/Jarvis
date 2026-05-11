module qa_camera_mount_1778434848291(
base_len=90,
base_wid=40,
base_thk=6,
riser_h=35,
mount_wall_thk=6,
corner_r=3,
fastener_d=4.5,
fastener_edge_x=12,
fastener_edge_y=20,
riser_hole_d=6.5,
riser_hole_z=18,
riser_hole_x=18,
access_clear_w=16,
access_clear_l=28,
access_clear_offset_x=56
){
difference() {
union() {
// Base plate
linear_extrude(height=base_thk)
offset(r=corner_r)
square([base_len - 2*corner_r, base_wid - 2*corner_r], center=false);

// Riser plate at rear edge of base
translate([base_len - mount_wall_thk, 0, base_thk])
cube([mount_wall_thk, base_wid, riser_h], center=false);
}

// Base fastener holes, kept away from rear riser and edges
translate([fastener_edge_x, fastener_edge_y, -1])
cylinder(h=base_thk + 2, d=fastener_d, $fn=48);

translate([fastener_edge_x, base_wid - fastener_edge_y, -1])
cylinder(h=base_thk + 2, d=fastener_d, $fn=48);

// Riser camera/interface hole
translate([base_len - mount_wall_thk/2, riser_hole_x, base_thk + riser_hole_z])
rotate([0,90,0])
cylinder(h=mount_wall_thk + 2, d=riser_hole_d, $fn=48);

// Fastener access
