# RISC-V Power Tools

This repository contains instructions on how to setup the RISC-V Power Tools lab environment.

## Setup


### Chipwhisperer

This is repo contains a "flattened" chipwhisperer repo, with all submodules included. Follow their own instructions on [setup](https://chipwhisperer.readthedocs.io/en/latest/linux-install.html).

The repo contains some minor fixes that have been merged in the official repo, but at the time of writing hasn't been properly propagated via submodules, hence the local flattened repo here.

### Ibex Demo System

For the ibex-demo-system, install this specific ```lowrisc-toolchain-gcc``` toolchain by running the following commands:

```bash
wget https://github.com/lowRISC/lowrisc-toolchains/releases/download/20250303-1/lowrisc-toolchain-gcc-rv32imcb-x86_64-20250303-1.tar.xz
tar -xvf lowrisc-toolchain-gcc-rv32imcb-x86_64-20250303-1.tar.xz --strip-components=1 -C /opt/riscv
rm lowrisc-toolchain-rv32imcb-x86_64-20250303-1.tar.xz
```

Remember to add ```/opt/riscv/bin``` to your PATH.

In the ```ibex-demo-system``` submodule, follow the [instructions](https://github.com/lowRISC/ibex-demo-system) for the remainder of the setup.

### Spike

The instruction sequence can be accurately simulated with Spike:

Install the [lowrisc supported Spike](https://github.com/lowRISC/riscv-isa-sim)

It is no longer maintained it seems, but regardless, clone and follow the build instructions.
You may need to patch ```/fesvr/device.h``` by adding ```#include <cstdint>```, and then running make.

## Customizations

### Bitstream

You may want to build your own bitstream to vary the configurations of the RISCV chip. 
In this case, you must place the bitstream in:

```./chipwhisperer/software/chipwhisperer/hardware/firmware/cw305```

Then it should be accessible via the Chipwhisperer API used in the notebook.

### Memory Modifications

In the default bitstream provided by NewAE, it is built for the 35t model.
We are using the Artix-7 100t model, so we have ~600kB of available storage.

To make use of this, do the following:

- In ```ibex-demo-system/rtl/system/ibex_demo_system.sv```:
    - Increase ```MEM_SIZE```.
- In ```ibex-demo-system/vendor/lowrisc_ibex/examples/sw/simple_system/common/link.ld```:
    - Adapt ```ram``` and ```stack``` values to match ```MEM_SIZE```.
- In ```ibex-demo-system/util/arty-a7-openocd-cfg.tcl```:
    - Configure ```work-area-phys``` *unknown - but likely to be near RAM base address*.
    - Configure ```work-area-size```.

## Simulation

The main build is broken, for reasons unknown.
To build the simulator check out v0.0.3 and build it.

```bash
git clone git@github.com:lowRISC/ibex-demo-system.git
cd ibex-demo-system
git checkout v0.0.3
fusesoc --cores-root=. run --target=sim --tool=verilator --setup --build lowrisc:ibex:demo_system
```

In this repo, the results of a clean successful v0.0.3 build have been copied over.

## Usage

Launch jupyter notebook via make from the project root directory:

```bash
make jupyter
```

Navigate to ```./chipwhisperer/jupyter/Data_Generation_Pipeline```

Here you will find python a python library and notebooks for running and measuring software on the softcore.

### Debugging the Softcore

To retrieve the instruction sequence executed on the FPGA we attach gdb to the softcore using OpenOCD and step through the execution to verify each step using [pexpect](https://pexpect.readthedocs.io/en/stable/).

To do this, the software must be loaded onto the softcore, and started in a halted state awaiting a debugger, as described in the [Ibex demo system](https://github.com/lowRISC/ibex-demo-system?tab=readme-ov-file#loading-an-application-to-the-programmed-fpga) repo.


# Replication of Varying Chipwhisperer Trace Length Issue

When repeating chipwhisperer measurements of the exact same binary, there may be some variation in the trace length.
Since there are no difference in the actual instruction sequence run, or the associated registers, this seems to be due to
some non-determinism. But I have not yet investigated this.

To replicate, set up the repository and:

1. Run ```make jupyter```, and open the notebook in your browser
2. Connect the FPGA, CW-Husky and JTAG to your device, if on WSL run ```make activate``` from the root directory
3. Navigate to the ```chipwhisperer/jupyter/Data_Generation_Pipeline``` directory and open the generateData.ipynb notebook
4. If you don't already have data generated, synthesize a few binaries with 200+ instructions, build and generate labels (just follow the Synthesize New Code section)
5. Generate data with multiple repetitions, and note the output logs will say something like:
```
Command executed successfully!
Output:
Variable trace lengths detected. Padding to max length: 2384
Length range: 2288 - 2384
Successfully captured trace of length 2384 for pre_rvi_mdb_100_0
```

The length range here are the minimum and maximum trace lengths respectively.
This is the oddity in question.
