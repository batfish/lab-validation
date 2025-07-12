#!/bin/bash
set -euo pipefail

#c1
file1=virginia_main.tf
file2=demo/c1_fix_virginia_sg.tf
if test -f "$file1"; then
    mv "$file1" demo/
else
    echo "$file1 does not exist"
fi

#c2
file1=c1_fix_virginia_sg.tf
file2=demo/c2_fix_virginia_nacl.tf
if test -f "$file2"; then
    mv "$file2" .
else
    echo "$file2 does not exist"
fi

#c3
file1=demo/c3_add_file_server.tf
if test -f "$file1"; then
    mv "$file1" .
else
    echo "$file1 does not exist"
fi

#c4
file1=demo/c4_fix_file_server_connectivity.tf
if test -f "$file1"; then
    mv "$file1" .
else
    echo "$file1 does not exist"
fi
