module desk_camera_mount(
base_len=92,
base_wid=40,
base_thk=6,
riser_h=36,
hole_spacing=50,
hole_d=5.2,
riser_thk=8,
riser_wid=24,
gusset_thk=6,
gusset_len=18,
gusset_h=16
){
hole_edge_margin = (base_len - hole_spacing)/2;
x1 = hole_edge_margin;
x2 = hole_edge_margin + hole_spacing;
hole_y = base_wid/2;

difference() {
union() {
cube([base_len, base_wid, base_thk], center=false);

translate([(base_len-riser_thk)/2, (base_wid-riser_wid)/2, base_thk])
cube([riser_thk, riser_wid, riser_h], center=false);

// Left gusset
hull() {
translate([x1 - gusset_len/2, hole_y - gusset_thk/2, base_thk])
cube([gusset_len, gusset_thk, 1], center=false);
translate([(base_len-riser_thk)/2, (base_wid-riser_wid)/2, base_thk + gusset_h])
cube([riser_thk, gusset_thk, 1], center=false);
}

// Right gusset
hull() {
translate([x2 - gusset_len/2, hole_y - gusset_thk/2, base_thk])
cube([gusset_len, gusset_thk, 1], center=false);
translate([(base_len-riser_thk)/2 + riser_thk, (base_wid-riser_wid)/2, base_thk + gusset_h])
cube([riser_thk, gusset_thk, 1], center=false);
}
}

// Base mounting holes, kept clear for fastener access
