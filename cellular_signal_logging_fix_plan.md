# Cellular Signal Strength Logging Fix Plan

**Date**: 2025-11-22
**Time**: 12:35
**Document Version**: 1.0
**Status**: Analysis Complete
**Author**: Claude Code Analysis
**Log Analyzed**: net12.txt

---

## Executive Summary

Analysis of net12.txt reveals that while the cellular scan is functioning and testing each carrier's signal strength, **the logging is insufficient**. The system only logs a single line per carrier with minimal information, missing critical details needed for debugging and carrier selection analysis.

---

## Current Issues Identified

### 1. Minimal Signal Strength Logging

**Current Output** (from net12.txt):
```
[00:03:10.828] [Cellular Scan - State 6: Verizon Wireless signal strength: 16]
[00:03:21.269] [Cellular Scan - State 6: 313 100 signal strength: 18]
[00:03:36.924] [Cellular Scan - State 6: T-Mobile signal strength: 16]
[00:03:52.580] [Cellular Scan - State 6: AT&T signal strength: 16]
[00:04:03.023] [Cellular Scan - State 6:  signal strength: 17]  ← Empty name
[00:04:13.473] [Cellular Scan - State 6:  signal strength: 17]  ← Empty name
```

**Problems**:
- Only CSQ value logged (16, 18, etc.)
- No RSSI dBm conversion shown
- No BER (Bit Error Rate) logged
- Missing MCCMNC codes
- Missing status (available/current/forbidden)
- Empty carrier names for some entries

### 2. Missing Carrier Details from AT+COPS Response

**AT+COPS Response** (Line 1255):
```
+COPS: (2,"Verizon Wireless","VZW","311480",7),
       (3,"313 100","313 100","313100",7),
       (1,"T-Mobile","T-Mobile","310260",7),
       (1,"AT&T","AT&T","310410",7),
       ,  ← Empty entries
       ,  ← Empty entries
```

**Not Logged**:
- Status codes (1=available, 2=current, 3=forbidden)
- MCCMNC codes (311480, 313100, 310260, 310410)
- Technology (7=LTE)
- Full carrier names vs. short names

### 3. No Carrier Comparison Table

Missing a comprehensive summary showing:
- All carriers found
- Their signal strengths
- Selection criteria
- Why specific carrier was chosen

---

## Expected Logging Format

### Per-Carrier Testing Should Log:

```
[Cellular Scan] Testing carrier 1/6:
  Name: Verizon Wireless
  MCCMNC: 311480
  Status: Current (2)
  Technology: LTE (7)
[Cellular Scan] Connecting to Verizon Wireless (311480)...
[Cellular Scan] Sending AT+COPS=1,2,"311480"
[Cellular Scan] Connection result: OK
[Cellular Scan] Testing signal strength...
[Cellular Scan] Sending AT+CSQ
[Cellular Scan] Signal report:
  CSQ: 16
  RSSI: -81 dBm
  BER: 99 (unknown)
  Signal Quality: Fair (16/31)
```

### Final Summary Should Log:

```
[Cellular Scan] === Scan Results Summary ===
[Cellular Scan] Found 6 carriers (4 valid, 2 empty):

Idx | Name               | MCCMNC  | Status    | Tech | CSQ | RSSI     | Quality
----|-------------------|---------|-----------|------|-----|----------|----------
1   | Verizon Wireless  | 311480  | Current   | LTE  | 16  | -81 dBm  | Fair
2   | 313 100           | 313100  | Forbidden | LTE  | 18  | -77 dBm  | Fair
3   | T-Mobile          | 310260  | Available | LTE  | 16  | -81 dBm  | Fair
4   | AT&T              | 310410  | Available | LTE  | 16  | -81 dBm  | Fair
5   | (empty)           | -       | -         | -    | 17  | -79 dBm  | Fair
6   | (empty)           | -       | -         | -    | 17  | -79 dBm  | Fair

[Cellular Scan] Best carrier: 313 100 (313100) with CSQ=18 (-77 dBm)
[Cellular Scan] Note: 313 100 is FORBIDDEN, selecting next best
[Cellular Scan] Selected: AT&T (310410) with CSQ=16 (-81 dBm)
```

---

## Root Cause Analysis

### 1. Parsing Issues
- Empty carrier entries in AT+COPS response not handled properly
- Parser creating entries for empty commas (,,)
- Missing validation of parsed data

### 2. Logging Deficiencies
- Only logging final CSQ value, not full details
- Not logging intermediate steps (connection attempt, AT command, response)
- Missing RSSI conversion and quality assessment

