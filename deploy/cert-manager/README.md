# Wildcard dniko.app через Cloudflare

[letsencrypt-production.yaml](letsencrypt-production.yaml) расширяет существующий
ClusterIssuer: HTTP-01 через nginx остаётся для обычных имён, DNS-01 через Cloudflare
выбирается только для запрашиваемого сертификата `*.dniko.app`. Имя issuer,
ACME server и `letsencrypt-prodaction-private-key` сохранены из текущей конфигурации.
Манифест применяется отдельно от runtime chart; он не попадает в Helm-релиз приложения.

1. В Cloudflare создайте API Token с правами `Zone / DNS / Edit` и
   `Zone / Zone / Read`. Ограничьте Zone Resources: `Include / Specific zone / dniko.app`.
2. Сохраните токен в Kubernetes Secret `cloudflare-dniko-api-token`, ключ `api-token`.
   Для ClusterIssuer Secret ищется в **cluster resource namespace** cert-manager:
   по умолчанию `cert-manager`, либо в namespace из `--cluster-resource-namespace`.
   Это не обязательно namespace runtime. Пример структуры Secret:

   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: cloudflare-dniko-api-token
     namespace: cert-manager
   type: Opaque
   stringData:
     api-token: "REPLACE_WITH_CLOUDFLARE_API_TOKEN"
   ```

   Значение задавайте через принятый в кластере способ управления Secrets или
   локальный файл вне репозитория. Реальный токен не добавляйте в Git.
3. После создания Secret обновите существующий issuer из
   [манифеста](letsencrypt-production.yaml). Если issuer управляется GitOps/Helm,
   внесите добавленный solver в его исходную конфигурацию. Сохраняйте любые другие
   настройки, если живой issuer отличается от предоставленного примера.
4. Используйте [values-multitenant.yaml](../../helm/examples/values-multitenant.yaml)
   поверх настроенных values runtime. Ingress запрашивает сертификат у
   `letsencrypt-production`; cert-manager создаст `runtime-dniko-wildcard-tls`
   **в namespace runtime**, создавая и удаляя проверочную TXT-запись
   `_acme-challenge.dniko.app` через Cloudflare API.

Проверки после применения (namespace runtime замените, если он другой):

```sh
kubectl get clusterissuer letsencrypt-production
kubectl -n dnk-runtime-core get certificates,certificaterequests,orders,challenges
kubectl -n dnk-runtime-core describe certificate runtime-dniko-wildcard-tls
```

Готовность issuer ещё не подтверждает доступ токена к DNS: дождитесь `Ready=True`
у wildcard Certificate. Существующие TLS Secrets не нужно удалять или перевыпускать.
Selector `dnsNames` сопоставляет имя буквально: отдельный запрос сертификата на
`tenant1.dniko.app` продолжит идти через HTTP-01. Здесь `dnsZones: [dniko.app]`
не используется, поскольку он переключил бы на DNS-01 всю зону, включая обычные имена.

Справка: [Cloudflare solver](https://cert-manager.io/docs/configuration/acme/dns01/cloudflare/),
[выбор solver](https://cert-manager.io/docs/configuration/acme/#dns-names),
[namespace Secrets](https://cert-manager.io/docs/configuration/#cluster-resource-namespace).
