{{- define "dnk.core.fullname" -}}
{{- $name := default (printf "%s-%s" .Release.Name (default "core" .Values.nameOverride)) .Values.fullnameOverride -}}
{{- if gt (len $name) 45 -}}
{{- printf "%s-%s" ($name | trunc 36 | trimSuffix "-") ($name | sha256sum | trunc 8) -}}
{{- else -}}{{- $name -}}{{- end -}}
{{- end -}}

{{- define "dnk.core.dependencyName" -}}
{{- default (printf "%s-%s" .root.Release.Name (default (printf "core-%s" .service) .values.nameOverride)) .values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "dnk.core.labels" -}}
app.kubernetes.io/name: core
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end -}}

{{- define "dnk.core.hostname" -}}
{{- $url := urlParse .Values.application.server.publicOrigin -}}
{{- regexReplaceAll ":[0-9]+$" $url.host "" | lower -}}
{{- end -}}

{{/* Every secret uses the same field shape. Requiredness is contextual. */}}
{{- define "dnk.core.validateSecret" -}}
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
{{- define "dnk.core.secretBindings" -}}
{{- $bindings := dict -}}
{{- $name := printf "%s-credentials" (include "dnk.core.fullname" .) -}}
{{- range $env, $path := (.Files.Get "files/secrets.yaml" | fromYaml) -}}
{{- $value := $.Values -}}
{{- range (splitList "." $path) -}}{{- $value = index $value . -}}{{- end -}}
{{- $_ := set $bindings $env (dict "source" $value "name" $name "key" $env) -}}
{{- end -}}
{{- range $service, $env := dict "postgresql" "CORE_DB_PASSWORD" "redis" "CORE_REDIS_PASSWORD" -}}
{{- $values := index $.Values $service -}}
{{- $inlineName := $name -}}{{- $key := $env -}}
{{- if $values.enabled -}}
{{- $inlineName = printf "%s-auth" (include "dnk.core.dependencyName" (dict "root" $ "values" $values "service" $service)) -}}
{{- $key = "password" -}}
{{- end -}}
{{- $_ := set $bindings $env (dict "source" $values.auth.password "name" $inlineName "key" $key) -}}
{{- end -}}
{{- if not .Values.redis.enabled -}}
{{- $_ := set $bindings "CORE_REDIS_URL" (dict "source" .Values.redis.external.url "name" $name "key" "CORE_REDIS_URL") -}}
{{- end -}}
{{- toYaml $bindings -}}
{{- end -}}

{{- define "dnk.core.secretEnv" -}}
{{- range $env, $binding := (include "dnk.core.secretBindings" . | fromYaml) -}}
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

{{- define "dnk.core.config" -}}
CORE_ENV_FILE: ""
CORE_PUBLIC_ORIGIN: {{ .Values.application.server.publicOrigin | quote }}
CORE_ALLOWED_HOSTS: {{ join "," (default (list (include "dnk.core.hostname" .)) .Values.application.server.allowedHosts) | quote }}
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
CORE_DB_HOST: {{ ternary (include "dnk.core.dependencyName" (dict "root" . "values" .Values.postgresql "service" "postgresql")) .Values.postgresql.external.host .Values.postgresql.enabled | quote }}
CORE_DB_PORT: {{ ternary 5432 (int .Values.postgresql.external.port) .Values.postgresql.enabled | quote }}
CORE_REDIS_HOST: {{ ternary (include "dnk.core.dependencyName" (dict "root" . "values" .Values.redis "service" "redis")) .Values.redis.external.host .Values.redis.enabled | quote }}
CORE_REDIS_PORT: {{ ternary 6379 (int .Values.redis.external.port) .Values.redis.enabled | quote }}
CORE_REDIS_DB: {{ .Values.redis.database | quote }}
{{- end -}}

{{- define "dnk.core.validatePort" -}}
{{- $port := regexFind ":[0-9]+$" .host | trimPrefix ":" -}}
{{- if and $port (or (lt (int $port) 1) (gt (int $port) 65535)) -}}
{{- fail (printf "%s port must be between 1 and 65535" .path) -}}
{{- end -}}
{{- end -}}

