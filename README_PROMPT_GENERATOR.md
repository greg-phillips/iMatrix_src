# iMatrix Prompt Generator - Quick Start Guide

**Version:** 1.0
**Status:** ✅ Fully Functional
**Last Updated:** 2025-11-17

---

## Overview

The iMatrix Prompt Generator is a comprehensive system for creating structured development prompts from YAML specifications. It supports three complexity levels and includes both a Claude Code slash command and a standalone Python script.

## Quick Start (30 seconds)

```bash
# 1. Create a YAML spec
cat > specs/my_feature.yaml <<EOF
complexity_level: "simple"
title: "Fix timeout bug"
task: "Fix the timeout in network.c line 123"
EOF

# 2. Generate prompt
python3 scripts/build_prompt.py specs/my_feature.yaml

# 3. Use the prompt
cat docs/gen/fix_timeout_bug.md
```

---

## Two Ways to Use

### Option 1: Standalone Python Script (Automated)

```bash
python3 scripts/build_prompt.py <yaml_file>
```

**Features:**
- ✅ Runs independently
- ✅ Batch processing
- ✅ CI/CD integration
- ✅ Colored output
- ✅ Comprehensive validation

**Requirements:**
- Python 3.6+
- PyYAML (`pip install pyyaml`)

### Option 2: Claude Code Slash Command (Interactive)

```bash
/build_imatrix_client_prompt <yaml_file>
```

**Features:**
- ✅ Interactive prompting
- ✅ Real-time Q&A
- ✅ Context-aware
- ✅ Integrated with Claude

**Note:** This loads the prompt specification and I (Claude) execute the generation interactively.

---

## File Locations

```
~/iMatrix/iMatrix_Client/
├── scripts/
│   └── build_prompt.py              ← Python script
├── .claude/commands/
│   └── build_imatrix_client_prompt.md  ← Slash command
├── specs/
│   ├── schema/
│   │   └── prompt_schema_v1.yaml    ← Complete schema
│   ├── templates/
│   │   ├── standard_imatrix_context.yaml    ← Reusable context
│   │   └── network_debugging_setup.yaml     ← Network debug
│   └── examples/
│       ├── simple/quick_bug_fix.yaml
│       ├── moderate/ping_command.yaml
│       └── advanced/ppp_refactoring.yaml
├── docs/
│   ├── gen/                         ← Generated prompts (output)
│   ├── prompt_yaml_guide.md         ← Complete user guide
│   └── slash_command_implementation_summary.md
└── README_PROMPT_GENERATOR.md       ← This file
```

---

## Three Complexity Levels

### Simple (Quick fixes, small tasks)

**YAML Example:**
```yaml
complexity_level: "simple"
title: "Fix memory leak"
task: "Fix leak in can_process.c line 245"
branch: "bugfix/can-memory-leak"
```

**Output:** ~2-page prompt with standard structure

### Moderate (Standard features, typical development)

**YAML Example:**
```yaml
complexity_level: "moderate"
title: "Add ping command"
objective: "Implement network diagnostics"
project:
  auto_populate_standard_info: true
task:
  summary: "Implement ping command"
  requirements:
    - "Support -c flag for count"
    - "Support -I flag for interface"
```

**Output:** ~5-10 page comprehensive prompt

### Advanced (Complex refactoring, multi-phase projects)

**YAML Example:**
```yaml
complexity_level: "advanced"
variables:
  project_root: "~/iMatrix/iMatrix_Client"
  path: "${project_root}/iMatrix"
includes:
  - "specs/templates/standard_imatrix_context.yaml"
metadata:
  title: "PPP Refactoring"
  objective: "Refactor PPP connection management"
task:
  phases:
    - phase: 1
      name: "Create Module"
      tasks: [...]
```

**Output:** ~15-30 page detailed plan

---

## Key Features

### ✅ Auto-Population
Standard sections automatically filled from CLAUDE.md:
- Project structure
- Hardware info
- User name (Greg)
- Standard references
- Development guidelines

