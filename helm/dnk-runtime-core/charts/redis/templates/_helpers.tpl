{{/* Public helper accepts {Values: <redis values>, Release: <release>}. */}}
{{- define "dnk.redis.fullname" -}}
{{- $name := default (printf "%s-%s" .Release.Name (default "redis" .Values.nameOverride)) .Values.fullnameOverride -}}
{{- if gt (len $name) 45 -}}
{{- printf "%s-%s" ($name | trunc 36 | trimSuffix "-") ($name | sha256sum | trunc 8) -}}
{{- else -}}{{- $name -}}{{- end -}}
{{- end -}}

{{/* Reserve the suffix while preserving uniqueness of long release names. */}}
{{- define "dnk.redis.headlessName" -}}
{{- $fullname := include "dnk.redis.fullname" . -}}
{{- if gt (len $fullname) 51 -}}
{{- printf "%s-%s-rd-headless" ($fullname | trunc 42 | trimSuffix "-") ($fullname | sha256sum | trunc 8) -}}
{{- else -}}
{{- printf "%s-rd-headless" $fullname -}}
{{- end -}}
{{- end -}}

{{- define "dnk.redis.selectorLabels" -}}
app.kubernetes.io/name: {{ default "redis" .Values.nameOverride | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/component: redis
{{- end -}}

{{- define "dnk.redis.labels" -}}
{{ include "dnk.redis.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | quote }}
{{- end -}}

{{- define "dnk.redis.secretName" -}}
{{- default (printf "%s-auth" (include "dnk.redis.fullname" .)) .Values.auth.password.existingSecret.name -}}
{{- end -}}

{{- define "dnk.redis.secretKey" -}}
{{- if .Values.auth.password.existingSecret.name -}}
{{- .Values.auth.password.existingSecret.key -}}
{{- else -}}password{{- end -}}
{{- end -}}

{{- define "dnk.redis.validate" -}}
{{- $password := .Values.auth.password -}}
{{- if and $password.value (or $password.existingSecret.name $password.existingSecret.key) -}}
{{- fail "redis.auth.password: set value OR existingSecret, never both" -}}
{{- end -}}
{{- if not (or $password.value (and $password.existingSecret.name $password.existingSecret.key)) -}}
{{- fail "redis.auth.password: a non-empty value or existingSecret.name and existingSecret.key is required" -}}
{{- end -}}
{{- if and (not .Values.persistence.enabled) .Values.persistence.existingClaim -}}
{{- fail "redis.persistence.existingClaim requires persistence.enabled=true" -}}
{{- end -}}
{{- end -}}
