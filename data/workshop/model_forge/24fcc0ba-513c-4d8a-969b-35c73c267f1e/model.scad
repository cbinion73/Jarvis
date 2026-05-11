module qa_camera_mount(base_l=90, base_w=40, base_t=6, riser_h=35, riser_t=10, riser_w=24,
edge_margin=8, fastener_d=5.4, fastener_head_d=10.5, fastener_head_h=3.5,
slot_len=16, slot_w=5.6, clearance=0.4)
{
difference() {
union() {
cube([base_l, base_w, base_t], center=false);

translate([(base_l - riser_t)/2, (base_w - riser_w)/2, base_t])
cube([riser_t, riser_w, riser_h], center=false);
}

// Base mounting slots for adjustability
for (ypos = [edge_margin, base_w - edge_margin])
translate([base_l/2 - slot_len/2, ypos - slot_w/2, -0.1])
hull() {
translate([0, 0, 0])
cylinder(h=base_t + 0.2, d=slot_w, $fn=40);
translate([slot_len, 0, 0])
cylinder(h=base_t + 0.2, d=slot_w, $fn=40);
}

// Counterbore relief on top side for fastener access
for (ypos = [edge_margin, base_w - edge_margin])
translate([base_l/2 - slot_len/2, ypos, base_t - fastener_head_h])
rotate([90,0,0])
cylinder(h=base_w, d=fastener_head_d + clearance, $fn=48);

// Cable or access relief beside riser
translate([base_l/2 - slot_len/2, (base_w - slot_w)/2, base_t + 6])
cube([slot_len, slot_w, riser_h - 6], center=false);
}
}

module fit_check()
{
// Printable envelope and witness gauge for hole/slot verification
difference() {
cube([
