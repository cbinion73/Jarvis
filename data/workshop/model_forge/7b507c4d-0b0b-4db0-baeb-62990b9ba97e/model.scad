module axle_spacer(outer_d=18, inner_d=8, length=12, chamfer=0.5) {
difference() {
// Main body
cylinder(h=length, d=outer_d, $fn=96);

// Through bore
translate([0,0,-0.1])
cylinder(h=length+0.2, d=inner_d, $fn=72);
}

// Optional manual refinement later:
// Add small chamfers or fillets at both ends if desired.
}

axle_spacer();
