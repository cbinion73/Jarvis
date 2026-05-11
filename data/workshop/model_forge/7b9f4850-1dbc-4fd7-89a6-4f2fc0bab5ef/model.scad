```scad
// QA Camera Mount 1778436400339
// Rough parameter-driven CAD stub for later refinement

base_len = 90;
base_wid = 40;
base_thk = 6;
riser_h = 35;

fit_clearance = 0.5;
edge_margin = 8;
riser_thk = 8;
riser_wid = 24;

hole_d = 4.3;
hole_spacing = 58;
hole_offset_x = (base_len - hole_spacing) / 2;
hole_center_y = base_wid / 2;

module mount_body() {
union() {
// Base plate
cube([base_len, base_wid, base_thk], center = false);

// Vertical riser, centered on base width, set back slightly to preserve access to front fasteners
translate([(base_len - riser_thk) / 2, (base_wid - riser_wid) / 2, base_thk])
cube([riser_thk, riser_wid, riser_h], center = false);
}
}

module fastener_holes() {
// Two through holes in the base, accessible from the top face
for (x = [hole_offset_x, hole_offset_x + hole_spacing]) {
translate([x, hole_center_y, -1])
cylinder(h = base_thk + 2, d = hole_d, center = false, $fn = 48);
}
}

module printable_mount() {
difference() {
mount_body();
fastener_holes();
}
}

printable_mount();
```
