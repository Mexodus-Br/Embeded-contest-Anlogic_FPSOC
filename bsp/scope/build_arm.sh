#!/bin/bash
set -euo pipefail
export LC_ALL=C
cd "${TASK:-$HOME/embedded-bsp-scope}"
mkdir -p build logs
exec > >(tee logs/arm-build.log) 2>&1
CXX=$HOME/embedded-bsp/vendor/tools/aarch64-linux/bin/aarch64-linux-gnu-g++
flags=(-std=c++17 -O0 -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off -static-libstdc++ -static-libgcc)
"$CXX" --version
set -x
"$CXX" "${flags[@]}" golden_model/src/model.cpp golden_model/src/main.cpp -o build/delta-model
"$CXX" "${flags[@]}" -Igolden_model/tests -Igolden_model/baseline golden_model/tests/oracle.cpp golden_model/baseline/robotGeometry.cpp golden_model/baseline/RampsStepper.cpp -o build/firmware-oracle
"$CXX" "${flags[@]}" -Werror -pthread -Igolden_model/src -Ibsp/motion golden_model/src/model.cpp bsp/scope/delta_scope.cpp -o build/delta-scope
"$CXX" "${flags[@]}" -Werror -pthread -Igolden_model/src -Ibsp/motion golden_model/src/model.cpp bsp/scope/unit_scope.cpp -o build/scope-unit
g++ -std=c++17 -O0 -Wall -Wextra -Wpedantic -Werror -fno-fast-math -ffp-contract=off -pthread -Igolden_model/src -Ibsp/motion golden_model/src/model.cpp bsp/scope/unit_scope.cpp -o build/scope-unit-host
build/scope-unit-host > logs/unit-host.log
sha256sum build/delta-model build/firmware-oracle build/delta-scope golden_model/configs/firmware_reference.cfg
file build/delta-model build/delta-scope
