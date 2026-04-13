import { useEffect, useMemo, useState } from "react";
import {
  getDashboardGeoSummary,
  getPlatformStatus,
  getRealtimeEventsFeed,
  getWorldMonitorConfig,
} from "../../api/api";

const severityClass = {
  high: "dash-severity-high",
  medium: "dash-severity-medium",
  low: "dash-severity-low",
};

const projectPoint = (lat, lon) => {
  const x = ((lon + 180) / 360) * 100;
  const y = ((90 - lat) / 180) * 100;
  return { x, y };
};

export default function GlobalDashboard() {
  const [events, setEvents] = useState([]);
  const [regions, setRegions] = useState([]);
  const [platform, setPlatform] = useState(null);
  const [worldMonitor, setWorldMonitor] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [regionFilter, setRegionFilter] = useState("all");
  const [search, setSearch] = useState("");

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const [feedData, geoData] = await Promise.all([
        getRealtimeEventsFeed(25, "india"),
        getDashboardGeoSummary(120, "india"),
      ]);
      setEvents(feedData?.events || []);
      setRegions(geoData?.regions || []);
      try {
        const platformStatus = await getPlatformStatus();
        setPlatform(platformStatus?.platform || null);
      } catch (statusErr) {
        console.warn("Platform status unavailable:", statusErr);
      }

      try {
        const worldMonitorConfig = await getWorldMonitorConfig();
        setWorldMonitor(worldMonitorConfig?.world_monitor || null);
      } catch (wmErr) {
        console.warn("World Monitor config unavailable:", wmErr);
      }
    } catch (err) {
      console.error("Failed to load global dashboard:", err);
      setError("Unable to load realtime intelligence.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 45000);
    return () => clearInterval(timer);
  }, []);

  const markers = useMemo(() => {
    return regions.slice(0, 12).map((region) => {
      const point = projectPoint(region.lat ?? 0, region.lon ?? 0);
      return {
        ...region,
        ...point,
        size: Math.max(8, Math.min(28, (region.events || 1) * 2.2)),
      };
    });
  }, [regions]);

  const availableRegions = useMemo(() => {
    const unique = new Set(events.map((event) => event.region || "Global"));
    return ["all", ...Array.from(unique)];
  }, [events]);

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const matchesSeverity = severityFilter === "all" || (event.severity || "low") === severityFilter;
      const matchesRegion = regionFilter === "all" || (event.region || "Global") === regionFilter;
      const haystack = `${event.title || ""} ${event.summary || ""}`.toLowerCase();
      const matchesSearch = !search.trim() || haystack.includes(search.trim().toLowerCase());
      return matchesSeverity && matchesRegion && matchesSearch;
    });
  }, [events, severityFilter, regionFilter, search]);

  const kpis = useMemo(() => {
    const high = events.filter((e) => (e.severity || "low") === "high").length;
    const medium = events.filter((e) => (e.severity || "low") === "medium").length;
    const activeRegions = new Set(events.map((e) => e.region || "Global")).size;
    return {
      total: events.length,
      high,
      medium,
      activeRegions,
    };
  }, [events]);

  return (
    <div className="dashboard-root">
      <div className="dashboard-topbar">
        <div>
          <h2>World Monitor Dashboard</h2>
          <p>India-first intelligence pulse with global context</p>
        </div>
        <button className="dashboard-refresh" onClick={refresh} disabled={loading}>
          {loading ? "Syncing..." : "Refresh Feed"}
        </button>
      </div>

      <div className="dashboard-kpis">
        <div className="dashboard-kpi-card"><span>Total Events</span><strong>{kpis.total}</strong></div>
        <div className="dashboard-kpi-card"><span>High Severity</span><strong>{kpis.high}</strong></div>
        <div className="dashboard-kpi-card"><span>Medium Severity</span><strong>{kpis.medium}</strong></div>
        <div className="dashboard-kpi-card"><span>Active Regions</span><strong>{kpis.activeRegions}</strong></div>
      </div>

      {platform ? (
        <div className="dashboard-platform-status">
          <span>Model: {platform.model}</span>
          <span>RAG: {platform.rag_enabled ? `on (${platform.rag_documents} docs)` : "off"}</span>
          <span>Scheduler: {platform.scheduler_running ? "running" : "stopped"}</span>
          <span>Cache hit: {Number(platform.cache_hit_rate_percent || 0).toFixed(1)}%</span>
        </div>
      ) : null}

      {error ? <div className="dashboard-error">{error}</div> : null}

      <div className="dashboard-filters">
        <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
          <option value="all">All severities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)}>
          {availableRegions.map((region) => (
            <option key={region} value={region}>
              {region === "all" ? "All regions" : region}
            </option>
          ))}
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search events"
        />
      </div>

      <div className="dashboard-grid">
        <section className="dashboard-map-card">
          <h3>Geo Activity Map</h3>
          <div className="dashboard-map-surface">
            {markers.map((marker) => (
              <div
                key={marker.region}
                className="dashboard-map-marker"
                style={{
                  left: `${marker.x}%`,
                  top: `${marker.y}%`,
                  width: `${marker.size}px`,
                  height: `${marker.size}px`,
                }}
                title={`${marker.region}: ${marker.events} events`}
              />
            ))}
          </div>
          <div className="dashboard-map-legend">
            {regions.slice(0, 6).map((region) => (
              <div className="dashboard-legend-item" key={region.region}>
                <span>{region.region}</span>
                <strong>{region.events}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="dashboard-feed-card">
          <h3>Live Event Feed</h3>
          <div className="dashboard-feed-list">
            {filteredEvents.length === 0 && !loading ? (
              <div className="dashboard-empty">No events available right now.</div>
            ) : (
              filteredEvents.map((event) => (
                <a
                  key={event.event_id}
                  className="dashboard-feed-item"
                  href={event.link || "#"}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  <div className="dashboard-feed-head">
                    <span className={`dashboard-severity ${severityClass[event.severity] || "dash-severity-low"}`}>
                      {event.severity || "low"}
                    </span>
                    <span className="dashboard-feed-region">{event.region || "Global"}</span>
                  </div>
                  <div className="dashboard-feed-title">{event.title}</div>
                  {event.summary ? <div className="dashboard-feed-summary">{event.summary}</div> : null}
                </a>
              ))
            )}
          </div>
        </section>

        <section className="dashboard-world-monitor-card">
          <h3>World Monitor Integration</h3>
          <p>
            Live strategic dashboard from worldmonitor.app integrated as an external
            launch because iframe embedding is restricted by the site security policy.
          </p>
          {worldMonitor ? (
            <div className="dashboard-world-monitor-meta">
              <span>Mode: {worldMonitor.integration_mode}</span>
              <span>Embeddable: {worldMonitor.embeddable ? "yes" : "no"}</span>
            </div>
          ) : null}
          <button
            className="dashboard-world-monitor-btn"
            onClick={() => window.open(worldMonitor?.url || "https://www.worldmonitor.app/", "_blank", "noopener,noreferrer")}
          >
            Open World Monitor
          </button>
        </section>
      </div>
    </div>
  );
}
