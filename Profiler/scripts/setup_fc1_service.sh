#!/bin/sh
##############################################################################
# @file setup_fc1_service.sh
# @brief Setup FC-1 as a managed service on target
# @author Claude Code
# @date 2025-12-21
#
# @description
#   Configure FC-1 (/home/FC-1) to run as a service on the target system.
#   Supports runit, sysvinit, systemd, or userland wrappers.
#   The FC-1 binary MUST remain at /home/FC-1 (not moved).
#
# @usage
#   ./scripts/setup_fc1_service.sh user@target
#
# @output
#   Service files installed on target
#   artifacts/logs/setup_service_<host>_<timestamp>.txt
#
##############################################################################

set -eu

##############################################################################
# Configuration
##############################################################################

# Script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROFILER_DIR/artifacts/logs"

# Source common SSH functions (supports sshpass for password auth)
. "$SCRIPT_DIR/common_ssh.sh"

# FC-1 binary path (MUST NOT be changed)
FC1_PATH="/home/FC-1"

##############################################################################
# Functions
##############################################################################

usage() {
    printf "Usage: %s [user@target]\n" "$(basename "$0")"
    printf "\n"
    printf "Setup FC-1 as a managed service on target.\n"
    printf "\n"
    printf "Arguments:\n"
    printf "  user@target    SSH target (optional, uses config if not specified)\n"
    printf "\n"
    printf "Configuration:\n"
    printf "  Connection settings loaded from config/target_connection.conf\n"
    printf "\n"
    printf "The script will detect the init system and create appropriate service files.\n"
    printf "FC-1 will always be run from: %s\n" "$FC1_PATH"
    exit 1
}

status() {
    printf "[*] %s\n" "$1"
}

error() {
    printf "[!] ERROR: %s\n" "$1" >&2
}

success() {
    printf "[+] %s\n" "$1"
}

warning() {
    printf "[~] WARNING: %s\n" "$1"
}

# Note: remote_cmd, remote_cmd_status, remote_has_cmd provided by common_ssh.sh

# Check if target path is writable
remote_writable() {
    path="$1"
    remote_cmd_status "test -w $path || (mkdir -p $path 2>/dev/null && test -w $path)"
}

# Detect init system
detect_init_system() {
    # Check for runit
    if remote_cmd "test -d /etc/sv"; then
        printf "runit"
        return
    fi

    # Check for systemd
    if remote_has_cmd systemctl; then
        printf "systemd"
        return
    fi

    # Check for OpenRC
    if remote_has_cmd rc-service; then
        printf "openrc"
        return
    fi

    # Check for sysvinit
    if remote_cmd "test -d /etc/init.d"; then
        printf "sysvinit"
        return
    fi

    printf "none"
}

# Setup runtime directories
setup_dirs() {
    status "Setting up runtime directories..."

    # Try system paths first
    if remote_writable "/var/log"; then
        LOG_PATH="/var/log/fc-1"
        PROFILE_PATH="/var/log/fc-1/profiles"
        RUN_PATH="/var/run/fc-1"
        remote_cmd "mkdir -p $LOG_PATH $PROFILE_PATH"
        remote_cmd "mkdir -p $RUN_PATH 2>/dev/null || true"
        success "Using system paths: $LOG_PATH"
    else
        # Fall back to home directory
        REMOTE_HOME=$(remote_cmd "echo \$HOME")
        if [ -z "$REMOTE_HOME" ]; then
            REMOTE_HOME="/home/$TARGET_USER"
        fi
        LOG_PATH="$REMOTE_HOME/fc-1-logs"
        PROFILE_PATH="$REMOTE_HOME/fc-1-profiles"
        RUN_PATH="$REMOTE_HOME/fc-1-run"
        remote_cmd "mkdir -p $LOG_PATH $PROFILE_PATH $RUN_PATH"
        status "Using home paths: $LOG_PATH"
    fi
}

