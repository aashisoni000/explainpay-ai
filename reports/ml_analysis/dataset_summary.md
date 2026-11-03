# ExplainPay: verified dataset and model evidence

Generated from `graph_data/*_audit.json` and CSV exports. Full precision lives in CSVs; prose tables round for readability. Sources and models were read locally. No retraining, URL visits, or external provider submissions occurred.

## Reproducibility
Raw SHA-256, ordered feature schema, exact cleaning results, 60/20/20 stratified split (seed 42), saved 100-row SHAP background, training-only scaler means, and selected validation/test predictions were checked against artifacts. A discrepancy aborts extraction. Cleaned row indices in split and explanation files are local analysis identifiers, not original merchant/transaction IDs. Histogram counts cover complete ranges; standard deviation uses ddof=1. Correlations are Pearson coefficients; constant-column correlations would be undefined, never replaced with zero.

## ULB credit card transactions

Source: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

Local input: `data/raw/transactions/creditcard.csv`

Raw size: **284,807 rows x 31 columns**. Cleaned size: **283,726 rows x 30 input features**, plus binary target.

Raw majority/minority ratio: **577.876016:1**. Cleaned ratio: **598.843552:1**. The majority class is legitimate for fraud and phishing for the URL dataset.

### Class distribution
| population | class_label | class_name | count | proportion |
| --- | --- | --- | --- | --- |
| raw | 0 | Legitimate | 284315 | 0.99827251 |
| raw | 1 | Fraud | 492 | 0.0017274856 |
| cleaned | 0 | Legitimate | 283253 | 0.9983329 |
| cleaned | 1 | Fraud | 473 | 0.0016671014 |

### Missing values, types, and schema
| feature | dtype | missing_count | missing_percent |
| --- | --- | --- | --- |
| Time | float64 | 0 | 0 |
| V1 | float64 | 0 | 0 |
| V2 | float64 | 0 | 0 |
| V3 | float64 | 0 | 0 |
| V4 | float64 | 0 | 0 |
| V5 | float64 | 0 | 0 |
| V6 | float64 | 0 | 0 |
| V7 | float64 | 0 | 0 |
| V8 | float64 | 0 | 0 |
| V9 | float64 | 0 | 0 |
| V10 | float64 | 0 | 0 |
| V11 | float64 | 0 | 0 |
| V12 | float64 | 0 | 0 |
| V13 | float64 | 0 | 0 |
| V14 | float64 | 0 | 0 |
| V15 | float64 | 0 | 0 |
| V16 | float64 | 0 | 0 |
| V17 | float64 | 0 | 0 |
| V18 | float64 | 0 | 0 |
| V19 | float64 | 0 | 0 |
| V20 | float64 | 0 | 0 |
| V21 | float64 | 0 | 0 |
| V22 | float64 | 0 | 0 |
| V23 | float64 | 0 | 0 |
| V24 | float64 | 0 | 0 |
| V25 | float64 | 0 | 0 |
| V26 | float64 | 0 | 0 |
| V27 | float64 | 0 | 0 |
| V28 | float64 | 0 | 0 |
| Amount | float64 | 0 | 0 |
| Class | int64 | 0 | 0 |

Exact duplicate source rows: **1,081**. Cleaning record:
```json
{
  "duplicates_removed": 1081,
  "label_mapping": {
    "0": "legitimate",
    "1": "fraud"
  },
  "features": "V1-V28 are anonymized PCA components; original merchant identity is unavailable."
}
```

### Raw numerical statistics
All numeric columns including target; mean/median/std/min/max are descriptive, not fitted preprocessing. Target statistics summarize prevalence, not a feature.

