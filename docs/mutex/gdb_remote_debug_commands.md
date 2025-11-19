# GDB Remote Debugging Commands for Mutex Deadlock Analysis

## Quick Reference for Remote GDB Session with MI Interface

**When system hangs on mutex deadlock, collect these data points:**

---

## 1. Connect to Target

```gdb
-exec target remote <target-ip>:1234
-exec set sysroot /opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot
```

---

## 2. Thread Information

### List All Threads
```gdb
-exec info threads
```

### Get All Thread Backtraces
```gdb
-exec thread apply all bt full
```

### Switch to Specific Thread
```gdb
-exec thread 1
-exec bt full
```

---

## 3. Mutex State Inspection

### CAN RX Mutex
```gdb
-exec print can_rx_mutex
-exec print/x can_rx_mutex.__data.__lock
-exec print/x can_rx_mutex.__data.__owner
```

### Unified Queue Mutex
```gdb
-exec print unified_queue
-exec print/x unified_queue.mutex.__data.__lock
-exec print/x unified_queue.mutex.__data.__owner
```

### Log Queue Mutex
```gdb
-exec print g_log_queue
-exec print/x g_log_queue.mutex.__data.__lock
-exec print/x g_log_queue.mutex.__data.__owner
```

### Ring Buffer Locks
```gdb
-exec print can0_ring
-exec print/x can0_ring.lock.__data.__lock
-exec print/x can0_ring.lock.__data.__owner

-exec print can1_ring
-exec print/x can1_ring.lock.__data.__lock
-exec print/x can1_ring.lock.__data.__owner

-exec print can2_ring
-exec print/x can2_ring.lock.__data.__lock
-exec print/x can2_ring.lock.__data.__owner
```

---

## 4. Ring Buffer Corruption Check

### Check Free Count Validity
```gdb
-exec print can0_ring.free_count
-exec print can0_ring.max_size
-exec print can0_ring.free_count <= can0_ring.max_size

-exec print can1_ring.free_count
-exec print can1_ring.max_size
-exec print can1_ring.free_count <= can1_ring.max_size

-exec print can2_ring.free_count
-exec print can2_ring.max_size
-exec print can2_ring.free_count <= can2_ring.max_size
```

**If any free_count > max_size:** Memory corruption detected!

---

## 5. Register and Memory State

### Current Thread Registers
```gdb
-exec info registers
-exec print/x $pc
-exec print/x $sp
-exec print/x $lr
```

### Memory Around PC (Instruction Pointer)
```gdb
-exec x/20i $pc-32
```

### Memory Around SP (Stack Pointer)
```gdb
-exec x/64xw $sp
```

---

## 6. Thread-Specific Analysis

### For Each Thread Showing futex_wait or __syscall_cp_c

```gdb
-exec thread 1
-exec bt full
-exec info locals

-exec thread 2
-exec bt full
-exec info locals

-exec thread 3
-exec bt full
-exec info locals

-exec thread 4
-exec bt full
-exec info locals

-exec thread 5
-exec bt full
-exec info locals
```

---

## 7. Identify Deadlocked Thread

Look for thread with backtrace showing:
- `__syscall_cp_c`
- `futex_wait`
- `pthread_mutex_lock`

Example:
```
Thread 1 (LWP 1234):
#0  0xb6f12345 in __syscall_cp_c () from /lib/ld-musl-armhf.so.1
#1  0xb6f12456 in pthread_mutex_lock () from /lib/ld-musl-armhf.so.1
#2  0x000a1234 in async_log_flush () at async_log_queue.c:264
#3  0x00012345 in do_everything () at do_everything.c:262
```

This tells you: Main thread stuck trying to lock log_queue.mutex

---

## 8. Determine Which Mutex is Corrupted

### Check Mutex Lock Value

Normal unlocked mutex:
```
__data.__lock = 0
__data.__owner = 0
```

Normal locked mutex:
```
__data.__lock = 1
__data.__owner = <thread-id>
```

Corrupted mutex:
```
__data.__lock = <large number or negative>
__data.__owner = <invalid thread id>
```

### Example Commands
```gdb
-exec print/x unified_queue.mutex.__data.__lock
```

If output is something like `0x41414141` or any value > 1, mutex is corrupted.

---

## 9. Complete Data Collection Script

**Copy and paste these commands one at a time in GDB:**