### ✅ Variable Substitution (Advanced)
```yaml
variables:
  root: "~/iMatrix"
  path: "${root}/iMatrix"  # Nested resolution
```

### ✅ Template Includes (Advanced)
```yaml
includes:
  - "specs/templates/standard_imatrix_context.yaml"
```

### ✅ Auto-Generation
Missing fields automatically generated:
- `prompt_name` from title
- `date` from current date
- `branch` from title + task type
- `plan_document` path

### ✅ Strict Validation
- Required fields enforced
- Format validation (dates, branch names)
- Helpful error messages
- Warnings for missing recommended fields

---

## Examples

### Example 1: Quick Bug Fix

```bash
python3 scripts/build_prompt.py specs/examples/simple/quick_bug_fix.yaml
```

**Output:**
```
✓ YAML parsed successfully
ℹ Complexity level: simple
✓ Generated prompt_name: fix_memory_leak_in_can_processing
✓ Validation passed
✓ Generated: docs/gen/fix_memory_leak_in_can_processing.md
  Lines: 83
```

### Example 2: Feature with Requirements

```bash
python3 scripts/build_prompt.py specs/examples/moderate/ping_command.yaml
```

**Features demonstrated:**
- Auto-population from CLAUDE.md
- Detailed requirements list
- Questions with answers
- Implementation notes

### Example 3: Complex Refactoring

```bash
python3 scripts/build_prompt.py specs/examples/advanced/ppp_refactoring.yaml
```

**Features demonstrated:**
- Variable substitution (5 variables)
- Include merging (2 templates)
- Multi-phase task breakdown
- Architecture definitions
- Design decisions

---

## Common Usage Patterns

### Pattern 1: Start from Template

```bash
# Copy existing example
cp specs/examples/simple/quick_bug_fix.yaml specs/my_fix.yaml

# Edit for your task
vim specs/my_fix.yaml

# Generate
python3 scripts/build_prompt.py specs/my_fix.yaml
```

### Pattern 2: Use Includes for Consistency

```yaml
complexity_level: "moderate"
includes:
  - "specs/templates/standard_imatrix_context.yaml"  # Standard info
  - "specs/templates/network_debugging_setup.yaml"    # If networking

title: "My Network Feature"
# ... rest of your spec
```

### Pattern 3: Batch Generate Multiple Prompts

```bash
for yaml in specs/my_features/*.yaml; do
    python3 scripts/build_prompt.py "$yaml"
done
```

---

## Validation Rules

### Required Fields

| Complexity | Required Fields |
|------------|----------------|
| Simple | `title`, `task` |
| Moderate | `title`, `task` |
| Advanced | `metadata.title`, `metadata`, `task` |

### Format Rules

| Field | Pattern | Example |
|-------|---------|---------|
| `prompt_name` | `^[a-z0-9_]+$` | `my_feature_plan` |
| `date` | `YYYY-MM-DD` | `2025-11-17` |
| `branch` | `(feature\|bugfix\|refactor\|debug)/[a-z0-9-]+` | `feature/my-feature` |

### Validation Modes

**Non-Interactive (Python Script):**
- Missing required → ERROR
- Missing recommended → WARNING → ERROR
- Invalid format → ERROR

**Interactive (Slash Command):**
- Missing required → PROMPT user
- Missing recommended → SUGGEST default
- Invalid format → ERROR with fix suggestion

---

## Troubleshooting

### Error: "YAML file not found"
```bash
# Use relative path from project root
python3 scripts/build_prompt.py specs/my_file.yaml
# NOT: python3 scripts/build_prompt.py my_file.yaml
```

### Error: "Invalid prompt_name"
```yaml
# Wrong:
prompt_name: "My-Feature-Plan"

# Correct:
prompt_name: "my_feature_plan"
```

### Error: "Required field missing: title"
```yaml
# For advanced mode, title goes in metadata:
metadata:
  title: "My Task Title"
```

