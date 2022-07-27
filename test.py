import os
import random
import subprocess
import sys
import tempfile
import time

QEMU="qemu-riscv32"

instructions = {"add": "R", "or": "R", "sll": "R", "slt": "R", "sltu": "R", "sra": "R", "srl": "R", "xor": "R", "sub": "R", "and": "R", "addi": "I", "andi": "I", "ori": "I", "slli": "IS", "slti": "I", "sltiu": "I", "srai": "IS", "xori": "I", "srli": "IS", "auipc": "U", "lui": "U", "beq": "B", "bge": "B", "bgeu": "B", "blt": "B", "bltu": "B", "bne": "B", "jal": "J", "lb": "L", "lbu": "L", "lh": "L", "lw": "L", "lhu": "L", "sb": "S", "sh": "S", "sw": "S", "jalr": "IJ"}

with open("testtemplate.s", "r") as f:
    template = f.read()

def save_inst(file, inst):
    file.write(template.replace("# [INSTRUCTION HERE]", inst).encode())
    file.close()

def assemble(genfile, rvfile, x86file):
    rvfile.close()
    x86file.close()

    if subprocess.run(["./as.sh", genfile.name, rvfile.name]).returncode != 0:
        return 1

    if subprocess.run(["./rv286.sh", rvfile.name, x86file.name]).returncode != 0:
        return 2

    return 0

def run_risc(file):
    return subprocess.run([QEMU, file.name], stdout=subprocess.PIPE).stdout

def run_x86(file):
    return subprocess.run([file.name], stdout=subprocess.PIPE).stdout

def random_reg():
    return "x" + str(random.randint(0, 30)) # Don't use x31 as it isn't checked

def random_inst():
    (inst, atype) = random.choice(list(instructions.items()))
    regs = [random_reg(), random_reg(), random_reg()]
    if atype == "R":
        return (inst + " " + regs[0] + ", " + regs[1] + ", " + regs[2], (regs[0], regs[1], regs[2]))
    elif atype == "I":
        return (inst + " " + regs[0] + ", " + regs[1] + ", " + str(random.randint(-2048, 2047))), (regs[0], regs[1])
    elif atype == "IS":
        return (inst + " " + regs[0] + ", " + regs[1] + ", " + str(random.randint(0, 31))), (regs[0], regs[1])
    elif atype == "U":
        return (inst + " " + regs[0] + ", " + str(random.randint(0, 1048575))), (regs[0], regs[1])
    elif atype == "B":
        return (inst + " " + regs[0] + ", " + regs[1] + ", branch2", (regs[0], regs[1]))
    elif atype == "J":
        return (inst + " " + regs[0] + ", branch2", (regs[0]))
    elif atype == "L":
        if regs[1] == "x0":
            regs[1] = "x1"
        imm = random.randint(-2047, 2047)
        return ("la " + regs[1] + ", branch1text\naddi " + regs[1] + ", " + regs[1] + ", " + str(-imm) + "\n" + inst + " " + regs[0] + ", " + str(imm) + "(" + regs[1] + ")", (regs[0], regs[1]))
    elif atype == "S":
        if regs[1] == "x0":
            regs[1] = "x1"
        imm = random.randint(-2047, 2047)
        return ("la " + regs[1] + ", teststore\naddi " + regs[1] + ", " + regs[1] + ", " + str(-imm) + "\n" + inst + " " + regs[0] + ", " + str(imm) + "(" + regs[1] + ")", (regs[0], regs[1]))
    elif atype == "IJ":
        if regs[1] == "x0":
            regs[1] = "x1"
        imm = random.randint(-2047, 2047)
        return ("la " + regs[1] + ", branch2\naddi " + regs[1] + ", " + regs[1] + ", " + str(-imm) + "\n" + inst + " " + regs[0] + ", " + str(imm) + "(" + regs[1] + ")", (regs[0], regs[1]))

def single_test():
    (inst, regs) = random_inst()

    while True:
        print("Checking instruction:", inst)

        try:
            genfile = tempfile.NamedTemporaryFile(delete=False)
            rvfile = tempfile.NamedTemporaryFile(delete=False)
            x86file = tempfile.NamedTemporaryFile(delete=False)
            save_inst(genfile, inst)
            as_success = assemble(genfile, rvfile, x86file)
            if as_success == 1:
                os.remove(genfile.name)
                os.remove(rvfile.name)
                os.remove(x86file.name)
                sys.exit(1)
            elif as_success == 2:
                os.remove(genfile.name)
                os.remove(rvfile.name)
                os.remove(x86file.name)
                print("Retest by pressing enter...")
                input()
                continue
            riscres = run_risc(rvfile).decode()
            x86res = run_x86(x86file).decode()

            if riscres != x86res:
                print("DISCREPANCY!")
                print("Instruction:", inst)
                print()

                try:
                    print("RISC-V")
                    print(riscres)
                    print("Registers:")
                    riscregs = [hex(0)] + riscres.split()
                    for reg in regs:
                        print(reg + ":", riscregs[int(reg.replace("x", ""))])
            
                    print()

                    print("x86")
                    print(x86res)
                    print("Registers:")
                    x86regs = [hex(0)] + x86res.split()
                    for reg in regs:
                        print(reg + ":", x86regs[int(reg.replace("x", ""))])

                    print()

                    print("Register differences:")
                    for i in range(1, 31):
                        if x86regs[i] != riscregs[i]:
                            print("x" + str(i) + ":")
                            print("  RISC-V:", riscregs[i])
                            print("  x86:   ", x86regs[i])

                    if x86regs[31] != riscregs[31]:
                        print("teststore:")
                        print("  RISC-V:", riscregs[31])
                        print("  x86:   ", x86regs[31])

                    os.remove(genfile.name)
                    os.remove(rvfile.name)
                    os.remove(x86file.name)
                    
                    print("Retest by pressing enter...")
                    input()
                except Exception as e:
                    os.remove(genfile.name)
                    os.remove(rvfile.name)
                    os.remove(x86file.name)
                    print("ERROR")
                    print()
                    print("RISC-V:")
                    print(riscres)
                    print()
                    print("x86:")
                    print(x86res)
                    print()
                    print("Retest by pressing enter...")
                    input()
            else:
                os.remove(genfile.name)
                os.remove(rvfile.name)
                os.remove(x86file.name)
                # Successful
                break
        except KeyboardInterrupt:
            print("SIGINT!")
            os.remove(genfile.name)
            os.remove(rvfile.name)
            os.remove(x86file.name)
            sys.exit(0)

while True:
    single_test()
