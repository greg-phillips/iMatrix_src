#!/bin/bash
FILES=$(grep -rl "indemnity Sierra" iMatrix Fleet-Connect-1 2>/dev/null | grep -v "/archive/")
for FILE in $FILES; do
    sed -i 's/indemnity Sierra/indemnify iMatrix/g' "$FILE"
    echo "Fixed: $FILE"
done
echo "Done"