| feature | count | mean | median | std | min | max | q25 | q75 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Time | 284807 | 94813.86 | 84692 | 47488.146 | 0 | 172792 | 54201.5 | 139320.5 |
| V1 | 284807 | 1.1751609e-15 | 0.018108799 | 1.9586958 | -56.40751 | 2.45493 | -0.92037338 | 1.3156417 |
| V2 | 284807 | 3.3849743e-16 | 0.065485556 | 1.6513086 | -72.715728 | 22.057729 | -0.59854991 | 0.80372387 |
| V3 | 284807 | -1.3795367e-15 | 0.17984634 | 1.516255 | -48.325589 | 9.3825584 | -0.89036484 | 1.0271955 |
| V4 | 284807 | 2.094852e-15 | -0.019846529 | 1.4158686 | -5.6831712 | 16.875344 | -0.84864012 | 0.74334129 |
| V5 | 284807 | 1.021879e-15 | -0.054335827 | 1.3802467 | -113.74331 | 34.801666 | -0.69159707 | 0.61192644 |
| V6 | 284807 | 1.4944981e-15 | -0.27418708 | 1.3322711 | -26.160506 | 73.301626 | -0.76829561 | 0.3985649 |
| V7 | 284807 | -5.6203347e-16 | 0.040103083 | 1.2370936 | -43.557242 | 120.58949 | -0.55407588 | 0.57043607 |
| V8 | 284807 | 1.1496139e-16 | 0.022358036 | 1.1943529 | -73.216718 | 20.007208 | -0.20862974 | 0.32734586 |
| V9 | 284807 | -2.4141892e-15 | -0.051428732 | 1.0986321 | -13.434066 | 15.594995 | -0.64309757 | 0.59713903 |
| V10 | 284807 | 2.2385538e-15 | -0.092917384 | 1.0888498 | -24.588262 | 23.745136 | -0.53542573 | 0.45392345 |
| V11 | 284807 | 1.7244209e-15 | -0.032757354 | 1.020713 | -4.7974735 | 12.018913 | -0.7624942 | 0.73959341 |
| V12 | 284807 | -1.2454151e-15 | 0.14003259 | 0.99920139 | -18.683715 | 7.8483921 | -0.40557149 | 0.61823803 |
| V13 | 284807 | 8.2388998e-16 | -0.013568057 | 0.99527423 | -5.7918812 | 7.126883 | -0.6485393 | 0.66250496 |
| V14 | 284807 | 1.2134814e-15 | 0.050601319 | 0.95859561 | -19.214325 | 10.526766 | -0.42557401 | 0.49314985 |
| V15 | 284807 | 4.8666989e-15 | 0.04807155 | 0.91531601 | -4.4989447 | 8.8777416 | -0.58288428 | 0.64882081 |
| V16 | 284807 | 1.4362191e-15 | 0.066413321 | 0.87625289 | -14.129855 | 17.315112 | -0.46803677 | 0.52329631 |
| V17 | 284807 | -3.768179e-16 | -0.065675754 | 0.84933706 | -25.162799 | 9.2535263 | -0.48374831 | 0.39967498 |
| V18 | 284807 | 9.7078509e-16 | -0.0036363124 | 0.83817621 | -9.4987459 | 5.0410692 | -0.4988498 | 0.50080675 |
| V19 | 284807 | 1.0362492e-15 | 0.003734823 | 0.8140405 | -7.2135274 | 5.5919714 | -0.45629892 | 0.45894936 |
| V20 | 284807 | 6.4186777e-16 | -0.062481092 | 0.77092502 | -54.49772 | 39.420904 | -0.21172136 | 0.13304084 |
| V21 | 284807 | 1.6286197e-16 | -0.029450168 | 0.73452401 | -34.830382 | 27.202839 | -0.22839495 | 0.1863772 |
| V22 | 284807 | -3.5765767e-16 | 0.0067819425 | 0.72570156 | -10.933144 | 10.50309 | -0.54235037 | 0.52855364 |
| V23 | 284807 | 2.618565e-16 | -0.01119293 | 0.6244603 | -44.807735 | 22.528412 | -0.16184635 | 0.14764206 |
| V24 | 284807 | 4.4739142e-15 | 0.040976056 | 0.60564707 | -2.8366269 | 4.5845491 | -0.35458614 | 0.4395266 |
| V25 | 284807 | 5.1093952e-16 | 0.016593502 | 0.52127807 | -10.295397 | 7.5195887 | -0.31714505 | 0.35071556 |
| V26 | 284807 | 1.6861004e-15 | -0.052139108 | 0.48222701 | -2.6045506 | 3.5173456 | -0.32698393 | 0.24095217 |
| V27 | 284807 | -3.6614006e-16 | 0.001342146 | 0.40363249 | -22.565679 | 31.612198 | -0.070839529 | 0.09104512 |
| V28 | 284807 | -1.2274524e-16 | 0.011243832 | 0.33008326 | -15.430084 | 33.847808 | -0.052959793 | 0.078279955 |
| Amount | 284807 | 88.349619 | 22 | 250.12011 | 0 | 25691.16 | 5.6 | 77.165 |
| Class | 284807 | 0.0017274856 | 0 | 0.04152719 | 0 | 1 | 0 | 0 |

