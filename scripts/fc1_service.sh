#!/bin/sh
#
# FC-1 Service Control Script
# For manual start/stop during testing
#
# Usage: ./fc1_service.sh [start|stop|restart|status|run|log]
#

FC1_BIN="/home/FC-1"
FC1_SV_DIR="/usr/qk/etc/sv/FC-1"
FC1_RUN_SCRIPT="${FC1_SV_DIR}/run"

print_status() {
    echo "========================================"
    echo " FC-1 Service Status"
    echo "========================================"

    # Check if binary exists
    if [ -f "$FC1_BIN" ]; then
        echo "[OK]  Binary: $FC1_BIN"
    else
        echo "[ERR] Binary: $FC1_BIN (MISSING)"
    fi

    # Check if run script exists
    if [ -f "$FC1_RUN_SCRIPT" ]; then
        echo "[OK]  Run script: $FC1_RUN_SCRIPT"
    else
        echo "[ERR] Run script: $FC1_RUN_SCRIPT (MISSING)"
    fi

    # Check service status
    echo ""
    echo "Service status:"
    sv status FC-1 2>/dev/null || echo "  Service not configured"

    # Check if process is running
    echo ""
    PID=$(pidof FC-1 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "[OK]  Process: Running (PID: $PID)"
    else
        echo "[--]  Process: Not running"
    fi
    echo "========================================"
}

create_run_script() {
    echo "Creating run script at $FC1_RUN_SCRIPT..."
    cat > "$FC1_RUN_SCRIPT" << 'RUNEOF'
#!/bin/sh
exec 2>&1

export PATH=/usr/qk/bin:/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin:/usr/local/sbin:/opt:/opt/bin

printf "Start FC-1 Gateway Service...\n"

cd /usr/qk/etc/sv/FC-1

exec /home/FC-1
RUNEOF
    chmod +x "$FC1_RUN_SCRIPT"
    echo "Run script created."
}

start_service() {
    echo "Starting FC-1 service..."

    # Check if run script exists, create if missing
    if [ ! -f "$FC1_RUN_SCRIPT" ]; then
        echo "Run script missing, creating..."
        create_run_script
    fi

    sv start FC-1
    sleep 2
    sv status FC-1
}

stop_service() {
    echo "Stopping FC-1 service..."
    sv stop FC-1
    sleep 1

    # Double-check process is stopped
    PID=$(pidof FC-1 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "Process still running (PID: $PID), sending SIGTERM..."
        kill "$PID" 2>/dev/null
        sleep 1
    fi

    PID=$(pidof FC-1 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "Process still running, sending SIGKILL..."
        kill -9 "$PID" 2>/dev/null
    fi

    sv status FC-1
}

restart_service() {
    echo "Restarting FC-1 service..."
    stop_service
    sleep 1
    start_service
}

run_foreground() {
    echo "Running FC-1 in foreground (Ctrl+C to stop)..."
    echo "========================================"

    # Stop service first if running
    sv stop FC-1 2>/dev/null

    # Kill any existing process
    PID=$(pidof FC-1 2>/dev/null)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null
        sleep 1
    fi

    cd "$FC1_SV_DIR"
    exec "$FC1_BIN" "$@"
}

show_log() {
    echo "FC-1 Logs (last 50 lines):"
    echo "========================================"
    if [ -f /var/log/FC-1/current ]; then
        tail -50 /var/log/FC-1/current
    else
        echo "No log file found at /var/log/FC-1/current"
        echo ""
        echo "Checking dmesg for FC-1 related messages..."
        dmesg | grep -i fc-1 | tail -20
    fi
}

show_help() {
    echo "FC-1 Service Control Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start       Start FC-1 via runsv service"
    echo "  stop        Stop FC-1 service"
    echo "  restart     Restart FC-1 service"
    echo "  status      Show service and process status"
    echo "  run [opts]  Run FC-1 in foreground (for testing)"
    echo "              Accepts FC-1 options: -S, -P, -I, -R, --help"
    echo "  log         Show recent log entries"
    echo "  create-run  Create the runsv run script"
    echo "  help        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 start           # Start service normally"
    echo "  $0 stop            # Stop service"
    echo "  $0 run             # Run in foreground"
    echo "  $0 run -S          # Run with config summary"
    echo "  $0 status          # Check status"
    echo ""
}

# Main
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        print_status
        ;;
    run)
        shift
        run_foreground "$@"
        ;;
    log)
        show_log
        ;;
    create-run)
        create_run_script
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|run|log|help}"
        echo "Run '$0 help' for more information."
        exit 1
        ;;
esac

exit 0
