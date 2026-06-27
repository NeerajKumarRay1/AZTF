import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
import joblib

def load_data():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "processed")
    X_train = np.load(os.path.join(base_dir, "X_train.npy"))
    X_val = np.load(os.path.join(base_dir, "X_val.npy"))
    X_test = np.load(os.path.join(base_dir, "X_test.npy"))
    y_train = np.load(os.path.join(base_dir, "y_train.npy"))
    y_val = np.load(os.path.join(base_dir, "y_val.npy"))
    y_test = np.load(os.path.join(base_dir, "y_test.npy"))
    return X_train, X_val, X_test, y_train, y_val, y_test

def print_metrics(model_name, y_true, y_pred):
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    
    # Calculate False Positive Rate
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    print(f"\n=== {model_name} Evaluation ===")
    print(f"Accuracy:  {acc:.4f} (Target: >=95%)")
    print(f"Precision: {prec:.4f} (Target: >=93%)")
    print(f"Recall:    {rec:.4f} (Target: >=95%)")
    print(f"F1-Score:  {f1:.4f} (Target: >=94%)")
    print(f"False Positive Rate: {fpr:.4f} (Target: <=2%)")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_true, y_pred))
    print("\nClassification Report:")
    print(classification_report(y_true, y_pred))
    
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "fpr": fpr}

def main():
    try:
        X_train, X_val, X_test, y_train, y_val, y_test = load_data()
    except FileNotFoundError as e:
        print(f"Error loading processed data: {e}")
        print("Please run preprocess.py first.")
        return

    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # Features list (must match preprocess.py unified feature set)
    features = ['duration', 'protocol', 'src_bytes', 'dst_bytes', 'src_pkts', 'dst_pkts', 'rate']

    # 1. Random Forest Classifier
    print("\nTraining Random Forest Classifier...")
    rf = RandomForestClassifier(n_estimators=200, class_weight='balanced', n_jobs=-1, random_state=42)
    rf.fit(X_train, y_train)
    
    # Evaluate RF on test set
    y_pred_rf = rf.predict(X_test)
    rf_metrics = print_metrics("Random Forest", y_test, y_pred_rf)
    joblib.dump(rf, os.path.join(models_dir, "rf_model.joblib"))
    
    # Feature Importance for RF
    importances_rf = rf.feature_importances_
    indices_rf = np.argsort(importances_rf)[::-1]
    print("\nRandom Forest Feature Importances:")
    for f in range(len(features)):
        print(f"{f + 1}. {features[indices_rf[f]]}: {importances_rf[indices_rf[f]]:.4f}")

    # 2. XGBoost Classifier
    print("\nTraining XGBoost Classifier...")
    xgb = XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=6, subsample=0.8, random_state=42)
    xgb.fit(X_train, y_train)
    
    # Evaluate XGBoost on test set
    y_pred_xgb = xgb.predict(X_test)
    xgb_metrics = print_metrics("XGBoost", y_test, y_pred_xgb)
    joblib.dump(xgb, os.path.join(models_dir, "xgb_model.joblib"))
    
    # Feature Importance for XGBoost
    importances_xgb = xgb.feature_importances_
    indices_xgb = np.argsort(importances_xgb)[::-1]
    print("\nXGBoost Feature Importances:")
    for f in range(len(features)):
        print(f"{f + 1}. {features[indices_xgb[f]]}: {importances_xgb[indices_xgb[f]]:.4f}")

    # 3. Isolation Forest (Anomaly Detection)
    # Isolation Forest is trained on benign data only
    print("\nTraining Isolation Forest (trained on BENIGN data only)...")
    X_train_benign = X_train[y_train == 0]
    iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42, n_jobs=-1)
    iso.fit(X_train_benign)
    
    # Predict on test set: Isolation Forest outputs -1 for anomalies and 1 for normal
    # Map -1 to 1 (Attack) and 1 to 0 (Benign)
    y_pred_iso_raw = iso.predict(X_test)
    y_pred_iso = np.where(y_pred_iso_raw == -1, 1, 0)
    
    iso_metrics = print_metrics("Isolation Forest Anomaly Detection", y_test, y_pred_iso)
    joblib.dump(iso, os.path.join(models_dir, "iso_model.joblib"))

    print("\n=== Model Training and Serialization Completed Successfully ===")

if __name__ == "__main__":
    main()
