from prometheus_client import Counter

mtls_rejections = Counter(
    "dnk_runtime_mtls_rejections_total",
    "Rejected management connections before proxy normalization.",
    ["reason"],
)
oidc_errors = Counter(
    "dnk_runtime_oidc_errors_total",
    "Cloud authorization failures without sensitive provider details.",
    ["reason"],
)
