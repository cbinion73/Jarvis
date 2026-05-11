module garden_bench_bracket(
hole_spacing=110,
plate_width=30,
thickness=8,
hole_diameter=8.5,
leg_a=70,
leg_b=70,
bend_radius=6,
edge_margin=10,
drain_slot_w=4,
drain_slot_l=12,
drain_slot_offset=8
) {
// Rough L-bracket representation, intended for refinement.
// Coordinate system:
// leg_a extends in +X, leg_b extends in +Y, thickness in Z.
// Hole spacing preserved along the long arm.

difference() {
union() {
// Horizontal leg
translate([0, 0, 0])
cube([leg_a, plate_width, thickness]);

// Vertical leg
translate([0, 0, 0])
cube([thickness, leg_b, plate_width]);
}

// Main through holes on long arm, centered on width
for (xpos = [edge_margin, edge_margin + hole_spacing]) {
translate([xpos, plate_width/2, thickness/2])
rotate([90, 0, 0])
cylinder(h=plate_width + 2, d=hole_diameter, $fn=48);
}

// Drain path slot on low region of horizontal leg
translate([leg_a - drain_slot_offset, plate_width/2, thickness/2])
cube([drain_slot_l, drain_slot_w, thickness + 2], center=true);

// Simple corner relief for bend/drain clearance
translate([thickness/2, thickness/2, thickness/2])
cube([thickness + 2, thickness + 2, thickness + 2], center=true);
}
}

garden_bench_bracket();
