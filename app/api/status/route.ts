export async function GET() {
  try {
    const response = await fetch("http://localhost:8000/status")
    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    return Response.json({ error: "Falha ao conectar com o backend" }, { status: 500 })
  }
}
