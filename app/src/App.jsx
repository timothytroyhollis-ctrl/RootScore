import { useState } from "react";


const API_BASE_URL = "http://localhost:8000";

const badgeClasses = {
  low: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  medium: "bg-amber-100 text-amber-800 ring-amber-200",
  high: "bg-orange-100 text-orange-800 ring-orange-200",
  critical: "bg-red-100 text-red-800 ring-red-200",
};

function parseSearchInput(value) {
  const trimmed = value.trim();
  const digitsOnly = trimmed.replace(/\D/g, "");

  if (digitsOnly.length === 11) {
    return { type: "tract", geoid: digitsOnly };
  }

  const cityStateMatch = trimmed.match(/^(.+?),\s*([A-Za-z]{2})$/);
  if (cityStateMatch) {
    return {
      type: "city",
      cityName: cityStateMatch[1].trim(),
      stateAbbr: cityStateMatch[2].toUpperCase(),
    };
  }

  return null;
}

function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatShapValue(value) {
  const numericValue = Number(value);
  const arrow = numericValue >= 0 ? "\u2191" : "\u2193";
  const tone = numericValue >= 0 ? "text-red-600" : "text-emerald-600";
  return {
    arrow,
    tone,
    text: `${arrow} ${Math.abs(numericValue).toFixed(3)}`,
  };
}

function ResultCard({ tract }) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
            Census Tract
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">{tract.GEOID}</h2>
        </div>

        <div className="flex flex-col items-start gap-3 sm:items-end">
          <span
            className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold capitalize ring-1 ${badgeClasses[tract.risk_tier] ?? badgeClasses.low}`}
          >
            {tract.risk_tier}
          </span>
          <div className="text-left sm:text-right">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
              Risk Score
            </p>
            <p className="mt-1 text-3xl font-bold text-slate-900">
              {formatPercent(tract.predicted_risk_score)}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <p className="text-sm font-semibold text-slate-900">Top driving factors</p>
        <ul className="mt-3 space-y-3">
          {tract.top_driving_factors?.map((factor) => {
            const shap = formatShapValue(factor.shap_value ?? 0);
            return (
              <li
                key={`${tract.GEOID}-${factor.feature}`}
                className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3"
              >
                <div>
                  <p className="font-medium text-slate-900">{factor.label}</p>
                  <p className="text-sm text-slate-500">
                    {Number(factor.shap_value) >= 0
                      ? "Associated with higher risk"
                      : "Associated with lower risk"}
                  </p>
                </div>
                <span className={`text-sm font-semibold ${shap.tone}`}>{shap.text}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </article>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searchContext, setSearchContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(event) {
    event.preventDefault();
    setError("");
    setResults([]);

    const parsed = parseSearchInput(query);
    if (!parsed) {
      setError("Enter either an 11-digit tract GEOID or a city search like Austin, TX.");
      return;
    }

    setLoading(true);

    try {
      if (parsed.type === "tract") {
        const response = await fetch(`${API_BASE_URL}/tract/${parsed.geoid}`);
        const payload = await response.json();

        if (!response.ok) {
          throw new Error(payload.detail || "Unable to load tract data.");
        }

        setResults([payload]);
        setSearchContext(`Showing RootScore for tract ${payload.GEOID}`);
      } else {
        const params = new URLSearchParams({ state_abbr: parsed.stateAbbr });
        const response = await fetch(
          `${API_BASE_URL}/city/${encodeURIComponent(parsed.cityName)}?${params.toString()}`
        );
        const payload = await response.json();

        if (!response.ok) {
          throw new Error(payload.detail || "Unable to load city data.");
        }

        setResults(payload.tracts || []);
        setSearchContext(
          `Showing ${payload.tract_count} tracts for ${payload.city_name}, ${payload.state_abbr}`
        );
      }
    } catch (searchError) {
      setError(searchError.message || "Something went wrong while searching.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(15,118,110,0.14),_transparent_38%),linear-gradient(180deg,_#f8fafc_0%,_#eef2ff_100%)] text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-12 sm:px-8 lg:px-10">
        <header className="rounded-[2rem] border border-white/70 bg-white/80 px-8 py-10 shadow-xl shadow-slate-200/50 backdrop-blur">
          <p className="text-sm font-semibold uppercase tracking-[0.32em] text-teal-700">
            RootScore
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
            Know before displacement happens.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
            Search by census tract GEOID or by city and state to surface eviction risk,
            neighborhood vulnerability, and the strongest drivers behind each score.
          </p>

          <form onSubmit={handleSearch} className="mt-8 flex flex-col gap-4 lg:flex-row">
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Enter tract GEOID or city, ST"
              className="h-14 flex-1 rounded-2xl border border-slate-200 bg-white px-5 text-base text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-teal-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-14 items-center justify-center rounded-2xl bg-slate-950 px-6 text-base font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {loading ? "Searching..." : "Search RootScore"}
            </button>
          </form>

          <p className="mt-3 text-sm text-slate-500">
            Examples: <span className="font-medium text-slate-700">17031010100</span> or{" "}
            <span className="font-medium text-slate-700">Austin, TX</span>
          </p>
        </header>

        <main className="mt-8">
          {error ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          {searchContext ? (
            <div className="mb-5 flex items-center justify-between">
              <p className="text-sm font-medium text-slate-600">{searchContext}</p>
              {results.length > 0 ? (
                <p className="text-sm text-slate-500">{results.length} result(s)</p>
              ) : null}
            </div>
          ) : null}

          {results.length > 0 ? (
            <div className="grid gap-5 lg:grid-cols-2">
              {results.map((tract) => (
                <ResultCard key={tract.GEOID} tract={tract} />
              ))}
            </div>
          ) : !loading ? (
            <section className="rounded-[2rem] border border-dashed border-slate-300 bg-white/60 px-8 py-16 text-center">
              <h2 className="text-xl font-semibold text-slate-900">Search a tract or city to begin</h2>
              <p className="mt-3 text-slate-600">
                RootScore returns tract-level eviction risk predictions with a transparent
                breakdown of the factors pushing risk up or down.
              </p>
            </section>
          ) : null}
        </main>
      </div>
    </div>
  );
}
