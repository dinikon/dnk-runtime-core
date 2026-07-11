# Cluster management

Owns Kubernetes targets, desired routes/certificates, reconciliation jobs and
read-only actual-state snapshots. Resources are applied with deterministic
names, ownership labels and least-privilege service accounts. TLS is issued by
cert-manager through an environment-configured `ClusterIssuer`. The first route
adapter targets `networking.k8s.io/v1` Ingress with `ingress-nginx`; all cluster
mutations are executed by an environment-scoped agent.
