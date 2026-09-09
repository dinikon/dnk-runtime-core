{{/* Public helper accepts {Values: <rabbitmq values>, Release: <release>}. */}}
{{- define "dnk.rabbitmq.fullname" -}}
{{- $name := default (printf "%s-%s" .Release.Name (default "rabbitmq" .Values.nameOverride)) .Values.fullnameOverride -}}
{{- if gt (len $name) 45 -}}
{{- printf "%s-%s" ($name | trunc 36 | trimSuffix "-") ($name | sha256sum | trunc 8) -}}
{{- else -}}{{- $name -}}{{- end -}}
{{- end -}}

{{/* Reserve the suffix while preserving uniqueness of long release names. */}}
{{- define "dnk.rabbitmq.headlessName" -}}
{{- $fullname := include "dnk.rabbitmq.fullname" . -}}
{{- if gt (len $fullname) 51 -}}
{{- printf "%s-%s-mq-headless" ($fullname | trunc 42 | trimSuffix "-") ($fullname | sha256sum | trunc 8) -}}
{{- else -}}
{{- printf "%s-mq-headless" $fullname -}}
{{- end -}}
{{- end -}}

{{- define "dnk.rabbitmq.selectorLabels" -}}
app.kubernetes.io/name: {{ default "rabbitmq" .Values.nameOverride | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/component: rabbitmq
{{- end -}}

{{- define "dnk.rabbitmq.labels" -}}
{{ include "dnk.rabbitmq.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | quote }}
{{- end -}}

{{- define "dnk.rabbitmq.secretName" -}}
{{- default (printf "%s-auth" (include "dnk.rabbitmq.fullname" .)) .Values.auth.password.existingSecret.name -}}
{{- end -}}

{{- define "dnk.rabbitmq.secretKey" -}}
{{- if .Values.auth.password.existingSecret.name -}}
{{- .Values.auth.password.existingSecret.key -}}
{{- else -}}password{{- end -}}
{{- end -}}

{{- define "dnk.rabbitmq.validate" -}}
{{- $password := .Values.auth.password -}}
{{- if and $password.value (or $password.existingSecret.name $password.existingSecret.key) -}}
{{- fail "rabbitmq.auth.password: set value OR existingSecret, never both" -}}
{{- end -}}
{{- if not (or $password.value (and $password.existingSecret.name $password.existingSecret.key)) -}}
{{- fail "rabbitmq.auth.password: a non-empty value or existingSecret.name and existingSecret.key is required" -}}
{{- end -}}
{{- if and (not .Values.persistence.enabled) .Values.persistence.existingClaim -}}
{{- fail "rabbitmq.persistence.existingClaim requires persistence.enabled=true" -}}
{{- end -}}
{{- end -}}
