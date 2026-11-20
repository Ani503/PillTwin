import os
import sys
import json
import random
import numpy as np
import pandas as pd
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

OCR_CONFUSIONS = {
    'o': '0', '0': 'o', 'l': '1', '1': 'l', 'i': '1', '1': 'i',
    'rn': 'm', 'm': 'rn', 'cl': 'd', 'd': 'cl', 'vv': 'w', 'w': 'vv',
    's': '5', '5': 's', 'b': '8', '8': 'b', 'z': '2', '2': 'z'
}

def perturb_string(text: str) -> str:
    """Simulates OCR noise, typo, omission, or case alteration."""
    if not text or len(text) < 3:
        return text
    
    chars = list(text)
    op = random.choice(['sub', 'del', 'ins', 'ocr', 'case'])
    
    if op == 'sub' and len(chars) > 2:
        idx = random.randint(0, len(chars) - 1)
        chars[idx] = random.choice('abcdefghijklmnopqrstuvwxyz0123456789')
    elif op == 'del' and len(chars) > 4:
        idx = random.randint(0, len(chars) - 1)
        del chars[idx]
    elif op == 'ins':
        idx = random.randint(0, len(chars))
        chars.insert(idx, random.choice('abcdefghijklmnopqrstuvwxyz'))
    elif op == 'ocr':
        s = "".join(chars)
        for k, v in OCR_CONFUSIONS.items():
            if k in s and random.random() < 0.5:
                s = s.replace(k, v, 1)
                return s
    elif op == 'case':
        return "".join(c.lower() if random.random() < 0.5 else c.upper() for c in chars)
        
    return "".join(chars)

def generate_evaluation_set(names: List[str], n_samples: int = 3000) -> Tuple[List[str], List[str]]:
    sampled_indices = random.sample(range(len(names)), min(n_samples, len(names)))
    queries = []
    ground_truths = []
    
    # 50% mild to moderate perturbations
    n_mild = int(n_samples * 0.5)
    for idx in sampled_indices[:n_mild]:
        true_name = names[idx]
        noisy = perturb_string(true_name)
        queries.append(noisy)
        ground_truths.append(true_name)

    # 25% multi-error perturbations
    n_multi = int(n_samples * 0.25)
    for idx in sampled_indices[n_mild:n_mild + n_multi]:
        true_name = names[idx]
        noisy = perturb_string(perturb_string(true_name))
        queries.append(noisy)
        ground_truths.append(true_name)

    # 25% random gibberish / out-of-vocabulary noise
    n_gib = n_samples - len(queries)
    gibberish_vocab = ['xyz', 'qwerty', 'tablet', 'strip', 'medicine', 'unknown', '12345', 'cough', 'fever', 'pharma', 'dr', 'clinic']
    for _ in range(n_gib):
        gib = " ".join(random.choices(gibberish_vocab, k=random.randint(1, 3))) + f" {random.randint(10, 999)}"
        queries.append(gib)
        ground_truths.append("__NEGATIVE__")

    return queries, ground_truths

def query_in_batches(X_queries, X_catalog, batch_size=500):
    """Computes top-1 and top-2 cosine similarities in memory-efficient batches."""
    n_queries = X_queries.shape[0]
    top1_indices = np.zeros(n_queries, dtype=int)
    top1_scores = np.zeros(n_queries, dtype=np.float32)
    top2_scores = np.zeros(n_queries, dtype=np.float32)

    X_cat_T = X_catalog.T.tocsc()

    for start_idx in range(0, n_queries, batch_size):
        end_idx = min(start_idx + batch_size, n_queries)
        q_batch = X_queries[start_idx:end_idx]
        batch_sims = q_batch.dot(X_cat_T).toarray() # shape: (batch, n_catalog)

        # Top 1
        b_top1_idx = np.argmax(batch_sims, axis=1)
        b_top1_scores = np.clip(np.max(batch_sims, axis=1), 0.0, 1.0)
        top1_indices[start_idx:end_idx] = b_top1_idx
        top1_scores[start_idx:end_idx] = b_top1_scores

        # Top 2 by zeroing top1
        rows = np.arange(len(b_top1_idx))
        batch_sims[rows, b_top1_idx] = -1.0
        top2_scores[start_idx:end_idx] = np.clip(np.max(batch_sims, axis=1), 0.0, 1.0)

    return top1_indices, top1_scores, top2_scores

