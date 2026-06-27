import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
import joblib

def load_nsl_kdd(path):
    print("Loading NSL-KDD...")
    cols = [
        'duration', 'protocol_type', 'service', 'flag', 'src_bytes', 'dst_bytes',
        'land', 'wrong_fragment', 'urgent', 'hot', 'num_failed_logins', 'logged_in',
        'num_compromised', 'root_shell', 'su_attempted', 'num_root', 'num_file_creations',
        'num_shells', 'num_access_files', 'num_outbound_cmds', 'is_host_login',
        'is_guest_login', 'count', 'srv_count', 'serror_rate', 'srv_serror_rate',
        'rerror_rate', 'srv_rerror_rate', 'same_srv_rate', 'diff_srv_rate',
        'srv_diff_host_rate', 'dst_host_count', 'dst_host_srv_count',
        'dst_host_same_srv_rate', 'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate',
        'dst_host_srv_diff_host_rate', 'dst_host_serror_rate', 'dst_host_srv_serror_rate',
        'dst_host_rerror_rate', 'dst_host_srv_rerror_rate', 'label', 'difficulty'
    ]
    
    # Read files if they exist
    train_file = os.path.join(path, "KDDTrain+.txt")
    test_file = os.path.join(path, "KDDTest+.txt")
    
    dfs = []
    if os.path.exists(train_file):
        dfs.append(pd.read_csv(train_file, names=cols, header=None))
    if os.path.exists(test_file):
        dfs.append(pd.read_csv(test_file, names=cols, header=None))
        
    if not dfs:
        raise FileNotFoundError("NSL-KDD files not found.")
        
    df = pd.concat(dfs, ignore_index=True)
    
    # Map protocol to numbers
    proto_map = {'tcp': 6, 'udp': 17, 'icmp': 1}
    df['protocol'] = df['protocol_type'].map(proto_map).fillna(0)
    
    # Map label: normal is 0, anything else is 1
    df['label'] = df['label'].apply(lambda x: 0 if str(x).strip().startswith('normal') else 1)
    
    # Select and rename core features
    df['src_pkts'] = df['count']
    df['dst_pkts'] = df['srv_count']
    df['rate'] = (df['src_pkts'] + df['dst_pkts']) / (df['duration'] + 1e-6)
    
    selected_cols = {
        'duration': 'duration',
        'protocol': 'protocol',
        'src_bytes': 'src_bytes',
        'dst_bytes': 'dst_bytes',
        'src_pkts': 'src_pkts',
        'dst_pkts': 'dst_pkts',
        'rate': 'rate',
        'label': 'label'
    }
    
    return df[list(selected_cols.keys())].rename(columns=selected_cols)

def load_unsw_nb15(path):
    print("Loading UNSW-NB15...")
    train_file = os.path.join(path, "UNSW_NB15_training-set.csv")
    test_file = os.path.join(path, "UNSW_NB15_testing-set.csv")
    
    dfs = []
    if os.path.exists(train_file):
        dfs.append(pd.read_csv(train_file))
    if os.path.exists(test_file):
        dfs.append(pd.read_csv(test_file))
        
    if not dfs:
        raise FileNotFoundError("UNSW-NB15 files not found.")
        
    df = pd.concat(dfs, ignore_index=True)
    
    # Clean up column names
    df.columns = df.columns.str.strip()
    
    # Map protocol to numbers
    proto_map = {'tcp': 6, 'udp': 17, 'icmp': 1}
    df['protocol'] = df['proto'].str.lower().map(proto_map).fillna(0)
    
    selected_cols = {
        'dur': 'duration',
        'protocol': 'protocol',
        'sbytes': 'src_bytes',
        'dbytes': 'dst_bytes',
        'spkts': 'src_pkts',
        'dpkts': 'dst_pkts',
        'rate': 'rate',
        'label': 'label'
    }
    
    return df[list(selected_cols.keys())].rename(columns=selected_cols)