{{- define "dnk.core.validate" -}}
{{- $app := .Values.application -}}
{{- $origin := required "application.server.publicOrigin is required" $app.server.publicOrigin -}}
{{- $parsed := urlParse $origin -}}
{{- include "dnk.core.validatePort" (dict "host" $parsed.host "path" "application.server.publicOrigin") -}}
{{- if or (not (has $parsed.scheme (list "http" "https"))) (empty $parsed.host) $parsed.path $parsed.query $parsed.fragment $parsed.userinfo -}}
{{- fail "application.server.publicOrigin must be an HTTP(S) origin without path, credentials, query or fragment" -}}
{{- end -}}
{{- if and (not $app.server.debug) (ne $parsed.scheme "https") -}}{{- fail "production application.server.publicOrigin requires HTTPS" -}}{{- end -}}
{{- if and (not $app.server.debug) (not $app.server.trustProxy) -}}{{- fail "production gateway requires application.server.trustProxy=true" -}}{{- end -}}
{{- if and (not $app.server.debug) $app.server.allowedHosts (or (has "*" $app.server.allowedHosts) (not (has (include "dnk.core.hostname" .) $app.server.allowedHosts))) -}}
{{- fail "application.server.allowedHosts must include the public hostname and exclude '*'" -}}{{- end -}}
{{- range $env, $path := (.Files.Get "files/secrets.yaml" | fromYaml) -}}
{{- $value := $.Values -}}{{- range (splitList "." $path) -}}{{- $value = index $value . -}}{{- end -}}
{{- include "dnk.core.validateSecret" (dict "secret" $value "path" $path "required" (or (eq $env "CORE_SECRET_KEY") (and (eq $env "CORE_MFA_ENCRYPTION_KEY") (not $app.server.debug)))) -}}
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
{{- include "dnk.core.validateSecret" (dict "secret" .Values.postgresql.auth.password "path" "postgresql.auth.password" "required" true) -}}
{{- if not .Values.postgresql.enabled -}}{{- $_ := required "postgresql.external.host is required when embedded PostgreSQL is disabled" .Values.postgresql.external.host -}}{{- end -}}
{{- $url := .Values.redis.external.url -}}
{{- include "dnk.core.validateSecret" (dict "secret" $url "path" "redis.external.url" "required" false) -}}
{{- $hasUrl := or $url.value $url.existingSecret.name -}}
{{- include "dnk.core.validateSecret" (dict "secret" .Values.redis.auth.password "path" "redis.auth.password" "required" .Values.redis.enabled) -}}
{{- if and .Values.redis.enabled $hasUrl -}}{{- fail "redis.external.url requires redis.enabled=false" -}}{{- end -}}
{{- if and (not .Values.redis.enabled) (not $hasUrl) (not .Values.redis.external.host) -}}{{- fail "external Redis requires host or url" -}}{{- end -}}
{{- if and $hasUrl (or .Values.redis.external.host .Values.redis.auth.password.value .Values.redis.auth.password.existingSecret.name) -}}{{- fail "redis.external.url cannot be combined with external.host or auth.password" -}}{{- end -}}
{{- if and $url.value (not (regexMatch "^rediss?://[^/]+(/[0-9]+)?(\\?.*)?$" $url.value)) -}}{{- fail "redis.external.url.value must be a redis:// or rediss:// URL" -}}{{- end -}}
{{- if $url.value -}}
{{- $redisUrl := urlParse $url.value -}}
{{- if or $redisUrl.error (not (regexMatch "^(\\[[0-9A-Fa-f:]+\\]|[A-Za-z0-9][A-Za-z0-9.-]*)(:[0-9]+)?$" (default "" $redisUrl.host))) $redisUrl.fragment -}}
{{- fail "redis.external.url.value must have a valid hostname and port" -}}
{{- end -}}
{{- include "dnk.core.validatePort" (dict "host" $redisUrl.host "path" "redis.external.url") -}}
{{- end -}}
{{- range $name := list "backend" "frontend" "gateway" -}}
{{- $w := index $.Values $name -}}
{{- $_ := required (printf "%s.image.repository is required" $name) $w.image.repository -}}
{{- $_ := required (printf "%s.image.tag is required" $name) $w.image.tag -}}
{{- range $key := list "app.kubernetes.io/name" "app.kubernetes.io/instance" "app.kubernetes.io/component" -}}
{{- if hasKey $w.pod.labels $key -}}{{- fail (printf "%s.pod.labels cannot override selector %s" $name $key) -}}{{- end -}}
{{- end -}}
{{- range $key := list "checksum/config" "checksum/credentials" -}}
{{- if hasKey $w.pod.annotations $key -}}{{- fail (printf "%s.pod.annotations cannot override managed annotation %s" $name $key) -}}{{- end -}}
{{- end -}}{{- end -}}
{{- $reserved := include "dnk.core.config" . | fromYaml -}}
{{- range $key, $_ := (include "dnk.core.secretBindings" . | fromYaml) -}}{{- $_ := set $reserved $key true -}}{{- end -}}
{{- $_ := set $reserved "CORE_REDIS_URL" true -}}
{{- range .Values.backend.extraEnv -}}
{{- if hasKey $reserved .name -}}{{- fail (printf "backend.extraEnv duplicates managed variable %s" .name) -}}{{- end -}}
{{- $_ := set $reserved .name true -}}
{{- end -}}
{{- if .Values.ingress.enabled -}}
{{- if ne $parsed.scheme "https" -}}{{- fail "Ingress requires an HTTPS publicOrigin" -}}{{- end -}}
{{- if contains ":" $parsed.host -}}{{- fail "Ingress publicOrigin must use a DNS hostname without explicit port" -}}{{- end -}}
{{- $_ := required "ingress.tls.secretName is required" .Values.ingress.tls.secretName -}}
{{- end -}}
{{- end -}}
