#!/bin/sh
##############################################################################
# @file monitor_fc1.sh
# @brief Real-time monitoring of FC-1 process on target
# @author Claude Code
# @date 2025-12-22
##############################################################################

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/common_ssh.sh"

INTERVAL=2
CLEAR_SCREEN=true

# Parse arguments
while [ $# -gt 0 ]; do
    case "$1" in
        -i|--interval) INTERVAL="$2"; shift 2 ;;
        -n|--no-clear) CLEAR_SCREEN=false; shift ;;
        -h|--help)
            printf "Usage: %s [-i interval] [-n|--no-clear]\n" "$(basename "$0")"
            printf "  -i N   Update interval in seconds (default: 2)\n"
            printf "  -n     Don't clear screen between updates\n"
            exit 0
            ;;
        *) shift ;;
    esac
done

# Initialize SSH
TARGET=$(get_configured_target)
[ -z "$TARGET" ] && { echo "ERROR: No target configured"; exit 1; }
init_ssh "$TARGET"
test_ssh_connection || { echo "ERROR: Cannot connect"; exit 1; }

trap 'printf "\n[*] Stopped.\n"; exit 0' INT TERM

printf "[*] Monitoring %s (interval: %ds) - Ctrl+C to stop\n" "$TARGET" "$INTERVAL"
sleep 1

while true; do
    [ "$CLEAR_SCREEN" = true ] && printf '\033[2J\033[H'

    remote_cmd 'TERM=dumb
FC1_PID=$(ps aux | grep "/usr/qk/bin/FC-1" | grep -v grep | awk "{print \$1}" | head -1)
NOW=$(date "+%Y-%m-%d %H:%M:%S")

echo "================================================================"
echo "  FC-1 Monitor                              $NOW"
echo "================================================================"
echo ""

echo "-- SERVICE --"
if [ -n "$FC1_PID" ]; then
    echo "  Status:  RUNNING"
    echo "  PID:     $FC1_PID"
    SV=$(sv status FC-1 2>/dev/null || echo "n/a")
    echo "  runit:   $SV"
else
    echo "  Status:  NOT RUNNING"
fi
echo ""

if [ -n "$FC1_PID" ]; then
    echo "-- PROCESS --"
    if [ -f "/proc/$FC1_PID/status" ]; then
        RSS=$(grep VmRSS /proc/$FC1_PID/status | awk "{print \$2}")
        THR=$(grep Threads /proc/$FC1_PID/status | awk "{print \$2}")
        echo "  Memory:  $((RSS/1024)) MB (RSS)"
        echo "  Threads: $THR"
    fi
    FD=$(ls /proc/$FC1_PID/fd 2>/dev/null | wc -l)
    SOCK=$(ls -la /proc/$FC1_PID/fd 2>/dev/null | grep -c socket: || echo 0)
    echo "  FDs:     $FD (sockets: $SOCK)"
    echo ""
fi

echo "-- SYSTEM --"
MEM=$(free -m | grep Mem:)
USED=$(echo "$MEM" | awk "{print \$3}")
TOTAL=$(echo "$MEM" | awk "{print \$2}")
AVAIL=$(echo "$MEM" | awk "{print \$7}")
echo "  RAM:     $USED / $TOTAL MB ($AVAIL MB available)"
LOAD=$(cat /proc/loadavg | cut -d" " -f1-3)
echo "  Load:    $LOAD"
DISK=$(df -h /usr/qk 2>/dev/null | tail -1 | awk "{print \$3 \" used, \" \$4 \" free\"}")
echo "  Disk:    $DISK"
echo ""
echo "================================================================"
'
    sleep "$INTERVAL"
done
