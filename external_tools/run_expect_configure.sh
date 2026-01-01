#!/bin/bash
set -e

cd /home/greg/iMatrix/iMatrix_Client/external_tools/build/expect-build
rm -rf *

export CC=/opt/qconnect_sdk_musl/bin/arm-linux-gcc
export CFLAGS="--sysroot=/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot -O2 -fPIC"
export LDFLAGS="--sysroot=/opt/qconnect_sdk_musl/arm-buildroot-linux-musleabihf/sysroot"

../../expect/configure \
    --host=arm-linux \
    --build=x86_64-linux-gnu \
    --prefix=/home/greg/iMatrix/iMatrix_Client/external_tools/build/install \
    --with-tcl=/home/greg/iMatrix/iMatrix_Client/external_tools/build/tcl-build \
    --with-tclinclude=/home/greg/iMatrix/iMatrix_Client/external_tools/tcl8.6.13/generic \
    --enable-shared
