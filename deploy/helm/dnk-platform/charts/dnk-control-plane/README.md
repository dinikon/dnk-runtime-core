# dnk-control-plane

Самостоятельный Django/Nuxt с системным Ingress пакет с PostgreSQL, Redis и Job миграций.
Настройки этого chart используются без префикса `controlPlane`.

Полная инструкция: [Helm и ArgoCD](../../../README.md).

По умолчанию: `ingress.className: nginx`, `ingress.tls.clusterIssuer: letsencrypt-production`. Cert-manager создаёт TLS Secret; gateway pods не создаются.
