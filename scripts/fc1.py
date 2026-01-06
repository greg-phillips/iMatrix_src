#!/usr/bin/env python3
"""
FC-1 Remote Control Script (Python version)
Run from host machine to control FC-1 on target

Usage: ./fc1.py [-d destination] [command] [options]

Supports both Linux/WSL and Windows.
- Linux/WSL: Uses sshpass for non-interactive password auth
- Windows: Uses paramiko library (pip install paramiko)
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

# Detect platform
IS_WINDOWS = platform.system() == "Windows"

# Try to import paramiko for Windows SSH support
PARAMIKO_AVAILABLE = False
PARAMIKO_ERROR = None
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError as e:
    PARAMIKO_ERROR = str(e)


class FC1Controller:
    """Controller for FC-1 remote operations via SSH."""

    LATEST_OS_VERSION = "4.0.0"
    MEMORY_THRESHOLD_KB = 509740  # 512MB threshold

    def __init__(self, target_host: str = "192.168.7.1", target_port: str = "22222",
                 target_user: str = "root", target_pass: str = "PasswordQConnect"):
        self.target_host = target_host
        self.target_port = target_port
        self.target_user = target_user
        self.target_pass = target_pass

        # Paths
        self.script_dir = Path(__file__).parent.resolve()
        self.remote_script_dir = "/usr/qk/etc/sv/FC-1"
        self.remote_script = f"{self.remote_script_dir}/fc1_service.sh"
        self.local_script = self.script_dir / "fc1_service.sh"
        self.local_binary = self.script_dir.parent / "Fleet-Connect-1" / "build" / "FC-1"
        self.remote_binary = "/usr/qk/bin/FC-1"

        # Expect tools paths
        self.expect_package = self.script_dir.parent / "external_tools" / "build" / "expect-arm.tar.gz"
        self.expect_cmd_script = self.script_dir / "fc1_cmd.exp"
        self.remote_expect_dir = "/usr/qk/etc/sv/FC-1/expect"
        self.remote_expect_cmd = "/tmp/fc1_cmd.exp"

        # OS Upgrade paths
        self.upgrade_dir = self.script_dir.parent / "quake_sw" / "rev_4.0.0"
        self.upgrade_dir_512mb = self.upgrade_dir / "OSv4.0.0_512MB"
        self.upgrade_dir_128mb = self.upgrade_dir / "OSv4.0.0_128MB"
        self.remote_upgrade_dir = "/root"

        # Memory model (set by detect_memory_model)
        self.memory_model: Optional[str] = None

    def _ssh_opts(self) -> list:
        """Return SSH options as a list."""
        return [
            "-p", self.target_port,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10"
        ]

    def _scp_opts(self) -> list:
        """Return SCP options as a list."""
        return [
            "-P", self.target_port,
            "-o", "StrictHostKeyChecking=no"
        ]

    def _run_cmd(self, cmd: list, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            if capture:
                return e
            raise

    def check_sshpass(self) -> bool:
        """Check if sshpass (Linux) or paramiko (Windows) is available."""
        if IS_WINDOWS:
            if not PARAMIKO_AVAILABLE:
                print("Error: paramiko not available")
                if PARAMIKO_ERROR:
                    print(f"Import error: {PARAMIKO_ERROR}")
                print("Install with: pip install paramiko")
                return False
            return True
        else:
            # On Linux/WSL, require sshpass for non-interactive password auth
            if shutil.which("sshpass") is None:
                print("Error: sshpass not installed")
                print("Install with: sudo apt-get install sshpass")
                return False
            return True

    def clear_host_key(self):
        """Clear SSH known_hosts entry for target."""
        print(f"Clearing old SSH host key for [{self.target_host}]:{self.target_port}...")
        known_hosts = Path.home() / ".ssh" / "known_hosts"
        if known_hosts.exists():
            subprocess.run(
                ["ssh-keygen", "-f", str(known_hosts), "-R", f"[{self.target_host}]:{self.target_port}"],
                capture_output=True
            )

    def _build_ssh_cmd(self, command: str) -> list:
        """Build SSH command list for the current platform."""
        if IS_WINDOWS:
            # Windows: use OpenSSH directly (will prompt for password or use keys)
            return [
                "ssh", *self._ssh_opts(),
                f"{self.target_user}@{self.target_host}",
                command
            ]
        else:
            # Linux/WSL: use sshpass for non-interactive password auth
            return [
                "sshpass", "-p", self.target_pass,
                "ssh", *self._ssh_opts(),
                f"{self.target_user}@{self.target_host}",
                command
            ]

    def _build_scp_cmd(self, local_path: Path, remote_path: str) -> list:
        """Build SCP command list for the current platform."""
        if IS_WINDOWS:
            # Windows: use OpenSSH SCP directly
            return [
                "scp", *self._scp_opts(),
                str(local_path),
                f"{self.target_user}@{self.target_host}:{remote_path}"
            ]
        else:
            # Linux/WSL: use sshpass for non-interactive password auth
            return [
                "sshpass", "-p", self.target_pass,
                "scp", *self._scp_opts(),
                str(local_path),
                f"{self.target_user}@{self.target_host}:{remote_path}"
            ]

    def _get_paramiko_client(self) -> 'paramiko.SSHClient':
        """Get a connected paramiko SSH client."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.target_host,
            port=int(self.target_port),
            username=self.target_user,
            password=self.target_pass,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        return client

    def run_remote(self, command: str, capture: bool = False) -> Tuple[int, str, str]:
        """Run command on target via SSH."""
        if IS_WINDOWS and PARAMIKO_AVAILABLE:
            try:
                client = self._get_paramiko_client()
                stdin, stdout, stderr = client.exec_command(command)
                exit_code = stdout.channel.recv_exit_status()
                stdout_str = stdout.read().decode('utf-8', errors='replace')
                stderr_str = stderr.read().decode('utf-8', errors='replace')
                client.close()

                if capture:
                    return exit_code, stdout_str, stderr_str
                else:
                    if stdout_str:
                        print(stdout_str, end='')
                    if stderr_str:
                        print(stderr_str, end='', file=sys.stderr)
                    return exit_code, stdout_str, stderr_str
            except Exception as e:
                if capture:
                    return 1, "", str(e)
                else:
                    print(f"SSH Error: {e}", file=sys.stderr)
                    return 1, "", str(e)
        else:
            cmd = self._build_ssh_cmd(command)
            result = subprocess.run(cmd, capture_output=True, text=True)
            if capture:
                return result.returncode, result.stdout, result.stderr
            else:
                if result.stdout:
                    print(result.stdout, end='')
                if result.stderr:
                    print(result.stderr, end='', file=sys.stderr)
                return result.returncode, result.stdout, result.stderr

    def scp_to_target(self, local_path: Path, remote_path: str) -> bool:
        """Copy file to target via SCP."""
        if IS_WINDOWS and PARAMIKO_AVAILABLE:
            try:
                client = self._get_paramiko_client()
                sftp = client.open_sftp()
                sftp.put(str(local_path), remote_path)
                sftp.close()
                client.close()
                return True
            except Exception as e:
                print(f"SFTP Error: {e}", file=sys.stderr)
                return False
        else:
            cmd = self._build_scp_cmd(local_path, remote_path)
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"SCP Error: {result.stderr}", file=sys.stderr)
                return False
            return True

    def check_target(self) -> bool:
        """Check if target is reachable and SSH works."""
        # Ping check (different syntax on Windows vs Linux)
        if IS_WINDOWS:
            ping_cmd = ["ping", "-n", "1", "-w", "2000", self.target_host]
        else:
            ping_cmd = ["ping", "-c", "1", "-W", "2", self.target_host]

        result = subprocess.run(ping_cmd, capture_output=True)
        if result.returncode != 0:
            print(f"Error: Cannot reach target at {self.target_host}")
            return False

        # SSH connection test
        retcode, stdout, stderr = self.run_remote("echo ok", capture=True)
        combined = stdout + stderr

        # Check for host key issues
        if "REMOTE HOST IDENTIFICATION HAS CHANGED" in combined or "Host key verification failed" in combined:
            print("Device changed detected - host key mismatch")
            self.clear_host_key()
            print("Retrying connection...")
            retcode, stdout, stderr = self.run_remote("echo ok", capture=True)
            combined = stdout + stderr

        # Verify SSH works
        if "ok" not in stdout:
            print("Error: SSH connection failed")
            print(combined)
            return False

        return True

    def deploy_script(self):
        """Deploy fc1_service.sh to target."""
        print("Deploying fc1_service.sh to target...")
        # Create directory if it doesn't exist
        self.run_remote(f"mkdir -p {self.remote_script_dir}")
        if not self.scp_to_target(self.local_script, self.remote_script):
            print("Error: Failed to copy service script")
            return False
        self.run_remote(f"chmod +x {self.remote_script}")
        print(f"Deployed to {self.remote_script}")
        return True

    def push_binary(self, start_service: bool = False):
        """Push built binary to target."""
        if not self.local_binary.exists():
            print(f"Error: Binary not found at {self.local_binary}")
            print("Run 'make' in Fleet-Connect-1/build first")
            return False

        print("Stopping FC-1 service...")
        self.run_remote("sv stop FC-1", capture=True)
        import time
        time.sleep(1)

        print("Pushing FC-1 binary to target...")
        if not self.scp_to_target(self.local_binary, self.remote_binary):
            print("Error: Failed to copy binary")
            return False

        print("Setting permissions...")
        self.run_remote(f"chmod +x {self.remote_binary}")

        if start_service:
            print("Starting FC-1 service...")
            self.run_remote("sv start FC-1")
        else:
            print("FC-1 service left stopped (use 'push -run' to auto-start)")

        print("")
        print(f"Deployed: {self.local_binary} -> {self.remote_binary}")
        self.run_remote(f"ls -la {self.remote_binary}")
        return True

    def push_config(self, config_file: str):
        """Push configuration file to target."""
        remote_config_dir = "/usr/qk/etc/sv/FC-1"
        config_path = Path(config_file)

        if not config_path.exists():
            print(f"Error: Configuration file not found: {config_file}")
            return False

        config_basename = config_path.name

        print("Deploying configuration file to target...")
        print(f"Source: {config_file}")
        print(f"Target: {remote_config_dir}/{config_basename}")

        # Delete existing .bin files
        print(f"Removing existing .bin files from {remote_config_dir}...")
        retcode, stdout, stderr = self.run_remote(f"ls {remote_config_dir}/*.bin 2>/dev/null", capture=True)
        if stdout.strip():
            print("Found .bin files to remove:")
            print(stdout)
            self.run_remote(f"rm -f {remote_config_dir}/*.bin")
            print("Removed .bin files")
        else:
            print("No .bin files found")

        # Copy configuration file
        print("Copying configuration file...")
        if not self.scp_to_target(config_path, f"{remote_config_dir}/{config_basename}"):
            print("Error: Failed to copy configuration file")
            return False

        # Verify
        retcode, _, _ = self.run_remote(f"test -f {remote_config_dir}/{config_basename}", capture=True)
        if retcode == 0:
            print("")
            print("Configuration deployed successfully:")
            self.run_remote(f"ls -la {remote_config_dir}/{config_basename}")
            return True
        else:
            print("Error: Configuration file not found on target after copy")
            return False

    def run_service_cmd(self, cmd: str, extra_args: list = None):
        """Run service script command on target."""
        # Deploy if script doesn't exist
        retcode, _, _ = self.run_remote(f"test -f {self.remote_script}", capture=True)
        if retcode != 0:
            self.deploy_script()

        args_str = " ".join(extra_args) if extra_args else ""
        self.run_remote(f"sh {self.remote_script} {cmd} {args_str}")

    def check_expect_installed(self) -> bool:
        """Check if expect is installed on target."""
        retcode, _, _ = self.run_remote(f"test -x {self.remote_expect_dir}/bin/expect", capture=True)
        return retcode == 0

    def deploy_expect(self) -> bool:
        """Deploy expect tools to target."""
        if not self.expect_package.exists():
            print(f"Error: Expect package not found at {self.expect_package}")
            print("Run the build_expect.sh script first")
            return False

        print("Deploying expect tools to target (persistent location)...")
        print(f"Package: {self.expect_package}")
        print(f"Target: {self.remote_expect_dir}")

        # Copy expect package
        print("Copying package to target...")
        if not self.scp_to_target(self.expect_package, "/tmp/expect-arm.tar.gz"):
            print("Error: SCP failed to copy expect package")
            return False

        # Verify file arrived
        retcode, _, _ = self.run_remote("test -f /tmp/expect-arm.tar.gz", capture=True)
        if retcode != 0:
            print("Error: Package file not found on target after SCP")
            return False

        # Create directory and extract
        print(f"Extracting to {self.remote_expect_dir}...")
        self.run_remote(f"mkdir -p {self.remote_expect_dir}")

        retcode, _, _ = self.run_remote(
            f"cd {self.remote_expect_dir} && tar xzf /tmp/expect-arm.tar.gz",
            capture=True
        )
        if retcode != 0:
            print("Error: Failed to extract expect package")
            self.run_remote("rm -f /tmp/expect-arm.tar.gz")
            return False

        # Clean up
        self.run_remote("rm -f /tmp/expect-arm.tar.gz")

        # Verify
        retcode, _, _ = self.run_remote(f"test -x {self.remote_expect_dir}/bin/expect-wrapper", capture=True)
        if retcode == 0:
            print(f"Expect tools deployed successfully to {self.remote_expect_dir}")
            return True
        else:
            print("Error: expect-wrapper not found after deployment")
            return False

    def run_cli_cmd(self, cli_cmd: str):
        """Execute CLI command via expect/microcom."""
        if not cli_cmd:
            print("Error: No command specified")
            print("Usage: fc1.py cmd \"<command>\"")
            return False

        # Check/deploy expect
        if not self.check_expect_installed():
            print("Expect not found on target. Deploying...")
            if not self.deploy_expect():
                return False

        # Copy expect script
        if not self.expect_cmd_script.exists():
            print(f"Error: Expect script not found at {self.expect_cmd_script}")
            return False

        if not self.scp_to_target(self.expect_cmd_script, self.remote_expect_cmd):
            return False
        self.run_remote(f"chmod +x {self.remote_expect_cmd}")

        # Run expect script
        print(f"Executing: {cli_cmd}")
        print("---")
        self.run_remote(f"{self.remote_expect_dir}/bin/expect-wrapper {self.remote_expect_cmd} '{cli_cmd}'")
        return True

    def check_os_version(self) -> bool:
        """Check if OS upgrade is needed. Returns True if upgrade needed."""
        print("Checking OS version on target...")

        retcode, versions, _ = self.run_remote("cat /var/ver/versions 2>/dev/null", capture=True)

        if not versions:
            print("Warning: Could not read /var/ver/versions")
            return False

        # Extract version components
        uboot_ver = kernel_ver = squash_ver = rootfs_ver = None

        for line in versions.strip().split('\n'):
            if line.startswith("u-boot="):
                uboot_ver = line.split('=')[1]
            elif line.startswith("kernel="):
                kernel_ver = line.split('=')[1]
            elif line.startswith("squash-fs="):
                squash_ver = line.split('=')[1]
            elif line.startswith("root-fs="):
                rootfs_ver = line.split('=')[1]

        print("Current versions:")
        print(f"  u-boot:    {uboot_ver or 'unknown'}")
        print(f"  kernel:    {kernel_ver or 'unknown'}")
        print(f"  squash-fs: {squash_ver or 'unknown'}")
        print(f"  root-fs:   {rootfs_ver or 'unknown'}")
        print(f"  Latest:    {self.LATEST_OS_VERSION}")

        # Check if all components are at latest
        if (uboot_ver == self.LATEST_OS_VERSION and
            kernel_ver == self.LATEST_OS_VERSION and
            squash_ver == self.LATEST_OS_VERSION and
            rootfs_ver == self.LATEST_OS_VERSION):
            print("")
            print(f"OS is up to date ({self.LATEST_OS_VERSION})")
            return False

        print("")
        print(f"OS upgrade available: current -> {self.LATEST_OS_VERSION}")
        return True

    def detect_memory_model(self) -> bool:
        """Detect memory model (512MB or 128MB)."""
        print("Detecting memory model...")

        retcode, meminfo, _ = self.run_remote("cat /proc/meminfo 2>/dev/null", capture=True)

        if not meminfo:
            print("Error: Could not read /proc/meminfo")
            return False

        mem_total_kb = None
        for line in meminfo.split('\n'):
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2:
                    mem_total_kb = int(parts[1])
                break

        if mem_total_kb is None:
            print("Error: Could not parse MemTotal")
            return False

        print(f"Detected memory: {mem_total_kb} kB")

        if mem_total_kb >= self.MEMORY_THRESHOLD_KB:
            self.memory_model = "512"
            print("Memory model: 512MB")
        else:
            self.memory_model = "128"
            print("Memory model: 128MB")

        return True

    def run_update_component(self, component: str, archive: str) -> bool:
        """Run update_universal.sh for a component."""
        retcode, output, stderr = self.run_remote(
            f"/etc/update_universal.sh --yes --type {component} --save --arch {archive} --dir {self.remote_upgrade_dir}",
            capture=True
        )
        print(output)
        if stderr:
            print(stderr, file=sys.stderr)

        # Check for success string (script may return non-zero even on success)
        return "Finish update artifact" in output

    def perform_os_upgrade(self) -> bool:
        """Perform OS upgrade on target device."""
        if not self.memory_model:
            print("Error: Memory model not detected")
            return False

        if self.memory_model == "512":
            upgrade_src_dir = self.upgrade_dir_512mb
            uboot_file = "u-boot-512_4.0.0.zip"
        else:
            upgrade_src_dir = self.upgrade_dir_128mb
            uboot_file = "u-boot-128_4.0.0.zip"

        # Verify upgrade files exist
        print(f"Verifying upgrade files in {upgrade_src_dir}...")
        files = ["kernel_4.0.0.zip", "root-fs_4.0.0.zip", "squash-fs_4.0.0.zip", uboot_file]
        for f in files:
            if not (upgrade_src_dir / f).exists():
                print(f"Error: Missing upgrade file: {f}")
                return False
        print("All upgrade files found.")

        # Copy upgrade files
        print("")
        print(f"Copying upgrade files to target {self.remote_upgrade_dir}...")
        for f in files:
            print(f"  Copying {f}...")
            if not self.scp_to_target(upgrade_src_dir / f, f"{self.remote_upgrade_dir}/"):
                print(f"Error: Failed to copy {f}")
                return False
        print("All files copied successfully.")

        # Execute upgrade sequence
        print("")
        print("Executing OS upgrade sequence...")

        print("1. Upgrading squash-fs...")
        if not self.run_update_component("squash-fs", "squash-fs_4.0.0.zip"):
            print("Error: squash-fs upgrade failed")
            return False

        print("2. Upgrading kernel...")
        if not self.run_update_component("kernel", "kernel_4.0.0.zip"):
            print("Error: kernel upgrade failed")
            return False

        print(f"3. Upgrading u-boot ({self.memory_model}MB)...")
        if not self.run_update_component("u-boot", uboot_file):
            print("Error: u-boot upgrade failed")
            return False

        print("4. Upgrading root-fs (this will trigger reboot)...")
        if not self.run_update_component("root-fs", "root-fs_4.0.0.zip"):
            print("Error: root-fs upgrade failed")
            return False

        print("")
        print("OS upgrade complete. The device will reboot.")
        print("Please wait for the device to come back online, then verify with:")
        print("  ./fc1.py ssh")
        print("  cat /var/ver/versions")

        return True

    def check_and_prompt_upgrade(self) -> bool:
        """Check for OS upgrade and prompt user."""
        if self.check_os_version():
            print("")
            response = input("Would you like to upgrade the OS before continuing? [y/N]: ")
            if response.lower() in ['y', 'yes']:
                if not self.detect_memory_model():
                    print("Cannot determine memory model. Skipping upgrade.")
                    return True
                if self.perform_os_upgrade():
                    print("")
                    print("Upgrade initiated. Please reconnect after reboot.")
                    sys.exit(0)
                else:
                    print("")
                    cont = input("Upgrade failed. Continue with deploy/push anyway? [y/N]: ")
                    if cont.lower() not in ['y', 'yes']:
                        sys.exit(1)
            else:
                print("Skipping OS upgrade.")
        return True

    def ssh_session(self):
        """Open interactive SSH session to target."""
        print(f"Connecting to {self.target_host}...")
        if IS_WINDOWS and PARAMIKO_AVAILABLE:
            # Use paramiko for interactive session
            try:
                client = self._get_paramiko_client()
                channel = client.invoke_shell()

                import select
                import threading

                def read_output():
                    while True:
                        if channel.recv_ready():
                            data = channel.recv(1024).decode('utf-8', errors='replace')
                            print(data, end='', flush=True)
                        if channel.closed:
                            break

                # Start output reader thread
                reader = threading.Thread(target=read_output, daemon=True)
                reader.start()

                print("Interactive session started. Type 'exit' to close.")
                print("-" * 40)

                # Read input and send to channel
                while not channel.closed:
                    try:
                        user_input = input()
                        channel.send(user_input + "\n")
                        if user_input.strip() == "exit":
                            break
                    except EOFError:
                        break
                    except KeyboardInterrupt:
                        break

                channel.close()
                client.close()
            except Exception as e:
                print(f"SSH Error: {e}", file=sys.stderr)
        else:
            if IS_WINDOWS:
                cmd = [
                    "ssh", *self._ssh_opts(),
                    f"{self.target_user}@{self.target_host}"
                ]
                subprocess.run(cmd)
            else:
                cmd = [
                    "sshpass", "-p", self.target_pass,
                    "ssh", *self._ssh_opts(),
                    f"{self.target_user}@{self.target_host}"
                ]
                os.execvp("sshpass", cmd)

    def fix_eth0(self) -> bool:
        """Fix eth0 IP address if USB ethernet is down."""
        print("Fixing eth0 on target...")
        retcode, _, _ = self.run_remote(
            "ip addr flush dev eth0; ip addr add 192.168.7.1/24 dev eth0; ip link set eth0 up",
            capture=True
        )
        if retcode != 0:
            print("")
            print("ERROR: Failed to fix eth0 remotely.")
            print("")
            print("Suggested action - run manually on the target device:")
            print("  ip addr flush dev eth0; ip addr add 192.168.7.1/24 dev eth0; ip link set eth0 up")
            return False
        print("Done. Verifying:")
        self.run_remote("ip addr show eth0 | grep inet")
        return True


