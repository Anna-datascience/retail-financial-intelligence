"""Customer segmentation model for RetailIQ."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    PowerTransformer,
    StandardScaler,
)

from src.features.customer_features import (
    SEGMENTATION_FEATURES,
)


FINAL_K = 3
RANDOM_STATE = 42
N_INIT = 20
MAX_ITER = 500


CLUSTER_NAME_MAP = {
    0: "Inactive / Low Frequency",
    1: "Active Core",
    2: "VIP / Strategic",
}


def prepare_segmentation_matrix(
    customer_features: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and return the RFM clustering matrix."""

    missing_columns = set(
        SEGMENTATION_FEATURES
    ).difference(customer_features.columns)

    if missing_columns:
        raise KeyError(
            "Missing segmentation features: "
            f"{sorted(missing_columns)}"
        )

    if customer_features.empty:
        raise ValueError(
            "Customer feature table is empty."
        )

    X_customer = (
        customer_features[
            SEGMENTATION_FEATURES
        ]
        .copy()
        .astype(float)
    )

    if X_customer.isna().any().any():
        missing_counts = (
            X_customer
            .isna()
            .sum()
        )

        raise ValueError(
            "Segmentation matrix contains missing "
            f"values:\n{missing_counts}"
        )

    if not np.isfinite(
        X_customer.to_numpy()
    ).all():
        raise ValueError(
            "Segmentation matrix contains "
            "infinite values."
        )

    return X_customer


def build_segmentation_pipeline(
    n_clusters: int = FINAL_K,
    random_state: int = RANDOM_STATE,
) -> Pipeline:
    """Build the validated RetailIQ K-Means pipeline."""

    preprocessing_pipeline = Pipeline(
        steps=[
            (
                "power_transform",
                PowerTransformer(
                    method="yeo-johnson",
                    standardize=False,
                ),
            ),
            (
                "standard_scaler",
                StandardScaler(),
            ),
        ]
    )

    segmentation_pipeline = Pipeline(
        steps=[
            (
                "preprocessing",
                preprocessing_pipeline,
            ),
            (
                "kmeans",
                KMeans(
                    n_clusters=n_clusters,
                    init="k-means++",
                    n_init=N_INIT,
                    max_iter=MAX_ITER,
                    random_state=random_state,
                ),
            ),
        ]
    )

    return segmentation_pipeline


def fit_customer_segmentation(
    customer_features: pd.DataFrame,
    n_clusters: int = FINAL_K,
    random_state: int = RANDOM_STATE,
) -> tuple[
    Pipeline,
    pd.DataFrame,
    pd.Series,
    pd.Series,
]:
    """
    Fit customer segmentation and return the model,
    customer results, metrics and cluster sizes.
    """

    X_customer = prepare_segmentation_matrix(
        customer_features
    )

    segmentation_pipeline = (
        build_segmentation_pipeline(
            n_clusters=n_clusters,
            random_state=random_state,
        )
    )

    cluster_labels = (
        segmentation_pipeline.fit_predict(
            X_customer
        )
    )

    X_processed = (
        segmentation_pipeline
        .named_steps["preprocessing"]
        .transform(X_customer)
    )

    cluster_sizes = (
        pd.Series(
            cluster_labels,
            name="Cluster",
        )
        .value_counts()
        .sort_index()
    )

    sampled_silhouette = silhouette_score(
        X_processed,
        cluster_labels,
        sample_size=(
            5000
            if len(X_processed) > 5000
            else None
        ),
        random_state=RANDOM_STATE,
    )

    full_silhouette = silhouette_score(
        X_processed,
        cluster_labels,
    )

    segmentation_metrics = pd.Series(
        {
            "Customers": len(X_customer),
            "Features": len(
                SEGMENTATION_FEATURES
            ),
            "Clusters": n_clusters,
            "Inertia": (
                segmentation_pipeline
                .named_steps["kmeans"]
                .inertia_
            ),
            "SampledSilhouetteScore": (
                sampled_silhouette
            ),
            "FullSilhouetteScore": (
                full_silhouette
            ),
            "SmallestClusterCustomers": (
                cluster_sizes.min()
            ),
            "LargestClusterCustomers": (
                cluster_sizes.max()
            ),
        },
        name="Value",
    )

    segmentation_results = (
        customer_features.copy()
    )

    segmentation_results[
        "Cluster"
    ] = cluster_labels

    segmentation_results[
        "ClusterName"
    ] = segmentation_results[
        "Cluster"
    ].map(CLUSTER_NAME_MAP)

    return (
        segmentation_pipeline,
        segmentation_results,
        segmentation_metrics,
        cluster_sizes,
    )


