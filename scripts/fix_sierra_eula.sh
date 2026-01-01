#!/bin/bash
#
# Fix remaining Sierra references in EULA section
#

FILES=$(grep -rl "Sierra hereby grants\|connection with Sierra\|permission of Sierra\|subsidiaries (\"Sierra\")" iMatrix Fleet-Connect-1 2>/dev/null | grep -v "/archive/")

for FILE in $FILES; do
    if [ -f "$FILE" ]; then
        sed -i \
            -e 's/Sierra hereby grants/iMatrix hereby grants/g' \
            -e "s/connection with Sierra's/connection with iMatrix's/g" \
            -e 's/permission of Sierra/permission of iMatrix/g' \
            -e 's/subsidiaries ("Sierra")/subsidiaries ("iMatrix")/g' \
            -e 's/("Sierra")/("iMatrix")/g' \
            "$FILE"
        echo "Fixed: $FILE"
    fi
done

echo "Done"
