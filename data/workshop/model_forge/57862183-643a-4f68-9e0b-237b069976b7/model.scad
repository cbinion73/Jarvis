```scad
// Twin Wake - rough parametric concept
// Units: mm

overall_h = 140;
overall_w = 70;
overall_d = 45;
base_h = 10;

arm_thk = 3;
arm_w   = 14;
gap     = 10;

rise1 = 78;
rise2 = 118;

twist1 = 18;
twist2 = -14;
sway   = 11;

segments = 48;

module rounded_base(w, d, h, r=2.5) {
minkowski() {
cube([w-2*r, d-2*r, h], center=true);
cylinder(r=r, h=0.01, $fn=segments);
}
}

module ribbon_arm(len=100, w=14, thk=3, twist=15, sway=10, z0=0) {
// A simple lofted ribbon made from stacked, rotated slices
steps = 16;
for (i = [0 : steps-1]) {
t1 = i/steps;
t2 = (i+1)/steps;

z1 = z0 + t1*len;
z2 = z0 + t2*len;

x1 = sway * sin(t1*180);
x2 = sway * sin(t2*180);

r1 = twist * t1;
r2 = twist * t2;

hull() {
translate([x1, 0, z1])
rotate([0, r1, 0])
cube([thk, w, thk], center=true);

translate([x2, 0, z2])
rotate([0, r2, 0])
cube([thk, w, thk], center=true);
}
}
}

module twin_wake() {
union() {
// Base
translate([0, 0, base_h/2])
rounded_base(overall_w, overall_d