def main():
    print("[Phase 2] Training & Calibrating Character N-Gram Brand Matcher...")
    
    brand_parquet = 'data/processed/brand_clean.parquet'
    if not os.path.exists(brand_parquet):
        print(f"Error: {brand_parquet} not found. Run make build first.")
        sys.exit(1)

    df_brand = pd.read_parquet(brand_parquet)
    unique_names = sorted(list(df_brand['brand_name'].dropna().unique()))
    print(f"Total unique brand catalog entries: {len(unique_names)}")

    # Vectorizer: character n-grams (3 to 5) with word boundary awareness
    print("Fitting character n-gram TF-IDF vectorizer (ngram_range=(3, 5))...")
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, dtype=np.float32)
    X_catalog = vectorizer.fit_transform(unique_names)
    print(f"Catalog TF-IDF matrix shape: {X_catalog.shape}")

    # Generate benchmark dataset for calibration & CV evaluation
    print("Generating 3,000 synthetic test queries (mild OCR noise, severe noise, and negative gibberish)...")
    queries, ground_truths = generate_evaluation_set(unique_names, n_samples=3000)

    # Transform queries and compute top candidate similarity in batches
    X_queries = vectorizer.transform(queries)
    top1_indices, top1_scores, top2_scores = query_in_batches(X_queries, X_catalog, batch_size=500)

    # Binary label: 1 if top-1 predicted name equals ground truth, 0 otherwise
    labels = np.array([
        1 if unique_names[pred_idx].lower() == gt.lower() else 0
        for pred_idx, gt in zip(top1_indices, ground_truths)
    ])

    print(f"Benchmark set size: {len(labels)}, Correct Top-1 matches: {labels.sum()} ({labels.mean():.1%})")

    # -------------------------------------------------------------
    # Cross-Validation Comparison: Platt vs Isotonic vs Baseline kNN
    # -------------------------------------------------------------
    print("\n--- Model Calibration & Baseline Comparison (5-Fold Stratified CV) ---")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

    platt_preds = np.zeros(len(labels))
    iso_preds = np.zeros(len(labels))
    # Baseline: 1-NN similarity baseline (raw score without calibration)
    raw_scores = top1_scores
    # kNN baseline: mean of top-1 and top-2 cosine similarity
    knn_preds = (top1_scores + top2_scores) / 2.0

    for fold, (train_idx, val_idx) in enumerate(skf.split(top1_scores, labels), 1):
        # 1. Platt Scaling (Logistic Regression on top1 similarity score)
        lr = LogisticRegression(C=1.0, random_state=SEED)
        lr.fit(top1_scores[train_idx].reshape(-1, 1), labels[train_idx])
        platt_preds[val_idx] = lr.predict_proba(top1_scores[val_idx].reshape(-1, 1))[:, 1]

        # 2. Isotonic Regression (non-parametric monotonic calibration)
        iso = IsotonicRegression(out_of_bounds='clip', y_min=0.0, y_max=1.0)
        iso.fit(top1_scores[train_idx], labels[train_idx])
        iso_preds[val_idx] = iso.predict(top1_scores[val_idx])

    # Evaluate metrics
    metrics = {}
    for name, probs in [
        ("Raw Cosine Similarity", np.clip(raw_scores, 0.0, 1.0)),
        ("kNN-style Mean Similarity", np.clip(knn_preds, 0.0, 1.0)),
        ("Platt Scaling (Logistic)", np.clip(platt_preds, 0.0, 1.0)),
        ("Isotonic Regression", np.clip(iso_preds, 0.0, 1.0))
    ]:
        brier = brier_score_loss(labels, probs)
        eps = 1e-6
        clipped_probs = np.clip(probs, eps, 1 - eps)
        ll = log_loss(labels, clipped_probs)
        auc = roc_auc_score(labels, probs)
        metrics[name] = {"brier_score": round(float(brier), 5), "log_loss": round(float(ll), 4), "roc_auc": round(float(auc), 4)}
        print(f"  {name:26s} | Brier Score: {brier:.5f} | Log Loss: {ll:.4f} | ROC-AUC: {auc:.4f}")

    # -------------------------------------------------------------
    # Optimal Abstention Threshold Selection on Out-Of-Fold Predictions
    # Prioritizing exact-match precision (Precision >= 98%)
    # -------------------------------------------------------------
    print("\n--- Calibrated Abstention Threshold Tuning (Precision-First) ---")
    thresholds = np.linspace(0.40, 0.95, 12)
    best_tau = 0.70
    best_coverage = 0.0

    print(f"{'Threshold (tau)':16s} | {'Precision':10s} | {'Coverage':10s} | {'Abstention Rate':16s}")
    print("-" * 60)
    for tau in thresholds:
        accepted = platt_preds >= tau
        if accepted.sum() == 0:
            continue
        prec = labels[accepted].mean()
        cov = accepted.mean()
        abstain_rate = 1.0 - cov
        print(f"{tau:16.2f} | {prec:10.1%} | {cov:10.1%} | {abstain_rate:16.1%}")
        if prec >= 0.98 and cov > best_coverage:
            best_coverage = cov
            best_tau = float(tau)

    print(f"\nSelected Calibrated Confidence Threshold: tau = {best_tau:.2f}")
    print(f"At tau = {best_tau:.2f}: Exact-match Precision = {labels[platt_preds >= best_tau].mean():.1%}, Coverage = {best_coverage:.1%}")

    # -------------------------------------------------------------
    # Final Fit on Full Dataset & Save Calibrator Artifacts
    # -------------------------------------------------------------
    final_platt = LogisticRegression(C=1.0, random_state=SEED)
    final_platt.fit(top1_scores.reshape(-1, 1), labels)
    
    calibrator_config = {
        "model_type": "platt_scaling_logistic",
        "intercept": float(final_platt.intercept_[0]),
        "coef": float(final_platt.coef_[0][0]),
        "abstention_threshold": best_tau,
        "metrics": metrics,
        "vectorizer_config": {
            "analyzer": "char_wb",
            "ngram_range": [3, 5],
            "min_df": 2
        }
    }

    os.makedirs('data/processed', exist_ok=True)
    out_config_path = 'data/processed/matcher_calibration.json'
    with open(out_config_path, 'w', encoding='utf-8') as f:
        json.dump(calibrator_config, f, indent=2)

    print(f"\nCalibrator configuration saved to {out_config_path}")
    print("Phase 2 Matcher Training & Calibration completed successfully.")

if __name__ == '__main__':
    main()
