module recovered_shell_study() {
difference() {
union() {
// stable base
cube([overall_w * 0.92, overall_d * 0.88, base_h], center=true);

// organic outer shell
for (i = [0 : shape_steps - 1]) {
z0 = base_h + (overall_h - base_h) * i / (shape_steps - 1);
t  = i / (shape_steps - 1);

w = overall_w * (0.52 + 0.48 * pow(1 - t, 0.55)) * profile_scale[i];
d = overall_d * (0.50 + 0.50 * pow(1 - t, 0.62)) * profile_scale[i];

xoff = side_bulge[i];
yoff = (i % 2 == 0) ? 0.0 : -1.5;

translate([xoff, yoff, z0])
rotate([0, 0, twist_deg[i]])
scale([w / overall_w, d / overall_d, 1.0])
sphere(d = 22);
}
}

// hollow interior, leaving walls
translate([0, 0, base_h + wall])
scale([
(overall_w - 2 * wall) / overall_w,
(overall_d - 2 * wall) / overall_d,
(overall_h - base_h - wall) / overall_h
])
union() {
for (i = [0 : shape_steps - 1]) {
z0 = base_h + (overall_h - base_h) * i / (shape_steps - 1);
t  = i / (shape_steps - 1);

w = overall_w * (0.52 + 0.48 * pow(1 - t, 0.55)) * profile_scale[i];
d = overall