### Actual model-input numerical statistics
| feature | count | mean | median | std | min | max | q25 | q75 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Time | 283726 | 94811.078 | 84692.5 | 47481.048 | 0 | 172792 | 54204.75 | 139298 |
| V1 | 283726 | 0.0059171498 | 0.020384055 | 1.9480261 | -56.40751 | 2.45493 | -0.91595133 | 1.3160678 |
| V2 | 283726 | -0.0041347556 | 0.063949172 | 1.646703 | -72.715728 | 22.057729 | -0.60032057 | 0.80028289 |
| V3 | 283726 | 0.0016131194 | 0.17996273 | 1.5086819 | -48.325589 | 9.3825584 | -0.889682 | 1.02696 |
| V4 | 283726 | -0.0029663077 | -0.022248017 | 1.414184 | -5.6831712 | 16.875344 | -0.85013447 | 0.73964696 |
| V5 | 283726 | 0.0018275601 | -0.053467607 | 1.3770083 | -113.74331 | 34.801666 | -0.68982973 | 0.61221796 |
| V6 | 283726 | -0.0011394882 | -0.27516764 | 1.3319306 | -26.160506 | 73.301626 | -0.76903077 | 0.39679214 |
| V7 | 283726 | 0.0018006918 | 0.040859471 | 1.2276639 | -43.557242 | 120.58949 | -0.55250944 | 0.57047387 |
| V8 | 283726 | -0.00085445257 | 0.021897947 | 1.1790544 | -73.216718 | 20.007208 | -0.20882847 | 0.32570368 |
| V9 | 283726 | -0.0015961996 | -0.052595651 | 1.0954925 | -13.434066 | 15.594995 | -0.64422077 | 0.59597686 |
| V10 | 283726 | -0.0014407105 | -0.093236526 | 1.0764074 | -24.588262 | 23.745136 | -0.53557811 | 0.45361873 |
| V11 | 283726 | 0.00020175764 | -0.03230594 | 1.0187202 | -4.7974735 | 12.018913 | -0.7616493 | 0.73957919 |
| V12 | 283726 | -0.00071478766 | 0.13907201 | 0.99467445 | -18.683715 | 7.8483921 | -0.40619773 | 0.61697649 |
| V13 | 283726 | 0.00060337579 | -0.01292699 | 0.99542964 | -5.7918812 | 7.126883 | -0.64786208 | 0.66317831 |
| V14 | 283726 | 0.0002523173 | 0.050208678 | 0.95221509 | -19.214325 | 10.526766 | -0.42573247 | 0.49233554 |
| V15 | 283726 | 0.001042838 | 0.049298852 | 0.91489363 | -4.4989447 | 8.8777416 | -0.58145185 | 0.65010412 |
| V16 | 283726 | 0.0011620128 | 0.067119138 | 0.87369633 | -14.129855 | 17.315112 | -0.46685962 | 0.52351158 |
| V17 | 283726 | 0.00017016094 | -0.065866933 | 0.84250732 | -25.162799 | 9.2535263 | -0.48392758 | 0.39897171 |
| V18 | 283726 | 0.001515166 | -0.0021417562 | 0.83737753 | -9.4987459 | 5.0410692 | -0.4980143 | 0.50195567 |
| V19 | 283726 | -0.00026426359 | 0.0033670829 | 0.81337855 | -7.2135274 | 5.5919714 | -0.45628892 | 0.45850793 |
| V20 | 283726 | 0.00018717525 | -0.062353459 | 0.76998424 | -54.49772 | 39.420904 | -0.21146928 | 0.13320712 |
| V21 | 283726 | -0.00037059312 | -0.029440589 | 0.72390937 | -34.830382 | 27.202839 | -0.22830491 | 0.1861936 |
| V22 | 283726 | -1.5027563e-05 | 0.0066748952 | 0.72455047 | -10.933144 | 10.50309 | -0.54269971 | 0.5282452 |
| V23 | 283726 | 0.00019817072 | -0.011158577 | 0.62370238 | -44.807735 | 22.528412 | -0.16170345 | 0.14774844 |
| V24 | 283726 | 0.00021420682 | 0.041015733 | 0.6056267 | -2.8366269 | 4.5845491 | -0.35445344 | 0.43973848 |
| V25 | 283726 | -0.00023238699 | 0.016278362 | 0.52122032 | -10.295397 | 7.5195887 | -0.31748537 | 0.35066737 |
| V26 | 283726 | 0.00014944109 | -0.052171628 | 0.48205294 | -2.6045506 | 3.5173456 | -0.3267634 | 0.2402613 |
| V27 | 283726 | 0.0017630316 | 0.0014785948 | 0.39574388 | -22.565679 | 31.612198 | -0.070640822 | 0.091208165 |
| V28 | 283726 | 0.0005473121 | 0.011287604 | 0.3280266 | -15.430084 | 33.847808 | -0.052818036 | 0.078276094 |
| Amount | 283726 | 88.472687 | 22 | 250.39944 | 0 | 25691.16 | 5.6 | 77.51 |

