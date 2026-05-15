base_len = 90;
base_wid = 40;
base_thk = 6;

riser_h = 35;
riser_thk = 8;
riser_wid = 30;
riser_offset_x = 15;
riser_backset = 0;

hole_d = 4.5;
hole_edge_x = 12;
hole_edge_y = 10;
hole_spacing_x = 60;

fastener_clearance = 8;

module base_plate() {
difference() {
cube([base_len, base_wid, base_thk], center=false);
for (x = [hole_edge_x, hole_edge_x + hole_spacing_x]) {
translate([x, hole_edge_y, -1])
cylinder(d=hole_d, h=base_thk + 2, $fn=48);
}
}
}

module riser_block() {
translate([riser_offset_x, (base_wid - riser_wid)/2, base_thk])
cube([riser_thk, riser_wid, riser_h], center=false);
}

module fastener_access_volume() {
translate([0, (base_wid - (riser_wid + fastener_clearance))/2, 0])
cube([base_len, riser_wid + fastener_clearance, base_thk + riser_h], center=false);
}

module mount() {
difference() {
union() {
base_plate();
riser_block();
}
fastener_access_volume();
}
}

module fit_check() {
union() {
base_plate();
translate([riser_offset_x, (base_wid - riser_wid)/2, base_thk])
cube([riser_thk, riser_wid, fit_check_thk], center=false);
}
}

// Render full part
mount();

// Uncomment for printable fit-check slice
// fit_check();
