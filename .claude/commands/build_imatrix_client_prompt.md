You are generating an iMatrix development prompt from a YAML specification file.

## Task Overview

Generate a comprehensive Markdown development prompt from a structured YAML specification file. The system supports three complexity levels (simple, moderate, advanced) with features including:
- Auto-population from CLAUDE.md
- Variable substitution (advanced)
- Template includes (advanced)
- Interactive missing field prompts
- Strict validation with helpful error messages

## Usage

```
/build_imatrix_client_prompt <yaml_spec_file> [options]
```

**Arguments:**
- `<yaml_spec_file>`: Path to YAML specification file (relative to ~/iMatrix/iMatrix_Client/)

**Options** (not yet implemented, just document path for now):
- `--no-interactive`: Skip interactive prompts for missing fields
- `--no-auto-populate`: Don't auto-populate from CLAUDE.md
- `--output <path>`: Override output path
- `--validate-only`: Only validate YAML, don't generate

## Processing Steps

### Step 1: Load and Parse YAML

1. Read the YAML file from the provided path
2. Parse using PyYAML (handle as structured data)
3. Determine complexity level from `complexity_level` field (default: "moderate")
4. Validate basic structure

**Error Handling:**
- If file not found: Show clear error with full path attempted
- If YAML malformed: Show parsing error with helpful message
- If missing required fields: List all missing fields

### Step 2: Process Advanced Features

**If complexity level is "advanced":**

1. **Process Variables:**
   - Extract `variables` section
   - Resolve nested variables (e.g., log_dir depends on project_root)
   - Substitute all ${var_name} references throughout YAML
   - Variables can be used in any string field

2. **Process Includes:**
   - Read each file in `includes` array
   - Merge sections in order (later overrides earlier)
   - Final YAML overrides all includes
   - Detect circular includes (error if found)

3. **Process Conditionals:**
   - Evaluate `conditional_sections` based on `task_type`
   - Include matching sections in final structure
   - Skip non-matching sections

### Step 3: Auto-Population from CLAUDE.md

**When `project.auto_populate_standard_info: true` OR complexity is not "simple":**

1. Read ~/iMatrix/iMatrix_Client/CLAUDE.md
2. Extract standard sections:
   - Repository Overview → project structure
   - Hardware info (iMX6, 512MB RAM, etc.) → hardware section
   - Development guidelines → guidelines.principles
3. Use extracted info as defaults
4. YAML-specified values override defaults
5. Track which sections were auto-generated for metadata

**Auto-populated defaults:**
- project.core_library: "iMatrix - Contains all core telematics functionality"
- project.main_application: "Fleet-Connect-1 - Main application logic"
- hardware.processor: "iMX6"
- hardware.ram: "512MB"
- hardware.flash: "512MB"
- user.name: "Greg"
- guidelines.principles: [KISS, Doxygen comments, use templates, embedded efficiency]

### Step 4: Validation

**Required Fields by Complexity:**

**Simple:**
- `title` (string, not empty)
- `task` (string, not empty)

**Moderate:**
- `title` (string, not empty)
- `task` (object or string, not empty)
- `deliverables` (object, can be auto-generated)

**Advanced:**
- `title` (string, not empty)
- `task` (object with phases OR detailed requirements)
- `metadata` (object)
- At least one of: `task.phases` OR `architecture` section

**Recommended Fields (warnings if missing, fail hard in non-interactive mode):**
- `prompt_name` (auto-generate from title if missing)
- `date` (auto-fill with current date if missing)
- `branch` (auto-generate from title if missing)
- `deliverables.plan_document` (auto-generate if missing)

**Validation Rules:**
1. `prompt_name`: Must match ^[a-z0-9_]+$ (lowercase, numbers, underscores only)
2. `date`: Must be YYYY-MM-DD format
3. `branch`: Should match (feature|bugfix|refactor|debug)/[a-z0-9-]+
4. Referenced files: Warn if don't exist (don't fail)
5. Empty question answers: Warn (will prompt during implementation)

**Non-Interactive Mode Behavior:**
- Missing required fields: FAIL with error message
- Missing recommended fields with auto-generate: WARN and auto-generate
- Missing recommended fields without auto-generate: FAIL
- Validation warnings: FAIL (strict mode)

**Interactive Mode Behavior:**
- Missing required fields: Prompt user to enter
- Missing recommended fields: Suggest auto-generated value, allow override
- Validation warnings: Show warning, ask to continue

### Step 5: Auto-Generate Missing Fields

1. **prompt_name**: If missing, generate from title
   - Convert title to lowercase
   - Replace spaces with underscores
   - Remove special characters
   - Example: "Add New Feature" → "add_new_feature"
   - Show preview and confirm

2. **date**: If missing, use current date (YYYY-MM-DD)

