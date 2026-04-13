import { useEffect, useMemo, useState } from "react";
import { getDashboardGeoSummary, getRealtimeEventsFeed } from "../../api/api";

const severityClass = {
  high: "intel-severity-high",
  medium: "intel-severity-medium",
  low: "intel-severity-low",
};

export default function GlobalIntelligencePanel() {
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState([]);
  const [regions, setRegions] = useState([]);
  const [error, setError] = useState("");
  const [collapsed, setCollapsed] = useState(false);

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const [feedData, geoData] = await Promise.all([
        getRealtimeEventsFeed(8, "india"),
        getDashboardGeoSummary(40, "india"),
      ]);
      setEvents(feedData?.events || []);
      setRegions(geoData?.regions || []);
    } catch (err) {
      console.error("Failed to load global intelligence panel:", err);
      setError("Unable to load live intelligence feed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 60000);
    return () => clearInterval(interval);
  }, []);

  const topRegions = useMemo(() => regions.slice(0, 4), [regions]);

  return (
    <section className="intel-panel">
      <div className="intel-panel-header">
        <div>
          <h3>Global Intelligence</h3>
          <p>Realtime event feed and regional pulse</p>
        </div>
        <div className="intel-panel-controls">
          <button className="intel-action-btn" onClick={refresh} disabled={loading}>
            {loading ? "Syncing..." : "Refresh"}
          </button>
          <button
            className="intel-action-btn"
            onClick={() => setCollapsed((prev) => !prev)}
            aria-label="Toggle intelligence panel"
          >
            {collapsed ? "Expand" : "Collapse"}
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          {error ? <div className="intel-error">{error}</div> : null}

          <div className="intel-region-grid">
            {topRegions.length === 0 && !loading ? (
              <div className="intel-empty">No region activity available.</div>
            ) : (
              topRegions.map((region) => (
                <div className="intel-region-card" key={region.region}>
                  <div className="intel-region-name">{region.region}</div>
                  <div className="intel-region-events">{region.events} events</div>
                </div>
              ))
            )}
          </div>

          <div className="intel-events-list">
            {events.length === 0 && !loading ? (
              <div className="intel-empty">No live events available right now.</div>
            ) : (
              events.map((event) => (
                <a
                  key={event.event_id}
                  className="intel-event-item"
                  href={event.link || "#"}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  <div className="intel-event-head">
                    <span className={`intel-severity ${severityClass[event.severity] || "intel-severity-low"}`}>
                      {event.severity || "low"}
                    </span>
                    <span className="intel-event-region">{event.region || "Global"}</span>
                  </div>
                  <div className="intel-event-title">{event.title}</div>
                  {event.summary ? <div className="intel-event-summary">{event.summary}</div> : null}
                </a>
              ))
            )}
          </div>
        </>
      )}
    </section>
  );
}
