#!/bin/bash
set -euo pipefail

file1=c3_add_file_server.tf

if test -f "$file1"; then
    mv "$file1" demo/
else
    echo "$file1 does not exist"
fi