### Train / validation / test split
| split | total | class_0 | class_1 |
| --- | --- | --- | --- |
| train | 170235 | 169951 | 284 |
| validation | 56745 | 56651 | 94 |
| test | 56746 | 56651 | 95 |

### Feature meanings

| feature | meaning | population |
| --- | --- | --- |
| Time | Seconds elapsed since the first source transaction; random splits overlap in time. | source |
| V1 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V2 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V3 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V4 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V5 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V6 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V7 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V8 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V9 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V10 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V11 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V12 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V13 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V14 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V15 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V16 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V17 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V18 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V19 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V20 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V21 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V22 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V23 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V24 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V25 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V26 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V27 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| V28 | Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable. | source |
| Amount | Source transaction amount; upstream ULB documentation describes euros. Application conservatively displays supplied amount without assuming currency for arbitrary uploads. | source |
| Class | Binary target: 1 fraudulent, 0 legitimate. Excluded from model inputs. | source |

### Every trained supervised candidate: validation and held-out test
Accuracy, specificity and false-negative rate below are computed exactly from saved confusion counts; other metrics are retained from the original experiment. Logistic Regression metrics are historical aggregates; its fitted estimator was not serialized.

| model | split | selected | threshold | precision | recall | f1 | roc_auc | pr_auc | false_positive_rate | accuracy | specificity | false_negative_rate | tn | fp | fn | tp | support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | validation | False | 0.99999992 | 0.875 | 0.81914894 | 0.84615385 | 0.97903823 | 0.78761655 | 0.00019417133 | 0.99950656 | 0.99980583 | 0.18085106 | 56640 | 11 | 17 | 77 | 56745 |
| xgboost | validation | True | 0.96870559 | 0.87096774 | 0.86170213 | 0.86631016 | 0.9746736 | 0.86907188 | 0.00021182327 | 0.99955943 | 0.99978818 | 0.13829787 | 56639 | 12 | 13 | 81 | 56745 |
| logistic_regression | test | False | 0.99999992 | 0.88607595 | 0.73684211 | 0.8045977 | 0.9645616 | 0.68650998 | 0.00015886745 | 0.99940084 | 0.99984113 | 0.26315789 | 56642 | 9 | 25 | 70 | 56746 |
| xgboost | test | True | 0.96870559 | 0.89873418 | 0.74736842 | 0.81609195 | 0.96739798 | 0.80004854 | 0.00014121551 | 0.99943608 | 0.99985878 | 0.25263158 | 56643 | 8 | 24 | 71 | 56746 |

### SHAP sampling and explainers
```json
{
  "sample_size": 512,
  "sample_class_distribution": {
    "0": 511,
    "1": 1
  },
  "sampling": "Stratified held-out test sample, seed42; original feature values retained; no raw URLs exported.",
  "explainer": "TreeExplainer",
  "explained_model": "xgboost",
  "background_size": 100,
  "units": "log-odds",
  "maximum_probability_reconstruction_error": 6.544666117380693e-08,
  "example_selection": "First held-out row in each actual outcome TP/FP/FN/TN; retrospective examples, not random representative cases."
}
```

### Top global SHAP contributions
Mean absolute log-odds contribution on the documented 512-row test sample, not the complete population. Gain importance is a different model-internal quantity.

