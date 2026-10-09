/** React coordinates the workflows; Python owns every analytical definition. */
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, setCsrfToken } from "./api";
import AuthScreen from "./components/AuthScreen";
import "./styles.css";
const num = (v) =>
  v == null
    ? "Unavailable"
    : Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 });
const pct = (v) => (v == null ? "—" : (v * 100).toFixed(1) + "%");
// Date inputs represent local calendar days, so avoid UTC conversion near midnight.
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
function Field({ label, children }) {
  return (
    <label>
      {label}
      {children}
    </label>
  );
}
function Cohorts({ rows }) {
  return (
    <div className="table-wrap">
      <table className="cohort">
        <thead>
          <tr>
            <th>First purchase</th>
            <th>Buyers</th>
            {rows[0]?.cells.map((x) => (
              <th key={x.month}>M{x.month}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.cohort}>
              <td>{row.cohort}</td>
              <td>{row.customers}</td>
              {row.cells.map((c) => (
                <td
                  key={c.month}
                  title={`${c.period}: ${c.active_customers ?? "unavailable"} buyers (${c.state})`}
                  style={{
                    background:
                      c.rate == null
                        ? "#f1f5f9"
                        : `rgba(7,140,128,${0.08 + c.rate * 0.65})`,
                    color: c.rate > 0.6 ? "#fff" : "#16354d",
                  }}
                >
                  {pct(c.rate)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function App() {
  const [user, U] = useState(null),
    [busy, B] = useState(false),
    [error, E] = useState(""),
    [message, M] = useState(""),
    [tab, T] = useState("Overview"),
    [stores, S] = useState([]),
    [selected, P] = useState(""),
    [datasets, D] = useState([]),
    [dataset, K] = useState(""),
    [analyses, A] = useState([]),
    [result, R] = useState(null),
    [preview, V] = useState(null),
    [source, O] = useState("Store order export"),
    [coverage, CV] = useState(today()),
    [asof, AS] = useState(today()),
    [inactivity, IN] = useState(90),
    [horizon, H] = useState(6),
    [scenario, N] = useState("Retention review"),
    [search, Q] = useState(""),
    [segment, F] = useState("All segments"),
    [checked, C] = useState([]),
    [comparison, J] = useState(null);
  async function task(fn) {
    B(true);
    E("");
    M("");
    try {
      await fn();
    } catch (e) {
      E(e.message);
    } finally {
      B(false);
    }
  }
  const write = (path, body) =>
    api("/v1" + path, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  async function load() {
    const [s, a] = await Promise.all([api("/v1/stores"), api("/v1/analyses")]);
    S(s);
    A(a);
    P((old) => old || s[0]?.id || "");
  }
  useEffect(() => {
    api("/auth/session")
      .then(async (s) => {
        U(s.user);
        setCsrfToken(s.csrf_token);
        await load();
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!selected) {
      D([]);
      K("");
      return;
    }
    let active = true;
    api("/v1/stores/" + selected + "/datasets")
      .then((d) => {
        if (active) {
          D(d);
          K(d[0]?.id || "");
          if (d[0]) AS(d[0].coverage_end);
        }
      })
      .catch((e) => {
        if (active) E(e.message);
      });
    return () => {
      active = false;
    };
  }, [selected]);
  async function auth(registering, body) {
    await task(async () => {
      const s = await api("/auth/" + (registering ? "register" : "login"), {
        method: "POST",
        body: JSON.stringify(body),
      });
      U(s.user);
      setCsrfToken(s.csrf_token);
      await load();
    });
  }
  async function run() {
    await task(async () => {
      const a = await write("/stores/" + selected + "/analyses", {
        dataset_id: dataset,
        scenario_name: scenario,
        as_of: asof,
        inactivity_days: Number(inactivity),
        cohort_horizon: Number(horizon),
      });
      R(a);
      await load();
      T("Overview");
    });
  }
  const current = datasets.find((x) => x.id === dataset),
    activeStore = stores.find((x) => x.id === selected),
    stats = result?.results.summary,
    currency = result?.inputs.store.currency || activeStore?.currency;
  if (!user) return <AuthScreen onSubmit={auth} busy={busy} error={error} />;
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <span>◈</span>
          <div>
            RetentionIQ<small>Customer retention analytics</small>
          </div>
        </div>
        <nav>
          {[
            "Overview",
            "Order data",
            "Analysis setup",
            "Customer segments",
            "Cohort retention",
            "Reports & comparisons",
          ].map((t) => (
            <button
              key={t}
              className={tab === t ? "active" : ""}
              onClick={() => T(t)}
            >
              {t}
            </button>
          ))}
        </nav>
        <div className="account">
          <small>{user.email}</small>
          <button
            onClick={() =>
              task(async () => {
                await api("/auth/logout", { method: "POST" });
                U(null);
                setCsrfToken("");
              })
            }
          >
            Sign out
          </button>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">
              CUSTOMER INTELLIGENCE / {tab.toUpperCase()}
            </p>
            <h1>
              {tab === "Overview"
                ? "Understand who returns and who needs attention"
                : tab}
            </h1>
            <p className="muted">
              Purchase cohorts, transparent segments and a clear view of
              customer activity.
            </p>
          </div>
          <Field label="Active store">
            <select
              aria-label="Active store"
              value={selected}
              onChange={(e) => P(e.target.value)}
            >
              <option value="">Select a store</option>
              {stores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.currency}
                </option>
              ))}
            </select>
          </Field>
        </header>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {message && (
          <p className="success" role="status">
            {message}
          </p>
        )}
        {busy && (
          <p role="status" className="muted">
            Calculating or saving…
          </p>
        )}
        {tab === "Overview" && (
          <>
            <section className="card">
              <div className="section-head">
                <div>
                  <h2>Customer relationship outlook</h2>
                  <p className="muted">
                    {activeStore?.name || "Create a store"} ·{" "}
                    {result
                      ? `Saved analysis as of ${result.inputs.as_of}`
                      : "Start with order history"}
                  </p>
                </div>
                <div className="controls">
                  {!stores.length ? (
                    <button
                      disabled={busy}
                      onClick={() =>
                        task(async () => {
                          const d = await write("/demo");
                          await load();
                          P(d.store_id);
                          M(d.message);
                        })
                      }
                    >
                      Load demo data
                    </button>
                  ) : (
                    <button disabled={busy || !dataset} onClick={run}>
                      Analyze customer retention
                    </button>
                  )}
                  <button
                    className="text-button"
                    onClick={() => T("Analysis setup")}
                  >
                    Edit assumptions
                  </button>
                </div>
              </div>
            </section>
            {result ? (
              <>
                <div className="metrics">
                  {[
                    ["Purchasing customers", num(stats.customers)],
                    ["Repeat-purchase rate", pct(stats.repeat_purchase_rate)],
                    ["Inactive customers", num(stats.inactive_customers)],
                    [
                      "Completed order revenue",
                      `${currency} ${num(stats.revenue)}`,
                    ],
                  ].map(([k, v]) => (
                    <div className="metric" key={k}>
                      <small>{k}</small>
                      <strong>{v}</strong>
                    </div>
                  ))}
                </div>
                <section className="card">
                  <div className="section-head">
                    <div>
                      <h2>Purchase retention by acquisition cohort</h2>
                      <p className="muted">
                        First observed purchase · M0 baseline · exact-month
                        repeat activity
                      </p>
                    </div>
                    <span className="pill">
                      {result.inputs.cohort_horizon} follow-up months
                    </span>
                  </div>
                  <Cohorts rows={result.results.cohorts} />
                  <p className="muted">
                    Blank cells are open or future follow-up months. Completed
                    months with no returning buyers show 0%.
                  </p>
                </section>
                <div className="grid two">
                  <section className="card">
                    <h2>Customer segments</h2>
                    {result.results.segments.map((x) => (
                      <div className="segment-row" key={x.segment}>
                        <span>{x.segment}</span>
                        <div className="segment-track">
                          <i
                            style={{
                              width: `${(x.customers / Math.max(1, stats.customers)) * 100}%`,
                            }}
                          />
                        </div>
                        <b>{x.customers}</b>
                      </div>
                    ))}
                  </section>
                  <section className="card">
                    <h2>What this analysis means</h2>
                    <p>
                      {stats.completed_orders} completed orders ·{" "}
                      {stats.repeat_buyers} buyers with at least two orders
                    </p>
                    <p>
                      Inactivity threshold:{" "}
                      <b>more than {result.inputs.inactivity_days} days</b>
                    </p>
                    <p>
                      Average order value:{" "}
                      <b>
                        {currency} {num(stats.average_order_value)}
                      </b>
                    </p>
                    <p className="muted">
                      Segments describe observed purchases. They do not estimate
                      churn probability or future lifetime value.
                    </p>
                  </section>
                </div>
                <section className="card">
                  <h2>Interpretation notes</h2>
                  {[
                    ...result.inputs.quality.warnings,
                    ...result.results.warnings,
                  ].map((w, i) => (
                    <p key={i} className="muted">
                      {w}
                    </p>
                  ))}
                </section>
              </>
            ) : (
              <section className="card empty">
                <h2>Start with customers and their orders</h2>
                <p>
                  Import order history or load synthetic demonstration records,
                  then save your first retention review.
                </p>
              </section>
            )}
          </>
        )}
        {tab === "Order data" && (
          <>
            <section className="card">
              <h2>Create a store</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = e.currentTarget,
                    body = Object.fromEntries(new FormData(form));
                  task(async () => {
                    const s = await write("/stores", body);
                    P(s.id);
                    await load();
                    form.reset();
                    M("Store created. Import its order history below.");
                  });
                }}
              >
                <div className="grid two">
                  <Field label="Store name">
                    <input
                      aria-label="Store name"
                      name="name"
                      required
                      maxLength={120}
                    />
                  </Field>
                  <Field label="Store currency">
                    <select aria-label="Store currency" name="currency">
                      {["USD", "EUR", "GBP", "DZD"].map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </Field>
                </div>
                <button disabled={busy}>Create store</button>
              </form>
            </section>
            <section className="card">
              <h2>Preview customer orders</h2>
              <p>
                One row per order:{" "}
                <code>customer_id,order_id,order_date,amount,status</code>.
              </p>
              <p className="muted">
                Use stable customer IDs without names or emails. Status is
                completed, cancelled or refunded; money uses decimal text.
              </p>
              <div className="grid three">
                <Field label="Dataset source">
                  <input
                    aria-label="Dataset source"
                    value={source}
                    onChange={(e) => O(e.target.value)}
                  />
                </Field>
                <Field label="Coverage end">
                  <input
                    aria-label="Coverage end"
                    type="date"
                    max={today()}
                    value={coverage}
                    onChange={(e) => CV(e.target.value)}
                  />
                </Field>
                <Field label="Orders CSV">
                  <input
                    aria-label="Orders CSV"
                    type="file"
                    accept=".csv,text/csv"
                    onChange={(e) => {
                      const f = e.target.files[0];
                      if (f)
                        task(async () => {
                          if (f.size > 2000000)
                            throw Error("Maximum CSV size is 2 MB.");
                          V(
                            await write("/imports/orders/preview", {
                              csv_text: await f.text(),
                            }),
                          );
                        });
                    }}
                  />
                </Field>
              </div>
              <p className="muted">
                Coverage end declares the last date with complete order
                coverage, including days with no purchases. Do not advance it
                without checking the source.
              </p>
              {preview && (
                <div className="import-preview">
                  <p>{preview.rows.length} valid orders</p>
                  {preview.errors.map((x, i) => (
                    <p key={i} className="error">
                      Row {x.row}: {x.message}
                    </p>
                  ))}
                  <button
                    disabled={busy || !selected || !preview.valid}
                    onClick={() =>
                      task(async () => {
                        const d = await write(
                          "/stores/" + selected + "/datasets",
                          {
                            source,
                            coverage_end: coverage,
                            orders: preview.rows,
                          },
                        );
                        D(await api("/v1/stores/" + selected + "/datasets"));
                        K(d.id);
                        AS(d.coverage_end);
                        V(null);
                        M("Immutable order dataset saved.");
                      })
                    }
                  >
                    Save reviewed dataset
                  </button>
                </div>
              )}
            </section>
            <section className="card">
              <h2>Dataset versions</h2>
              {datasets.map((d) => (
                <div className="saved" key={d.id}>
                  <div>
                    <b>{d.source}</b>
                    <small>
                      {d.quality.count} orders · {d.quality.customer_ids}{" "}
                      customer IDs · coverage through {d.coverage_end}
                    </small>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => {
                      K(d.id);
                      AS(d.coverage_end);
                      T("Analysis setup");
                    }}
                  >
                    Use dataset
                  </button>
                </div>
              ))}
            </section>
          </>
        )}
        {tab === "Analysis setup" && (
          <section className="card">
            <h2>Retention review assumptions</h2>
            <div className="grid three">
              <Field label="Dataset version">
                <select
                  aria-label="Dataset version"
                  value={dataset}
                  onChange={(e) => {
                    K(e.target.value);
                    const d = datasets.find((x) => x.id === e.target.value);
                    if (d) AS(d.coverage_end);
                  }}
                >
                  <option value="">Select dataset</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.source} · {d.coverage_end}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Analysis name">
                <input
                  aria-label="Analysis name"
                  value={scenario}
                  onChange={(e) => N(e.target.value)}
                  maxLength={120}
                />
              </Field>
              <Field label="Analysis date">
                <input
                  aria-label="Analysis date"
                  type="date"
                  min={current?.quality.start}
                  max={current?.coverage_end || today()}
                  value={asof}
                  onChange={(e) => AS(e.target.value)}
                />
              </Field>
              <Field label="Inactivity days">
                <input
                  aria-label="Inactivity days"
                  type="number"
                  min="7"
                  max="365"
                  value={inactivity}
                  onChange={(e) => IN(e.target.value)}
                />
              </Field>
              <Field label="Cohort follow-up months">
                <input
                  aria-label="Cohort follow-up months"
                  type="number"
                  min="1"
                  max="12"
                  value={horizon}
                  onChange={(e) => H(e.target.value)}
                />
              </Field>
            </div>
            <p className="muted">
              Only completed orders on or before the analysis date are included.
              RFM scores are relative to the customers in that snapshot.
              Analysis cannot extend beyond declared dataset coverage.
            </p>
            <p>
              Inactive means recency is strictly greater than the selected
              threshold. Long inactive means greater than twice that threshold.
              This is a descriptive business rule.
            </p>
            <button disabled={busy || !dataset} onClick={run}>
              Analyze and save review
            </button>
          </section>
        )}
        {tab === "Customer segments" && (
          <section className="card">
            <h2>Customer RFM and purchase history</h2>
            {result ? (
              <>
                <div className="grid two">
                  <Field label="Search customer ID">
                    <input
                      aria-label="Search customer ID"
                      value={search}
                      onChange={(e) => Q(e.target.value)}
                    />
                  </Field>
                  <Field label="Segment filter">
                    <select
                      aria-label="Segment filter"
                      value={segment}
                      onChange={(e) => F(e.target.value)}
                    >
                      <option>All segments</option>
                      {result.results.segments.map((s) => (
                        <option key={s.segment}>{s.segment}</option>
                      ))}
                    </select>
                  </Field>
                </div>
                <p className="muted">
                  Showing up to 200 matching customers. Export CSV for the
                  complete snapshot.
                </p>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {[
                          "Customer",
                          "Last purchase",
                          "Recency days",
                          "Orders",
                          "Spend",
                          "RFM",
                          "Segment",
                        ].map((h) => (
                          <th key={h}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.results.customers
                        .filter(
                          (x) =>
                            x.customer_id
                              .toLowerCase()
                              .includes(search.toLowerCase()) &&
                            (segment === "All segments" ||
                              x.segment === segment),
                        )
                        .slice(0, 200)
                        .map((x) => (
                          <tr key={x.customer_id}>
                            <td>{x.customer_id}</td>
                            <td>{x.last_purchase}</td>
                            <td>{x.recency_days}</td>
                            <td>{x.frequency}</td>
                            <td>
                              {currency} {num(x.monetary)}
                            </td>
                            <td>
                              <span className="pill">{x.rfm}</span>
                            </td>
                            <td>{x.segment}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
                <p className="muted">
                  Recency is inverted: recent buyers score higher. Equal values
                  receive equal scores. Three is the score when all values tie.
                </p>
              </>
            ) : (
              <p>Save or open an analysis first.</p>
            )}
          </section>
        )}
        {tab === "Cohort retention" && (
          <section className="card">
            <h2>Exact-month purchase retention</h2>
            {result ? (
              <>
                <Cohorts rows={result.results.cohorts} />
                <p className="muted">
                  A customer may return after a gap. This table does not measure
                  consecutive survival or subscription cancellation.
                </p>
                <h3>Monthly activity</h3>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Month</th>
                        <th>Unique buyers</th>
                        <th>Orders</th>
                        <th>Revenue</th>
                        <th>Period</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.results.monthly.map((m) => (
                        <tr key={m.month}>
                          <td>{m.month}</td>
                          <td>{m.buyers}</td>
                          <td>{m.orders}</td>
                          <td>
                            {currency} {num(m.revenue)}
                          </td>
                          <td>
                            {m.partial
                              ? "Open through analysis date"
                              : "Closed"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p>Save or open an analysis first.</p>
            )}
          </section>
        )}
        {tab === "Reports & comparisons" && (
          <section className="card">
            <h2>Saved retention reviews</h2>
            <p className="muted">
              Compare inactivity thresholds on the same store, dataset, date and
              cohort horizon.
            </p>
            {analyses.map((a) => (
              <div className="saved" key={a.id}>
                <input
                  type="checkbox"
                  aria-label={"Compare " + a.inputs.scenario_name}
                  checked={checked.includes(a.id)}
                  onChange={(e) =>
                    C(
                      e.target.checked
                        ? [...checked, a.id]
                        : checked.filter((x) => x !== a.id),
                    )
                  }
                />
                <div>
                  <b>{a.inputs.scenario_name}</b>
                  <small>
                    {a.inputs.store.name} · {a.inputs.as_of} · inactive after{" "}
                    {a.inputs.inactivity_days} days
                  </small>
                </div>
                <button
                  className="text-button"
                  onClick={() => {
                    R(a);
                    T("Overview");
                  }}
                >
                  Open review
                </button>
                {[
                  ["json", "JSON report"],
                  ["customers", "Customer CSV"],
                  ["cohorts", "Cohort CSV"],
                ].map(([f, label]) => (
                  <a
                    key={f}
                    href={"/api/v1/analyses/" + a.id + "/report?format=" + f}
                  >
                    {label}
                  </a>
                ))}
              </div>
            ))}
            <button
              disabled={busy || checked.length < 2 || checked.length > 10}
              onClick={() =>
                task(async () =>
                  J(await write("/comparisons", { analysis_ids: checked })),
                )
              }
            >
              Compare selected reviews
            </button>
            {comparison && (
              <>
                <h3>Review comparison</h3>
                <p>{comparison.message}</p>
                <table>
                  <thead>
                    <tr>
                      <th>Review</th>
                      <th>Inactive buyers</th>
                      <th>Inactivity rate</th>
                      <th>Repeat buyers</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.analyses.map((a) => (
                      <tr key={a.id}>
                        <td>{a.inputs.scenario_name}</td>
                        <td>{a.results.summary.inactive_customers}</td>
                        <td>{pct(a.results.summary.inactivity_rate)}</td>
                        <td>{a.results.summary.repeat_buyers}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </section>
        )}
        <footer>
          RetentionIQ v1.0 · Observed purchase analytics and reviewable customer
          segments
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
