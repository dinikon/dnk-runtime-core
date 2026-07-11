# Cluster management

Owns Kubernetes targets, desired routes/certificates, reconciliation jobs and
read-only actual-state snapshots. Resources are applied with deterministic
names, ownership labels and least-privilege service accounts. TLS is issued by
cert-manager through an environment-configured `Issuer` or `ClusterIssuer`.