| feature | mean_abs_shap | mean_shap | model_gain_importance | n_samples |
| --- | --- | --- | --- | --- |
| V4 | 0.93499355 | -0.044007207 | 0.058874372 | 512 |
| V14 | 0.61666444 | -0.039239223 | 0.36969659 | 512 |
| V8 | 0.56261061 | -0.017526613 | 0.047683392 | 512 |
| V15 | 0.34232334 | -0.0088928032 | 0.015066145 | 512 |
| V3 | 0.30377696 | -0.064001622 | 0.020227322 | 512 |
| V12 | 0.25445266 | -0.020381899 | 0.039805707 | 512 |
| V6 | 0.25417398 | -0.0047995891 | 0.011208507 | 512 |
| V28 | 0.21186164 | -0.0011752972 | 0.023559444 | 512 |
| V11 | 0.1976469 | 0.01905233 | 0.018354611 | 512 |
| V1 | 0.19668118 | -0.030206306 | 0.011860976 | 512 |
| V26 | 0.17293619 | 0.017944546 | 0.016683778 | 512 |
| V27 | 0.16140785 | -0.0051410506 | 0.010230026 | 512 |
| V19 | 0.1374691 | -0.0055032138 | 0.031001132 | 512 |
| V20 | 0.12175017 | -0.0022608449 | 0.029366231 | 512 |
| V25 | 0.1174788 | -0.0014192519 | 0.012680405 | 512 |
| V18 | 0.11529412 | -0.036269722 | 0.0083426517 | 512 |
| V5 | 0.098808133 | -0.00051409697 | 0.013432612 | 512 |
| V7 | 0.091266987 | 0.019819923 | 0.0099886106 | 512 |
| V17 | 0.090290864 | -0.014790975 | 0.014750452 | 512 |
| V24 | 0.083935138 | -0.0020268074 | 0.0093726134 | 512 |
| V2 | 0.082119433 | 0.0090033142 | 0.0089819273 | 512 |
| V16 | 0.071537622 | 0.0013187592 | 0.012589543 | 512 |
| V13 | 0.066222931 | -0.0061516087 | 0.034874953 | 512 |
| Time | 0.065877251 | 0.0090911486 | 0.0060501732 | 512 |
| V10 | 0.059204389 | 0.012244168 | 0.075518489 | 512 |
| Amount | 0.054589544 | 0.0042367892 | 0.030103197 | 512 |
| V9 | 0.052939039 | 0.0102786 | 0.0074588871 | 512 |
| V22 | 0.050363706 | -0.012509435 | 0.019431949 | 512 |
| V23 | 0.03764536 | -0.0052091744 | 0.0096689826 | 512 |
| V21 | 0.036745136 | 7.8497355e-05 | 0.023136249 | 512 |

### Actual time ranges
```json
{
  "train": {
    "time_min": 0.0,
    "time_max": 172788.0
  },
  "validation": {
    "time_min": 0.0,
    "time_max": 172792.0
  },
  "test": {
    "time_min": 2.0,
    "time_max": 172786.0
  }
}
```
No chronological/forward-looking fraud evaluation was conducted.

## Phishing URLs with extracted features

Source: https://www.kaggle.com/datasets/victusadi/phishing-urls-dataset-with-extracted-features

Local input: `data/raw/websites/phishing_features.csv`

Raw size: **160,064 rows x 13 columns**. Cleaned size: **103,264 rows x 15 input features**, plus binary target.

Raw majority/minority ratio: **194.200000:1**. Cleaned ratio: **124.931707:1**. The majority class is legitimate for fraud and phishing for the URL dataset.

### Class distribution
| population | class_label | class_name | count | proportion |
| --- | --- | --- | --- | --- |
| raw | 0 | Legitimate | 820 | 0.0051229508 |
| raw | 1 | Phishing | 159244 | 0.99487705 |
| cleaned | 0 | Legitimate | 820 | 0.0079408119 |
| cleaned | 1 | Phishing | 102444 | 0.99205919 |

### Missing values, types, and schema
| feature | dtype | missing_count | missing_percent |
| --- | --- | --- | --- |
| url | object | 0 | 0 |
| label | int64 | 0 | 0 |
| url_length | int64 | 0 | 0 |
| num_dots | int64 | 0 | 0 |
| has_https | int64 | 0 | 0 |
| has_ip | int64 | 0 | 0 |
| num_subdirs | int64 | 0 | 0 |
| num_params | int64 | 0 | 0 |
| suspicious_words | int64 | 0 | 0 |
| tld | object | 821 | 0.51291983 |
| special_char_count | int64 | 0 | 0 |
| digits_count | int64 | 0 | 0 |
| entropy | float64 | 0 | 0 |

Exact duplicate source rows: **0**. Cleaning record:
```json
{
  "url_column": "url",
  "target_column": "label",
  "label_mapping": {
    "1": "phishing",
    "0": "legitimate"
  },
  "invalid_urls_removed": 56678,
  "invalid_url_reasons": {
    "Invalid website URL: A valid public hostname is required.": 817,
    "Invalid website URL: Only standard HTTP/HTTPS ports are supported.": 55814,
    "Invalid website URL: URLs containing credentials are not allowed.": 35,
    "URL must not contain whitespace, controls, or backslashes.": 9,
    "URL must contain 1 to 2048 characters.": 3
  },
  "duplicate_urls_removed": 122,
  "features": "Only deterministic URL lexical features; supplied extracted features are not trusted."
}
```

