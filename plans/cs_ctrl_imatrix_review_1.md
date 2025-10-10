
**ROLE:** You are the Lead Architect and an expert embedded software engineer specializing in **C development** for bare-metal and cross-platform systems. Your task is to perform an exhaustive architectural analysis of the iMatrix sensor collection's memory management system.

**CORE GOAL:** Create a **comprehensive technical architecture document** detailing the memory management helper functions and their entire system usage, with a specific focus on the `data_store_info_t` structure.

**OUTPUT FORMAT:** The final deliverable must be a single, well-structured Markdown document named `docs/imatrix_memory_architecture.md`.

---

### Phase 1: Exhaustive Codebase Analysis

**INSTRUCTION:** Perform a deep, cross-directory analysis of the following relevant codebases accessible within the workspace:
1.  `~/iMatrix/iMatrix_Client/iMatrix`
2.  `~/iMatrix/iMatrix_Client/Fleet-Connect-1`

**ACTION:**
1.  **Identify and Analyze:** Locate all memory management helper functions defined or declared within the `iMatrix/cs_ctrl` directory (or wherever sensor control helpers are located).
2.  **Trace `data_store_info_t`:** Identify the definition of the `data_store_info_t` structure (likely in `~/iMatrix/iMatrix_Client/iMatrix/common.h` or an adjacent header) and perform a system-wide search for every source file (`*.c`) that references a variable of this type.

### Phase 2: Documentation Generation

**ACTION:** Generate the final document, `docs/cs_ctrl_mm_architecture.md`, structured as follows:

**1. iMatrix Memory Management Helper Functions**
* Provide a list of all identified helper functions.
* For each function, include:
    * **Full C Signature** (return type, name, and parameters).
    * **Purpose/Description** (In-depth explanation of its role in memory management/sensor collection).
    * **Call Tracing Summary** (A brief summary of where and why this function is called across the entire system).

**2. `data_store_info_t` Structure Usage Deep Dive**
* Provide the full C definition of the `data_store_info_t` structure.
* Present a comprehensive table of all usage locations:

| Source File (Relative Path) | Function Name | Variable Name/Context | Type of Access (Read/Write/Allocation) |
| :--- | :--- | :--- | :--- |
| e.g., iMatrix/data_collector.c | data_collection_loop | g_store_info | Read and Write to internal fields |
| ... | ... | ... | ... |

---

**FINAL DELIVERABLES CHECKLIST:**
* [ ] The file `docs/cs_ctrl_mm_architecture.md` has been created.
* [ ] The document details all memory management functions, their signatures, and uses.
* [ ] The document includes an exhaustive trace of all uses of `data_store_info_t` structure variables, as specified in the table format above.