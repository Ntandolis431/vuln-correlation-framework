FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas==2.2.0 \
    scikit-learn==1.8.0 \
    shap==0.46.0 \
    matplotlib==3.9.0 \
    joblib==1.4.0

COPY predict_vulnerabilities.py /app/
COPY explain_all_flagged.py /app/
COPY random_forest_calibrated_new.pkl /app/

VOLUME ["/data"]
WORKDIR /data

ENTRYPOINT ["python", "/app/predict_vulnerabilities.py"]
