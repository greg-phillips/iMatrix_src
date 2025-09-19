#!/bin/bash
#
# Basic PCAN TRC Logging Examples
# These examples demonstrate common usage patterns for the PCAN TRC Logger
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGGER="${SCRIPT_DIR}/../pcan_trc_logger.py"

echo "============================================"
echo "PCAN TRC Logger - Basic Usage Examples"
echo "============================================"
echo ""

# Example 1: Simple logging at 500 kbit/s
echo "Example 1: Basic logging at 500 kbit/s"
echo "Command: $LOGGER --bitrate 500000"
echo "Press Ctrl+C to stop..."
echo ""
# $LOGGER --bitrate 500000

# Example 2: Log for 30 seconds
echo "Example 2: Time-limited logging (30 seconds)"
echo "Command: $LOGGER --bitrate 500000 --duration 30"
echo ""
# $LOGGER --bitrate 500000 --duration 30

# Example 3: Log to specific file
echo "Example 3: Log to specific file"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="can_log_${TIMESTAMP}.trc"
echo "Command: $LOGGER --bitrate 500000 --outfile $OUTPUT_FILE --duration 10"
echo ""
# $LOGGER --bitrate 500000 --outfile "$OUTPUT_FILE" --duration 10

# Example 4: Different bitrates
echo "Example 4: Common bitrate examples"
echo ""
echo "  125 kbit/s (Low speed CAN):"
echo "  $LOGGER --bitrate 125000"
echo ""
echo "  250 kbit/s (Medium speed CAN):"
echo "  $LOGGER --bitrate 250000"
echo ""
echo "  500 kbit/s (High speed CAN - most common):"
echo "  $LOGGER --bitrate 500000"
echo ""
echo "  1 Mbit/s (Maximum CAN speed):"
echo "  $LOGGER --bitrate 1000000"
echo ""

# Example 5: Different channels
echo "Example 5: Using different PCAN channels"
echo ""
echo "  USB Channel 1 (default):"
echo "  $LOGGER --bitrate 500000 --channel PCAN_USBBUS1"
echo ""
echo "  USB Channel 2:"
echo "  $LOGGER --bitrate 500000 --channel PCAN_USBBUS2"
echo ""
echo "  PCI Channel 1:"
echo "  $LOGGER --bitrate 500000 --channel PCAN_PCIBUS1"
echo ""

# Example 6: Verbose output for debugging
echo "Example 6: Verbose output modes"
echo ""
echo "  INFO level (basic information):"
echo "  $LOGGER --bitrate 500000 -v --duration 5"
echo ""
echo "  DEBUG level (detailed debugging):"
echo "  $LOGGER --bitrate 500000 -vv --duration 5"
echo ""

# Example 7: Log including transmitted messages
echo "Example 7: Log own transmitted messages"
echo "Command: $LOGGER --bitrate 500000 --receive-own --duration 10"
echo ""
# $LOGGER --bitrate 500000 --receive-own --duration 10

echo "============================================"
echo "To run any example, uncomment the command line"
echo "or copy and run it directly."
echo "============================================"