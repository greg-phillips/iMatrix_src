#!/usr/bin/env python3
"""
iMatrix Prompt Generator - Standalone Tool

Generates comprehensive Markdown development prompts from YAML specifications.
Supports three complexity levels: simple, moderate, advanced

Usage:
    python build_prompt.py <yaml_file>
    python build_prompt.py specs/examples/simple/quick_bug_fix.yaml

Author: iMatrix Development Team
Version: 1.0
Date: 2025-11-17
"""

import sys
import os
import yaml
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Constants
SCHEMA_VERSION = "1.0"
PROJECT_ROOT = Path.home() / "iMatrix" / "iMatrix_Client"
CLAUDE_MD_PATH = PROJECT_ROOT / "CLAUDE.md"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "gen"

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")

def print_error(msg: str):
    print(f"{Colors.FAIL}✗ ERROR:{Colors.ENDC} {msg}")

def print_warning(msg: str):
    print(f"{Colors.WARNING}⚠ WARNING:{Colors.ENDC} {msg}")

def print_info(msg: str):
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {msg}")

def print_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{msg}{Colors.ENDC}")


class PromptGenerator:
    """Main prompt generator class"""

    def __init__(self, yaml_file: str):
        self.yaml_file = Path(yaml_file)
        self.data = None
        self.complexity = "moderate"
        self.warnings = []
        self.auto_populated_sections = []

    def load_yaml(self) -> bool:
        """Load and parse YAML file"""
        try:
            if not self.yaml_file.exists():
                print_error(f"YAML file not found: {self.yaml_file}")
                return False

            with open(self.yaml_file, 'r') as f:
                self.data = yaml.safe_load(f)

            print_success(f"YAML parsed successfully: {self.yaml_file.name}")
            return True

        except yaml.YAMLError as e:
            print_error(f"Failed to parse YAML file")
            print(f"  {str(e)}")
            print("\nTips:")
            print("  - Check indentation (use spaces, not tabs)")
            print("  - Ensure colons have spaces after them")
            print("  - Quote strings containing special characters")
            return False

    def determine_complexity(self):
        """Determine complexity level from YAML"""
        self.complexity = self.data.get('complexity_level', 'moderate')
        if self.complexity not in ['simple', 'moderate', 'advanced']:
            print_warning(f"Invalid complexity_level '{self.complexity}', using 'moderate'")
            self.complexity = 'moderate'
        print_info(f"Complexity level: {self.complexity}")

    def process_variables(self) -> bool:
        """Process variable substitution (advanced mode)"""
        if self.complexity != 'advanced':
            return True

        variables = self.data.get('variables', {})
        if not variables:
            return True

        print_info(f"Processing {len(variables)} variables")

        # Resolve variables (handle nested dependencies)
        resolved = {}
        max_iterations = 10
        iteration = 0

        while len(resolved) < len(variables) and iteration < max_iterations:
            iteration += 1
            for key, value in variables.items():
                if key in resolved:
                    continue

                # Check if value contains unresolved variables
                if isinstance(value, str):
                    unresolved = re.findall(r'\$\{(\w+)\}', value)
                    if all(v in resolved for v in unresolved):
                        # All dependencies resolved, resolve this variable
                        resolved_value = value
                        for var in unresolved:
                            resolved_value = resolved_value.replace(f'${{{var}}}', resolved[var])
                        resolved[key] = resolved_value
                else:
                    resolved[key] = value

        if len(resolved) < len(variables):
            print_error("Circular variable dependencies detected")
            return False

        # Substitute variables throughout the data structure
        self._substitute_variables(self.data, resolved)
        print_success(f"Variables resolved: {len(resolved)} substitutions")
        return True

    def _substitute_variables(self, obj: Any, variables: Dict[str, str]):
        """Recursively substitute variables in data structure"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = self._substitute_variables(value, variables)
        elif isinstance(obj, list):
            return [self._substitute_variables(item, variables) for item in obj]
        elif isinstance(obj, str):
            for var_name, var_value in variables.items():
                obj = obj.replace(f'${{{var_name}}}', str(var_value))
        return obj

    def process_includes(self) -> bool:
        """Process include files (advanced mode)"""
        if self.complexity != 'advanced':
            return True

        includes = self.data.get('includes', [])
        if not includes:
            return True

        print_info(f"Processing {len(includes)} include files")

        # Load and merge include files
        for include_file in includes:
            include_path = PROJECT_ROOT / include_file
            if not include_path.exists():
                print_warning(f"Include file not found: {include_file}")
                continue

            try:
                with open(include_path, 'r') as f:
                    include_data = yaml.safe_load(f)

                # Merge (current data overrides includes)
                self._merge_dicts(include_data, self.data)
                self.data = include_data
                print_success(f"  Merged: {include_file}")

            except Exception as e:
                print_error(f"Failed to process include: {include_file}")
                print(f"  {str(e)}")
                return False

        return True

    def _merge_dicts(self, base: Dict, override: Dict):
        """Recursively merge dictionaries (override takes precedence)"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_dicts(base[key], value)
            else:
                base[key] = value

    def validate(self) -> bool:
        """Validate YAML structure and required fields"""
        print_header("Validation")

        # Required fields by complexity
        required_fields = {
            'simple': ['title', 'task'],
            'moderate': ['title', 'task'],
            'advanced': ['metadata', 'task']  # title is in metadata for advanced
        }

        required = required_fields[self.complexity]
        missing = []

        for field in required:
            if field not in self.data or not self.data[field]:
                missing.append(field)

        # For advanced mode, check metadata.title exists
        if self.complexity == 'advanced':
            if 'metadata' in self.data:
                if 'title' not in self.data['metadata'] or not self.data['metadata']['title']:
                    missing.append('metadata.title')

        if missing:
            print_error(f"Required fields missing: {', '.join(missing)}")
            print(f"  Complexity level: {self.complexity}")
            print(f"  Required fields: {', '.join(required)}")
            return False

        # Validate formats
        if 'prompt_name' in self.data:
            if not re.match(r'^[a-z0-9_]+$', self.data['prompt_name']):
                print_error("Invalid prompt_name: must match ^[a-z0-9_]+$")
                return False

        if 'date' in self.data:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', self.data['date']):
                self.warnings.append("Invalid date format (should be YYYY-MM-DD)")

        if 'branch' in self.data:
            if not re.match(r'^(feature|bugfix|refactor|debug)/[a-z0-9-]+$', self.data['branch']):
                self.warnings.append("Branch name doesn't match recommended pattern")

        # Show warnings
        if self.warnings:
            for warning in self.warnings:
                print_warning(warning)
            # Fail hard in non-interactive mode
            print_error("Validation failed (strict mode)")
            return False

        print_success("Validation passed")
        return True

    def auto_generate_fields(self):
        """Auto-generate missing fields"""
        print_header("Auto-Generation")

        # Get title from appropriate location based on complexity
        if self.complexity == 'advanced':
            title = self.data.get('metadata', {}).get('title', 'untitled')
        else:
            title = self.data.get('title', 'untitled')

        # Generate prompt_name from title
        if 'prompt_name' not in self.data or not self.data['prompt_name']:
            prompt_name = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')
            self.data['prompt_name'] = prompt_name
            print_success(f"Generated prompt_name: {prompt_name}")

        # Generate date
        if 'date' not in self.data or not self.data['date']:
            self.data['date'] = datetime.now().strftime('%Y-%m-%d')
            print_success(f"Generated date: {self.data['date']}")

        # Generate branch
        if 'branch' not in self.data or not self.data['branch']:
            # Detect type from task content
            task_str = str(self.data.get('task', '')).lower()
            if 'fix' in task_str or 'bug' in task_str:
                prefix = 'bugfix'
            elif 'refactor' in task_str:
                prefix = 'refactor'
            elif 'debug' in task_str:
                prefix = 'debug'
            else:
                prefix = 'feature'

            branch = f"{prefix}/{self.data['prompt_name'].replace('_', '-')}"
            self.data['branch'] = branch
            print_success(f"Generated branch: {branch}")

        # Generate plan_document
        if 'deliverables' not in self.data:
            self.data['deliverables'] = {}

        if 'plan_document' not in self.data['deliverables']:
            self.data['deliverables']['plan_document'] = f"docs/{self.data['prompt_name']}.md"
            print_success(f"Generated plan_document path")

    def auto_populate_from_claude_md(self):
        """Auto-populate standard sections from CLAUDE.md"""
        if self.complexity == 'simple':
            return  # Simple mode doesn't auto-populate

        auto_populate = self.data.get('project', {}).get('auto_populate_standard_info', True)
        if not auto_populate:
            return

        print_header("Auto-Population from CLAUDE.md")

        # Set defaults (in real implementation, would parse CLAUDE.md)
        defaults = {
            'project': {
                'core_library': 'iMatrix - Contains all core telematics functionality',
                'main_application': 'Fleet-Connect-1 - Main system management logic'
            },
            'hardware': {
                'processor': 'iMX6',
                'ram': '512MB',
                'flash': '512MB',
                'wifi_chipset': 'Combination Wi-Fi/Bluetooth chipset',
                'cellular_chipset': 'PLS62/63 from TELIT CINTERION using AAT Command set'
            },
            'user': {
                'name': 'Greg'
            }
        }

        # Merge defaults (existing values take precedence)
        for section, values in defaults.items():
            if section not in self.data:
                self.data[section] = {}
                self.auto_populated_sections.append(section)

            for key, value in values.items():
                if key not in self.data[section]:
                    self.data[section][key] = value

        if self.auto_populated_sections:
            print_success(f"Auto-populated: {', '.join(self.auto_populated_sections)}")

    def generate_markdown(self) -> str:
        """Generate markdown output based on complexity level"""
        print_header("Generating Markdown")

        if self.complexity == 'simple':
            return self._generate_simple_template()
        elif self.complexity == 'moderate':
            return self._generate_moderate_template()
        else:  # advanced
            return self._generate_advanced_template()

    def _generate_simple_template(self) -> str:
        """Generate simple complexity markdown"""
        md = []

        # Get title from appropriate location
        if self.complexity == 'advanced':
            title = self.data.get('metadata', {}).get('title', 'Untitled')
        else:
            title = self.data.get('title', 'Untitled')

        # Header comment
        md.append("<!--")
        md.append("AUTO-GENERATED PROMPT")
        md.append(f"Generated from: {self.yaml_file}")
        md.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"Schema version: {SCHEMA_VERSION}")
        md.append(f"Complexity level: {self.complexity}")
        md.append("")
        md.append("To modify this prompt, edit the source YAML file and regenerate.")
        md.append("-->")
        md.append("")

        # Title
        md.append(f"## Aim {title}")
        md.append("")
        md.append(f"**Date:** {self.data.get('date', 'N/A')}")
        md.append(f"**Branch:** {self.data.get('branch', 'N/A')}")
        md.append("")
        md.append("---")
        md.append("")

        # Standard code structure
        md.append("## Code Structure:")
        md.append("")
        md.append("iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).")
        md.append("")
        md.append("Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.")
        md.append("")

        # Background
        md.append("## Background")
        md.append("")
        md.append("The system is a telematics gateway supporting CAN BUS and various sensors.")
        md.append("The Hardware is based on an iMX6 processor with 512MB RAM and 512MB FLASH")
        md.append("The wifi communications uses a combination Wi-Fi/Bluetooth chipset")
        md.append("The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.")
        md.append("")
        md.append("The user's name is Greg")
        md.append("")
        md.append("use the template files as a base for any new files created")
        md.append("iMatrix/templates/blank.c")
        md.append("iMatrix/templates/blank.h")
        md.append("")
        md.append("Always create extensive comments using doxygen style")
        md.append("")
        md.append("**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**")
        md.append("")

        # Notes if provided
        if 'notes' in self.data:
            md.append("## Additional Notes")
            md.append("")
            for note in self.data['notes']:
                md.append(f"- {note}")
            md.append("")

        # Task
        md.append("## Task")
        md.append("")
        task = self.data['task']
        if isinstance(task, str):
            md.append(task)
        else:
            md.append(task.get('summary', ''))
            if 'description' in task:
                md.append("")
                md.append(task['description'])
        md.append("")

        # Files to modify
        if 'files_to_modify' in self.data:
            md.append("**Files to modify:**")
            for file in self.data['files_to_modify']:
                md.append(f"- {file}")
            md.append("")

        # Standard deliverables
        md.append("## Deliverables")
        md.append("")
        md.append("1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.")
        md.append(f"2. Detailed plan document, *** {self.data['deliverables']['plan_document']} ***, of all aspects and detailed todo list for me to review before commencing the implementation.")
        md.append("3. Once plan is approved implement and check off the items on the todo list as they are completed.")
        md.append("4. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found fix them immediately.")
        md.append("5. **Final build verification**: Before marking work complete, perform a final clean build to verify:")
        md.append("   - Zero compilation errors")
        md.append("   - Zero compilation warnings")
        md.append("   - All modified files compile successfully")
        md.append("   - The build completes without issues")
        md.append("6. Once I have determined the work is completed successfully add a concise description to the plan document of the work undertaken.")
        md.append("7. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.")
        md.append("8. Merge the branch back into the original branch.")
        md.append("9. Update all documents with relevant details")
        md.append("")

        # Footer
        md.append("---")
        md.append("")
        md.append("**Plan Created By:** Claude Code (via YAML specification)")
        md.append(f"**Source Specification:** {self.yaml_file}")
        md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(md)

    def _generate_moderate_template(self) -> str:
        """Generate moderate complexity markdown with comprehensive sections"""
        md = []

        title = self.data.get('title', 'Untitled')
        objective = self.data.get('objective', '')

        # Header comment
        md.append("<!--")
        md.append("AUTO-GENERATED PROMPT")
        md.append(f"Generated from: {self.yaml_file}")
        md.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"Schema version: {SCHEMA_VERSION}")
        md.append(f"Complexity level: {self.complexity}")
        md.append("")
        md.append("To modify this prompt, edit the source YAML file and regenerate.")
        md.append("-->")
        md.append("")

        # Title section
        md.append(f"## Aim {title}")
        if objective:
            md.append(objective)
        md.append("")
        md.append("Think ultrahard as you read and implement the following.")
        md.append("Stop and ask questions if any failure to find Background material")
        md.append("")

        # Metadata
        md.append(f"**Date:** {self.data.get('date', 'N/A')}")
        md.append(f"**Branch:** {self.data.get('branch', 'N/A')}")
        if objective:
            md.append(f"**Objective:** {objective}")
        md.append("")

        # Code Structure
        md.append("## Code Structure:")
        md.append("")
        project = self.data.get('project', {})
        if project.get('core_library'):
            md.append(f"iMatrix (Core Library): {project['core_library']}")
        else:
            md.append("iMatrix (Core Library): Contains all core telematics functionality (data logging, comms, peripherals).")
        md.append("")
        if project.get('main_application'):
            md.append(f"Fleet-Connect-1 (Main Application): {project['main_application']}")
        else:
            md.append("Fleet-Connect-1 (Main Application): Contains the main system management logic and utilizes the iMatrix API to handle data uploading to servers.")
        md.append("")

        # Additional project context
        if project.get('additional_context'):
            md.append(project['additional_context'])
            md.append("")

        # Background
        md.append("## Background")
        md.append("")
        md.append("The system is a telematics gateway supporting CAN BUS and various sensors.")

        hardware = self.data.get('hardware', {})
        processor = hardware.get('processor', 'iMX6')
        ram = hardware.get('ram', '512MB')
        flash = hardware.get('flash', '512MB')
        md.append(f"The Hardware is based on an {processor} processor with {ram} RAM and {flash} FLASH")
        md.append("The wifi communications uses a combination Wi-Fi/Bluetooth chipset")
        md.append("The Cellular chipset is a PLS62/63 from TELIT CINTERION using the AAT Command set.")
        md.append("")

        # Hardware additional notes
        if hardware.get('additional_notes'):
            for note in hardware['additional_notes']:
                md.append(f"- {note}")
            md.append("")

        user = self.data.get('user', {})
        user_name = user.get('name', 'Greg')
        md.append(f"The user's name is {user_name}")
        md.append("")

        # References
        references = self.data.get('references', {})
        if references.get('read_first'):
            md.append("Read and understand the following")
            md.append("")
            for ref in references['read_first']:
                md.append(f"{ref}")
            md.append("")

        if references.get('source_files'):
            md.append("**Source files to review:**")
            md.append("")
            for src in references['source_files']:
                md.append(f"- {src.get('path', '')}")
                if src.get('focus'):
                    md.append(f"  Focus on: {', '.join(src['focus'])}")
            md.append("")

        md.append("use the template files as a base for any new files created")
        md.append("iMatrix/templates/blank.c")
        md.append("iMatrix/templates/blank.h")
        md.append("")
        md.append("code runs on embedded system from: /home directory")
        md.append("")
        md.append("Always create extensive comments using doxygen style")
        md.append("")
        md.append("**Use the KISS principle - do not over-engineer. keep it simple and maintainable.**")
        md.append("")

        # Debug configuration (if present)
        debug = self.data.get('debug', {})
        if debug:
            md.append("## Debug Configuration")
            md.append("")
            if debug.get('log_directory'):
                md.append(f"Log files will be stored {debug['log_directory']}")
            if debug.get('flags'):
                md.append("Debug flags:")
                for flag in debug['flags']:
                    md.append(f"- {flag}")
            md.append("")

        # Task
        md.append("## Task")
        md.append("")
        task = self.data.get('task', {})

        if isinstance(task, str):
            md.append(task)
        else:
            if task.get('summary'):
                md.append(task['summary'])
                md.append("")

            # Requirements
            if task.get('requirements'):
                md.append("**Requirements:**")
                md.append("")
                for req in task['requirements']:
                    md.append(f"- {req}")
                md.append("")

            # Implementation notes
            if task.get('implementation_notes'):
                md.append("**Implementation Notes:**")
                md.append("")
                for note in task['implementation_notes']:
                    md.append(f"- {note}")
                md.append("")

            # Detailed specifications
            if task.get('detailed_specifications'):
                md.append("## Detailed Specifications")
                md.append("")
                for spec in task['detailed_specifications']:
                    section_name = spec.get('section', 'Details')
                    md.append(f"### {section_name}")
                    md.append("")
                    details = spec.get('details')
                    if isinstance(details, str):
                        md.append(details)
                    elif isinstance(details, list):
                        for detail in details:
                            md.append(f"- {detail}")
                    md.append("")

        md.append("")

        # Files to modify
        if 'files_to_modify' in self.data:
            md.append("**Files to modify:**")
            md.append("")
            for file in self.data['files_to_modify']:
                md.append(f"- {file}")
            md.append("")

        # Deliverables
        md.append("## Deliverables")
        md.append("")

        deliverables = self.data.get('deliverables', {})
        use_standard = deliverables.get('use_standard_workflow', True)

        if use_standard:
            md.append("1. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.")
            plan_doc = deliverables.get('plan_document', f"docs/{self.data['prompt_name']}_plan.md")
            md.append(f"2. Detailed plan document, *** {plan_doc} ***, of all aspects and detailed todo list for me to review before commencing the implementation.")
            md.append("3. Once plan is approved implement and check off the items on the todo list as they are completed.")
            md.append("4. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings. If compile errors or warnings are found fix them immediately.")
            md.append("5. **Final build verification**: Before marking work complete, perform a final clean build to verify:")
            md.append("   - Zero compilation errors")
            md.append("   - Zero compilation warnings")
            md.append("   - All modified files compile successfully")
            md.append("   - The build completes without issues")
            md.append("6. Once I have determined the work is completed successfully add a concise description to the plan document of the work undertaken.")
            md.append("7. Include in the update the number of tokens used, number of recompilations required for syntax errors, time taken in both elapsed and actual work time, time waiting on user responses to complete the feature.")
            md.append("8. Merge the branch back into the original branch.")
            md.append("9. Update all documents with relevant details")

        # Additional steps
        if deliverables.get('additional_steps'):
            md.append("")
            md.append("**Additional Steps:**")
            for step in deliverables['additional_steps']:
                md.append(f"- {step}")

        md.append("")

        # Questions
        questions = self.data.get('questions', [])
        if questions:
            md.append("## ASK ANY QUESTIONS needed to verify work requirements.")
            md.append("")
            md.append("Before I begin implementation, please provide guidance on:")
            md.append("")

            for i, q in enumerate(questions, 1):
                question = q.get('question', '')
                md.append(f"{i}. {question}")

            md.append("")
            md.append("Answers")
            for i, q in enumerate(questions, 1):
                answer = q.get('answer', '')
                md.append(f"{i}. {answer}")

            md.append("")

        # Footer
        md.append("---")
        md.append("")
        md.append("**Plan Created By:** Claude Code (via YAML specification)")
        md.append(f"**Source Specification:** {self.yaml_file}")
        md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(md)

    def _generate_advanced_template(self) -> str:
        """Generate advanced complexity markdown with all comprehensive sections"""
        md = []

        metadata = self.data.get('metadata', {})
        title = metadata.get('title', 'Untitled')
        objective = metadata.get('objective', '')
        date = metadata.get('date', self.data.get('date', 'N/A'))
        branch = metadata.get('branch', self.data.get('branch', 'N/A'))
        estimated_effort = metadata.get('estimated_effort', '')
        priority = metadata.get('priority', '')

        # Header comment
        md.append("<!--")
        md.append("AUTO-GENERATED PROMPT - ADVANCED COMPLEXITY")
        md.append(f"Generated from: {self.yaml_file}")
        md.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"Schema version: {SCHEMA_VERSION}")
        md.append(f"Complexity level: {self.complexity}")
        md.append("")
        md.append("To modify this prompt, edit the source YAML file and regenerate.")
        md.append("-->")
        md.append("")

        # Title with full metadata
        md.append(f"# {title}")
        md.append("")
        md.append(f"**Date:** {date}")
        md.append(f"**Branch:** {branch}")
        md.append(f"**Objective:** {objective}")
        if estimated_effort:
            md.append(f"**Estimated Effort:** {estimated_effort}")
        if priority:
            md.append(f"**Priority:** {priority}")
        md.append("")
        md.append("---")
        md.append("")

        # Executive Summary (auto-generated from objective)
        md.append("## Executive Summary")
        md.append("")
        if objective:
            md.append(objective)
        else:
            md.append("This document outlines the implementation plan for the proposed changes.")
        md.append("")

        # Additional context if provided
        project = self.data.get('project', {})
        if project.get('additional_context'):
            md.append(project['additional_context'])
            md.append("")

        md.append("---")
        md.append("")

        # Current Implementation Analysis
        current_state = self.data.get('current_state', {})
        if current_state:
            md.append("## Current Implementation Analysis")
            md.append("")

            # Workflow steps
            workflow = current_state.get('workflow', [])
            if workflow:
                md.append("### Workflow")
                md.append("")
                for i, step in enumerate(workflow, 1):
                    step_desc = step.get('step', '')
                    location = step.get('location', '')
                    md.append(f"{i}. **{step_desc}**")
                    if location:
                        md.append(f"   - Location: `{location}`")
                md.append("")

            # Problems
            problems = current_state.get('problems', [])
            if problems:
                md.append("### Problems")
                md.append("")
                for prob in problems:
                    issue = prob.get('issue', '')
                    description = prob.get('description', '')
                    severity = prob.get('severity', 'medium')
                    md.append(f"- **{issue}** (Severity: {severity})")
                    md.append(f"  - {description}")
                md.append("")

            # Working system evidence
            if current_state.get('working_system_evidence'):
                md.append("### Working System Evidence")
                md.append("")
                md.append(current_state['working_system_evidence'])
                md.append("")

            # Conclusion
            if current_state.get('conclusion'):
                md.append(f"**Conclusion:** {current_state['conclusion']}")
                md.append("")

            md.append("---")
            md.append("")

        # Proposed Architecture
        architecture = self.data.get('architecture', {})
        if architecture:
            md.append("## Proposed Architecture")
            md.append("")

            # New module
            new_module = architecture.get('new_module', {})
            if new_module:
                md.append(f"### New Module: {new_module.get('name', 'unnamed')}")
                md.append("")
                md.append(f"**Purpose:** {new_module.get('purpose', 'To be defined')}")
                md.append("")
                if new_module.get('location'):
                    md.append(f"**Location:** `{new_module['location']}`")
                    md.append("")

                responsibilities = new_module.get('responsibilities', [])
                if responsibilities:
                    md.append("**Responsibilities:**")
                    for resp in responsibilities:
                        md.append(f"- {resp}")
                    md.append("")

            # Data structures
            data_structures = architecture.get('data_structures', [])
            if data_structures:
                md.append("### Data Structures")
                md.append("")
                for ds in data_structures:
                    ds_name = ds.get('name', 'unnamed')
                    ds_type = ds.get('type', 'struct')
                    ds_desc = ds.get('description', '')
                    md.append(f"#### {ds_name} ({ds_type})")
                    md.append("")
                    if ds_desc:
                        md.append(ds_desc)
                        md.append("")

                    # Code block for struct/enum definition
                    if ds.get('values'):  # enum
                        md.append("```c")
                        md.append(f"typedef enum {{")
                        for val in ds['values']:
                            md.append(f"    {val},")
                        md.append(f"}} {ds_name};")
                        md.append("```")
                        md.append("")
                    elif ds.get('fields'):  # struct
                        md.append("```c")
                        md.append(f"typedef struct {{")
                        for field_name, field_type in ds['fields'].items():
                            md.append(f"    {field_type} {field_name};")
                        md.append(f"}} {ds_name};")
                        md.append("```")
                        md.append("")

            md.append("---")
            md.append("")

        # Implementation Phases
        task = self.data.get('task', {})
        phases = task.get('phases', [])
        if phases:
            md.append("## Implementation Phases")
            md.append("")

            for phase in phases:
                phase_num = phase.get('phase', 1)
                phase_name = phase.get('name', f'Phase {phase_num}')
                phase_tasks = phase.get('tasks', [])
                deliverable = phase.get('deliverable', '')

                md.append(f"### Phase {phase_num}: {phase_name}")
                md.append("")

                if phase_tasks:
                    md.append("**Tasks:**")
                    for task_item in phase_tasks:
                        md.append(f"- [ ] {task_item}")
                    md.append("")

                if deliverable:
                    md.append(f"**Deliverable:** {deliverable}")
                    md.append("")

            md.append("---")
            md.append("")

        # Design Decisions & Rationale (from conditional_sections)
        conditional = self.data.get('conditional_sections', {})
        when_refactoring = conditional.get('when_refactoring', {})

        design_decisions = when_refactoring.get('design_decisions', [])
        if design_decisions:
            md.append("## Design Decisions & Rationale")
            md.append("")

            for decision in design_decisions:
                decision_name = decision.get('decision', 'Unnamed Decision')
                rationale = decision.get('rationale', '')

                md.append(f"### {decision_name}")
                md.append("")
                md.append(rationale.strip())
                md.append("")

            md.append("---")
            md.append("")

        # Risk Mitigation
        risk_mitigation = when_refactoring.get('risk_mitigation', [])
        if risk_mitigation:
            md.append("## Risk Mitigation")
            md.append("")
            md.append("| Risk | Mitigation |")
            md.append("|------|------------|")

            for risk_item in risk_mitigation:
                risk = risk_item.get('risk', '')
                mitigation = risk_item.get('mitigation', '')
                md.append(f"| {risk} | {mitigation} |")

            md.append("")
            md.append("---")
            md.append("")

        # Success Criteria
        success_criteria = self.data.get('success_criteria', {})
        if success_criteria:
            md.append("## Success Criteria")
            md.append("")

            functional = success_criteria.get('functional', [])
            if functional:
                md.append("### Functional Requirements")
                md.append("")
                for criterion in functional:
                    md.append(f"- {criterion}")
                md.append("")

            quality = success_criteria.get('quality', [])
            if quality:
                md.append("### Quality Requirements")
                md.append("")
                for criterion in quality:
                    md.append(f"- {criterion}")
                md.append("")

            performance = success_criteria.get('performance', [])
            if performance:
                md.append("### Performance Requirements")
                md.append("")
                for criterion in performance:
                    md.append(f"- {criterion}")
                md.append("")

            md.append("---")
            md.append("")

        # Deliverables with metrics
        deliverables = self.data.get('deliverables', {})
        md.append("## Deliverables")
        md.append("")

        use_standard = deliverables.get('use_standard_workflow', True)
        if use_standard:
            plan_doc = deliverables.get('plan_document', f"docs/{self.data['prompt_name']}.md")
            md.append(f"1. **Plan Document:** {plan_doc}")
            md.append("2. Make a note of the current branches for iMatrix and Fleet-Connect-1 and create new git branches for any work created.")
            md.append("3. Detailed plan document with all aspects and detailed todo list for review before commencing implementation.")
            md.append("4. Once plan is approved implement and check off the items on the todo list as they are completed.")
            md.append("5. **Build verification**: After every code change run the linter and build the system to ensure there are no compile errors or warnings.")
            md.append("6. **Final build verification**: Before marking work complete, perform a final clean build to verify:")
            md.append("   - Zero compilation errors")
            md.append("   - Zero compilation warnings")
            md.append("   - All modified files compile successfully")
            md.append("7. Once work is completed successfully add a concise description to the plan document of the work undertaken.")
            md.append("8. Update all documents with relevant details")
            md.append("")

        # Additional deliverables
        additional_deliverables = deliverables.get('additional_deliverables', [])
        if additional_deliverables:
            md.append("**Additional Deliverables:**")
            for item in additional_deliverables:
                md.append(f"- {item}")
            md.append("")

        # Metrics
        metrics = deliverables.get('metrics', [])
        if metrics:
            md.append("**Metrics to Track:**")
            for metric in metrics:
                md.append(f"- {metric}")
            md.append("")

        md.append("---")
        md.append("")

        # Special Instructions
        special_instructions = self.data.get('special_instructions', {})
        if special_instructions:
            md.append("## Special Instructions")
            md.append("")

            pre_impl = special_instructions.get('pre_implementation', [])
            if pre_impl:
                md.append("### Pre-Implementation Steps")
                md.append("")
                for step in pre_impl:
                    md.append(f"- {step}")
                md.append("")

            system_files = special_instructions.get('system_files_required', [])
            if system_files:
                md.append("### System Files Required")
                md.append("")
                md.append("The following files must exist on the target system:")
                md.append("")
                for file_info in system_files:
                    path = file_info.get('path', '')
                    desc = file_info.get('description', '')
                    md.append(f"- **`{path}`** - {desc}")
                md.append("")

            md.append("---")
            md.append("")

        # Questions
        questions = self.data.get('questions', [])
        if questions:
            md.append("## Questions")
            md.append("")
            md.append("The following questions should be addressed before or during implementation:")
            md.append("")

            for q in questions:
                question = q.get('question', '')
                suggested_answer = q.get('suggested_answer', '')
                answer = q.get('answer', '')

                md.append(f"**Q:** {question}")
                if suggested_answer:
                    md.append(f"- Suggested: {suggested_answer}")
                if answer:
                    md.append(f"- **Answer:** {answer}")
                else:
                    md.append(f"- **Answer:** _To be determined_")
                md.append("")

            md.append("---")
            md.append("")

        # Footer
        md.append("**Plan Created By:** Claude Code (via YAML specification)")
        md.append(f"**Source Specification:** {self.yaml_file}")
        md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if metadata.get('estimated_effort'):
            md.append(f"**Estimated Effort:** {metadata['estimated_effort']}")
        md.append("")
        md.append("---")

        return "\n".join(md)

    def write_output(self, content: str) -> bool:
        """Write generated markdown to output file"""
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Generate output filename
        output_file = OUTPUT_DIR / f"{self.data['prompt_name']}.md"

        # Check if file exists
        if output_file.exists():
            print_warning(f"Output file already exists: {output_file}")
            print("  Overwriting...")

        try:
            with open(output_file, 'w') as f:
                f.write(content)

            print_success(f"Generated: {output_file}")
            print_info(f"  Lines: {len(content.splitlines())}")
            print_info(f"  Size: {len(content)} bytes")
            return True

        except Exception as e:
            print_error(f"Failed to write output file: {e}")
            return False

    def generate(self) -> bool:
        """Main generation pipeline"""
        print_header(f"iMatrix Prompt Generator v{SCHEMA_VERSION}")
        print_info(f"Input: {self.yaml_file}")
        print()

        # Step 1: Load YAML
        if not self.load_yaml():
            return False

        # Step 2: Determine complexity
        self.determine_complexity()

        # Step 3: Process advanced features
        if not self.process_variables():
            return False

        if not self.process_includes():
            return False

        # Step 4: Auto-populate
        self.auto_populate_from_claude_md()

        # Step 5: Auto-generate missing fields
        self.auto_generate_fields()

        # Step 6: Validate
        if not self.validate():
            return False

        # Step 7: Generate markdown
        content = self.generate_markdown()

        # Step 8: Write output
        if not self.write_output(content):
            return False

        # Success summary
        print()
        print_header("✓ Generation Complete")
        print_info(f"Output: {OUTPUT_DIR / self.data['prompt_name']}.md")

        if self.auto_populated_sections:
            print_info(f"Auto-populated: {', '.join(self.auto_populated_sections)}")

        print()
        print("Next steps:")
        print(f"  1. Review: cat {OUTPUT_DIR / self.data['prompt_name']}.md")
        print("  2. Use the prompt with Claude Code for implementation")
        print()

        return True


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <yaml_spec_file>")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} specs/examples/simple/quick_bug_fix.yaml")
        print(f"  {sys.argv[0]} specs/my_feature.yaml")
        sys.exit(1)

    yaml_file = sys.argv[1]

    generator = PromptGenerator(yaml_file)
    success = generator.generate()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