3. **branch**: If missing, generate from title and type
   - Detect type from task content (feature/bugfix/refactor/debug)
   - Use prompt_name as branch suffix
   - Example: "feature/add_new_feature"

4. **deliverables.plan_document**: If missing
   - Generate as: "docs/${prompt_name}.md" or "docs/gen/${prompt_name}.md"

### Step 6: Generate Markdown Output

**Output Structure depends on complexity level:**

#### SIMPLE Template

```markdown
<!--
AUTO-GENERATED PROMPT
Generated from: {yaml_source_file}
Generated on: {generation_timestamp}
Schema version: 1.0
Complexity level: simple

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim {title}

**Date:** {date}
**Branch:** {branch}

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

Read and understand the following

{auto_populated_references or defaults}

use the template files as a base for any new files created
iMatrix/templates/blank.c
iMatrix/templates/blank.h

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

{additional notes if provided}

## Task

{task description}

{files_to_modify if provided}

{notes if provided}

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** {plan_document} ***, of all aspects and detailed todo list for me to review before commencing the implementation.
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
**Source Specification:** {yaml_source_file}
**Generated:** {generation_timestamp}
```

#### MODERATE Template

```markdown
<!--
AUTO-GENERATED PROMPT
Generated from: {yaml_source_file}
Generated on: {generation_timestamp}
Schema version: 1.0
Complexity level: moderate
Auto-populated sections: {list}

To modify this prompt, edit the source YAML file and regenerate.
-->

## Aim {title}

**Date:** {date}
**Branch:** {branch}
**Objective:** {objective}

---

## Code Structure:

{project.core_library description}

{project.main_application description}

{project.additional_context if provided}

## Background

The system is a telematics gateway supporting CAN BUS and various sensors.
The Hardware is based on an {hardware.processor} processor with {hardware.ram} RAM and {hardware.flash} FLASH
{hardware details...}

The user's name is {user.name}

Read and understand the following

{references.documentation as list}

{references.source_files with focus areas}

use the template files as a base for any new files created
{references.templates}

code runs on embedded system from: {guidelines.code_runtime.directory}

Always create extensive comments using doxygen style

**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**

{additional_background if provided}

{debug section if provided:}
Debug flags currently in use:
{debug.flags as list with values and descriptions}

debug {debug.active_flags}

Log files will be stored {debug.log_directory}

## Task

{task.summary}

{task.description}

{task.requirements as numbered list}

{task.implementation_notes if provided}

{task.detailed_specifications if provided}

## Deliverables

1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.
2. Detailed plan document, *** {deliverables.plan_document} ***, of all aspects and detailed todo list for me to review before commencing the implementation.
{standard workflow steps or deliverables.steps}
{deliverables.additional_steps if provided}

{questions section if provided}

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** {yaml_source_file}
**Generated:** {generation_timestamp}
**Auto-populated:** {count} sections
```

#### ADVANCED Template

```markdown
<!--
AUTO-GENERATED PROMPT
Generated from: {yaml_source_file}
Generated on: {generation_timestamp}
Schema version: 1.0
Complexity level: advanced
Auto-populated sections: {list}

To modify this prompt, edit the source YAML file and regenerate.
-->

# {metadata.title}

**Date:** {metadata.date}
**Branch:** {metadata.branch}
**Objective:** {metadata.objective}
**Estimated Effort:** {metadata.estimated_effort}
**Priority:** {metadata.priority}

---

## Executive Summary

{auto_generated from objective and task.phases summary}

---

{current_state section if provided:}
## Current Implementation Analysis

### Workflow

{current_state.workflow as numbered steps with locations}

### Problems

{current_state.problems as list with severity indicators}

---

{architecture section if provided:}
## Proposed Architecture

### New Module: {architecture.new_module.name}

**Purpose:** {derived from responsibilities}

**Location:** {architecture.new_module.location}

**Responsibilities:**
{architecture.new_module.responsibilities as list}

### Data Structures

{for each architecture.data_structures:}
#### {name}

```c
{description}
typedef {type} {
  {fields or values}
}
```
{end for}

---

## Detailed Design

{if task.phases:}
## Implementation Phases

{for each phase:}
### Phase {phase.phase}: {phase.name}

**Tasks:**
{phase.tasks as checklist}

**Deliverable:** {phase.deliverable}

{end for}
{else:}
## Task Requirements

{task.requirements as detailed list}
{endif}

---

{conditional_sections if task_type matches:}
## Design Decisions & Rationale

{for each conditional_sections.when_{task_type}.design_decisions:}
### {decision.decision}

{decision.rationale}
{end for}

## Risk Mitigation

{for each conditional_sections.when_{task_type}.risk_mitigation:}
| Risk | Mitigation |
|------|------------|
| {risk.risk} | {risk.mitigation} |
{end for}

---

{success_criteria if provided:}
## Success Criteria

### Functional Requirements
{success_criteria.functional as checklist}

### Quality Requirements
{success_criteria.quality as checklist}

{if success_criteria.performance:}
### Performance Requirements
{success_criteria.performance as checklist}
{endif}

---

## Deliverables

{deliverables.plan_document}

{deliverables.steps or standard workflow}

{if deliverables.additional_deliverables:}
**Additional Deliverables:**
{deliverables.additional_deliverables as list}
{endif}

{if deliverables.metrics:}
**Metrics to Track:**
{deliverables.metrics as list}
{endif}

---

{special_instructions if provided:}
## Special Instructions

{special_instructions.pre_implementation}
{special_instructions.system_files_required}
{etc.}

---

{questions if provided:}
## Questions

{for each question:}
### {question.question}

{if question.suggested_answer:}
**Suggested Answer:** {question.suggested_answer}
{endif}

**Answer:** {question.answer or ""}

{end for}

---

**Plan Created By:** Claude Code (via YAML specification)
**Source Specification:** {yaml_source_file}
**Generated:** {generation_timestamp}
**Schema Version:** 1.0
**Auto-populated:** {auto_populated_count} sections
```