def show_help(controller: FC1Controller):
    """Show help message."""
    print("FC-1 Remote Control (Python)")
    print("")
    print("Usage: fc1.py [-d destination] <command> [options]")
    print("")
    if IS_WINDOWS:
        if PARAMIKO_AVAILABLE:
            print("Platform: Windows (using paramiko for SSH)")
        else:
            print("Platform: Windows (paramiko not installed - install with: pip install paramiko)")
    else:
        print("Platform: Linux/WSL (using sshpass for non-interactive auth)")
    print("")
    print("Options:")
    print("  -d <addr>   Specify target host (default: 192.168.7.1)")
    print("")
    print("Commands:")
    print("  start       Start FC-1 service on target")
    print("  stop        Stop FC-1 service on target")
    print("  restart     Restart FC-1 service")
    print("  status      Show service status")
    print("  enable      Enable FC-1 auto-start and start service")
    print("  disable     Disable FC-1 auto-start (with confirmation)")
    print("  disable -y  Disable without confirmation prompt")
    print("  run [opts]  Run FC-1 in foreground on target")
    print("  log         Show recent logs")
    print("  ppp         Show PPP link status (interface, service, log)")
    print("  cmd <cmd>   Execute CLI command via microcom (returns output)")
    print("  config <file> Deploy config file to target (removes old .bin files first)")
    print("  deploy      Deploy service script to target (checks OS version first)")
    print("  push        Push built FC-1 binary to target (checks OS version first)")
    print("  push -run   Push binary and start FC-1 service")
    print(f"  upgrade     Check and upgrade target OS to {controller.LATEST_OS_VERSION}")
    print("  fix-eth0    Fix eth0 IP address if USB ethernet is down")
    print("  ssh         Open SSH session to target")
    print("  clear-key   Clear SSH host key (for device changes)")
    print("  help        Show this help")
    print("")
    print(f"Target: {controller.target_user}@{controller.target_host}:{controller.target_port}")
    print("")
    print("Examples:")
    print("  fc1.py start                 # Start FC-1 on default host")
    print("  fc1.py -d 192.168.1.100 start  # Start FC-1 on specific host")
    print("  fc1.py stop                  # Stop FC-1")
    print("  fc1.py enable                # Enable auto-start")
    print("  fc1.py disable               # Disable auto-start (prompts)")
    print("  fc1.py disable -y            # Disable without prompt")
    print("  fc1.py status                # Check status")
    print("  fc1.py -d 10.0.0.50 status   # Check status on specific host")
    print("  fc1.py run -S                # Run with config summary")
    print("  fc1.py ppp                   # Show PPP link status")
    print('  fc1.py cmd "help"            # Execute \'help\' CLI command')
    print('  fc1.py cmd "cell status"     # Execute \'cell status\' CLI command')
    print('  fc1.py cmd "imx stats"       # Execute \'imx stats\' CLI command')
    print("  fc1.py config myconfig.bin   # Deploy config file to target")
    print("  fc1.py deploy                # Update service script on target")
    print("  fc1.py push                  # Deploy binary (service stays stopped)")
    print("  fc1.py push -run             # Deploy binary and start service")
    print("  fc1.py upgrade               # Check and upgrade OS if needed")
    print("  fc1.py -d beaglebone.local ssh  # SSH to specific host")
    print("")


