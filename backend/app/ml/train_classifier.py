from pathlib import Path
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split


def load_promise_dataset() -> pd.DataFrame:
    csv_path = Path("data/processed/promise_exp.csv")
    arff_path = Path("data/raw/PROMISE_exp.arff")

    if csv_path.exists():
        return pd.read_csv(csv_path)

    if not arff_path.exists():
        raise FileNotFoundError(f"Neither {csv_path} nor {arff_path} found.")

    raw_text = arff_path.read_text(encoding="utf-8", errors="ignore")
    data_idx = raw_text.find("@DATA")
    data_section = raw_text[data_idx + len("@DATA") :].strip()
    lines = [
        l.strip()
        for l in data_section.splitlines()
        if l.strip() and not l.startswith("%")
    ]

    rows = []
    for line in lines:
        parts = line.rsplit(",", 1)
        if len(parts) == 2:
            text, label = parts[0].strip().strip("'\""), parts[1].strip()
            rows.append({"text": text, "class": label})

    df = pd.DataFrame(rows)
    df["binary_label"] = df["class"].apply(
        lambda c: "Functional" if c.strip().upper() == "F" else "Non-Functional"
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    return df


def train_and_evaluate():
    df = load_promise_dataset()

    X = df["text"].values
    # 0 = Functional, 1 = Non-Functional
    label_mapping = {"Functional": 0, "Non-Functional": 1}
    y = df["binary_label"].map(label_mapping).values

    # Stratified Train/Test Split (80% train, 20% test, fixed random_state)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    # Save held-out test split for Phase 16 evaluation
    Path("data/test").mkdir(parents=True, exist_ok=True)
    test_df = pd.DataFrame(
        {
            "text": X_test,
            "label_int": y_test,
            "binary_label": [
                "Functional" if i == 0 else "Non-Functional" for i in y_test
            ],
        }
    )
    test_df.to_csv("data/test/promise_test_split.csv", index=False)

    # TF-IDF Vectorizer with word 1-2 grams, min_df=2, sublinear_tf=True
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, sublinear_tf=True
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Logistic Regression Classifier
    clf = LogisticRegression(random_state=42, max_iter=1000)
    clf.fit(X_train_vec, y_train)

    # Predictions on test set
    y_pred = clf.predict(X_test_vec)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, pos_label=1)
    rec = recall_score(y_test, y_pred, pos_label=1)
    f1 = f1_score(y_test, y_pred, pos_label=1)
    cm = confusion_matrix(y_test, y_pred)

    print("==================================================")
    print("CLASSIFIER EVALUATION METRICS (ACTUAL TEST RUN)")
    print("==================================================")
    print(f"Total Test Samples: {len(y_test)}")
    print(f"Accuracy:  {acc:.4f} ({acc*100:.2f}%)")
    print(f"Precision: {prec:.4f} (Non-Functional)")
    print(f"Recall:    {rec:.4f} (Non-Functional)")
    print(f"F1-Score:  {f1:.4f}")
    print("\nConfusion Matrix [ [TN, FP], [FN, TP] ]:")
    print(f"  [TN={cm[0,0]} (True Functional),  FP={cm[0,1]} (False Non-Func)]")
    print(f"  [FN={cm[1,0]} (False Functional), TP={cm[1,1]} (True Non-Func)]")
    print("\nDetailed Classification Report:")
    print(
        classification_report(
            y_test, y_pred, target_names=["Functional", "Non-Functional"]
        )
    )

    # Save model artifacts
    artifacts_dir = Path("backend/app/ml/artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Background sample for SHAP explanation
    bg_sample = X_train_vec[:100]

    artifact = {
        "vectorizer": vectorizer,
        "classifier": clf,
        "classes": ["Functional", "Non-Functional"],
        "background_sample": bg_sample,
        "metrics": {
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "confusion_matrix": cm.tolist(),
        },
    }
    model_file = artifacts_dir / "classifier_pipeline.joblib"
    joblib.dump(artifact, model_file)
    print(f"\nSaved trained pipeline and artifacts to {model_file}")

    # Generate Global SHAP Summary Plot
    figures_dir = Path("docs/figures")
    figures_dir.mkdir(parents=True, exist_ok=True)
    explainer = shap.LinearExplainer(clf, X_train_vec)
    shap_values = explainer(X_test_vec)

    feature_names = vectorizer.get_feature_names_out()
    plt.figure(figsize=(10, 6))
    shap.summary_plot(
        shap_values.values,
        features=X_test_vec.toarray(),
        feature_names=feature_names,
        show=False,
        max_display=15,
    )
    plt.title(
        "Global SHAP Summary Plot (TF-IDF + Logistic Regression)", fontsize=12
    )
    plt.tight_layout()
    summary_plot_path = figures_dir / "shap_summary.png"
    plt.savefig(summary_plot_path, dpi=200)
    plt.close()
    print(f"Generated global SHAP summary plot at {summary_plot_path}")


if __name__ == "__main__":
    train_and_evaluate()
