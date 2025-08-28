# iMatrix Source Code Repository

This repository contains the main development environment for the iMatrix project, including test scripts, documentation, and build configurations.

## Project Structure

```
iMatrix_Client/
├── Fleet-Connect-1/        # Fleet Connect gateway application (separate git repo)
├── iMatrix/               # Core iMatrix embedded system code (separate git repo)
├── iMatrix-Android-Mobile-App/  # Android mobile application (separate git repo)
├── iMatrix-Web-UI/        # Web user interface (separate git repo)
├── imatrix-node-backend/  # Node.js backend server (separate git repo)
├── mbedtls/               # MbedTLS cryptography library (separate git repo)
├── test_scripts/          # Test scripts and utilities
├── test_results/          # Test execution results
├── docs/                  # Project documentation
├── scripts/               # Build and utility scripts
└── build/                 # Build output directory
```

## Setting Up Development Environment

### Prerequisites

- Linux development environment (Ubuntu 20.04+ or WSL2)
- GCC compiler toolchain
- CMake 3.10+
- Python 3.8+
- Node.js 14+ (for web components)
- Git

### Initial Setup

1. Clone this repository:
```bash
git clone <repository-url> iMatrix_Client
cd iMatrix_Client
```

2. Initialize submodule repositories (if needed):
Each subdirectory with its own git repository needs to be cloned separately:

```bash
# Clone the individual repositories
git clone <fleet-connect-repo-url> Fleet-Connect-1
git clone <imatrix-core-repo-url> iMatrix
git clone <android-app-repo-url> iMatrix-Android-Mobile-App
git clone <web-ui-repo-url> iMatrix-Web-UI
git clone <node-backend-repo-url> imatrix-node-backend
git clone <mbedtls-repo-url> mbedtls
```

3. Set up build environment:
```bash
cd test_scripts
cmake .
make
```

## Building

### Test Scripts
```bash
cd test_scripts
make
```

### Individual Components
Each component has its own build process. Refer to the README files in each subdirectory.

## Testing

Run the test suite:
```bash
cd test_scripts
./run_tiered_storage_tests.sh
```

## Project Components

### Core Components
- **iMatrix**: Core embedded system functionality including memory management, CAN bus, networking
- **Fleet-Connect-1**: Gateway application for vehicle connectivity
- **test_scripts**: Comprehensive test suite for memory management and system functionality

### User Interfaces
- **iMatrix-Android-Mobile-App**: React Native mobile application
- **iMatrix-Web-UI**: React-based web dashboard
- **imatrix-node-backend**: Node.js API backend server

### Libraries
- **mbedtls**: Cryptography and TLS library

## Development Notes

- Each major component maintains its own git repository
- This parent repository tracks integration points and shared test scripts
- Sensitive files (certificates, keys) are excluded via .gitignore
- Build artifacts are not tracked in version control

## Documentation

- Project documentation is in the `docs/` directory
- Component-specific documentation is in each component's directory
- API documentation can be generated using Doxygen

## License

[Specify your license here]

## Contact

[Add contact information]