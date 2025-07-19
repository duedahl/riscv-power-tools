import chipwhisperer as cw
import os, subprocess, time, re
from chipwhisperer.hardware.firmware.open_fw import getsome_generator
import json, datetime, shutil
import pexpect, multiprocessing
from IPython.display import clear_output
import numpy as np
import math
import anthropic
from typing import Optional, List, Dict, Any, Union, Set, Callable

class ProjectBaseClass:
    """
    Base class for Ibex-related operations.
    Provides common path handling and utility functions.
    """
    
    def __init__(self, project_root_path="../../../"):
        """
        Initialize the base class with project root path.
        
        Args:
            project_root_path (str): Path to the project root directory
        """
        self.root_path = os.path.abspath(project_root_path)
        self.ibex_path = os.path.join(self.root_path, "ibex-demo-system")
        self.software_path = os.path.join(self.root_path, "software")
        self.src_dir = os.path.join(self.software_path, "src")
        
    def get_software_directories(self):
        """Get all software directories in the source directory that contain a .c file with the same name"""
        software_directories = []
        for item in os.listdir(self.src_dir):
            item_path = os.path.join(self.src_dir, item)
            if "0ignore_" not in item and os.path.isdir(item_path):
                expected_c_filename = item + ".c"
                expected_c_path = os.path.join(item_path, expected_c_filename)
                if os.path.isfile(expected_c_path):
                    software_directories.append(item_path)
        return sorted(software_directories)
    
    def get_dir(self, software_name):
        """Get full path of the software directory
        
        Args:
            software_name (str): Name of the software
            
        Returns:
            str: Full path of the specified directory.
        """
        return os.path.join(self.src_dir, software_name)
        
    def get_ext(self, software_name, ext="hex", platform="CW305_IBEX"):
        """Get full path of the compiled software software_name with extension ext
        
        Args:
            software_name (str): Name of the software
            ext (str): File extension of software
            platform (str): Name of the compile target platform
            
        Returns:
            str: Full path of the specified file.
        """
        software_dir = self.get_dir(software_name)
        ext_path = os.path.join(software_dir, f"{software_name}-{platform}.{ext}")
        return ext_path

class IbexChipWhisperer(ProjectBaseClass):
    """
    Class to manage ChipWhisperer operations with Ibex RISC-V core.
    Handles FPGA programming, firmware loading, and debugging operations with CW305 Artix-7 FPGA.
    """
    
    def __init__(self, project_root_path="../../../", oversampling_factor = 4):
        """
        Initialize the IbexChipWhisperer controller.
        
        Args:
            ibex_base_path (str): Path to the Ibex demo system repository
            oversampling_rate (int): Oversampling rate = sampling frequency / softcore clock frequency
        """
        super().__init__(project_root_path)
        self.script_path = f"{self.ibex_path}/util/load_demo_system.sh"
        self.fpga_target = cw.target(None, cw.targets.CW305, bsfile=None, force=False)
        self.oversampling_factor = oversampling_factor
        self.target = None # Softcore target
        self.scope = None
        
    def connect(self):
        """
        Connect to the ChipWhisperer measurement device and set up the scope and target.
        """
        self.scope = cw.scope()
        
        # Determine SimpleSerial version
        try:
            if SS_VER == "SS_VER_2_1":
                target_type = cw.targets.SimpleSerial2
            elif SS_VER == "SS_VER_2_0":
                raise OSError("SS_VER_2_0 is deprecated. Use SS_VER_2_1")
            else:
                target_type = cw.targets.SimpleSerial
        except:
            SS_VER = "SS_VER_1_1"
            target_type = cw.targets.SimpleSerial
        
        # Attempt to connect to target
        try:
            self.target = cw.target(self.scope, target_type)
        except:
            print("INFO: Caught exception on reconnecting to target - attempting to reconnect to scope first.")
            print("INFO: This is a work-around when USB has died without Python knowing. Ignore errors above this line.")
            self.scope = cw.scope()
            self.target = cw.target(self.scope, target_type)
        
        print("INFO: Found ChipWhisperer😍")
        self.scope.default_setup()
        print("""\nSet DIP Switches on the CW305:
            J16: 1 ; K16: 1""")
        
        # Configure clocks
        print('Set the CW305 J16 switch to 1 so that Ibex is clocked from HS2. Note this is different from what most other CW305 notebooks require.')
        self.scope.clock.clkgen_src = 'system'
        self.scope.clock.clkgen_freq = 100e6 # Bitstreams are built to take in an external clock of 100MHz and transform.
        if self.scope._is_husky:
            self.scope.clock.adc_mul = 2
            self.scope.gain.gain = 1    # Set gain to 1 (may need adjustment)
            #self.scope.adc.clip_errors_disabled = True  # Optional: disable clip errors
        else:
            self.scope.clock.adc_src = 'clkgen_x1'

        base_baud_rate = 115200 * 4
        self.target.baud = base_baud_rate // self.oversampling_factor
    
    def program_fpga(self, bitstream="lowrisc_ibex_demo_system_512KRAM.bit", prog_speed=10e6):
        """
        Program the FPGA with the specified bitstream.
        
        Args:
            bitstream (str): Name of the bitstream file to program
            prog_speed (float): Programming speed
            
        Returns:
            bool: True if programming was successful, False otherwise
        """           
        getsome = getsome_generator("cw305")
        bsdata = getsome(bitstream)
        status = self.fpga_target.fpga.FPGAProgram(bsdata, exceptOnDoneFailure=False, prog_speed=prog_speed)
        
        if status:
            print("✅ FPGA programmed. Next you need to program the firmware using the load_demo_system.sh command from the Ibex repository.")
            return True
        else:
            print(status)
            print("❌ FPGA Done pin failed to go high")
            return False
    
    def reload(self, program_path, debug=False, verbose=True):
        """
        Reset the device and load a program.
        
        Args:
            program_path (str): Path to the program to load
            debug (bool): If True, halt after loading (await debugger)
            verbose (bool): If True, print verbose output
            
        Returns:
            subprocess.CompletedProcess: Result of the load operation
        """
        if not os.path.exists(program_path):
            raise FileNotFoundError(f"File not found: {program_path}")
        if self.scope:
            # Ensure clip errors are cleared when new software loaded
            self.scope.adc.clear_clip_errors()
        
        instruction = "halt" if debug else "run"
        cmd = f"{self.script_path} {instruction} {program_path}"
        
        try:
            # Execute the command and capture output
            print(f"Executing command: {cmd}")
            result = subprocess.run(cmd, shell=True, check=True)
            
            # Print the output
            if verbose:
                print("Command executed successfully!")
                print("Output:")
                
                if hasattr(result, 'stderr') and result.stderr:
                    for line in result.stderr.splitlines():
                        print(line)
                
            return result
        
        except subprocess.CalledProcessError as e:
            print(f"Error executing command. Return code: {e.returncode}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Error message: {e.stderr}")
            return e
        
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            return e
            
    def disconnect(self):
        """
        Disconnect from the ChipWhisperer device.
        """
        if self.scope:
            self.scope.dis()
            print("Disconnected from ChipWhisperer")




