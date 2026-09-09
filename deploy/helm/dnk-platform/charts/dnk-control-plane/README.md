# dnk-control-plane

Самостоятельный пакет Django/Nuxt с системным Ingress, PostgreSQL, Redis и Job миграций.
Настройки этого chart используются без префикса `controlPlane`.

Полная инструкция: [Helm и ArgoCD](../../../README.md).

По умолчанию: `ingress.className: nginx`, `ingress.tls.clusterIssuer: letsencrypt-production`. Cert-manager создаёт TLS Secret; gateway pods не создаются.
