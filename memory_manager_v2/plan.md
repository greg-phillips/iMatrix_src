**Sensor Storage & Upload System**

**1) Purpose & Scope**

Design a simple, memory-efficient, thread-safe sensor data store for two
targets:

* **STM32** (RAM-only, ~32 KB budget for
  data + metadata)
* **Linux on i.MX6** (RAM first; overflow +
  persistence to disk)

Stores **hundreds of sensors** , each logging **32-bit unsigned values**
as:

* **Time-Series** : value-only samples
* **Event-Driven** : value + **64-bit** timestamp
  (UTC ms when available, else monotonic ms).

   There is **no explicit flag** indicating UTC vs monotonic; consumers
   infer from the value domain.
**KISS** is non-negotiable: minimal data structures, predictable behavior, easy
to reason about.

STM32 systems will have up to ~100 sensors, Linux up to
~2048, and sample rates ~1-60 seconds. Split between event and timeseries is application-dependent
and should not be a constraint of the system.

---

**2) High-Level Behavior*** **Per-sensor store** : Each sensor has its **own
  sector chain** (ring) in RAM; on Linux, sectors also roll to **disk**
  when RAM usage crosses a threshold.
* **Sectors** are fixed-size blocks allocated
  from a **common pool** per platform:

  * STM32 RAM sector: **256 B**
    proposed (payload ≈ 244 B if 12 B header).
  * Linux RAM sector: **4 KB**
    preferred.
  * Linux disk sector: **64 KB**
    preferred.
* **Autogrow by sectors** : When the current sector fills,
  auto-assign a new sector.
* **Upload interplay** : Uploader drains “unsent”
  records, which become **pending** ; when cloud acknowledges, uploader
  calls **erase-all-pending** to free space.
* **Full policies** :
* STM32: at 100% RAM and only **pending**
  remains, **drop new writes** (acceptable).
* Linux: when **RAM ≥ 80%** , move
  all data to **disk** until consumer starts to use erase pending calls.
  At that time when the last on disk records have been consumed allocate
  new space back in the ram araea.When **disk quota hit** , **drop
  oldest unsent** sectors.
* **Shutdown** : Linux attempts to flush to disk
  (≥ 60 s budget). Partial writes are tolerated; invalid CRC sectors ignored
  on restart.


Should sector sizes be runtime-configurable with these as defaults?

---

**3) Record Formats (packed,
little-endian in memory; uploader handles byte order)**

* **Time-Series record** : uint32_t value (4 B).
* **Event record** :

·
struct EventRecord { uint32_t value; uint64_t ts_ms; }; // 12 B

*Note* : No extra flag; ts_ms itself conveys UTC
vs monotonic by value range/policy.

4-byte alignment is acceptable (event records are 12 B, naturally
aligned)? No need for timestamp origin ID or clock seq to disambiguate reboots?

---

**4) Sector Layouts (RAM & Disk)**

**Design goal** : tiny headers, CRC at sector level; entries are tightly packed.

**4.1 Header choice**

* **(ultra-compact)** : **12 B** total header —
  requires bit-packing.
* **STM32 256 B** : payload = **240 B** (if 16B
  header) ⇒ **TS: 60 rec/sector** , **EVT: 20 rec/sector** .

   (If you **must** keep 12 B header: payload = **244 B** , TS: 61, EVT:
   20.)

  * **Linux RAM 4 KB** : payload ≈ 4080 B ⇒ TS: 1020, EVT:
    340.
  * **Linux Disk 64 KB** : payload ≈ 65520 B ⇒ TS: 16380,
    EVT: 5460.
---

**5) Per-Sensor State (in RAM)**

Minimal ring-buffer metadata; all counters are uint32_t unless noted:

typedef struct {

uint32_t sensor_id;

uint8_t  type;            // 1=TS, 2=EVT

Mutex    lock;            // provided by iMatrix

// sector list (RAM): intrusive singly-linked list or index ring

Sector  *head;            // sector containing oldest valid
record

Sector  *tail;            // current write sector (OPEN)

// logical cursors within the concatenated stream:

uint64_t rec_head_idx;    // first
valid record index (oldest)

uint64_t rec_pending_idx; // first PENDING record index (>= head)

uint64_t rec_tail_idx;    //
one-past-last written record

// tallies

uint64_t total_written;   //
monotonic counter since boot

uint64_t total_erased;    //
includes pending-erase commits

uint64_t total_pending;   //
convenience mirror: rec_tail - rec_pending

// Linux-only disk handles (nullable on STM32):

int      fd_data;         // append-only sector file
(preallocated ring optional)

int      fd_meta;         // small metadata file for cursors
(atomic replace)

uint64_t disk_bytes_max;  //
per-sensor quota; or shared pool

} SensorStore;

* **Cursors** define three regions:

   [head ..
   pending) = **unsent** ; [pending .. tail) = **pending** ; tail .. = **empty** .
shared pool based on demand.

---

**6) Allocation & Pools**

