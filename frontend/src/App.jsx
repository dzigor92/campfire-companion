import { useEffect, useMemo, useState } from "react";
import "./App.css";
import {
  getHealth,
  importCampfireEvent,
  lookupCampfireClub,
} from "./api/client";

const features = [
  {
    title: "Check-In Insight",
    description: "Pull Campfire event rosters into your own database so ambassador teams can analyze attendance trends.",
  },
  {
    title: "Club Health",
    description: "Resolve Campfire deep links to confirm ownership, badge grants, and visibility before promoting them publicly.",
  },
  {
    title: "Ambassador Playbook",
    description: "Use the persisted data set to power raffles, rewards, and follow-ups tailored to your Pokémon GO community.",
  },
];

const highlights = [
  {
    label: "Stack",
    value: "Django API + React SPA",
  },
  {
    label: "Focus",
    value: "Pokémon GO Ambassador tooling",
  },
  {
    label: "Data",
    value: "Clubs + events cached from Campfire",
  },
];

function App() {
  const [health, setHealth] = useState({
    loading: true,
    message: "Checking backend...",
    error: null,
  });
  const [eventRef, setEventRef] = useState("");
  const [eventState, setEventState] = useState({
    loading: false,
    data: null,
    error: null,
  });
  const [clubLookup, setClubLookup] = useState({
    id: "",
    url: "",
  });
  const [clubState, setClubState] = useState({
    loading: false,
    data: null,
    error: null,
  });

  useEffect(() => {
    let isMounted = true;
    getHealth()
      .then((data) => {
        if (!isMounted) return;
        setHealth({
          loading: false,
          message: data?.status ?? "ok",
          error: null,
        });
      })
      .catch((error) => {
        if (!isMounted) return;
        setHealth({
          loading: false,
          message: error.message,
          error: true,
        });
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const statusChip = useMemo(() => {
    if (health.loading) return "Connecting...";
    return health.error ? "API offline" : "API online";
  }, [health]);

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Campfire Companion</p>
        <h1>
          Build the missing dashboard for Pokémon GO Community Ambassadors.
        </h1>
        <p className="lede">
          Campfire Companion connects directly to Niantic Campfire so you can import meetups,
          verify clubs, and surface the insights your local community needs without hopping
          between spreadsheets and discord bots.
        </p>
        <div className="cta-row">
          <button className="cta primary">Review Events</button>
          <button className="cta ghost">Sync a Club</button>
        </div>
      </header>

      <section className="status-card">
        <div className="status-chip" data-variant={health.error ? "error" : "success"}>
          {statusChip}
        </div>
        <p className="status-text">{health.message}</p>
        <p className="status-subtext">
          The frontend performs a fetch against <code>/api/health/</code> on load so
          you can confirm connectivity end-to-end.
        </p>
      </section>

      <section className="grid">
        {features.map((feature) => (
          <article className="card" key={feature.title}>
            <h3>{feature.title}</h3>
            <p>{feature.description}</p>
          </article>
        ))}
      </section>

      <section className="actions">
        <article className="form-card">
          <div>
            <p className="eyebrow">Event Import</p>
            <h3>Pull a Campfire meetup into the local store.</h3>
            <p className="lede small">
              Paste any Campfire meetup link or event ID from your Pokémon GO group.
              We hit the Django proxy (which in turn calls Campfire) and show what
              was persisted for ambassador reporting.
            </p>
          </div>
          <form
            className="form"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!eventRef.trim()) {
                setEventState((state) => ({
                  ...state,
                  error: "Please enter an event URL or ID.",
                }));
                return;
              }
              setEventState({ loading: true, data: null, error: null });
              try {
                const data = await importCampfireEvent(eventRef.trim());
                setEventState({ loading: false, data, error: null });
              } catch (error) {
                setEventState({
                  loading: false,
                  data: null,
                  error: error.message,
                });
              }
            }}
          >
            <label className="form-group">
              <span>Event URL or ID</span>
              <input
                type="text"
                placeholder="https://campfire.nianticlabs.com/discover/meetup/..."
                value={eventRef}
                onChange={(event) => setEventRef(event.target.value)}
              />
            </label>
            <button className="cta primary" type="submit" disabled={eventState.loading}>
              {eventState.loading ? "Importing..." : "Import Event"}
            </button>
            {eventState.error && (
              <p className="form-error">{eventState.error}</p>
            )}
          </form>
          {eventState.data && (
            <div className="result-card">
              <h4>{eventState.data.name}</h4>
              <p>
                <strong>Club:</strong> {eventState.data.club.name}
              </p>
              <p>
                <strong>Attendees:</strong>{" "}
                {eventState.data.checked_in_members_count}/
                {eventState.data.members_total}
              </p>
              <div className="pill-list">
                {(eventState.data.badge_grants ?? []).map((badge) => (
                  <span className="pill" key={badge}>
                    {badge}
                  </span>
                ))}
              </div>
              <div className="rsvp-list">
                {(eventState.data.rsvps ?? []).slice(0, 4).map((rsvp) => (
                  <div className="rsvp-item" key={rsvp.member.id}>
                    <p className="rsvp-name">
                      {rsvp.member.display_name || rsvp.member.username || "Unknown"}
                    </p>
                    <span className="pill muted">{rsvp.status}</span>
                  </div>
                ))}
                {eventState.data.rsvps?.length > 4 && (
                  <p className="hint">
                    +{eventState.data.rsvps.length - 4} more RSVPs stored in the DB
                  </p>
                )}
              </div>
            </div>
          )}
        </article>

        <article className="form-card">
          <div>
            <p className="eyebrow">Club Lookup</p>
            <h3>Resolve a club deep-link and cache it locally.</h3>
            <p className="lede small">
              Provide either the campfire.onelink deep link or a club ID to confirm
              who owns the space, what badges/visibility it has, and whether it
              should be surfaced to your trainers.
            </p>
          </div>
          <form
            className="form"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!clubLookup.id.trim() && !clubLookup.url.trim()) {
                setClubState((state) => ({
                  ...state,
                  error: "Enter a club ID or URL.",
                }));
                return;
              }
              setClubState({ loading: true, data: null, error: null });
              try {
                const data = await lookupCampfireClub({
                  id: clubLookup.id.trim() || undefined,
                  url: clubLookup.url.trim() || undefined,
                });
                setClubState({ loading: false, data, error: null });
              } catch (error) {
                setClubState({ loading: false, data: null, error: error.message });
              }
            }}
          >
            <label className="form-group">
              <span>Club ID</span>
              <input
                type="text"
                value={clubLookup.id}
                onChange={(event) =>
                  setClubLookup((prev) => ({ ...prev, id: event.target.value }))
                }
                placeholder="b632fc8e-0b41-49de-ade2-21b0cd81db69"
              />
            </label>
            <label className="form-group">
              <span>Club URL</span>
              <input
                type="text"
                value={clubLookup.url}
                onChange={(event) =>
                  setClubLookup((prev) => ({ ...prev, url: event.target.value }))
                }
                placeholder="https://campfire.onelink.me/eBr8?..."
              />
            </label>
            <button className="cta primary" type="submit" disabled={clubState.loading}>
              {clubState.loading ? "Resolving..." : "Lookup Club"}
            </button>
            {clubState.error && <p className="form-error">{clubState.error}</p>}
          </form>
          {clubState.data && (
            <div className="result-card">
              <h4>{clubState.data.name}</h4>
              <p>
                <strong>Game:</strong> {clubState.data.game || "Unknown"}
              </p>
              <p>
                <strong>Visibility:</strong> {clubState.data.visibility}
              </p>
              <div className="pill-list">
                {(clubState.data.badge_grants ?? []).map((badge) => (
                  <span className="pill" key={badge}>
                    {badge}
                  </span>
                ))}
              </div>
              {clubState.data.creator && (
                <p className="hint">
                  Creator:{" "}
                  {clubState.data.creator.display_name ||
                    clubState.data.creator.username ||
                    clubState.data.creator.id}
                </p>
              )}
            </div>
          )}
        </article>
      </section>

      <section className="highlights">
        {highlights.map((item) => (
          <div className="highlight" key={item.label}>
            <p className="highlight-label">{item.label}</p>
            <p className="highlight-value">{item.value}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

export default App;
