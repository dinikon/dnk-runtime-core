{{- define "dnk.runtime.validateControlPlane" -}}
{{- $cp := .Values.controlPlane -}}
{{- include "dnk.runtime.validateSecret" (dict "secret" $cp.rabbitmqUrl "path" "controlPlane.rabbitmqUrl" "required" $cp.enabled) -}}
{{- if $cp.enabled -}}
{{- range $field := list "publicOrigin" "managementOrigin" "managementHost" "instanceId" "ingressProbeAddress" "credentialsSecret" "clientCaSecret" -}}
{{- $_ := required (printf "controlPlane.%s is required when enabled" $field) (index $cp $field) -}}
{{- end -}}
{{- range $field := list "allowedBaseDomains" "trustedProxyNetworks" "allowedCoreFingerprints" -}}
{{- if not (index $cp $field) -}}{{- fail (printf "controlPlane.%s must not be empty" $field) -}}{{- end -}}
{{- end -}}
{{- if not .Values.ingress.enabled -}}{{- fail "Control Plane integration requires public ingress" -}}{{- end -}}
{{- if not $cp.networkPolicy.ingressNamespaceSelector -}}{{- fail "Control Plane requires an explicit ingress namespace selector" -}}{{- end -}}
{{- if not $cp.networkPolicy.ingressPodSelector -}}{{- fail "Control Plane requires an explicit ingress pod selector" -}}{{- end -}}
{{- range $network := $cp.trustedProxyNetworks -}}
{{- if has $network (list "0.0.0.0/0" "::/0" "*") -}}{{- fail "Control Plane must not trust all proxy addresses" -}}{{- end -}}
{{- end -}}
{{- $hosts := include "dnk.ingress.hosts" . | fromYamlArray -}}
{{- range $zone := $cp.allowedBaseDomains -}}
{{- if not (has (printf "*.%s" $zone) $hosts) -}}{{- fail (printf "Control Plane zone %s requires its wildcard ingress host" $zone) -}}{{- end -}}
{{- end -}}
{{- if has $cp.managementHost $hosts -}}{{- fail "Management host must not appear in public ingress.hosts" -}}{{- end -}}
{{- if not $cp.ingress.className -}}{{- fail "Control Plane management ingress requires className" -}}{{- end -}}
{{- if and (not $cp.ingress.tls.clusterIssuer) (not $cp.ingress.tls.secretName) -}}{{- fail "Management ingress requires TLS secretName or clusterIssuer" -}}{{- end -}}
{{- if ge (int $cp.stepTimeoutSeconds) (int $cp.leaseSeconds) -}}{{- fail "Control Plane step timeout must be shorter than lease" -}}{{- end -}}
{{- if eq $cp.installQueue $cp.accessQueue -}}{{- fail "Installation and access queues must differ" -}}{{- end -}}
{{- end -}}
{{- end -}}
