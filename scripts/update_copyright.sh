#!/bin/bash
#
# Update Copyright from Sierra Telecom to iMatrix Systems, Inc.
# Date: 2026-01-01
#

# Find all files with "Sierra Telecom" excluding archive directories
FILES=$(grep -rl "Sierra Telecom" iMatrix Fleet-Connect-1 2>/dev/null | grep -v "/archive/")

COUNT=0
for FILE in $FILES; do
    if [ -f "$FILE" ]; then
        # Perform all replacements
        sed -i \
            -e 's/Copyright 20[0-9][0-9], Sierra Telecom\. All Rights Reserved\./Copyright 2026, iMatrix Systems, Inc. All Rights Reserved./g' \
            -e 's/Copyright 20[0-9][0-9], Sierra Telecom, Inc\./Copyright 2026, iMatrix Systems, Inc./g' \
            -e 's/Copyright 20[0-9][0-9], Sierra Telecom, Inc\. or a subsidiary of/Copyright 2026, iMatrix Systems, Inc./g' \
            -e 's/Sierra Telecom ("Sierra")/iMatrix Systems ("iMatrix")/g' \
            -e 's/owned by Sierra Telecom/owned by iMatrix Systems/g' \
            -e 's/Sierra reserves/iMatrix reserves/g' \
            -e 's/Sierra does not assume/iMatrix does not assume/g' \
            -e 's/Sierra does not authorize/iMatrix does not authorize/g' \
            -e 's/Sierra product/iMatrix product/g' \
            -e "s/Sierra's product/iMatrix's product/g" \
            -e 's/indemnify Sierra/indemnify iMatrix/g' \
            "$FILE"
        ((COUNT++))
        echo "Updated: $FILE"
    fi
done

echo ""
echo "====================================="
echo "Updated $COUNT files"
echo "====================================="
