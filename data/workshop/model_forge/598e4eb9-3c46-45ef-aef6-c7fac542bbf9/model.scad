module rounded_box(size=[10,10,10], r=1) {
minkowski() {
cube([size[0]-2*r, size[1]-2*r, size[2]-2*r], center=false);
sphere(r=r, $fn=32);
}
}

module ceremonial_shelf_totem(
overall_h=160,
overall_w=70,
overall_d=60,
base_h=12,
thickness=6
) {
body_h = overall_h - base_h;
base_w = overall_w;
base_d = overall_d;

body_w = 34;
body_d = 28;

shoulder_h = 18;
top_h = 26;
neck_h = body_h - shoulder_h - top_h;

top_w = 44;
top_d = 36;

union() {
// Weighted base
translate([0,0,0])
rounded_box([base_w, base_d, base_h], r=2);

// Main vertical spine, slightly narrower for a calm taper
translate([(base_w-body_w)/2, (base_d-body_d)/2, base_h])
hull() {
rounded_box([body_w, body_d, max(neck_h,1)], r=2);
}

// Shoulder flare for visual presence
translate([(base_w-top_w)/2, (base_d-top_d)/2, base_h + neck_h])
hull() {
rounded_box([body_w, body_d, shoulder_h], r=2);
translate([0,0,shoulder_h])
rounded_box([top_w, top_d, 1], r=2);
}

// Ceremonial top cap
translate([(base_w-top_w)/2, (base_d-top_d)/2, base_h + neck_h + shoulder_h])
rounded_box([top_w, top_d, top_h], r=2);
}
}

// Render
ceremonial_shelf_totem();
