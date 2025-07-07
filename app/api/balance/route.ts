export async function GET() {
  try {
    const response = await fetch("http://localhost:8000/balance")
    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    // Retorna dados simulados se o backend não estiver disponível
    const mockBalance = {
      total_balance: 1000.0,
      available_balance: 850.0,
      used_balance: 150.0,
      unrealized_pnl: 25.5,
      total_wallet_balance: 1025.5,
      currency: "USDT",
    }
    return Response.json(mockBalance)
  }
}
