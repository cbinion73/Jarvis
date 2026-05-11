part_name = "QA Camera Mount 1778444985970";

base_len = 90;
base_wid = 40;
base_thk = 6;
riser_h = 35;
wall_thk = 6;

hole_d = 5.5;
hole_edge_x = 12;
hole_edge_y = 10;
hole_spacing_x = 66;
hole_spacing_y = 20;

clearance_front = 12;
clearance_top = 10;

module camera_mount() {
difference() {
union() {
cube([base_len, base_wid, base_thk], center=false);

translate([0, (base_wid - wall_thk)/2, base_thk])
cube([wall_thk, wall_thk, riser_h], center=false);

translate([0, (base_wid - wall_thk)/2, base_thk + riser_h - wall_thk])
cube([clearance_front + wall_thk, wall_thk, wall_thk], center=false);
}

translate([hole_edge_x, hole_edge_y, -0.5])
cylinder(h=base_thk + 1, d=hole_d, center=false, $fn=48);

translate([hole_edge_x + hole_spacing_x, hole_edge_y, -0.5])
cylinder(h=base_thk + 1, d=hole_d, center=false, $fn=48);

translate([hole_edge_x, hole_edge_y + hole_spacing_y, -0.5])
cylinder(h=base_thk + 1, d=hole_d, center=false, $fn=48);

translate([hole_edge_x + hole_spacing_x, hole_edge_y + hole_spacing_y, -0.5])
cylinder(h=base_thk + 1, d=hole_d, center=false, $fn=48);

translate([wall_thk, (base_wid - wall_thk)/2 - 0.1, base_thk + riser_h - wall_thk])
cube([clearance_front, wall_thk + 0.2, wall_thk + 0.2], center=false);
}
}

module fit_check() {
difference
