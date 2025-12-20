#!/usr/bin/env python3
"""Setup script for OBD2 Vehicle Simulator."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="obd2-sim",
    version="1.0.0",
    author="Sierra Telecom",
    author_email="support@sierratelecom.com",
    description="OBD2 Vehicle Simulator for bench testing telematics gateways",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sierratelecom/obd2-sim",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8",
    install_requires=[
        "python-can>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "obd2_sim=obd2_sim.cli:main",
        ],
    },
)