class DataGenerator(ProjectBaseClass):
    """
    DataGenerator handle data and label generation for the software running on the Ibex softcore.

    This class manages the build process, data generation, and labeling for software targets,
    keeping track of state to avoid redundant operations.
    """
    def __init__(self, project_root_path="../../../", platform='CW305_IBEX', state_file='data_generator_state.json'):
        """Initialize the DataGenerator

        Args:
            src_dir (str): Source directory containing software folders
            platform (str): Target platform for compilation
            state_file (str): File to store/load state information
        """
        super().__init__(project_root_path)
        self.main_path = os.path.join(self.root_path, "software/main.c")
        self.platform = platform
        self.state_file = state_file
        self.last_trace = None
        
        # Find all viable software directories
        self.software_dirs = self.get_software_directories()
        
        # Load or initialize state
        self.state = self._load_state()
        
        # Initialize state for any new software directories
        for software_dir in self.software_dirs:
            software_name = os.path.basename(software_dir)
            if software_name not in self.state:
                self.state[software_name] = {
                    'compiled': False,
                    'compile_status': None,
                    'compiled_timestamp': None,
                    'data_generated': False,
                    'data_timestamp': None,
                    'labeled': False,
                    'labeled_timestamp': None,
                    'debugged': False,
                    'debugged_timestamp': None,
                    'final_status': None,
                    'dir_path': None
                }
        
        # Save state to ensure new software entries are recorded
        self._save_state()

    def get_dir(self, software_name):
        """Get full path of the software directory
        
        Args:
            software_name (str): Name of the software
            
        Returns:
            str: Full path of the specified directory.
        """
        software_dir = os.path.join(self.src_dir, software_name)

        return software_dir
        
    def get_ext(self, software_name, ext="hex", platform="CW305_IBEX"):
        """Get full path of the compiled software software_name with extension ext
        
        Args:
            software_name (str): Name of the software
            ext (str): File extension of software
            platform (str): Name of the compile target platform
            
        Returns:
            str: Full path of the specified file.
        """
        software_dir = self.get_dir(software_name)

        ext_path = os.path.join(software_dir, f"{software_name}-{platform}.{ext}")

        return ext_path

    def _load_state(self):
        """Load state from disk or create new state dictionary"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading state file: {e}")
                print("Creating new state file")
                return {}
        return {}

    def _save_state(self):
        """Save state to disk"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            print(f"Error saving state file: {e}")

    def gen_makefile(self, source_path):
        """Create a modified Makefile with main.c and the specified source file"""
        # Get the absolute paths
        target_path = os.path.dirname(source_path)
        name_key = os.path.basename(source_path).split(".")[0]
        firmware_path = os.path.join(self.root_path, "chipwhisperer/firmware/mcu")
        makefile_path = os.path.join(target_path, "Makefile")

        # Get relative paths with respect to target_path
        relative_main_path = os.path.relpath(self.main_path, target_path)
        relative_source_path = os.path.relpath(source_path, target_path)
        relative_firmware_path = os.path.relpath(firmware_path, target_path)

        # Create Makefile to run in the specific software subdirectory
        makefile = f"""
# SPIKE parameter - can be overridden from command line
SPIKE ?= 0
CFLAGS += -DSPIKE=$(SPIKE)

# Target file name (without extension).
# This is the name of the compiled .hex file.
ifeq ($(SPIKE),1)
TARGET = spike_{name_key}
else
TARGET = {name_key}
endif

# List C source files here.
# Header files (.h) are automatically pulled in.
SRC += {relative_main_path} {relative_source_path}

SS_VER = SS_VER_1_0

#Add simpleserial project to build
FIRMWAREPATH = {relative_firmware_path}
include $(FIRMWAREPATH)/simpleserial/Makefile.simpleserial

include $(FIRMWAREPATH)/Makefile.inc
"""

        # Write the Makefile
        with open(makefile_path, 'w') as f:
            f.write(makefile)

    def find_source_file(self, directory):
        """Find the .c file in the software directory"""
        for filename in os.listdir(directory):
            if filename == f"{os.path.basename(directory)}.c":
                return os.path.join(directory, filename)
        return None

    def build_software(self, software_name, clean=False, force=False):
        """Build the software with a new Makefile
        
        Args:
            software_name (str): Name of the software
            clean (bool): Whether to clean before building
            force (bool): Whether to force rebuild even if already compiled
            
        Returns:
            bool: True if build was successful, False otherwise
        """
        
        # Check if already compiled and not forcing rebuild
        if not force and self.state[software_name]['compiled']:
            print(f"Software {software_name} already compiled. Use force=True to rebuild.")
            return True
        
        print(f"\n=== Building software: {software_name} ===")
        
        # Find the source file
        software_dir = self.get_dir(software_name)
        source_path = self.find_source_file(software_dir)
        if not source_path:
            print(f"Error: No .c file found in {software_dir}")
            self.state[software_name]['compile_status'] = 'error_no_source'
            self._save_state()
            return False
        
        print(f"Building file: {source_path}")
        
        # Create modified Makefile
        self.gen_makefile(source_path)
        
        original_cwd = os.getcwd()
        os.chdir(software_dir)  # Change to the software directory before running make

        try:
            # Clean if requested
            if clean:
                subprocess.run(['make', 'clean'], check=True)

            # Build with specified platform
            cmd = ['make', f'PLATFORM={self.platform}', 'CRYPTO_TARGET=NONE', 'CRYPTO_OPTIONS=NONE']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Build for spike tracing
            cmd.append('SPIKE=1')
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Update state
            self.state[software_name]['compiled'] = True
            self.state[software_name]['compiled_timestamp'] = datetime.datetime.now().isoformat()
            self.state[software_name]['compile_status'] = 'success'
            self.state[software_name]['dir_path'] = software_dir
            
            print(f"Successfully built {software_name}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error building {software_name}:")
            print(e.stderr)
            # Update state with error information
            self.state[software_name]['compiled'] = False
            self.state[software_name]['compile_status'] = f'error: {e.returncode}'
            return False
        except FileNotFoundError:
            print(f"Error: 'make' command not found. Ensure it's in your system's PATH.")
            self.state[software_name]['compile_status'] = 'error_make_not_found'
            return False
        except Exception as e:
            print(f"Exception during build: {e}")
            self.state[software_name]['compile_status'] = f'error: {str(e)}'
            return False
        finally:
            os.chdir(original_cwd)
            self._save_state()

    def build_all(self, clean=False, force=False):
        """Build all software
        
        Args:
            clean (bool): Whether to clean before building
            force (bool): Whether to force rebuild even if already compiled
            
        Returns:
            tuple: Lists of successful and failed software names
        """
        successful = []
        failed = []
        
        for software_dir in self.software_dirs:
            software_name = os.path.basename(software_dir)
            if self.build_software(software_name, clean, force):
                successful.append(software_name)
            else:
                failed.append(software_name)
        
        # Print summary
        print("\n=== Build Summary ===")
        print(f"Successful: {len(successful)}/{len(self.software_dirs)}")
        if failed:
            print(f"Failed: {len(failed)}/{len(self.software_dirs)}")
            print(f"Failed software: {', '.join(failed)}")
            
        return successful, failed


    def _set_sample_range(self, software_name, softcore):
        """Return the appropriate amount of samples to capture till trigger_low
        
        Args:
            software_name (str): Name of the software
            softcore (IbexChipWhisperer): Softcore on which to run and debug the software
            
        Returns:
            int: n samples to capture between trigger_high and trigger_low for software_name
        """
        
        # Adapted to Husky specifically
        MAX_CAPTURE_LEN = 1e6
        #SAMPLE_BUFFER_SIZE = 131124
        #softcore.scope.adc.samples = SAMPLE_BUFFER_SIZE
        softcore.scope.arm()
        
        EXECUTE_PROGRAM = '1'
        softcore.target.simpleserial_write(EXECUTE_PROGRAM, "A".encode())
        # Find number of relevant samples
        ret = softcore.scope.capture()
        if ret:
            raise Exception(f"Capture error! Returned {ret}")

        capture_interval = softcore.scope.adc.trig_count

        if capture_interval > MAX_CAPTURE_LEN:
            raise Exception("Capture exceeds the upper threshold of 1M samples.")
            
        return capture_interval

    def _capture_trace(self, software_name, softcore):
        """Captures trace between trigger_high and trigger_low
        
        Args:
            software_name (str): Name of the software
            softcore (IbexChipWhisperer): Softcore on which to run and debug the software
        """
        
        # Adapted to Husky specifically
        trig_count = self._set_sample_range(software_name, softcore) # Upper offset limit for capture
        SAMPLE_BUFFER_SIZE = 131124
        softcore.scope.adc.samples = SAMPLE_BUFFER_SIZE # Capture as many samples per iteration as possible
        softcore.scope.adc.offset = 0 # Initialize offset to start at trigger_high
        
        EXECUTE_PROGRAM = '1'
        composite_trace = np.array([])

        while softcore.scope.adc.offset < trig_count:
            # If last capture iteration, set samples to end at trigger_low
            if trig_count - softcore.scope.adc.offset < softcore.scope.adc.samples:
                softcore.scope.adc.samples = trig_count % softcore.scope.adc.samples
            
            softcore.scope.arm()
            softcore.target.simpleserial_write(EXECUTE_PROGRAM, "A".encode())
            # Find number of relevant samples
            ret = softcore.scope.capture()
            if ret:
                raise Exception("Capture error!")

            composite_trace = np.append(composite_trace, softcore.scope.get_last_trace())
            softcore.scope.adc.offset += softcore.scope.adc.samples

        return composite_trace
        
        

    def generate_data(self, software_name, softcore, repetitions = 1, platform="CW305_IBEX", force=False, save=True):
        """Generate data for a specific software
        
        Args:
            software_name (str): Name of the software
            softcore (IbexChipWhisperer): Softcore on which to run and debug the software
            repetitions (int): Amount of repeated traces to capture for the software
            platform (str): Name of the compile target platform
            force (bool): Whether to force data generation even if already done
            save (bool): Whether to save the data to disk
            
        Returns:
            bool: True if data generation was successful, False otherwise
        """
        if not force and self.state[software_name]['data_generated']:
            print(f"Data for {software_name} already generated. Use force=True to regenerate.")
            return True
            
        # Check if software has been compiled
        if not self.state[software_name]['compiled']:
            print(f"Software {software_name} has not been compiled yet. Compile first.")
            return False

        print(f"\n=== Generating data for: {software_name} ===")

        try:
            softcore.reload(self.get_ext(software_name))

            all_traces = []

            for i in range(repetitions):
                trace = self._capture_trace(software_name, softcore)
                all_traces.append(trace)
            self.last_trace = trace

            # Handle variable length traces by padding to longest
            trace_lengths = [len(trace) for trace in all_traces]
            max_length = max(trace_lengths)
            if len(set(trace_lengths)) > 1:
                print(f"Variable trace lengths detected. Padding to max length: {max_length}")
                print(f"Length range: {min(trace_lengths)} - {max_length}")
                
                # Pad shorter traces with zeros
                padded_traces = []
                for i, trace in enumerate(all_traces):
                    if len(trace) < max_length:
                        padded_trace = np.pad(trace, (0, max_length - len(trace)), mode='constant', constant_values=0)
                        padded_traces.append(padded_trace)
                    else:
                        padded_traces.append(trace)
                
                traces_matrix = np.array(padded_traces)
            else:
                # All traces same length
                traces_matrix = np.array(all_traces)

            if save:
                # Save the trace data
                data_path = os.path.join(self.src_dir,software_name,"trace.npy")
                np.save(data_path, traces_matrix)
                
                # Update state
                self.state[software_name]['data_generated'] = True
                self.state[software_name]['data_timestamp'] = datetime.datetime.now().isoformat()
                self._save_state()
            
            print(f"Successfully captured trace of length {len(trace)} for {software_name}")
            
            return True
        
        except Exception as e:
            error_message = str(e)
            print(f"Error generating data for {software_name}: {error_message}")        
            return False

    def generate_all_data(self, softcore, repetitions=1, force=False):
        """Generate data for all successfully compiled software
        
        Args:
            softcore (IbexChipWhisperer): Softcore on which to run and debug the software
            repetitions (int): How many repeated measurements should be captured per software
            force (bool): Whether to force data generation even if already done
            
        Returns:
            tuple: Lists of successful and failed software names
        """
        successful = []
        failed = []
        
        for software_dir in self.software_dirs:
            software_name = os.path.basename(software_dir)
            
            # Skip software that hasn't been compiled successfully
            if not self.state[software_name]['compiled']:
                print(f"Skipping {software_name} - not compiled")
                failed.append(software_name)
                continue
                
            if self.generate_data(software_name, softcore, repetitions=repetitions, force=force):
                successful.append(software_name)
            else:
                failed.append(software_name)
                
        print(f"\n=== Data Generation Summary ===")
        print(f"Successful: {len(successful)}/{len(successful) + len(failed)}")
        if failed:
            print(f"Failed: {len(failed)}/{len(successful) + len(failed)}")
            print(f"Failed software: {', '.join(failed)}")
            
        return successful, failed

    def _run_gdb_command_efficient(self, gdb, cmd, max_timeout=30, verbose=False):
        """
        Run a GDB command and proceed as soon as the prompt returns.
        Only waits as long as necessary, up to max_timeout.
        """
         # Clear any pending output in the buffer first
        try:
            while True:
                # Try to read any pending output with a very short timeout
                gdb.expect([pexpect.TIMEOUT, pexpect.EOF], timeout=0.0)
                break
        except:
            pass  # Buffer is now empty
        
        if verbose:
            print(f"Running: {cmd}")
        gdb.sendline(cmd)
        
        # Wait specifically for the GDB prompt to return
        try:
            gdb.expect(r'\(gdb\)', timeout=max_timeout)
            output = gdb.before.decode('utf-8', errors='ignore')
            return output
        except pexpect.TIMEOUT:
            print(f"Command '{cmd}' did not complete within {max_timeout} seconds")
            return gdb.before.decode('utf-8', errors='ignore')
        except pexpect.EOF:
            print(f"GDB process ended while running '{cmd}'")
            return gdb.before.decode('utf-8', errors='ignore')

    def _prime_debugger(self, gdb, output_path):
        commands = [
            "target extended-remote localhost:3333",
            "monitor reset halt",
            "load",
            "break main",
            "continue",
            "del 1",
            "set debug_skip_loop = 1",
            "break initialize_cw",
            "continue",
            "del 2",
            f"set logging file {output_path}/gdb_log.txt",
            "set logging overwrite on",
            "set logging enabled on"
        ]

        for cmd in commands:
            output = self._run_gdb_command_efficient(gdb, cmd)
            print(output)

    def _run_gdb_trace(self, gdb, software_name):
        print("\n--- Instructions between trigger_high and trigger_low ---\n")
        instruction_count = 0
        start_time = time.time()
        last_update = start_time
        
        while True:
            # Get and execute instruction
            instr_info = self._run_gdb_command_efficient(gdb, "x/i $pc")
            output = self._run_gdb_command_efficient(gdb, "stepi")
            instruction_count += 1
        
            # Update counter every 2 seconds
            current_time = time.time()
            if current_time - last_update > 2:
                elapsed = current_time - start_time
                rate = instruction_count / elapsed if elapsed > 0 else 0
        
                print(f"\n--- File: {software_name} | Instructions: {instruction_count} | Time: {elapsed:.1f}s | Rate: {rate:.1f} instr/sec ---")
                print(instr_info.strip())
                print(output.strip())
                
                # Clear and update in Jupyter
                clear_output(wait=True)
                last_update = current_time
            
            # Check for exit condition
            if "trigger_low" in output:
                break
        
        # Final stats
        total_time = time.time() - start_time
        print(f"\n--- End of instructions: {instruction_count} instructions in {total_time:.2f}s ---\n")

    def generate_labels(self, software_name, platform="CW305_IBEX", force=False):
        """Generate labels for a specific software via Spike simulation.
        
        Args:
            software_name (str): Name of the software
            platform (str): Name of the compile target platform
            force (bool): Whether to force label generation even if already done
            
        Returns:
            bool: True if label generation was successful, False otherwise
        """
        if not force and self.state[software_name]['labeled']:
            print(f"Labels for {software_name} already generated. Use force=True to regenerate.")
            return True
            
        # Check if software has been compiled
        if not self.state[software_name]['compiled']:
            print(f"Software {software_name} has not been compiled yet. Compile first.")
            return False
            
        software_dir = os.path.join(self.src_dir, software_name)
        
        tmp = self.get_ext(software_name, ext="elf").split("/")
        tmp[-1] = "spike_" + tmp[-1]
        elf_path = "/".join(tmp)

        spike_cmd_path = f'{software_dir}/spike_commands.txt'
        
        # Get start and end address
        getSymbol = lambda dump, symbol: f"0x{[line for line in dump.stdout.splitlines() if symbol in line][0].split()[0]}"
        
        try:
            print("Generating symbols")
            result = subprocess.run(
                ['riscv32-unknown-elf-nm', elf_path],
                capture_output=True,
                text=True
            )
            print("Generating Spike command file")
            start_addr, end_addr = getSymbol(result, "execute_cw"), getSymbol(result, "trigger_low")
            with open(spike_cmd_path, 'w') as f:
                f.write(
f"""until pc 0 {start_addr}
untiln pc 0 {end_addr}
quit
""")
        except Exception as e:
            print(f"Failed to find start and end addresses: {e}")
            return False

        # Run Spike to generate instruction dump
        try:
            print("Running Spike script")
            
            result = subprocess.run([
                'spike', '-d', 
                f'--debug-cmd={spike_cmd_path}',
                '--isa=rv32imc',
                '-m0x100000:0x100000,0x20000:0x10000,0x80000000:0x100000',
                elf_path
            ],
            capture_output=True,
            text=True
            )
        except Exception as e:
            print(f"Failed at Spike debugging stage: {e}")
            return False

        # Parse and save the labels
        try:
            raw_output = result.stderr.splitlines()[1:]
            spike_pattern = r'core\s+\d+:\s+0x[0-9a-f]+\s+\(0x[0-9a-f]+\)\s+(.*)'
            asm = [re.search(spike_pattern, line).group(1) for line in raw_output]
    
            with open(os.path.join(software_dir, "label_instr_reg.txt"), "w") as f:
                f.write("\n".join(asm))
            
            instr = [line.split()[0] for line in asm]
            with open(os.path.join(software_dir, "label_instr.txt"), "w") as f:
                f.write("\n".join(instr))
        except Exception as e:
            print(f"Failed parsing and saving results: {e}")
        
        # Update state after successful implementation
        self.state[software_name]['labeled'] = True
        self.state[software_name]['labeled_timestamp'] = datetime.datetime.now().isoformat()
        self._save_state()  # Save state after each successful run
        return True

    def generate_all_labels(self, force=False):
        """Generate labels for all software using spike
        
        Args:
            force (bool): Whether to force label generation even if already done
            
        Returns:
            tuple: Lists of successful and failed software names
        """
        successful = []
        failed = []
        
        for software_dir in self.software_dirs:
            software_name = os.path.basename(software_dir)
            
            # Skip software that don't have data generated
            if not self.state[software_name]['compiled']:
                print(f"Skipping {software_name} - has not been compiled.")
                failed.append(software_name)
                continue
            if not force and self.state[software_name]['labeled']:
                print(f"Skipping {software_name} - has already been labeled.")
                successful.append(software_name)
                continue
                
            if self.generate_labels(software_name, force=force):
                successful.append(software_name)
            else:
                failed.append(software_name)
                
        print(f"\n=== Label Generation Summary ===")
        print(f"Successful: {len(successful)}/{len(successful) + len(failed)}")
        if failed:
            print(f"Failed: {len(failed)}/{len(successful) + len(failed)}")
            print(f"Failed software: {', '.join(failed)}")
            
        return successful, failed
        
        
            
    def debug_labels(self, software_name, softcore, platform="CW305_IBEX", force=False):
        """Generate labels for a specific software
        
        Args:
            software_name (str): Name of the software
            softcore (IbexChipWhisperer): Softcore on which to run and debug the software
            platform (str): Name of the compile target platform
            force (bool): Whether to force label generation even if already done
            
        Returns:
            bool: True if label generation was successful, False otherwise
        """
        if not force and self.state[software_name]['debugged']:
            print(f"Labels for {software_name} already generated. Use force=True to regenerate.")
            return True
            
        # Check if software has been compiled
        if not self.state[software_name]['compiled']:
            print(f"Software {software_name} has not been compiled yet. Compile first.")
            return False
        
        # Empty interface for label generation - to be implemented by user
        software_dir = os.path.join(self.src_dir, software_name)
        hex_path = self.get_ext(software_name)
        elf_path = self.get_ext(software_name, ext="elf")

        # Start program awaiting debugger
        try: 
            # Cleanup - kill openocd processes before running
            subprocess.run(["killall", "openocd"], check=False)
            if reset_process:
                reset_process.terminate()
                reset_process.join(timeout=2)
        except Exception as e:
            print(f"Warning during cleanup: {str(e)}")
            pass

        try:
            print(f"Starting debugger for {software_name}...")
            # Use multiprocessing to avoid blocking
            reset_process = multiprocessing.Process(
                target=softcore.reload,
                args=(hex_path,),
                kwargs={"debug": True}
            )
            reset_process.start()

            print(f"Launching GDB for {software_name}...")
            gdb = pexpect.spawn(f"riscv32-unknown-elf-gdb {elf_path}")
    
            self._prime_debugger(gdb, software_dir)
    
            self._run_gdb_trace(gdb, software_name)
    
            print("Disconnecting gdb session\n")
            gdb.terminate()

            # Ensure reset process is terminated
            if reset_process and reset_process.is_alive():
                reset_process.terminate()
                reset_process.join(timeout=2)
            
            # Update state after successful implementation
            self.state[software_name]['debugged'] = True
            self.state[software_name]['debugged_timestamp'] = datetime.datetime.now().isoformat()
            self._save_state()  # Save state after each successful run
            return True
            
        except Exception as e:
            print(f"Debugging failed for {software_name}: {str(e)}")
            # Ensure cleanup
            if gdb:
                try:
                    gdb.terminate()
                except:
                    pass
            if reset_process and reset_process.is_alive():
                reset_process.terminate()
                reset_process.join(timeout=2)
            return False

    def debug_all_labels(self, softcore, force=False):
        """Generate labels for all software with data
        
        Args:
            softcore (IbexChipWhisperer): Softcore on which to run and debug the software
            force (bool): Whether to force label generation even if already done
            
        Returns:
            tuple: Lists of successful and failed software names
        """
        successful = []
        failed = []
        
        for software_dir in self.software_dirs:
            software_name = os.path.basename(software_dir)
            
            # Skip software that don't have data generated
            if not self.state[software_name]['compiled']:
                print(f"Skipping {software_name} - has not been compiled.")
                failed.append(software_name)
                continue
            if not force and self.state[software_name]['debugged']:
                print(f"Skipping {software_name} - has already been debugged.")
                successful.append(software_name)
                continue
                
            if self.debug_labels(software_name, softcore, force=force):
                successful.append(software_name)
            else:
                failed.append(software_name)
                
        print(f"\n=== Debug Generation Summary ===")
        print(f"Successful: {len(successful)}/{len(successful) + len(failed)}")
        if failed:
            print(f"Failed: {len(failed)}/{len(successful) + len(failed)}")
            print(f"Failed software: {', '.join(failed)}")
            
        return successful, failed

    def get_software_status(self, software_name=None):
        """Get status of one or all software
        
        Args:
            software_name (str, optional): Specific software name, or None for all software
            
        Returns:
            dict: Dictionary containing software status information
        """
        if software_name:
            if software_name in self.state:
                return {software_name: self.state[software_name]}
            else:
                return {software_name: "Software not found"}
        else:
            return self.state

    def list_software(self):
        """List all available software with their compilation status
        
        Returns:
            list: List of software names
        """
        print("Available software:")
        print(f"{'#':3s}\t{'Name':<20s}\t{'Compiled':8s}\t{'Data':8s}\t{'Labeled':8s}\t{'Debugged':8s}")
        print("-" * 70)
        
        for i, software_dir in enumerate(self.software_dirs):
            software_name = os.path.basename(software_dir)
            compile_status = "✓" if self.state[software_name]['compiled'] else "✗"
            data_status = "✓" if self.state[software_name]['data_generated'] else "✗"
            label_status = "✓" if self.state[software_name]['labeled'] else "✗"
            debug_status = "✓" if self.state[software_name]['debugged'] else "✗"
            
            print(f"{i+1:2d}.\t{software_name:<20s}\t{compile_status:^8s}\t{data_status:^8s}\t{label_status:^8s}\t{debug_status:^8s}")
            
        return [os.path.basename(d) for d in self.software_dirs]

