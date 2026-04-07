"""
LSTM Autoencoder — Roadmap / Production Upgrade Path
-----------------------------------------------------
Treats each session as a TIME SERIES of behavioral snapshots
rather than a single static feature vector.

Architecture:
    Encoder: LSTM compresses (seq_len, 47) → latent vector
    Decoder: LSTM reconstructs latent vector → (seq_len, 47)
    Loss:    MSE reconstruction error
    Anomaly: High reconstruction error = behavior unlike training sessions

Usage: Position as upgrade from One-Class SVM when >= 10 labelled sessions
       exist and GPU/CPU budget allows heavier inference.

Requirements: torch (pip install torch --index-url https://download.pytorch.org/whl/cpu)
"""

import os
import numpy as np

# Guard: PyTorch optional — SVM is primary model
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

MODEL_DIR = os.path.join(os.getcwd(), "backend", "ml", "models")
FEATURE_DIM = 47          # Must match len(FEATURE_NAMES)
HIDDEN_DIM  = 32          # Latent space size — smaller = more compression
NUM_LAYERS  = 1           # Single LSTM layer (sufficient for demo)
EPOCHS      = 50
BATCH_SIZE  = 1           # Each session is one sample
LR          = 1e-3


# ─────────────────────────────────────────────
# Model Definition
# ─────────────────────────────────────────────

class LSTMAutoencoder(nn.Module):
    """
    Sequence-to-sequence LSTM Autoencoder.

    Input:  (batch, seq_len, 47)
    Output: (batch, seq_len, 47)  — reconstructed sequence

    Anomaly score = mean squared error between input and output.
    Legitimate sessions → low error. Attacker sessions → high error.
    """

    def __init__(self, feature_dim: int = FEATURE_DIM, hidden_dim: int = HIDDEN_DIM, num_layers: int = NUM_LAYERS):
        super().__init__()
        self.feature_dim = feature_dim
        self.hidden_dim  = hidden_dim
        self.num_layers  = num_layers

        # Encoder: compress input sequence into hidden state
        self.encoder = nn.LSTM(
            input_size=feature_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )

        # Decoder: reconstruct sequence from hidden state
        self.decoder = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=feature_dim,
            num_layers=num_layers,
            batch_first=True
        )

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        """
        x: (batch, seq_len, feature_dim)
        returns: (batch, seq_len, feature_dim)
        """
        # Encode: run through LSTM, keep hidden state
        _, (hidden, cell) = self.encoder(x)

        # Repeat hidden state across seq_len to feed decoder
        seq_len = x.size(1)
        # hidden: (num_layers, batch, hidden_dim)
        latent = hidden[-1]                        # (batch, hidden_dim)
        latent_seq = latent.unsqueeze(1).repeat(1, seq_len, 1)  # (batch, seq_len, hidden_dim)

        # Decode: reconstruct sequence
        reconstructed, _ = self.decoder(latent_seq)
        return reconstructed


# ─────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────

def train_lstm(user_id: int, session_sequences: list[list[list[float]]]) -> dict:
    """
    Train LSTM Autoencoder on user's legitimate session sequences.

    Args:
        user_id:           User to train for
        session_sequences: List of sessions. Each session = list of feature snapshots.
                           Shape per session: (num_snapshots, 47)
                           Typical: 4–6 snapshots per session, each 6 seconds apart.

    Returns:
        dict with training status
    """
    if not TORCH_AVAILABLE:
        return {"error": "PyTorch not installed. Run: pip install torch"}

    if len(session_sequences) < 10:
        return {"error": "Need >= 10 sessions for LSTM training"}

    model = LSTMAutoencoder()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()

    model.train()
    final_loss = None

    for epoch in range(EPOCHS):
        epoch_loss = 0.0
        for seq in session_sequences:
            # seq: (num_snapshots, 47)
            x = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)  # (1, seq_len, 47)

            optimizer.zero_grad()
            reconstructed = model(x)
            loss = criterion(reconstructed, x)
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

        final_loss = epoch_loss / len(session_sequences)

    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, f"lstm_{user_id}.pt")
    torch.save(model.state_dict(), model_path)

    # Compute threshold: max reconstruction error on training data (+ small buffer)
    model.eval()
    errors = []
    with torch.no_grad():
        for seq in session_sequences:
            x = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)
            recon = model(x)
            err = nn.MSELoss()(recon, x).item()
            errors.append(err)

    threshold = float(np.max(errors) * 1.2)  # 20% buffer above worst training error

    # Save threshold
    import pickle
    with open(os.path.join(MODEL_DIR, f"lstm_meta_{user_id}.pkl"), 'wb') as f:
        pickle.dump({"threshold": threshold, "user_id": user_id, "final_loss": final_loss}, f)

    return {
        "trained": True,
        "epochs": EPOCHS,
        "final_loss": round(final_loss, 6),
        "anomaly_threshold": round(threshold, 6),
        "model_path": model_path,
    }


# ─────────────────────────────────────────────
# Prediction
# ─────────────────────────────────────────────

def predict_lstm_score(user_id: int, session_sequence: list[list[float]]) -> int:
    """
    Compute anomaly score (0–100) for session using LSTM reconstruction error.

    Args:
        user_id:          User whose model to load
        session_sequence: List of feature snapshots for current session
                          Shape: (num_snapshots, 47)

    Returns:
        score (int): 0 = certain attack, 100 = certain legitimate
    """
    if not TORCH_AVAILABLE:
        return 50  # Fallback

    import pickle

    model_path = os.path.join(MODEL_DIR, f"lstm_{user_id}.pt")
    meta_path  = os.path.join(MODEL_DIR, f"lstm_meta_{user_id}.pkl")

    if not os.path.exists(model_path) or not os.path.exists(meta_path):
        return 50  # Model not trained — neutral score

    # Load model
    model = LSTMAutoencoder()
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()

    # Load threshold
    with open(meta_path, 'rb') as f:
        meta = pickle.load(f)
    threshold = meta["threshold"]

    # Compute reconstruction error for current session
    x = torch.tensor(session_sequence, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        recon = model(x)
        error = nn.MSELoss()(recon, x).item()

    # Map error → score
    # error = 0           → score = 100 (perfect reconstruction = legitimate)
    # error = threshold   → score = 50  (boundary)
    # error = 2*threshold → score = 0   (double the threshold = definite anomaly)
    if error <= threshold:
        score = 100 - int((error / threshold) * 50)   # 100 → 50
    else:
        overshoot = (error - threshold) / (threshold + 1e-6)
        score = max(0, 50 - int(overshoot * 50))       # 50 → 0

    return int(max(0, min(100, score)))
