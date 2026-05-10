import pandas as pd, joblib, shap, matplotlib.pyplot as plt, os, sys

if len(sys.argv) != 2:
    print("Usage: python explain_all_flagged.py <predictions.csv>")
    print("Example: python explain_all_flagged.py predictions.csv")
    sys.exit(1)

predictions_csv = sys.argv[1]
# Check deployment path first, then fall back to development path
deploy_model = os.path.join(os.path.dirname(__file__), 'random_forest_calibrated_new.pkl')
if os.path.exists(deploy_model):
    model_path = deploy_model
else:
    model_path = os.path.join(os.path.dirname(__file__),
                              "../../results/phase2/models/random_forest_calibrated_new.pkl")

df = pd.read_csv(predictions_csv)
flagged = df[df['prediction'] == 1]

if len(flagged) == 0:
    print("No high-confidence predictions found.")
    sys.exit(0)

print(f"Generating SHAP waterfall plots for {len(flagged)} flagged endpoint(s)...")

model = joblib.load(model_path)
feature_cols = list(model.feature_names_in_)
X = df[feature_cols]

base_model = model.calibrated_classifiers_[0].estimator
explainer = shap.TreeExplainer(base_model)

for _, row in flagged.iterrows():
    ep = row['test_name']
    idx = df[df['test_name'] == ep].index[0]
    shap_vals = explainer.shap_values(X.iloc[idx:idx+1])
    vals = shap_vals[0, :, 1]
    base_val = explainer.expected_value[1]

    fig, ax = plt.subplots(figsize=(8, 5))
    shap.waterfall_plot(
        shap.Explanation(values=vals,
                         base_values=base_val,
                         data=X.iloc[idx].values,
                         feature_names=feature_cols),
        show=False
    )
    plt.tight_layout(pad=1)
    output_png = f"shap_flagged_{ep.replace('/','_')}.png"
    plt.savefig(output_png, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  Saved {output_png}")

print("Done.")