def load_cicids2017(path):
    print("Loading CICIDS2017...")
    files = [
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"
    ]
    
    dfs = []
    for f in files:
        file_path = os.path.join(path, f)
        if os.path.exists(file_path):
            dfs.append(pd.read_csv(file_path, encoding='latin1'))
            
    if not dfs:
        raise FileNotFoundError("CICIDS2017 files not found.")
        
    df = pd.concat(dfs, ignore_index=True)
    
    # Clean up column names
    df.columns = df.columns.str.strip()
    
    # Map protocol to numbers (already numeric or standard)
    # Map label: BENIGN is 0, anything else is 1
    df['label'] = df['Label'].apply(lambda x: 0 if str(x).strip() == 'BENIGN' else 1)
    
    # Map Flow Duration (microseconds to seconds)
    df['duration'] = df['Flow Duration'] / 1e6
    df['protocol'] = df['Protocol']
    df['src_bytes'] = df['Total Length of Fwd Packets']
    df['dst_bytes'] = df['Total Length of Bwd Packets']
    df['src_pkts'] = df['Total Fwd Packets']
    df['dst_pkts'] = df['Total Backward Packets']
    df['rate'] = df['Flow Packets/s']
    
    selected_cols = {
        'duration': 'duration',
        'protocol': 'protocol',
        'src_bytes': 'src_bytes',
        'dst_bytes': 'dst_bytes',
        'src_pkts': 'src_pkts',
        'dst_pkts': 'dst_pkts',
        'rate': 'rate',
        'label': 'label'
    }
    
    return df[list(selected_cols.keys())].rename(columns=selected_cols)

def preprocess_and_merge():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    
    try:
        df_nsl = load_nsl_kdd(os.path.join(base_dir, "nsl_kdd"))
        df_unsw = load_unsw_nb15(os.path.join(base_dir, "unsw_nb15"))
        df_cic = load_cicids2017(os.path.join(base_dir, "cicids2017"))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure you run download_data.py first.")
        return

    print("Merging datasets...")
    merged_df = pd.concat([df_nsl, df_unsw, df_cic], ignore_index=True)
    
    # Handle infinite/NaN values
    print("Cleaning data...")
    merged_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    merged_df.dropna(inplace=True)
    
    # Downsample to keep memory usage reasonable and make SMOTE faster
    # Keep up to 100,000 samples per class
    print("Downsampling for training optimization...")
    benign = merged_df[merged_df['label'] == 0]
    attack = merged_df[merged_df['label'] == 1]
    
    n_samples = min(100000, len(benign), len(attack))
    benign = benign.sample(n=n_samples, random_state=42)
    attack = attack.sample(n=n_samples, random_state=42)
    
    final_df = pd.concat([benign, attack], ignore_index=True)
    
    X = final_df.drop('label', axis=1)
    y = final_df['label']
    
    # Normalizing numerical features
    print("Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Apply SMOTE to ensure balance
    print("Applying SMOTE oversampling...")
    smote = SMOTE(random_state=42)
    X_res, y_res = smote.fit_resample(X_scaled, y)
    
    # Train-test split (70% train / 15% val / 15% test)
    print("Splitting datasets (70% train, 15% validation, 15% test)...")
    X_train, X_temp, y_train, y_temp = train_test_split(X_res, y_res, test_size=0.30, random_state=42, stratify=y_res)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp)
    
    # Save datasets and scaler
    os.makedirs(os.path.join(base_dir, "processed"), exist_ok=True)
    np.save(os.path.join(base_dir, "processed", "X_train.npy"), X_train)
    np.save(os.path.join(base_dir, "processed", "X_val.npy"), X_val)
    np.save(os.path.join(base_dir, "processed", "X_test.npy"), X_test)
    np.save(os.path.join(base_dir, "processed", "y_train.npy"), y_train)
    np.save(os.path.join(base_dir, "processed", "y_val.npy"), y_val)
    np.save(os.path.join(base_dir, "processed", "y_test.npy"), y_test)
    
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"), exist_ok=True)
    joblib.dump(scaler, os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "scaler.joblib"))
    
    print("\n=== Preprocessing Completed Successfully ===")
    print(f"Train set size: {X_train.shape[0]} samples")
    print(f"Validation set size: {X_val.shape[0]} samples")
    print(f"Test set size: {X_test.shape[0]} samples")
    print("Scaler saved to models/scaler.joblib")

if __name__ == "__main__":
    preprocess_and_merge()
