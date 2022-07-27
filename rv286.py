from elftools.elf.elffile import ELFFile
from riscemu.decoder import decode
import sys

filename = sys.argv[1]

f = open(filename, "rb")
ef = ELFFile(f)

codes = ef.get_section_by_name(".text")
code = codes.data()
insts = []

i = 0
for c in code:
    if i % 4 == 0:
        insts.append([c])
    else:
        insts[len(insts) - 1].append(c)
    i += 1

textstart = codes["sh_addr"]

# Register mapping:
# a0 -> ebx
# a1 -> -    Leaving ecx unmapped frees it as a spare register, especially
#            useful in the x86 shift instructions.
# a2 -> edx
# a3 -> esi
# a4 -> edi
# a5 -> ebp
# a7 -> eax

print("global _start")
print()

print("textstart equ " + str(textstart))
print()

print("section .data")
print()

num_segs = ef.num_segments()
first_vaddr = ef.get_segment(0)["p_vaddr"]
rawcode = []

prev_addr = first_vaddr
for segment in ef.iter_segments():
    paddr = segment["p_vaddr"]
    psize = segment["p_memsz"]
    for section in ef.iter_sections():
        saddr = section["sh_addr"]
        ssize = section["sh_size"]
        if saddr == 0:
            continue
        if saddr >= paddr and saddr < paddr + psize:
            rawcode += [0] * (saddr - prev_addr)
            print(hex(saddr), hex(len(rawcode)), file=sys.stderr)
            sdata = [int(i) for i in section.data()]
            rawcode += sdata
            prev_addr = saddr + ssize

print("rawcodee: db", ",".join(map(str, rawcode)))
print("rawcode equ rawcodee + " + str(textstart - first_vaddr))
print()

print("jumptable: dd " + ",".join(["inst_" + str(i) for i in range(0, len(code), 4)]))
print()

print("safeplace: dd 0")
print("safeplace1: dd 0")
print("safeplace2: dd 0")
print("sysret: dd 0")

regmaps = [ "dword 0", 1, "esp" ] + [ i for i in range(3, 10) ] + [ "ebx", 11, "edx", "esi", "edi", "ebp", 16, "eax" ] + [ i for i in range(18, 32) ]
print("x0: dd 0")
print("x1: dd 0")
for i in range(3, 10):
    print("x" + str(i) + ": dd 0")
print("x11: dd 0")
print("x16: dd 0")
for i in range(18, 32):
    print("x" + str(i) + ": dd 0")
print()

print("stack: dd " + ",".join(["0"] * 8192))
print()

def regs(*reg):
    if not "eax" in reg:
        return "eax"

    if not "ebx" in reg:
        return "ebx"

    if not "edx" in reg:
        return "edx"

    if not "esi" in reg:
        return "esi"

    if not "edi" in reg:
        return "edi"

    if not "ebp" in reg:
        return "ebp"

def regreginst(x86_name, tgt, reg1, reg2):
    if tgt != "dword 0":
        if isinstance(reg1, str):
            print("mov ecx,", reg1)
        else:
            print("mov ecx, [x" + str(reg1) + "]")

        if isinstance(reg2, str):
            print(x86_name, "ecx,", reg2)
        else:
            print(x86_name, "ecx, [x" + str(reg2) + "]")

        if isinstance(tgt, str):
            print("mov", tgt + ", ecx")
        else:
            print("mov [x" + str(tgt) + "], ecx")
    else:
        print("nop")

def regimminst(x86_name, tgt, reg1, imm):
    if tgt != "dword 0":
        if tgt == reg1:
            if isinstance(tgt, str):
                print(x86_name, tgt + ",", imm)
            else:
                print(x86_name + " dword [x" + str(tgt) + "],", imm)
        else:
            if isinstance(tgt, str):
                if isinstance(reg1, str):
                    print("mov", tgt + ",", reg1)
                else:
                    print("mov", tgt + ", [x" + str(reg1) + "]")
                print(x86_name, tgt + ",", imm)
            else:
                if isinstance(reg1, str):
                    print("mov ecx,", reg1)
                else:
                    print("mov ecx, [x" + str(reg1) + "]")

                print(x86_name, "ecx,", imm)

                print("mov [x" + str(tgt) + "], ecx")
    else:
        print("nop")

