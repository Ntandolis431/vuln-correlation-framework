import argparse, pandas as pd, json, re, os, joblib, sys

# ----- 1. Command line -----
parser = argparse.ArgumentParser(
    description='Hybrid SAST-DAST vulnerability correlation framework')
parser.add_argument('endpoints_csv', help='CSV with endpoint, method, source_file columns')
parser.add_argument('--semgrep', help='Semgrep JSON output file')
parser.add_argument('--zap', help='OWASP ZAP JSON or XML report')
parser.add_argument('--spotbugs', help='SpotBugs XML report')
parser.add_argument('--sonarqube', help='SonarQube JSON report (scorecard or direct)')
parser.add_argument('--pmd', help='PMD XML report')
parser.add_argument('--findbugs', help='FindBugs XML report')
parser.add_argument('--findsecbugs', help='FindSecBugs XML report')
parser.add_argument('--output', default='predictions.csv', help='Output CSV file')
args = parser.parse_args()

# ----- 2. Load endpoints -----
ep_df = pd.read_csv(args.endpoints_csv)
if 'endpoint' not in ep_df.columns:
    if 'test_name' in ep_df.columns:
        ep_df = ep_df.rename(columns={'test_name': 'endpoint'})
    else:
        raise ValueError("CSV must contain an 'endpoint' or 'test_name' column")
print(f"[OK] Loaded {len(ep_df)} endpoints")

# ----- 3. Parse Semgrep -----
semgrep_paths = set()
if args.semgrep:
    with open(args.semgrep) as f:
        semgrep_data = json.load(f)
    semgrep_paths = {r.get('path','').replace('\\','/') for r in semgrep_data.get('results',[])}
    print(f"[OK] Semgrep flagged {len(semgrep_paths)} files")
else:
    print("[--] Semgrep skipped (no file provided)")

# ----- 4. Parse ZAP (JSON or XML auto-detect) -----
zap_urls = set()
if args.zap:
    ext = os.path.splitext(args.zap)[1].lower()
    if ext == '.json':
        with open(args.zap) as f:
            zap_data = json.load(f)
        # Handle both ZAP formats: 'site' -> alerts, or flat 'alerts' key
        if 'site' in zap_data:
            alerts = []
            for site in zap_data.get('site', []):
                alerts.extend(site.get('alerts', []))
        else:
            alerts = zap_data.get('alerts', [])
                # Filter Medium/High: try 'riskcode' first, then 'risk' string
        active = []
        for a in alerts:
            rc = str(a.get('riskcode','')).strip()
            risk_str = str(a.get('risk','')).strip()
            if rc in ('2','3') or risk_str in ('Medium','High'):
                active.append(a)
        for a in active:
            # Format 1: instances with uri
            for inst in a.get('instances', []):
                path = re.sub(r'^https?://[^/]+','', inst.get('uri','')).rstrip('/')
                if path:
                    zap_urls.add(path)
            # Format 2: direct url field
            direct_url = a.get('url','')
            if direct_url:
                path = re.sub(r'^https?://[^/]+','', direct_url).rstrip('/')
                if path:
                    zap_urls.add(path)
    elif ext == '.xml':
        import xml.etree.ElementTree as ET
        tree = ET.parse(args.zap)
        root = tree.getroot()
        for alertitem in root.findall('.//alertitem'):
            risk = alertitem.find('riskcode')
            if risk is not None and risk.text in ('2','3'):
                uri_el = alertitem.find('uri')
                if uri_el is not None and uri_el.text:
                    path = re.sub(r'^https?://[^/]+','', uri_el.text).rstrip('/')
                    if path:
                        zap_urls.add(path)
    print(f"[OK] ZAP active alerts on {len(zap_urls)} URLs")
else:
    print("[--] ZAP skipped (no file provided)")

# ----- 5. Parse SpotBugs (XML) -----
spotbugs_paths = set()
if args.spotbugs:
    import xml.etree.ElementTree as ET
    tree = ET.parse(args.spotbugs)
    root = tree.getroot()
    for bug in root.findall('.//BugInstance'):
        src = bug.find('SourceLine')
        if src is not None:
            spotbugs_paths.add(src.get('sourcepath','').replace('\\','/'))
    print(f"[OK] SpotBugs flagged {len(spotbugs_paths)} source files")