### 3. Missing Information Correlation
- Not associating carrier info from AT+COPS with signal test results
- Not building comprehensive carrier profile

---

## Implementation Fix

### 1. Enhanced Carrier Structure

```c
typedef struct {
    char long_name[64];     // "Verizon Wireless"
    char short_name[32];    // "VZW"
    char mccmnc[16];        // "311480"
    int status;             // 0=unknown, 1=available, 2=current, 3=forbidden
    int technology;         // 0=GSM, 2=UMTS, 7=LTE
    int csq;                // 0-31 or 99
    int rssi_dbm;           // Calculated from CSQ
    int ber;                // Bit error rate
    bool valid;             // False for empty entries
    bool tested;            // Has signal been tested
    char test_result[64];   // "OK", "FAILED", "TIMEOUT", etc.
} CarrierInfo;
```

### 2. Enhanced Logging Functions

```c
/**
 * @brief Log carrier details during scan
 */
void log_carrier_details(int idx, int total, CarrierInfo* carrier) {
    PRINTF("[Cellular Scan] ========================================\n");
    PRINTF("[Cellular Scan] Testing carrier %d/%d:\n", idx + 1, total);
    PRINTF("[Cellular Scan]   Name: %s\n",
           carrier->long_name[0] ? carrier->long_name : "(empty)");
    PRINTF("[Cellular Scan]   MCCMNC: %s\n",
           carrier->mccmnc[0] ? carrier->mccmnc : "N/A");
    PRINTF("[Cellular Scan]   Status: %s (%d)\n",
           get_status_string(carrier->status), carrier->status);
    PRINTF("[Cellular Scan]   Technology: %s (%d)\n",
           get_tech_string(carrier->technology), carrier->technology);
    PRINTF("[Cellular Scan] ========================================\n");
}

/**
 * @brief Log signal test results
 */
void log_signal_test_results(CarrierInfo* carrier) {
    PRINTF("[Cellular Scan] Signal test results for %s:\n",
           carrier->long_name[0] ? carrier->long_name : carrier->mccmnc);
    PRINTF("[Cellular Scan]   CSQ: %d\n", carrier->csq);
    PRINTF("[Cellular Scan]   RSSI: %d dBm\n", carrier->rssi_dbm);
    PRINTF("[Cellular Scan]   BER: %d\n", carrier->ber);
    PRINTF("[Cellular Scan]   Signal Quality: %s (%d/31)\n",
           get_signal_quality_string(carrier->csq), carrier->csq);
    PRINTF("[Cellular Scan]   Test Result: %s\n", carrier->test_result);
}

/**
 * @brief Log comprehensive scan summary
 */
void log_scan_summary(CarrierInfo* carriers, int count) {
    PRINTF("\n[Cellular Scan] =======================================\n");
    PRINTF("[Cellular Scan] SCAN RESULTS SUMMARY\n");
    PRINTF("[Cellular Scan] =======================================\n");
    PRINTF("[Cellular Scan] Total carriers found: %d\n", count);

    // Count valid vs empty
    int valid_count = 0;
    for (int i = 0; i < count; i++) {
        if (carriers[i].valid) valid_count++;
    }
    PRINTF("[Cellular Scan] Valid carriers: %d, Empty entries: %d\n",
           valid_count, count - valid_count);

    // Table header
    PRINTF("\n");
    PRINTF("%-3s | %-18s | %-7s | %-10s | %-4s | %-3s | %-8s | %-10s\n",
           "Idx", "Name", "MCCMNC", "Status", "Tech", "CSQ", "RSSI", "Quality");
    PRINTF("----|-------------------|---------|------------|------|-----|----------|------------\n");

    // Table rows
    for (int i = 0; i < count; i++) {
        CarrierInfo* c = &carriers[i];

        if (!c->valid) {
            PRINTF("%-3d | %-18s | %-7s | %-10s | %-4s | %-3s | %-8s | %-10s\n",
                   i + 1, "(empty)", "-", "-", "-", "-", "-", "-");
        } else {
            char rssi_str[16];
            if (c->csq == 99) {
                strcpy(rssi_str, "unknown");
            } else {
                snprintf(rssi_str, sizeof(rssi_str), "%d dBm", c->rssi_dbm);
            }

            PRINTF("%-3d | %-18s | %-7s | %-10s | %-4s | %-3d | %-8s | %-10s\n",
                   i + 1,
                   c->long_name[0] ? c->long_name : c->short_name,
                   c->mccmnc,
                   get_status_string(c->status),
                   get_tech_short(c->technology),
                   c->csq,
                   rssi_str,
                   get_signal_quality_string(c->csq));
        }
    }

    PRINTF("\n[Cellular Scan] =======================================\n");
}

/**
 * @brief Convert CSQ to RSSI in dBm
 */
int csq_to_rssi_dbm(int csq) {
    if (csq == 99) return -999;  // Unknown
    if (csq == 0) return -113;
    if (csq == 31) return -51;
    return -113 + (csq * 2);
}

/**
 * @brief Get signal quality description
 */
const char* get_signal_quality_string(int csq) {
    if (csq == 99) return "Unknown";
    if (csq == 0) return "No Signal";
    if (csq < 10) return "Poor";
    if (csq < 15) return "Fair";
    if (csq < 20) return "Good";
    if (csq < 25) return "Very Good";
    return "Excellent";
}

/**
 * @brief Get carrier status string
 */
const char* get_status_string(int status) {
    switch (status) {
        case 0: return "Unknown";
        case 1: return "Available";
        case 2: return "Current";
        case 3: return "Forbidden";
        default: return "Invalid";
    }
}

/**
 * @brief Get technology string
 */
const char* get_tech_string(int tech) {
    switch (tech) {
        case 0: return "GSM";
        case 2: return "UMTS";
        case 7: return "LTE";
        case 9: return "5G";
        default: return "Unknown";
    }
}

const char* get_tech_short(int tech) {
    switch (tech) {
        case 0: return "GSM";
        case 2: return "3G";
        case 7: return "LTE";
        case 9: return "5G";
        default: return "?";
    }
}
```

