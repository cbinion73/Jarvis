```scad
// Twin Wake - rough parameter-driven concept model
// Units: mm

overall_h = 140;
overall_w = 70;
overall_d = 45;
base_h = 10;

arm_thickness = 3.5;
arm_width = 12;
arm_gap = 8;
arm_offset_x = 16;
arm_offset_z = 6;

ribbon_steps = 7;
ribbon_twist_deg = 28;
ribbon_sweep_y = 18;
ribbon_peak_z = 126;

base_corner_r = 4;

module rounded_base(w, d, h, r=4) {
// Simple rounded-rectangle approximation for easy hand refinement later
linear_extrude(height = h)
offset(r = r)
square([w - 2*r, d - 2*r], center = true);
}

module ribbon_arm(side = 1) {
// side = 1 or -1 for mirrored pair
for (i = [0 : ribbon_steps - 1]) {
t0 = i / ribbon_steps;
t1 = (i + 1) / ribbon_steps;

z0 = base_h + arm_offset_z + t0 * (ribbon_peak_z - (base_h + arm_offset_z));
z1 = base_h + arm_offset_z + t1 * (ribbon_peak_z - (base_h + arm_offset_z));

x0 = side * (arm_offset_x + t0 * 12);
x1 = side * (arm_offset_x + t1 * 12);

y0 = -arm_width/2 + t0 * arm_sweep();
y1 = -arm_width/2 + t1 * arm_sweep();

rotate([0, 0, side * t0 * ribbon_twist_deg])
hull() {
translate([x0, y0, z0])
cube([arm_thickness, arm_width, arm_thickness], center = true);
translate([x1, y1, z1
