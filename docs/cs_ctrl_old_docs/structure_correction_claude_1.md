**CONTEXT and ENVIRONMENT:** You are operating as an AI assistant within the **Cursor** IDE environment, with full access to the project file system. Your response will be a structured plan and a set of instructions for code modification.

**ROLE:** You are the **Senior Embedded System Architect** and an expert C developer specializing in **STM32 bare-metal** and **Embedded iMX6 Linux** installations. Your task is to perform a critical data structure refactoring, focusing on efficiency and correct design principles for embedded systems.

**CORE GOAL: Data Structure Refactoring for `per_source_disk_state_s`**

The current nesting of the data structure `per_source_disk_state_s` is logically incorrect and leads to memory inefficiency. You must move this structure to the correct, higher-level context to align with the system's architecture. This move must be tracked meticulously.

---
### Phase 1: Comprehensive System Analysis

**INSTRUCTION:** Perform a complete analysis of the core data structures and their usage.

| Component | Path/File | Purpose |
| :--- | :--- | :--- |
| **Source Code (Usage)** | `iMatrix/cs_ctrl` (Directory) | Directory containing control-sensor logic using the structures. |
| **Header (Definitions)** | `iMatrix/storage.h` | Likely location of `imx_mmcb` and related structs. |
| **Header (Definitions)** | `iMatrix/common.h` | General project definitions. |
| **Header (Definitions)** | `iMatrix/device/icb_def.h` | Location of `icb_data_` (the target parent structure). |
| **Background (Context)** | `iMatrix/docs/MM2_IMPLEMENTATION_GUIDE.md` | Context for memory/data flow. |
| **Background (Context)** | `iMatrix/MM2_TECHNICAL_DOCUMENTATION.md` | Context for overall system design. |

**CURRENT ISSUE DIAGNOSIS:**
* The target structure is: `struct per_source_disk_state_s`
* It is currently incorrectly nested inside: `typedef struct imx_mmcb`
* Which is incorrectly nested inside: `typedef struct control_sensor_data` (A per-sensor structure).
* The correct, logical owner for this state is the data block/device context: `typedef struct icb_data_`.

---
### Phase 2: Refactoring Plan and Documentation

**RESOLUTION STEPS:**

1.  **RELOCATION:** Move the definition of `struct per_source_disk_state_s` and nest it directly inside the definition of **`struct icb_data_`** (likely located in `iMatrix/device/icb_def.h`).
2.  **REMOVAL:** Completely remove all references and the definition of `struct per_source_disk_state_s` from `typedef struct imx_mmcb` and `typedef struct control_sensor_data`.
3.  **USAGE TRACKING:** Identify every single location in the codebase where an element of the relocated `per_source_disk_state_s` is accessed.

**DELIVERABLE:** Create a detailed migration document, **`fix_per_source_issue_1.md`**, that I can use to commit the changes.

The document must contain:

* **Mapping Summary:** A brief table showing the old access path vs. the new access path (e.g., `sensor_data->mmcb->disk_state->field` $\rightarrow$ `icb_data->disk_state->field`).
* **Detailed To-Do List:** A sequential, file-by-file list of necessary code edits. For each file:
    * State the file path.
    * Identify the line(s) or function where the access path needs to be updated.
    * Provide the **exact line of C code** (old vs. new) for the most complex path replacements.

---
### Phase 3: Validation

**INSTRUCTION:** Wait for user confirmation. I will perform a clean compile on the target embedded cross-compiler after your edits.

**FINAL CHECK:** Ensure your plan results in the successful relocation of the structure and the correction of all usage points across the codebase.