def shift_regreg(tgt, reg1, reg2, x86_inst):
    if tgt != "dword 0":
        safereg = regs(tgt, reg1, reg2)
        print("mov [safeplace],", safereg)

        if isinstance(reg1, str):
            print("mov", safereg + ",", reg1)
        else:
            print("mov", safereg + ", [x" + str(reg1) + "]")

        if isinstance(reg2, str):
            print("mov ecx,", reg2)
        else:
            print("mov ecx, [x" + str(reg2) + "]")

        print(x86_inst, safereg + ", cl")

        if isinstance(tgt, str):
            print("mov", tgt + ",", safereg)
        else:
            print("mov [x" + str(tgt) + "],", safereg)

        print("mov", safereg + ", [safeplace]")
    else:
        print("nop")

def slt_regreg(tgt, reg1, reg2, x86_inst):
    tgt = regmaps[params[0]]
    reg1 = regmaps[params[1]]
    reg2 = regmaps[params[2]]
    safereg = regs(tgt, reg1, reg2)
    safereg1 = regs(tgt, reg1, reg2, safereg)

    if tgt != "dword 0":
        if isinstance(reg1, str):
            if reg1 == "dword 0":
                print("mov [safeplace], " + safereg)
                print("mov " + safereg + ", 0")
                reg1 = safereg
                if isinstance(reg2, str):
                    print("cmp", reg1 + ",", reg2)
                else:
                    print("cmp", reg1 + ", [x" + str(reg2) + "]")
                print("mov " + safereg + ", [safeplace]")
            else:
                if isinstance(reg2, str):
                    print("cmp", reg1 + ",", reg2)
                else:
                    print("cmp", reg1 + ", [x" + str(reg2) + "]")
        else:
            if isinstance(reg2, str):
                print("cmp [x" + str(reg1) + "],", reg2)
            else:
                print("mov [safeplace], " + safereg)
                print("mov " + safereg + ", [x" + str(reg1) + "]")
                print("cmp " + safereg + ", [x" + str(reg2) + "]")
                print("mov " + safereg + ", [safeplace]")

        print("mov [safeplace], " + safereg)
        print("mov " + safereg + ", 1")
        if isinstance(tgt, str):
            print("mov", tgt + ", 0")
            print(x86_inst, tgt + ", " + safereg)
        else:
            print("mov [safeplace1], " + safereg1)
            print("mov " + safereg1 + ", 0")
            print(x86_inst, safereg1 + ", " + safereg)
            print("mov [x" + str(tgt) + "], " + safereg1)
            print("mov " + safereg1 + ", [safeplace1]")
        print("mov " + safereg + ", [safeplace]")
    else:
        print("nop")

def slt_regimm(tgt, reg1, imm, x86_inst):
    safereg = regs(tgt, reg1)
    safereg1 = regs(tgt, reg1, safereg)

    if tgt != "dword 0":
        if isinstance(reg1, str):
            if reg1 == "dword 0":
                print("mov [safeplace], " + safereg)
                print("mov " + safereg + ", 0")
                reg1 = safereg
                print("cmp", reg1 + ",", str(imm))
                print("mov " + safereg + ", [safeplace]")
            else:
                print("cmp", reg1 + ",", str(imm))
        else:
            print("cmp [x" + str(reg1) + "], dword", imm)

        print("mov [safeplace], " + safereg)
        print("mov " + safereg + ", 1")
        if isinstance(tgt, str):
            print("mov", tgt + ", 0")
            print(x86_inst, tgt + ", " + safereg)
        else:
            print("mov [safeplace1], " + safereg1)
            print("mov " + safereg1 + ", 0")
            print(x86_inst, safereg1 + ", " + safereg)
            print("mov [x" + str(tgt) + "], " + safereg1)
            print("mov " + safereg1 + ", [safeplace1]")
        print("mov " + safereg + ", [safeplace]")
    else:
        print("nop")

def load_inst(tgt, reg1, offset, inst):
    safereg = regs(tgt, reg1)
    safereg1 = regs(tgt, reg1, safereg)
    size = "dword"
    if inst.startswith("lb"):
        size = "byte"
    elif inst.startswith("lh"):
        size = "word"

    extend = "sx"
    if inst.endswith("u"):
        extend = "zx"
    elif inst == "lw":
        extend = ""

    if tgt != "dword 0":
        if isinstance(reg1, str):
            print("add", reg1 + ", rawcode -", textstart)
            print("add", reg1 + ",", str(offset))
            print("mov" + extend, "ecx, " + size + " [" + reg1 + "]")
            print("sub", reg1 + ",", str(offset))
            print("sub", reg1 + ", rawcode -", textstart)
        else:
            print("mov [safeplace],", safereg)
            print("mov " + safereg + ", [x" + str(reg1) + "]")
            print("add " + safereg + ", " + str(offset))
            print("add", safereg + ", rawcode -", textstart)
            print("mov" + extend, "ecx, " + size + " [" + safereg + "]")
            print("mov " + safereg + ", [safeplace]")
        
        if isinstance(tgt, str):
            print("mov ", tgt + ", ecx")
        else:
            print("mov [x" + str(tgt) + "], ecx")