class DataWrangler(ProjectBaseClass):
    """
    DataWrangler to handle data parsing and analysis.
    """
    def __init__(self, project_root_path="../../../", platform='CW305_IBEX'):
        """Initialize the DataWrangler
        Args:
            project_root_path (str): Source directory containing software folders
            platform (str): Target platform for compilation
        """
        super().__init__(project_root_path)
        self.platform = platform
        
        # Find all viable software directories
        self.software_dirs = self.get_software_directories()
        self.software_names = list(map(os.path.basename, self.software_dirs))
        self.software_dict = {key:val for key, val in zip(self.software_names, self.software_dirs)}
        
    def _get_fileformat(self, fileformat, loader, software_name=None):
        formatter = lambda x : f"{x}/{fileformat}"
        if software_name:
            return loader(formatter(self.software_dict[software_name]))
        return {key:loader(formatter(val)) for key, val in self.software_dict.items()}
        
    def get_traces(self, software_name=None):
        """
        Get trace data for specified software or all software.
        
        Args:
            software_name (str, optional): Name of the software to get traces for. 
                                          If None, gets traces for all software.
        
        Returns:
            dict or numpy.ndarray: Dictionary of traces for all software or array for specific software
        """
        loader = lambda x : np.load(x, allow_pickle=True)
        return self._get_fileformat("trace.npy", loader, software_name=software_name)
    
    def get_raw_labels(self, software_name=None, source='gdb'):
        """
        Get raw instruction data for specified software or all software.
        
        Args:
            software_name (str, optional): Name of the software to get labels for.
                                          If None, gets labels for all software.
            source (str): Data source - 'gdb' or 'spike'
        
        Returns:
            dict or str: Dictionary of raw labels for all software or string for specific software
        """
        def loader(f):
            try:
                with open(f, 'r') as file:
                    return file.read()
            except:
                return None

        filename = "gdb_log.txt" if source == 'gdb' else "label_instr.txt"
        return self._get_fileformat(filename, loader, software_name=software_name)
    
    def parse_raw_data(self, raw_data, source='gdb'):
        """
        Parse raw instruction data into instruction list.
        
        Args:
            raw_data (str): Raw instruction data
            source (str): Data source - 'gdb' or 'spike'
            
        Returns:
            list: List of parsed instructions with their details
        """
        if not raw_data:
            return []
        
        if source == 'gdb':
            raw_instructions = [line for line in raw_data.splitlines() if line.startswith("=>")]
            return [raw.split(":")[-1][1:].split("\t") for raw in raw_instructions]
        
        elif source == 'spike':
            return [line.split() for line in raw_data.splitlines()]
        
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def extract_instructions(self, instr_list):
        """
        Extract just the instruction names from parsed instruction list, excluding register operands.
        
        Args:
            instr_list (list): List of parsed instructions
            
        Returns:
            list: List of instruction names
        """
        return [entry[0] for entry in instr_list]
    
    def count_instructions(self, instructions):
        """
        Count occurrences of each instruction.
        
        Args:
            instructions (list): List of instruction names
            
        Returns:
            dict: Dictionary with instruction counts
        """
        count_dict = {}
        for instr in instructions:
            if instr not in count_dict:
                count_dict[instr] = 1
            else:
                count_dict[instr] += 1
        
        return count_dict
    
    def aggregate_counts(self, count_dicts):
        """
        Aggregate instruction counts across multiple software.
        
        Args:
            count_dicts (dict): Dictionary of instruction count dictionaries
            
        Returns:
            dict: Aggregated count dictionary
        """
        agr_dct = {}
        for dct in count_dicts.values():
            for key, val in dct.items():
                if key not in agr_dct:
                    agr_dct[key] = val
                else:
                    agr_dct[key] += val
        return agr_dct
    
    def parse_labels(self, software_name=None, source='gdb'):
        """
        Parse instruction logs into structured instruction data.
        
        Args:
            software_name (str, optional): Name of the software to parse labels for.
                                          If None, parses labels for all software.
            source (str): Data source - 'gdb' or 'spike'
        
        Returns:
            dict or list: Parsed instruction data
        """
        raw_data_dict = self.get_raw_labels(software_name, source=source)
        
        if software_name:
            return self.parse_raw_data(raw_data_dict, source)
        
        # Process for all software
        instruction_line_dict = {
            key: self.parse_raw_data(val, source) 
            for key, val in raw_data_dict.items() if val
        }
        instruction_dict = {
            key: self.extract_instructions(val) 
            for key, val in instruction_line_dict.items()
        }
        count_dict = {
            key: self.count_instructions(val) 
            for key, val in instruction_dict.items()
        }
        
        return {
            'instruction_lines': instruction_line_dict,
            'instructions': instruction_dict,
            'counts': count_dict,
            'aggregate_counts': self.aggregate_counts(count_dict)
        }

    def gen_labels(self, force=False):
        """
        Generate and save instruction labels for each software.
        
        Creates two files for each software in its respective directory:
        - debug_instr.txt: Contains only instruction names, one per line
        - debug_instr_reg.txt: Contains instructions with their registers/operands, one per line
        
        If a file already exists, it will be skipped unless force=True.
        
        Args:
            force (bool, optional): If True, overwrite existing files. Defaults to False.
            
        Returns:
            None
        """
        label_dict = self.parse_labels()["instruction_lines"]
        for sw, labels in label_dict.items():
            # Process instructions-only file
            label_path = os.path.join(self.get_dir(sw), "debug_instr.txt")
            
            # Only write if file doesn't exist or force=True
            if force or not os.path.exists(label_path):
                with open(label_path, "w") as f:
                    instructions = [instr[0] for instr in labels]
                    f.write("\n".join(instructions))
            
            # Process instructions-with-registers file independently
            reg_label_path = os.path.join(self.get_dir(sw), "debug_instr_reg.txt")
            
            # Only write if file doesn't exist or force=True
            if force or not os.path.exists(reg_label_path):
                with open(reg_label_path, "w") as f:
                    instr_reg_list = []
                    for instr_parts in labels:
                        if len(instr_parts) > 1:
                            full_instr = instr_parts[0] + " " + " ".join(instr_parts[1:])
                            instr_reg_list.append(full_instr.strip())
                        else:
                            instr_reg_list.append(instr_parts[0].strip())
                    
                    f.write("\n".join(instr_reg_list))

    def genDatasetFairseq(self, dataset_dict, name="dataset", manifest_dir=None):
        """
        Generate a dataset for Fairseq's FileTraceDataset by arranging directory structure and creating manifest.
        
        This method:
        1. Creates partition directories as specified in dataset_dict
        2. Copies trace files to appropriate locations
        3. Creates manifest files with batch information including trace paths, program labels, and trace lengths
        
        Args:
            dataset_dict (dict): Dictionary mapping partition names (e.g., 'train', 'test')
                                 to lists of software names to include in each partition
            name (str): Name of the dataset
            manifest_dir (str): The base directory for manifests
        
        Returns:
            None
            
        Side effects:
            - Creates directories for each partition
            - Copies trace NPY files to appropriate locations
            - Creates manifest JSON files for each partition
        """
        
        # Create the dataset directory
        dataset_path = os.path.join(self.root_path, "datasets", name)
        os.makedirs(dataset_path, exist_ok=True)
        
        # Parse the instruction labels for all software
        parsed_labels = self.parse_labels(source="spike")
        vocab = set()
        #agr_dict = parsed_labels["aggregate_counts"]
        #self.generateVocab(agr_dict.keys(), dataset_path)
        instruction_dict = parsed_labels['instructions'] if 'instructions' in parsed_labels else {}
        
        for partition, softwares in dataset_dict.items():
            # Create partition directory
            partition_dir = os.path.join(dataset_path, partition)
            os.makedirs(partition_dir, exist_ok=True)
            
            # Prepare manifest data
            manifest_data = {
                "num_batches": len(softwares),
                "batches": []
            }
            
            # Process each software
            for i, sw in enumerate(softwares):
                sw_dir = self.get_dir(sw)
                source_trace_path = os.path.join(sw_dir, "trace.npy")
                
                # Copy trace file to dataset directory with unique name
                dest_trace_filename = f"{sw}_traces.npy"
                dest_trace_path = os.path.join(partition_dir, dest_trace_filename)
                shutil.copy2(source_trace_path, dest_trace_path)
                
                # Get trace dimensions and handle 1D vectors
                trace_data = np.load(source_trace_path)
                if trace_data.ndim == 1:
                    # Reshape 1D vector to a 2D matrix with a single row
                    trace_data = trace_data.reshape(1, -1)
                    np.save(dest_trace_path, trace_data)
                else:
                    # Copy the file as is for 2D matrices
                    shutil.copy2(source_trace_path, dest_trace_path)
    
                num_traces = trace_data.shape[0]
                trace_length = trace_data.shape[1]
                
                # Get instruction sequence as space-separated string
                instruction_sequence = ""
                if sw in instruction_dict:
                    instruction_sequence = " ".join(instruction_dict[sw])
                    # Add to vocab
                    vocab = vocab.union(set(instruction_dict[sw]))
                
                # Add batch info to manifest
                batch_info = {
                    "traces": f"{manifest_dir}/{name}/{partition}/{dest_trace_filename}",
                    "program_label": instruction_sequence,
                    "num_traces": int(num_traces),
                    "trace_length": int(trace_length),
                    "name": sw
                }
                manifest_data["batches"].append(batch_info)
            
            # Write manifest to disk
            manifest_path = os.path.join(dataset_path, f"{partition}.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest_data, f, indent=4)

        # Write vocab to disk
        vocab_path = os.path.join(dataset_path, "tokenizer.vocab")
        with open(vocab_path, "w") as f:
            for token in sorted(vocab):  # Sort for consistent ordering
                f.write(f"{token}\n")
                
                    
        print(f"Dataset '{name}' generated successfully in {dataset_path}")
        print(f"Manifests created at {os.path.join(dataset_path, 'manifest_*.json')}")

    def generateVocab(self, labels, out_dir):
        """
        labels: list of strings, labels to generate vocab from
        out_path: str, path to the directory to write vocab file to
    
        Writes vocab.txt file to disk
        """
        out_path = os.path.join(out_dir, "tokenizer.vocab")
        vocab = ""
        for label in labels:
            vocab += f"{label}\n"
        vocab = vocab[:-1]
        with open(out_path, "w") as f:
            f.write(vocab)
                
    def wavWrite(self, fpath, trace_path):
        """
        Convert and write a trace file to WAV format.
        
        Args:
            fpath (str): Path to write .wav file to
            trace_path (str): Path to .npy np.array trace file to convert
            
        Returns:
            float: Duration of the trace in seconds
            
        Side effects:
            Writes trace to disk as a .wav file
        """
        from scipy.io.wavfile import write
        trace = np.load(trace_path)
        #rate in Hz
        rate = 44100
        # Convert .npy to .wav and write to disk
        write(fpath, rate, trace.astype(np.float32))
        # Return trace duration in seconds
        return len(trace)/rate
    
    def get_trace_counts(self):
        """
        Get the number of traces for each software, only first repetition.
        
        Returns:
            list: List of tuples (software_name, trace_count) sorted by count in descending order
        """
        trace_dict = self.get_traces()
        pairs = [(sw, len(trace[0])) for sw, trace in trace_dict.items()]
        pairs.sort(key=lambda x: x[1], reverse=True)
        return pairs
    
    def get_instruction_distribution(self):
        """
        Get the aggregate count of each instruction across all software.
        
        Returns:
            tuple: Two lists (instruction_names, counts) sorted by count in descending order
        """
        parsed_data = self.parse_labels()
        agr_dct = parsed_data['aggregate_counts']
        sorted_items = sorted(agr_dct.items(), key=lambda x: x[1], reverse=True)
        x, y = zip(*sorted_items) if sorted_items else ([], [])
        return x, y
    
    def calculate_snr(self, datagenerator, software_name):
        """
        Calculate signal-to-noise ratio for a software.
        
        Args:
            datagenerator: Data generator
            software_name (str): Name of the software
            
        Returns:
            float: Signal-to-noise ratio
        """
        # Implementation to be added
        pass

import riscv32_isg as isg

class DataSynthesizer(ProjectBaseClass):
    """
    Class for synthesizing data and creating C files for Ibex-related operations.
    Inherits from ProjectBaseClass to leverage common path handling and utility functions.
    """
    
    def __init__(self, project_root_path="../../../", allowed_instructions: Set[str] = None):
        """
        Initialize the DataSynthesizer class with project root path.
        
        Args:
            project_root_path (str): Path to the project root directory
        """
        super().__init__(project_root_path)
        self.allowed_instructions = allowed_instructions
        
    def gen_c_file(self, software_name: str, num_instructions: int, overwrite: bool = False,
                   allow_nop_fill: bool = False) -> str:
        """
        Create a .c file in the appropriate directory for the specified software.
        
        Args:
            software_name (str): Name of the software
            num_instructions (int): (approximate) number of ASM instructions to generate
            overwrite (bool): Whether to overwrite an existing file (default: False)
            
        Returns:
            str: Path to the created C file
            
        Raises:
            FileExistsError: If the file already exists and overwrite is False
            ValueError: If the software_name is invalid
        """
        # Validate software name
        if not software_name or not isinstance(software_name, str):
            raise ValueError("Software name must be a non-empty string")
        
        # Get the software directory
        software_dir = self.get_dir(software_name)
        
        # Create the directory if it doesn't exist
        if not os.path.exists(software_dir):
            os.makedirs(software_dir)
        
        # Create the path for the .c file
        c_file_path = os.path.join(software_dir, f"{software_name}.c")
        
        # Check if the file already exists
        if os.path.exists(c_file_path) and not overwrite:
            raise FileExistsError(f"The file {c_file_path} already exists. Set overwrite=True to replace it.")

        # Generate the contents of the file
        insngen = isg.RISCVAssemblyGenerator(allowed_instructions = self.allowed_instructions, allow_nop_fill=allow_nop_fill)
        buffer_register = insngen.buffer_register
        asm = insngen.generate_program(num_instructions = num_instructions)
        inline_asm = insngen.format_for_inline_asm(asm)

        c_transplant = f"""// Global buffer allocated at compile time with explicit alignment
static volatile int buffer[1024] __attribute__((aligned(8)));

int execute_cw (void)
{{
    volatile int *buf_ptr = &buffer[512]; // Point to middle of buffer
    
    register volatile int *buf_ptr_reg asm("{buffer_register}") = buf_ptr;
    register long saved_ra asm("x1");

    // Save return address
    asm volatile ("mv %0, ra" : "=r" (saved_ra));
    
    __asm__ volatile (
{inline_asm}
        :
        : "r" (buf_ptr_reg)
        : "memory"
    );

    // Restore return address  
    asm volatile ("mv ra, %0" : : "r" (saved_ra));

    return 0;
}}

void initialize_cw() {{}}
"""

        # Write contents to file
        with open(c_file_path, "w") as f:
            f.write(c_transplant)

        return c_file_path

    def extend_corpus(self, num_instructions: int, num_new_files: int, prefix: str = "isg") -> bool:
        """
        Generate more .c files containing random RISCV32IMC assembly instructions.
        All new softwares are named according to the convention: isg_<NUM_INSTRUCTIONS>_<ID>
        
        Args:
            num_instructions (int): (approximate) number of ASM instructions per file
            num_new_files (int): number of new files to generate
            prefix (str): name prefix for each of the created softwares
            
        Returns:
            bool: Success status of the generation
            
        Raises:
            pass
        """

        # Get ID of most recent file belonging to the num_instructions group
        ids = [int(_dir.split("_")[-1]) for _dir in os.listdir(self.src_dir) if f"{prefix}_{num_instructions}_" in _dir]
        start_id = 0 if not ids else max(ids) + 1

        try:
            for i in range(num_new_files):
                new_id = start_id + i
                self.gen_c_file(f"{prefix}_{num_instructions}_{new_id}", num_instructions)
        except Exception as e:
            print(f"Corpus extension failed at iteration {i}: ", e)
        
        

        
            
        

        
        
        
    

            