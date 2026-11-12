"""Shared user-interface helpers for the RetailIQ dashboard."""

from __future__ import annotations

import logging

import streamlit as st

logger = logging.getLogger("retailiq")

GITHUB_URL = "https://github.com/Anna-datascience/retail-financial-intelligence"
LINKEDIN_URL = "https://www.linkedin.com/in/annapoornam-karthikeyan-168031124/"
DATASET_URL = "https://doi.org/10.24432/C5CG6D"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"


def render_footer() -> None:
    """Show data attribution, a usage note and author links at the end of a page."""
    st.divider()
    st.caption(
        f"**Data:** [UCI Online Retail II]({DATASET_URL}) (Chen, 2012), "
        f"licensed under [CC BY 4.0]({LICENCE_URL}). "
        "Historical transactions from a UK online retailer, 2009-2011."
    )
    st.caption(
        "Model outputs support decisions and do not replace expert review. "
        "Anomaly cases are review candidates, not confirmed fraud."
    )
    st.caption(
        "Built by **Annapoornam Karthikeyan** · "
        f"[Source code on GitHub]({GITHUB_URL}) · "
        f"[LinkedIn]({LINKEDIN_URL})"
    )


def show_load_error(error: Exception, what: str = "the dashboard data") -> None:
    """Show a visitor-friendly message, log the technical details, and stop the page."""
    logger.error("Could not load %s: %s", what, error, exc_info=error)
    st.error(
        f"Sorry, {what} could not be loaded. Please reload the page. "
        "If the problem continues, please report it on GitHub."
    )
    st.caption(f"Error type: {type(error).__name__}")
    st.stop()
