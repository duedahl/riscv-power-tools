# Copyright lowRISC contributors.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

adapter driver ftdi
ftdi vid_pid 0x0403 0x6014
ftdi channel 0
adapter speed 10000

# FIXME: Disable when working #
# debug_level 3
###############################

ftdi layout_init 0x00e8 0x60eb
transport select jtag

# Configure JTAG chain and the target processor
set _CHIPNAME riscv

# arty-a7-100t
set _EXPECTED_ID 0x13631093 

jtag newtap $_CHIPNAME cpu -irlen 6 -expected-id $_EXPECTED_ID -ignore-version
set _TARGETNAME $_CHIPNAME.cpu
target create $_TARGETNAME riscv -chain-position $_TARGETNAME

# Added - take into account the MEM_SIZE set in verilog.
# work-area-phys: work area base address to use when no MMU is active.
# work-area-size: work area size in bytes. For both phys/virt addressing.
#$_TARGETNAME configure -work-area-phys 0x0010a000 -work-area-size 0x8000 -work-area-backup 1

riscv set_ir idcode 0x09
riscv set_ir dtmcs 0x22
riscv set_ir dmi 0x23

# adapter speed 10000

#riscv set_prefer_sba on
gdb_report_data_abort enable
gdb_report_register_access_error enable
gdb_breakpoint_override hard

reset_config none

init
halt
