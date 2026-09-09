{{/* Names reserve space for component suffixes, preserving long-release uniqueness. */}}
{{- define "dnk.lifecycle.shortName" -}}
{{- if gt (len .) 45 -}}
{{- printf "%s-%s" (. | trunc 36 | trimSuffix "-") (. | sha256sum | trunc 8) -}}
{{- else -}}{{- . -}}{{- end -}}
{{- end -}}

{{- define "dnk.lifecycle.fullname" -}}
{{/* Dependency aliases change Chart.Name; keep canonical names in both install modes. */}}
{{- $annotations := default dict .Chart.Annotations -}}
{{- $applicationName := default .Chart.Name (index $annotations "dnk.io/application-name") -}}
{{- default (printf "%s-%s" .Release.Name (default $applicationName .Values.nameOverride)) .Values.fullnameOverride | include "dnk.lifecycle.shortName" -}}
{{- end -}}

{{- define "dnk.lifecycle.jobName" -}}
{{- printf "%s-migrate-r%d" (include "dnk.lifecycle.fullname" .) (int .Release.Revision) -}}
{{- end -}}

{{- define "dnk.lifecycle.token" -}}
{{- $global := default dict .Values.global -}}
{{- $deployment := default dict $global.deployment -}}
{{- printf "%d:%s" (int .Release.Revision) (default "" $deployment.revision) | sha256sum | trunc 32 -}}
{{- end -}}

{{- define "dnk.lifecycle.coordinatorName" -}}
{{- $global := default dict .Values.global -}}
{{- $migrations := default dict $global.migrations -}}
{{- $name := include "dnk.lifecycle.fullname" . -}}
{{- if $migrations.coordinator -}}
{{- $name = include "dnk.lifecycle.shortName" (printf "%s-%s" .Release.Name $migrations.coordinator) -}}
{{- end -}}
{{- printf "%s-migrations" $name -}}
{{- end -}}

{{- define "dnk.lifecycle.serviceAccountName" -}}
{{- printf "%s-waiter" (include "dnk.lifecycle.coordinatorName" .) -}}
{{- end -}}

{{/* Shared mode always waits, including apps whose own migration is disabled. */}}
{{- define "dnk.lifecycle.gateEnabled" -}}
{{- $global := default dict .Values.global -}}
{{- $shared := default dict $global.migrations -}}
{{- if or .Values.migrations.enabled $shared.coordinator -}}true{{- end -}}
{{- end -}}

{{/* Caller passes {root: Helm context, targets: [{name: Job name, token: token}]}. */}}
{{- define "dnk.lifecycle.coordinator" -}}
{{- $root := .root -}}
{{- $name := include "dnk.lifecycle.coordinatorName" $root -}}
{{- $account := include "dnk.lifecycle.serviceAccountName" $root -}}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ $name }}
  annotations:
    argocd.argoproj.io/sync-wave: "-30"
  labels:
    app.kubernetes.io/instance: {{ $root.Release.Name | quote }}
    app.kubernetes.io/component: migration-coordinator
data:
  deployment-token: {{ include "dnk.lifecycle.token" $root | quote }}
  targets.json: {{ toJson .targets | quote }}
  gate.py: |
{{ include "dnk.lifecycle.gateScript" $root | indent 4 }}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ $account }}
  annotations:
    argocd.argoproj.io/sync-wave: "-30"
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: {{ $account }}
  annotations:
    argocd.argoproj.io/sync-wave: "-30"
{{ if .targets -}}
rules:
  - apiGroups: [batch]
    resources: [jobs]
    verbs: [get]
    resourceNames:
{{- range .targets }}
      - {{ .name | quote }}
{{- end }}
{{ else -}}
rules: []
{{ end -}}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: {{ $account }}
  annotations:
    argocd.argoproj.io/sync-wave: "-30"
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: {{ $account }}
subjects:
  - kind: ServiceAccount
    name: {{ $account }}
    namespace: {{ $root.Release.Namespace | quote }}
{{- end -}}

{{- define "dnk.lifecycle.localCoordinator" -}}
{{- $global := default dict .Values.global -}}
{{- $shared := default dict $global.migrations -}}
{{- if not $shared.coordinator -}}
{{- include "dnk.lifecycle.validateNames" (list .) -}}
{{- end -}}
{{- if and .Values.migrations.enabled (not $shared.coordinator) -}}
{{- include "dnk.lifecycle.coordinator" (dict "root" . "targets" (list (dict "name" (include "dnk.lifecycle.jobName" .) "token" (include "dnk.lifecycle.token" .)))) -}}
{{- end -}}
{{- end -}}

{{/* Reserve one Kubernetes identity and fail before rendering conflicting resources. */}}
{{- define "dnk.lifecycle.reserveName" -}}
{{- $identity := printf "%s/%s" .kind .name -}}
{{- if hasKey .names $identity -}}
{{- fail (printf "resource name collision %s between %s and %s; use distinct names or external infrastructure" $identity (index .names $identity) .owner) -}}
{{- end -}}
{{- $_ := set .names $identity .owner -}}
{{- end -}}

