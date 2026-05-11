module qa_camera_mount(base_len=90, base_wid=40, base_thk=6, riser_h=35,
camera_pad_len=30, camera_pad_wid=24, camera_pad_thk=4,
mount_wall=4, hole_d=4.5, hole_edge_x=12, hole_edge_y=10,
hole_spacing_x=62, hole_spacing_y=20, standoff_d=12,
standoff_h=8, fastener_clear_d=9, fastener_access_slot_w=10,
fastener_access_slot_h=18) {

difference() {
union() {
// Base plate
cube([base_len, base_wid, base_thk]);

// Central riser / camera pad
translate([(base_len-camera_pad_len)/2, (base_wid-camera_pad_wid)/2, base_thk])
cube([camera_pad_len, camera_pad_wid, riser_h]);

// Reinforcing side gussets, keeping front access clear
translate([18, 0, base_thk])
linear_extrude(height=riser_h)
polygon(points=[[0,0],[8,0],[0,18]]);
translate([base_len-18, base_wid, base_thk])
rotate([180,0,0])
linear_extrude(height=riser_h)
polygon(points=[[0,0],[8,0],[0,18]]);
}

// Base mounting holes, aligned for tool access
for (x = [hole_edge_x, base_len-hole_edge_x])
for (y = [hole_edge_y, base_wid-hole_edge_y])
translate([x, y, -1])
cylinder(d=hole_d, h=base_thk+2, $fn=48);

// Fastener access relief through the riser face
translate([(base_len-fastener_access_slot_w)/2
