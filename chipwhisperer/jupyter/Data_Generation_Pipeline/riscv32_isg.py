from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Callable, Optional, Set
import random
import re

class Extension(Enum):
    """RISC-V extensions"""
    RV32I = "rv32i"      # Base integer instruction set
    RV32M = "rv32m"      # Integer multiplication and division
    RV32C = "rv32c"      # Compressed instructions
    RV32A = "rv32a"      # Atomic instructions
    RV32F = "rv32f"      # Single-precision floating-point
    RV32D = "rv32d"      # Double-precision floating-point

class InstructionClass(Enum):
    """Functional classification of instructions"""
    ALU = "alu"                    # Arithmetic/Logic operations
    LOAD = "load"                  # Memory load operations
    STORE = "store"                # Memory store operations
    BRANCH = "branch"              # Control flow - conditional
    JUMP = "jump"                  # Control flow - unconditional
    SYSTEM = "system"              # System calls, CSR access
    ATOMIC = "atomic"              # Atomic memory operations
    MULTIPLY = "multiply"          # Multiplication/division

class SyntaxType(Enum):
    """Instruction syntax patterns - base instruction formats from RISC-V ratified specification"""
    R_TYPE = "r_type"              # rd, rs1, rs2
    I_TYPE = "i_type"              # rd, rs1, imm
    S_TYPE = "s_type"              # rs2, offset(rs1)
    B_TYPE = "b_type"              # rs1, rs2, label
    U_TYPE = "u_type"              # rd, imm
    J_TYPE = "j_type"              # rd, label
    CSR_TYPE = "csr_type"          # rd, csr, rs1
    # Compressed formats from Table 37
    CR_TYPE = "cr_type"            # Register format
    CI_TYPE = "ci_type"            # Immediate format
    CSS_TYPE = "css_type"          # Stack-relative Store format
    CIW_TYPE = "ciw_type"          # Wide Immediate format
    CL_TYPE = "cl_type"            # Load format
    CS_TYPE = "cs_type"            # Store format
    CA_TYPE = "ca_type"            # Arithmetic format
    CB_TYPE = "cb_type"            # Branch/Arithmetic format
    CJ_TYPE = "cj_type"            # Jump format

class InstructionComplexity(Enum):
    """Instruction complexity levels"""
    SIMPLE = "simple"        # Basic instructions safe for filler
    COMPLEX = "complex"      # Instructions that generate sequences
    CONTROL = "control"      # Branches/jumps that shouldn't be filler

@dataclass
class InstructionSpec:
    """Specification for a RISC-V instruction"""
    mnemonic: str
    extension: Extension
    inst_class: InstructionClass
    syntax_type: SyntaxType
    complexity: InstructionComplexity
    description: str
    constraints: Optional[Dict] = None  # Additional constraints for operands

class RegisterType(Enum):
    """Register type classification"""
    ZERO = "zero"           # Hard-wired zero
    RETURN_ADDR = "ra"      # Return address
    STACK_PTR = "sp"        # Stack pointer  
    GLOBAL_PTR = "gp"       # Global pointer
    THREAD_PTR = "tp"       # Thread pointer
    TEMP = "temp"           # Temporary registers
    SAVED = "saved"         # Saved registers
    ARG = "arg"             # Argument registers

@dataclass
class RegisterSpec:
    """Specification for a RISC-V register"""
    name: str                    # x0, x1, etc.
    abi_name: str               # zero, ra, sp, etc.
    reg_type: RegisterType
    supports_compressed: bool
    description: str