* **RAM sector pool** (platform-specific size).
  * STM32: with 100 sensors × 256 B
    = **25.6 KB** if each holds at least 1 sector. Leaves ~6.4 KB for
    metadata/overhead ⇒ feasible.
  * Linux: pool sized to available
    RAM; manager monitors **80%** threshold.
* **Disk sector pool** (Linux): preallocate or
  grow-on-demand up to quota; use **aligned 64 KB writes** .

Expected Linux RAM budget 64KB for the pool and disk quota 256 MB. No
need to pre-allocate.

---

**7) Concurrency & Locks**

* **One mutex per SensorStore** ; any API that reads/writes store
  **must lock** it.
* Pool operations (allocate/free
  sector) protected by a **pool mutex** .
* Uploader reads under lock; long
  transfers do **not** hold the lock—records are copied out; then
  uploader marks them pending using a light call.

Single uploader thread/process, multi thread saving of sensor data.

---

**8) Upload & Pending Semantics**

* **Read for upload** yields records from [head ..
  pending) (unsent region).
* Immediately after a batch is
  successfully transmitted, uploader calls **mark_pending(n)** (implicit
  in API #8 consumption), advancing rec_pending_idx by n records.
* After cloud **ack** , uploader
  calls **erase_all_pending()** (API #9), which moves rec_head_idx =
  rec_pending_idx and physically trims sectors from the front.
* **STM32 @ 100% full** : if **only pending remains** ,
  **drop new writes** until pending is erased (explicitly allowed).
* **Linux disk full** : **drop oldest unsent**
  sectors (advance rec_head_idx sector-by-sector) to make room.

Each sensor can have one batch of data pending successful POST/PUT/GRPC
call.) No max pending window size?

---

**9) Thresholds & Policies**

* **RAM high-water (Linux)** : start disk flushing at **≥ 80%**
  RAM pool in use; continue until last** ** on disk** ** erase then
  return to RAM
* **Disk atomicity** : each **64 KB sector write**
  is **atomic** at file-system level via:

   pwrite(fd, buf,
   64KB, aligned_offset); fsync(fd); sector includes CRC32C; invalid sectors ignored at mount/restart.

  * **Disk metadata atomicity** : persist cursors by writing a
    temp meta file and rename() + fsync() dir (classic atomic replace).
rely on rename() + fsync() durability semantics.

---

**10) Management Routine (every ~100 ms)**

* Seal current sector if full;
  allocate a new sector as needed.
* On Linux:
  * Check RAM pool usage; if ≥ 80%,
    schedule flush of SEALED sectors to disk.
  * If **shutdown flag true** ,
    aggressively flush OPEN sectors (force-seal) until time budget expires.
  * Enforce disk quota by trimming **oldest
    unsent** sectors.
* Service a small **work queue** :
  disk writes, CRC calc (optional deferred), metadata updates.

Can use a worker thread for disk flush, shutdown system needs a helper function
to know when all data has been flushed to disk. Data sources will stop adding
data during shutdown phase.

---

**11) Startup & Recovery**

* **STM32** : start with empty pools and
  zeroed cursors.
* **Linux** : on boot, scan the sensor’s data
  file **by sector** : load only **valid CRC** sectors into an in-RAM
  index; rebuild cursors (fast because sectors are large). Meta file (if
  present) is used first; if absent or invalid, fall back to scan.

boot-time scan takes as long as it takes. No time budget.

---

**12) Errors & Backpressure**

* **Out of RAM sectors** :
  * STM32: drop newest writes when
    only pending remains; else recycle by erasing oldest **unsent** to
    preserve newest.
  * Linux: trigger disk flush; if
    disk also full, drop oldest **unsent** (policy already defined).
* **Write failures** (disk): mark sector as DIRTY,
  retry next tick; if persistent, trip a health flag.
* **CRC mismatch** on read: drop that sector and
  continue.

STM32 ever recycle **unsent** (not pending) records. If none drop new
data.

---

**13) Public C API (thread-safe)**

// types

typedef struct SensorStore
SensorStore; // opaque

typedef enum { SENSOR_TS = 1,
SENSOR_EVT = 2 } SensorType;

// 1) Initialize the pool(s) and
manager (platform-specific caps & disk path on Linux)

int ss_init_system(const SsInitCfg
*cfg); // returns 0 on success

// 2) Initialize a data store for a
sensor

int ss_sensor_init(uint32_t sensor_id,
SensorType type, SensorStore **out);

// 3) Add time-series reading (value)

int ss_ts_add(SensorStore *s, uint32_t
value);

// 4) Add event reading (value, ts_ms)

int ss_evt_add(SensorStore *s,
uint32_t value, uint64_t ts_ms);

// 5) Get total records currently
retained for this sensor

int ss_get_total_records(const
SensorStore *s, uint64_t *out_total_current);

// 6) Get count of currently stored
UNSENT samples (= total_current - pending_count)

int ss_get_unsent_count(const
SensorStore *s, uint64_t *out_unsent);

