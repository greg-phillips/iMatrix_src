Here's an improved prompt optimized for Claude Code in Cursor:

---

# Embedded Systems Data Structure Refactoring Task

## Your Role
You are a senior embedded systems architect specializing in STM32 processors and Embedded iMX6 Linux installations. Your task is to analyze and fix a data structure architecture issue.

## Project Context

### Codebase Structure
First, read and analyze these files in order:
1. `iMatrix/common.h` - Common definitions
2. `iMatrix/device/icb_def.h` - iMatrix Control Block definitions
3. `iMatrix/storage.h` - Storage structures
4. `iMatrix/cs_ctrl/` - All source files in this directory
5. `iMatrix/docs/MM2_IMPLEMENTATION_GUIDE.md` - Implementation background
6. `iMatrix/docs/MM2_TECHNICAL_DOCUMENTATION.md` - Technical background

### Current (Incorrect) Architecture
```
iMatrix_Control_Block_t
  ├─ control_sensor_data_t[] i_cd  // sensor array
  ├─ control_sensor_data_t[] i_sd  // sensor array
  └─ control_sensor_data_t[] i_vd  // sensor array
       └─ imx_mmcb_t mmcb
            └─ per_source_disk_state_s[] // ❌ INCORRECTLY NESTED HERE
```

### Target (Correct) Architecture
```
iMatrix_Control_Block_t
  ├─ control_sensor_data_t[] i_cd
  ├─ control_sensor_data_t[] i_sd
  ├─ control_sensor_data_t[] i_vd
  │    └─ imx_mmcb_t mmcb (no disk state here)
  └─ per_source_disk_state_s[] // ✅ SHOULD BE HERE in icb_data_
```

## The Problem
The `per_source_disk_state_s` structure is currently nested inside `imx_mmcb_t`, which is inside `control_sensor_data_t`. This is incorrect because disk state is per-source, not per-sensor. It should be an array directly inside `struct icb_data_` (part of `iMatrix_Control_Block_t`).

## Your Task - Step by Step

### Phase 1: Analysis (Do This First)
1. **Map the current structure hierarchy** - Document exactly where `per_source_disk_state_s` is defined and nested
2. **Find all references** - Search the entire codebase for:
   - Direct references to `per_source_disk_state_s`
   - Access patterns like `sensor->mmcb.disk_state[x]`
   - Any initialization or allocation code
   - Any pointer dereferencing chains that reach this structure
3. **Identify dependencies** - Note which functions/modules depend on the current nesting

### Phase 2: Create Fix Plan
Create a markdown document: `iMatrix/docs/fix_per_source_issue_1.md` with:

```markdown
# Per-Source Disk State Refactoring Plan

## Current Structure Analysis
[Your findings from Phase 1]

## Files to Modify
[Numbered list with file paths]

## Detailed Changes Required

### 1. Structure Definitions
- [ ] File: [path]
  - Line: [number]
  - Change: [specific edit]
  - Rationale: [why]

### 2. Structure Access Pattern Changes
- [ ] File: [path]
  - Function: [name]
  - Line: [number]
  - Old: `sensor->mmcb.disk_state[idx]`
  - New: `icb->disk_state[idx]`
  - Impact: [describe]

[Continue for all locations...]

### 3. Initialization/Cleanup Changes
[Document any init/destroy patterns that need updating]

## Testing Checklist
- [ ] Verify structure sizes are correct
- [ ] Check alignment requirements
- [ ] Validate pointer arithmetic
- [ ] Confirm no dangling references

## Compilation Validation
Cross-compiler target: [specify from build config]
```

### Phase 3: Implementation Guidance
After creating the plan document:
1. Do NOT make changes yet - wait for human approval of the plan
2. Estimate the risk level of each change (Low/Medium/High)
3. Suggest any temporary compatibility shims if needed
4. Note any potential runtime issues (pointer arithmetic, memory alignment, etc.)

## Success Criteria
- ✅ Complete analysis document created
- ✅ All references identified with line numbers
- ✅ Clear before/after code snippets for each change
- ✅ Zero ambiguity - I should be able to execute the plan mechanically
- ✅ The plan, when executed, results in a clean cross-compile

## Important Constraints
- This is embedded systems code - be mindful of memory layout, alignment, and packing
- This likely affects memory-mapped hardware registers - structure changes may break timing
- Consider cache line boundaries on iMX6
- Document any ABI implications

## Output Format
Start by confirming you've read all the specified files, then create the `fix_per_source_issue_1.md` document. Use clear section headers, checkboxes for actionable items, and code blocks with diff-style formatting where helpful.

---

**Begin by reading the codebase files listed above, then proceed with Phase 1.**