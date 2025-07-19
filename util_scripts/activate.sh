#!/bin/bash

# Create path to activate powershell script
WORKDIR=$(pwd)
FULL_PATH="$WORKDIR/util_scripts/cw_activate.ps1"
WIN_PATH=$(wslpath -w $FULL_PATH)

# Run script in elevated powershell
powershell.exe -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"$WIN_PATH\"' -Verb RunAs"