def branch_cond(reg1, reg2, joffset, x86_jump):
    safereg = regs(reg1, reg2)
    if isinstance(reg1, str):
        if reg1 == "dword 0":
            print("mov [safeplace], " + safereg)
            print("mov " + safereg + ", 0")
            reg1 = safereg
        if isinstance(reg2, str):
            print("cmp", reg1 + ",", reg2)
        else:
            print("cmp", reg1 + ", [x" + str(reg2) + "]")
        if reg1 == safereg:
            print("mov", safereg + ", [safeplace]")
    else:
        if isinstance(reg2, str):
            print("cmp dword [x" + str(reg1) + "],", reg2)
        else:
            print("mov [safeplace], " + safereg)
            print("mov " + safereg + ", [x" + str(reg1) + "]")
            print("cmp " + safereg + ", [x" + str(reg2) + "]")
            print("mov " + safereg + ", [safeplace]")
    print(x86_jump, "inst_" + str(pc + params[2]))

print("%include \"syscalls.s\"")
print()

print("section .text")
print()

print("_start:")
print("mov ebx, esp")
print("mov ecx, [ebx]") # argc into ecx
print(".argv_loop:")
print("add ebx, 4")
print("sub dword [ebx], rawcode -", str(textstart))
print("dec ecx")
print("cmp ecx, 0")
print("jne .argv_loop")
print("mov ebx, 0")
print("sub esp, rawcode -", str(textstart))
print("jmp _start1")

