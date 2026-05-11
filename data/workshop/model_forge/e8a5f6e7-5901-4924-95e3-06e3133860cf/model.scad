```scad
// Sensor enclosure - rough parametric stub
// Units: mm

$fn = 64;

// ---------- Parameters ----------
L = 120;
W = 80;
H = 45;
wall = 3;
lip = 2;

clearance = 0.3;
corner_r = 4;

lid_thk = 3;
lid_flange = lip;
lid_overhang = 0.8;

inner_L = L - 2*wall;
inner_W = W - 2*wall;
base_inner_H = H - wall - lip;
base_outer_H = H;

hole_edge = 12;

// ---------- Helpers ----------
module rounded_rect_2d(l, w, r) {
offset(r = r)
square([l - 2*r, w - 2*r], center = true);
}

module rounded_box(l, w, h, r) {
linear_extrude(height = h)
rounded_rect_2d(l, w, r);
}

// ---------- Base Shell ----------
module base_shell() {
difference() {
// Outer body
rounded_box(L, W, base_outer_H, corner_r);

// Internal cavity
translate([0, 0, wall])
rounded_box(inner_L, inner_W, base_inner_H + 0.5, max(corner_r - wall, 0.8));

// Open top
translate([0, 0, H - lip])
cube([L + 2, W + 2, lip + 2], center = true);
}

// Internal lip shelf for lid registration
translate([0, 0, H - lip - 0.01])
difference() {
rounded_box(L - 2*wall, W - 2*wall, lip, max(corner_r - wall, 0.8));
translate([0, 0, -0.5])
rounded_box((L - 2*wall) - 2*clearance, (W - 2*wall) - 2*clearance, lip + 1, max(corner_r - wall - clearance, 0
