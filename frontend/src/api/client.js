const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

let authToken = null;

function withAuth(headers = {}) {
  if (authToken) {
    return { ...headers, Authorization: `Token ${authToken}` };
  }
  return headers;
}

async function handleResponse(response) {
  if (!response.ok) {
    let errorPayload = {};
    try {
      errorPayload = await response.json();
    } catch (_err) {
      // ignore non-JSON errors
    }
    throw new Error(errorPayload?.detail ?? "Request failed");
  }

  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  if (!text) {
    return null;
  }
  return JSON.parse(text);
}

export function setAuthToken(token) {
  authToken = token;
}

export function clearAuthToken() {
  authToken = null;
}

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health/`);
  return handleResponse(response);
}

export async function importCampfireEvent(eventReference) {
  const response = await fetch(`${API_BASE_URL}/campfire/events/import/`, {
    method: "POST",
    headers: withAuth({ "Content-Type": "application/json" }),
    body: JSON.stringify({ event: eventReference }),
  });
  return handleResponse(response);
}

export async function storeCampfireToken(token) {
  const response = await fetch(`${API_BASE_URL}/campfire/tokens/`, {
    method: "POST",
    headers: withAuth({ "Content-Type": "application/json" }),
    body: JSON.stringify({ token }),
  });
  return handleResponse(response);
}

export async function importCampfireClubHistory(clubReference) {
  const response = await fetch(
    `${API_BASE_URL}/campfire/clubs/import-history/`,
    {
      method: "POST",
      headers: withAuth({ "Content-Type": "application/json" }),
      body: JSON.stringify({ club: clubReference }),
    }
  );
  return handleResponse(response);
}

export async function lookupCampfireClub({ query, id, url }) {
  const params = new URLSearchParams();
  if (query) {
    params.set("club", query);
  } else {
    if (id) params.set("id", id);
    if (url) params.set("url", url);
  }

  const qs = params.toString();
  const target = qs
    ? `${API_BASE_URL}/campfire/clubs/lookup/?${qs}`
    : `${API_BASE_URL}/campfire/clubs/lookup/`;
  const response = await fetch(target, {
    headers: withAuth(),
  });
  return handleResponse(response);
}

export async function registerUser(username, password) {
  const response = await fetch(`${API_BASE_URL}/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  return handleResponse(response);
}

export async function loginUser(username, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  return handleResponse(response);
}

export async function logoutUser() {
  const response = await fetch(`${API_BASE_URL}/auth/logout/`, {
    method: "POST",
    headers: withAuth({ "Content-Type": "application/json" }),
  });
  return handleResponse(response);
}

export async function linkCampfireAccount({ memberId, username }) {
  const response = await fetch(`${API_BASE_URL}/auth/campfire/`, {
    method: "POST",
    headers: withAuth({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      campfire_member_id: memberId,
      campfire_username: username,
    }),
  });
  return handleResponse(response);
}

export async function unlinkCampfireAccount() {
  const response = await fetch(`${API_BASE_URL}/auth/campfire/`, {
    method: "DELETE",
    headers: withAuth({ "Content-Type": "application/json" }),
  });
  return handleResponse(response);
}
