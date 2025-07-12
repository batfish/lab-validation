#!/bin/bash
set -euo pipefail

file1=c4_fix_file_server_connectivity.tf

if test -f "$file1"; then
    mv "$file1" demo/
else
    echo "$file1 does not exist"
fi
