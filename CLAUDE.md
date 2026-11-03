# ExplainPay working rules

These are project-specific rules inspired by observations about coding-agent
failures, not an official document by Andrej Karpathy.

## Think before coding
- Inspect relevant existing code and actual dataset schemas before editing.
- State material assumptions. Verify dependency compatibility.
- Preserve the root Next.js App Router structure; the backend lives in `backend`.

## Simplicity first
- Implement requested behavior, not speculative abstractions or extra services.
- Reuse components, types, dependencies, and preprocessing.
- Keep communication concise. Spend tokens on engineering, not narration.

## Surgical changes
- Preserve the existing homepage, visual identity, and Three.js shader.
- Do not reformat or remove unrelated working code.
- Never overwrite another contributor's changes; inspect diffs before finishing.

## Goal-driven execution
- Define measurable success criteria; implement and validate logical units.
- Test actual frontend/API/PostgreSQL integration, not only UI appearance.
- Fix failures at their cause. Never claim unexecuted tests passed.
- Missing datasets block training, not unrelated implementation.

## Scientific and engineering integrity
- Strict TypeScript; typed Python. No unexplained `any`, silent errors, or fake APIs.
- Train only on the actual downloaded Kaggle datasets. Inspect phishing labels.
- Keep train, validation, and test sets separate; deduplicate before splitting.
- Fit preprocessing on training data only; share it with inference.
- Select models and thresholds on validation data, never on the test set.
- Persist real artifacts, evaluations, and SHAP explanations; never invent metrics.
- V1-V28 are anonymized PCA components, not merchant or device attributes.
- Anomaly, fraud classification, phishing classification, and provider evidence
  are distinct signals, not proof. No detections does not establish safety.
- Missing models return explicit errors; missing optional providers are visible.
- No placeholder endpoints, dead buttons, fake switches, or fabricated history.

## Data and security
- Never commit raw/processed datasets, model binaries, credentials, or `.env`.
- `data/raw/`, `data/processed/`, and `data/models/` must remain ignored.
- Do not download datasets on the user's behalf without explicit permission.
- Never send financial rows or credentials to third-party services.
- Never fetch user-submitted website URLs; use validated lexical analysis and
  fixed trusted provider endpoints only. No private IPs or arbitrary redirects.
- Validate finite numbers, file sizes, CSV schemas, URLs, and report paths.
- Store only the input fields necessary for investigation.
- This unauthenticated academic demo binds to loopback; add authentication,
  authorization, rate limiting, and retention policies before public deployment.
- ExplainPay is educational decision support, not professional financial or
  cybersecurity advice.

Update these rules when the user corrects a recurring project mistake.
