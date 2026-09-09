const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function fetchJson<T = any>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `Request failed with status ${response.status}`)
  }

  return response.json()
}

export async function getProductionOverview() {
  return fetchJson("/api/production/overview")
}

export async function getIncidents() {
  return fetchJson("/api/incidents")
}

export async function getIncident(id: string) {
  return fetchJson(`/api/incidents/${id}`)
}

export async function getTelemetryStatus() {
  return fetchJson("/api/telemetry/status")
}

export async function getGrafanaStatus() {
  return fetchJson("/api/integrations/grafana/status").catch(() => fetchJson("/api/agent/grafana/status"))
}

export async function simulateIncident(scenario: string) {
  return fetchJson("/api/incidents/simulate", {
    method: "POST",
    body: JSON.stringify({ scenario }),
  })
}

export async function resetDemo() {
  return fetchJson("/api/incidents/reset", {
    method: "POST",
  })
}

export async function getWhatIfImpact(incidentId: string) {
  return fetchJson(`/api/agent/impact`, {
    method: "POST",
    body: JSON.stringify({ incident_id: incidentId }),
  })
}

export async function approveRemediation(actionId: string) {
  return fetchJson("/api/remediation/approve", {
    method: "POST",
    body: JSON.stringify({ remediation_id: actionId, approved_by: "OPERATOR" }),
  })
}

export async function simulateRemediation(actionId: string) {
  return fetchJson("/api/remediation/simulate", {
    method: "POST",
    body: JSON.stringify({ remediation_id: actionId }),
  })
}