# Setup runit service
setup_runit() {
    status "Setting up runit service..."

    SERVICE_DIR="/etc/sv/FC-1"

    # Create service directory
    if ! remote_writable "/etc/sv"; then
        warning "Cannot write to /etc/sv, using userland wrapper instead"
        setup_userland
        return 1
    fi

    remote_cmd "mkdir -p $SERVICE_DIR"

    # Create run script
    remote_cmd "cat > $SERVICE_DIR/run << 'RUNEOF'
#!/bin/sh
exec 2>&1
exec $FC1_PATH
RUNEOF"

    remote_cmd "chmod +x $SERVICE_DIR/run"

    # Create log directory if svlogd is available
    if remote_has_cmd svlogd; then
        remote_cmd "mkdir -p $SERVICE_DIR/log"
        remote_cmd "cat > $SERVICE_DIR/log/run << 'LOGEOF'
#!/bin/sh
exec svlogd -tt $LOG_PATH
LOGEOF"
        remote_cmd "chmod +x $SERVICE_DIR/log/run"
    else
        # Log to file directly
        remote_cmd "cat > $SERVICE_DIR/run << 'RUNEOF'
#!/bin/sh
exec $FC1_PATH >> $LOG_PATH/fc-1.log 2>&1
RUNEOF"
        remote_cmd "chmod +x $SERVICE_DIR/run"
    fi

    # Create finish script
    remote_cmd "cat > $SERVICE_DIR/finish << 'FINEOF'
#!/bin/sh
echo \"FC-1 exited with status \$1\" >> $LOG_PATH/fc-1.log
sleep 1
FINEOF"
    remote_cmd "chmod +x $SERVICE_DIR/finish"

    # Enable service (link to /etc/service or /var/service)
    if remote_cmd "test -d /etc/service"; then
        remote_cmd "ln -sf $SERVICE_DIR /etc/service/FC-1 2>/dev/null || true"
    elif remote_cmd "test -d /var/service"; then
        remote_cmd "ln -sf $SERVICE_DIR /var/service/FC-1 2>/dev/null || true"
    fi

    success "runit service created"

    # Print commands
    printf "\n"
    printf "Service commands:\n"
    printf "  Start:   sv start FC-1\n"
    printf "  Stop:    sv stop FC-1\n"
    printf "  Status:  sv status FC-1\n"
    printf "  Restart: sv restart FC-1\n"
    printf "  Logs:    tail -f %s/fc-1.log\n" "$LOG_PATH"

    return 0
}

# Setup sysvinit service
setup_sysvinit() {
    status "Setting up sysvinit service..."

    INIT_SCRIPT="/etc/init.d/fc-1"

    if ! remote_writable "/etc/init.d"; then
        warning "Cannot write to /etc/init.d, using userland wrapper instead"
        setup_userland
        return 1
    fi

    # Create init script
    remote_cmd "cat > $INIT_SCRIPT << 'INITEOF'
#!/bin/sh
### BEGIN INIT INFO
# Provides:          fc-1
# Required-Start:    \$local_fs \$network
# Required-Stop:     \$local_fs \$network
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: FC-1 Gateway Application
# Description:       Fleet Connect 1 gateway application
### END INIT INFO

DAEMON=$FC1_PATH
NAME=FC-1
PIDFILE=$RUN_PATH/fc-1.pid
LOGFILE=$LOG_PATH/fc-1.log

start() {
    echo \"Starting \$NAME...\"
    if [ -f \$PIDFILE ]; then
        PID=\$(cat \$PIDFILE)
        if kill -0 \$PID 2>/dev/null; then
            echo \"\$NAME is already running (PID \$PID)\"
            return 1
        fi
    fi
    mkdir -p $LOG_PATH $RUN_PATH
    nohup \$DAEMON >> \$LOGFILE 2>&1 &
    echo \$! > \$PIDFILE
    echo \"\$NAME started (PID \$!)\"
}

stop() {
    echo \"Stopping \$NAME...\"
    if [ -f \$PIDFILE ]; then
        PID=\$(cat \$PIDFILE)
        if kill -0 \$PID 2>/dev/null; then
            kill \$PID
            rm -f \$PIDFILE
            echo \"\$NAME stopped\"
        else
            echo \"\$NAME is not running\"
            rm -f \$PIDFILE
        fi
    else
        echo \"\$NAME is not running\"
    fi
}

status() {
    if [ -f \$PIDFILE ]; then
        PID=\$(cat \$PIDFILE)
        if kill -0 \$PID 2>/dev/null; then
            echo \"\$NAME is running (PID \$PID)\"
            return 0
        fi
    fi
    echo \"\$NAME is not running\"
    return 1
}

case \"\$1\" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
        echo \"Usage: \$0 {start|stop|restart|status}\"
        exit 1
        ;;
esac
INITEOF"

    remote_cmd "chmod +x $INIT_SCRIPT"

    success "sysvinit script created"

    printf "\n"
    printf "Service commands:\n"
    printf "  Start:   /etc/init.d/fc-1 start\n"
    printf "  Stop:    /etc/init.d/fc-1 stop\n"
    printf "  Status:  /etc/init.d/fc-1 status\n"
    printf "  Restart: /etc/init.d/fc-1 restart\n"
    printf "  Logs:    tail -f %s/fc-1.log\n" "$LOG_PATH"

    return 0
}

