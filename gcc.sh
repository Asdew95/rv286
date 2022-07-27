#!/bin/sh

riscv64-elf-gcc -march=rv32i -mabi=ilp32 "$1" -o "$2"
