#!/bin/bash
#
# Fix remaining Sierra Telecom references
#

FILES=$(grep -rl "Sierra Telecom" iMatrix Fleet-Connect-1 2>/dev/null | grep -v "/archive/")

for FILE in $FILES; do
    if [ -f "$FILE" ]; then
        sed -i \
            -e 's/Copyright {{YEAR}}, Sierra Telecom\./Copyright 2026, iMatrix Systems, Inc./g' \
            -e 's/Copyright 20[0-9][0-9], Sierra Telecom inc\./Copyright 2026, iMatrix Systems, Inc./g' \
            -e 's/Copyright 20[0-9][0-9], Sierra Telecom Inc\./Copyright 2026, iMatrix Systems, Inc./g' \
            -e 's/Sierra Telecom/iMatrix Systems/g' \
            "$FILE"
        echo "Fixed: $FILE"
    fi
done

echo "Done"
