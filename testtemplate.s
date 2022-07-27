.globl _start

# Parameters:
# - a0: pointer to null-terminated string
print:
    # Calculate length of string to a2
    li a2, 0
    .len_loop:
    lbu t1, 0(a0)
    beq t1, x0, .len_loop_end
    addi a0, a0, 1
    addi a2, a2, 1
    j .len_loop
    .len_loop_end:
    sub a0, a0, a2

    li a7, 64 # sys_write
    mv a1, a0
    li a0, 1 # stdout
    # a2 already has the length of the string
    ecall
    ret

# Parameters:
# - a0: integer to be printed
print_int:
    la a1, print_int_secret + 9 # Load end of print_int_secret hex to a1
    la a5, hex
    li a2, 8
    .int_loop:
    andi a3, a0, 0xf
    add a4, a5, a3
    lb a6, 0(a4)
    sb a6, 0(a1)
    addi a1, a1, -1
    addi a2, a2, -1
    sra a0, a0, 4
    bne a2, x0, .int_loop
    
    la a0, print_int_secret
    mv s0, ra
    call print
    mv ra, s0
    ret

save_regs:
    la x31, regs # x31 is discarded so it isn't saved, sadly
    sw x1, 0(x31)
    sw x2, 4(x31)
    sw x3, 8(x31)
    sw x4, 12(x31)
    sw x5, 16(x31)
    sw x6, 20(x31)
    sw x7, 24(x31)
    sw x8, 28(x31)
    sw x9, 32(x31)
    sw x10, 36(x31)
    sw x11, 40(x31)
    sw x12, 44(x31)
    sw x13, 48(x31)
    sw x14, 52(x31)
    sw x15, 56(x31)
    sw x16, 60(x31)
    sw x17, 64(x31)
    sw x18, 68(x31)
    sw x19, 72(x31)
    sw x20, 76(x31)
    sw x21, 80(x31)
    sw x22, 84(x31)
    sw x23, 88(x31)
    sw x24, 92(x31)
    sw x25, 96(x31)
    sw x26, 100(x31)
    sw x27, 104(x31)
    sw x28, 108(x31)
    sw x29, 112(x31)
    sw x30, 116(x31)
    ret

print_regs:
    addi sp, sp, -12
    sw ra, 4(sp)

    li t0, 30
    la t1, regs
    .regs_loop:
    lw a0, 0(t1)
    sw t0, 8(sp)
    sw t1, 12(sp)
    call print_int
    la a0, space
    call print
    lw t0, 8(sp)
    lw t1, 12(sp)
    addi t1, t1, 4
    addi t0, t0, -1
    bne t0, x0, .regs_loop
    
    la a0, teststore
    lw a0, 0(a0)
    call print_int

    la a0, newline
    call print

    lw ra, 4(sp)
    addi sp, sp, 12
    ret

branch2:
    la gp, __global_pointer$
    la sp, regs + 4094
    call save_regs
    call print_regs

    la a0, branch2text
    call print

    li a7, 93 # sys_exit
    li a0, 0
    ecall

_start:
.option norelax
    # Initialize registers
    li x1, 0x1
    li x2, 0x2
    li x3, 0x3
    li x4, 0x4
    li x5, 0x5
    li x6, 0x6
    li x7, 0x7
    li x8, 0x8
    li x9, 0x9
    li x10, 0x10
    li x11, 0x11
    li x12, 0x12
    li x13, 0x13
    li x14, 0x14
    li x15, 0x15
    li x16, 0x16
    li x17, 0x17
    li x18, 0x18
    li x19, 0x19
    li x20, 0x20
    li x21, 0x21
    li x22, 0x22
    li x23, 0x23
    li x24, 0x24
    li x25, 0x25
    li x26, 0x26
    li x27, 0x27
    li x28, 0x28
    li x29, 0x29
    li x30, 0x30

    # [INSTRUCTION HERE]

    la gp, __global_pointer$
    la sp, regs + 4094
    call save_regs
    call print_regs

    la a0, branch1text
    call print

    li a7, 93 # sys_exit
    li a0, 0
    ecall

.data
hello_world: .ascii "Hello, world!\n\0"
hex: .ascii "0123456789abcdef"
print_int_secret: .ascii "0xdeadbeef\0"
space: .ascii " \0"
newline: .ascii "\n\0"
branch1text: .ascii "BRANCH 1\n\0"
branch2text: .ascii "BRANCH 2\n\0"
teststore: .byte 0x12, 0x34, 0x56, 0x78

# Registers
.lcomm regs, 4 * 30 # Only 30 because x31 and x0 aren't saved
.lcomm stack, 4096
