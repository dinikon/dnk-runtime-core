from prometheus_client import Counter

oidc_errors = Counter(
    "dnk_runtime_oidc_errors_total",
    "Cloud authorization failures without sensitive provider details.",
    ["reason"],
)
