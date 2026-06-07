#!/usr/bin/env python3
"""
Step 1: Feature Engineering for Phase 2
Load the hybrid dataset, add new columns, and save the enhanced version.
"""

import pandas as pd

# Load the dataset
df = pd.read_csv('results/ml-ready/complete_hybrid_dataset.csv')
print(f"Loaded {len(df)} rows. Original columns: {list(df.columns)}")

# --- Add new features ---

# 1. Number of tools that flagged the test case
df['num_tools'] = df[['sonarqube', 'semgrep', 'spotbugs', 'zap']].sum(axis=1)

# 2. Number of tools that DID NOT flag it (disagreement)
df['num_disagree'] = 4 - df['num_tools']

# 3. Corroboration features: both static and dynamic tools agree
df['semgrep_and_zap'] = ((df['semgrep'] == 1) & (df['zap'] == 1)).astype(int)
df['spotbugs_and_zap'] = ((df['spotbugs'] == 1) & (df['zap'] == 1)).astype(int)

# 4. Weighted ZAP severity (using CVSS‑like weights: High=9, Medium=6, Low=3, Info=0)
df['zap_weighted'] = (
    df['zap_high'] * 9 +
    df['zap_medium'] * 6 +
    df['zap_low'] * 3 +
    df['zap_info'] * 0
)

# Save the enhanced dataset
output_path = 'results/phase2/features/enhanced_dataset.csv'
df.to_csv(output_path, index=False)
print(f"Enhanced dataset saved to {output_path}")
print(f"New columns added: {[c for c in df.columns if c not in ['test_name','category','cwe','ground_truth','sonarqube','semgrep','spotbugs','zap','zap_high','zap_medium','zap_low','zap_info','zap_alert_count']]}")
