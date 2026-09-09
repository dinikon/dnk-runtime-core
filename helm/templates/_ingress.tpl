{{/* System ingress controller and cert-manager are installed by the cluster operator. */}}
{{- define "dnk.ingress.tlsSecretName" -}}
{{- default (printf "%s-tls" (include "dnk.lifecycle.fullname" .)) .Values.ingress.tls.secretName -}}
{{- end -}}

{{- define "dnk.ingress.validate" -}}
{{- range $key := list "argocd.argoproj.io/sync-wave" "cert-manager.io/cluster-issuer" "cert-manager.io/issuer" "cert-manager.io/issuer-kind" "cert-manager.io/issuer-group" "kubernetes.io/ingress.class" -}}
{{- if hasKey $.Values.ingress.annotations $key -}}
{{- fail (printf "ingress.annotations cannot override managed annotation %s; use ingress.className or ingress.tls" $key) -}}
{{- end -}}
{{- end -}}
{{- if .Values.ingress.enabled -}}
{{- $_ := required "ingress.className is required" .Values.ingress.className -}}
{{- if not .Values.ingress.tls.clusterIssuer -}}
{{- $_ := required "ingress.tls.secretName is required when clusterIssuer is disabled" .Values.ingress.tls.secretName -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "dnk.ingress.annotations" -}}
{{- with .Values.ingress.annotations }}
{{ toYaml . }}
{{- end }}
argocd.argoproj.io/sync-wave: "0"
{{- with .Values.ingress.tls.clusterIssuer }}
cert-manager.io/cluster-issuer: {{ . | quote }}
{{- end }}
{{- end -}}
