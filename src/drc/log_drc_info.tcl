# Initialize
set log_file [open "drc/AAL_DRC_OUTPUT.log" "w"]
drc catchup
select top cell

# DRC count
puts -nonewline $log_file "Total DRC Errors: "
puts $log_file [drc list count total]

# Get top cell error descriptions and detailed top cell error descriptions.
# Each detailed error is presented as a list of four values indicating the
# bounding box of the error, as {llx lly urx ury} values in internal database units.

set drc_description [drc list why]
set drc_detailed_description [drc listall why]

puts -nonewline $log_file "DRC Error Descriptions: "
if {[string length $drc_description] == 0} {
    puts $log_file "None"
} else {
    puts $log_file [expr {([string length $drc_detailed_description] != 0) ? [drc list why] : ""}]
}

puts -nonewline $log_file "Detailed DRC Error Descriptions: "
if {[string length $drc_detailed_description] == 0} {
    puts $log_file "None"
} else {
    puts $log_file [expr {([string length $drc_description] != 0) ? [drc listall why] : ""}]
}

close $log_file
quit
