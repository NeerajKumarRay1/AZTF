# AI-Driven Next-Generation Firewall (NGFW)

An AI-driven Next-Generation Firewall for dynamic threat detection and Zero Trust enforcement. The project combines real-time network traffic analysis, signature-based filtering, ensemble machine learning classifications, and automated firewall rules insertion in WSL2.

## Project Structure

- `setup_env.sh` - Installs Miniconda and sets up the Python 3.10 virtual environment inside WSL.
- `download_data.py` - Script to acquire intrusion detection datasets (CICIDS2017, UNSW-NB15, NSL-KDD).
- `preprocess.py` - Unified data processing pipeline (merging, SMOTE, scaling, train-test splits).
- `train_models.py` - Trains and serializes Random Forest, XGBoost, and Isolation Forest models.
- `models/` - Directory storing serialized models and scaler artifacts.
- `data/` - Directory storing raw and processed datasets.

## Requirements

- Windows 10/11 with WSL2 (Ubuntu 22.04 or newer)
- Python 3.10 (managed via Miniconda in WSL)

## Getting Started

### 1. Set Up Environment
Run the environment setup script inside your WSL terminal to install Miniconda and all dependencies:
```bash
./setup_env.sh
```

### 2. Activate the Environment
Always activate the conda environment before running python scripts:
```bash
source ~/miniconda3/etc/profile.d/conda.sh && conda activate ai-ngfw
```

### 3. Download Benchmark Datasets
```bash
python download_data.py
```

### 4. Preprocess Data
```bash
python preprocess.py
```

### 5. Train Threat Detection Models
```bash
python train_models.py
```
