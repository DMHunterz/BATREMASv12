"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Play, Square, Settings, Activity, TrendingUp, AlertCircle } from "lucide-react"
import { ConfigPanel } from "@/components/config-panel"
import { LogsPanel } from "@/components/logs-panel"
import { PositionsPanel } from "@/components/positions-panel"
import { StatsCards } from "@/components/stats-cards"
import { BalanceCard } from "@/components/balance-card"
import { KeepAlive } from "@/components/keep-alive"

interface BotStatus {
  running: boolean
  start_time?: string
  uptime?: string
  positions_count: number
  test_mode: boolean
}

export default function Dashboard() {
  const [botStatus, setBotStatus] = useState<BotStatus>({
    running: false,
    positions_count: 0,
    test_mode: true,
  })
  const [loading, setLoading] = useState(false)

  const fetchStatus = async () => {
    try {
      const response = await fetch("/api/status")
      const data = await response.json()
      setBotStatus(data)
    } catch (error) {
      console.error("Erro ao buscar status:", error)
    }
  }

  const handleStartStop = async () => {
    setLoading(true)
    try {
      const endpoint = botStatus.running ? "/api/stop" : "/api/start"
      const response = await fetch(endpoint, { method: "POST" })

      if (response.ok) {
        await fetchStatus()
      }
    } catch (error) {
      console.error("Erro ao controlar bot:", error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000) // Atualiza a cada 5 segundos
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Trading Bot Dashboard</h1>
            <p className="text-slate-600">Gerencie seu bot de trading Binance</p>
          </div>

          <div className="flex items-center gap-4">
            <KeepAlive />

            <Badge variant={botStatus.test_mode ? "secondary" : "destructive"}>
              {botStatus.test_mode ? "MODO TESTE" : "MODO REAL"}
            </Badge>

            <Badge variant={botStatus.running ? "default" : "secondary"}>
              {botStatus.running ? "ATIVO" : "PARADO"}
            </Badge>

            <Button
              onClick={handleStartStop}
              disabled={loading}
              variant={botStatus.running ? "destructive" : "default"}
              size="lg"
            >
              {botStatus.running ? (
                <>
                  <Square className="w-4 h-4 mr-2" />
                  Parar Bot
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Iniciar Bot
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <StatsCards botStatus={botStatus} />

        {/* Main Content */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">
              <Activity className="w-4 h-4 mr-2" />
              Visão Geral
            </TabsTrigger>
            <TabsTrigger value="config">
              <Settings className="w-4 h-4 mr-2" />
              Configurações
            </TabsTrigger>
            <TabsTrigger value="positions">
              <TrendingUp className="w-4 h-4 mr-2" />
              Posições
            </TabsTrigger>
            <TabsTrigger value="logs">
              <AlertCircle className="w-4 h-4 mr-2" />
              Logs
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <div className="grid gap-6 md:grid-cols-3">
              <BalanceCard />

              <Card>
                <CardHeader>
                  <CardTitle>Status do Bot</CardTitle>
                  <CardDescription>Informações em tempo real sobre o bot</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <Badge variant={botStatus.running ? "default" : "secondary"}>
                      {botStatus.running ? "Rodando" : "Parado"}
                    </Badge>
                  </div>

                  {botStatus.uptime && (
                    <div className="flex justify-between">
                      <span>Tempo Ativo:</span>
                      <span className="font-mono">{botStatus.uptime}</span>
                    </div>
                  )}

                  <div className="flex justify-between">
                    <span>Posições Abertas:</span>
                    <span className="font-bold">{botStatus.positions_count}</span>
                  </div>

                  <div className="flex justify-between">
                    <span>Modo:</span>
                    <Badge variant={botStatus.test_mode ? "secondary" : "destructive"}>
                      {botStatus.test_mode ? "Teste" : "Real"}
                    </Badge>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Controles Rápidos</CardTitle>
                  <CardDescription>Ações principais do bot</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Button
                    onClick={handleStartStop}
                    disabled={loading}
                    variant={botStatus.running ? "destructive" : "default"}
                    className="w-full"
                  >
                    {botStatus.running ? "Parar Bot" : "Iniciar Bot"}
                  </Button>

                  <Button variant="outline" className="w-full bg-transparent">
                    Fechar Todas Posições
                  </Button>

                  <Button variant="outline" className="w-full bg-transparent">
                    Recarregar Configurações
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="config">
            <ConfigPanel />
          </TabsContent>

          <TabsContent value="positions">
            <PositionsPanel />
          </TabsContent>

          <TabsContent value="logs">
            <LogsPanel />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