### Warning: "Branch name doesn't match pattern"
```yaml
# Follow pattern:
branch: "feature/my-feature"  # ✓
branch: "feat/my-feature"     # ✗
branch: "my-feature"           # ✗
```

---

## Output Structure

### Generated Files

```
docs/gen/{prompt_name}.md
```

### Header Comment

Every generated prompt includes:
```markdown
<!--
AUTO-GENERATED PROMPT
Generated from: specs/examples/my_feature.yaml
Generated on: 2025-11-17 08:05:38
Schema version: 1.0
Complexity level: moderate

To modify this prompt, edit the source YAML file and regenerate.
-->
```

### Standard Sections

All prompts include:
1. Title/Aim
2. Date, Branch, Objective
3. Code Structure
4. Background
5. Task Description
6. Deliverables (with build verification)
7. Footer with generation info

---

## Advanced Topics

### Creating Custom Templates

```yaml
# specs/templates/my_template.yaml
project:
  my_field: "my value"

guidelines:
  principles:
    - "My custom guideline"
```

Use in specs:
```yaml
includes:
  - "specs/templates/my_template.yaml"
```

### Variable Scope

Variables resolve in order with nested dependencies:

```yaml
variables:
  root: "/path"
  sub: "${root}/subdir"    # → /path/subdir
  final: "${sub}/file"      # → /path/subdir/file
```

### Conditional Sections

```yaml
task_type: "refactor"

conditional_sections:
  when_refactoring:
    design_decisions: [...]
```

---

## Documentation

- **Complete User Guide:** `docs/prompt_yaml_guide.md` (500+ lines)
- **Schema Reference:** `specs/schema/prompt_schema_v1.yaml`
- **Implementation Summary:** `docs/slash_command_implementation_summary.md`
- **This Quick Start:** `README_PROMPT_GENERATOR.md`

---

## Testing

### Test All Examples

```bash
# Simple
python3 scripts/build_prompt.py specs/examples/simple/quick_bug_fix.yaml

# Moderate
python3 scripts/build_prompt.py specs/examples/moderate/ping_command.yaml

# Advanced
python3 scripts/build_prompt.py specs/examples/advanced/ppp_refactoring.yaml

# Verify output
ls -lh docs/gen/
```

### Validate Without Generating

```bash
# Not yet implemented, but coming soon:
python3 scripts/build_prompt.py --validate-only specs/my_file.yaml
```

---

## Integration

### CI/CD Pipeline

```yaml
# .github/workflows/generate-prompts.yml
- name: Generate Prompts
  run: |
    for yaml in specs/features/*.yaml; do
      python3 scripts/build_prompt.py "$yaml"
    done
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
if git diff --cached --name-only | grep -q "^specs/.*\.yaml$"; then
    echo "Regenerating prompts..."
    python3 scripts/build_prompt.py specs/updated_file.yaml
fi
```

---

## Next Steps

1. **Read the complete guide:** `docs/prompt_yaml_guide.md`
2. **Try the examples:** Generate all three example prompts
3. **Create your first spec:** Copy an example and customize
4. **Use the generated prompt:** Feed it to Claude Code for implementation

---

## Support

- **Examples:** `specs/examples/`
- **Templates:** `specs/templates/`
- **Schema:** `specs/schema/prompt_schema_v1.yaml`
- **Full Guide:** `docs/prompt_yaml_guide.md`

---

## System Status

### ✅ Phase 1 Complete
- Core infrastructure
- Schema definition
- Reusable templates
- All three complexity levels
- Python script implementation
- Claude slash command specification
- Comprehensive documentation

### ✅ Phase 2 Complete
- Tested all three examples
- Validation working
- Variable substitution working
- Include merging working
- Auto-generation working
- Error handling working

### ⏳ Future Enhancements
- Interactive mode for Python script
- Reverse conversion (MD → YAML)
- Additional templates
- More examples

---

**Created:** 2025-11-17
**Version:** 1.0
**Status:** Production Ready
**Author:** iMatrix Development Team
