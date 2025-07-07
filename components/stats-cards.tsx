"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, DollarSign, Activity, Clock, Wallet } from "lucide-react"

interface BotStatus {
  running: boolean
  start_time?: string
  uptime?: string
  positions_count: number
  test_mode: boolean
}

interface BalanceData {
  total_balance: number
  available_balance: number
  used_balance: number
  unrealized_pnl: number
  total_wallet_balance: number
  currency: string
}

interface StatsCardsProps {
  botStatus: BotStatus
}

export function StatsCards({ botStatus }: StatsCardsProps) {
  const [balance, setBalance] = useState<BalanceData | null>(null)

  const fetchBalance = async () => {
    try {
      const response = await fetch("/api/balance")
      const data = await response.json()
      setBalance(data)
    } catch (error) {
      console.error("Erro ao carregar saldo:", error)
    }
  }

  useEffect(() => {
    fetchBalance()
    const interval = setInterval(fetchBalance, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Status</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{botStatus.running ? "Ativo" : "Parado"}</div>
          <p className="text-xs text-muted-foreground">{botStatus.test_mode ? "Modo Teste" : "Modo Real"}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Saldo Total</CardTitle>
          <Wallet className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">${balance ? balance.total_wallet_balance.toFixed(2) : "0.00"}</div>
          <p className="text-xs text-muted-foreground">
            Disponível: ${balance ? balance.available_balance.toFixed(2) : "0.00"}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tempo Ativo</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{botStatus.uptime || "0h 0m"}</div>
          <p className="text-xs text-muted-foreground">Desde o último início</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Posições</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{botStatus.positions_count}</div>
          <p className="text-xs text-muted-foreground">Posições abertas</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">PnL Não Realizado</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div
            className={`text-2xl font-bold ${balance && balance.unrealized_pnl >= 0 ? "text-green-600" : "text-red-600"}`}
          >
            {balance ? (balance.unrealized_pnl >= 0 ? "+" : "") + "$" + balance.unrealized_pnl.toFixed(2) : "$0.00"}
          </div>
          <p className="text-xs text-muted-foreground">Lucro/Prejuízo atual</p>
        </CardContent>
      </Card>
    </div>
  )
}
