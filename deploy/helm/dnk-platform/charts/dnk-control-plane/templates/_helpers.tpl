{{- define "dnk.controlPlane.fullname" -}}
{{- include "dnk.lifecycle.fullname" . -}}
{{- end -}}

{{- define "dnk.controlPlane.dependencyName" -}}
{{- default (printf "%s-%s" .root.Release.Name (default .service .values.nameOverride)) .values.fullnameOverride | include "dnk.lifecycle.shortName" -}}
{{- end -}}

{{- define "dnk.controlPlane.labels" -}}
app.kubernetes.io/name: dnk-control-plane
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end -}}

{{- define "dnk.controlPlane.hostname" -}}
{{- $url := urlParse .Values.application.server.publicOrigin -}}
{{- regexReplaceAll ":[0-9]+$" $url.host "" | lower -}}
{{- end -}}

{{/* Every secret uses the same field shape. Requiredness is contextual. */}}
{{- define "dnk.controlPlane.validateSecret" -}}
{{- $s := .secret -}}
{{- if and $s.value (or $s.existingSecret.name $s.existingSecret.key) -}}
{{- fail (printf "%s: use value OR existingSecret, never both" .path) -}}
{{- end -}}
{{- if ne (empty $s.existingSecret.name) (empty $s.existingSecret.key) -}}
{{- fail (printf "%s: existingSecret requires both name and key" .path) -}}
{{- end -}}
{{- if and .required (not (or $s.value $s.existingSecret.name)) -}}
{{- fail (printf "%s: value or existingSecret is required" .path) -}}
{{- end -}}
{{- end -}}

{{/* Resolved bindings feed both Secret rendering and container environment. */}}
{{- define "dnk.controlPlane.secretBindings" -}}
{{- $bindings := dict -}}
{{- $name := printf "%s-credentials" (include "dnk.controlPlane.fullname" .) -}}
{{- range $env, $path := (.Files.Get "files/secrets.yaml" | fromYaml) -}}
{{- $value := $.Values -}}
{{- range (splitList "." $path) -}}{{- $value = index $value . -}}{{- end -}}
{{- $_ := set $bindings $env (dict "source" $value "name" $name "key" $env) -}}
{{- end -}}
{{- range $service, $env := dict "postgresql" "CORE_DB_PASSWORD" "redis" "CORE_REDIS_PASSWORD" -}}
{{- $values := index $.Values $service -}}
{{- $inlineName := $name -}}{{- $key := $env -}}
{{- if $values.enabled -}}
{{- $inlineName = printf "%s-auth" (include "dnk.controlPlane.dependencyName" (dict "root" $ "values" $values "service" $service)) -}}
{{- $key = "password" -}}
{{- end -}}
{{- $_ := set $bindings $env (dict "source" $values.auth.password "name" $inlineName "key" $key) -}}
{{- end -}}
{{- if not .Values.redis.enabled -}}
{{- $_ := set $bindings "CORE_REDIS_URL" (dict "source" .Values.redis.external.url "name" $name "key" "CORE_REDIS_URL") -}}
{{- end -}}
{{- toYaml $bindings -}}
{{- end -}}

{{- define "dnk.controlPlane.secretEnv" -}}
{{- range $env, $binding := (include "dnk.controlPlane.secretBindings" . | fromYaml) -}}
{{- $source := $binding.source -}}
{{- if or $source.value $source.existingSecret.name }}
- name: {{ $env }}
  valueFrom:
    secretKeyRef:
      name: {{ default $binding.name $source.existingSecret.name | quote }}
      key: {{ default $binding.key $source.existingSecret.key | quote }}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "dnk.controlPlane.config" -}}
CORE_ENV_FILE: ""
CORE_PUBLIC_ORIGIN: {{ .Values.application.server.publicOrigin | quote }}
CORE_ALLOWED_HOSTS: {{ join "," (default (list (include "dnk.controlPlane.hostname" .)) .Values.application.server.allowedHosts) | quote }}
{{- range $env, $path := (.Files.Get "files/environment.yaml" | fromYaml) }}
{{- $value := $.Values -}}
{{- range (splitList "." $path) -}}{{- $value = index $value . -}}{{- end }}
{{- if kindIs "float64" $value }}
{{ $env }}: {{ $value | toJson | quote }}
{{- else }}
{{ $env }}: {{ $value | toString | quote }}
{{- end }}
{{- end }}
CORE_DB_NAME: {{ .Values.postgresql.auth.database | quote }}
CORE_DB_USER: {{ .Values.postgresql.auth.username | quote }}
CORE_DB_HOST: {{ ternary (include "dnk.controlPlane.dependencyName" (dict "root" . "values" .Values.postgresql "service" "postgresql")) .Values.postgresql.external.host .Values.postgresql.enabled | quote }}
CORE_DB_PORT: {{ ternary 5432 (int .Values.postgresql.external.port) .Values.postgresql.enabled | quote }}
CORE_REDIS_HOST: {{ ternary (include "dnk.controlPlane.dependencyName" (dict "root" . "values" .Values.redis "service" "redis")) .Values.redis.external.host .Values.redis.enabled | quote }}
CORE_REDIS_PORT: {{ ternary 6379 (int .Values.redis.external.port) .Values.redis.enabled | quote }}
CORE_REDIS_DB: {{ .Values.redis.database | quote }}
{{- end -}}

