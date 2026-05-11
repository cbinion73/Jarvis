module rounded_block(l,w,h,r=2){
minkowski(){
cube([max(l-2*r,0), max(w-2*r,0), max(h-2*r,0)], center=false);
sphere(r=r, $fn=24);
}
}

module mount_body(){
difference(){
union(){
rounded_block(base_len, base_w, base_th, fillet_r);

translate([base_len - riser_th, (base_w - wall*2)/2, base_th])
cube([riser_th, wall*2, riser_h], center=false);

translate([base_len - riser_th - camera_offset_from_riser, (base_w - camera_pad_w)/2, base_th + riser_h - camera_pad_th])
cube([camera_pad_len, camera_pad_w, camera_pad_th], center=false);
}

translate([fastener_edge_x, fastener_edge_y, -0.1])
cylinder(h=base_th + 0.2, d=fastener_d, $fn=32);

translate([fastener_edge_x, base_w - fastener_edge_y, -0.1])
cylinder(h=base_th + 0.2, d=fastener_d, $fn=32);

translate([base_len - riser_th - camera_offset_from_riser + camera_pad_len/2, base_w/2 - access_slot_w/2, base_th + riser_h - access_slot_h])
cube([access_slot_h, access_slot_w, access_slot_h], center=false);
}
}

mount_body();
