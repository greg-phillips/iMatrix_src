# Call Graph Documentation

## Overview

Call graphs provide visual representations of function relationships in the codebase, showing which functions call which other functions. This documentation explains how to generate and interpret call graphs for the iMatrix and Fleet-Connect-1 projects.

## Types of Call Graphs

### 1. Call Graph (cgraph)
Shows all functions that are called by a specific function.
- **Filename pattern**: `*_cgraph.svg`
- **Direction**: Top-down (parent → children)
- **Use case**: Understanding what a function does by seeing what it calls

### 2. Caller Graph (icgraph)
Shows all functions that call a specific function.
- **Filename pattern**: `*_icgraph.svg`
- **Direction**: Bottom-up (children → parent)
- **Use case**: Understanding impact analysis - what will be affected if you change this function

## Prerequisites

To generate call graphs, you need:

1. **Doxygen** (version 1.8.0 or higher)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install doxygen
   
   # macOS
   brew install doxygen
   
   # RHEL/CentOS
   sudo yum install doxygen
   ```

2. **Graphviz** (for graph visualization)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install graphviz
   
   # macOS
   brew install graphviz
   
   # RHEL/CentOS
   sudo yum install graphviz
   ```

## Generating Call Graphs

### Automatic Generation

Use the provided script:
```bash
cd /home/greg/iMatrix_src
./scripts/generate_doxygen_docs.sh
```

This will:
- Generate documentation for both iMatrix and Fleet-Connect-1
- Create call graphs for all documented functions
- Output HTML documentation with embedded graphs

### Manual Generation

For a specific project:
```bash
cd /home/greg/iMatrix_src/iMatrix
doxygen Doxyfile

# Or for Fleet-Connect-1
cd /home/greg/iMatrix_src/Fleet-Connect-1
doxygen Doxyfile
```

### Using CMake

If you're using the CMake build system:
```bash
cd /home/greg/iMatrix_src/iMatrix/build
cmake ..
make docs

# Or for Fleet-Connect-1
cd /home/greg/iMatrix_src/Fleet-Connect-1/build
cmake ..
make docs
```

## Viewing Call Graphs

### HTML Documentation

Open the generated HTML documentation:
- iMatrix: `file:///home/greg/iMatrix_src/iMatrix/docs/doxygen/html/index.html`
- Fleet-Connect-1: `file:///home/greg/iMatrix_src/Fleet-Connect-1/docs/doxygen/html/index.html`

Navigate to any function documentation to see its call graphs.

### Standalone SVG Files

Call graphs are generated as SVG files in:
- `docs/doxygen/html/*_cgraph.svg`
- `docs/doxygen/html/*_icgraph.svg`

You can open these directly in a web browser or image viewer.

## Interpreting Call Graphs

### Graph Elements

- **Nodes**: Represent functions
  - Rectangular boxes: Regular functions
  - Rounded boxes: External/system functions
  - Different colors indicate different modules

- **Edges**: Represent function calls
  - Solid arrows: Direct function calls
  - Dashed arrows: Indirect calls (through function pointers)
  - Arrow direction: From caller to callee

### Example Analysis

For a function like `process_obd2()`:

**Call Graph** (`process_obd2_cgraph.svg`) shows:
```
process_obd2()
├── get_available_pids()
├── process_pid_data()
├── decode_can_message()
└── save_obd2_value()
```

**Caller Graph** (`process_obd2_icgraph.svg`) shows:
```
main_loop()
└── process_obd2()
```

## Key Functions to Examine

### iMatrix Core Functions
1. **main()** - Entry point, shows initialization sequence
2. **coap_xmit()** - CoAP message transmission flow
3. **process_coap_msg()** - CoAP message processing
4. **ble_mgr_process()** - BLE event processing
5. **imx_data_upload()** - Data upload to cloud

### Fleet-Connect-1 Core Functions
1. **process_obd2()** - OBD2 state machine
2. **can_msg_process()** - CAN message processing
3. **i15765_tx_app()** - ISO-TP message transmission
4. **decode_can_message()** - CAN signal extraction

## Advanced Usage

### Filtering Call Graphs

Modify the Doxyfile to control graph complexity:

```
# Limit graph depth
MAX_DOT_GRAPH_DEPTH = 3

# Include only certain files
INCLUDE_PATH = src/core src/obd2

# Exclude test files
EXCLUDE_PATTERNS = */test/* */tests/*
```

### Generating Specific Graphs

To generate graphs for specific functions only:

1. Use the `\callgraph` and `\callergraph` commands in comments:
```c
/**
 * @brief Process OBD2 messages
 * \callgraph
 * \callergraph
 */
void process_obd2() {
    // ...
}
```

2. Set in Doxyfile:
```
CALL_GRAPH = NO
CALLER_GRAPH = NO
```

This will generate graphs only for functions with explicit commands.

## Alternative Tools

### 1. cflow
Generates text-based call graphs:
```bash
cflow --tree --depth=3 *.c
```

### 2. egypt
Generates call graphs using GCC RTL dumps:
```bash
gcc -fdump-rtl-expand *.c
egypt *.expand | dot -Tsvg -o callgraph.svg
```

### 3. CodeViz
Perl-based tool for call graph generation:
```bash
genfull -g full.graph
gengraph -f main -d 3 -g full.graph | dot -Tsvg -o main.svg
```

## Troubleshooting

### No Graphs Generated

1. **Check Graphviz installation**:
   ```bash
   dot -V
   ```

2. **Verify Doxyfile settings**:
   ```
   HAVE_DOT = YES
   CALL_GRAPH = YES
   CALLER_GRAPH = YES
   ```

3. **Check for errors**:
   ```bash
   doxygen Doxyfile 2>&1 | grep -i error
   ```

### Graphs Too Complex

1. Reduce depth:
   ```
   MAX_DOT_GRAPH_DEPTH = 2
   ```

2. Use clustering:
   ```
   UML_LOOK = YES
   ```

3. Filter by directory:
   ```
   INCLUDE_PATH = src/core
   ```

### Performance Issues

For large codebases:
1. Use parallel processing:
   ```
   DOT_NUM_THREADS = 4
   ```

2. Generate graphs on-demand:
   ```
   DOT_GRAPH_MAX_NODES = 50
   ```

## Best Practices

1. **Start with key functions**: Begin analysis with main entry points
2. **Use both graph types**: cgraph for implementation, icgraph for impact
3. **Combine with documentation**: Use graphs alongside code comments
4. **Regular updates**: Regenerate graphs after significant changes
5. **Module-level analysis**: Generate graphs for entire modules to understand architecture

## Integration with Development Workflow

1. **Code Reviews**: Include call graphs for complex changes
2. **Refactoring**: Use caller graphs to assess impact
3. **Documentation**: Embed key graphs in design documents
4. **Debugging**: Trace execution paths using call graphs
5. **Onboarding**: Help new developers understand code structure