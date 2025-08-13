# Network Manager - TODO List

## High Priority Tasks

### 1. Complete Remaining Implementation Phases
- [ ] Phase 3.2: Improve WiFi re-enable timing for DHCP
  - Add configurable grace period after WiFi re-enable
  - Delay first ping test to allow DHCP completion
  - Track DHCP acquisition time for metrics
  
- [ ] Phase 3.3: Document interface priority logic
  - Create clear documentation of cost-based selection
  - Explain why eth0/wifi preferred over cellular
  - Add configuration guide for priority tuning

- [ ] Phase 4.1: Simplify PPP retry logic with state machine
  - Refactor complex retry counters
  - Use state machine for PPP lifecycle
  - Improve blacklist decision logic

- [ ] Phase 4.2: Add fallback handling during interface verification
  - Handle verification failures gracefully
  - Implement automatic fallback to previous interface
  - Add verification timeout handling

### 2. Production Readiness
- [ ] Field testing with real network conditions
- [ ] Long-running stability tests (24-48 hours)
- [ ] Performance profiling under load
- [ ] Memory leak detection and validation
- [ ] Test with various AP configurations (WPA2/WPA3/Enterprise)

### 3. Enhanced Monitoring
- [ ] Add Prometheus metrics for network events
- [ ] Create Grafana dashboard templates
- [ ] Implement SNMP traps for failover events
- [ ] Add detailed logging for post-mortem analysis
- [ ] Create network health scoring system

## Medium Priority Tasks

### 4. Advanced Hysteresis Features
- [ ] Make hysteresis parameters runtime configurable via CLI
- [ ] Add per-interface hysteresis settings
- [ ] Implement adaptive hysteresis based on stability history
- [ ] Add hysteresis bypass for emergency failover
- [ ] Create hysteresis statistics and reporting

### 5. WiFi Enhancements
- [ ] Add 802.11k/v/r support for fast roaming
- [ ] Implement background scanning while connected
- [ ] Add RSSI-based proactive reassociation
- [ ] Support for multiple SSIDs with priorities
- [ ] Band steering support (2.4GHz vs 5GHz)

### 6. Cellular Optimizations
- [ ] Improve carrier selection algorithm
- [ ] Add signal strength monitoring
- [ ] Implement data usage tracking
- [ ] Add APN failover support
- [ ] Support for dual-SIM configurations

### 7. Configuration Management
- [ ] Create configuration file support (JSON/YAML)
- [ ] Add configuration validation tool
- [ ] Implement configuration hot-reload
- [ ] Add configuration backup/restore
- [ ] Create configuration migration tool

## Low Priority Tasks

### 8. Testing Enhancements
- [ ] Add fuzzing tests for state machine
- [ ] Create network simulation framework
- [ ] Add chaos engineering tests
- [ ] Implement performance regression tests
- [ ] Create automated test report generation

### 9. Documentation
- [ ] Create operator's guide
- [ ] Write troubleshooting guide
- [ ] Document all CLI commands
- [ ] Create architecture diagrams
- [ ] Write performance tuning guide

### 10. Code Quality
- [ ] Add static analysis (cppcheck, clang-tidy)
- [ ] Increase code coverage to >90%
- [ ] Refactor large functions
- [ ] Add more unit tests
- [ ] Create coding standards document

## Technical Debt

### 11. Refactoring Needs
- [ ] Split process_network.c into smaller modules
- [ ] Create proper interface abstraction layer
- [ ] Separate policy from mechanism
- [ ] Remove global variables where possible
- [ ] Improve error code consistency

### 12. Performance Optimizations
- [ ] Reduce ping test frequency when stable
- [ ] Implement adaptive ping timeout
- [ ] Add connection pooling for DNS
- [ ] Optimize state machine transitions
- [ ] Reduce mutex contention

## Future Features

### 13. Advanced Networking
- [ ] IPv6 support
- [ ] VPN integration
- [ ] SD-WAN capabilities
- [ ] Traffic shaping/QoS
- [ ] Multi-WAN load balancing

### 14. Cloud Integration
- [ ] Remote configuration management
- [ ] Cloud-based monitoring
- [ ] Automatic firmware updates
- [ ] Remote diagnostics
- [ ] Fleet management integration

### 15. Security Enhancements
- [ ] Add network intrusion detection
- [ ] Implement certificate-based auth
- [ ] Add firewall integration
- [ ] Support for 802.1X
- [ ] Encrypted configuration storage

## Known Issues

### 16. Current Limitations
- [ ] No IPv6 support currently
- [ ] Limited to 3 interface types
- [ ] No VLAN support
- [ ] Single routing table only
- [ ] No multicast routing

### 17. Bug Fixes Needed
- [ ] Occasional mutex timeout warnings
- [ ] DNS cache may become stale
- [ ] PPP cleanup not always complete
- [ ] WiFi scan may block too long
- [ ] Hysteresis counter overflow (after weeks)

## Testing Requirements

### 18. Test Scenarios
- [ ] Multi-AP roaming tests
- [ ] Cellular tower handoff testing
- [ ] Power failure recovery
- [ ] High packet loss conditions
- [ ] Extreme temperature testing

### 19. Compliance Testing
- [ ] EMC compliance validation
- [ ] Carrier certification tests
- [ ] WiFi Alliance testing
- [ ] Security penetration testing
- [ ] Performance benchmarking

## Documentation Needs

### 20. User Documentation
- [ ] Quick start guide
- [ ] CLI reference manual
- [ ] Troubleshooting flowcharts
- [ ] FAQ document
- [ ] Video tutorials

## Notes

- Priority should be given to completing the remaining implementation phases
- Production testing is critical before deployment
- Monitoring capabilities will greatly aid in field support
- Consider creating a network manager daemon for better system integration
- Regular review of hysteresis effectiveness needed based on field data