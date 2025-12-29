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
FC1_DOWN_FILE="${FC1_SV_DIR}/down"

##
# @brief Check if the FC-1 service is enabled (no down file)
# @return 0 if enabled, 1 if disabled
##
is_enabled() {
    if [ -f "$FC1_DOWN_FILE" ]; then
        return 1  # Disabled (down file exists)
    else
        return 0  # Enabled (no down file)
    fi
}

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

    # Check if service is enabled (no down file)
    if is_enabled; then
        echo "[OK]  Auto-start: Enabled"
    else
        echo "[--]  Auto-start: Disabled (down file exists)"
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

##
# @brief Enable the FC-1 service for auto-start
# Removes the down file and starts the service
##
enable_service() {
    echo "Enabling FC-1 service..."

    # Remove down file if it exists
    if [ -f "$FC1_DOWN_FILE" ]; then
        rm -f "$FC1_DOWN_FILE"
        echo "Removed down file: $FC1_DOWN_FILE"
    else
        echo "Service already enabled (no down file)"
    fi

    # Start the service
    start_service
}

##
# @brief Disable the FC-1 service from auto-start
# Stops the service and creates a down file
# @param $1 Optional: -y to skip confirmation
##
disable_service() {
    SKIP_CONFIRM=""
    if [ "$1" = "-y" ]; then
        SKIP_CONFIRM="yes"
    fi

    echo "========================================"
    echo " WARNING: Disabling FC-1 Service"
    echo "========================================"
    echo ""
    echo "This will:"
    echo "  - Stop the currently running service"
    echo "  - Prevent FC-1 from auto-starting on reboot"
    echo ""
    echo "The run script will be preserved for re-enabling."
    echo ""

    if [ -z "$SKIP_CONFIRM" ]; then
        printf "Are you sure you want to disable FC-1? [y/N]: "
        read -r CONFIRM
        case "$CONFIRM" in
            [yY]|[yY][eE][sS])
                ;;
            *)
                echo "Cancelled."
                return 1
                ;;
        esac
    fi

    # Stop the service
    stop_service

    # Create down file to prevent auto-start
    touch "$FC1_DOWN_FILE"
    echo ""
    echo "Created down file: $FC1_DOWN_FILE"
    echo "FC-1 service disabled - will not auto-start on reboot."
    echo ""
    echo "To re-enable, run: $0 enable"
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
    echo "  enable      Enable FC-1 auto-start and start service"
    echo "  disable     Disable FC-1 auto-start (with confirmation)"
    echo "  disable -y  Disable without confirmation prompt"
    echo "  run [opts]  Run FC-1 in foreground (for testing)"
    echo "              Accepts FC-1 options: -S, -P, -I, -R, --help"
    echo "  log         Show recent log entries"
    echo "  create-run  Create the runsv run script"
    echo "  help        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 start           # Start service normally"
    echo "  $0 stop            # Stop service"
    echo "  $0 enable          # Enable auto-start and start"
    echo "  $0 disable         # Disable auto-start (prompts)"
    echo "  $0 disable -y      # Disable without prompt"
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
    enable)
        enable_service
        ;;
    disable)
        shift
        disable_service "$@"
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
        echo "Usage: $0 {start|stop|restart|status|enable|disable|run|log|help}"
        echo "Run '$0 help' for more information."
        exit 1
        ;;
esac

exit 0
