module garden_bench_bracket(
plate_width=30,
thickness=8,
hole_spacing=110,
bend_radius=12,
hole_dia=9,
edge_margin=10,
leg_length=70,
bend_clearance=2,
drain_slot_w=4,
drain_slot_l=18,
drain_offset=8,
motif_scale=0.35,
motif_depth=1.2
){
inner_r = bend_radius;
outer_r = bend_radius + thickness;
straight = leg_length;

module hole2d(x, y, d=hole_dia) {
translate([x, y]) circle(d=d, $fn=48);
}

module drain_slot2d(x, y, w=drain_slot_w, l=drain_slot_l) {
translate([x, y]) hull() {
translate([-l/2 + w/2, 0]) circle(d=w, $fn=24);
translate([ l/2 - w/2, 0]) circle(d=w, $fn=24);
}
}

module scout_motif2d(scale=1, depth=1) {
// Subtle, abstracted badge-like notch pattern; keep hand-refinable.
// Replace with a proper scout emblem if desired.
union() {
polygon(points=[
[0, 0],
[4*scale, 8*scale],
[8*scale, 0],
[6.2*scale, 0],
[4*scale, 4.2*scale],
[1.8*scale, 0]
]);
translate([4*scale, 3.2*scale])
circle(r=1.0*scale);
}
}

linear_extrude(height=thickness)
union() {
// Leg A
difference() {
square([straight, plate_width], center=false);

// Hole pattern preserved: first hole at edge_margin, second at edge_margin + spacing
hole2d(edge_margin, plate_width/2);