else:
    print("[--] SpotBugs skipped (no file provided)")

# ----- 6. Placeholder parsers for other tools -----
def skip_tool(name, provided):
    if provided:
        print(f"[--] {name} parser not yet implemented; column set to 0")
    else:
        print(f"[--] {name} skipped (no file provided)")

skip_tool("SonarQube", args.sonarqube)
skip_tool("PMD", args.pmd)
skip_tool("FindBugs", args.findbugs)
skip_tool("FindSecBugs", args.findsecbugs)

# ----- 7. Map tools to endpoints -----
def match_tool_to_endpoint(ep_name, src_file, paths):
    # Strategy 1: if source_file column is present and non-empty, match by filename
    if pd.notna(src_file) and src_file:
        base = os.path.basename(str(src_file))
        for p in paths:
            if base in p or p.endswith(base):
                return 1
    # Strategy 2: fallback — match endpoint name against tool paths
    ep_clean = ep_name.strip('/').lower()
    for p in paths:
        p_clean = p.replace('\\', '/').lower()
        # Extract the filename without extension from the tool path
        p_filename = os.path.splitext(os.path.basename(p_clean))[0]
        if p_filename and p_filename in ep_clean:
            return 1
        # Also try matching whole path components
        if any(part in p_clean for part in ep_clean.split('/') if len(part) > 2):
            return 1
    return 0

def match_zap(ep_name, urls):
    ep = ep_name.strip('/')
    # Strip query strings from both sides for comparison
    ep_clean = ep.split('?')[0]
    for z in urls:
        zp = z.strip('/')
        zp_clean = zp.split('?')[0]
        if zp_clean == ep_clean:
            return 1
        # Path parameter matching: support {param} and :param
        ep_parts, zp_parts = ep_clean.split('/'), zp_clean.split('/')
        if len(ep_parts) == len(zp_parts):
            if all(
                (e.startswith('{') and e.endswith('}')) or
                (e.startswith(':') and len(e) > 1) or
                e.lower() == zz.lower()
                for e, zz in zip(ep_parts, zp_parts)
            ):
                return 1
    return 0

# ----- 8. Build feature matrix -----
rows = []
for _, r in ep_df.iterrows():
    ep = r['endpoint']
    src = r.get('source_file', '')
    sem = match_tool_to_endpoint(ep, src, semgrep_paths)
    zap = match_zap(ep, zap_urls)
    spot = match_tool_to_endpoint(ep, src, spotbugs_paths)
    # Other tools are 0 for now
    rows.append({
        'test_name': ep, 'method': r.get('method','GET'),
        'ground_truth': r.get('ground_truth', -1),
        'sonarqube': 0, 'semgrep': sem, 'spotbugs': spot, 'zap': zap,
        'pmd': 0, 'findbugs': 0, 'findsecbugs': 0,
        'num_tools': (0 + sem + spot + zap),
        'num_disagree': 4 - (0 + sem + spot + zap),
        'semgrep_and_zap': 1 if (sem and zap) else 0,
        'spotbugs_and_zap': 1 if (spot and zap) else 0,
        'zap_weighted': 0, 'zap_relevant': 0
    })

features_df = pd.DataFrame(rows)
print(f"[OK] Feature matrix built: {len(features_df)} rows")

# ----- 9. Predict -----
# Check deployment path first, then fall back to development path
deploy_model = os.path.join(os.path.dirname(__file__), 'random_forest_calibrated_new.pkl')
if os.path.exists(deploy_model):
    model_path = deploy_model
else:
    model_path = os.path.join(os.path.dirname(__file__),
                              "../../results/phase2/models/random_forest_calibrated_new.pkl")
model = joblib.load(model_path)
X = features_df[model.feature_names_in_]
probs = model.predict_proba(X)[:, 1]
features_df['probability'] = probs
features_df['prediction'] = (probs >= 0.30).astype(int)

features_df.to_csv(args.output, index=False)
print(f"[DONE] Predictions saved to {args.output}")
print("\nTop 10 highest-probability endpoints:")
top = features_df.sort_values('probability', ascending=False).head(10)
print(top[['test_name','ground_truth','probability','prediction',
           'semgrep','spotbugs','zap']].to_string(index=False))
