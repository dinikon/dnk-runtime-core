{{- define "dnk.runtime.fullname" -}}{{ include "dnk.lifecycle.fullname" . }}{{- end -}}
{{- define "dnk.runtime.dependencyName" -}}
{{- default (printf "%s-%s" .root.Release.Name (default .service .values.nameOverride)) .values.fullnameOverride | include "dnk.lifecycle.shortName" -}}
{{- end -}}
{{- define "dnk.runtime.labels" -}}
app.kubernetes.io/name: dnk-runtime-core
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end -}}
{{- define "dnk.runtime.hostname" -}}
{{- $url := urlParse .Values.application.server.publicOrigin -}}
{{- regexReplaceAll ":[0-9]+$" $url.host "" | lower -}}
{{- end -}}
{{- define "dnk.runtime.validateSecret" -}}
{{- $s := .secret -}}
{{- if and $s.value (or $s.existingSecret.name $s.existingSecret.key) -}}{{- fail (printf "%s: use value OR existingSecret, never both" .path) -}}{{- end -}}
{{- if ne (empty $s.existingSecret.name) (empty $s.existingSecret.key) -}}{{- fail (printf "%s: existingSecret requires both name and key" .path) -}}{{- end -}}
{{- if and .required (not (or $s.value $s.existingSecret.name)) -}}{{- fail (printf "%s: value or existingSecret is required" .path) -}}{{- end -}}
{{- end -}}
{{- define "dnk.runtime.secretBindings" -}}
{{- $bindings := dict -}}{{- $name := printf "%s-credentials" (include "dnk.runtime.fullname" .) -}}
{{- range $env, $path := (.Files.Get "files/secrets.yaml" | fromYaml) -}}
{{- $source := $.Values -}}{{- range (splitList "." $path) -}}{{- $source = index $source . -}}{{- end -}}
{{- $_ := set $bindings $env (dict "source" $source "name" $name "key" $env) -}}
{{- end -}}
{{- range $dep, $env := dict "postgresql" "DB_PASSWORD" "redis" "REDIS_PASSWORD" "rabbitmq" "DNK_RABBITMQ_PASSWORD" -}}
{{- $v := index $.Values $dep -}}{{- $inline := $name -}}{{- $key := $env -}}
{{- if $v.enabled -}}{{- $inline = printf "%s-auth" (include "dnk.runtime.dependencyName" (dict "root" $ "values" $v "service" $dep)) -}}{{- $key = "password" -}}{{- end -}}
{{- $_ := set $bindings $env (dict "source" $v.auth.password "name" $inline "key" $key) -}}
{{- end -}}
{{- range $dep, $env := dict "redis" "DNK_REDIS_URL" "rabbitmq" "DNK_RABBITMQ_URL" -}}
{{- $v := index $.Values $dep -}}
{{- if not $v.enabled -}}{{- $_ := set $bindings $env (dict "source" $v.external.url "name" $name "key" $env) -}}{{- end -}}
{{- end -}}
{{- toYaml $bindings -}}
{{- end -}}
{{- define "dnk.runtime.secretEnv" -}}
{{- range $env, $binding := (include "dnk.runtime.secretBindings" . | fromYaml) -}}
{{- if or $binding.source.value $binding.source.existingSecret.name }}
- name: {{ $env }}
  valueFrom:
    secretKeyRef:
      name: {{ default $binding.name $binding.source.existingSecret.name | quote }}
      key: {{ default $binding.key $binding.source.existingSecret.key | quote }}
{{- end -}}{{- end -}}
{{- end -}}
{{- define "dnk.runtime.config" -}}
SQLALCHEMY_DATABASE_URI_SCHEME: "postgresql+asyncpg"
{{- range $env, $path := (.Files.Get "files/environment.yaml" | fromYaml) }}
{{- $v := $.Values -}}{{- range (splitList "." $path) -}}{{- $v = index $v . -}}{{- end }}
{{- if kindIs "float64" $v }}
{{ $env }}: {{ $v | toJson | quote }}
{{- else }}
{{ $env }}: {{ $v | toString | quote }}
{{- end }}
{{- end }}
DB_DATABASE: {{ .Values.postgresql.auth.database | quote }}
DB_USERNAME: {{ .Values.postgresql.auth.username | quote }}
DB_HOST: {{ ternary (include "dnk.runtime.dependencyName" (dict "root" . "values" .Values.postgresql "service" "postgresql")) .Values.postgresql.external.host .Values.postgresql.enabled | quote }}
DB_PORT: {{ ternary 5432 (int .Values.postgresql.external.port) .Values.postgresql.enabled | quote }}
REDIS_HOST: {{ ternary (include "dnk.runtime.dependencyName" (dict "root" . "values" .Values.redis "service" "redis")) .Values.redis.external.host .Values.redis.enabled | quote }}
REDIS_PORT: {{ ternary 6379 (int .Values.redis.external.port) .Values.redis.enabled | quote }}
REDIS_DB: {{ .Values.redis.database | quote }}
REDIS_USERNAME: {{ .Values.redis.auth.username | quote }}
REDIS_USE_SSL: {{ .Values.redis.external.useSsl | quote }}
DNK_RABBITMQ_HOST: {{ ternary (include "dnk.runtime.dependencyName" (dict "root" . "values" .Values.rabbitmq "service" "rabbitmq")) .Values.rabbitmq.external.host .Values.rabbitmq.enabled | quote }}
DNK_RABBITMQ_PORT: {{ ternary 5672 (int .Values.rabbitmq.external.port) .Values.rabbitmq.enabled | quote }}
DNK_RABBITMQ_USERNAME: {{ .Values.rabbitmq.auth.username | quote }}
DNK_RABBITMQ_VHOST: {{ .Values.rabbitmq.auth.vhost | quote }}
DNK_RABBITMQ_USE_SSL: {{ .Values.rabbitmq.external.useSsl | quote }}
EVENT_BUS__PUBLISHER_WORKER_ENABLED: {{ .Values.workers.publisher.enabled | quote }}
{{- end -}}
{{- define "dnk.runtime.validate" -}}
{{- $app := .Values.application -}}
{{- $origin := required "application.server.publicOrigin is required" $app.server.publicOrigin -}}{{- $url := urlParse $origin -}}
{{- if or (not (has $url.scheme (list "http" "https"))) (empty $url.host) $url.path $url.query $url.fragment $url.userinfo -}}{{- fail "application.server.publicOrigin must be an HTTP(S) origin without path, credentials, query or fragment" -}}{{- end -}}
{{- $port := regexFind ":[0-9]+$" $url.host | trimPrefix ":" -}}
{{- if and $port (or (lt (int $port) 1) (gt (int $port) 65535)) -}}{{- fail "application.server.publicOrigin port must be between 1 and 65535" -}}{{- end -}}
{{- if and (eq $app.server.environment "PRODUCTION") (ne $url.scheme "https") -}}{{- fail "production application.server.publicOrigin requires HTTPS" -}}{{- end -}}
{{- include "dnk.runtime.validateSecret" (dict "secret" $app.security.controlPlaneApiKey "path" "application.security.controlPlaneApiKey" "required" true) -}}
{{- include "dnk.runtime.validateSecret" (dict "secret" $app.email.smtp.password "path" "application.email.smtp.password" "required" false) -}}
{{- $_ := required "application.email.smtp.host is required" $app.email.smtp.host -}}
{{- $_ := required "application.email.fromAddress is required" $app.email.fromAddress -}}
{{- if and $app.email.smtp.useTls $app.email.smtp.useStarttls -}}{{- fail "application.email.smtp.useTls and useStarttls are mutually exclusive" -}}{{- end -}}
{{- if and (not $app.events.enabled) (or .Values.workers.publisher.enabled .Values.workers.console.enabled) -}}{{- fail "enabled workers require application.events.enabled=true" -}}{{- end -}}
{{- include "dnk.runtime.validateSecret" (dict "secret" .Values.postgresql.auth.password "path" "postgresql.auth.password" "required" true) -}}
{{- if and (not .Values.postgresql.enabled) (not .Values.postgresql.external.host) -}}{{- fail "postgresql.external.host is required when embedded PostgreSQL is disabled" -}}{{- end -}}
{{- if and .Values.postgresql.enabled .Values.postgresql.external.host -}}{{- fail "postgresql.external.host requires postgresql.enabled=false" -}}{{- end -}}
{{- range $dep := list "redis" "rabbitmq" -}}
{{- $v := index $.Values $dep -}}{{- $secret := $v.external.url -}}{{- $hasUrl := or $secret.value $secret.existingSecret.name -}}
{{- include "dnk.runtime.validateSecret" (dict "secret" $secret "path" (printf "%s.external.url" $dep) "required" false) -}}
{{- include "dnk.runtime.validateSecret" (dict "secret" $v.auth.password "path" (printf "%s.auth.password" $dep) "required" (and (or $v.enabled (eq $dep "rabbitmq")) (not $hasUrl))) -}}
{{- if and $v.enabled (or $hasUrl $v.external.host $v.external.useSsl) -}}{{- fail (printf "%s external connection settings require enabled=false" $dep) -}}{{- end -}}
{{- if and (not $v.enabled) (not $hasUrl) (not $v.external.host) -}}{{- fail (printf "external %s requires host or url" $dep) -}}{{- end -}}
{{- if and $hasUrl (or $v.external.host $v.auth.password.value $v.auth.password.existingSecret.name $v.external.useSsl) -}}{{- fail (printf "%s.external.url cannot be combined with host, password or useSsl" $dep) -}}{{- end -}}
{{- if and (eq $dep "redis") $v.enabled $v.auth.username -}}{{- fail "embedded Redis only supports the default user" -}}{{- end -}}
{{- if and (eq $dep "redis") $hasUrl $v.auth.username -}}{{- fail "redis.external.url cannot be combined with auth.username" -}}{{- end -}}
{{- if $secret.value -}}
{{- $u := urlParse $secret.value -}}{{- $schemes := ternary (list "redis" "rediss") (list "amqp" "amqps") (eq $dep "redis") -}}
{{- if or $u.error (not (has $u.scheme $schemes)) (not (regexMatch "^(\\[[0-9A-Fa-f:]+\\]|[A-Za-z0-9][A-Za-z0-9.-]*)(:[0-9]+)?$" (default "" $u.host))) $u.fragment $u.query -}}{{- fail (printf "%s.external.url.value must be a valid connection URL without query or fragment" $dep) -}}{{- end -}}
{{- $p := regexFind ":[0-9]+$" $u.host | trimPrefix ":" -}}
{{- if and $p (or (lt (int $p) 1) (gt (int $p) 65535)) -}}{{- fail (printf "%s.external.url port must be between 1 and 65535" $dep) -}}{{- end -}}
{{- if and (eq $dep "redis") (not (regexMatch "^(|/|/[0-9]+)$" $u.path)) -}}{{- fail "redis.external.url must use an integer database path" -}}{{- end -}}
{{- end -}}
{{- end -}}
{{- $workloads := dict "backend" .Values.backend "frontend" .Values.frontend "publisher" .Values.workers.publisher "console" .Values.workers.console -}}
{{- range $name, $w := $workloads -}}
{{- $_ := required (printf "%s.image.repository is required" $name) $w.image.repository -}}{{- $_ := required (printf "%s.image.tag is required" $name) $w.image.tag -}}
{{- range $key := list "app.kubernetes.io/name" "app.kubernetes.io/instance" "app.kubernetes.io/component" -}}{{- if hasKey $w.pod.labels $key -}}{{- fail (printf "%s.pod.labels cannot override selector %s" $name $key) -}}{{- end -}}{{- end -}}
{{- range $key := list "checksum/config" "checksum/credentials" "checksum/migration-gate" "dnk.io/deployment-token" "dnk.io/deployment-revision" -}}{{- if hasKey $w.pod.annotations $key -}}{{- fail (printf "%s.pod.annotations cannot override managed annotation %s" $name $key) -}}{{- end -}}{{- end -}}
{{- end -}}
{{- $reserved := include "dnk.runtime.config" . | fromYaml -}}
{{- range $key, $_ := (include "dnk.runtime.secretBindings" . | fromYaml) -}}{{- $_ := set $reserved $key true -}}{{- end -}}
{{- range $key := list "RABBITMQ__URL" "DNK_REDIS_URL" "DNK_RABBITMQ_URL" "SQLALCHEMY_DATABASE_URI" -}}{{- $_ := set $reserved $key true -}}{{- end -}}
{{- range .Values.backend.extraEnv -}}
{{- if hasKey $reserved .name -}}{{- fail (printf "backend.extraEnv duplicates managed variable %s" .name) -}}{{- end -}}{{- $_ := set $reserved .name true -}}
{{- end -}}
{{- include "dnk.ingress.validate" . -}}
{{- if .Values.ingress.enabled -}}
{{- if or (ne $url.scheme "https") (contains ":" $url.host) -}}{{- fail "Ingress requires an HTTPS publicOrigin with a DNS hostname and no explicit port" -}}{{- end -}}
{{- end -}}
{{- end -}}
