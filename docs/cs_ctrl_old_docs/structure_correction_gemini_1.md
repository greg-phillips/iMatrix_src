**CONTEXT and ENVIRONMENT:** You are operating as an AI assistant within the **Cursor** IDE environment, with full and immediate access to the entire project file system. Your output must be a self-contained, actionable plan for refactoring.

**ROLE:** You are a **Principal Embedded Systems Architect**, specializing in STM32 and i.MX 6 Linux development. Your immediate focus is on **data structure optimization and refactoring** for the iMatrix client system to resolve a critical structural inefficiency.

**CORE TASK:** Rectify an incorrect nesting of the `per_source_disk_state_s` data structure within the iMatrix control flow.

-----

### Phase 0: Required Review and Analysis

**INSTRUCTION:** Perform a thorough analysis of the following files to establish the current data structure layout and usage patterns.

| File/Document | Path | Focus Area |
| :--- | :--- | :--- |
| **Control Block Logic** | `iMatrix/cs_ctrl` | Core logic using `iMatrix_Control_Block_t`. |
| **Headers** | `iMatrix/storage.h` | Storage-related data structures. |
| **Headers** | `iMatrix/common.h` | Global definitions. |
| **Headers** | `iMatrix/device/icb_def.h` | Definitions for `iMatrix_Control_Block_t` and related structures. **(CRITICAL)** |
| **Background** | `iMatrix/docs/MM2_IMPLEMENTATION_GUIDE.md` | Context on the memory manager's expected integration. |
| **Background** | `iMatrix/MM2_TECHNICAL_DOCUMENTATION.md` | Technical details that might influence pointer sizing/alignment. |

**CORE ISSUE IDENTIFICATION:**
The structure `per_source_disk_state_s` is currently **incorrectly nested** inside `imx_mmcb_t`, which itself is nested inside `control_sensor_data_t`. This results in **data duplication** because the array of disk states should be a single, global array within the primary control block, not duplicated for every sensor data entry.

**DESIRED STRUCTURAL CHANGE (The Fix):**

1.  **Removal:** Remove `per_source_disk_state_s` (or a pointer/array reference to it) from inside `imx_mmcb_t` / `control_sensor_data_t`.
2.  **Relocation:** Move the structure `per_source_disk_state_s` (or an array of this structure) to be a direct member **inside** the top-level control block structure, `icb_data_` (which is typically typedef'd to `iMatrix_Control_Block_t`). The array size should be determined by constants found in the reviewed headers (e.g., max number of disk sources).

### Phase 1: Migration Plan Generation

**INSTRUCTION:** Create a detailed document outlining every single change required to achieve the desired structural state and clean compilation.

**DELIVERABLE:** A new file, `fix_per_source_issue_1.md`, structured as follows:

```markdown
# Data Structure Refactoring: iMatrix Control Block Disk State Issue

## 1. Summary of Structural Change (CRITICAL)
* **Old Path:** `iMatrix_Control_Block_t` -> `control_sensor_data_t[]` -> `imx_mmcb_t` -> `per_source_disk_state_s` (Nested incorrectly).
* **New Path:** `iMatrix_Control_Block_t` (or `icb_data_`) -> `per_source_disk_state_s[]` (Directly contained).
* **Affected Files:** [List the specific header files where the structures are defined]

## 2. Global Code Impact Analysis
Provide a precise list of every file and line range where the old, incorrect structure member (`i_cd->mmcb.disk_state...` or similar) is accessed. This is the **most crucial part** of the analysis.

## 3. Step-by-Step To-Do List (Atomic Changes)
* [ ] **Structure Definition Update (icb_def.h):** Modify `icb_data_` definition to add the correct array of `per_source_disk_state_s`.
* [ ] **Structure Definition Cleanup (icb_def.h/storage.h):** Remove the incorrect nesting/member from `imx_mmcb_t` and/or `control_sensor_data_t`.
* [ ] **Code Fix 1 (File X):** Locate and update usage of the old structure member to the new path (`icb->disk_states[i]...`). *Provide the old code snippet and the exact replacement snippet.*
* [ ] **Code Fix 2 (File Y):** Locate and update usage...
* *...continue with a distinct item for every source file modification identified in Section 2...*
* [ ] **Review/Refactor:** Check initialization routines (e.g., `init_control_block`) to ensure the new `disk_state` array is correctly zeroed/initialized.

## 4. Final Verification
* [ ] Ensure all old references are removed.
* [ ] Check for compiler warnings/errors related to incomplete types or misaligned structures.

```

**RESULT CHECK:** Your final state must ensure a clean project state, ready for the target embedded cross-compiler. I will perform the final clean compile after receiving your plan.