"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Wifi, WifiOff } from "lucide-react"

export function KeepAlive() {
  const [isActive, setIsActive] = useState(false)
  const [lastPing, setLastPing] = useState<Date | null>(null)

  useEffect(() => {
    const pingServer = async () => {
      try {
        const response = await fetch("/api/health")
        if (response.ok) {
          setIsActive(true)
          setLastPing(new Date())
        } else {
          setIsActive(false)
        }
      } catch (error) {
        setIsActive(false)
        console.error("Keep-alive ping failed:", error)
      }
    }

    // Ping inicial
    pingServer()

    // Ping a cada 10 minutos (600000ms)
    const interval = setInterval(pingServer, 600000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center gap-2">
      <Badge variant={isActive ? "default" : "destructive"}>
        {isActive ? <Wifi className="w-3 h-3 mr-1" /> : <WifiOff className="w-3 h-3 mr-1" />}
        {isActive ? "Ativo" : "Inativo"}
      </Badge>
      {lastPing && <span className="text-xs text-gray-500">Último ping: {lastPing.toLocaleTimeString()}</span>}
    </div>
  )
}
