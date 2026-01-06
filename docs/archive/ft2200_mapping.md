# FT2200 OBD2 Gateway Sensor Mapping

**Date:** 2026-01-02
**Author:** Claude Code Analysis
**Status:** Draft - Awaiting Review

---

## Overview

This document maps sensors returned by the FT2200 OBD2 gateway to the iMatrix internal sensor definitions defined in `iMatrix/internal_sensors_def.h`.

**Source Files:**
- FT2200 Sensors: `docs/FT220/list_of_sensors_returned.json`
- iMatrix Sensors: `iMatrix/internal_sensors_def.h`

---

## Section 1: Matching Sensors

The following FT2200 sensors have direct mappings to existing iMatrix internal sensors:

| FT2200 PID | FT2200 Description | FT2200 Type | FT2200 Unit | iMatrix Sensor | iMatrix ID | Unit Match | Notes |
|------------|-------------------|-------------|-------------|----------------|------------|------------|-------|
| 04 | Calculated engine load | integer | percentage | CALCULATED_ENGINE_LOAD | 554 | Yes | Direct match |
| 05 | Engine coolant temperature | integer | Celsius | ENGINE_COOLANT_TEMPERATURE | 150 | Yes | Direct match |
| 0C | Engine RPM | float | RPM | ENGINE_RPM | 147 | Yes | Type difference: FT2200=float, iMatrix=unspecified |
| 0D | Vehicle speed | integer | km/h | VEHICLE_SPEED | 142 | Unknown | iMatrix unit unspecified - verify km/h or m/s |
| 10 | MAF air flow rate | float | grams/sec | MASS_AIR_FLOW | 555 | Unknown | iMatrix unit unspecified - verify g/s |
| 11 | Throttle position | integer | percentage | THROTTLE_POSITION | 149 | Yes | Direct match |
| 1F | Time since engine start | integer | seconds | ENGINE_RUN_TIME | 618 | Unknown | iMatrix unit unspecified - verify seconds |
| 2F | Fuel Level Input | integer | percentage | FUEL_LEVEL | 58 | Yes | Direct match |
| 5C | Engine oil temperature | integer | Celsius | ENGINE_OIL_TEMPERATURE | 148 | Yes | Direct match |
| A6 | Odometer (Extended PID) | integer | meters | OBD_ODOMETER | 561 | Unknown | iMatrix unit unspecified - verify meters or km |
| MIL | Malfunction Indicator Lamp Status | integer | bool | MIL_STATUS | 550 | Yes | Direct match (0/1 boolean) |

### Summary: 11 of 15 FT2200 sensors have existing iMatrix mappings

---

## Section 2: Unmatched Sensors

The following FT2200 sensors do NOT have direct mappings in the current iMatrix internal sensor definitions:

| FT2200 PID | FT2200 Description | FT2200 Type | FT2200 Unit | Suggested Action |
|------------|-------------------|-------------|-------------|------------------|
| 01 | Monitor status since DTCs cleared | integer | bitmask | **Add new sensor** - OBD2 readiness monitor status is distinct from MIL_STATUS_DTC_COUNT |
| 46 | Ambient air temperature | integer | Celsius | **Add new sensor** - No ambient/outside air temp sensor exists |
| 9D | Fuel Rail Pressure | float | kPa | **Add new sensor** - Fuel rail pressure is distinct from existing sensors |
| MPG | Miles Per Gallon (Calculated) | float | MPG | **Review** - Could map to FUEL_ECONOMY (61) but units may differ (MPG vs L/100km) |

### Detailed Analysis of Unmatched Sensors

#### 1. Monitor Status Since DTCs Cleared (PID 01)
- **OBD2 Standard:** Mode 01 PID 01 returns a bitmask indicating which emission monitors are supported and their completion status
- **Closest iMatrix Sensor:** `MIL_STATUS_DTC_COUNT` (616) - but this combines MIL status with DTC count, not readiness monitors
- **Recommendation:** Add `OBD_MONITOR_STATUS` sensor (new ID needed)

