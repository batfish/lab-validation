#!/bin/bash
set -euo pipefail

file1=demo/c1_fix_virginia_sg.tf
file2=c2_fix_virginia_nacl.tf

if test -f "$file1"; then
    mv "$file1" .
else
    echo "$file1 does not exist"
fi

if test -f "$file2"; then
    mv "$file2" demo/
else
    echo "$file2 does not exist"
fi
