#!/bin/sh

OBJ=$(mktemp)

trap 'rm -f "$OBJ"' EXIT TERM INT

riscv64-elf-as -march=rv32i "$1" -o "$OBJ" && riscv64-elf-ld -melf32lriscv "$OBJ" -o "$2"
