"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Wallet, RefreshCw, TrendingUp, TrendingDown, AlertTriangle, CheckCircle } from "lucide-react"

interface BalanceData {
  total_balance: number
  available_balance: number
  used_balance: number
  unrealized_pnl: number
  total_wallet_balance: number
  currency: string
  margin_ratio?: number
}

export function BalanceCard() {
  const [balance, setBalance] = useState<BalanceData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  const fetchBalance = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("/api/balance")
      if (!response.ok) {
        throw new Error(`Erro ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      setBalance(data)
      setLastUpdate(new Date())
    } catch (error: any) {
      console.error("Erro ao carregar saldo:", error)
      setError(error.message || "Erro ao carregar saldo")
    } finally {
      setLoading(false)
    }
  }

  const testConnection = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/test-connection", { method: "POST" })
      const data = await response.json()

      if (data.status === "success") {
        setBalance(data.balance)
        setError(null)
        setLastUpdate(new Date())
      } else {
        setError(data.message)
      }
    } catch (error: any) {
      setError("Erro ao testar conexão")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBalance()
    const interval = setInterval(fetchBalance, 10000) // Atualiza a cada 10 segundos
    return () => clearInterval(interval)
  }, [])

  const getMarginStatus = () => {
    if (!balance || !balance.margin_ratio) return { status: "unknown", color: "gray" }

    if (balance.margin_ratio < 50) return { status: "safe", color: "green" }
    if (balance.margin_ratio < 80) return { status: "warning", color: "yellow" }
    return { status: "danger", color: "red" }
  }

  const marginStatus = getMarginStatus()

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="w-5 h-5" />
            Saldo da Conta
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <div className="flex gap-2 mt-4">
            <Button variant="outline" size="sm" onClick={fetchBalance} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Tentar Novamente
            </Button>
            <Button variant="outline" size="sm" onClick={testConnection} disabled={loading}>
              <CheckCircle className="w-4 h-4 mr-2" />
              Testar Conexão
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!balance) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="w-5 h-5" />
            Saldo da Conta
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
              <p className="text-sm text-gray-500">Carregando saldo...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Wallet className="w-5 h-5" />
            Saldo da Conta
          </CardTitle>
          <div className="flex items-center gap-2">
            {lastUpdate && <span className="text-xs text-gray-500">{lastUpdate.toLocaleTimeString()}</span>}
            <Button variant="outline" size="sm" onClick={fetchBalance} disabled={loading}>
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Saldo Total */}
        <div className="text-center p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg">
          <p className="text-sm text-gray-600 mb-1">Saldo Total da Carteira</p>
          <p className="text-3xl font-bold text-gray-900">${balance.total_wallet_balance.toFixed(2)}</p>
          <p className="text-xs text-gray-500">{balance.currency}</p>
        </div>

        {/* Detalhes do Saldo */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Disponível:</span>
              <span className="font-semibold text-green-600">${balance.available_balance.toFixed(2)}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Em Uso:</span>
              <span className="font-semibold text-orange-600">${balance.used_balance.toFixed(2)}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-sm text-gray-600">PnL Não Realizado:</span>
              <div className="flex items-center gap-1">
                {balance.unrealized_pnl >= 0 ? (
                  <TrendingUp className="w-3 h-3 text-green-500" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-red-500" />
                )}
                <span className={`font-semibold ${balance.unrealized_pnl >= 0 ? "text-green-600" : "text-red-600"}`}>
                  ${balance.unrealized_pnl.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Margem Livre</p>
              <p className="text-lg font-bold text-gray-900">
                {balance.total_balance > 0
                  ? ((balance.available_balance / balance.total_balance) * 100).toFixed(1)
                  : "0.0"}
                %
              </p>
            </div>

            {balance.margin_ratio !== undefined && (
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500 mb-1">Ratio de Margem</p>
                <p
                  className={`text-sm font-bold ${
                    marginStatus.color === "green"
                      ? "text-green-600"
                      : marginStatus.color === "yellow"
                        ? "text-yellow-600"
                        : "text-red-600"
                  }`}
                >
                  {balance.margin_ratio.toFixed(2)}%
                </p>
              </div>
            )}

            <Badge
              variant={balance.available_balance > balance.used_balance ? "default" : "destructive"}
              className="w-full justify-center"
            >
              {marginStatus.status === "safe"
                ? "Saudável"
                : marginStatus.status === "warning"
                  ? "Atenção"
                  : marginStatus.status === "danger"
                    ? "Alto Risco"
                    : "Normal"}
            </Badge>
          </div>
        </div>

        {/* Barra de Progresso do Saldo */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-gray-500">
            <span>Utilização do Saldo</span>
            <span>
              {balance.total_balance > 0 ? ((balance.used_balance / balance.total_balance) * 100).toFixed(1) : "0"}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                balance.used_balance / balance.total_balance < 0.5
                  ? "bg-green-500"
                  : balance.used_balance / balance.total_balance < 0.8
                    ? "bg-yellow-500"
                    : "bg-red-500"
              }`}
              style={{
                width: `${balance.total_balance > 0 ? Math.min((balance.used_balance / balance.total_balance) * 100, 100) : 0}%`,
              }}
            ></div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
