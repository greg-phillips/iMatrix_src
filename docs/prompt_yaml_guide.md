# iMatrix Prompt Generation System - Complete Guide

**Version:** 1.0
**Last Updated:** 2025-11-17
**Author:** Claude Code

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Overview](#system-overview)
3. [Complexity Levels](#complexity-levels)
4. [Complete Field Reference](#complete-field-reference)
5. [Examples by Complexity](#examples-by-complexity)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

**5-Minute Quickstart - Create Your First Prompt**

1. **Create a YAML file** in `specs/examples/`:
   ```yaml
   complexity_level: "simple"
   title: "Fix GPS timeout bug"
   task: "Fix the GPS timeout occurring in location.c line 342"
   branch: "bugfix/gps-timeout"
   ```

2. **Generate the prompt**:
   ```bash
   /build_imatrix_client_prompt specs/examples/my_fix.yaml
   ```

3. **Review the output**:
   ```bash
   cat docs/gen/fix_gps_timeout_bug.md
   ```

4. **Use the generated prompt** to start your development task!

---

## System Overview

The iMatrix Prompt Generation System transforms structured YAML specifications into comprehensive Markdown development prompts. It supports:

- ✅ **Three complexity levels** (simple, moderate, advanced)
- ✅ **Auto-population** from CLAUDE.md
- ✅ **Variable substitution** (advanced mode)
- ✅ **Template includes** for reusability
- ✅ **Strict validation** with helpful errors
- ✅ **Interactive mode** for missing fields

### Architecture

```
YAML Spec File
      ↓
  Parse & Validate
      ↓
  Process Includes/Variables (advanced)
      ↓
  Auto-populate from CLAUDE.md
      ↓
  Generate Markdown
      ↓
  Output to docs/gen/
```

### Directory Structure

```
~/iMatrix/iMatrix_Client/
├── specs/
│   ├── templates/              # Reusable YAML templates
│   │   ├── standard_imatrix_context.yaml
│   │   └── network_debugging_setup.yaml
│   ├── examples/
│   │   ├── simple/             # Simple complexity examples
│   │   ├── moderate/           # Moderate complexity examples
│   │   └── advanced/           # Advanced complexity examples
│   └── schema/
│       └── prompt_schema_v1.yaml  # Complete schema definition
├── docs/gen/                   # Generated prompt output
└── .claude/commands/
    └── build_imatrix_client_prompt.md  # Slash command
```

---

## Complexity Levels

### Comparison Table

| Feature | Simple | Moderate | Advanced |
|---------|--------|----------|----------|
| **Use Case** | Quick fixes, small tasks | Standard features | Complex refactoring, multi-phase projects |
| **Structure** | Flat | Nested sections | Highly structured |
| **Required Fields** | title, task | title, task, deliverables | title, task, metadata, (phases OR architecture) |
| **Auto-population** | No | Yes | Yes |
| **Variables** | No | No | Yes |
| **Includes** | No | No | Yes |
| **Conditionals** | No | No | Yes |
| **Typical Length** | 50-100 lines YAML | 100-200 lines YAML | 200-500 lines YAML |
| **Output Prompt** | ~2 pages | ~5-10 pages | ~15-30 pages |

### When to Use Each Level

#### Simple
- **Best for:**
  - Quick bug fixes
  - Simple feature additions
  - Documentation updates
  - Code cleanup tasks

- **Example scenarios:**
  - "Fix memory leak in CAN processing"
  - "Add logging to network function"
  - "Update README with new build instructions"

#### Moderate
- **Best for:**
  - Standard feature development
  - Module additions
  - Integration work
  - Most daily development tasks

- **Example scenarios:**
  - "Add ping command to CLI"
  - "Implement new sensor driver"
  - "Add BLE characteristic for configuration"

#### Advanced
- **Best for:**
  - System refactoring
  - Architecture changes
  - Multi-phase projects
  - Complex debugging investigations

- **Example scenarios:**
  - "Refactor PPP connection management"
  - "Redesign memory allocation system"
  - "Debug and fix network stability issues"

---

## Complete Field Reference

### Top-Level Fields

#### `complexity_level`
```yaml
complexity_level: "simple"  # or "moderate" or "advanced"
```
- **Type:** string
- **Values:** simple, moderate, advanced
- **Default:** moderate
- **Description:** Determines which schema features are available

#### `prompt_name`
```yaml
prompt_name: "my_feature_plan"
```
- **Type:** string
- **Pattern:** `^[a-z0-9_]+$` (lowercase, numbers, underscores)
- **Auto-generate:** Yes (from title)
- **Description:** Output filename (without .md extension)

#### `title`
```yaml
title: "Add new feature to system"
```
- **Type:** string
- **Required:** YES (all levels)
- **Description:** Main prompt title/aim

#### `date`
```yaml
date: "2025-11-17"
```
- **Type:** string
- **Format:** YYYY-MM-DD
- **Auto-fill:** Yes (current date)
- **Description:** Prompt creation date

#### `branch`
```yaml
branch: "feature/my-new-feature"
```
- **Type:** string
- **Pattern:** `^(feature|bugfix|refactor|debug)/[a-z0-9-]+$`
- **Auto-generate:** Yes (from title and task type)
- **Description:** Git branch name for this work

#### `objective`
```yaml
objective: "Implement user authentication system"
```
- **Type:** string
- **Recommended:** Yes (moderate+)
- **Description:** High-level objective statement

---

### Project Section

```yaml
project:
  core_library: "iMatrix"
  main_application: "Fleet-Connect-1"
  auto_populate_standard_info: true  # Moderate/Advanced
  additional_context: |
    This feature focuses on the networking subsystem...
```

**Fields:**
- `core_library`: Name or description of core library
- `main_application`: Name or description of main app
- `auto_populate_standard_info`: Pull standard info from CLAUDE.md
- `additional_context`: Extra project-specific information

**Auto-populated defaults:**
- core_library: "iMatrix - Contains all core telematics functionality"
- main_application: "Fleet-Connect-1 - Main system management logic"

---

### Hardware Section

```yaml
hardware:
  processor: "iMX6"
  ram: "512MB"
  flash: "512MB"
  wifi_chipset: "Combination Wi-Fi/Bluetooth chipset"
  cellular_chipset: "PLS62/63 from TELIT CINTERION"
  additional_info:
    - "Code is cross-compiled for ARM"
  additional_notes:
    - "Limited to LINUX_PLATFORM only"
```

**All fields auto-populated from CLAUDE.md unless overridden**

---

### References Section

```yaml
references:
  documentation:
    - "~/iMatrix/docs/api_guide.md"
    - "~/iMatrix/docs/developer_guide.md"

  source_files:
    - "iMatrix/cli/cli_commands.c"
    - path: "iMatrix/networking"
      focus: ["process_network.c", "cellular_man.c"]  # Advanced

  templates:
    - "iMatrix/templates/blank.c"
    - "iMatrix/templates/blank.h"

  read_first:  # Recommended to read before starting
    - "docs/CLI_Guide.md"

  use_standard: true  # Auto-include blank.c/blank.h
```

**Advanced mode features:**
- `pattern`: Glob pattern for file matching
- `focus`: Specific files to focus on
- `exclude`: Files to exclude from pattern

---

### Debug Section

```yaml
debug:
  flags:
    - value: "0x0000000000040000"
      description: "Debugs for WIFI0 Networking"
    - value: "0x0000000000080000"
      description: "Debugs for PPP0 Networking"

  active_flags: "0x00000008001F0000"

  log_directory: "~/iMatrix/iMatrix_Client/logs"

  log_files:
    - "network_debug.log"
    - "cellular_debug.log"

  analysis_files:  # Advanced
    use_agent: true  # Use agent for large file analysis
    files:
      - "logs/net1.txt"
      - "logs/net2.txt"
```

---

### Guidelines Section

```yaml
guidelines:
  principles:
    - "KISS principle - keep it simple"
    - "Use Doxygen comments"
    - "Follow embedded best practices"

  code_runtime:
    directory: "/home"
    platform: "Embedded Linux system"
```

**Auto-populated principles:**
- "Think ultrahard as you read and implement"
- "KISS principle - do not over-engineer"
- "Always create extensive comments using Doxygen style"
- "Use template files as base for any new files created"

---

### Task Section

#### Simple Mode
```yaml
task: |
  Fix the memory leak in can_process.c line 245.
  Add proper cleanup for allocated buffers.
```

#### Moderate Mode
```yaml
task:
  summary: "Implement ping command for CLI"

  description: |
    Add a Linux-style ping command to the CLI for network diagnostics.

  requirements:
    - "Support -c <count> flag"
    - "Support -I <interface> flag"
    - "Default to 4 ping attempts"

  implementation_notes:
    - "Use existing ping from process_network.c"
    - "Run in non-blocking mode"

  detailed_specifications:
    - section: "Output Format"
      details: |
        PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
        64 bytes from 8.8.8.8: icmp_seq=1 ttl=113 time=20.3 ms
```

#### Advanced Mode
```yaml
task:
  phases:
    - phase: 1
      name: "Create New Module"
      tasks:
        - "Define data structures"
        - "Implement core functions"
        - "Add to build system"
      deliverable: "Working module with tests"

    - phase: 2
      name: "Integration"
      tasks:
        - "Integrate with existing system"
        - "Add error handling"
      deliverable: "Integrated and tested"
```

---

### Current State Section (Advanced)

```yaml
current_state:
  workflow:
    - step: "cellular_man.c initializes modem"
      location: "cellular_man.c:2064"
    - step: "process_network.c detects ready flag"
      location: "process_network.c:4531"

  problems:
    - issue: "Missing Configuration"
      description: "pon requires /etc/ppp/peers/provider which doesn't exist"
      severity: "high"
    - issue: "No Logging"
      description: "Cannot see chat script execution"
      severity: "medium"
```

---

### Architecture Section (Advanced)

```yaml
architecture:
  new_module:
    name: "ppp_connection.c"
    location: "iMatrix/IMX_Platform/LINUX_Platform/networking/ppp_connection.c"
    responsibilities:
      - "Start/stop PPPD daemon"
      - "Parse connection logs"
      - "Provide status information"

  data_structures:
    - name: "ppp_state_t"
      type: "enum"
      file: "ppp_connection.h"
      values:
        - "PPP_STATE_STOPPED"
        - "PPP_STATE_STARTING"
        - "PPP_STATE_CONNECTED"
```

---

### Deliverables Section

```yaml
deliverables:
  plan_document: "docs/my_feature_plan.md"

  use_standard_workflow: true  # Include standard iMatrix workflow

  workflow_template: "standard_imatrix_development"  # Named template

  steps:  # Custom steps (replaces standard if provided)
    - "Create git branch"
    - "Implement feature"
    - "Test and validate"

  additional_steps:  # Adds to standard workflow
    - "Create integration tests"
    - "Update documentation"

  additional_deliverables:
    - "Performance test results"
    - "Updated architecture diagram"

  metrics:  # Advanced
    - "Connection time: old vs new"
    - "Memory usage comparison"
```

---

### Questions Section

```yaml
questions:
  - question: "Should we support IPv6?"
    answer: "No, IPv4 only for now"

  - question: "Timeout duration?"
    suggested_answer: "30 seconds (current value)"
    answer: "30 seconds"

  - question: "Add CLI command for status?"
    answer: ""  # Empty - will prompt during implementation
    conditional: "task_type == refactor"  # Advanced: only if refactoring
```

---

### Metadata Section (Advanced)

```yaml
metadata:
  title: "PPP0 Connection Refactoring Plan"
  date: "2025-11-16"
  branch: "bugfix/network-stability"
  objective: "Refactor PPP connection management"
  estimated_effort: "4-6 hours development + 2 hours testing"
  priority: "high"  # or low, medium, critical
```

---

### Variables Section (Advanced)

```yaml
variables:
  project_root: "~/iMatrix/iMatrix_Client"
  imatrix_path: "${project_root}/iMatrix"
  network_path: "${imatrix_path}/IMX_Platform/LINUX_Platform/networking"
  log_dir: "${project_root}/logs"

# Use variables anywhere with ${var_name}
debug:
  log_directory: "${log_dir}"

architecture:
  new_module:
    location: "${network_path}/ppp_connection.c"
```

**Features:**
- Nested variable resolution
- Substitution in any string field
- Clear error if undefined variable referenced

---

### Includes Section (Advanced)

```yaml
includes:
  - "specs/templates/standard_imatrix_context.yaml"
  - "specs/templates/network_debugging_setup.yaml"
```

**Processing:**
1. Files merged in order
2. Later includes override earlier
3. Final YAML overrides all includes
4. Circular include detection

---

### Conditional Sections (Advanced)

```yaml
task_type: "refactor"  # or feature, bugfix, debug

conditional_sections:
  when_refactoring:  # Only included if task_type == "refactoring"
    design_decisions:
      - decision: "Wrapper Functions"
        rationale: "Maintains API compatibility..."

    risk_mitigation:
      - risk: "Breaking existing functionality"
        mitigation: "Keep deprecated functions, use wrappers"

  when_debug:  # Only if task_type == "debug"
    debug_strategy:
      - "Add comprehensive logging"
      - "Use mutex tracking tools"
```

---

### Success Criteria (Advanced)

```yaml
success_criteria:
  functional:
    - "PPP0 connects successfully"
    - "Logs show clear state progression"
    - "Error messages are actionable"

  quality:
    - "Build clean with zero warnings"
    - "Backward compatible"
    - "Works in production environment"

  performance:
    - "Connection time < 5 seconds"
    - "Log parsing overhead < 10ms"
```

---

## Examples by Complexity

### Simple Example: Bug Fix

```yaml
complexity_level: "simple"

title: "Fix memory leak in CAN processing"

task: |
  Fix the memory leak occurring in can_process.c when processing high-frequency
  CAN messages. The leak is at line 245 where buffers aren't being freed.

  Steps:
  1. Review can_process.c line 245
  2. Identify buffer allocation
  3. Add proper cleanup
  4. Verify with valgrind

branch: "bugfix/can-memory-leak"

files_to_modify:
  - "iMatrix/canbus/can_process.c"
  - "iMatrix/canbus/can_process.h"

notes:
  - "Affects high CAN traffic vehicles (>1000 msgs/sec)"
  - "Memory grows ~10MB/hour under load"
```

**Generated Output:** ~2-page prompt with task, standard deliverables, build verification

---

### Moderate Example: Feature Addition

See `specs/examples/moderate/ping_command.yaml` for complete example.

**Key features:**
- Auto-populated project/hardware info
- Detailed requirements list
- Implementation notes
- Questions with answers
- Standard workflow deliverables

**Generated Output:** ~5-10 page comprehensive prompt

---

### Advanced Example: Refactoring

See `specs/examples/advanced/ppp_refactoring.yaml` for complete example.

**Key features:**
- Variable substitution
- Template includes
- Multi-phase task breakdown
- Architecture definitions
- Design decisions & risk mitigation
- Conditional sections
- Success criteria

**Generated Output:** ~15-30 page detailed plan

---

## Best Practices

### 1. Choose the Right Complexity Level

**Start simple, scale up as needed:**
- Simple: If you can describe the task in 1-2 paragraphs
- Moderate: If you need multiple requirements and references
- Advanced: If you have architecture changes or multi-phase work

### 2. Use Includes for Reusability

```yaml
includes:
  - "specs/templates/standard_imatrix_context.yaml"  # Always include
  - "specs/templates/network_debugging_setup.yaml"   # If networking task
```

**Benefits:**
- Consistent project context
- Reduces duplication
- Easy to update common sections

### 3. Leverage Auto-Population

```yaml
project:
  auto_populate_standard_info: true  # Let CLAUDE.md fill in defaults
  additional_context: |
    Override only what's specific to this task...
```

**Benefits:**
- Less typing
- Consistent information
- Automatic updates when CLAUDE.md changes

### 4. Use Variables for Paths (Advanced)

```yaml
variables:
  project_root: "~/iMatrix/iMatrix_Client"
  module_path: "${project_root}/iMatrix/my_module"

references:
  source_files:
    - "${module_path}/src/main.c"
```

**Benefits:**
- DRY principle
- Easy path updates
- Clear intent

### 5. Break Complex Tasks into Phases (Advanced)

```yaml
task:
  phases:
    - phase: 1
      name: "Foundation"
      tasks: [...]
      deliverable: "Core module working"

    - phase: 2
      name: "Integration"
      tasks: [...]
      deliverable: "Integrated with system"
```

**Benefits:**
- Clear milestones
- Easier to track progress
- Natural checkpoint for review

### 6. Document Design Decisions

```yaml
conditional_sections:
  when_refactoring:
    design_decisions:
      - decision: "Choice made"
        rationale: "Why we made this choice..."
```

**Benefits:**
- Context for future maintainers
- Easier code review
- Documents trade-offs

### 7. Define Success Criteria

```yaml
success_criteria:
  functional:
    - "Feature works as specified"
  quality:
    - "Zero warnings"
  performance:
    - "Meets timing requirements"
```

**Benefits:**
- Clear definition of "done"
- Testable criteria
- Prevents scope creep

---

## Troubleshooting

### Common Errors and Solutions

#### 1. "Required field missing: title"

**Problem:** YAML missing required field

**Solution:**
```yaml
# Add required field
title: "My Task Title"
```

#### 2. "Invalid prompt_name: Must match ^[a-z0-9_]+$"

**Problem:** Prompt name has invalid characters

**Solution:**
```yaml
# Wrong:
prompt_name: "My-Feature-Plan"

# Correct:
prompt_name: "my_feature_plan"
```

#### 3. "Failed to parse YAML: mapping values not allowed"

**Problem:** YAML syntax error (often indentation)

**Solution:**
- Check indentation (use spaces, not tabs)
- Ensure colons have spaces after them
- Use a YAML validator: `yamllint specs/my_file.yaml`

#### 4. "Variable ${var_name} is undefined"

**Problem:** Using variable that wasn't defined

**Solution:**
```yaml
# Define before use
variables:
  var_name: "value"

# Then use
field: "${var_name}/path"
```

#### 5. "Circular include detected"

**Problem:** File A includes B, which includes A

**Solution:**
- Review include chain
- Remove circular dependency
- Create shared base template

#### 6. "Output file already exists"

**Problem:** Trying to overwrite existing file

**Solutions:**
- Delete old file first
- Use different prompt_name
- Confirm overwrite in interactive mode

---

## Advanced Topics

### Creating Reusable Templates

Create templates in `specs/templates/`:

```yaml
# specs/templates/my_template.yaml
project:
  my_common_field: "common value"

guidelines:
  my_common_guidelines:
    - "Guideline 1"
    - "Guideline 2"
```

Include in your spec:
```yaml
includes:
  - "specs/templates/my_template.yaml"
```

### Variable Scope and Resolution

Variables are resolved in order:

1. Define variables
2. Resolve nested dependencies
3. Substitute throughout document

```yaml
variables:
  root: "/path"
  sub: "${root}/subdir"    # Resolves to /path/subdir
  final: "${sub}/file"      # Resolves to /path/subdir/file
```

### Conditional Logic Patterns

```yaml
task_type: "feature"  # Set condition variable

conditional_sections:
  when_feature:      # Matches task_type == "feature"
    feature_specific: [...]

  when_bugfix:       # Skipped (task_type != "bugfix")
    bugfix_specific: [...]
```

---

## Validation Reference

### Required Fields by Level

| Level | Required Fields |
|-------|----------------|
| Simple | title, task |
| Moderate | title, task, deliverables |
| Advanced | title, task, metadata, (phases OR architecture) |

### Field Format Rules

| Field | Rule | Example |
|-------|------|---------|
| prompt_name | `^[a-z0-9_]+$` | `my_feature_plan` |
| date | `YYYY-MM-DD` | `2025-11-17` |
| branch | `(feature\|bugfix\|refactor\|debug)/[a-z0-9-]+` | `feature/my-feature` |

### Validation Modes

**Non-Interactive (Strict):**
- Missing required: FAIL
- Missing recommended: FAIL (unless auto-generate)
- Warnings: FAIL
- Invalid format: FAIL

**Interactive:**
- Missing required: PROMPT user
- Missing recommended: SUGGEST default
- Warnings: SHOW, ask to continue
- Invalid format: SHOW error, ask to fix

---

## Quick Reference Card

```yaml
# Minimal Simple
complexity_level: "simple"
title: "Task Title"
task: "Task description"

# Minimal Moderate
complexity_level: "moderate"
title: "Task Title"
task:
  summary: "Summary"
  requirements: [...]

# Minimal Advanced
complexity_level: "advanced"
includes: ["specs/templates/standard_imatrix_context.yaml"]
metadata:
  title: "Title"
  objective: "Objective"
task:
  phases: [...]
```

---

## Getting Help

- **Schema Reference**: `specs/schema/prompt_schema_v1.yaml`
- **Examples**: `specs/examples/{simple,moderate,advanced}/`
- **Templates**: `specs/templates/`
- **This Guide**: `docs/prompt_yaml_guide.md`

For issues or questions, refer to the example files or schema definition.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-17
**Maintained By:** iMatrix Development Team
