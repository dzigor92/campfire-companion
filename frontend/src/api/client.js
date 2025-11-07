const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function handleResponse(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error?.detail ?? "Request failed");
  }
  return response.json();
}

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health/`);
  return handleResponse(response);
}

export async function importCampfireEvent(eventReference) {
  const response = await fetch(`${API_BASE_URL}/campfire/events/import/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event: eventReference }),
  });
  return handleResponse(response);
}

export async function lookupCampfireClub({ id, url }) {
  const params = new URLSearchParams();
  if (id) params.set("id", id);
  if (url) params.set("url", url);
  const response = await fetch(
    `${API_BASE_URL}/campfire/clubs/lookup/?${params.toString()}`
  );
  return handleResponse(response);
}