```gdb
-exec set logging on
-exec set logging file /tmp/deadlock_debug.log
-exec set pagination off

-exec echo ==========================================\n
-exec echo DEADLOCK DEBUG INFORMATION\n
-exec echo ==========================================\n

-exec echo \n=== THREAD OVERVIEW ===\n
-exec info threads

-exec echo \n=== ALL THREAD BACKTRACES ===\n
-exec thread apply all bt full

-exec echo \n=== CAN RX MUTEX ===\n
-exec print can_rx_mutex
-exec print/x can_rx_mutex.__data.__lock
-exec print/x can_rx_mutex.__data.__owner

-exec echo \n=== UNIFIED QUEUE MUTEX ===\n
-exec print unified_queue
-exec print/x unified_queue.mutex.__data.__lock
-exec print/x unified_queue.mutex.__data.__owner

-exec echo \n=== RING BUFFER 0 ===\n
-exec print can0_ring
-exec print/x can0_ring.lock.__data.__lock
-exec print/x can0_ring.lock.__data.__owner
-exec print can0_ring.free_count <= can0_ring.max_size

-exec echo \n=== RING BUFFER 1 ===\n
-exec print can1_ring
-exec print/x can1_ring.lock.__data.__lock
-exec print/x can1_ring.lock.__data.__owner
-exec print can1_ring.free_count <= can1_ring.max_size

-exec echo \n=== RING BUFFER 2 (Ethernet) ===\n
-exec print can2_ring
-exec print/x can2_ring.lock.__data.__lock
-exec print/x can2_ring.lock.__data.__owner
-exec print can2_ring.free_count <= can2_ring.max_size

-exec echo \n=== CURRENT THREAD REGISTERS ===\n
-exec info registers

-exec echo \n=== INSTRUCTION AT PC ===\n
-exec x/20i $pc-32

-exec echo \n=== STACK MEMORY ===\n
-exec x/64xw $sp

-exec set logging off
-exec echo \nDebug data saved to /tmp/deadlock_debug.log\n
```

---

## 10. Quick Diagnostic Checklist

When connected to hung system:

1. **Find hung thread:**
   ```gdb
   -exec info threads
   ```
   Look for thread showing stopped state

2. **Get backtrace:**
   ```gdb
   -exec thread <ID>
   -exec bt full
   ```

3. **Check which mutex it's waiting on:**
   Look at backtrace - usually shows in `pthread_mutex_lock()` call

4. **Examine that mutex:**
   ```gdb
   -exec print <mutex_name>
   -exec print/x <mutex_name>.__data.__lock
   ```

5. **Determine if corrupted:**
   - __lock should be 0 or 1
   - If __lock is anything else → CORRUPTED

---

## 11. Common Scenarios and Commands

### Scenario 1: Main Thread Hung on Log Queue

```gdb
-exec thread 1
-exec bt
# If you see async_log_flush:
-exec print g_log_queue.mutex.__data.__lock
-exec print g_log_queue.mutex.__data.__owner
-exec print g_log_queue.count
-exec print g_log_queue.head
-exec print g_log_queue.tail
```

### Scenario 2: CAN Thread Hung on Ring Buffer

```gdb
-exec thread 2
-exec bt
# If you see can_ring_buffer_alloc or can_ring_buffer_free:
-exec up
-exec print ring
-exec print/x ring->lock.__data.__lock
-exec print ring->free_count
-exec print ring->max_size
```

### Scenario 3: Multiple Threads Deadlocked

```gdb
-exec thread apply all bt
# Look for circular wait pattern:
# Thread 1 waiting on Mutex A (owned by Thread 2)
# Thread 2 waiting on Mutex B (owned by Thread 1)
```

---

## 12. Interpreting Results

### Normal Mutex State
```
can_rx_mutex = {
  __data = {
    __lock = 0,           ← Unlocked
    __owner = 0,          ← No owner
    __kind = 0,           ← Normal mutex
    ...
  }
}
```

### Locked Mutex State
```
can_rx_mutex = {
  __data = {
    __lock = 1,           ← Locked
    __owner = 1237,       ← Owner thread ID
    __kind = 0,
    ...
  }
}
```

### Corrupted Mutex State
```
can_rx_mutex = {
  __data = {
    __lock = 0x41414141, ← CORRUPTED!
    __owner = 0xdeadbeef, ← CORRUPTED!
    __kind = 99,          ← CORRUPTED!
    ...
  }
}
```

---

## 13. Copy-Paste Quick Check

**When system hangs, paste this entire block:**

```gdb
-exec info threads
-exec thread apply all bt
-exec print can_rx_mutex.__data.__lock
-exec print unified_queue.mutex.__data.__lock
-exec print can0_ring.lock.__data.__lock
-exec print can1_ring.lock.__data.__lock
-exec print can2_ring.lock.__data.__lock
-exec print can0_ring.free_count <= can0_ring.max_size
-exec print can1_ring.free_count <= can1_ring.max_size
-exec print can2_ring.free_count <= can2_ring.max_size
```

This will quickly show:
- Which threads are running/blocked
- Which mutexes are locked
- Whether any mutexes are corrupted
- Whether ring buffers have valid state

---

## Expected Outcome

**With the mutex fix:**
- System should **NOT hang**
- All mutexes should show valid state
- Ring buffers should show `free_count <= max_size` always
- No corruption detected

**If it still hangs:**
- GDB will now show complete stack traces (thanks to DebugGDB build)
- Can identify exact location of hang
- Can see all variable values
- Can determine if new issue or missed scenario

---

**Created:** 2025-11-13
**For:** Mutex deadlock debugging in Fleet-Connect-1
**Binary:** /home/greg/iMatrix/iMatrix_Client/Fleet-Connect-1/build/FC-1
