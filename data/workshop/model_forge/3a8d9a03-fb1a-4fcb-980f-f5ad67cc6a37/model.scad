part_name = "QA Camera Mount 1778870712575";

base_len = 90;
base_wid = 40;
base_thk = 6;

riser_h = 35;
riser_thk = 8;

corner_r = 3;

mount_hole_d = 5.2;
mount_hole_edge_x = 15;
mount_hole_edge_y = 10;

riser_hole_d = 5.2;
riser_hole_z = 18;
riser_hole_clearance = 16;

fit_check_clearance = 0.5;

module rounded_plate(l, w, t, r){
linear_extrude(height=t)
offset(r=r)
offset(delta=-r)
square([l, w], center=true);
}

module base(){
difference(){
rounded_plate(base_len, base_wid, base_thk, corner_r);

for (sx = [-1, 1], sy = [-1, 1]) {
translate([sx * (base_len/2 - mount_hole_edge_x),
sy * (base_wid/2 - mount_hole_edge_y),
-0.1])
cylinder(h=base_thk + 0.2, d=mount_hole_d, $fn=48);
}
}
}

module riser(){
// Riser placed near one end of the base to keep the front area open for fastener access.
difference(){
translate([base_len/2 - riser_thk/2 - 8, 0, base_thk])
cube([riser_thk, base_wid, riser_h], center=true);

// Through-hole for camera/fixture fastener, kept centered and accessible.
translate([base_len/2 - riser_thk/2 - 8, 0, base_thk + riser_hole_z])
rotate([0,90,0])
cylinder(h=riser_thk + 0.2, d=riser_hole_d, center=true, $fn=48);

// Light relief slot to preserve wrench/finger access behind the fastener zone.
translate([base_len/2 - ris
