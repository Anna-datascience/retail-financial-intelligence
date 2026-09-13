from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    FunctionTransformer,
    StandardScaler
)


SEGMENTATION_FEATURES = [
    "Recency",
    "Frequency",
    "Monetary",
    "AverageOrderValue",
    "UnitsPurchased",
    "UniqueProducts",
    "CancellationRatePercent"
]


LOG_FEATURES = [
    "Frequency",
    "Monetary",
    "AverageOrderValue",
    "UnitsPurchased",
    "UniqueProducts"
]


def log_transform_customer_features(
    feature_df
):
    """Apply the transformations used before K-Means."""

    transformed_df = pd.DataFrame(
        feature_df,
        columns=SEGMENTATION_FEATURES
    ).copy()

    transformed_df[LOG_FEATURES] = np.log1p(
        transformed_df[LOG_FEATURES]
        .clip(lower=0)
    )

    return transformed_df


def build_segmentation_pipeline(
    n_clusters=3,
    random_state=42,
    n_init=50
):
    """Create the final customer K-Means pipeline."""

    return Pipeline([
        (
            "log_transform",
            FunctionTransformer(
                log_transform_customer_features,
                validate=False
            )
        ),
        (
            "scaler",
            StandardScaler()
        ),
        (
            "kmeans",
            KMeans(
                n_clusters=n_clusters,
                random_state=random_state,
                n_init=n_init
            )
        )
    ])


def validate_segmentation_input(
    customer_df
):
    """Validate the model-ready customer feature table."""

    missing_columns = (
        set(SEGMENTATION_FEATURES)
        - set(customer_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing segmentation features: "
            f"{sorted(missing_columns)}"
        )

    model_data = customer_df[
        SEGMENTATION_FEATURES
    ]

    if model_data.isna().any().any():
        raise ValueError(
            "Missing values found in segmentation data."
        )

    if not np.isfinite(model_data).all():
        raise ValueError(
            "Non-finite values found in segmentation data."
        )

    if model_data["Recency"].lt(0).any():
        raise ValueError(
            "Negative Recency values found."
        )

    positive_features = [
        "Frequency",
        "Monetary",
        "AverageOrderValue",
        "UnitsPurchased",
        "UniqueProducts"
    ]

    if model_data[
        positive_features
    ].le(0).any().any():
        raise ValueError(
            "Non-positive values found in features "
            "that must be positive."
        )


def fit_customer_segmentation(
    customer_df,
    pipeline=None
):
    """Fit the pipeline and return labels and metrics."""

    validate_segmentation_input(customer_df)

    X_customer = customer_df[
        SEGMENTATION_FEATURES
    ].copy()

    if pipeline is None:
        pipeline = build_segmentation_pipeline()

    fitted_pipeline = clone(pipeline)

    cluster_labels = (
        fitted_pipeline.fit_predict(X_customer)
    )

    transformed_features = (
        fitted_pipeline[:-1]
        .transform(X_customer)
    )

    kmeans_model = (
        fitted_pipeline.named_steps["kmeans"]
    )

    metrics = pd.Series({
        "Customers": len(customer_df),
        "Clusters": (
            kmeans_model.n_clusters
        ),
        "Inertia": (
            kmeans_model.inertia_
        ),
        "SilhouetteScore": silhouette_score(
            transformed_features,
            cluster_labels
        ),
        "SmallestClusterCustomers": (
            pd.Series(cluster_labels)
            .value_counts()
            .min()
        )
    })

    segmented_customers = (
        customer_df.copy()
    )

    segmented_customers["Cluster"] = (
        cluster_labels
    )

    return (
        fitted_pipeline,
        segmented_customers,
        metrics
    )


def save_segmentation_pipeline(
    pipeline,
    output_path
):
    """Save the fitted sklearn pipeline."""

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(
        pipeline,
        output_path
    )

    return output_path