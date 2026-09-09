# Проверка корневого Helm chart 0.3.2

Проверка структуры от 2026-09-09. Результаты версии 0.3.1 сохранены отдельно:
[исторический отчёт](../docs/history/helm-validation-0.3.1.md).

Среда: Helm 3.19.0, Python 3.13.9, PyYAML 6.0.3.
Исходное состояние этого изменения: commit `4295b05f171d1f9413b14e41511a97740c075471`; приложение и образы не менялись.

| Проверка | Результат |
| --- | --- |
| Offline unittest discovery в `helm/tests` | 42 тестов прошли |
| Прямые `helm lint`, `helm template`, `helm package helm` | Прошли, подготовка chart не требуется |
| `python helm/build.py --destination dist/helm` | Собран `dnk-runtime-core-0.3.2.tgz` |
| Состав пакета | Собственные templates и локальные infrastructure charts; без tooling, тестов, wrappers и common archive |
| Отсутствие изменений исходников при упаковке | Проверено сравнением содержимого файлов до/после |
| Black для Helm tooling/tests | Пройден |

Сопоставлены по 16 вариантов прежнего самостоятельного chart 0.3.1 и корневого 0.3.2
(всего 32 для пары репозиториев): PostgreSQL/Redis embedded или external,
inline/existing Secrets и включённый/выключенный Ingress. Допустимые отличия —
`helm.sh/chart` и производный checksum frontend ConfigMap runtime. При выравнивании
версии во временной копии результаты совпадают полностью, включая имена, selectors,
PVC, окружение, миграции и доступ к Kubernetes API.

Офлайн проверки также проверяют неверные настройки/schema, отсутствие конфликтов
Secrets и имён, миграционный барьер и актуальность путей ArgoCD. Текущие проверки
относятся к двум самостоятельным packages; umbrella удалена.

Kubernetes smoke и PostgreSQL migration integration runtime в этом изменении
повторно не запускались: deployment-шаблоны и исполняемые скрипты перенесены без
изменения поведения, что подтверждено сравнением рендера и unit-тестами скриптов.
Результаты интеграционных прогонов 0.3.1 доступны в историческом отчёте выше.
