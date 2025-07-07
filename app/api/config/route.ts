export async function GET() {
  try {
    const response = await fetch("http://localhost:8000/config")
    const data = await response.json()

    // Ensure all required fields exist with defaults
    const config = {
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
    }

    return Response.json(config)
  } catch (error) {
    // Return default config if backend is not available
    const defaultConfig = {
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
    }
    return Response.json(defaultConfig)
  }
}

export async function POST(request: Request) {
  try {
    const config = await request.json()
    const response = await fetch("http://localhost:8000/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    })
    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    return Response.json({ error: "Falha ao salvar configurações" }, { status: 500 })
  }
}