# Setup systemd service
setup_systemd() {
    status "Setting up systemd service..."

    UNIT_FILE="/etc/systemd/system/fc-1.service"

    if ! remote_writable "/etc/systemd/system"; then
        warning "Cannot write to /etc/systemd/system, using userland wrapper instead"
        setup_userland
        return 1
    fi

    # Create unit file
    remote_cmd "cat > $UNIT_FILE << 'UNITEOF'
[Unit]
Description=FC-1 Gateway Application
After=network.target

[Service]
Type=simple
ExecStart=$FC1_PATH
Restart=on-failure
RestartSec=5
StandardOutput=append:$LOG_PATH/fc-1.log
StandardError=append:$LOG_PATH/fc-1.log

[Install]
WantedBy=multi-user.target
UNITEOF"

    # Reload systemd
    remote_cmd "systemctl daemon-reload"

    success "systemd service created"

    printf "\n"
    printf "Service commands:\n"
    printf "  Start:   systemctl start fc-1\n"
    printf "  Stop:    systemctl stop fc-1\n"
    printf "  Status:  systemctl status fc-1\n"
    printf "  Enable:  systemctl enable fc-1\n"
    printf "  Logs:    journalctl -u fc-1 -f\n"
    printf "           tail -f %s/fc-1.log\n" "$LOG_PATH"

    return 0
}

