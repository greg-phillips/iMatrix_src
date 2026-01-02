Read: /home/greg/iMatrix/iMatrix_Client/docs/testing_fc_1_application.md to learn how to connect to the gateway
use the srcript: /home/greg/iMatrix/iMatrix_Client$ scripts/fc1 to push a new copy of the program to the gateway. Full options for script are below.
'''
greg@Greg-P1-Laptop:~/iMatrix/iMatrix_Client$ scripts/fc1 help
FC-1 Remote Control

Usage: scripts/fc1 [-d destination] <command> [options]

Options:
  -d <addr>   Specify target host (default: 192.168.7.1)

Commands:
  start       Start FC-1 service on target
  stop        Stop FC-1 service on target
  restart     Restart FC-1 service
  status      Show service status
  enable      Enable FC-1 auto-start and start service
  disable     Disable FC-1 auto-start (with confirmation)
  disable -y  Disable without confirmation prompt
  run [opts]  Run FC-1 in foreground on target
  log         Show recent logs
  ppp         Show PPP link status (interface, service, log)
  cmd <cmd>   Execute CLI command via microcom (returns output)
  deploy      Deploy service script to target
  push        Push built FC-1 binary to target (leaves service stopped)
  push -run   Push binary and start FC-1 service
  ssh         Open SSH session to target
  clear-key   Clear SSH host key (for device changes)
  help        Show this help

Target: root@192.168.7.1:22222

Examples:
  scripts/fc1 start                 # Start FC-1 on default host
  scripts/fc1 -d 192.168.1.100 start  # Start FC-1 on specific host
  scripts/fc1 stop                  # Stop FC-1
  scripts/fc1 enable                # Enable auto-start
  scripts/fc1 disable               # Disable auto-start (prompts)
  scripts/fc1 disable -y            # Disable without prompt
  scripts/fc1 status                # Check status
  scripts/fc1 -d 10.0.0.50 status   # Check status on specific host
  scripts/fc1 run -S                # Run with config summary
  scripts/fc1 ppp                   # Show PPP link status
  scripts/fc1 cmd "help"            # Execute 'help' CLI command
  scripts/fc1 cmd "cell status"     # Execute 'cell status' CLI command
  scripts/fc1 cmd "imx stats"       # Execute 'imx stats' CLI command
  scripts/fc1 deploy                # Update service script on target
  scripts/fc1 push                  # Deploy binary (service stays stopped)
  scripts/fc1 push -run             # Deploy binary and start service
  scripts/fc1 -d beaglebone.local ssh  # SSH to specific host
'''
Once the program is pushed then start the program.
Connect to the script to get the output of a specific command to see the progress of any test.
Use the script to stop the program
extract the log and review 
