<!--
AUTO-GENERATED PROMPT
Generated from: docs/prompt_work/GPS_errors_issue.yaml
Generated on: 2026-01-05
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim: Implement Robust GPS Telemetry Filter with State Machine

**Date:** 2026-01-05
**Branch:** feature/gps_errors_issue

---

## Code Structure:

iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).

Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH
The wifi communications uses a combination Wi-Fi/Bluetooth chipset
The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.

The user's name is Greg

Read and understand the following:

- iMatrix/location/process_nmea.c
- iMatrix/get_location.c

use the template files as a base for any new files created:
- iMatrix/templates/blank.c
- iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

### Additional Background

During testing the GPS we have found the data often contains a lot of noise and errors.

The system is a telematics gateway that must process incoming GPS telemetry (Latitude,
Longitude, Altitude, HDOP, and Satellite count) while integrating vehicle wheel speed
from the J1939 CAN bus. The goal is to provide a single, clean, filtered coordinate
point that handles three specific vehicle scenarios: driving, stationary (engine on
or off), and being towed.

## Task

Implement a robust state-machine filter that uses a recursive smoothing (alpha-beta) approach.

## Requirements & Logic

### Data Structures
Define a TelematicsTracker struct to persist state, including:
- Last valid Lat/Lon/Alt
- Motion state
- Stationary confirmation counter
- Initialization status

### Initialization
The tracker should initialize its "home" position only after receiving a high-confidence
fix (HDOP < 2.0 and Sats > 5).

### The Gatekeeper (Pre-Filtering)

**Signal Integrity:** Discard points where Satellites < 4 or HDOP > 3.5.

**Horizontal Gross Error:** Calculate the distance from the last known good point using
the Haversine formula. If distance > 1,000 meters (within a 1s interval), discard as a
multipath jump.

**Vertical Gross Error (Altitude):** If the vehicle is stationary or moving slowly, an
altitude change of > 50 meters between 1s samples is physically impossible. Use this as
a trigger to discard the horizontal data as well, as it indicates a multipath reflection.

### State Machine Logic

**State: MOVING** - Triggered if j1939_speed > 0.3 m/s OR if gps_distance > 15 meters
consistently without J1939 speed (detecting a Towed state).

**State: STATIONARY** - Triggered if j1939_speed == 0 AND gps_distance < 5 meters for
at least 10 consecutive samples.

### Smoothing Filter

Use the recursive formula: Output = LastValid + (Gain × (New - LastValid))

**Dynamic Gain:**
- If STATIONARY, set gain = 0.01 to lock the position and ignore drift.
- If MOVING, calculate gain = 1.0 / (hdop + 1.2), clamped at a maximum of 0.75.

## Code Interface

Implement the following function:

```c
void process_telematics_update(
    double raw_lat,
    double raw_lon,
    double raw_alt,
    float hdop,
    int num_sats,
    float j1939_speed,
    double *out_lat,
    double *out_lon,
    double *out_alt
);
```

## Implementation Constraints

- **Standard Headers Only:** Use only math.h and stdint.h.
- **Memory Efficiency:** Avoid printf, malloc, or any heap allocation. Use static or
  passed-in pointers for state.
- **Robustness:** Gracefully handle j1939_speed, using a special value flag if the speed is not available, from routine imx_get_j1939_speed() in: /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/OBD2/get_J1939_sensors.c
- **Documentation:** Provide detailed comments explaining how the Altitude check acts
  as a "Z-gate" to protect the Latitude/Longitude integrity.

### Files to Review/Modify

| File | Focus |
|------|-------|
| iMatrix/get_location.c | Review existing GPS handling implementation |
| iMatrix/location/process_nmea.c | Review NMEA processing for integration points |

### Notes

Ask any questions you need to before starting the work.

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** docs/gen/gps_errors_issue_plan.md ***, of all aspects and detailed todo list for me to review before commencing the implementation.
3. Once plan is approved implement and check off the items on the todo list as they are completed.
4. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found fix them immediately.
5. **Final build verification**: Before marking work complete, perform a final clean build to verify:
   - Zero compilation errors
   - Zero compilation warnings
   - All modified files compile successfully
   - The build completes without issues
6. Once I have determined the work is completed successfully add a concise description to the plan document of the work undertaken.
7. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.
8. Merge the branch back into the original branch.
9. Update all documents with relevant details

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** docs/prompt_work/GPS_errors_issue.yaml
**Generated:** 2026-01-05
