module ceremonial_shelf_totem(
overall_h=160,
overall_w=70,
overall_d=60,
base_h=12,
thickness=6,
body_w=46,
body_d=34,
shoulder_h=22,
top_taper_h=28,
foot_overhang=2
){
base_w = overall_w;
base_d = overall_d;

union() {
// Low, stable base
translate([0,0,0])
cube([base_w, base_d, base_h], center=true);

// Main column, centered to keep CG low and predictable
translate([0,0,base_h + (overall_h - base_h - top_taper_h)/2])
linear_extrude(height=overall_h - base_h - top_taper_h, center=true)
offset(delta=0)
square([body_w, body_d], center=true);

// Shoulder transition for a more ceremonial read
translate([0,0,base_h + shoulder_h/2])
hull() {
cube([body_w, body_d, 1], center=true);
translate([0,0,shoulder_h])
cube([body_w + 8, body_d + 8, 1], center=true);
}

// Top taper / crown
translate([0,0,overall_h - top_taper_h/2])
hull() {
cube([body_w + 8, body_d + 8, 1], center=true);
cube([thickness, thickness, 1], center=true);
}
}
}

ceremonial_shelf_totem();
