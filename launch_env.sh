#!/usr/bin/env bash

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

# models get lower priority than ui
# - ui is ~5ms
# - modeld is 20ms
# - DM is 10ms
# in order to run ui at 60fps (16.67ms), we need to allow
# it to preempt the model workloads. we have enough
# headroom for this until ui is moved to the CPU.
export QCOM_PRIORITY=12

if [ -z "$AGNOS_VERSION" ]; then
  export AGNOS_VERSION="19.7"
fi

export STAGING_ROOT="/data/safe_staging"

# on AGNOS, /home is an ephemeral overlay (upperdir on tmpfs) that's wiped every
# reboot. uv defaults its managed-Python install dir and cache under $HOME, so a
# `uv sync` there works until the next reboot, then .venv/bin/python3 points at a
# now-missing interpreter and everything invoking it (e.g. capnpc) fails with
# "required file not found". Keep both on /data, which persists.
export UV_PYTHON_INSTALL_DIR="/data/uv_python"
export UV_CACHE_DIR="/data/uv_cache"
