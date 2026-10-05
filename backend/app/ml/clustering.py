"""SRS Guardian - Requirement Clustering Engine.

Phase 15B: Tier 3.
Groups requirements into thematic, semantically cohesive functional clusters
using sentence embeddings and TF-IDF topic keyword extraction.

Features:
- Reuses existing cached MiniLM embeddings (Rule 7: zero recomputation)
- Deterministic Agglomerative Clustering using cosine distance
- Automatic cluster labeling via distinctive TF-IDF keyword extraction
"""

import math
from typing import Any
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.app.ml.embeddings import encode


def determine_optimal_clusters(n_items: int) -> int:
    """Calculates an adaptive, sensible cluster count k based on requirement count."""
    if n_items <= 1:
        return 1
    if n_items <= 3:
        return 2
    if n_items <= 5:
        return 3
    if n_items <= 8:
        return 4
    # For larger document sets, scale with square root bounded between 3 and 10
    return min(10, max(3, int(math.sqrt(n_items * 1.5))))


def extract_cluster_keywords(
    texts: list[str],
    cluster_labels: list[int],
    num_clusters: int,
    top_n: int = 4,
) -> list[list[str]]:
    """Extracts distinctive top TF-IDF keywords for each cluster."""
    if not texts:
        return [[] for _ in range(num_clusters)]

    # Fit TF-IDF with English stop words filtering
    try:
        tfidf = TfidfVectorizer(stop_words="english", max_features=500, min_df=1)
        matrix = tfidf.fit_transform(texts).toarray()
        vocab = np.array(tfidf.get_feature_names_out())
    except Exception:
        # Fallback if vocabulary cannot be built
        return [["requirements"] for _ in range(num_clusters)]

    if len(vocab) == 0:
        return [["general"] for _ in range(num_clusters)]

    cluster_keywords: list[list[str]] = []
    labels_arr = np.array(cluster_labels)

    for cid in range(num_clusters):
        idx = np.where(labels_arr == cid)[0]
        if len(idx) == 0:
            cluster_keywords.append(["general"])
            continue

        # Compute average TF-IDF vector for this cluster
        mean_vector = matrix[idx].mean(axis=0)
        sorted_indices = np.argsort(mean_vector)[::-1]

        # Filter out 0-weight terms
        words = []
        for word_idx in sorted_indices:
            if mean_vector[word_idx] > 0 and len(words) < top_n:
                words.append(vocab[word_idx])

        if not words:
            words = ["functionality"]
        cluster_keywords.append(words)

    return cluster_keywords


def cluster_requirements(
    requirements: list[dict[str, Any]],
    n_clusters: int | None = None,
) -> dict[str, Any]:
    """Clusters a collection of requirements into thematic topics with auto-generated labels.

    Args:
        requirements: List of requirement dicts containing at least 'id', 'req_key', and 'text'.
        n_clusters: Optional explicit number of clusters to form.

    Returns:
        Structured clustering report with cluster sizes, top keywords, and member requirements.
    """
    total = len(requirements)
    if total == 0:
        return {
            "total_requirements": 0,
            "num_clusters": 0,
            "clusters": [],
        }

    texts = [r["text"] for r in requirements]

    # Handle single item edge case
    if total == 1:
        return {
            "total_requirements": 1,
            "num_clusters": 1,
            "clusters": [
                {
                    "cluster_id": 0,
                    "label": "General System Requirement",
                    "keywords": ["general"],
                    "size": 1,
                    "requirements": requirements,
                }
            ],
        }

    k = n_clusters if (n_clusters and 1 <= n_clusters <= total) else determine_optimal_clusters(total)

    # 1. Retrieve embeddings (cached to disk via all-MiniLM-L6-v2)
    embeddings = encode(texts)

    # 2. Cluster using cosine distance
    clustering = AgglomerativeClustering(
        n_clusters=k,
        metric="cosine",
        linkage="average",
    )
    cluster_labels = clustering.fit_predict(embeddings).tolist()

    # 3. Extract distinctive keywords per cluster
    keywords_per_cluster = extract_cluster_keywords(texts, cluster_labels, k, top_n=3)

    # 4. Assemble cluster response
    clusters: list[dict[str, Any]] = []
    for cid in range(k):
        members = [requirements[i] for i, label in enumerate(cluster_labels) if label == cid]
        kw = keywords_per_cluster[cid]
        label_title = " / ".join(w.capitalize() for w in kw)

        clusters.append({
            "cluster_id": cid,
            "label": label_title,
            "keywords": kw,
            "size": len(members),
            "requirements": members,
        })

    # Sort clusters by size descending
    clusters.sort(key=lambda c: c["size"], reverse=True)

    # Re-index cluster IDs sequentially after sorting
    for idx, c in enumerate(clusters):
        c["cluster_id"] = idx

    return {
        "total_requirements": total,
        "num_clusters": k,
        "clusters": clusters,
    }