class RegisterFile:
    """Manages RISC-V register specifications"""
    
    def __init__(self, excluded_registers = None):
        self.excluded_registers = set(excluded_registers or [])
        self.registers = [
            RegisterSpec("x0", "zero", RegisterType.ZERO, False, "Hard-wired zero"),
            RegisterSpec("x1", "ra", RegisterType.RETURN_ADDR, False, "Return address"),
            RegisterSpec("x2", "sp", RegisterType.STACK_PTR, False, "Stack pointer"),
            RegisterSpec("x3", "gp", RegisterType.GLOBAL_PTR, False, "Global pointer"),
            RegisterSpec("x4", "tp", RegisterType.THREAD_PTR, False, "Thread pointer"),
            RegisterSpec("x5", "t0", RegisterType.TEMP, False, "Temporary register 0"),
            RegisterSpec("x6", "t1", RegisterType.TEMP, False, "Temporary register 1"),
            RegisterSpec("x7", "t2", RegisterType.TEMP, False, "Temporary register 2"),
            RegisterSpec("x8", "s0", RegisterType.SAVED, True, "Saved register 0 / frame pointer"),
            RegisterSpec("x9", "s1", RegisterType.SAVED, True, "Saved register 1"),
            RegisterSpec("x10", "a0", RegisterType.ARG, True, "Function argument 0 / return value 0"),
            RegisterSpec("x11", "a1", RegisterType.ARG, True, "Function argument 1 / return value 1"),
            RegisterSpec("x12", "a2", RegisterType.ARG, True, "Function argument 2"),
            RegisterSpec("x13", "a3", RegisterType.ARG, True, "Function argument 3"),
            RegisterSpec("x14", "a4", RegisterType.ARG, True, "Function argument 4"),
            RegisterSpec("x15", "a5", RegisterType.ARG, True, "Function argument 5"),
            RegisterSpec("x16", "a6", RegisterType.ARG, False, "Function argument 6"),
            RegisterSpec("x17", "a7", RegisterType.ARG, False, "Function argument 7"),
            RegisterSpec("x18", "s2", RegisterType.SAVED, False, "Saved register 2"),
            RegisterSpec("x19", "s3", RegisterType.SAVED, False, "Saved register 3"),
            RegisterSpec("x20", "s4", RegisterType.SAVED, False, "Saved register 4"),
            RegisterSpec("x21", "s5", RegisterType.SAVED, False, "Saved register 5"),
            RegisterSpec("x22", "s6", RegisterType.SAVED, False, "Saved register 6"),
            RegisterSpec("x23", "s7", RegisterType.SAVED, False, "Saved register 7"),
            RegisterSpec("x24", "s8", RegisterType.SAVED, False, "Saved register 8"),
            RegisterSpec("x25", "s9", RegisterType.SAVED, False, "Saved register 9"),
            RegisterSpec("x26", "s10", RegisterType.SAVED, False, "Saved register 10"),
            RegisterSpec("x27", "s11", RegisterType.SAVED, False, "Saved register 11"),
            RegisterSpec("x28", "t3", RegisterType.TEMP, False, "Temporary register 3"),
            RegisterSpec("x29", "t4", RegisterType.TEMP, False, "Temporary register 4"),
            RegisterSpec("x30", "t5", RegisterType.TEMP, False, "Temporary register 5"),
            RegisterSpec("x31", "t6", RegisterType.TEMP, False, "Temporary register 6"),
        ]
    
    def get_registers_by_type(self, reg_types: Set[RegisterType]) -> List[RegisterSpec]:
        """Get all registers matching given types"""
        return [reg for reg in self.registers if reg.reg_type in reg_types]
    
    def get_compressed_registers(self, reg_types: Set[RegisterType] = None) -> List[RegisterSpec]:
        """Get registers that support compressed instructions"""
        regs = [reg for reg in self.registers if reg.supports_compressed]
        if reg_types:
            regs = [reg for reg in regs if reg.reg_type in reg_types]
        return regs
    
    def get_random_reg(self, allowed_types: Set[RegisterType] = None, exclusions: Set[str] = None, 
                      use_compressed: bool = False) -> str:
        """Get a random register name filtered by criteria"""
        if allowed_types is None:
            allowed_types = {RegisterType.TEMP, RegisterType.SAVED, RegisterType.ARG}
            
        if exclusions is None:
            exclusions = set()
        
        if use_compressed:
            candidates = self.get_compressed_registers(allowed_types)
        else:
            # Only use registers that DON'T support compressed instructions
            candidates = self.get_registers_by_type(allowed_types)
            candidates = [reg for reg in candidates if not reg.supports_compressed]
        
        # Filter out excluded registers
        all_exclusions = self.excluded_registers.union(exclusions)
        candidates = [reg for reg in candidates if reg.name not in all_exclusions]
        
        if not candidates:
            raise ValueError(f"No registers available for types: {allowed_types}, exclusions: {all_exclusions}")
        
        return random.choice(candidates).name

