#!/bin/bash
set -e

echo "=== Setting up Miniconda and Python 3.10 Environment ==="

MINICONDA_DIR="$HOME/miniconda3"
INSTALLER_PATH="/tmp/miniconda.sh"

if [ ! -d "$MINICONDA_DIR" ]; then
    echo "Downloading Miniconda..."
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O "$INSTALLER_PATH"
    echo "Installing Miniconda..."
    bash "$INSTALLER_PATH" -b -p "$MINICONDA_DIR"
    rm "$INSTALLER_PATH"
    echo "Miniconda installed successfully at $MINICONDA_DIR."
else
    echo "Miniconda is already installed at $MINICONDA_DIR."
fi

# Initialize conda for the shell session
source "$MINICONDA_DIR/etc/profile.d/conda.sh"

# Configure channels: remove defaults and add conda-forge
echo "Configuring conda channels..."
conda config --remove channels defaults || true
conda config --add channels conda-forge || true

# Recreate conda environment to ensure pip is installed
echo "Removing existing environment if any..."
conda env remove -n ai-ngfw -y || true

echo "Creating conda environment 'ai-ngfw' with Python 3.10 and pip..."
conda create -n ai-ngfw -c conda-forge --override-channels python=3.10 pip -y

ENV_PIP="$MINICONDA_DIR/envs/ai-ngfw/bin/pip"

echo "Installing project dependencies using $ENV_PIP..."
"$ENV_PIP" install --upgrade pip

# Install dependencies
"$ENV_PIP" install scikit-learn xgboost tensorflow pandas numpy flask fastapi uvicorn pyjwt bcrypt joblib imbalanced-learn scapy python-dotenv websockets pytest black flake8 jupyter

echo "=== Setup Completed Successfully ==="
echo "To activate the environment in the future, run:"
echo "source ~/miniconda3/etc/profile.d/conda.sh && conda activate ai-ngfw"