### 3. Modified Scan State Machine Logging

```c
case CELL_SCAN_PARSE_COPS:
    // Parse AT+COPS response
    carrier_count = parse_cops_response(response, carriers, MAX_CARRIERS);

    PRINTF("[Cellular Scan] Parsed AT+COPS response:\n");
    PRINTF("[Cellular Scan]   Total entries: %d\n", carrier_count);

    // Log each parsed carrier
    for (int i = 0; i < carrier_count; i++) {
        if (carriers[i].valid) {
            PRINTF("[Cellular Scan]   [%d] %s (%s) - Status:%d, Tech:%d\n",
                   i + 1,
                   carriers[i].long_name,
                   carriers[i].mccmnc,
                   carriers[i].status,
                   carriers[i].technology);
        } else {
            PRINTF("[Cellular Scan]   [%d] (empty entry - will skip)\n", i + 1);
        }
    }
    break;

case CELL_SCAN_TEST_CARRIER:
    if (current_idx < carrier_count) {
        CarrierInfo* carrier = &carriers[current_idx];

        // Skip empty entries
        if (!carrier->valid) {
            PRINTF("[Cellular Scan] Skipping empty entry at index %d\n",
                   current_idx);
            current_idx++;
            break;
        }

        // Log full details before testing
        log_carrier_details(current_idx, carrier_count, carrier);

        // Connect to carrier
        PRINTF("[Cellular Scan] Attempting connection...\n");
        sprintf(cmd, "AT+COPS=1,2,\"%s\"", carrier->mccmnc);
        PRINTF("[Cellular Scan] Sending: %s\n", cmd);
        send_at_command(cmd, 30000);
        state = CELL_SCAN_WAIT_CONNECT;
    }
    break;

case CELL_SCAN_TEST_SIGNAL:
    PRINTF("[Cellular Scan] Testing signal strength...\n");
    PRINTF("[Cellular Scan] Sending: AT+CSQ\n");
    send_at_command("AT+CSQ", 10000);
    state = CELL_SCAN_WAIT_CSQ;
    break;

case CELL_SCAN_PROCESS_CSQ:
    // Parse CSQ response
    if (parse_csq_response(response, &csq, &ber)) {
        carriers[current_idx].csq = csq;
        carriers[current_idx].ber = ber;
        carriers[current_idx].rssi_dbm = csq_to_rssi_dbm(csq);
        carriers[current_idx].tested = true;
        strcpy(carriers[current_idx].test_result, "SUCCESS");

        // Log detailed results
        log_signal_test_results(&carriers[current_idx]);
    } else {
        PRINTF("[Cellular Scan] Failed to parse CSQ response\n");
        strcpy(carriers[current_idx].test_result, "PARSE_ERROR");
    }

    current_idx++;
    state = CELL_SCAN_TEST_CARRIER;
    break;

case CELL_SCAN_COMPLETE:
    PRINTF("[Cellular Scan] All carriers tested\n");

    // Log comprehensive summary
    log_scan_summary(carriers, carrier_count);

    // Select best carrier
    int best_idx = select_best_carrier(carriers, carrier_count);
    if (best_idx >= 0) {
        PRINTF("[Cellular Scan] SELECTED: %s (%s) with CSQ=%d (%d dBm)\n",
               carriers[best_idx].long_name,
               carriers[best_idx].mccmnc,
               carriers[best_idx].csq,
               carriers[best_idx].rssi_dbm);
    } else {
        PRINTF("[Cellular Scan] ERROR: No viable carrier found\n");
    }
    break;
```

