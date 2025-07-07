export async function GET() {
  try {
    const response = await fetch("http://localhost:8000/positions")
    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    return Response.json({ error: "Falha ao carregar posições" }, { status: 500 })
  }
}
