export async function POST() {
  try {
    const response = await fetch("http://localhost:8000/start", {
      method: "POST",
    })
    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    return Response.json({ error: "Falha ao iniciar bot" }, { status: 500 })
  }
}