def predict_customer_segments(
    segmentation_pipeline: Pipeline,
    customer_features: pd.DataFrame,
) -> pd.DataFrame:
    """Assign clusters using a fitted pipeline."""

    X_customer = prepare_segmentation_matrix(
        customer_features
    )

    cluster_labels = (
        segmentation_pipeline.predict(
            X_customer
        )
    )

    predictions = customer_features.copy()

    predictions["Cluster"] = cluster_labels

    predictions["ClusterName"] = (
        predictions["Cluster"]
        .map(CLUSTER_NAME_MAP)
    )

    return predictions


def build_cluster_profile(
    segmentation_results: pd.DataFrame,
) -> pd.DataFrame:
    """Create the business profile for each cluster."""

    required_columns = {
        "Cluster",
        "Recency",
        "Frequency",
        "Monetary",
        "GrossMonetary",
        "AverageOrderValue",
        "UnitsPurchased",
        "UniqueProducts",
        "CancellationRatePercent",
    }

    missing_columns = required_columns.difference(
        segmentation_results.columns
    )

    if missing_columns:
        raise KeyError(
            "Missing cluster-profile columns: "
            f"{sorted(missing_columns)}"
        )

    cluster_profile = (
        segmentation_results
        .groupby("Cluster")
        .agg(
            Customers=("Cluster", "size"),
            AverageRecency=("Recency", "mean"),
            MedianRecency=("Recency", "median"),
            AverageFrequency=("Frequency", "mean"),
            MedianFrequency=("Frequency", "median"),
            TotalNetMonetary=("Monetary", "sum"),
            AverageNetMonetary=("Monetary", "mean"),
            MedianNetMonetary=("Monetary", "median"),
            AverageOrderValue=(
                "AverageOrderValue",
                "mean",
            ),
            AverageUnitsPurchased=(
                "UnitsPurchased",
                "mean",
            ),
            AverageUniqueProducts=(
                "UniqueProducts",
                "mean",
            ),
            AverageCancellationRate=(
                "CancellationRatePercent",
                "mean",
            ),
        )
    )

    cluster_profile["ClusterName"] = [
        CLUSTER_NAME_MAP.get(
            int(cluster),
            f"Cluster {cluster}",
        )
        for cluster in cluster_profile.index
    ]

    total_customers = (
        cluster_profile["Customers"].sum()
    )

    total_revenue = (
        cluster_profile[
            "TotalNetMonetary"
        ].sum()
    )

    cluster_profile[
        "CustomerSharePercent"
    ] = (
        cluster_profile["Customers"]
        .div(total_customers)
        .mul(100)
    )

    if total_revenue != 0:
        cluster_profile[
            "RevenueSharePercent"
        ] = (
            cluster_profile[
                "TotalNetMonetary"
            ]
            .div(total_revenue)
            .mul(100)
        )
    else:
        cluster_profile[
            "RevenueSharePercent"
        ] = 0.0

    profile_order = [
        "ClusterName",
        "Customers",
        "AverageRecency",
        "MedianRecency",
        "AverageFrequency",
        "MedianFrequency",
        "TotalNetMonetary",
        "AverageNetMonetary",
        "MedianNetMonetary",
        "AverageOrderValue",
        "AverageUnitsPurchased",
        "AverageUniqueProducts",
        "AverageCancellationRate",
        "CustomerSharePercent",
        "RevenueSharePercent",
    ]

    return cluster_profile[
        profile_order
    ]


def get_raw_cluster_centres(
    segmentation_pipeline: Pipeline,
) -> pd.DataFrame:
    """Convert transformed K-Means centres back to RFM values."""

    transformed_centres = (
        segmentation_pipeline
        .named_steps["kmeans"]
        .cluster_centers_
    )

    raw_centres = (
        segmentation_pipeline
        .named_steps["preprocessing"]
        .inverse_transform(
            transformed_centres
        )
    )

    cluster_centres = pd.DataFrame(
        raw_centres,
        columns=SEGMENTATION_FEATURES,
    )

    cluster_centres.index.name = "Cluster"

    cluster_centres["ClusterName"] = [
        CLUSTER_NAME_MAP.get(
            cluster,
            f"Cluster {cluster}",
        )
        for cluster in cluster_centres.index
    ]

    return cluster_centres