pc = 0
for inst in insts:
    di = decode(inst)
    iname = di[0]
    params = di[1]

    if pc == ef["e_entry"] - textstart:
        print("_start1:")

    # DEBUG
    print(";", hex(textstart + pc), di)

    print("inst_" + str(pc) + ": ", end="")

    if iname == "addi":
        tgt = regmaps[params[0]]
        reg1 = regmaps[params[1]]
        imm = params[2]

        if imm == 0:
            if tgt != "dword 0":
                if isinstance(tgt, str):
                    if isinstance(reg1, str):
                        print("mov", tgt + ",", reg1)
                    else:
                        print("mov", tgt + ", [x" + str(reg1) + "]")
                else:
                    if isinstance(reg1, str):
                        print("mov [x" + str(tgt) + "],", reg1)
                    else:
                        print("mov ecx, [x" + str(reg1) + "]")
                        print("mov [x" + str(tgt) + "], ecx")
            else:
                print("nop")
        else:
            regimminst("add", tgt, reg1, imm)
    elif iname == "ecall":
        print("mov [safeplace1], eax")
        print("shl eax, 2")
        print("mov [safeplace], eax")
        print("mov eax, syscalls")
        print("add eax, [safeplace]")
        print("mov [safeplace], ebx")
        print("mov ebx, [eax]")
        print("mov eax, ebx")
        print("mov ebx, syscall_params")
        print("shl eax, 2")
        print("add ebx, eax")
        print("mov ebx, [ebx]")
        print("shr eax, 2")
        print("mov [sysret], dword inst_" + str(pc) + "_ret")
        print("jmp ebx")
        print("inst_" + str(pc) + "_ret:")
        print("mov ebx, eax") # On x86, eax is used for the return value, while on RISC-V a0 (mapped to ebx) is used for the return value
        print("mov eax, [safeplace1]")
    elif iname == "bne":
        branch_cond(regmaps[params[0]], regmaps[params[1]], params[2], "jne")
    elif iname == "beq":
        branch_cond(regmaps[params[0]], regmaps[params[1]], params[2], "je")
    elif iname == "bge":
        branch_cond(regmaps[params[0]], regmaps[params[1]], params[2], "jge")
    elif iname == "bgeu":
        branch_cond(regmaps[params[0]], regmaps[params[1]], params[2], "jae")
    elif iname == "blt":
        branch_cond(regmaps[params[0]], regmaps[params[1]], params[2], "jl")
    elif iname == "bltu":
        branch_cond(regmaps[params[0]], regmaps[params[1]], params[2], "jb")
    elif iname == "lui":
        tgt = regmaps[params[0]]
        val = params[1]
        if tgt != "dword 0":
            if isinstance(tgt, str):
                print("mov", tgt + ",", val << 12)
            else:
                print("mov dword [x" + str(tgt) + "],", val << 12)
        else:
            print("nop")
    elif iname == "auipc":
        tgt = regmaps[params[0]]
        val = params[1] << 12

        if tgt != "dword 0":
            if isinstance(tgt, str):
                #print("mov", tgt + ", rawcode +", pc)
                print("mov", tgt + ", " + str(textstart + pc))
                print("add", tgt + ",", val)
            else:
                #print("mov dword [x" + str(tgt) + "], rawcode +", pc)
                print("mov dword [x" + str(tgt) + "], " + str(textstart + pc))
                print("add dword [x" + str(tgt) + "],", val)
        else:
            print("nop")
    elif iname == "andi":
        if params[2] == 0:
            regimminst("mov", regmaps[params[0]], "dword 0", 0)
        else:
            regimminst("and", regmaps[params[0]], regmaps[params[1]], params[2])
    elif iname == "ori":
        regimminst("or", regmaps[params[0]], regmaps[params[1]], params[2])
    elif iname == "xori":
        regimminst("xor", regmaps[params[0]], regmaps[params[1]], params[2])
    elif iname == "add":
        regreginst("add", regmaps[params[0]], regmaps[params[1]], regmaps[params[2]])
    elif iname == "or":
        regreginst("or", regmaps[params[0]], regmaps[params[1]], regmaps[params[2]])
    elif iname == "xor":
        regreginst("xor", regmaps[params[0]], regmaps[params[1]], regmaps[params[2]])
    elif iname == "sub":
        regreginst("sub", regmaps[params[0]], regmaps[params[1]], regmaps[params[2]])
    elif iname == "and":
        regreginst("and", regmaps[params[0]], regmaps[params[1]], regmaps[params[2]])
    elif iname == "sll":
        shift_regreg(regmaps[params[0]], regmaps[params[1]], regmaps[params[2]], "shl")
    elif iname == "sra":
        shift_regreg(regmaps[params[0]], regmaps[params[1]], regmaps[params[2]], "sar")
    elif iname == "srl":
        shift_regreg(regmaps[params[0]], regmaps[params[1]], regmaps[params[2]], "shr")
    elif iname == "sltu":
        slt_regreg(regmaps[params[0]], regmaps[params[1]], regmaps[params[2]], "cmovb")
    elif iname == "slt":
        slt_regreg(regmaps[params[0]], regmaps[params[1]], regmaps[params[2]], "cmovl")
    elif iname == "jalr":
        tgt = regmaps[params[0]]
        reg1 = regmaps[params[1]]
        imm = params[2]
        safereg = regs(tgt, reg1)
        safereg1 = regs(tgt, reg1, safereg)

        print("mov [safeplace], " + safereg)

        if isinstance(reg1, str):
            print("mov " + safereg + ",", reg1)
        else:
            print("mov " + safereg + ", [x" + str(reg1) + "]")

        print("add " + safereg + ",", imm, "-", str(textstart), "+ jumptable")
        print("mov [safeplace1], " + safereg1)
        print("mov " + safereg1 + ", [" + safereg + "]")
        print("mov " + safereg + ", [safeplace]")
        print("mov [safeplace], " + safereg1)
        print("mov " + safereg1 + ", [safeplace1]")

        if tgt != "dword 0":
            if isinstance(tgt, str):
                #print("mov", tgt + ", inst_" + str(pc + 4))
                print("mov", tgt + ",", pc + 4 + textstart)
            else:
                #print("mov dword [x" + str(tgt) + "], inst_" + str(pc + 4))
                print("mov dword [x" + str(tgt) + "],", pc + 4 + textstart)

        print("jmp dword [safeplace]")
    elif iname == "lb":
        load_inst(regmaps[params[0]], regmaps[params[1]], params[2], "lb")
    elif iname == "lbu":
        load_inst(regmaps[params[0]], regmaps[params[1]], params[2], "lbu")
    elif iname == "lh":
        load_inst(regmaps[params[0]], regmaps[params[1]], params[2], "lh")
    elif iname == "lhu":
        load_inst(regmaps[params[0]], regmaps[params[1]], params[2], "lhu")
    elif iname == "lw":
        load_inst(regmaps[params[0]], regmaps[params[1]], params[2], "lw")
    elif iname == "slli":
        regimminst("shl", regmaps[params[0]], regmaps[params[1]], params[2])
    elif iname == "srai":
        regimminst("sar", regmaps[params[0]], regmaps[params[1]], params[2])
    elif iname == "srli":
        regimminst("shr", regmaps[params[0]], regmaps[params[1]], params[2])
    elif iname == "slti":
        slt_regimm(regmaps[params[0]], regmaps[params[1]], params[2], "cmovl")
    elif iname == "sltiu":
        slt_regimm(regmaps[params[0]], regmaps[params[1]], params[2], "cmovb")
    elif iname == "jal":

        tgt = regmaps[params[0]]
        imm = params[1]

        if tgt != "dword 0":
            if isinstance(tgt, str):
                #print("mov", tgt + ", inst_" + str(pc + 4))
                print("mov", tgt + ",", pc + 4 + textstart)
            else:
                #print("mov dword [x" + str(tgt) + "], inst_" + str(pc + 4))
                print("mov dword [x" + str(tgt) + "],", pc + 4 + textstart)

        print("jmp inst_" + str(pc + imm))
    elif iname == "ret":
        safereg = "eax"
        safereg1 = "ebx"

        print("mov [safeplace], " + safereg)
        print("mov " + safereg + ", [x1]")
        print("add " + safereg + ", jumptable -", str(textstart))
        print("mov [safeplace1], " + safereg1)
        print("mov " + safereg1 + ", [" + safereg + "]")
        print("mov " + safereg + ", [safeplace]")
        print("mov [safeplace], " + safereg1)
        print("mov " + safereg1 + ", [safeplace1]")
        print("jmp dword [safeplace]")
    elif iname == "sb":
        src = regmaps[params[0]]
        reg1 = regmaps[params[1]]
        imm = params[2]
        safereg = regs(src, reg1)
        safereg1 = regs(src, reg1, safereg)
        safereg2 = regs(src, reg1, safereg, safereg1)

        print("mov [safeplace],", safereg)
        print("mov [safeplace1],", safereg1)
        if isinstance(src, str):
            if isinstance(reg1, str):
                print("mov " + safereg1 + ",", src)
                print("and " + safereg1 + ", 0xff")
                print("add " + reg1 + ",", imm, "+ rawcode -", textstart)
                print("mov " + safereg + ", [" + reg1 + "]")
                print("and " + safereg + ", 0xffffff00")
                print("or " + safereg + ", " + safereg1)
                print("mov [" + reg1 + "], " + safereg)
                print("sub " + reg1 + ",", imm, "+ rawcode -", textstart)
            else:
                print("mov [safeplace2],", safereg2)
                print("mov " + safereg1 + ",", src)
                print("and " + safereg1 + ", 0xff")
                print("mov " + safereg2 + ", [x" + str(reg1) + "]")
                print("add " + safereg2 + ",", imm, "+ rawcode -", textstart)
                print("mov " + safereg + ", [" + safereg2 + "]")
                print("and " + safereg + ", 0xffffff00")
                print("or " + safereg + ", " + safereg1)
                print("mov [" + safereg2 + "], " + safereg)
                print("mov", safereg2 + ", [safeplace2]")
        else:
            if isinstance(reg1, str):
                print("mov " + safereg1 + ", [x" + str(src) + "]")
                print("and " + safereg1 + ", 0xff")
                print("add " + reg1 + ",", imm, "+ rawcode -", textstart)
                print("mov " + safereg + ", [" + reg1 + "]")
                print("and " + safereg + ", 0xffffff00")
                print("or " + safereg + ", " + safereg1)
                print("mov [" + reg1 + "], " + safereg)
                print("sub " + reg1 + ",", imm, "+ rawcode -", textstart)
            else:
                print("mov [safeplace2],", safereg2)
                print("mov " + safereg1 + ", [x" + str(src) + "]")
                print("and " + safereg1 + ", 0xff")
                print("mov " + safereg2 + ", [x" + str(reg1) + "]")
                print("add " + safereg2 + ",", imm, "+ rawcode -", textstart)
                print("mov " + safereg + ", [" + safereg2 + "]")
                print("and " + safereg + ", 0xffffff00")
                print("or " + safereg + ", " + safereg1)
                print("mov [" + safereg2 + "], " + safereg)
                print("mov", safereg2 + ", [safeplace2]")
        print("mov", safereg + ", [safeplace]")
        print("mov", safereg1 + ", [safeplace1]")
    elif iname == "sh":
        src = regmaps[params[0]]
        reg1 = regmaps[params[1]]
        imm = params[2]
        safereg = regs(src, reg1)
        safereg1 = regs(src, reg1, safereg)
        safereg2 = regs(src, reg1, safereg, safereg1)

        print("mov [safeplace],", safereg)
        print("mov [safeplace1],", safereg1)
        if isinstance(src, str):
            if isinstance(reg1, str):
                print("mov " + safereg1 + ",", src)
                print("and " + safereg1 + ", 0xffff")
                print("add " + reg1 + ",", imm, "+ rawcode -", textstart)
                print("mov " + safereg + ", [" + reg1 + "]")
                print("and " + safereg + ", 0xffff0000")
                print("or " + safereg + ", " + safereg1)
                print("mov [" + reg1 + "], " + safereg)
                print("sub " + reg1 + ",", imm, "+ rawcode -", textstart)
            else:
                print("mov [safeplace2],", safereg2)
                print("mov " + safereg1 + ",", src)
                print("and " + safereg1 + ", 0xffff")
                print("mov " + safereg2 + ", [x" + str(reg1) + "]")
                print("add " + safereg2 + ",", imm, "+ rawcode -", textstart)
                print("mov " + safereg + ", [" + safereg2 + "]")
                print("and " + safereg + ", 0xffff0000")
                print("or " + safereg + ", " + safereg1)
                print("mov [" + safereg2 + "], " + safereg)
                print("mov", safereg2 + ", [safeplace2]")
        else:
            if isinstance(reg1, str):
                print("mov " + safereg1 + ", [x" + str(src) + "]")
                print("and " + safereg1 + ", 0xffff")
                print("add " + reg1 + ",", imm, "+ rawcode -", textstart)
                print("mov " + safereg + ", [" + reg1 + "]")
                print("and " + safereg + ", 0xffff0000")
                print("or " + safereg + ", " + safereg1)
                print("mov [" + reg1 + "], " + safereg)
                print("sub " + reg1 + ",", imm, "+ rawcode -", textstart)
            else:
                print("mov [safeplace2],", safereg2)
                print("mov " + safereg1 + ", [x" + str(src) + "]")
                print("and " + safereg1 + ", 0xffff")
                print("mov " + safereg2 + ", [x" + str(reg1) + "]")
                print("add " + safereg2 + ",", imm, "+ rawcode -", textstart)
                print("mov " + safereg + ", [" + safereg2 + "]")
                print("and " + safereg + ", 0xffff0000")
                print("or " + safereg + ", " + safereg1)
                print("mov [" + safereg2 + "], " + safereg)
                print("mov", safereg2 + ", [safeplace2]")
        print("mov", safereg + ", [safeplace]")
        print("mov", safereg1 + ", [safeplace1]")
    elif iname == "sw":
        src = regmaps[params[0]]
        reg1 = regmaps[params[1]]
        imm = params[2]
        safereg = regs(src, reg1)
        safereg1 = regs(src, reg1, safereg)

        if isinstance(src, str):
            if isinstance(reg1, str):
                print("mov ecx,", reg1)
                print("add ecx,", imm, "+ rawcode -", textstart)
                print("mov [ecx], " + src)
            else:
                print("mov [safeplace],", safereg)
                print("mov " + safereg + ", [x" + str(reg1) + "]")
                print("add " + safereg + ",", imm, "+ rawcode -", textstart)
                print("mov [" + safereg + "], " + src)
                print("mov " + safereg + ", [safeplace]")
        else:
            if isinstance(reg1, str):
                print("mov ecx, [x" + str(src) + "]")
                print("add " + reg1 + ",", imm, "+ rawcode -", textstart)
                print("mov [" + reg1 + "], ecx")
                print("sub " + reg1 + ",", imm, "+ rawcode -", textstart)
            else:
                print("mov [safeplace1],", safereg1)
                print("mov ecx, [x" + str(src) + "]")
                print("mov " + safereg1 + ", [x" + str(reg1) + "]")
                print("add " + safereg1 + ",", imm, "+ rawcode -", textstart)
                print("mov [" + safereg1 + "], ecx")
                print("mov " + safereg1 + ", [safeplace1]")
    elif iname == "nop":
        print("nop")
    else:
        print("nop")
        print("Unhandled instruction:", di, file=sys.stderr)

    pc += 4
