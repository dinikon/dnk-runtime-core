{{- define "dnk.minio.fullname" -}}
{{- $name := default (printf "%s-%s" .Release.Name (default "minio" .Values.nameOverride)) .Values.fullnameOverride -}}
{{- if gt (len $name) 45 -}}
{{- printf "%s-%s" ($name | trunc 36 | trimSuffix "-") ($name | sha256sum | trunc 8) -}}
{{- else -}}{{- $name -}}{{- end -}}
{{- end -}}

{{- define "dnk.minio.headlessName" -}}
{{- printf "%s-s3-headless" (include "dnk.minio.fullname" .) -}}
{{- end -}}

{{- define "dnk.minio.selectorLabels" -}}
app.kubernetes.io/name: {{ default "minio" .Values.nameOverride | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/component: minio
{{- end -}}

{{- define "dnk.minio.labels" -}}
{{ include "dnk.minio.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | quote }}
{{- end -}}

{{- define "dnk.minio.secretName" -}}
{{- $credential := index .root.Values.auth .credential -}}
{{- default (printf "%s-auth" (include "dnk.minio.fullname" .root)) $credential.existingSecret.name -}}
{{- end -}}

{{- define "dnk.minio.secretKey" -}}
{{- $credential := index .root.Values.auth .credential -}}
{{- if $credential.existingSecret.name -}}{{- $credential.existingSecret.key -}}
{{- else -}}{{- ternary "access-key" "secret-key" (eq .credential "accessKey") -}}{{- end -}}
{{- end -}}

{{- define "dnk.minio.validate" -}}
{{- range $name := list "accessKey" "secretKey" -}}
{{- $credential := index $.Values.auth $name -}}
{{- if and $credential.value (or $credential.existingSecret.name $credential.existingSecret.key) -}}
{{- fail (printf "minio.auth.%s: set value OR existingSecret, never both" $name) -}}
{{- end -}}
{{- if not (or $credential.value (and $credential.existingSecret.name $credential.existingSecret.key)) -}}
{{- fail (printf "minio.auth.%s: a non-empty value or existingSecret.name and existingSecret.key is required" $name) -}}
{{- end -}}
{{- $minimum := ternary 3 8 (eq $name "accessKey") -}}
{{- if and $credential.value (lt (len $credential.value) $minimum) -}}
{{- fail (printf "minio.auth.%s.value must contain at least %d characters" $name $minimum) -}}
{{- end -}}
{{- end -}}
{{- if and (not .Values.persistence.enabled) .Values.persistence.existingClaim -}}
{{- fail "minio.persistence.existingClaim requires persistence.enabled=true" -}}
{{- end -}}
{{- end -}}
