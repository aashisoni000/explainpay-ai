export interface Contribution {
  feature: string;
  value: number;
  contribution: number;
}

export interface TransactionResult {
  id: string;
  upload_id: string | null;
  investigation_id: string;
  transaction_reference: string;
  amount: number;
  fraud_probability: number;
  prediction: number;
  risk_level: string;
  threshold: number;
  explanation: Contribution[];
  base_value: number;
  anomaly_score: number | null;
  is_anomaly: boolean | null;
  model_version: string;
  merchant_url: string | null;
  created_at: string;
}

export interface TransactionUpload {
  id: string;
  filename: string;
  total_records: number;
  processed_records: number;
  status: string;
  columns: string[];
  preview: Record<string, unknown>[];
  created_at: string;
  investigation_id: string;
}

export interface UploadDetail extends TransactionUpload {
  results?: TransactionResult[];
  summary?: { total: number; flagged: number; legitimate: number; high_risk: number };
  feature_importance?: { feature: string; importance: number }[];
}

export interface WebsiteScan {
  id: string;
  investigation_id: string;
  url: string;
  normalized_domain: string;
  ml_probability: number;
  ml_prediction: number;
  risk_level: string;
  threshold: number;
  explanation: Contribution[];
  features: Record<string, number>;
  model_version: string;
  scan_status: string;
  findings: { finding_type: string; severity: string; description: string; evidence: string; source: string }[];
  providers: { name: string; status: string; details: Record<string, unknown> }[];
  created_at: string;
}

export interface Investigation {
  id: string;
  investigation_type: string;
  title: string;
  status: string;
  risk_level: string | null;
  created_at: string;
  updated_at: string;
  resource_id: string | null;
  upload?: UploadDetail;
  transaction?: TransactionResult;
  website?: WebsiteScan;
}

export interface Report {
  id: string;
  investigation_id: string;
  report_type: string;
  created_at: string;
}

export interface SystemStatus {
  database: { available: boolean; error: string | null };
  models: {
    fraud: { available: boolean; error: string | null };
    phishing: { available: boolean; error: string | null };
  };
  providers: { virustotal: string; google_webrisk: string; rdap: string };
}

export interface Evaluation {
  precision: number;
  recall: number;
  f1: number;
  pr_auc: number;
  roc_auc: number;
  confusion_matrix: number[][];
  false_positive_rate: number;
  fraud_detection_rate: number;
  threshold: number;
}

export interface ModelMetrics {
  selected_model: string;
  threshold: number;
  threshold_selection: unknown;
  validation: { logistic_regression: Evaluation; xgboost: Evaluation };
  test: Evaluation;
  test_comparison: Record<string, Evaluation>;
  split: { train: number; validation: number; test: number; seed: number };
  class_distribution: unknown;
  scale_pos_weight: number;
  explanation_units: string;
  limitations: string[];
  created_at: string;
  dataset_sha256: string;
  inspection: unknown;
  preparation: unknown;
  versions: unknown;
}