### Raw numerical statistics
All numeric columns including target; mean/median/std/min/max are descriptive, not fitted preprocessing. Target statistics summarize prevalence, not a feature.

| feature | count | mean | median | std | min | max | q25 | q75 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| label | 160064 | 0.99487705 | 1 | 0.071391442 | 0 | 1 | 1 | 1 |
| url_length | 160064 | 55.107382 | 37 | 101.78247 | 6 | 25523 | 30 | 65 |
| num_dots | 160064 | 2.9989629 | 3 | 1.1192099 | 1 | 59 | 2 | 4 |
| has_https | 160064 | 0.43408886 | 0 | 0.49563823 | 0 | 1 | 0 | 1 |
| has_ip | 160064 | 0.48547456 | 0 | 0.49979053 | 0 | 1 | 0 | 1 |
| num_subdirs | 160064 | 4.1284361 | 3 | 2.09018 | 0 | 104 | 3 | 4 |
| num_params | 160064 | 0.2214989 | 0 | 0.93560752 | 0 | 45 | 0 | 0 |
| suspicious_words | 160064 | 0.023809226 | 0 | 0.16823495 | 0 | 3 | 0 | 0 |
| special_char_count | 160064 | 1.4954456 | 0 | 3.699627 | 0 | 264 | 0 | 1 |
| digits_count | 160064 | 12.737036 | 12 | 17.420579 | 0 | 3413 | 3 | 16 |
| entropy | 160064 | 4.2461002 | 4.1714653 | 0.47927533 | 2.0588139 | 6.0304217 | 3.9077343 | 4.4848501 |

### Actual model-input numerical statistics
| feature | count | mean | median | std | min | max | q25 | q75 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| url_length | 103264 | 55.195228 | 39 | 49.497842 | 13 | 1585 | 31 | 63 |
| domain_length | 103264 | 17.67493 | 15 | 10.228919 | 4 | 112 | 12 | 21 |
| dot_count | 103264 | 2.6007612 | 2 | 1.1232398 | 1 | 59 | 2 | 3 |
| subdomain_count | 103264 | 0.61450263 | 1 | 0.6052663 | 0 | 8 | 0 | 1 |
| hyphen_count | 103264 | 0.66549814 | 0 | 1.2668803 | 0 | 50 | 0 | 1 |
| digit_count | 103264 | 8.6637744 | 5 | 12.059591 | 0 | 347 | 1 | 12 |
| ip_hostname | 103264 | 0.21354005 | 0 | 0.40980767 | 0 | 1 | 0 | 0 |
| https | 103264 | 0.64997482 | 1 | 0.47697983 | 0 | 1 | 0 | 1 |
| suspicious_tokens | 103264 | 0.029235745 | 0 | 0.18879698 | 0 | 3 | 0 | 0 |
| parameter_count | 103264 | 0.33352378 | 0 | 1.1057858 | 0 | 43 | 0 | 0 |
| suspicious_extension | 103264 | 0.075612024 | 0 | 0.26437761 | 0 | 1 | 0 | 0 |
| url_entropy | 103264 | 4.3168808 | 4.2499706 | 0.46353854 | 2.3533378 | 6.0304217 | 4.0165645 | 4.4998284 |
| path_length | 103264 | 22.904788 | 11 | 28.65405 | 1 | 997 | 7 | 26 |
| at_count | 103264 | 0.0024790827 | 0 | 0.051073839 | 0 | 2 | 0 | 0 |
| encoded_count | 103264 | 0.081219011 | 0 | 1.4647825 | 0 | 264 | 0 | 0 |

### Train / validation / test split
| split | total | class_0 | class_1 |
| --- | --- | --- | --- |
| train | 61958 | 492 | 61466 |
| validation | 20653 | 164 | 20489 |
| test | 20653 | 164 | 20489 |

### Feature meanings

