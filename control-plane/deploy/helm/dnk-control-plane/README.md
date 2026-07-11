# DNK Control Plane Helm chart

This is a chart-value scaffold, not a deployable chart yet. Templates are added
in the deployment phase in this order:

1. API and worker Deployments, Services and health probes.
2. Migration Job with release-safe locking.
3. Cabinet Deployment/Service/Ingress.
4. ServiceAccount/RBAC and ExternalSecret references.
5. NetworkPolicy, PodDisruptionBudget, HPA and monitoring resources.

`values-preprod.yaml` and `values-prod.yaml` must remain explicit. Secrets must
not be committed to either file.
