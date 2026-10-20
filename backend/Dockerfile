FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Trained model artifacts (app/ml/artifacts/*.joblib, training_report.json) are
# committed to the repo rather than regenerated here -- retraining needs ~2M
# rows of historical data and trains 40+ models, which risks exceeding a free
# hosting tier's build time/memory. The live simulator starts from an empty
# DB and builds up its own data on tick; it only needs the pre-trained
# artifacts for inference, which COPY . . above already brought in.

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
