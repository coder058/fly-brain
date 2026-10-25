#!/usr/bin/env sh
# Fetch the FlyWire 630 connectivity that Shiu et al. (Nature 2024) simulated.
# Source: https://github.com/philshiu/Drosophila_brain_model (MIT). FlyWire data are subject
# to the FlyWire terms of use; they are not redistributed in this repository.
set -e
cd "$(dirname "$0")/.."
mkdir -p external
if [ ! -d external/Drosophila_brain_model ]; then
  git clone --depth 1 https://github.com/philshiu/Drosophila_brain_model external/Drosophila_brain_model
fi
ls -la external/Drosophila_brain_model/2023_03_23_connectivity_630_final.parquet
