"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { 
  AlertCircle, 
  RefreshCw, 
  Activity, 
  Terminal, 
  ExternalLink, 
  HardDrive, 
  Server, 
  Clock, 
  Wifi, 
  Camera, 
  Layers,
  ArrowUpRight
} from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { getTelemetryStatus, simulateIncident, resetDemo, getGrafanaStatus } from "@/lib/api"

export default function TelemetryPage() {
  const [mounted, setMounted] = useState(false)
  const [status, setStatus] = useState<any>(null)
  const [grafanaStatus, setGrafanaStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [simulating, setSimulating] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  const fetchData = async () => {
    try {
      const [telData, grafData] = await Promise.all([
        getTelemetryStatus(),
        getGrafanaStatus().catch(() => ({ mcp_available: false, message: "Connection failed" }))
      ])
      setStatus(telData)
      setGrafanaStatus(grafData)
      setLastUpdated(new Date())
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setMounted(true)
    fetchData()
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [])

  if (!mounted || (loading && !status)) {
    return <div className="flex h-[50vh] items-center justify-center">Loading telemetry data...</div>
  }

  const handleSimulate = async (scenario: string) => {
    setSimulating(true)
    try {
      await simulateIncident(scenario)
      await fetchData()
    } catch (err) {
      console.error(err)
      alert("Failed to simulate incident")
    } finally {
      setSimulating(false)
    }
  }

  const handleReset = async () => {
    setResetting(true)
    try {
      await resetDemo()
      await fetchData()
    } catch (err) {
      console.error(err)
      alert("Failed to reset demo")
    } finally {
      setResetting(false)
    }
  }

  const grafanaUrl = grafanaStatus?.grafana_url || "https://mightyblackberry600.grafana.net"
  const exploreUrl = grafanaStatus?.explore_url || `${grafanaUrl}/explore`

  const scenarios = [
    {
      id: "STORAGE_SATURATION",
      name: "Storage Saturation",
      desc: "Disk fills up causing I/O contention and dropped throughput.",
      target: "INGEST-01",
      affectedMetric: "storage_utilization",
    },
    {
      id: "NETWORK_DEGRADATION",
      name: "Network Degradation",
      desc: "Packet loss and latency spike on edge network.",
      target: "NET-EDGE-07",
      affectedMetric: "packet_loss_pct",
    },
    {
      id: "CAMERA_FAILURE",
      name: "Camera Overheat",
      desc: "Thermal event causing recording errors and dropped frames.",
      target: "CAM-03",
      affectedMetric: "camera_temperature_c",
    },
    {
      id: "RENDER_BOTTLENECK",
      name: "Render Bottleneck",
      desc: "GPU saturation causing queue buildup.",
      target: "EDIT-01",
      affectedMetric: "gpu_usage_pct",
    }
  ]

  const metrics = status?.metrics || {}
  const storageVal = metrics.storage_utilization || 68.0
  const ingestThroughput = metrics.ingest_throughput_gbps || 1.85
  const writeLatency = metrics.disk_write_latency_ms || 40.0
  const uploadQueue = metrics.upload_queue_depth || 18.0
  const networkLatency = metrics.network_latency_ms || 2.4
  const packetLoss = metrics.packet_loss_pct || 0.01
  const cameraTemp = metrics.camera_temperature_c || 38.0
  const gpuUsage = metrics.gpu_usage_pct || 45.0

  const isStorageCritical = storageVal > 85.0

  return (
    <div className="space-y-8 pb-12 animate-in fade-in duration-500" suppressHydrationWarning>
      {/* Header with quick links */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Telemetry &amp; Control</h1>
          <p className="text-muted-foreground">Manage the synthetic environment and live Grafana Cloud integration</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <a
            href={exploreUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80 h-9 px-4 py-2 border border-secondary/50"
          >
            <ExternalLink className="mr-2 h-4 w-4 text-orange-400" />
            Open Grafana Explore ↗
          </a>
          <Button 
            variant="outline" 
            onClick={handleReset} 
            disabled={resetting || !status?.incident_active}
          >
            {resetting ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Reset Demo
          </Button>
        </div>
      </div>

      {/* Overview Cards: Simulator & Grafana MCP */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="mr-2 h-5 w-5 text-sky-400" />
              Simulator Engine
            </CardTitle>
            <CardDescription>Synthetic production telemetry generator</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">State</span>
              <Badge variant={status?.incident_active ? "destructive" : "success"}>
                {status?.simulator_state || "UNKNOWN"}
              </Badge>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">Active Scenario</span>
              <span className="font-medium">{status?.scenario || "None (Baseline)"}</span>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">Data Destination</span>
              <Badge variant="outline" className="text-emerald-400 border-emerald-900/50 bg-emerald-500/10">
                Grafana Cloud (Remote Write)
              </Badge>
            </div>
            <div className="flex justify-between pb-2">
              <span className="text-muted-foreground">Push Frequency</span>
              <span className="text-sm font-mono text-muted-foreground">Every 15s</span>
            </div>
            
            {status?.incident_active && (
              <div className="mt-4 rounded-md bg-destructive/10 p-4 border border-destructive/30">
                <div className="flex items-start">
                  <AlertCircle className="mr-2 h-5 w-5 text-destructive shrink-0 mt-0.5" />
                  <div className="space-y-2">
                    <h4 className="font-semibold text-destructive">Incident is active in Grafana</h4>
                    <p className="text-sm text-destructive/90">
                      Degraded telemetry is actively pushing to Prometheus on Grafana Cloud.
                    </p>
                    <div className="flex gap-2 pt-1">
                      <a
                        href={exploreUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs inline-flex items-center text-destructive underline font-semibold hover:opacity-80"
                      >
                        Inspect query in Grafana ↗
                      </a>
                      <span className="text-destructive/50">•</span>
                      <Link href="/incidents" className="text-xs inline-flex items-center text-primary underline font-semibold hover:opacity-80">
                        Investigate Incident →
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Terminal className="mr-2 h-5 w-5 text-emerald-400" />
              Grafana MCP Integration
            </CardTitle>
            <CardDescription>Model Context Protocol gateway for AI agent investigations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={grafanaStatus?.mcp_available ? "success" : "destructive"}>
                {grafanaStatus?.mcp_available ? "CONNECTED" : "UNAVAILABLE"}
              </Badge>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">MCP Gateway</span>
              <span className="text-sm font-mono text-emerald-400">
                {grafanaStatus?.mcp_url ? (grafanaStatus.mcp_url.endsWith("/mcp") ? grafanaStatus.mcp_url : `${grafanaStatus.mcp_url}/mcp`) : "http://localhost:8000/mcp"}
              </span>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground">Connected Stack</span>
              <a
                href={grafanaUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-mono text-primary hover:underline flex items-center"
              >
                mightyblackberry600 ↗
              </a>
            </div>
            <div className="flex justify-between pb-2">
              <span className="text-muted-foreground">Available MCP Tools</span>
              <span className="font-medium text-emerald-400">{grafanaStatus?.tools_available?.length || 6} tools ready</span>
            </div>

            <div className="mt-4 rounded-md bg-secondary/30 p-3 text-xs text-muted-foreground space-y-1">
              <div className="font-semibold text-foreground flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                Live Tool Registry Active
              </div>
              <p>Gemini queries PromQL, logs, and datasources directly via standard JSON-RPC 2.0.</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Live Telemetry Stream Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
              <HardDrive className="h-5 w-5 text-primary" />
              Live Telemetry Stream
            </h2>
            <p className="text-sm text-muted-foreground">
              Current metric values actively streaming to Grafana Cloud Prometheus
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="font-mono">Pushed {lastUpdated.toLocaleTimeString()}</span>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Storage Utilization */}
          <Card className={isStorageCritical ? "border-destructive bg-destructive/5" : ""}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Storage Utilization</span>
                <Badge variant={isStorageCritical ? "destructive" : "secondary"}>INGEST-01</Badge>
              </div>
              <CardTitle className={`text-2xl font-mono ${isStorageCritical ? "text-destructive" : ""}`}>
                {storageVal.toFixed(1)}%
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <Progress value={storageVal} className="h-2" />
              <p className="text-xs text-muted-foreground mt-2">
                Baseline: 68.0% &bull; Threshold: 85.0%
              </p>
            </CardContent>
          </Card>

          {/* Ingest Throughput */}
          <Card className={ingestThroughput < 1.0 ? "border-amber-500/50 bg-amber-500/5" : ""}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Ingest Throughput</span>
                <Badge variant="secondary">INGEST-01</Badge>
              </div>
              <CardTitle className={`text-2xl font-mono ${ingestThroughput < 1.0 ? "text-amber-400" : ""}`}>
                {ingestThroughput.toFixed(2)} GB/s
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground">
                Normal target: 1.85 GB/s minimum
              </p>
            </CardContent>
          </Card>

          {/* Disk Write Latency */}
          <Card className={writeLatency > 70.0 ? "border-amber-500/50 bg-amber-500/5" : ""}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Write Latency</span>
                <Badge variant="secondary">I/O Queue</Badge>
              </div>
              <CardTitle className={`text-2xl font-mono ${writeLatency > 70.0 ? "text-amber-400" : ""}`}>
                {writeLatency.toFixed(1)} ms
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground">
                Baseline: 40.0 ms &bull; Spikes on contention
              </p>
            </CardContent>
          </Card>

          {/* Upload Queue Depth */}
          <Card className={uploadQueue > 100 ? "border-amber-500/50 bg-amber-500/5" : ""}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Upload Queue Depth</span>
                <Badge variant="secondary">Frames</Badge>
              </div>
              <CardTitle className={`text-2xl font-mono ${uploadQueue > 100 ? "text-amber-400" : ""}`}>
                {Math.round(uploadQueue)} frames
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground">
                Normal: 18 frames &bull; Buffer overflow risk
              </p>
            </CardContent>
          </Card>

          {/* Network Latency */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Network Latency</span>
                <Badge variant="secondary">NET-CORE-01</Badge>
              </div>
              <CardTitle className="text-2xl font-mono">
                {networkLatency.toFixed(1)} ms
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground">Normal baseline: 2.4 ms</p>
            </CardContent>
          </Card>

          {/* Packet Loss */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Packet Loss</span>
                <Badge variant="secondary">NET-EDGE-07</Badge>
              </div>
              <CardTitle className="text-2xl font-mono">
                {packetLoss.toFixed(2)}%
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground">Healthy range: &lt; 0.05%</p>
            </CardContent>
          </Card>

          {/* Camera Temperature */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Camera Thermal</span>
                <Badge variant="secondary">CAM-03</Badge>
              </div>
              <CardTitle className="text-2xl font-mono">
                {cameraTemp.toFixed(1)}°C
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground">Operating limit: 55.0°C</p>
            </CardContent>
          </Card>

          {/* GPU Usage */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Editorial GPU</span>
                <Badge variant="secondary">EDIT-01</Badge>
              </div>
              <CardTitle className="text-2xl font-mono">
                {gpuUsage.toFixed(1)}%
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground">Rendering timeline frames</p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Incident Simulator Scenarios */}
      <div className="space-y-4 pt-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Incident Simulator</h2>
          <p className="text-muted-foreground">
            Trigger specific infrastructure incidents to test real-time degradation in Grafana Cloud and agent diagnostics.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {scenarios.map((scenario) => {
            const isActive = status?.scenario === scenario.id
            return (
              <Card key={scenario.id} className={isActive ? "border-destructive shadow-lg bg-destructive/5" : ""}>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg">{scenario.name}</CardTitle>
                    <Badge variant={isActive ? "destructive" : "outline"}>{scenario.target}</Badge>
                  </div>
                  <CardDescription>{scenario.desc}</CardDescription>
                </CardHeader>
                <CardFooter className="flex gap-2">
                  <Button 
                    onClick={() => handleSimulate(scenario.id)} 
                    disabled={simulating || status?.incident_active}
                    variant={isActive ? "destructive" : "default"}
                    className="w-full font-semibold"
                  >
                    {isActive ? "Currently Active in Grafana" : "Simulate Incident"}
                  </Button>
                </CardFooter>
              </Card>
            )
          })}
        </div>
      </div>
    </div>
  )
}
