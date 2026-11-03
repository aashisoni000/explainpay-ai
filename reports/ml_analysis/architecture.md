# ExplainPay architecture and workflows (implemented)

This document reflects the repository state and generated ML artifacts in
`reports/ml_analysis/`.

## 1) Overall system architecture

```mermaid
flowchart LR
    User["Browser user"]
    FE["Next.js app (App Router)\nTypeScript + Tailwind + Geist"]
    Proxy["Next.js rewrite proxy\n/backend/*"]
    API["FastAPI backend\nPydantic + service layer"]
    DB[("PostgreSQL\ninvestigations + reports")]
    Fraud["Fraud model runtime\njoblib pipeline + SHAP"]
    Phish["Phishing runtime\nURL normalization/features + SHAP"]
    Threat["Optional providers\nVirusTotal / Web Risk / RDAP"]

    User --> FE --> Proxy --> API
    API --> DB
    API --> Fraud
    API --> Phish
    API -. conditional .-> Threat
```

## 2) Transaction fraud detection pipeline

```mermaid
flowchart LR
    Upload["CSV upload (/transactions)"]
    Parse["Frontend parse + preview"]
    Submit["POST /api/transactions/analyze"]
    Validate["Backend schema/range validation"]
    Features["Ordered fraud features:\nTime,V1..V28,Amount"]
    Predict["Selected pipeline predict_proba"]
    Score["Threshold + risk level"]
    Explain["Tree SHAP contributions"]
    Persist["Save optional investigation/report rows"]
    UI["UI table/charts/detail modal"]

    Upload --> Parse --> Submit --> Validate --> Features --> Predict --> Score --> Explain --> UI
    Score --> Persist
```

## 3) Website trust scanning pipeline

```mermaid
flowchart LR
    Input["User URL input (/website-scanner)"]
    Call["POST /api/website-scanner/scan"]
    Normalize["Strict URL normalization\nhttp/https, no credentials/private IP"]
    Extract["15 lexical features\n(backend/app/ml/urls.py)"]
    Predict["Selected phishing pipeline predict_proba"]
    Score["Threshold + trust verdict"]
    Explain["Tree SHAP contributions"]
    Optional["Optional threat enrichment"]
    Save["Persist investigation/report"]
    Render["Frontend scan result + history"]

    Input --> Call --> Normalize --> Extract --> Predict --> Score --> Explain --> Render
    Score --> Optional --> Render
    Score --> Save
```

## 4) ML training pipeline

```mermaid
flowchart LR
    Raw["Raw CSVs\ntransactions/creditcard.csv\nwebsites/phishing_features.csv"]
    Prepare["Task-specific preparation\ncleaning + dedupe + feature schema"]
    Split["Stratified 60/20/20 split\nseed=42"]
    Scale["StandardScaler fit(train)"]
    Train["Train LR + XGBoost candidates"]
    Select["Select by validation AP\nthreshold by validation F1"]
    Persist["Persist selected artifact\n+ metrics JSON + background sample"]
    Analyze["Offline audit exports\nreports/ml_analysis/analyze.py"]

    Raw --> Prepare --> Split --> Scale --> Train --> Select --> Persist --> Analyze
```

## 5) Prediction and explainability workflow

```mermaid
flowchart LR
    Request["Prediction request"]
    Load["Load selected artifact\n(versioned metadata)"]
    Infer["Pipeline inference\nprobability + predicted class"]
    Explain["SHAP TreeExplainer\ninterventional/raw log-odds"]
    Aggregate["Per-row top contributors\nand global mean |SHAP|"]
    Response["API response payload"]

    Request --> Load --> Infer --> Explain --> Aggregate --> Response
```

## 6) Frontend-backend-ML service communication

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Next.js Frontend
    participant PX as /backend Proxy
    participant BE as FastAPI
    participant ML as ML Runtime
    participant DB as PostgreSQL

    U->>FE: Upload CSV / submit URL
    FE->>PX: /backend/api/*
    PX->>BE: Forward request
    BE->>ML: Validate + compute prediction/SHAP
    ML-->>BE: Scores, labels, explanations
    BE->>DB: Save investigation/report (if requested)
    DB-->>BE: Persisted ids/records
    BE-->>FE: JSON response
    FE-->>U: Visualized result/history/report
```

## Planned vs implemented

- **Implemented:** all components shown above, including local selected model
  artifacts and SHAP payloads.
- **Planned/optional only:** live threat-provider enrichment unless credentials
  are configured; broader unseen-domain/temporal evaluation experiments.