class SyntaxGenerator:
    """Generates instruction syntax based on type"""
    
    def __init__(self):
        self.label_counter = 0
        temp_register_file = RegisterFile()
        buffer_register = temp_register_file.get_random_reg(use_compressed=True)
        self.register_file = RegisterFile(excluded_registers=[buffer_register])
        self.buffer_register = buffer_register
        self.generators = {
            SyntaxType.R_TYPE: self._gen_r_type,
            SyntaxType.I_TYPE: self._gen_i_type,
            SyntaxType.S_TYPE: self._gen_s_type,
            SyntaxType.B_TYPE: self._gen_b_type,
            SyntaxType.U_TYPE: self._gen_u_type,
            SyntaxType.J_TYPE: self._gen_j_type,
            SyntaxType.CSR_TYPE: self._gen_csr_type,
            #### Compressed format generators ####
            SyntaxType.CR_TYPE: self._gen_cr_type,
            SyntaxType.CI_TYPE: self._gen_ci_type, 
            SyntaxType.CSS_TYPE: self._gen_css_type,
            SyntaxType.CIW_TYPE: self._gen_ciw_type,
            SyntaxType.CL_TYPE: self._gen_cl_type,
            SyntaxType.CS_TYPE: self._gen_cs_type,
            SyntaxType.CA_TYPE: self._gen_ca_type,
            SyntaxType.CB_TYPE: self._gen_cb_type,
            SyntaxType.CJ_TYPE: self._gen_cj_type,
        }
    
    def generate(self, spec: InstructionSpec, constraints: Dict = None) -> str:
        """Generate operands for given syntax type"""
        generator = self.generators.get(spec.syntax_type)
        if not generator:
            raise ValueError(f"No generator for syntax type: {syntax_type}")
        return generator(spec, constraints or {})

    ################## Special Cases #######################

    def _generate_jalr_sequence(self) -> str:
        """Generate AUIPC + filler + JALR sequence"""
        temp_reg = self.register_file.get_random_reg({RegisterType.TEMP})
        link_reg = self.register_file.get_random_reg({RegisterType.TEMP, RegisterType.SAVED, RegisterType.ARG}, 
                                                     exclusions={temp_reg})
        
        if not hasattr(self, '_main_generator'):
            raise Exception("SyntaxGenerator must be created from the RISCVAssemblyGenerator class to call its methods.")
        # We'll need a reference to the main generator for this
        self._main_generator.instruction_sequence.append(f"auipc {temp_reg}, 0")

        # Generate filler instructions using the main generator
        num_filler = random.randint(0, 3)
        offset = 8 # AUIPC + JALR base offset
        
        for _ in range(num_filler):
            # Ensure no register clobbering with link and temp reg.
            self._main_generator.generate_instruction({InstructionComplexity.SIMPLE},
                                                      excluded_registers={temp_reg, link_reg})
            last_instruction = self._main_generator.instruction_sequence[-1]
            if last_instruction.strip().startswith('c.'):
                offset += 2
            else:
                offset += 4
        
        return f"{link_reg}, {temp_reg}, {offset}"

    def _generate_compressed_jump_sequence(self) -> str:
        """Generate AUIPC + filler + compressed jump sequence (for both c.jr and c.jalr)"""
        temp_reg = self.register_file.get_random_reg({RegisterType.TEMP})
        
        if not hasattr(self, '_main_generator'):
            raise Exception("SyntaxGenerator must be created from the RISCVAssemblyGenerator class to call its methods.")
        
        # Generate AUIPC to load PC-relative address
        auipc_index = len(self._main_generator.instruction_sequence)
        self._main_generator.instruction_sequence.append(f"auipc {temp_reg}, 0")
        
        # Generate filler instructions
        num_filler = random.randint(0, 3)
        offset = 8  # AUIPC (4 bytes) + compressed jump (2 bytes) + c.addi (2 bytes) base offset

        add_index = random.randint(0,num_filler)
        
        for _ in range(num_filler):
            # Exclude temp_reg to avoid clobbering the address
            self._main_generator.generate_instruction({InstructionComplexity.SIMPLE},
                                                      excluded_registers={temp_reg})
            last_instruction = self._main_generator.instruction_sequence[-1]
            if last_instruction.strip().startswith('c.'):
                offset += 2
            else:
                offset += 4
        
        # Add offset to the temp register to point to instruction after the jump
        self._main_generator.instruction_sequence.append(f"c.addi {temp_reg}, {offset}")

        # Swap c.addi with a random filler instruction (if any exist)
        if num_filler > 0:
            addi_index = len(self._main_generator.instruction_sequence) - 1
            # Pick a random filler instruction to swap with (between auipc and c.addi)
            filler_start = auipc_index + 1
            filler_end = addi_index
            swap_index = random.randint(filler_start, filler_end - 1)
            
            # Swap the instructions
            self._main_generator.instruction_sequence[addi_index], self._main_generator.instruction_sequence[swap_index] = \
                self._main_generator.instruction_sequence[swap_index], self._main_generator.instruction_sequence[addi_index]

        
        # Return just the register (single register format for both c.jr and c.jalr)
        return temp_reg

    def _generate_addi16sp_sequence(self) -> str:
        """Generate ADDI16SP + filler + ADDI16SP sequence"""
        
        if not hasattr(self, '_main_generator'):
            raise Exception("SyntaxGenerator must be created from the RISCVAssemblyGenerator class to call its methods.")

        # Generate filler instructions
        num_filler = random.randint(0, 3)

        self._main_generator.instruction_sequence.append(f"c.addi16sp sp, 16")

        for _ in range(num_filler):
            # Exclude temp_reg to avoid clobbering the address
            self._main_generator.generate_instruction({InstructionComplexity.SIMPLE, InstructionComplexity.CONTROL})
        
        return f"sp, -16"

    def _generate_stack_pointer_sequence(self, spec: InstructionSpec) -> str:
        """Generate sequence for c.lwsp/c.swsp that sets up SP to point to inline buffer with interleaved filler"""
        
        if not hasattr(self, '_main_generator'):
            raise Exception("SyntaxGenerator must be created from the RISCVAssemblyGenerator class to call its methods.")
        
        from collections import deque
        
        # Choose a temporary register for SP manipulation
        temp_reg = self.register_file.get_random_reg({RegisterType.TEMP})
        
        # Generate the actual c.lwsp/c.swsp instruction operands
        if spec.mnemonic == "c.lwsp":
            rd = self.register_file.get_random_reg({RegisterType.TEMP, RegisterType.SAVED, RegisterType.ARG}, 
                                                   exclusions={temp_reg})
            offset = random.randint(0, 63) * 4  # Word-aligned, 6-bit immediate scaled by 4
            main_instruction = f"{spec.mnemonic} {rd}, {offset}(sp)"
        elif spec.mnemonic == "c.swsp":
            rs2 = self.register_file.get_random_reg(exclusions={temp_reg})
            offset = random.randint(0, 63) * 4  # Word-aligned, 6-bit immediate scaled by 4
            main_instruction = f"{spec.mnemonic} {rs2}, {offset}(sp)"
        
        # Define the required sequence in order as a queue
        required_queue = deque([
            f"c.mv {temp_reg}, sp",    # 1. Save current SP
            f"c.mv sp, %0",            # 2. Set SP to buffer address  
            main_instruction,          # 3. The actual load/store
            f"c.mv sp, {temp_reg}"     # 4. Restore original SP
        ])
        
        # Process the queue: pop required instruction, then add 0-2 filler instructions
        while required_queue:
            # Add the next required instruction
            required_instruction = required_queue.popleft()
            self._main_generator.instruction_sequence.append(required_instruction)
            
            # Generate 0-2 random filler instructions after each required instruction
            # (except we break immediately if queue is empty, so no filler after the last)
            if required_queue:  # Only add filler if there are more required instructions
                num_filler = random.randint(0, 2)
                for _ in range(num_filler):
                    self._main_generator.generate_instruction({InstructionComplexity.SIMPLE},
                                                              excluded_registers={temp_reg, "x2"})
        
        # Return empty string since we've already added everything to the sequence
        return ""

    ################## General Types #######################
  
    def _gen_r_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate R-type: rd, rs1, rs2"""
        excluded = constraints.get('excluded_registers', set())
        rd = self.register_file.get_random_reg(exclusions=excluded)
        rs1 = self.register_file.get_random_reg(exclusions=excluded)
        rs2 = self.register_file.get_random_reg(exclusions=excluded)
        return f"{rd}, {rs1}, {rs2}"
    
    def _gen_i_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate I-type: rd, rs1, imm"""
        # Special cases
        if spec.mnemonic == "nop":
            return ""
        elif spec.mnemonic == "jalr":
            return self._generate_jalr_sequence()

        excluded = constraints.get('excluded_registers', set())
        rd = self.register_file.get_random_reg(exclusions=excluded)

        rs1 = self.register_file.get_random_reg(exclusions=excluded)
        
        # Handle different immediate ranges
        imm_range = constraints.get('imm_range', (-2048, 2047))
        imm = random.randint(imm_range[0], imm_range[1])
        return f"{rd}, {rs1}, {imm}"
    
    def _gen_s_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate S-type: rs2, offset(rs1) or rd, offset(rs1) for loads"""
        excluded = constraints.get('excluded_registers', set())
        
        # Use inline assembly buffer reference if specified
        if spec.inst_class in [InstructionClass.LOAD, InstructionClass.STORE]:
            base_reg = "%0"  # Reference to buf_ptr input operand
            offset = random.randint(-100, 100) * 4  # Word-aligned offsets within buffer range
        else:
            base_reg = self.register_file.get_random_reg(exclusions=excluded)
            offset = random.randint(-2048, 2047)
        
        # For loads: rd, offset(base_reg)
        if spec.inst_class == InstructionClass.LOAD:
            rd = self.register_file.get_random_reg({RegisterType.TEMP, RegisterType.SAVED, RegisterType.ARG})
            return f"{rd}, {offset}({base_reg})"
        else:
            # For stores: rs2, offset(base_reg)
            rs2 = self.register_file.get_random_reg(exclusions=excluded)
            return f"{rs2}, {offset}({base_reg})"
    
    def _gen_b_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate B-type: rs1, rs2, label"""
        excluded = constraints.get('excluded_registers', set())
        rs1 = self.register_file.get_random_reg(exclusions=excluded)
        rs2 = self.register_file.get_random_reg(exclusions=excluded)
        label = constraints.get('target_label', self._gen_label())
        return f"{rs1}, {rs2}, {label}"
    
    def _gen_u_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate U-type: rd, imm or rd, label"""
        excluded = constraints.get('excluded_registers', set())
        rd = self.register_file.get_random_reg(exclusions=excluded)
        
        # Upper immediate is 20 bits
        imm = random.randint(0, (1 << 20) - 1)
        return f"{rd}, {imm}"
    
    def _gen_j_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate J-type: rd, label"""
        excluded = constraints.get('excluded_registers', set())
        rd = self.register_file.get_random_reg(exclusions=excluded)
        label = constraints.get('target_label', self._gen_label())
        return f"{rd}, {label}"
    
    def _gen_csr_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate CSR-type: rd, csr, rs1"""
        excluded = constraints.get('excluded_registers', set())
        rd = self.register_file.get_random_reg(exclusions=excluded)
        rs1 = self.register_file.get_random_reg(exclusions=excluded)
        # Common CSR addresses
        csrs = [0x300, 0x301, 0x304, 0x305, 0x340, 0x341, 0x342]
        csr = random.choice(csrs)
        return f"{rd}, {csr:#x}, {rs1}"

    ####### Compressed Generators ########
    
    def _gen_cr_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate CR-type: rd, rs2 or single register"""
        excluded = constraints.get('excluded_registers', set())
        
        # Special cases for compressed jumps
        if spec.mnemonic in ['c.jalr', 'c.jr']:
            return self._generate_compressed_jump_sequence()
        
        rd = self.register_file.get_random_reg(exclusions=excluded)
        rs2 = self.register_file.get_random_reg(exclusions=excluded)
        return f"{rd}, {rs2}"
    
    def _gen_ci_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        # All registers allowed according to spec
        """Generate CI-type: rd, imm or special formats"""
        excluded = constraints.get('excluded_registers', set())
        
        # Special cases
        if spec.mnemonic == 'c.nop':
            return ""
        elif spec.mnemonic == 'c.addi16sp':
            return self._generate_addi16sp_sequence()
        elif spec.mnemonic == 'c.lwsp':
            return self._generate_stack_pointer_sequence(spec)           

        rd = self.register_file.get_random_reg(exclusions=excluded)
        
        if 'imm_range' in constraints:
            imm_min, imm_max = constraints['imm_range']
            imm = random.randint(imm_min, imm_max)
        else:
            imm = random.randint(-32, 31)
            
        return f"{rd}, {imm}"

    def _gen_css_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        # All registers allowed according to spec
        """Generate CSS-type: rs2, offset(sp)"""
        excluded = constraints.get('excluded_registers', set())

        if spec.mnemonic == 'c.swsp':
            return self._generate_stack_pointer_sequence(spec)
        
        rs2 = self.register_file.get_random_reg(exclusions=excluded)
        offset = random.randint(0, 63) * 4  # Word-aligned
        return f"{rs2}, {offset}(sp)"
    
    def _gen_ciw_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate CIW-type: rd', uimm"""
        excluded = constraints.get('excluded_registers', set())
        rd = self.register_file.get_random_reg(exclusions=excluded, use_compressed=True)
        imm = 4  # Non-zero, word-aligned
        return f"{rd}, sp, {imm}"
    
    def _gen_cl_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate CL-type: rd', offset(rs1')"""
        excluded = constraints.get('excluded_registers', set())
        rd = self.register_file.get_random_reg({RegisterType.TEMP, RegisterType.SAVED, RegisterType.ARG}, 
                                               exclusions=excluded, use_compressed=True)

        base_reg = "%0"  # Reference to buf_ptr input operand
        offset = random.randint(0, 31) * 4  # Word-aligned offsets within buffer (and register) range
        return f"{rd}, {offset}({base_reg})"
    
    def _gen_cs_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate CS-type: rs2', offset(rs1')"""
        excluded = constraints.get('excluded_registers', set())
        rs = self.register_file.get_random_reg(exclusions=excluded, use_compressed=True)
        base_reg = "%0"  # Reference to buf_ptr input operand
        offset = random.randint(0, 31) * 4  # Word-aligned offsets within buffer (and register) range
        return f"{rs}, {offset}({base_reg})"
    
    def _gen_ca_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate CA-type: rd'/rs1', rs2'"""
        excluded = constraints.get('excluded_registers', set())
        rd_rs1 = self.register_file.get_random_reg(exclusions=excluded, use_compressed=True)
        rs2 = self.register_file.get_random_reg(exclusions=excluded, use_compressed=True)
        return f"{rd_rs1}, {rs2}"
    
    def _gen_cb_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate CB-type: rs1', offset or rs1', imm"""
        excluded = constraints.get('excluded_registers', set())
        rs1 = self.register_file.get_random_reg(exclusions=excluded, use_compressed=True)
        if 'imm_range' in constraints:
            imm_min, imm_max = constraints['imm_range']
            imm = random.randint(imm_min, imm_max)
            return f"{rs1}, {imm}"
        else:  # Default: use labels for branches
            label = constraints.get('target_label', self._gen_label())
            return f"{rs1}, {label}"
    
    def _gen_cj_type(self, spec: InstructionSpec, constraints: Dict) -> str:
        """Generate CJ-type: offset"""
        label = constraints.get('target_label', self._gen_label())
        return label

    ####### Generic ########
    
    def _gen_label(self) -> str:
        """Generate a unique label"""
        self.label_counter += 1
        return f"L{self.label_counter}"

class RISCVInstructionSet:
    """Database of RISC-V instructions"""
    
    def __init__(self, allow_nop_fill=False):
        self.instructions = []
        self._populate_rv32i()
        self._populate_rv32m()
        self._populate_rv32c()
        self.allow_nop_fill = allow_nop_fill
    
    def _populate_rv32i(self):
        """Populate RV32I base instruction set"""
        rv32i_specs = [
            # NOP pseudoinstruction (encoded as ADDI x0, x0, 0)
            InstructionSpec("nop", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "No operation (pseudoinstruction)"),
            
            # R-type ALU operations
            InstructionSpec("add", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Add"),
            InstructionSpec("sub", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Subtract"),
            InstructionSpec("and", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Bitwise AND"),
            InstructionSpec("or", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Bitwise OR"),
            InstructionSpec("xor", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Bitwise XOR"),
            InstructionSpec("sll", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Shift left logical"),
            InstructionSpec("srl", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Shift right logical"),
            InstructionSpec("sra", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Shift right arith"),
            InstructionSpec("slt", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Set less than"),
            InstructionSpec("sltu", Extension.RV32I, InstructionClass.ALU, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Set less than unsigned"),
            
            # I-type ALU operations
            InstructionSpec("addi", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "Add immediate"),
            InstructionSpec("andi", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "AND immediate"),
            InstructionSpec("ori", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "OR immediate"),
            InstructionSpec("xori", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "XOR immediate"),
            InstructionSpec("slli", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "Shift left logical imm", {"imm_range": (0, 31)}),
            InstructionSpec("srli", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "Shift right logical imm", {"imm_range": (0, 31)}),
            InstructionSpec("srai", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "Shift right arith imm", {"imm_range": (0, 31)}),
            InstructionSpec("slti", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "Set less than imm"),
            InstructionSpec("sltiu", Extension.RV32I, InstructionClass.ALU, SyntaxType.I_TYPE, 
                            InstructionComplexity.SIMPLE, "Set less than unsigned imm"),
            
            # Load instructions
            InstructionSpec("lb", Extension.RV32I, InstructionClass.LOAD, SyntaxType.S_TYPE, 
                            InstructionComplexity.COMPLEX, "Load byte"),
            InstructionSpec("lh", Extension.RV32I, InstructionClass.LOAD, SyntaxType.S_TYPE, 
                            InstructionComplexity.COMPLEX, "Load halfword"),
            InstructionSpec("lw", Extension.RV32I, InstructionClass.LOAD, SyntaxType.S_TYPE, 
                            InstructionComplexity.COMPLEX, "Load word"),
            InstructionSpec("lbu", Extension.RV32I, InstructionClass.LOAD, SyntaxType.S_TYPE, 
                            InstructionComplexity.COMPLEX, "Load byte unsigned"),
            InstructionSpec("lhu", Extension.RV32I, InstructionClass.LOAD, SyntaxType.S_TYPE, 
                            InstructionComplexity.COMPLEX, "Load halfword unsigned"),
            
            # Store instructions
            InstructionSpec("sb", Extension.RV32I, InstructionClass.STORE, SyntaxType.S_TYPE, 
                            InstructionComplexity.COMPLEX, "Store byte"),
            InstructionSpec("sh", Extension.RV32I, InstructionClass.STORE, SyntaxType.S_TYPE, 
                            InstructionComplexity.COMPLEX, "Store halfword"),
            InstructionSpec("sw", Extension.RV32I, InstructionClass.STORE, SyntaxType.S_TYPE, 
                            InstructionComplexity.COMPLEX, "Store word"),
            
            # Branch instructions
            InstructionSpec("beq", Extension.RV32I, InstructionClass.BRANCH, SyntaxType.B_TYPE, 
                            InstructionComplexity.CONTROL, "Branch if equal"),
            InstructionSpec("bne", Extension.RV32I, InstructionClass.BRANCH, SyntaxType.B_TYPE, 
                            InstructionComplexity.CONTROL, "Branch if not equal"),
            InstructionSpec("blt", Extension.RV32I, InstructionClass.BRANCH, SyntaxType.B_TYPE, 
                            InstructionComplexity.CONTROL, "Branch if less than"),
            InstructionSpec("bge", Extension.RV32I, InstructionClass.BRANCH, SyntaxType.B_TYPE, 
                            InstructionComplexity.CONTROL, "Branch if greater equal"),
            InstructionSpec("bltu", Extension.RV32I, InstructionClass.BRANCH, SyntaxType.B_TYPE, 
                            InstructionComplexity.CONTROL, "Branch if less than unsigned"),
            InstructionSpec("bgeu", Extension.RV32I, InstructionClass.BRANCH, SyntaxType.B_TYPE, 
                            InstructionComplexity.CONTROL, "Branch if greater equal unsigned"),
            
            # Jump instructions
            InstructionSpec("jal", Extension.RV32I, InstructionClass.JUMP, SyntaxType.J_TYPE, 
                            InstructionComplexity.CONTROL, "Jump and link"),
            InstructionSpec("jalr", Extension.RV32I, InstructionClass.JUMP, SyntaxType.I_TYPE, 
                            InstructionComplexity.COMPLEX, "Jump and link register", {"imm_range": (4, 4)}),
            
            # Upper immediate
            InstructionSpec("lui", Extension.RV32I, InstructionClass.ALU, SyntaxType.U_TYPE, 
                            InstructionComplexity.SIMPLE, "Load upper immediate"),
            InstructionSpec("auipc", Extension.RV32I, InstructionClass.ALU, SyntaxType.U_TYPE, 
                            InstructionComplexity.SIMPLE, "Add upper immediate to PC"),
        ]
        self.instructions.extend(rv32i_specs)
    
    def _populate_rv32m(self):
        """Populate RV32M multiplication extension"""
        rv32m_specs = [
            InstructionSpec("mul", Extension.RV32M, InstructionClass.MULTIPLY, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Multiply"),
            InstructionSpec("mulh", Extension.RV32M, InstructionClass.MULTIPLY, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Multiply high"),
            InstructionSpec("mulhsu", Extension.RV32M, InstructionClass.MULTIPLY, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Multiply high signed-unsigned"),
            InstructionSpec("mulhu", Extension.RV32M, InstructionClass.MULTIPLY, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Multiply high unsigned"),
            InstructionSpec("div", Extension.RV32M, InstructionClass.MULTIPLY, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Divide"),
            InstructionSpec("divu", Extension.RV32M, InstructionClass.MULTIPLY, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Divide unsigned"),
            InstructionSpec("rem", Extension.RV32M, InstructionClass.MULTIPLY, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Remainder"),
            InstructionSpec("remu", Extension.RV32M, InstructionClass.MULTIPLY, SyntaxType.R_TYPE, 
                            InstructionComplexity.SIMPLE, "Remainder unsigned"),
        ]
        self.instructions.extend(rv32m_specs)
    
    def _populate_rv32c(self):
        """Populate RV32C compressed extension (subset)"""
        rv32c_specs = [
            # FIXME: Polish ordering, a bit messy
            InstructionSpec("c.add", Extension.RV32C, InstructionClass.ALU, SyntaxType.CR_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed add"),
            InstructionSpec("c.and", Extension.RV32C, InstructionClass.ALU, SyntaxType.CA_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed and"),
            InstructionSpec("c.or", Extension.RV32C, InstructionClass.ALU, SyntaxType.CA_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed or"),
            InstructionSpec("c.xor", Extension.RV32C, InstructionClass.ALU, SyntaxType.CA_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed xor"),
            InstructionSpec("c.mv", Extension.RV32C, InstructionClass.ALU, SyntaxType.CR_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed move"),
            InstructionSpec("c.sub", Extension.RV32C, InstructionClass.ALU, SyntaxType.CA_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed subtract"),
            
            # CI-type instructions
            InstructionSpec("c.addi", Extension.RV32C, InstructionClass.ALU, SyntaxType.CI_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed add immediate"),
            InstructionSpec("c.slli", Extension.RV32C, InstructionClass.ALU, SyntaxType.CI_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed shift left logical immediate", {"imm_range": (1, 31)}),
            InstructionSpec("c.srli", Extension.RV32C, InstructionClass.ALU, SyntaxType.CB_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed shift right logical immediate", {"imm_range": (1, 31)}),
            InstructionSpec("c.srai", Extension.RV32C, InstructionClass.ALU, SyntaxType.CB_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed shift right arithmetic immediate", {"imm_range": (1, 31)}),
            InstructionSpec("c.andi", Extension.RV32C, InstructionClass.ALU, SyntaxType.CB_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed and immediate", {"imm_range": (-32, 31)}),
            InstructionSpec("c.nop", Extension.RV32C, InstructionClass.ALU, SyntaxType.CI_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed no operation", {"no_operands": True}),
            InstructionSpec("c.li", Extension.RV32C, InstructionClass.ALU, SyntaxType.CI_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed load immediate"),
            InstructionSpec("c.lui", Extension.RV32C, InstructionClass.ALU, SyntaxType.CI_TYPE, 
                            InstructionComplexity.SIMPLE, "Compressed load upper immediate", {"imm_range": (1, 31)}),
            
            # Load instructions
            InstructionSpec("c.lw", Extension.RV32C, InstructionClass.LOAD, SyntaxType.CL_TYPE, 
                            InstructionComplexity.COMPLEX, "Compressed load word"),
            InstructionSpec("c.lwsp", Extension.RV32C, InstructionClass.LOAD, SyntaxType.CI_TYPE, 
                            InstructionComplexity.COMPLEX, "Compressed load word stack pointer"),

            # Store instructions
            InstructionSpec("c.sw", Extension.RV32C, InstructionClass.STORE, SyntaxType.CS_TYPE, 
                            InstructionComplexity.COMPLEX, "Compressed store word"),
            InstructionSpec("c.swsp", Extension.RV32C, InstructionClass.STORE, SyntaxType.CSS_TYPE, 
                            InstructionComplexity.COMPLEX, "Compressed store word stack pointer"),
            
            # Branch instructions
            InstructionSpec("c.beqz", Extension.RV32C, InstructionClass.BRANCH, SyntaxType.CB_TYPE, 
                            InstructionComplexity.CONTROL, "Compressed branch if equal zero"),
            InstructionSpec("c.bnez", Extension.RV32C, InstructionClass.BRANCH, SyntaxType.CB_TYPE, 
                            InstructionComplexity.CONTROL, "Compressed branch if not equal zero"),
            
            # Jump instructions
            InstructionSpec("c.jalr", Extension.RV32C, InstructionClass.JUMP, SyntaxType.CR_TYPE, 
                            InstructionComplexity.COMPLEX, "Compressed jump and link register"),
            InstructionSpec("c.jr", Extension.RV32C, InstructionClass.JUMP, SyntaxType.CR_TYPE, 
                            InstructionComplexity.COMPLEX, "Compressed jump register"),
            InstructionSpec("c.jal", Extension.RV32C, InstructionClass.JUMP, SyntaxType.CJ_TYPE,
                            InstructionComplexity.CONTROL, "Compressed jump and link"),
            InstructionSpec("c.j", Extension.RV32C, InstructionClass.JUMP, SyntaxType.CJ_TYPE, 
                            InstructionComplexity.CONTROL, "Compressed jump"),

            # Stack pointer specific
            InstructionSpec("c.addi16sp", Extension.RV32C, InstructionClass.ALU, SyntaxType.CI_TYPE, 
                            InstructionComplexity.COMPLEX, "Compressed add immediate to SP"),
            InstructionSpec("c.addi4spn", Extension.RV32C, InstructionClass.ALU, SyntaxType.CIW_TYPE, 
                            InstructionComplexity.COMPLEX, "Compressed add immediate 4x to SP"),
            
            # Ignored fence, fence.tso, pause, ecall, ebreak, and pseudoinstructions other than nop
        ]
        self.instructions.extend(rv32c_specs)
    
    def get_instructions_by_extension(self, extension: Extension) -> List[InstructionSpec]:
        """Get all instructions for a specific extension"""
        return [inst for inst in self.instructions if inst.extension == extension]
    
    def get_instructions_by_class(self, inst_class: InstructionClass) -> List[InstructionSpec]:
        """Get all instructions for a specific class"""
        return [inst for inst in self.instructions if inst.inst_class == inst_class]
    
    def get_random_instruction(self, extensions: Set[Extension] = None, 
                               complexity: Set[InstructionComplexity] = None,
                               instruction_names: Set[str] = None) -> InstructionSpec:
        """Get a random instruction, optionally filtered by extensions or complexity"""
        
        candidates = self.instructions
        
        if extensions:
            candidates = [inst for inst in candidates if inst.extension in extensions]
        if complexity:
            candidates = [inst for inst in candidates if inst.complexity in complexity]
        if instruction_names:
            candidates = [inst for inst in candidates if inst.mnemonic in instruction_names]

        if self.allow_nop_fill:
            candidates.extend([inst for inst in self.instructions if inst.mnemonic == "nop"])
        
        if not candidates:
            raise ValueError("No instructions available for given extensions")
        
        return random.choice(candidates)

class RISCVAssemblyGenerator:
    """Main assembly generator class"""
    
    def __init__(self, enabled_extensions: Set[Extension] = None,
                 allowed_instructions: Set[str] = None,
                 allow_nop_fill: bool = False):
        self.instruction_set = RISCVInstructionSet(allow_nop_fill=allow_nop_fill)
        self.syntax_generator = SyntaxGenerator()
        # Set up circular reference so syntax generator can call back
        self.syntax_generator._main_generator = self
        self.buffer_register = self.syntax_generator.buffer_register
        self.enabled_extensions = enabled_extensions or {Extension.RV32I, Extension.RV32M, Extension.RV32C}
        self.allowed_instructions = allowed_instructions
        self.generated_labels = []

        self.instruction_sequence = []
    
    def generate_instruction(self, complexity: Set[InstructionComplexity] = None,
                            excluded_registers: Set[str] = None) -> None:
        """Generate a single random instruction, with label if needed"""
        if excluded_registers is None:
            excluded_registers = set()
            
        spec = self.instruction_set.get_random_instruction(self.enabled_extensions, complexity, self.allowed_instructions)
        constraints = spec.constraints.copy() if spec.constraints else {}

        # Pass register exclusions through constraints
        constraints['excluded_registers'] = excluded_registers
        
        # Check if this instruction needs a label, non complex jump instructions can use labels
        needs_label = (
                       (spec.inst_class == InstructionClass.BRANCH) or 
                       (spec.inst_class == InstructionClass.JUMP and (spec.complexity != InstructionComplexity.COMPLEX))
                      )
        if needs_label:
            next_label = f"L{len(self.generated_labels) + 1}"
            self.generated_labels.append(next_label)
            constraints['target_label'] = next_label
        
        operands = self.syntax_generator.generate(spec, constraints)
        
        if spec.mnemonic not in ['c.swsp','c.lwsp']: # Not elegant, but hey, it works
            self.instruction_sequence.append(f"{spec.mnemonic} {operands}")
        
        if needs_label:
            self.instruction_sequence.append(f"{next_label}:")
    
    def generate_program(self, num_instructions: int = 10) -> str:
        """Generate an assembly program snippet for inline use in C"""
        self.instruction_sequence = []
        while len(self.instruction_sequence) < num_instructions:
            self.generate_instruction()
        
        # Postprocess to add .option directives around non-compressed instruction sequences
        processed_sequence = []
        in_norvc_block = False
        
        for line in self.instruction_sequence:
            if line.endswith(':'):
                processed_sequence.append(line)
            else:
                is_compressed = line.strip().startswith('c.')
                
                if not is_compressed and not in_norvc_block:
                    # Start of non-compressed sequence
                    processed_sequence.append(".option norvc")
                    in_norvc_block = True
                elif is_compressed and in_norvc_block:
                    # End of non-compressed sequence, start compressed
                    processed_sequence.append(".option rvc")
                    in_norvc_block = False
                
                processed_sequence.append(f"    {line}")
        
        # Close any open norvc block at the end
        if in_norvc_block:
            processed_sequence.append(".option rvc")
        
        result = "\n".join(processed_sequence)
        self.instruction_sequence = []
        
        return result

    def format_for_inline_asm(self, assembly_code: str) -> str:
        """Format assembly code for inline assembly compatibility"""
        lines = assembly_code.split('\n')
        formatted_lines = []
        
        # Add quotes around all non-empty lines
        for line in lines:
            if line.strip():  # Skip empty lines
                formatted_lines.append(f'"{line}\\n"')
        
        # Join all lines and replace labels with GCC inline asm format
        result = '\n'.join(formatted_lines)
        result = re.sub(r'L(\d+)', r'L\1%=', result)
        
        return result