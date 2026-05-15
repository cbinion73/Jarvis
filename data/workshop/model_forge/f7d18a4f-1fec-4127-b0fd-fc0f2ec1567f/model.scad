module rounded_plate(len, wid, thk, r){
linear_extrude(height=thk)
offset(r=r)
offset(delta=-r)
square([len, wid], center=true);
}

module qa_camera_mount(){
difference(){
union(){
translate([0,0,base_thk/2])
rounded_plate(base_len, base_wid, base_thk, corner_r);

translate([0, base_wid/2 - riser_setback - riser_thk/2, base_thk + riser_h/2])
cube([riser_thk, riser_wid, riser_h], center=true);
}

// Base fastener access holes, kept clear and symmetric
for (x = [-fastener_hole_spacing_x/2, fastener_hole_spacing_x/2])
for (y = [-fastener_hole_spacing_y/2, fastener_hole_spacing_y/2])
translate([x, y, base_thk/2])
cylinder(h=base_thk+2, d=fastener_hole_d, center=true, $fn=48);

// Optional camera face holes on riser
for (y = [-camera_hole_spacing/2, camera_hole_spacing/2])
translate([0, base_wid/2 - riser_setback - riser_thk/2, base_thk + camera_face_offset + y])
rotate([0,90,0])
cylinder(h=riser_thk+2, d=camera_hole_d, center=true, $fn=40);
}
}

qa_camera_mount();
