export async function POST() {
  try {
    const response = await fetch("http://localhost:8000/test-connection", {
      method: "POST",
    })
    const data = await response.json()
    return Response.json(data)
  } catch (error) {
    return Response.json(
      {
        status: "error",
        message: "Falha ao conectar com o backend",
      },
      { status: 500 },
    )
  }
}
