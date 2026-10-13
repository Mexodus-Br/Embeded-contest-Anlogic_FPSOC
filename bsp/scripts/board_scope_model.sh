#!/bin/sh
# Identity and pure ARM model only. No GPIO motion enable/start.
set -eu
/usr/bin/bsp-readonly-check "$1"
test "$(uname -r)" = 6.1.111-rt42-bsp-sd1
test "$(zcat /proc/config.gz | sha256sum | cut -d' ' -f1)" = 81f7b75cb8e2f0901ef3dbd6eb78282db988031904dd1001ed709beb1120dbf1
sha256sum -c /etc/delta-scope/files.sha256
test ! -e /run/delta-scope.sock
echo ARM_GOLDEN_VALIDATION_BEGIN
DELTA_SCOPE_CONFIG=/etc/delta-scope/firmware_reference.cfg scope-unit
delta-model --config /etc/delta-scope/firmware_reference.cfg --batch < /etc/delta-scope/model-inputs.txt > /tmp/scope-model.jsonl
firmware-oracle < /etc/delta-scope/model-inputs.txt > /tmp/scope-oracle.jsonl
echo ARM_MODEL_JSON_BEGIN
cat /tmp/scope-model.jsonl
echo ARM_MODEL_JSON_END
echo ARM_ORACLE_JSON_BEGIN
cat /tmp/scope-oracle.jsonl
echo ARM_ORACLE_JSON_END
echo FIXED_MODEL_BEGIN
delta-scope model --xyz 0 0 -140
delta-scope model --xyz 5 0 -140
if delta-scope model --xyz nan 0 -140; then exit 1; fi
if delta-scope model --xyz 0 0 0; then exit 1; fi
if delta-scope model --xyz 1e100 0 -140; then exit 1; fi
echo ARM_MODELS_CAPTURED_NO_GPIO_MOTION
