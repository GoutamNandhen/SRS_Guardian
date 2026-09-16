from pathlib import Path
import joblib

MODEL_PATH = Path("backend/app/ml/artifacts/classifier_pipeline.joblib")

_PIPELINE = None


def get_pipeline():
    global _PIPELINE
    if _PIPELINE is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Classifier artifact not found at {MODEL_PATH}. Run train_classifier.py first."
            )
        _PIPELINE = joblib.load(MODEL_PATH)
    return _PIPELINE


def classify(text: str) -> tuple[str, float]:
    """Classifies a requirement text into 'Functional' or 'Non-Functional'.

    Returns (label, probability).
    """
    pipeline = get_pipeline()
    vectorizer = pipeline["vectorizer"]
    clf = pipeline["classifier"]
    classes = pipeline["classes"]

    X_vec = vectorizer.transform([text])
    probabilities = clf.predict_proba(X_vec)[0]
    pred_idx = int(clf.predict(X_vec)[0])

    label = classes[pred_idx]
    confidence = float(probabilities[pred_idx])

    return label, confidence