#### 2. Ambient Air Temperature (PID 46)
- **OBD2 Standard:** Outside/ambient air temperature from vehicle sensor
- **Closest iMatrix Sensor:** None - existing temperature sensors are for engine/battery/tire
- **Recommendation:** Add `AMBIENT_AIR_TEMPERATURE` sensor (new ID needed)

#### 3. Fuel Rail Pressure (PID 9D)
- **OBD2 Standard:** Fuel rail absolute pressure (extended range)
- **Closest iMatrix Sensor:** None - no fuel system pressure sensors exist
- **Recommendation:** Add `FUEL_RAIL_PRESSURE` sensor (new ID needed)

#### 4. Miles Per Gallon (Calculated)
- **Description:** Real-time fuel economy calculation
- **Closest iMatrix Sensors:**
  - `FUEL_ECONOMY` (61) - "Fuel_Economy" - likely candidate
  - `FUEL_ECONOMY_AVERAGE` (62) - "Fuel_Economy_Average"
  - `MPGE` (509) - "MPGe" - for electric vehicles
- **Issue:** Unit ambiguity - is FUEL_ECONOMY in MPG, km/L, or L/100km?
- **Recommendation:** Clarify FUEL_ECONOMY units; if MPG, use direct mapping

---

## Section 3: Unit Conversion Requirements

If unit conversions are needed, implement in the FT2200 data processing layer:

| Sensor | FT2200 Unit | iMatrix Unit (if different) | Conversion |
|--------|-------------|----------------------------|------------|
| Vehicle Speed | km/h | m/s (if applicable) | value / 3.6 |
| Odometer | meters | km (if applicable) | value / 1000 |
| Fuel Economy | MPG | L/100km (if applicable) | 235.215 / value |

---

## Section 4: Proposed New Sensor Definitions

If new sensors are approved, add to `internal_sensors_def.h`:

```c
/* FT2200 OBD2 Gateway Sensors */
X(OBD_MONITOR_STATUS, 631, "OBD_Monitor_Status")
X(AMBIENT_AIR_TEMPERATURE, 632, "Ambient_Air_Temperature")
X(FUEL_RAIL_PRESSURE, 633, "Fuel_Rail_Pressure")
```

**Note:** IDs 631-633 are suggested; verify no conflicts with existing definitions (current max observed: 630).

---

## Section 5: Implementation Checklist

- [ ] Review and approve sensor mappings
- [ ] Decide on unmatched sensor handling (add new or omit)
- [ ] Clarify unit specifications for ambiguous sensors
- [ ] Add new sensor definitions to `internal_sensors_def.h` (if approved)
- [ ] Implement FT2200 data translation in Fleet-Connect-1
- [ ] Add unit conversion routines (if needed)
- [ ] Test with live FT2200 data

---

## Appendix: Complete Mapping Table

| FT2200 PID | FT2200 Description | iMatrix Mapping | Status |
|------------|-------------------|-----------------|--------|
| 01 | Monitor status since DTCs cleared | *NONE* | Unmatched |
| 04 | Calculated engine load | CALCULATED_ENGINE_LOAD (554) | Matched |
| 05 | Engine coolant temperature | ENGINE_COOLANT_TEMPERATURE (150) | Matched |
| 0C | Engine RPM | ENGINE_RPM (147) | Matched |
| 0D | Vehicle speed | VEHICLE_SPEED (142) | Matched |
| 10 | MAF air flow rate | MASS_AIR_FLOW (555) | Matched |
| 11 | Throttle position | THROTTLE_POSITION (149) | Matched |
| 1F | Time since engine start | ENGINE_RUN_TIME (618) | Matched |
| 2F | Fuel Level Input | FUEL_LEVEL (58) | Matched |
| 46 | Ambient air temperature | *NONE* | Unmatched |
| 5C | Engine oil temperature | ENGINE_OIL_TEMPERATURE (148) | Matched |
| 9D | Fuel Rail Pressure | *NONE* | Unmatched |
| A6 | Odometer (Extended PID) | OBD_ODOMETER (561) | Matched |
| MIL | Malfunction Indicator Lamp Status | MIL_STATUS (550) | Matched |
| MPG | Miles Per Gallon (Calculated) | FUEL_ECONOMY (61)? | Review Needed |

---

*Document generated by Claude Code*