---

## Testing Requirements

### 1. Verify Enhanced Logging
- Each carrier should have detailed multi-line log entry
- Signal strength should show CSQ, RSSI (dBm), and quality description
- Empty entries should be clearly marked and skipped

### 2. Verify Summary Table
- All carriers listed with complete information
- Status (Available/Current/Forbidden) shown correctly
- Selection logic explained in logs

### 3. Edge Cases
- Handle empty carrier entries (,,) without crashing
- Handle CSQ=99 (unknown) gracefully
- Log when forbidden carrier has best signal

---

## Expected Output After Fix

```
[Cellular Scan] ========================================
[Cellular Scan] Testing carrier 1/4:
[Cellular Scan]   Name: Verizon Wireless
[Cellular Scan]   MCCMNC: 311480
[Cellular Scan]   Status: Current (2)
[Cellular Scan]   Technology: LTE (7)
[Cellular Scan] ========================================
[Cellular Scan] Attempting connection...
[Cellular Scan] Sending: AT+COPS=1,2,"311480"
[Cellular Scan] Response: OK (took 2453ms)
[Cellular Scan] Testing signal strength...
[Cellular Scan] Sending: AT+CSQ
[Cellular Scan] Response: +CSQ: 16,99
[Cellular Scan] Signal test results for Verizon Wireless:
[Cellular Scan]   CSQ: 16
[Cellular Scan]   RSSI: -81 dBm
[Cellular Scan]   BER: 99
[Cellular Scan]   Signal Quality: Good (16/31)
[Cellular Scan]   Test Result: SUCCESS

[... similar for other carriers ...]

[Cellular Scan] =======================================
[Cellular Scan] SCAN RESULTS SUMMARY
[Cellular Scan] =======================================
[Cellular Scan] Total carriers found: 6
[Cellular Scan] Valid carriers: 4, Empty entries: 2

Idx | Name              | MCCMNC  | Status     | Tech | CSQ | RSSI     | Quality
----|-------------------|---------|------------|------|-----|----------|------------
1   | Verizon Wireless  | 311480  | Current    | LTE  | 16  | -81 dBm  | Good
2   | 313 100           | 313100  | Forbidden  | LTE  | 18  | -77 dBm  | Good
3   | T-Mobile          | 310260  | Available  | LTE  | 16  | -81 dBm  | Good
4   | AT&T              | 310410  | Available  | LTE  | 16  | -81 dBm  | Good
5   | (empty)           | -       | -          | -    | -   | -        | -
6   | (empty)           | -       | -          | -    | -   | -        | -

[Cellular Scan] Best signal: 313 100 with CSQ=18, but status is FORBIDDEN
[Cellular Scan] SELECTED: Verizon Wireless (311480) with CSQ=16 (-81 dBm)
[Cellular Scan] =======================================
```

---

## Benefits of Enhanced Logging

1. **Debugging**: Clear visibility into each step of the scan process
2. **Analysis**: Can identify why certain carriers weren't selected
3. **Performance**: Can see connection and test timing for each carrier
4. **Quality**: Signal quality assessment helps understand coverage
5. **Troubleshooting**: Can identify parsing issues with empty entries

---

## Implementation Priority

1. **HIGH**: Add signal strength details (CSQ, RSSI, quality)
2. **HIGH**: Add carrier information (name, MCCMNC, status)
3. **HIGH**: Add summary table at end of scan
4. **MEDIUM**: Add timing information for each operation
5. **LOW**: Add verbose mode for even more detailed logging

---

## Conclusion

The current logging is insufficient for proper debugging and analysis of the cellular carrier selection process. Implementing these enhanced logging functions will provide complete visibility into the scan process, making it easier to identify issues and understand carrier selection decisions.

---

**Document Version**: 1.0
**Date**: 2025-11-22
**Time**: 12:35
**Next Step**: Implement enhanced logging functions in cellular_man.c