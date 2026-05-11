part_name = "monitor_mount_plate";

length = 90;
width = 45;
thickness = 6;
hole_spacing = 60;
hole_diameter = 6;
riser_height = 22;

hole_r = hole_diameter / 2;
hole_offset_x = hole_spacing / 2;
plate_center_x = length / 2;
plate_center_y = width / 2;

module monitor_mount_plate() {
difference() {
union() {
// Main plate
cube([length, width, thickness], center = false);

// Simple rear riser block for desk-mount prototype
// Adjust or replace with a true angled bracket later.
translate([plate_center_x - 8, width - 12, thickness])
cube([16, 12, riser_height], center = false);
}

// Mounting holes, centered along the length
translate([plate_center_x - hole_offset_x, plate_center_y, -1])
cylinder(h = thickness + 2, r = hole_r, $fn = 48);

translate([plate_center_x + hole_offset_x, plate_center_y, -1])
cylinder(h = thickness + 2, r = hole_r, $fn = 48);
}
}

monitor_mount_plate();
