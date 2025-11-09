# Quick Build Reference

Convenient build scripts for the iMatrix project.

## Build Scripts

All scripts are in the root `iMatrix_Client/` directory:

### Primary Build Scripts

```bash
./build_fleet_connect.sh    # Build Fleet-Connect-1 application (most common)
./build_imatrix.sh          # Build iMatrix library only
./build_all.sh              # Build both iMatrix + Fleet-Connect-1
./rebuild_fleet_connect.sh  # Clean rebuild of Fleet-Connect-1
./clean_all.sh              # Remove all build artifacts
```

### Quick Commands

**Most common workflow:**
```bash
# Build and run Fleet-Connect
./build_fleet_connect.sh
cd Fleet-Connect-1/build
./FC-1
```

**Full rebuild:**
```bash
./rebuild_fleet_connect.sh
```

**Clean everything:**
```bash
./clean_all.sh
```

## Manual CMake Commands

If you prefer manual control:

### iMatrix Library
```bash
cd iMatrix
cmake .
make -j4
```

### Fleet-Connect-1
```bash
cd Fleet-Connect-1
cmake . -DENABLE_TESTING=OFF
make FC-1 -j4
```

### Clean Build
```bash
cd Fleet-Connect-1
rm -rf build CMakeCache.txt CMakeFiles Makefile
cmake . -DENABLE_TESTING=OFF
make FC-1 -j4
```

## Testing Thread Tracking

After building, run Fleet-Connect and test the new `threads` command:

```bash
cd Fleet-Connect-1/build
./FC-1

# In the CLI prompt:
threads           # Table view of all threads + timers
threads -v        # Detailed view
threads -j        # JSON output
threads -T        # Timers only
threads -t -v     # Threads only, detailed
threads -h        # Help
```

## Current Branches

The thread tracking feature is on these branches:
- iMatrix: `feature/thread-tracking`
- Fleet-Connect-1: `feature/thread-tracking`

## Build Issues

If you encounter mbedtls errors, these are pre-existing and not related to the thread tracking implementation. The thread tracking code compiles successfully.
