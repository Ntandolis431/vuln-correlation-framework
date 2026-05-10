# Hybrid SAST–DAST Vulnerability Correlation Framework

A lightweight, interpretable machine‑learning tool that takes raw output from multiple SAST (Semgrep, SpotBugs, SonarQube, PMD, FindBugs, FindSecBugs) and DAST (OWASP ZAP) scanners and produces a ranked, evidence‑backed vulnerability report. It reduces false positives by requiring consensus among multiple tools before issuing a high‑confidence alert, and it explains every prediction with SHAP visualisations.

---

## Technologies Used

- **Python 3.12** – core language
- **scikit‑learn 1.8** – Random Forest classifier, Platt scaling, cross‑validation
- **SHAP** – model interpretability (waterfall plots)
- **pandas** – data processing and feature engineering
- **matplotlib** – visualisation
- **joblib** – model persistence
- **Docker** – containerised deployment

---

## Installation

### Prerequisites
- Docker (any recent version)

### Steps

1. **Clone the repository:**

```bash
git clone https://github.com/Ntandolis431/vuln-correlation-framework.git
cd vuln-correlation-framework
Build the Docker image:

bash
docker build -t vuln-correlation .
That's it. No Python, no libraries, no security tools are required on your machine.

Usage
1. Prepare your scan files
After running your security scanners on an application, gather these files in a single folder:

File	Required	Description
endpoints.csv	Yes	List of API endpoints (endpoint, method, source_file optional)
semgrep.json	No	Raw Semgrep JSON output
zap.json	No	Raw OWASP ZAP JSON or XML report
spotbugs.xml	No	SpotBugs XML report (Java applications)
sonarqube.json	No	SonarQube JSON report
pmd.xml	No	PMD XML report
findbugs.xml	No	FindBugs XML report
findsecbugs.xml	No	FindSecBugs XML report
Provide as many or as few tool outputs as you have. The framework automatically sets any missing tool columns to zero and computes consensus features from whatever signals are available.

2. Run the framework
Navigate to the folder containing your scan files and execute:

bash
docker run --rm -v "$(pwd):/data" vuln-correlation \
  endpoints.csv --semgrep semgrep.json --zap zap.json --spotbugs spotbugs.xml
Use only the flags that correspond to files you have. The tool processes your files in seconds and displays a ranked report in the terminal.

3. View the prioritised report
The framework saves predictions.csv with every endpoint, its vulnerability probability (0–1), and the classification:

prediction = 1 → high‑confidence vulnerability (probability ≥ 0.30)

prediction = 0 → not flagged

Endpoints are sorted from highest to lowest risk.

4. Get SHAP explanations
To understand why an endpoint was flagged, generate waterfall plots:

bash
docker run --rm -v "$(pwd):/data" --entrypoint python vuln-correlation \
  /app/explain_all_flagged.py predictions.csv
This produces PNG files for each flagged endpoint, showing exactly which tool signals drove the prediction.

Example output
Below are real screenshots from running the framework on crAPI, a deliberately vulnerable API‑first application (44 endpoints, Semgrep + ZAP):

https://i.imgur.com/o3n6u3y.png

https://i.imgur.com/fhXxeoL.png

https://i.imgur.com/1phLrmY.png

License
This project is distributed for academic and research purposes. See the accompanying thesis for full details:

Kondo K. N. Efficient Web‑Vulnerability Detection Technique Using Hybrid SAST–DAST Analysis and Machine Learning. Master's Thesis. Belarusian State University of Informatics and Radioelectronics, Minsk, 2025.
