#!/usr/bin/env python3
"""
Step 5: Train and evaluate Random Forest with proper threshold selection and calibration.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import (confusion_matrix, roc_auc_score,
                             precision_recall_curve, auc, brier_score_loss)
import matplotlib.pyplot as plt
import joblib

# Load data
train = pd.read_csv('results/phase2/features/train.csv')
test = pd.read_csv('results/phase2/features/test.csv')
print(f"Train: {len(train)} rows, Test: {len(test)} rows")

# Features (exclude non-predictive columns)
exclude_cols = ['test_name', 'category', 'cwe', 'ground_truth']
feature_cols = [c for c in train.columns if c not in exclude_cols]
X_train = train[feature_cols]
y_train = train['ground_truth']
X_test = test[feature_cols]
y_test = test['ground_truth']

# Base Random Forest (uncalibrated, for SHAP later)
rf_base = RandomForestClassifier(n_estimators=100, class_weight='balanced',
                                 random_state=42, n_jobs=-1)

# --- Step 1: Use cross-validation to select threshold for recall ≥ 90% ---
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Get cross-validated predicted probabilities on training set using base RF
y_proba_cv = cross_val_predict(rf_base, X_train, y_train, cv=cv, method='predict_proba', n_jobs=-1)[:,1]

# Try thresholds from 0.1 to 0.9
thresholds = np.arange(0.1, 0.9, 0.05)
best_threshold = 0.5
best_f1 = 0
target_recall = 0.90

for thresh in thresholds:
    y_pred_thresh = (y_proba_cv >= thresh).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_train, y_pred_thresh).ravel()
    recall = tp / (tp + fn) if (tp+fn)>0 else 0
    precision = tp / (tp + fp) if (tp+fp)>0 else 0
    f1 = 2*precision*recall/(precision+recall) if (precision+recall)>0 else 0
    if recall >= target_recall and f1 > best_f1:
        best_f1 = f1
        best_threshold = thresh

print(f"Selected threshold from CV: {best_threshold:.2f}")

# --- Step 2: Train final model with calibration ---
# Use CalibratedClassifierCV with 5-fold cross-validation (this will train base estimators)
calibrated_rf = CalibratedClassifierCV(rf_base, method='sigmoid', cv=5)
calibrated_rf.fit(X_train, y_train)

# Save calibrated model
joblib.dump(calibrated_rf, 'results/phase2/models/random_forest_calibrated.pkl')

# For SHAP, we also need an uncalibrated RF trained on full data (use the same base but refit)
rf_base.fit(X_train, y_train)
joblib.dump(rf_base, 'results/phase2/models/random_forest_uncalibrated.pkl')

# --- Step 3: Evaluate on test set using selected threshold ---
y_proba_test = calibrated_rf.predict_proba(X_test)[:,1]
y_pred_final = (y_proba_test >= best_threshold).astype(int)

tn, fp, fn, tp = confusion_matrix(y_test, y_pred_final).ravel()
precision = tp / (tp + fp) if (tp+fp)>0 else 0
recall = tp / (tp + fn) if (tp+fn)>0 else 0
f1 = 2*precision*recall/(precision+recall) if (precision+recall)>0 else 0

print(f"\n--- Random Forest Results (threshold={best_threshold:.2f}) ---")
print(f"TP={tp}, FP={fp}, FN={fn}, TN={tn}")
print(f"Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}")
print(f"AUC-ROC = {roc_auc_score(y_test, y_proba_test):.3f}")

# Precision-Recall curve
precision_vals, recall_vals, _ = precision_recall_curve(y_test, y_proba_test)
pr_auc = auc(recall_vals, precision_vals)
print(f"AUC-PR = {pr_auc:.3f}")

# Brier score
brier = brier_score_loss(y_test, y_proba_test)
print(f"Brier score = {brier:.3f}")

# Feature importance (from uncalibrated RF)
importances = rf_base.feature_importances_
feat_imp = pd.DataFrame({'feature': feature_cols, 'importance': importances})
feat_imp = feat_imp.sort_values('importance', ascending=False)
print("\n--- Top 10 feature importances ---")
print(feat_imp.head(10).to_string(index=False))

# Save results
results = pd.DataFrame([{
    'model': 'Random Forest (calibrated)',
    'threshold': best_threshold,
    'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
    'precision': precision, 'recall': recall, 'f1': f1,
    'auc_roc': roc_auc_score(y_test, y_proba_test),
    'auc_pr': pr_auc,
    'brier': brier
}])
results.to_csv('results/phase2/evaluations/random_forest_calibrated_results.csv', index=False)
print("\nResults saved to results/phase2/evaluations/random_forest_calibrated_results.csv")
