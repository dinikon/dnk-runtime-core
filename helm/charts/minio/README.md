# MinIO для DNK Runtime

Локальная инфраструктурная зависимость с одним StatefulSet, сохраняемым PVC и
внутренним S3 Service на порту 9000. Используется закреплённый образ
`quay.io/thanos/minio:RELEASE.2025-09-07T16-13-09Z`. Console отключена;
публичные Ingress, NodePort и LoadBalancer не создаются.

В корневом chart включите `minio.enabled: true` и задайте `minio.auth.accessKey`
и `minio.auth.secretKey` через `existingSecret: {name, key}` либо `value`.
Один и тот же источник credentials используется сервером MinIO и Runtime.
Secret находится в namespace релиза. Ключи не генерируются автоматически.

`persistence.size` по умолчанию равен `20Gi`; `storageClass: null` использует
StorageClass кластера по умолчанию. `existingClaim` подключает готовый PVC.
Созданный StatefulSet сохраняет PVC при удалении; отдельной репликации и
резервного копирования этот одиночный экземпляр не предоставляет.

NetworkPolicy по умолчанию разрешает S3 только pod Runtime того же релиза и
namespace. `networkPolicy.clientPodSelector` задаёт дополнительные метки клиента;
метка instance всегда соответствует текущему релизу. Фактическая фильтрация
трафика требует поддержки NetworkPolicy установленным CNI.

Для отдельной установки chart используйте те же `auth` и `persistence` на верхнем
уровне его values. При ротации внешнего Secret перезапустите MinIO и Runtime:
изменение содержимого существующего Secret Helm не отслеживает.
