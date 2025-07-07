export async function POST(request: Request, { params }: { params: { symbol: string } }) {
  try {
    const response = await fetch(`http://localhost:8000/positions/${params.symbol}/close`, {
      method: "POST",
    })
    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    return Response.json({ error: "Falha ao fechar posição" }, { status: 500 })
  }
}
