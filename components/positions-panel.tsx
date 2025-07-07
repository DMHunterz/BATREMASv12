"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { RefreshCw, X } from "lucide-react"

interface Position {
  symbol: string
  side: string
  size: number
  entry_price: number
  current_price: number
  pnl: number
  pnl_percent: number
  status: string
}

export function PositionsPanel() {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(false)

  const fetchPositions = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/positions")
      const data = await response.json()
      setPositions(data.positions || [])
    } catch (error) {
      console.error("Erro ao carregar posições:", error)
    } finally {
      setLoading(false)
    }
  }

  const closePosition = async (symbol: string) => {
    try {
      const response = await fetch(`/api/positions/${symbol}/close`, {
        method: "POST",
      })

      if (response.ok) {
        await fetchPositions()
      }
    } catch (error) {
      console.error("Erro ao fechar posição:", error)
    }
  }

  useEffect(() => {
    fetchPositions()
    const interval = setInterval(fetchPositions, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Posições Abertas</CardTitle>
            <CardDescription>Monitore suas posições em tempo real</CardDescription>
          </div>

          <Button variant="outline" size="sm" onClick={fetchPositions} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Atualizar
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {positions.length === 0 ? (
          <div className="text-center py-8 text-slate-500">Nenhuma posição aberta</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Símbolo</TableHead>
                <TableHead>Lado</TableHead>
                <TableHead>Tamanho</TableHead>
                <TableHead>Preço Entrada</TableHead>
                <TableHead>Preço Atual</TableHead>
                <TableHead>PnL</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((position, index) => (
                <TableRow key={index}>
                  <TableCell className="font-medium">{position.symbol}</TableCell>
                  <TableCell>
                    <Badge variant={position.side === "LONG" ? "default" : "destructive"}>{position.side}</Badge>
                  </TableCell>
                  <TableCell>{position.size}</TableCell>
                  <TableCell>${position.entry_price.toFixed(4)}</TableCell>
                  <TableCell>${position.current_price.toFixed(4)}</TableCell>
                  <TableCell>
                    <span className={position.pnl >= 0 ? "text-green-600" : "text-red-600"}>
                      ${position.pnl.toFixed(2)} ({position.pnl_percent.toFixed(2)}%)
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{position.status}</Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm" onClick={() => closePosition(position.symbol)}>
                      <X className="w-4 h-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
