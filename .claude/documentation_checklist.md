# Documentation Standards Checklist

**Created**: 2025-11-21
**Purpose**: Ensure all planning documents meet quality standards
**Reference**: See CLAUDE.md "Documentation Standards" section

---

## Required in ALL Planning Documents

### Header Section (Required)

```markdown
# Document Title

**Date**: 2025-11-21
**Time**: 08:07 (if specific time matters)
**Last Updated**: 2025-11-21
**Document Version**: 1.0
**Status**: Draft | In Review | Approved | Implemented
**Author**: Claude Code Analysis
**Reviewer**: Greg
```

### Build/Code References (When Applicable)

```markdown
**Build Date**: Nov 21 2025 @ 08:07:22
**Binary Location**: /path/to/binary
**Git Commit**: abc123def456
**Branch**: feature/branch-name
```

### Footer Section (Required)

```markdown
---

**Document Version**: 1.0
**Date**: 2025-11-21
**Last Updated**: 2025-11-21
**Status**: Ready for Implementation
```

---

## Document Types and Requirements

### Planning Documents
- [ ] Date (required)
- [ ] Version (required)
- [ ] Status (required)
- [ ] Author (required)
- [ ] Estimated timeline
- [ ] Implementation checklist

### Analysis Reports
- [ ] Date (required)
- [ ] Build information (required if analyzing logs/binaries)
- [ ] Log file references with dates
- [ ] Version (required)
- [ ] Reviewer (required)

### Implementation Summaries
- [ ] Date (required)
- [ ] Build date/time (required)
- [ ] Files modified with line numbers
- [ ] Testing status
- [ ] Version (required)

### Test Results
- [ ] Test date (required)
- [ ] Build date being tested (required)
- [ ] Log file name with date
- [ ] Results summary
- [ ] Next actions

---

## Why This Matters

**Timeline Reconstruction**:
- Correlate code changes with test results
- Understand sequence of fixes
- Identify which build was tested

**Version Control**:
- Match logs to specific builds
- Track when issues were fixed
- Avoid testing wrong version

**Debugging**:
- "Was this bug present in Nov 20 build?"
- "Which fix was applied when?"
- "Is this log from before or after the fix?"

**Audit Trail**:
- Who approved what when
- Decision history
- Implementation timeline

---

## Quick Reference Template

Copy/paste this at the top of every new document:

```markdown
# [Document Title]

**Date**: 2025-11-21
**Document Version**: 1.0
**Status**: Draft
**Author**: Claude Code Analysis

---

## [Content sections here]

---

**Document Version**: 1.0
**Date**: 2025-11-21
**Status**: [Current Status]
```

---

**This Checklist**:
- **Created**: 2025-11-21
- **Version**: 1.0
- **Location**: `.claude/documentation_checklist.md`
- **Purpose**: Quick reference for documentation standards
