#!/usr/bin/env bash
# Run ON the Lightsail host after first SSH login.
set -euo pipefail
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip build-essential git rsync
mkdir -p ~/fly-lab
cd ~/fly-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install numpy scipy pandas pyarrow
echo "BOOTSTRAP_OK $(hostname) $(free -h | awk '/Mem:/{print $2}')"