### Step 7: Write Output File

1. Generate filename from `prompt_name` field: `{prompt_name}.md`
2. Full output path: `~/iMatrix/iMatrix_Client/docs/gen/{prompt_name}.md`
3. Check if file exists:
   - If exists: Show warning, ask for confirmation to overwrite (interactive mode)
   - If exists in non-interactive: ERROR and abort
4. Create `docs/gen/` directory if it doesn't exist
5. Write generated markdown to file
6. Set file permissions (644)

### Step 8: Display Summary

Show comprehensive summary:

```
✓ YAML parsed successfully
  Complexity: {complexity_level}
  Variables: {count} defined, {count} substitutions
  Includes: {count} files merged

✓ Validation passed
  Warnings: {count}
  {list warnings if any}

✓ Auto-populated {count} sections from CLAUDE.md
  - Project structure
  - Hardware information
  - Development guidelines
  - Standard references

✓ Generated markdown prompt
  Output: ~/iMatrix/iMatrix_Client/docs/gen/{prompt_name}.md
  Sections: {total_sections} ({auto_generated_count} auto, {yaml_count} from YAML)
  Lines: {line_count}
  Size: {file_size}

Preview (first 20 lines):
---
{first 20 lines of output}
---

{if warnings:}
⚠ Warnings:
  - {warning 1}
  - {warning 2}
{endif}

Next steps:
  1. Review generated prompt: docs/gen/{prompt_name}.md
  2. Use this prompt with Claude Code to implement the task
  3. Update YAML spec with any refinements during implementation
```

## Error Messages

### Missing Required Field

```
ERROR: YAML validation failed

Required fields missing:
  - title (required for all complexity levels)
  - task (required for all complexity levels)

Complexity level: moderate
Additional required for moderate:
  - deliverables (can be auto-generated if you approve)

In non-interactive mode, all required fields must be present.

Would you like to:
  1. Enter missing values interactively
  2. Edit YAML file and try again
  3. Cancel

Choice [1-3]:
```

### Invalid YAML Syntax

```
ERROR: Failed to parse YAML file

File: specs/examples/my_prompt.yaml
Error: mapping values are not allowed here
  in "<unicode string>", line 45, column 15

Please check your YAML syntax.

Tips:
  - Check indentation (use spaces, not tabs)
  - Ensure colons have spaces after them
  - Quote strings containing special characters
  - Use a YAML validator: yamllint specs/examples/my_prompt.yaml
```

### File Already Exists

```
WARNING: Output file already exists

Path: ~/iMatrix/iMatrix_Client/docs/gen/my_prompt.md
Last modified: 2025-11-17 10:30:45
Size: 15.2 KB

Options:
  1. Overwrite existing file
  2. Save with different name (specify)
  3. Cancel and exit

Choice [1-3]:
```

### Validation Warning (Strict Mode)

```
ERROR: Validation failed in strict mode

Warnings treated as errors in non-interactive mode:

  1. Question 3 has no answer
     Field: questions[2].answer
     Issue: Empty answer field
     Suggestion: Provide answer or remove question

  2. Referenced file not found
     Field: references.documentation[5]
     File: ~/iMatrix/docs/missing_file.md
     Suggestion: Verify file path or remove reference

To proceed:
  - Fix issues in YAML file
  - OR run in interactive mode: /build_imatrix_client_prompt --interactive <file>
```

## Implementation

Now implement the above logic. Use the YAML parsing capabilities available, handle all error cases gracefully, and generate well-formatted markdown output that matches the structure of the example prompts provided.

Read the YAML file, perform all processing steps, validate thoroughly, and generate the complete markdown prompt file as specified above.