# Setup userland wrappers (no root required)
setup_userland() {
    status "Setting up userland wrapper scripts..."

    REMOTE_HOME=$(remote_cmd "echo \$HOME")
    if [ -z "$REMOTE_HOME" ]; then
        REMOTE_HOME="/home/$TARGET_USER"
    fi

    # Ensure paths are set for userland
    LOG_PATH="$REMOTE_HOME/fc-1-logs"
    RUN_PATH="$REMOTE_HOME/fc-1-run"

    remote_cmd "mkdir -p $LOG_PATH $RUN_PATH"

    # Create run script
    remote_cmd "cat > $REMOTE_HOME/fc1_run.sh << 'RUNEOF'
#!/bin/sh
# FC-1 Run Script (userland)
DAEMON=$FC1_PATH
PIDFILE=$RUN_PATH/fc-1.pid
LOGFILE=$LOG_PATH/fc-1.log

if [ -f \$PIDFILE ]; then
    PID=\$(cat \$PIDFILE)
    if kill -0 \$PID 2>/dev/null; then
        echo \"FC-1 is already running (PID \$PID)\"
        exit 1
    fi
fi

echo \"Starting FC-1...\"
nohup \$DAEMON >> \$LOGFILE 2>&1 &
echo \$! > \$PIDFILE
echo \"FC-1 started (PID \$!)\"
echo \"Logs: \$LOGFILE\"
RUNEOF"
    remote_cmd "chmod +x $REMOTE_HOME/fc1_run.sh"

    # Create stop script
    remote_cmd "cat > $REMOTE_HOME/fc1_stop.sh << 'STOPEOF'
#!/bin/sh
# FC-1 Stop Script (userland)
PIDFILE=$RUN_PATH/fc-1.pid

if [ -f \$PIDFILE ]; then
    PID=\$(cat \$PIDFILE)
    if kill -0 \$PID 2>/dev/null; then
        echo \"Stopping FC-1 (PID \$PID)...\"
        kill \$PID
        rm -f \$PIDFILE
        echo \"FC-1 stopped\"
    else
        echo \"FC-1 is not running (stale pidfile)\"
        rm -f \$PIDFILE
    fi
else
    # Try to find process anyway
    PID=\$(pidof FC-1 2>/dev/null || pgrep -f '/home/FC-1' 2>/dev/null || true)
    if [ -n \"\$PID\" ]; then
        echo \"Stopping FC-1 (PID \$PID)...\"
        kill \$PID
        echo \"FC-1 stopped\"
    else
        echo \"FC-1 is not running\"
    fi
fi
STOPEOF"
    remote_cmd "chmod +x $REMOTE_HOME/fc1_stop.sh"

    # Create status script
    remote_cmd "cat > $REMOTE_HOME/fc1_status.sh << 'STATEOF'
#!/bin/sh
# FC-1 Status Script (userland)
PIDFILE=$RUN_PATH/fc-1.pid

if [ -f \$PIDFILE ]; then
    PID=\$(cat \$PIDFILE)
    if kill -0 \$PID 2>/dev/null; then
        echo \"FC-1 is running (PID \$PID)\"
        ps -p \$PID -o pid,vsz,rss,time,comm 2>/dev/null || ps | grep \$PID
        exit 0
    else
        echo \"FC-1 is not running (stale pidfile)\"
        rm -f \$PIDFILE
        exit 1
    fi
else
    # Try to find process anyway
    PID=\$(pidof FC-1 2>/dev/null || pgrep -f '/home/FC-1' 2>/dev/null || true)
    if [ -n \"\$PID\" ]; then
        echo \"FC-1 is running (PID \$PID) - no pidfile\"
        ps -p \$PID -o pid,vsz,rss,time,comm 2>/dev/null || ps | grep \$PID
        exit 0
    fi
    echo \"FC-1 is not running\"
    exit 1
fi
STATEOF"
    remote_cmd "chmod +x $REMOTE_HOME/fc1_status.sh"

    success "Userland wrapper scripts created"

    printf "\n"
    printf "Service commands:\n"
    printf "  Start:   %s/fc1_run.sh\n" "$REMOTE_HOME"
    printf "  Stop:    %s/fc1_stop.sh\n" "$REMOTE_HOME"
    printf "  Status:  %s/fc1_status.sh\n" "$REMOTE_HOME"
    printf "  Logs:    tail -f %s/fc-1.log\n" "$LOG_PATH"

    return 0
}

##############################################################################
# Main
##############################################################################

# Handle optional argument - use config if not specified
if [ $# -ge 1 ]; then
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        usage
    fi
    TARGET="$1"
else
    # Get target from config file
    TARGET=$(get_configured_target)
    if [ -z "$TARGET" ]; then
        printf "ERROR: No target specified and TARGET_HOST not set in config\n" >&2
        printf "Either provide target as argument or configure config/target_connection.conf\n" >&2
        exit 1
    fi
fi

# Initialize SSH with password support from config
init_ssh "$TARGET"

# Extract hostname and user
TARGET_HOST=$(printf "%s" "$TARGET" | sed 's/.*@//')
TARGET_USER=$(printf "%s" "$TARGET" | sed 's/@.*//')
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/setup_service_${TARGET_HOST}_${TIMESTAMP}.txt"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

status "Setting up FC-1 service on target: $TARGET (port $SSH_PORT)"

# Test SSH connection
if ! test_ssh_connection; then
    error "Cannot connect to target via SSH"
    error "Check target IP, port ($SSH_PORT), and credentials"
    exit 1
fi

# Verify FC-1 exists
if ! remote_cmd_status "test -x $FC1_PATH"; then
    error "FC-1 not found or not executable at $FC1_PATH"
    printf "Run first: ./scripts/verify_fc1.sh %s\n" "$TARGET"
    exit 1
fi

success "FC-1 verified at $FC1_PATH"

# Start logging
{
    printf "Service Setup Log\n"
    printf "%s\n" "================="
    printf "Generated: %s\n" "$(date)"
    printf "Target: %s\n" "$TARGET"
    printf "FC-1 path: %s\n\n" "$FC1_PATH"
} > "$LOG_FILE"

# Setup runtime directories first
setup_dirs

{
    printf "Log path: %s\n" "$LOG_PATH"
    printf "Profile path: %s\n" "$PROFILE_PATH"
    printf "Run path: %s\n\n" "$RUN_PATH"
} >> "$LOG_FILE"

# Detect init system
INIT_SYSTEM=$(detect_init_system)
status "Detected init system: $INIT_SYSTEM"

{
    printf "Init system: %s\n\n" "$INIT_SYSTEM"
} >> "$LOG_FILE"

# Setup service based on init system
case "$INIT_SYSTEM" in
    runit)
        setup_runit
        ;;
    systemd)
        setup_systemd
        ;;
    openrc|sysvinit)
        setup_sysvinit
        ;;
    none|*)
        warning "No init system detected, using userland wrappers"
        setup_userland
        ;;
esac

{
    printf "\nSetup completed at: %s\n" "$(date)"
} >> "$LOG_FILE"

printf "\n"
status "Log saved to: $LOG_FILE"
printf "\n"
success "Service setup completed"
printf "Next step: ./scripts/profile_fc1.sh %s\n" "$TARGET"