// 7) Read record by offset from START
(diagnostics; does not change cursors)

int ss_diag_read_at(const SensorStore
*s, uint64_t offset, void *out_rec /* TS: uint32_t*; EVT: EventRecord* */);

// 8) Consume next UNSENT record
(moves "read" boundary to PENDING for one record or a small batch)

int ss_consume_next(SensorStore *s,
void *out_rec);

// (optional helper) Consume up to N
UNSENT records into caller buffer (better throughput)

int ss_consume_batch(SensorStore *s,
void *out_buf, uint32_t max_records, uint32_t *out_n);

// 9) Erase all PENDING records
(advance head = pending; free whole sectors where applicable)

int ss_erase_all_pending(SensorStore
*s);

// Periodic manager (call ~every 100
ms)

void ss_manager_tick(void);

// Helper that platform sets/clears
(e.g., on SIGTERM or powerfail notice)

void ss_set_shutdown(bool
in_progress);

**Return codes** : 0=OK, -ENOSPC, -EINVAL, -EIO, -EAGAIN (try later), etc.

---

**14) Disk Organization (Linux)**

·
Sectors written to disk must be stored in sub directories based on
source. Three sources exist. Host, Applicaton and CAN.

·The same sensor id may exist in the three sources.

* **Per-sensor files** (KISS):
  * sensor_<id>.dat — append-only **64 KB sectors** ,
    CRC’d.
  * sensor_<id>.meta — cursors (rec_head_idx, rec_pending_idx, rec_tail_idx) + small hash; write-to-temp
    then rename(); fsync() directory.
  * sensor id, 0 filled 10 digits.
* **Atomicity** : A single sector is validated by
  its CRC; partial writes are discarded on boot.
* **Quota enforcement** : If size > quota, drop **oldest unsent sectors**
  until under quota; never truncate through pending without policy allowing
  it.

One file per sensor.

---

**15) Integrity**

* **Checksum** : **CRC32C** (Castagnoli).
* **All disk writes atomic at sector
  granularity** ; meta file writes are atomic via rename().
* **Partial flush tolerated** during aborted shutdown.

use plain CRC32?

---

**16) Resource & Performance Targets
(initial)**

* **STM32** : ≤ 32 KB RAM (data + metadata);
  per-call add/write ≤ 20 µs at 100 MHz (guideline).
* **Linux** : add/write ≤ 5 µs typical; disk
  flush sustained at sensor aggregate ≥ your max ingress rate.

No ingress rate target and cloud upload batch size are system-dependent and
pre-planned.

---

**17) Diagnostics**

* ss_diag_read_at() for human-driven inspection.
* Optional ss_dump_stats(sensor_id) for counts, sector usage, and
  cursor positions.

System has a powerful CLI/debug shell. Using of iMatrix help print functions will be used.

---

**18) Configuration Knobs**

* Sector sizes (RAM/Disk), RAM pool
  size, disk quota, RAM high/low watermarks, flush batch size, force-seal
  interval, CRC on/off (should stay **on** for disk).
* All in a small SsInitCfg struct.

Ship the above as defaults?

---

**19) Edge Cases & Notes**

* **Clock changes** : Event timestamps are stored
  raw; interpretation is delegated to the consumer (no flag).
* **No compression; encryption
  handled upstream** .
* **Byte order** : uploader normalizes; storage
  stays native.
* **Multithreaded** : all APIs acquire the per-sensor
  mutex; background tasks use internal worker or the 100 ms tick.

---

**20) Example Capacity Math (helpful
sanity check)**

* **STM32** (256 B/sector, 16 B header):

  * TS: **60 rec/sector** ⇒ for 100 sensors with 1 sector each ⇒ 6,000 rec retained minimum.
  * EVT: **20 rec/sector** .
* **Linux RAM** (4 KB/sector): TS **1020** ,
  EVT **340** per sector.
* **Linux Disk** (64 KB/sector): TS **16,380** ,
  EVT **5,460** per sector.

   With 1 GB quota per sensor, that’s **~16,000 TS sectors** ⇒ **~262 M TS
   records** max per sensor (upper bound; real will be lower due to churn).
STM32 and Linux needs at least 1 sector per sensor on start up.

---

**21) Implementation Notes (kept simple)**

* **Memory manager** uses free-list arrays, not
  malloc per record.
* **Writing** : append within the current
  sector; when w_off + rec_sz > payload, **seal** and allocate next.
* **Erasing** : when head sector becomes empty
  (after advancing head to pending), free entire sector to the pool; do not
  shift bytes within a sector.
* **Disk flush** (Linux): write sealed sectors
  as-is; OPEN sectors can be force-sealed after a timeout to bound RAM
  usage.

---

**22) Create an exhaustive unit test
suite**

* **Create tests as the development proceeds
  to ensure each step has been completed correctly**
* **Create a full system test suite,
  including all corner cases**
* **Simulate sensor and event record
  generation and consumption**

Think hard and review this specification and create an
implementation plan with extensive and detailed todo list
