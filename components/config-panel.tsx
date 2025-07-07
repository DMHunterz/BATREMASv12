"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Save, AlertTriangle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface Config {
  limit: number
  leverage: number
  risk_per_trade_percent: number
  max_risk_usdt_per_trade: number
  test_mode: boolean
  kline_interval_minutes: number
  kline_trend_period: number
  kline_pullback_period: number
  kline_atr_period: number
  min_atr_multiplier_for_entry: number
  max_symbols_to_monitor: number
  risk_reward_ratio: number
}

export function ConfigPanel() {
  const [config, setConfig] = useState<Config>({
    limit: 100,
    leverage: 15,
    risk_per_trade_percent: 0.5,
    max_risk_usdt_per_trade: 1.0,
    test_mode: true,
    kline_interval_minutes: 5,
    kline_trend_period: 50,
    kline_pullback_period: 10,
    kline_atr_period: 14,
    min_atr_multiplier_for_entry: 1.5,
    max_symbols_to_monitor: 5,
    risk_reward_ratio: 2.0,
  })

  const [loading, setLoading] = useState(false)
  const [configLoaded, setConfigLoaded] = useState(false)
  const { toast } = useToast()

  const fetchConfig = async () => {
    try {
      const response = await fetch("/api/config")
      const data = await response.json()
      // Ensure all values are defined with fallbacks
      setConfig({
        limit: data.limit ?? 100,
        leverage: data.leverage ?? 15,
        risk_per_trade_percent: data.risk_per_trade_percent ?? 0.5,
        max_risk_usdt_per_trade: data.max_risk_usdt_per_trade ?? 1.0,
        test_mode: data.test_mode ?? true,
        kline_interval_minutes: data.kline_interval_minutes ?? 5,
        kline_trend_period: data.kline_trend_period ?? 50,
        kline_pullback_period: data.kline_pullback_period ?? 10,
        kline_atr_period: data.kline_atr_period ?? 14,
        min_atr_multiplier_for_entry: data.min_atr_multiplier_for_entry ?? 1.5,
        max_symbols_to_monitor: data.max_symbols_to_monitor ?? 5,
        risk_reward_ratio: data.risk_reward_ratio ?? 2.0,
      })
      setConfigLoaded(true)
    } catch (error) {
      console.error("Erro ao carregar configurações:", error)
      setConfigLoaded(true) // Still set as loaded to show the form
    }
  }

  const saveConfig = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      })

      if (response.ok) {
        toast({
          title: "Configurações salvas",
          description: "As configurações foram atualizadas com sucesso.",
        })
      }
    } catch (error) {
      toast({
        title: "Erro",
        description: "Falha ao salvar configurações.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConfig()
  }, [])

  if (!configLoaded) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Carregando configurações...</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Configurações do Bot
          </CardTitle>
          <CardDescription>
            Configure os parâmetros de trading do bot. Mudanças requerem reinicialização.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Configurações de Risco */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Gerenciamento de Risco</h3>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="leverage">Alavancagem</Label>
                <Input
                  id="leverage"
                  type="number"
                  value={config.leverage.toString()}
                  onChange={(e) => setConfig({ ...config, leverage: Number(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="risk_percent">Risco por Trade (%)</Label>
                <Input
                  id="risk_percent"
                  type="number"
                  step="0.1"
                  value={config.risk_per_trade_percent.toString()}
                  onChange={(e) => setConfig({ ...config, risk_per_trade_percent: Number(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="max_risk">Risco Máximo (USDT)</Label>
                <Input
                  id="max_risk"
                  type="number"
                  step="0.1"
                  value={config.max_risk_usdt_per_trade.toString()}
                  onChange={(e) => setConfig({ ...config, max_risk_usdt_per_trade: Number(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="risk_reward">Risk/Reward Ratio</Label>
                <Input
                  id="risk_reward"
                  type="number"
                  step="0.1"
                  value={config.risk_reward_ratio.toString()}
                  onChange={(e) => setConfig({ ...config, risk_reward_ratio: Number(e.target.value) || 0 })}
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Configurações Técnicas */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Indicadores Técnicos</h3>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="kline_interval">Intervalo Kline (min)</Label>
                <Input
                  id="kline_interval"
                  type="number"
                  value={config.kline_interval_minutes.toString()}
                  onChange={(e) => setConfig({ ...config, kline_interval_minutes: Number(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="trend_period">Período EMA Tendência</Label>
                <Input
                  id="trend_period"
                  type="number"
                  value={config.kline_trend_period.toString()}
                  onChange={(e) => setConfig({ ...config, kline_trend_period: Number(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="pullback_period">Período EMA Pullback</Label>
                <Input
                  id="pullback_period"
                  type="number"
                  value={config.kline_pullback_period.toString()}
                  onChange={(e) => setConfig({ ...config, kline_pullback_period: Number(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="atr_period">Período ATR</Label>
                <Input
                  id="atr_period"
                  type="number"
                  value={config.kline_atr_period.toString()}
                  onChange={(e) => setConfig({ ...config, kline_atr_period: Number(e.target.value) || 0 })}
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Configurações Gerais */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Configurações Gerais</h3>

            <div className="flex items-center space-x-2">
              <Switch
                id="test_mode"
                checked={config.test_mode}
                onCheckedChange={(checked) => setConfig({ ...config, test_mode: checked })}
              />
              <Label htmlFor="test_mode">Modo Teste (Paper Trading)</Label>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="max_symbols">Máx. Símbolos Monitorados</Label>
                <Input
                  id="max_symbols"
                  type="number"
                  value={config.max_symbols_to_monitor.toString()}
                  onChange={(e) => setConfig({ ...config, max_symbols_to_monitor: Number(e.target.value) || 0 })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="atr_multiplier">Multiplicador ATR Mínimo</Label>
                <Input
                  id="atr_multiplier"
                  type="number"
                  step="0.1"
                  value={config.min_atr_multiplier_for_entry.toString()}
                  onChange={(e) => setConfig({ ...config, min_atr_multiplier_for_entry: Number(e.target.value) || 0 })}
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <Button onClick={saveConfig} disabled={loading}>
              <Save className="w-4 h-4 mr-2" />
              Salvar Configurações
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