{{- define "dnk.controlPlane.validatePort" -}}
{{- $port := regexFind ":[0-9]+$" .host | trimPrefix ":" -}}
{{- if and $port (or (lt (int $port) 1) (gt (int $port) 65535)) -}}
{{- fail (printf "%s port must be between 1 and 65535" .path) -}}
{{- end -}}
{{- end -}}

{{- define "dnk.controlPlane.validate" -}}
{{- $app := .Values.application -}}
{{- $origin := required "application.server.publicOrigin is required" $app.server.publicOrigin -}}
{{- $parsed := urlParse $origin -}}
{{- include "dnk.controlPlane.validatePort" (dict "host" $parsed.host "path" "application.server.publicOrigin") -}}
{{- if or (not (has $parsed.scheme (list "http" "https"))) (empty $parsed.host) $parsed.path $parsed.query $parsed.fragment $parsed.userinfo -}}
{{- fail "application.server.publicOrigin must be an HTTP(S) origin without path, credentials, query or fragment" -}}
{{- end -}}
{{- if and (not $app.server.debug) (ne $parsed.scheme "https") -}}{{- fail "production application.server.publicOrigin requires HTTPS" -}}{{- end -}}
{{- if and (not $app.server.debug) (not $app.server.trustProxy) -}}{{- fail "production reverse proxy requires application.server.trustProxy=true" -}}{{- end -}}
{{- if and (not $app.server.debug) $app.server.allowedHosts (or (has "*" $app.server.allowedHosts) (not (has (include "dnk.controlPlane.hostname" .) $app.server.allowedHosts))) -}}
{{- fail "application.server.allowedHosts must include the public hostname and exclude '*'" -}}{{- end -}}
{{- range $env, $path := (.Files.Get "files/secrets.yaml" | fromYaml) -}}
{{- $value := $.Values -}}{{- range (splitList "." $path) -}}{{- $value = index $value . -}}{{- end -}}
{{- include "dnk.controlPlane.validateSecret" (dict "secret" $value "path" $path "required" (or (eq $env "CORE_SECRET_KEY") (and (eq $env "CORE_MFA_ENCRYPTION_KEY") (not $app.server.debug)))) -}}
{{- end -}}
{{- if and $app.mfa.encryptionKey.value (not (regexMatch "^[A-Za-z0-9_-]{43}=$" $app.mfa.encryptionKey.value)) -}}{{- fail "application.mfa.encryptionKey.value must be a Fernet key" -}}{{- end -}}
{{- if and (has $app.auth.passwordMode (list "optional" "passwordless")) (not $app.auth.emailCodeEnabled) -}}{{- fail "emailCodeEnabled must be true for optional/passwordless passwordMode" -}}{{- end -}}
{{- if and $app.auth.signupEnabled $app.auth.passkeySignupEnabled (or (not $app.auth.passkeyLoginEnabled) (not $app.mfa.passkeyEnrollmentEnabled)) -}}{{- fail "passkey signup requires passkey login and enrollment" -}}{{- end -}}
{{- if and $app.email.useTls $app.email.useSsl -}}{{- fail "application.email.useTls and useSsl are mutually exclusive" -}}{{- end -}}
{{- if and (not $app.server.debug) (not $app.email.verifyCertificate) -}}{{- fail "production SMTP requires certificate verification" -}}{{- end -}}
{{- if has $app.email.backend (list "django.core.mail.backends.smtp.EmailBackend" "accounts.mail.SMTPEmailBackend") -}}
{{- $_ := required "SMTP application.email.host is required" $app.email.host -}}
{{- $_ := required "SMTP application.email.from is required" $app.email.from -}}
{{- end -}}
{{- range $name, $provider := $app.providers -}}
{{- if eq (toString $provider.enabled) "true" -}}
{{- if eq $name "telegramGateway" -}}
{{- if not (or $provider.token.value $provider.token.existingSecret.name) -}}{{- fail "enabled telegramGateway requires a token" -}}{{- end -}}
{{- else -}}
{{- if or (not $provider.clientId) (not (or $provider.clientSecret.value $provider.clientSecret.existingSecret.name)) -}}{{- fail (printf "enabled %s requires clientId and clientSecret" $name) -}}{{- end -}}
{{- end -}}{{- end -}}{{- end -}}
{{- include "dnk.controlPlane.validateSecret" (dict "secret" .Values.postgresql.auth.password "path" "postgresql.auth.password" "required" true) -}}
{{- if not .Values.postgresql.enabled -}}{{- $_ := required "postgresql.external.host is required when embedded PostgreSQL is disabled" .Values.postgresql.external.host -}}{{- end -}}
{{- if and .Values.postgresql.enabled .Values.postgresql.external.host -}}{{- fail "postgresql.external.host requires postgresql.enabled=false" -}}{{- end -}}
{{- if and .Values.redis.enabled .Values.redis.external.host -}}{{- fail "redis.external.host requires redis.enabled=false" -}}{{- end -}}
{{- $url := .Values.redis.external.url -}}
{{- include "dnk.controlPlane.validateSecret" (dict "secret" $url "path" "redis.external.url" "required" false) -}}
{{- $hasUrl := or $url.value $url.existingSecret.name -}}
{{- include "dnk.controlPlane.validateSecret" (dict "secret" .Values.redis.auth.password "path" "redis.auth.password" "required" .Values.redis.enabled) -}}
{{- if and .Values.redis.enabled $hasUrl -}}{{- fail "redis.external.url requires redis.enabled=false" -}}{{- end -}}
{{- if and (not .Values.redis.enabled) (not $hasUrl) (not .Values.redis.external.host) -}}{{- fail "external Redis requires host or url" -}}{{- end -}}
{{- if and $hasUrl (or .Values.redis.external.host .Values.redis.auth.password.value .Values.redis.auth.password.existingSecret.name) -}}{{- fail "redis.external.url cannot be combined with external.host or auth.password" -}}{{- end -}}
{{- if and $url.value (not (regexMatch "^rediss?://[^/]+(/[0-9]+)?(\\?.*)?$" $url.value)) -}}{{- fail "redis.external.url.value must be a redis:// or rediss:// URL" -}}{{- end -}}
{{- if $url.value -}}
{{- $redisUrl := urlParse $url.value -}}
{{- if or $redisUrl.error (not (regexMatch "^(\\[[0-9A-Fa-f:]+\\]|[A-Za-z0-9][A-Za-z0-9.-]*)(:[0-9]+)?$" (default "" $redisUrl.host))) $redisUrl.fragment -}}
{{- fail "redis.external.url.value must have a valid hostname and port" -}}
{{- end -}}
{{- include "dnk.controlPlane.validatePort" (dict "host" $redisUrl.host "path" "redis.external.url") -}}
{{- end -}}
{{- range $name := list "backend" "frontend" -}}
{{- $w := index $.Values $name -}}
{{- $_ := required (printf "%s.image.repository is required" $name) $w.image.repository -}}
{{- $_ := required (printf "%s.image.tag is required" $name) $w.image.tag -}}
{{- range $key := list "app.kubernetes.io/name" "app.kubernetes.io/instance" "app.kubernetes.io/component" -}}
{{- if hasKey $w.pod.labels $key -}}{{- fail (printf "%s.pod.labels cannot override selector %s" $name $key) -}}{{- end -}}
{{- end -}}
{{- range $key := list "checksum/config" "checksum/credentials" "checksum/migration-gate" "dnk.io/deployment-token" "dnk.io/deployment-revision" -}}
{{- if hasKey $w.pod.annotations $key -}}{{- fail (printf "%s.pod.annotations cannot override managed annotation %s" $name $key) -}}{{- end -}}
{{- end -}}{{- end -}}
{{- $reserved := include "dnk.controlPlane.config" . | fromYaml -}}
{{- range $key, $_ := (include "dnk.controlPlane.secretBindings" . | fromYaml) -}}{{- $_ := set $reserved $key true -}}{{- end -}}
{{- $_ := set $reserved "CORE_REDIS_URL" true -}}
{{- range .Values.backend.extraEnv -}}
{{- if hasKey $reserved .name -}}{{- fail (printf "backend.extraEnv duplicates managed variable %s" .name) -}}{{- end -}}
{{- $_ := set $reserved .name true -}}
{{- end -}}
{{- include "dnk.ingress.validate" . -}}
{{- if .Values.ingress.enabled -}}
{{- if ne $parsed.scheme "https" -}}{{- fail "Ingress requires an HTTPS publicOrigin" -}}{{- end -}}
{{- if contains ":" $parsed.host -}}{{- fail "Ingress publicOrigin must use a DNS hostname without explicit port" -}}{{- end -}}
{{- end -}}
{{- end -}}
