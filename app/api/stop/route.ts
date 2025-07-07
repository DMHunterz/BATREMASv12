export async function POST() {
  try {
    const response = await fetch("http://localhost:8000/stop", {
      method: "POST",
    })
    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    return Response.json({ error: "Falha ao parar bot" }, { status: 500 })
  }
}
