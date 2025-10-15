{{/*
Resource optimization helpers for limited environments
*/}}

{{- define "carpeta-ciudadana.optimizedResources" -}}
{{- $defaultRequests := .Values.global.resourceOptimization.defaultRequests -}}
{{- $defaultLimits := .Values.global.resourceOptimization.defaultLimits -}}
{{- if .Values.global.resourceOptimization.enabled -}}
requests:
  cpu: {{ .resources.requests.cpu | default $defaultRequests.cpu }}
  memory: {{ .resources.requests.memory | default $defaultRequests.memory }}
limits:
  cpu: {{ .resources.limits.cpu | default $defaultLimits.cpu }}
  memory: {{ .resources.limits.memory | default $defaultLimits.memory }}
{{- else -}}
requests:
  cpu: {{ .resources.requests.cpu | default "100m" }}
  memory: {{ .resources.requests.memory | default "128Mi" }}
limits:
  cpu: {{ .resources.limits.cpu | default "500m" }}
  memory: {{ .resources.limits.memory | default "512Mi" }}
{{- end -}}
{{- end -}}

{{/*
Optimized replica count for limited environments
*/}}
{{- define "carpeta-ciudadana.optimizedReplicas" -}}
{{- $context := . -}}
{{- if $context.global.resourceOptimization.enabled -}}
{{ .replicaCount | default 1 }}
{{- else -}}
{{ .replicaCount | default 2 }}
{{- end -}}
{{- end -}}

{{/*
HPA configuration for limited environments
*/}}
{{- define "carpeta-ciudadana.optimizedHPA" -}}
{{- if and .autoscaling.enabled .Values.global.resourceOptimization.enabled -}}
minReplicas: {{ .autoscaling.minReplicas | default 1 }}
maxReplicas: {{ .autoscaling.maxReplicas | default .Values.global.resourceOptimization.maxReplicas }}
{{- else if .autoscaling.enabled -}}
minReplicas: {{ .autoscaling.minReplicas | default 2 }}
maxReplicas: {{ .autoscaling.maxReplicas | default 10 }}
{{- else -}}
enabled: false
{{- end -}}
{{- end -}}
