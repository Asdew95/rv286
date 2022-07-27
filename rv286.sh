#!/bin/sh

ASM=$(mktemp)
OBJ=$(mktemp)

trap 'rm -f "$ASM" "$OBJ"' EXIT TERM INT

python rv286.py "$1" > "$ASM" && nasm -f elf32 "$ASM" -o "$OBJ" && ld -melf_i386 "$OBJ" -o "$2"
