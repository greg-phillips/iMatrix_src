#!/bin/bash
#
# Fix remaining Sierra references in disclaimer (spans multiple lines)
#

# Simply replace all standalone "Sierra" with "iMatrix" in the copyright blocks
# Looking for patterns like ". Sierra" or "e Sierra" (after "the Sierra product")

FILES=$(grep -rl "PURPOSE\. Sierra\|notice\. Sierra\|the Software\. Sierra\|the Sierra product\|indemnify Sierra" iMatrix Fleet-Connect-1 2>/dev/null | grep -v "/archive/")

for FILE in $FILES; do
    if [ -f "$FILE" ]; then
        sed -i \
            -e 's/PURPOSE\. Sierra/PURPOSE. iMatrix/g' \
            -e 's/notice\. Sierra/notice. iMatrix/g' \
            -e 's/the Software\. Sierra/the Software. iMatrix/g' \
            -e 's/the Sierra product/the iMatrix product/g' \
            -e 's/indemnify Sierra/indemnify iMatrix/g' \
            "$FILE"
        echo "Fixed: $FILE"
    fi
done

echo "Done"