| feature | meaning | population |
| --- | --- | --- |
| url | Source URL string; normalized and validated before feature recomputation. | source |
| label | Publisher encoding: 1 phishing, 0 benign. | source |
| url_length | Publisher: total source URL length; NOT used directly by the trained pipeline. | source |
| num_dots | Publisher: number of dots; extractor details not included in repository. | source |
| has_https | Publisher: HTTPS indicator; source values not used in inference. | source |
| has_ip | Publisher: IP-in-URL indicator; differs from our hostname parser. | source |
| num_subdirs | Publisher: slash count; not an actual parsed subdomain count. | source |
| num_params | Publisher: question-mark/ampersand count, not our parsed parameter pairs. | source |
| suspicious_words | Publisher suspicious-token feature; exact source token list unavailable. | source |
| tld | Publisher top-level domain; 821 missing values, unused by selected preprocessing. | source |
| special_char_count | Publisher count of -_%@=~ characters; source implementation not saved. | source |
| digits_count | Publisher digit count; source implementation not saved. | source |
| entropy | Publisher URL entropy; source normalization details unavailable. | source |
| url_length | Character count of normalized URL, including scheme and query; fragment removed. | recomputed_model_input |
| domain_length | Length of normalized ASCII/IDNA hostname. | recomputed_model_input |
| dot_count | Dot characters anywhere in normalized URL, not only hostname. | recomputed_model_input |
| subdomain_count | max(hostname dot-separated labels minus 2, 0); 0 for IP. Not public-suffix-aware. | recomputed_model_input |
| hyphen_count | Hyphens anywhere in normalized URL. | recomputed_model_input |
| digit_count | Characters for which Python str.isdigit() is true in normalized URL. | recomputed_model_input |
| ip_hostname | 1 if hostname parses as a public IP; otherwise 0. | recomputed_model_input |
| https | 1 for normalized HTTPS scheme; encryption is not a safety guarantee. | recomputed_model_input |
| suspicious_tokens | Count of distinct substrings present: login, verify, secure, account, update, bank, wallet, password. | recomputed_model_input |
| parameter_count | Parsed query pairs, including blank values, using urllib.parse.parse_qsl. | recomputed_model_input |
| suspicious_extension | Path ends with .exe, .zip, .scr, .apk, or .js, case insensitive. | recomputed_model_input |
| url_entropy | Shannon character entropy (bits/character) of normalized URL. | recomputed_model_input |
| path_length | Character count of URL path (default /). | recomputed_model_input |
| at_count | @ characters anywhere; credential URLs are already rejected. | recomputed_model_input |
| encoded_count | Percent-sign characters; this is not a validated count of encoded bytes. | recomputed_model_input |

### Every trained supervised candidate: validation and held-out test
Accuracy, specificity and false-negative rate below are computed exactly from saved confusion counts; other metrics are retained from the original experiment. Logistic Regression metrics are historical aggregates; its fitted estimator was not serialized.

| model | split | selected | threshold | precision | recall | f1 | roc_auc | pr_auc | false_positive_rate | accuracy | specificity | false_negative_rate | tn | fp | fn | tp | support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | validation | False | 0.021696551 | 0.99921757 | 0.99726683 | 0.99824124 | 0.99830159 | 0.99998642 | 0.097560976 | 0.99651382 | 0.90243902 | 0.0027331739 | 148 | 16 | 56 | 20433 | 20653 |
| xgboost | validation | True | 0.01491343 | 0.99824339 | 0.99848699 | 0.99836518 | 0.99879114 | 0.99999016 | 0.2195122 | 0.99675592 | 0.7804878 | 0.001513007 | 128 | 36 | 31 | 20458 | 20653 |
| logistic_regression | test | False | 0.021696551 | 0.99902181 | 0.99692518 | 0.9979724 | 0.99690256 | 0.99997493 | 0.12195122 | 0.99598121 | 0.87804878 | 0.0030748206 | 144 | 20 | 63 | 20426 | 20653 |
| xgboost | test | True | 0.01491343 | 0.99819468 | 0.99848699 | 0.99834082 | 0.99893994 | 0.9999914 | 0.22560976 | 0.9967075 | 0.77439024 | 0.001513007 | 127 | 37 | 31 | 20458 | 20653 |

### SHAP sampling and explainers
```json
{
  "sample_size": 512,
  "sample_class_distribution": {
    "1": 508,
    "0": 4
  },
  "sampling": "Stratified held-out test sample, seed42; original feature values retained; no raw URLs exported.",
  "explainer": "TreeExplainer",
  "explained_model": "xgboost",
  "background_size": 100,
  "units": "log-odds",
  "maximum_probability_reconstruction_error": 1.301439520595693e-07,
  "example_selection": "First held-out row in each actual outcome TP/FP/FN/TN; retrospective examples, not random representative cases."
}
```

