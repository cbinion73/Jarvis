```scad
// Recovered Shell Study - rough parameter-driven stub
// Units: mm

part_name = "Recovered Shell Study";

overall_h = 145;
overall_w = 82;
overall_d = 54;
base_h = 12;
wall = 5;

silhouette_tilt = 0.08;   // subtle lean
bulge_x = 0.18;           // asymmetry in X
bulge_y = -0.10;          // asymmetry in Y

organic_r1 = 0.92;
organic_r2 = 1.08;
organic_r3 = 0.86;

shell_opening_scale = 0.72;
shell_taper = 0.64;
shell_twist = 12;
shell_segments = 7;

base_margin = 1.5;

// Simple helper: non-uniform organic scaling
module organic_scale() {
scale([organic_r1, organic_r2, organic_r3]) children();
}

// Stable base, flattened to sit cleanly
module stable_base() {
linear_extrude(height = base_h)
offset(r = base_margin)
hull_profile();
}

// Outer observed silhouette profile in 2D
module hull_profile() {
// Intentionally asymmetrical, hand-refinable outline
polygon(points = [
[  0,  38],
[ 18,  42],
[ 34,  33],
[ 40,  16],
[ 36,  -2],
[ 24, -18],
[  8, -28],
[ -8, -26],
[-22, -16],
[-31,  -2],
[-34,  16],
[-28,  32],
[-14,  41]
]);
}

// Main shell body
module shell_body() {
translate([0, 0, base_h])
rotate([0, silhouette_tilt * 35, shell_twist])
scale([overall_w/80, overall_d/52, (overall_h-base_h)/90])
union() {
//
