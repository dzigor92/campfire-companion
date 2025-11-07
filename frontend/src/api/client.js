const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health/`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error?.detail ?? "Unable to reach backend");
  }

  return response.json();
}
