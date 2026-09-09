{{/* Public helper accepts {Values: <postgresql values>, Release: <release>}. */}}
{{- define "dnk.postgresql.fullname" -}}
{{- $name := default (printf "%s-%s" .Release.Name (default "postgresql" .Values.nameOverride)) .Values.fullnameOverride -}}
{{- if gt (len $name) 45 -}}
{{- printf "%s-%s" ($name | trunc 36 | trimSuffix "-") ($name | sha256sum | trunc 8) -}}
{{- else -}}{{- $name -}}{{- end -}}
{{- end -}}

{{/* Reserve the suffix while preserving uniqueness of long release names. */}}
{{- define "dnk.postgresql.headlessName" -}}
{{- $fullname := include "dnk.postgresql.fullname" . -}}
{{- if gt (len $fullname) 51 -}}
{{- printf "%s-%s-pg-headless" ($fullname | trunc 42 | trimSuffix "-") ($fullname | sha256sum | trunc 8) -}}
{{- else -}}
{{- printf "%s-pg-headless" $fullname -}}
{{- end -}}
{{- end -}}

{{- define "dnk.postgresql.selectorLabels" -}}
app.kubernetes.io/name: {{ default "postgresql" .Values.nameOverride | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/component: postgresql
{{- end -}}

{{- define "dnk.postgresql.labels" -}}
{{ include "dnk.postgresql.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | quote }}
{{- end -}}

{{- define "dnk.postgresql.secretName" -}}
{{- default (printf "%s-auth" (include "dnk.postgresql.fullname" .)) .Values.auth.password.existingSecret.name -}}
{{- end -}}

{{- define "dnk.postgresql.secretKey" -}}
{{- if .Values.auth.password.existingSecret.name -}}
{{- .Values.auth.password.existingSecret.key -}}
{{- else -}}password{{- end -}}
{{- end -}}

{{- define "dnk.postgresql.validate" -}}
{{- $password := .Values.auth.password -}}
{{- if and $password.value (or $password.existingSecret.name $password.existingSecret.key) -}}
{{- fail "postgresql.auth.password: set value OR existingSecret, never both" -}}
{{- end -}}
{{- if not (or $password.value (and $password.existingSecret.name $password.existingSecret.key)) -}}
{{- fail "postgresql.auth.password: a non-empty value or existingSecret.name and existingSecret.key is required" -}}
{{- end -}}
{{- if and (not .Values.persistence.enabled) .Values.persistence.existingClaim -}}
{{- fail "postgresql.persistence.existingClaim requires persistence.enabled=true" -}}
{{- end -}}
{{- end -}}
