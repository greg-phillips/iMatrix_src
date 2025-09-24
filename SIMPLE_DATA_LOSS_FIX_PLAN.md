# SIMPLE RESOLUTION PLAN: Fix Data Loss Bug

**Approach:** Direct fix, no staging, no over-engineering
**Goal:** Stop data destruction, fix the core issue, move on
**Timeline:** Single implementation addressing all issues

---

## THE CORE PROBLEM

**Current Code:**
```c
// Response handler erases ALL pending data regardless of what was sent
erase_tsd_evt_pending_data(csb, csd, no_items);  // WRONG: Erases everything
```

**What Happens:**
- Read 1000 samples, send 100, erase ALL 1000
- 900 samples permanently lost per "successful" upload

---

## THE SIMPLE FIX

### **1. Track What Goes Into Each Packet**

**Add to imatrix_upload.c:**
```c
// Simple tracking of what we actually put in the packet
static struct {
    uint16_t entry_counts[IMX_NO_PERIPHERAL_TYPES][MAX_ENTRIES_PER_TYPE];
    bool in_use;
} packet_contents;
```

### **2. Record During Packet Building**

**Modify packet building loop:**
```c
// Clear tracking at start
memset(&packet_contents, 0, sizeof(packet_contents));
packet_contents.in_use = true;

// During packet building, record what we add
for ( uint16_t j = 0; j < no_samples; j++)
{
    read_tsd_evt(csb, csd, i, (uint32_t*)&event_sample);
    add_to_packet(event_sample);
    packet_contents.entry_counts[type][i]++;  // Track this entry
}
```

### **3. Erase Only What Was Sent**

**Replace response handler:**
```c
static void _imatrix_upload_response_hdl(message_t *recv)
{
    bool result = (recv != NULL);
    if (result && (MSG_CLASS(recv->coap.header.mode.udp.code) != 2)) {
        result = false;
    }

    if (result && packet_contents.in_use)
    {
        // SUCCESS: Erase only what was actually sent
        for (type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++)
        {
            imx_set_csb_vars(type, &csb, &csd, &no_items, &device_updates);
            for (uint16_t i = 0; i < no_items; i++)
            {
                if (packet_contents.entry_counts[type][i] > 0)
                {
                    // Erase exactly this many samples from this entry
                    erase_specific_samples(csb, csd, i, packet_contents.entry_counts[type][i]);
                }
            }
        }
    }
    else
    {
        // FAILURE: Revert read pointers properly
        revert_packet_reads(&packet_contents);
    }

    packet_contents.in_use = false;
    // ... rest of existing logic
}
```

### **4. New Erasure Function**

**Add to memory_manager_tsd_evt.c:**
```c
void erase_specific_samples(imx_control_sensor_block_t *csb, control_sensor_data_t *csd,
                           uint16_t entry, uint16_t count)
{
    for (uint16_t i = 0; i < count; i++)
    {
        // Erase exactly one sample
        if (csd[entry].no_pending > 0)
        {
            // Advance pointer and decrement counters
            if (csb[entry].sample_rate == 0) {
                csd[entry].ds.start_index += EVT_RECORD_SIZE;
            } else {
                csd[entry].ds.start_index += TSD_RECORD_SIZE;
            }
            csd[entry].no_pending--;
            csd[entry].no_samples--;

            // Handle sector management if needed
            manage_sector_transitions(csb, csd, entry);
        }
    }
}
```

### **5. Proper Revert Function**

**Add to memory_manager_tsd_evt.c:**
```c
void revert_packet_reads(packet_contents_t *contents)
{
    for (type = IMX_CONTROLS; type < IMX_NO_PERIPHERAL_TYPES; type++)
    {
        imx_set_csb_vars(type, &csb, &csd, &no_items, NULL);
        for (uint16_t i = 0; i < no_items; i++)
        {
            if (contents->entry_counts[type][i] > 0)
            {
                // Revert the read operation by restoring pointers
                uint16_t samples_read = contents->entry_counts[type][i];
                uint16_t record_size = (csb[i].sample_rate == 0) ? EVT_RECORD_SIZE : TSD_RECORD_SIZE;

                // Move read pointer back
                csd[i].ds.start_index -= (samples_read * record_size);
                csd[i].no_pending -= samples_read;

                // Handle sector boundary corrections if needed
                correct_sector_boundaries(csd, i);
            }
        }
    }
}
```

---

## IMPLEMENTATION STEPS

### **Step 1: Add Tracking Structure**
- Add simple packet contents tracking to imatrix_upload.c
- Initialize/clear on each packet build

### **Step 2: Modify Packet Building**
- Record each sample added to packet in tracking structure
- No other changes to packet building logic

### **Step 3: Replace Response Handler**
- Replace bulk erasure with granular erasure based on tracking
- Add proper revert logic for failures

### **Step 4: Add New Erasure Functions**
- `erase_specific_samples()` - erase exact count
- `revert_packet_reads()` - proper rollback

### **Step 5: Test and Deploy**
- Test with various packet sizes and failure scenarios
- Verify no data loss occurs
- Deploy to development environment

---

## VALIDATION

**Simple Test:**
1. Write 1000 samples to storage
2. Build packet with 100 samples
3. Simulate successful upload
4. Verify exactly 100 samples erased, 900 remain
5. Verify remaining 900 samples are accessible

**That's it. Problem solved.**

No staging, no complex monitoring, no over-engineering. Just fix the core issue: **erase exactly what was sent, nothing more, nothing less.**