### Top global SHAP contributions
Mean absolute log-odds contribution on the documented 512-row test sample, not the complete population. Gain importance is a different model-internal quantity.

| feature | mean_abs_shap | mean_shap | model_gain_importance | n_samples |
| --- | --- | --- | --- | --- |
| url_length | 0.54548573 | 0.021700695 | 0.13025449 | 512 |
| path_length | 0.53424511 | -0.11678539 | 0.58878958 | 512 |
| url_entropy | 0.37906543 | -0.027958636 | 0.0091301464 | 512 |
| dot_count | 0.22757214 | 0.012045246 | 0.14268689 | 512 |
| domain_length | 0.16030483 | -0.02724611 | 0.027133649 | 512 |
| https | 0.1105107 | -0.024610898 | 0.059698839 | 512 |
| hyphen_count | 0.083437888 | 0.0084379119 | 0.029190164 | 512 |
| digit_count | 0.072832968 | -0.00047768688 | 0.0056174803 | 512 |
| subdomain_count | 0.014762914 | 0.00073957729 | 0.0074987654 | 512 |
| ip_hostname | 0 | 0 | 0 | 512 |
| suspicious_tokens | 0 | 0 | 0 | 512 |
| parameter_count | 0 | 0 | 0 | 512 |
| suspicious_extension | 0 | 0 | 0 | 512 |
| at_count | 0 | 0 | 0 | 512 |
| encoded_count | 0 | 0 | 0 | 512 |

### Actual hostname overlap audit
```json
{
  "train_unique_hostnames": 25349,
  "validation_unique_hostnames": 10238,
  "test_unique_hostnames": 10317,
  "train_test_shared_hostnames": 3749,
  "test_rows_with_training_hostname": 13840,
  "test_rows": 20653,
  "method": "Exact normalized hostname overlap, not registrable-domain grouping; no DNS or website fetch."
}
```
This is a URL-level random holdout, NOT an unseen-domain benchmark. Exact URL deduplication does not prevent related domains/paths from crossing splits.

## Graph-ready data inventory

- `graph_data/*_class_distribution.csv`: raw and cleaned class counts/proportions.
- `graph_data/*_histograms.csv`: complete 50-bin per-class feature distributions for source and cleaned numeric inputs.
- `graph_data/*_raw_statistics.csv`, `*_cleaned_statistics.csv`: all numerical summaries.
- `graph_data/*_raw_class_statistics.csv`, `*_class_statistics.csv`: class-conditioned means, medians, standard deviations, ranges and quartiles.
- `graph_data/*_raw_correlation.csv`, `*_correlation.csv`: raw/cleaned Pearson matrices; target associations are descriptive, not causal.
- `graph_data/*_missing_values.csv`: every source column, including zero missing counts.
- `graph_data/*_split_assignments.csv`, `*_heldout_scores.csv`: exact local cleaned indices, split membership and selected-model test scores.
- Root `*_model_results.csv`, `*_confusion_matrix.csv`, `*_roc_data.csv`, `*_pr_data.csv`: actual saved/reproduced supervised results.
- `shap_analysis/*_values.csv`: long-form beeswarm data; original feature values and log-odds SHAP values, no URL strings.
- `shap_analysis/*_examples.csv`: complete per-feature explanations for one actual TP/FP/FN/TN case where present.
- `graph_data/*_parameters.json`: fitted pipeline configurations; JSON string `nan` denotes XGBoost's missing-value sentinel, not a fabricated numeric result.
- `manifest.json`: input/artifact hashes, versions and audit execution metadata.

## Scientific cautions

1. Fraud has only 95 positive test examples; 24 are missed by selected XGBoost.
2. Phishing test prevalence is about 99.2%; its no-skill AP baseline is already about 0.992. Very high AP/F1 must not hide 37 false alarms among only 164 benign test examples.
3. Logistic Regression has lower phishing benign false-positive rate (20/164) than selected XGBoost (37/164). Selection followed validation AP, not specificity. Do not reselect or retune using these test results.
4. SHAP global sampling preserves prevalence: fraud 511 negative/1 positive, phishing 4 negative/508 positive. These rankings are dominated by the majority population; class-conditioned explanation studies remain needed.
5. High confidence scores are not calibrated probabilities. No probability-calibration or confidence-interval experiment was saved.
6. Exact domain overlap, random time overlap, source imbalance and the URL rejection policy limit external validity.