def main():
    """Main entry point."""
    # Parse arguments manually to handle -d before command
    args = sys.argv[1:]
    target_host = "192.168.7.1"

    # Check for -d option
    if len(args) >= 2 and args[0] == "-d":
        target_host = args[1]
        args = args[2:]

    # Get command
    command = args[0] if args else None
    extra_args = args[1:] if len(args) > 1 else []

    # Create controller
    controller = FC1Controller(target_host=target_host)

    # Handle help before checking dependencies
    if command in ["help", "--help", "-h"]:
        show_help(controller)
        return

    # Check sshpass (or ssh on Windows)
    if not controller.check_sshpass():
        sys.exit(1)

    # Handle commands
    if command in ["start", "stop", "restart", "status", "enable", "log", "create-run", "ppp"]:
        if not controller.check_target():
            sys.exit(1)
        controller.run_service_cmd(command)

    elif command == "disable":
        if not controller.check_target():
            sys.exit(1)
        controller.run_service_cmd("disable", extra_args)

    elif command == "run":
        if not controller.check_target():
            sys.exit(1)
        controller.run_service_cmd("run", extra_args)

    elif command == "deploy":
        if not controller.check_target():
            sys.exit(1)
        controller.check_and_prompt_upgrade()
        controller.deploy_script()

    elif command == "push":
        if not controller.check_target():
            sys.exit(1)
        controller.check_and_prompt_upgrade()
        start_service = "-run" in extra_args
        controller.push_binary(start_service=start_service)

    elif command == "upgrade":
        if not controller.check_target():
            sys.exit(1)
        if controller.check_os_version():
            if not controller.detect_memory_model():
                print("Error: Cannot determine memory model")
                sys.exit(1)
            controller.perform_os_upgrade()
        else:
            print("No upgrade needed.")

    elif command == "ssh":
        if not controller.check_target():
            sys.exit(1)
        controller.ssh_session()

    elif command == "cmd":
        if not controller.check_target():
            sys.exit(1)
        cli_cmd = " ".join(extra_args)
        if not cli_cmd:
            print("Error: No command specified")
            print("Usage: fc1.py cmd \"<command>\"")
            sys.exit(1)
        controller.run_cli_cmd(cli_cmd)

    elif command == "config":
        if not controller.check_target():
            sys.exit(1)
        if not extra_args:
            print("Error: No configuration file specified")
            print("Usage: fc1.py config <config_file>")
            sys.exit(1)
        controller.push_config(extra_args[0])

    elif command == "clear-key":
        controller.clear_host_key()
        print("Host key cleared. Next connection will accept new key.")

    elif command == "fix-eth0":
        if not controller.check_target():
            sys.exit(1)
        if not controller.fix_eth0():
            sys.exit(1)

    elif command is None:
        # Default: show status
        if not controller.check_target():
            sys.exit(1)
        controller.run_service_cmd("status")

    else:
        print(f"Unknown command: {command}")
        print("Run 'fc1.py help' for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
