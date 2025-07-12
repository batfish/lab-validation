#!/bin/bash
set -euo pipefail

file1=demo/virginia_main.tf
file2=c1_fix_virginia_sg.tf

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
