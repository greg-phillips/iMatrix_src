i want your help to create a slash command, build_imatrix_client_prompt,  to create a prompt that will take as input a specification markdown file.
The contents of the file will be strutured ymal and use those details to create the full prompt to use for new software development.
Review these basic development prompts. 
1. ~iMatrix/iMatrix_Client/docs/ppp_connection_refactoring_plan.md
2. ~iMatrix/iMatrix_Client/docs/new_feature_ping_prompt.md
3. ~iMatrix/iMatrix_Client/docs/debug_network_issue_prompt_2.md 

Note the common structrure and the indepent for each one.
THink unltrahard and create a plan to create a slash command to perform this task. Provide extremely detailed information about the stucture and use of yaml the the slash command will use to create the new prompt.
Include how the new prompt is named from a yaml parameter.
Ask any questions.

Advanced Features

  1. Template Variables

  Support dynamic substitution:

  variables:
    project_root: "~/iMatrix/iMatrix_Client"
    log_dir: "${project_root}/logs"

  references:
    documentation:
      - "${project_root}/docs/api.md"

  2. Section Templates

  Reusable section definitions:

  section_templates:
    standard_deliverables:
      - "Create git branch"
      - "Build verification"
      - "Documentation updates"

  deliverables:
    steps:
      - use_template: "standard_deliverables"
      - "Additional custom step"

  3. Conditional Sections

  Include sections based on task type:

  task_type: "debug"  # or "feature", "refactor"

  # Only included if task_type == "debug"
  debug_specific:
    log_analysis: true
    mutex_tracking: true

  4. Multi-file References

  Support glob patterns:

  references:
    source_files:
      - pattern: "iMatrix/IMX_Platform/**/*.c"
        focus: ["networking", "cellular"]

  ---
  Questions for You

  Before I finalize this plan, I need your input on several design decisions:

  1. YAML Complexity Level

  - Simple: Flat structure, basic string/list fields (easier to write, less flexible)
  - Moderate: Nested structure as shown above (balanced)
  - Advanced: Template variables, conditionals, includes (most powerful, steeper learning curve)

     Recommendation: Start with Moderate, add Advanced features later

  2. Section Auto-Generation

     Should the command automatically include standard sections (Code Structure, Background, Hardware) if not explicitly provided, using defaults from CLAUDE.md?

     Recommendation: Yes, with ability to override

  3. Validation Strictness

  - Lenient: Missing optional fields just skip sections
  - Strict: Warn about missing commonly-used optional fields
  - Very Strict: Require all sections for completeness

     Recommendation: Strict with warnings

  4. Output Format Options

     Should the command support multiple output formats?
  - Markdown only (current plan)
  - Also support plain text
  - Also support HTML for web viewing

     Recommendation: Markdown only initially

  5. Interactive Mode

     Should the command support an interactive mode that prompts for missing required fields?

     Example:
  /build_imatrix_client_prompt specs/incomplete.yaml
  > Error: Required field 'title' is missing
  > Enter title: Add new feature
  > Generating prompt...

     Recommendation: Yes, very helpful for users

  6. Existing Prompt Conversion

     Should I create a reverse tool that can analyze existing .md prompts and generate YAML specs from them?

     Recommendation: Yes, useful for bootstrapping

  7. Prompt Name Generation

     If prompt_name is not provided in YAML, should it be auto-generated from:
  - title field (sanitized)
  - Timestamp + task type
  - Prompt user

Answers
1. Support all three levels with a directive in the ymal file to indicate YAML Complexity Level. When creating documentation create detailed examples of each case.
2. Yes, with ability to override
3. Strict with warnings
4. Markdown only initially
5. Yes, very helpful for users
6. Yes, useful for bootstrapping.
7. Auto-generate from title with confirmation

  ### Additional Questions:

  1. **YAML Library**: Should I use a specific YAML parsing approach in the slash command, or handle it as structured text?

  2. **Template Storage**: Should reusable templates (standard_imatrix_context.yaml) be stored in the repository or generated dynamically?

  3. **Validation Strictness**: Should I fail hard on warnings in non-interactive mode, or just display warnings and continue?

  4. **Output Location**: Confirmed as `~/iMatrix/iMatrix_Client/docs/` for generated prompts?

  5. **Version Control**: Should generated prompts include a comment header indicating they were auto-generated from YAML?

  Answers
  1. Use standard PyYAML
  2. tored in the repository
  3. fail hard on warnings in non-interactive mode
  4. ~/iMatrix/iMatrix_Client/docs/gen/
  5. yes
  