{{/* Takes the list of enabled application contexts, including their alias values. */}}
{{- define "dnk.lifecycle.validateNames" -}}
{{- $names := dict -}}
{{- $coordinators := dict -}}
{{- range $app := . -}}
{{- $fullname := include "dnk.lifecycle.fullname" $app -}}
{{- $owner := $app.Chart.Name -}}
{{- $runtime := hasKey $app.Values "rabbitmq" -}}
{{- $configmaps := list "config" "gateway" -}}
{{- if $runtime -}}{{- $configmaps = concat $configmaps (list "frontend" "scripts") -}}{{- end -}}
{{- range $suffix := $configmaps -}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" "ConfigMap" "name" (printf "%s-%s" $fullname $suffix) "owner" $owner) -}}
{{- end -}}
{{/* Credential names are reserved even when all sources are existing Secrets. */}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" "Secret" "name" (printf "%s-credentials" $fullname) "owner" $owner) -}}
{{- range $component := list "backend" "frontend" "gateway" -}}
{{- range $kind := list "Deployment" "Service" -}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" $kind "name" (printf "%s-%s" $fullname $component) "owner" $owner) -}}
{{- end -}}
{{- end -}}
{{- if $runtime -}}
{{- range $component := list "publisher" "console" -}}
{{- if (index $app.Values.workers $component).enabled -}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" "Deployment" "name" (printf "%s-%s" $fullname $component) "owner" $owner) -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- if $app.Values.migrations.enabled -}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" "Job" "name" (include "dnk.lifecycle.jobName" $app) "owner" $owner) -}}
{{- end -}}
{{- if include "dnk.lifecycle.gateEnabled" $app -}}
{{- $coordinator := include "dnk.lifecycle.coordinatorName" $app -}}
{{- if not (hasKey $coordinators $coordinator) -}}
{{- $_ := set $coordinators $coordinator true -}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" "ConfigMap" "name" $coordinator "owner" "migration coordinator") -}}
{{- range $kind := list "ServiceAccount" "Role" "RoleBinding" -}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" $kind "name" (include "dnk.lifecycle.serviceAccountName" $app) "owner" "migration coordinator") -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- range $service := list "postgresql" "redis" "rabbitmq" -}}
{{- if hasKey $app.Values $service -}}
{{- $dependency := index $app.Values $service -}}
{{- if $dependency.enabled -}}
{{- $name := default (printf "%s-%s" $app.Release.Name (default $service $dependency.nameOverride)) $dependency.fullnameOverride | include "dnk.lifecycle.shortName" -}}
{{- $depOwner := printf "%s.%s" $owner $service -}}
{{- range $kind := list "StatefulSet" "Service" -}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" $kind "name" $name "owner" $depOwner) -}}
{{- end -}}
{{- $headlessSuffix := index (dict "postgresql" "pg-headless" "redis" "rd-headless" "rabbitmq" "mq-headless") $service -}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" "Service" "name" (printf "%s-%s" $name $headlessSuffix) "owner" $depOwner) -}}
{{- if $dependency.auth.password.value -}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" "Secret" "name" (printf "%s-auth" $name) "owner" $depOwner) -}}
{{- end -}}
{{/* Distinct resource names must not mask two Services selecting both databases. */}}
{{- include "dnk.lifecycle.reserveName" (dict "names" $names "kind" "StatefulSet selector" "name" (printf "%s/%s/%s" $app.Release.Name $service (default $service $dependency.nameOverride)) "owner" $depOwner) -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/* Include as initContainers list items; no credentials enter application containers. */}}
{{- define "dnk.lifecycle.gate" -}}
{{- if include "dnk.lifecycle.gateEnabled" . }}
- name: wait-migrations
  image: {{ printf "%s:%s" .Values.backend.image.repository .Values.backend.image.tag | quote }}
  imagePullPolicy: {{ .Values.backend.image.pullPolicy }}
  command: [python, /opt/dnk-gate/gate.py]
  env:
    - name: DNK_GATE_NAMESPACE
      valueFrom:
        fieldRef:
          fieldPath: metadata.namespace
    - name: DNK_GATE_TIMEOUT_SECONDS
      value: {{ .Values.migrations.gateTimeoutSeconds | quote }}
    - name: DNK_GATE_DEPLOYMENT_TOKEN
      value: {{ include "dnk.lifecycle.token" . | quote }}
  resources:
    requests:
      cpu: 10m
      memory: 32Mi
    limits:
      memory: 96Mi
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    runAsNonRoot: true
    runAsUser: 65532
    capabilities:
      drop: [ALL]
  volumeMounts:
    - name: migration-gate
      mountPath: /opt/dnk-gate
      readOnly: true
    - name: migration-api-token
      mountPath: /var/run/dnk-api
      readOnly: true
{{- end -}}
{{- end -}}

{{- define "dnk.lifecycle.gateVolumes" -}}
{{- if include "dnk.lifecycle.gateEnabled" . }}
- name: migration-gate
  configMap:
    name: {{ include "dnk.lifecycle.coordinatorName" . }}
    defaultMode: 0444
- name: migration-api-token
  projected:
    defaultMode: 0444
    sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 600
      - configMap:
          name: kube-root-ca.crt
          items:
            - key: ca.crt
              path: ca.crt
{{- end -}}
{{- end -}}
