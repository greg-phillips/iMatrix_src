#!/usr/bin/env python3
"""
PTY Test Controller for Network Manager Testing

This script provides a flexible test harness for testing the embedded
application through a PTY (pseudo-terminal) interface.
"""

import os
import sys
import time
import pty
import select
import subprocess
import threading
import argparse
import json
import re
from datetime import datetime
from typing import Optional, List, Dict, Tuple

class PTYController:
    """PTY controller for automated testing"""
    
    def __init__(self, app_path: str, log_file: Optional[str] = None):
        self.app_path = app_path
        self.master_fd = None
        self.slave_fd = None
        self.process = None
        self.reader_thread = None
        self.running = False
        self.output_buffer = []
        self.output_lock = threading.Lock()
        self.log_file = None
        
        if log_file:
            self.log_file = open(log_file, 'w')
            
        # Test results
        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'timeout': 0,
            'start_time': datetime.now(),
            'tests': []
        }
    
    def start(self) -> bool:
        """Start the application with PTY"""
        try:
            # Create PTY
            self.master_fd, self.slave_fd = pty.openpty()
            
            # Get slave name for debugging
            slave_name = os.ttyname(self.slave_fd)
            self.log(f"Created PTY: {slave_name}")
            
            # Start the application
            self.process = subprocess.Popen(
                [self.app_path],
                stdin=self.slave_fd,
                stdout=self.slave_fd,
                stderr=self.slave_fd,
                preexec_fn=os.setsid
            )
            
            self.log(f"Started application with PID {self.process.pid}")
            
            # Start reader thread
            self.running = True
            self.reader_thread = threading.Thread(target=self._reader_loop)
            self.reader_thread.daemon = True
            self.reader_thread.start()
            
            # Wait for initialization
            time.sleep(2)
            
            return True
            
        except Exception as e:
            self.log(f"Failed to start: {e}")
            return False
    
    def stop(self):
        """Stop the application and clean up"""
        self.running = False
        
        if self.process:
            self.process.terminate()
            self.process.wait()
            
        if self.master_fd:
            os.close(self.master_fd)
            
        if self.log_file:
            self.log_file.close()
    
    def _reader_loop(self):
        """Thread function to read PTY output"""
        while self.running:
            try:
                ready, _, _ = select.select([self.master_fd], [], [], 0.1)
                if ready:
                    data = os.read(self.master_fd, 4096)
                    if data:
                        text = data.decode('utf-8', errors='replace')
                        with self.output_lock:
                            self.output_buffer.append(text)
                            print(text, end='', flush=True)
                            if self.log_file:
                                self.log_file.write(text)
                                self.log_file.flush()
            except Exception as e:
                if self.running:
                    self.log(f"Reader error: {e}")
                break
    
    def send_command(self, command: str, delay: float = 0.5) -> bool:
        """Send a command to the PTY"""
        try:
            cmd_bytes = f"{command}\r\n".encode('utf-8')
            os.write(self.master_fd, cmd_bytes)
            self.log(f"[SEND] {command}")
            time.sleep(delay)
            return True
        except Exception as e:
            self.log(f"Send error: {e}")
            return False
    
    def wait_for_output(self, pattern: str, timeout: float = 5.0) -> Optional[str]:
        """Wait for specific output pattern"""
        start_time = time.time()
        accumulated = ""
        
        while (time.time() - start_time) < timeout:
            with self.output_lock:
                if self.output_buffer:
                    accumulated += ''.join(self.output_buffer)
                    self.output_buffer.clear()
            
            if re.search(pattern, accumulated):
                return accumulated
                
            time.sleep(0.1)
        
        return None
    
    def clear_output(self):
        """Clear the output buffer"""
        with self.output_lock:
            self.output_buffer.clear()
    
    def log(self, message: str):
        """Log a message"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_msg = f"[{timestamp}] {message}\n"
        print(log_msg, end='')
        if self.log_file:
            self.log_file.write(log_msg)
            self.log_file.flush()
    
    def run_test(self, name: str, command: str, 
                 expected: Optional[str] = None, 
                 timeout: float = 5.0) -> bool:
        """Run a single test"""
        self.log(f"\n=== Test: {name} ===")
        self.results['total'] += 1
        
        test_result = {
            'name': name,
            'command': command,
            'expected': expected,
            'result': 'FAILED',
            'output': ''
        }
        
        # Clear output buffer
        self.clear_output()
        
        # Send command
        if not self.send_command(command):
            test_result['result'] = 'FAILED'
            test_result['output'] = 'Failed to send command'
            self.results['failed'] += 1
            self.results['tests'].append(test_result)
            return False
        
        # Check for expected output
        if expected:
            output = self.wait_for_output(expected, timeout)
            if output:
                test_result['result'] = 'PASSED'
                test_result['output'] = output[:200]  # Truncate for summary
                self.results['passed'] += 1
                self.log(f"PASSED: Found expected pattern '{expected}'")
            else:
                test_result['result'] = 'TIMEOUT'
                self.results['timeout'] += 1
                self.log(f"TIMEOUT: Pattern '{expected}' not found within {timeout}s")
        else:
            # No specific output expected
            time.sleep(1)
            test_result['result'] = 'PASSED'
            self.results['passed'] += 1
            self.log("PASSED: Command executed")
        
        self.results['tests'].append(test_result)
        return test_result['result'] == 'PASSED'


def run_network_tests(controller: PTYController):
    """Run the network manager test suite"""
    controller.log("\n=== Network Manager Test Suite ===\n")
    
    # Basic tests
    controller.run_test("Network Status", "net", "Network:")
    controller.run_test("Show Configuration", "c", "WiFi Reassociation:")
    
    # Interface control tests
    controller.run_test("Disable ETH0", "net eth0 down")
    time.sleep(2)
    controller.run_test("Check ETH0 Down", "net", "ETH0: DOWN")
    
    controller.run_test("Enable ETH0", "net eth0 up")
    time.sleep(5)
    controller.run_test("Check ETH0 Up", "net", "ETH0: UP")
    
    # WiFi tests
    controller.run_test("Disable WiFi", "net wlan0 down")
    time.sleep(2)
    controller.run_test("Enable WiFi", "net wlan0 up")
    time.sleep(5)
    
    # Online mode tests
    controller.run_test("Set Offline Mode", "online off", "DISABLED")
    controller.run_test("Set Online Mode", "online on", "ENABLED")
    
    # Hysteresis test
    controller.log("\n=== Hysteresis Test ===")
    for i in range(5):
        controller.send_command("net eth0 down")
        time.sleep(0.5)
        controller.send_command("net eth0 up")
        time.sleep(0.5)
    
    controller.run_test("Check Hysteresis Active", "net", 
                       r"(HYSTERESIS:|Switches:)", timeout=10)
    
    # State machine tests
    controller.log("\n=== State Machine Tests ===")
    controller.run_test("Check State", "net", r"Status: \w+")
    
    # Force all interfaces down
    controller.send_command("net eth0 down")
    controller.send_command("net wlan0 down")
    time.sleep(5)
    controller.run_test("Check Offline State", "net", "Network: OFFLINE")
    
    # Bring interfaces back up
    controller.send_command("net eth0 up")
    controller.send_command("net wlan0 up")
    time.sleep(10)
    controller.run_test("Check Online Recovery", "net", "Network: ONLINE")


def run_stress_tests(controller: PTYController):
    """Run stress tests"""
    controller.log("\n=== Stress Tests ===\n")
    
    # Rapid command test
    controller.log("Rapid command test...")
    start_time = time.time()
    for i in range(20):
        controller.send_command("net", delay=0.1)
    
    elapsed = time.time() - start_time
    controller.log(f"Sent 20 commands in {elapsed:.2f}s")
    
    # Concurrent interface switching
    controller.log("\nConcurrent interface switching...")
    for i in range(10):
        controller.send_command("net eth0 down", delay=0)
        controller.send_command("net wlan0 down", delay=0)
        time.sleep(0.5)
        controller.send_command("net eth0 up", delay=0)
        controller.send_command("net wlan0 up", delay=0)
        time.sleep(0.5)
    
    time.sleep(5)
    controller.run_test("System Still Responsive", "net", "Status:")


def main():
    parser = argparse.ArgumentParser(description='PTY Test Controller')
    parser.add_argument('app_path', help='Path to application to test')
    parser.add_argument('-l', '--log', help='Log file path')
    parser.add_argument('-t', '--tests', default='all', 
                       choices=['all', 'basic', 'stress'],
                       help='Which tests to run')
    parser.add_argument('-j', '--json', help='Save results as JSON')
    
    args = parser.parse_args()
    
    # Create controller
    controller = PTYController(args.app_path, args.log)
    
    try:
        # Start application
        if not controller.start():
            return 1
        
        # Run tests
        if args.tests in ['all', 'basic']:
            run_network_tests(controller)
        
        if args.tests in ['all', 'stress']:
            run_stress_tests(controller)
        
        # Print results
        results = controller.results
        duration = (datetime.now() - results['start_time']).total_seconds()
        
        print("\n=== Test Results ===")
        print(f"Duration:      {duration:.1f}s")
        print(f"Total tests:   {results['total']}")
        print(f"Passed:        {results['passed']}")
        print(f"Failed:        {results['failed']}")
        print(f"Timeouts:      {results['timeout']}")
        
        if results['total'] > 0:
            success_rate = 100.0 * results['passed'] / results['total']
            print(f"Success rate:  {success_rate:.1f}%")
        
        # Save JSON results if requested
        if args.json:
            with open(args.json, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to {args.json}")
        
        # Return exit code based on results
        return 0 if (results['failed'] + results['timeout']) == 0 else 1
        
    finally:
        controller.stop()


if __name__ == '__main__':
    sys.exit(main())