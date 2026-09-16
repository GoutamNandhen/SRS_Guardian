import shap
from backend.app.ml.classifier import get_pipeline

_EXPLAINER = None
_EXPLANATION_CACHE: dict[str, list[tuple[str, float]]] = {}


def get_explainer():
    global _EXPLAINER
    if _EXPLAINER is None:
        pipeline = get_pipeline()
        clf = pipeline["classifier"]
        bg = pipeline["background_sample"]
        _EXPLAINER = shap.LinearExplainer(clf, bg)
    return _EXPLAINER


def explain(
    text: str, requirement_id: int | str | None = None
) -> list[tuple[str, float]]:
    """Explains classification of text using SHAP LinearExplainer.

    Returns the top 8 tokens (token, shap_value) contributing to the predicted
    class. Results are cached per requirement_id or text hash.
    """
    cache_key = str(requirement_id) if requirement_id is not None else hash(text)
    if cache_key in _EXPLANATION_CACHE:
        return _EXPLANATION_CACHE[cache_key]

    pipeline = get_pipeline()
    vectorizer = pipeline["vectorizer"]
    clf = pipeline["classifier"]

    explainer = get_explainer()
    X_vec = vectorizer.transform([text])

    pred_class = clf.predict(X_vec)[0]  # 0 = Functional, 1 = Non-Functional
    sv = explainer(X_vec)

    feat_names = vectorizer.get_feature_names_out()
    nonzero_indices = X_vec.nonzero()[1]

    # For Non-Functional (class 1), positive values push toward Non-Functional.
    # For Functional (class 0), negative values push toward Functional, so invert sign.
    raw_vals = sv.values[0]
    class_vals = raw_vals if pred_class == 1 else -raw_vals

    token_scores: list[tuple[str, float]] = []
    for idx in nonzero_indices:
        token_scores.append((str(feat_names[idx]), round(float(class_vals[idx]), 4)))

    # Sort by absolute impact descending
    token_scores.sort(key=lambda x: abs(x[1]), reverse=True)
    top_tokens = token_scores[:8]

    _EXPLANATION_CACHE[cache_key] = top_tokens
    return top_tokens
