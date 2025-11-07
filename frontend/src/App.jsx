import { useEffect, useMemo, useState } from "react";
import "./App.css";
import { getHealth } from "./api/client";

const features = [
  {
    title: "Route Planning",
    description: "Map outings, milestones, and logistics with collaborative timelines.",
  },
  {
    title: "Gear Coordination",
    description: "Share packing lists, assign owners, and track outstanding needs.",
  },
  {
    title: "Knowledge Base",
    description: "Capture camp recipes, survival tips, and location notes for the next trip.",
  },
];

const highlights = [
  {
    label: "Stack",
    value: "Django API + React SPA",
  },
  {
    label: "API Ready",
    value: "/api/health/ endpoint wired up",
  },
  {
    label: "Styling",
    value: "Vanilla CSS with utility tokens",
  },
];

function App() {
  const [health, setHealth] = useState({
    loading: true,
    message: "Checking backend...",
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
          Plan, organize, and share trips with a modern React + Django stack.
        </h1>
        <p className="lede">
          This starter pairs a Django REST API with a Vite-powered React frontend,
          giving you everything you need to start modeling itineraries, collecting
          field data, and building the collaborative tools adventurers rely on.
        </p>
        <div className="cta-row">
          <button className="cta primary">View Trips</button>
          <button className="cta ghost">Create Workspace</button>
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
