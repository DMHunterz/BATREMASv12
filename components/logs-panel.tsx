"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { RefreshCw, Download } from "lucide-react"

export function LogsPanel() {
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/logs")
      const data = await response.json()
      setLogs(data.logs || [])
    } catch (error) {
      console.error("Erro ao carregar logs:", error)
    } finally {
      setLoading(false)
    }
  }

  const downloadLogs = () => {
    const logText = logs.join("\n")
    const blob = new Blob([logText], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `bot_logs_${new Date().toISOString().split("T")[0]}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  useEffect(() => {
    fetchLogs()
    const interval = setInterval(fetchLogs, 10000) // Atualiza a cada 10 segundos
    return () => clearInterval(interval)
  }, [])

  const getLogLevel = (log: string) => {
    if (log.includes("ERROR") || log.includes("ERRO")) return "error"
    if (log.includes("WARNING") || log.includes("AVISO")) return "warning"
    if (log.includes("INFO")) return "info"
    return "default"
  }

  const getLogColor = (level: string) => {
    switch (level) {
      case "error":
        return "text-red-600"
      case "warning":
        return "text-amber-600"
      case "info":
        return "text-blue-600"
      default:
        return "text-slate-600"
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Logs do Bot</CardTitle>
            <CardDescription>Últimas 100 linhas de log em tempo real</CardDescription>
          </div>

          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={downloadLogs}>
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
            <Button variant="outline" size="sm" onClick={fetchLogs} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Atualizar
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[600px] w-full rounded-md border p-4">
          <div className="space-y-1">
            {logs.length === 0 ? (
              <p className="text-slate-500 text-center py-8">Nenhum log disponível</p>
            ) : (
              logs.map((log, index) => {
                const level = getLogLevel(log)
                const color = getLogColor(level)

                return (
                  <div key={index} className={`text-sm font-mono ${color} hover:bg-slate-50 p-1 rounded`}>
                    {log}
                  </div>
                )
              })
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
