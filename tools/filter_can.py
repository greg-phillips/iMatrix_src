#!/usr/bin/env python3
"""
filter_can.py

Read a PCAN-View–style dump of OBD2 CAN traffic, print the header unchanged,
then print only those message lines whose CAN ID is above 0x700, excluding IDs 0x799 and 0x7C1.
"""

import argparse
import sys
import re


def is_record_line(line: str) -> bool:
    """
    Detect whether a line is a CAN message record.
    Records typically start with optional whitespace followed by digits and a ')' character.
    """
    return bool(re.match(r'^\s*\d+\)', line))


def parse_can_id(line: str) -> int:
    """
    Given a record line, extract the 4th whitespace-separated field (the ID in hex)
    and return its integer value.
    """
    fields = line.split()
    try:
        hex_str = fields[3]
        return int(hex_str, 16)
    except (IndexError, ValueError) as e:
        raise ValueError(f"Unable to parse CAN ID from line: {line!r}") from e


def main():
    parser = argparse.ArgumentParser(
        description="Filter OBD2 CAN records by ID > 0x700, excluding specific IDs, preserving header."
    )
    parser.add_argument(
        "infile",
        metavar="INFILE",
        help="Path to the PCAN-View–style dump file"
    )
    args = parser.parse_args()

    try:
        with open(args.infile, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        sys.exit(f"Error opening '{args.infile}': {e}")

    header_lines = []
    data_lines = []
    in_header = True

    for line in lines:
        if in_header and is_record_line(line):
            in_header = False

        if in_header:
            header_lines.append(line.rstrip("\n"))
        else:
            if is_record_line(line):
                data_lines.append(line.rstrip("\n"))

    # Print header
    for hl in header_lines:
        print(hl)

    # Filter parameters
    threshold = 0x700
    excluded_ids = {0x799, 0x7C1}

    # Print filtered records
    for dl in data_lines:
        try:
            can_id = parse_can_id(dl)
        except ValueError:
            continue
        if can_id > threshold and can_id not in excluded_ids:
            print(dl)


if __name__ == "__main__":
    main()
