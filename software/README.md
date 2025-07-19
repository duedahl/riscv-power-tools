# Target Software

This directory contains source code and build instruction for each measurement target.
Source files and all associated files are located in the ```src``` folder, each with their own subfolder.

Subfolders prefixed with ```0ignore``` will not be built.

## Structure

```
software/
├── .dep/                               # Dependencies directory
├── main.c                              # Main C wrapper file used to call each individual target software
└── src/                                # Source code directory
    ├── 0ignore_X                       # Folder to be ignored
    ├── beebs_Y                         # Folder containing files related to the beebs_Y software
    |   ├── beebs_Y.c                   # C source code
    |   └── other generated files       # Makefile, .bin, .elf files etc
    ├── Z    
    |   ├── Z.c
    |   └── other generated files
    .
    .
    .   
```

## Usage

To build targets use the DataGenerator class accessible in ´´´chipwhisperer/jupyter/Data_Generation_Pipeline´´´´.

## Bugs

For some reason breakpoints at main do not work when running the gdb -x script, but -ex works fine line by line...
Also works fine manually.

It seems the riscv32 toolchains -x flag may be erroneous, at least it behaves strangely.