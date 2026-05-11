module rounded_plate(len=190, w=plate_w, t=plate_t, cr=corner_r) {
linear_extrude(height=t)
offset(r=cr)
offset(delta=-cr)
square([len, w], center=false);
}

module hole_pattern(len=190, w=plate_w, hs=hole_spacing, hd=hole_d, em=edge_margin) {
for (x = [em, em + hs]) {
translate([x, w/2, -1])
cylinder(h=plate_t + 2, d=hd, $fn=48);
}
}

module drainage_slot(w=plate_w, t=plate_t, dd=drain_d) {
translate([len/2, w - 2, plate_t/2])
rotate([90,0,0])
cylinder(h=w, d=dd, $fn=32);
}

module bend_bracket(len=190, w=plate_w, t=plate_t, br=bend_r) {
// Simple L-bracket placeholder: one flat leg, one vertical leg, bend approximated by a fillet radius placeholder.
difference() {
union() {
cube([len, w, t], center=false);
translate([0, 0, t])
cube([len, t, w], center=false);
}

// Mounting holes in first leg
for (x = [edge_margin, edge_margin + hole_spacing]) {
translate([x, w/2, -1])
cylinder(h=t + 2, d=hole_d, $fn=48);
}

// Soft relief at bend root
translate([0, -1, -1])
cube([bend_relief_l, bend_relief_w, t + 2], center=false);

// Drainage
translate([len/2, w/2, -1])
cylinder(h=t + 2, d=drain_d, $fn=32);
}
}

// Main
bend_bracket();
