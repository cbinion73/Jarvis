module rounded_plate(len, wid, thk, r){
linear_extrude(height=thk)
offset(r=r)
square([len-2*r, wid-2*r], center=true);
}

module hole_pair(spacing, dia, thk){
for (x = [-spacing/2, spacing/2])
translate([x, 0, -1])
cylinder(h=thk+2, d=dia, $fn=48);
}

module drainage_slot(len, wid, thk, dia, off){
translate([0, -wid/2 + off, thk/2])
rotate([90,0,0])
cylinder(h=wid+2, d=dia, $fn=32);
}

module garden_bench_bracket(){
plate_len = hole_spacing + 2*end_margin;
base_w = plate_width;

difference(){
union(){
// Flat mounting plate, placeholder for the folded form later
rounded_plate(plate_len, base_w, plate_thickness, corner_radius);
// Bend region / second leg is intentionally left as a hand-refinement stub
// to preserve bend radius 12 mm without pretending to be a finished forming model.
}

// Mounting holes preserved at specified spacing
hole_pair(hole_spacing, hole_dia, plate_thickness);

// Drainage feature near one edge
drainage_slot(plate_len, base_w, plate_thickness, drain_hole_dia, drain_offset);
}
}

garden_bench_bracket();
