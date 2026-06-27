import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import classification_report, confusion_matrix

def load_data():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "processed")
    X_train = np.load(os.path.join(base_dir, "X_train.npy"))
    X_val = np.load(os.path.join(base_dir, "X_val.npy"))
    X_test = np.load(os.path.join(base_dir, "X_test.npy"))
    y_train = np.load(os.path.join(base_dir, "y_train.npy"))
    y_val = np.load(os.path.join(base_dir, "y_val.npy"))
    y_test = np.load(os.path.join(base_dir, "y_test.npy"))
    return X_train, X_val, X_test, y_train, y_val, y_test

def create_sequences(X, y, seq_len=10):
    X_seq, y_seq = [], []
    for i in range(len(X) - seq_len + 1):
        X_seq.append(X[i : i + seq_len])
        y_seq.append(y[i + seq_len - 1])
    return np.array(X_seq), np.array(y_seq)

def main():
    print("Loading preprocessed data...")
    try:
        X_train, X_val, X_test, y_train, y_val, y_test = load_data()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please run preprocess.py first.")
        return
        
    seq_len = 10
    print(f"Creating sequences of length {seq_len}...")
    X_train_seq, y_train_seq = create_sequences(X_train, y_train, seq_len)
    X_val_seq, y_val_seq = create_sequences(X_val, y_val, seq_len)
    X_test_seq, y_test_seq = create_sequences(X_test, y_test, seq_len)
    
    print(f"Sequence Train shape: {X_train_seq.shape}")
    print(f"Sequence Test shape: {X_test_seq.shape}")
    
    # Build LSTM Model
    print("Building LSTM model...")
    model = Sequential([
        LSTM(64, input_shape=(seq_len, X_train.shape[1]), return_sequences=True, dropout=0.2),
        LSTM(32, dropout=0.2),
        Dense(16, activation='relu'),
        Dropout(0.2),
        Dense(1, activation='sigmoid')
    ])
    
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    model.summary()
    
    # Train Model (Keep epochs low to run quickly in setup phase)
    epochs = 5
    batch_size = 128
    print(f"Training LSTM model for {epochs} epochs...")
    model.fit(
        X_train_seq, y_train_seq,
        validation_data=(X_val_seq, y_val_seq),
        epochs=epochs,
        batch_size=batch_size,
        verbose=1
    )
    
    # Evaluate model
    print("\nEvaluating LSTM Model on Test Set...")
    loss, accuracy = model.evaluate(X_test_seq, y_test_seq, verbose=0)
    print(f"Test Loss: {loss:.4f}, Test Accuracy: {accuracy:.4f}")
    
    y_pred_probs = model.predict(X_test_seq, verbose=0)
    y_pred = (y_pred_probs >= 0.60).astype(int).flatten()
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test_seq, y_pred))
    print("\nClassification Report:")
    print(classification_report(y_test_seq, y_pred))
    
    # Save Model
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "lstm_model.h5")
    model.save(model_path)
    print(f"LSTM model saved successfully to {model_path}")

if __name__ == "__main__":
    main()
