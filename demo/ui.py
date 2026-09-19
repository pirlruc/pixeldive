"""HTML UI for the pixeldive capture demo."""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>pixeldive capture demo</title>
  <style>
    :root { color-scheme: dark; --bg:#0f1419; --card:#1a2330; --accent:#3ee0a0; --text:#e8eef5; --muted:#8aa0b5; --bad:#ff7b72; }
    body { font-family: ui-sans-serif, system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; }
    main { max-width: 960px; margin: 0 auto; padding: 24px; }
    h1 { font-size: 1.4rem; }
    .muted { color: var(--muted); }
    .row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin: 12px 0; }
    button, input[type=file] { font: inherit; }
    button { background: var(--accent); color: #042016; border: 0; border-radius: 8px; padding: 8px 14px; cursor: pointer; font-weight: 600; }
    button.danger { background: var(--bad); color: #1a0404; }
    section { background: var(--card); border-radius: 12px; padding: 16px; margin: 16px 0; }
    pre { overflow: auto; background: #0b1016; padding: 12px; border-radius: 8px; font-size: 12px; }
    .status { font-family: ui-monospace, monospace; font-size: 12px; }
    .error { color: var(--bad); min-height: 1.2em; }
    a { color: var(--accent); }
  </style>
</head>
<body>
<main>
  <h1>pixeldive capture demo</h1>
  <p class="muted">Android-shaped session payloads via the Python SDK (<code>pixeldive_sdk.RestClient</code>).</p>
  <p class="status" id="health">checking service…</p>
  <p class="error" id="error"></p>
  <section>
    <h2>Session</h2>
    <div class="row">
      <button id="create">Create session</button>
      <button id="refresh">Refresh list</button>
      <button id="delete" class="danger">Delete session</button>
    </div>
    <pre id="session">{}</pre>
  </section>
  <section>
    <h2>Upload</h2>
    <div class="row">
      <input id="file" type="file" accept="image/*"/>
      <button id="upload">Upload image</button>
    </div>
    <pre id="images">[]</pre>
    <p class="muted" id="download"></p>
  </section>
</main>
<script>
const $ = (id) => document.getElementById(id);
let sessionId = null;
function showError(err) {
  $("error").textContent = err ? String(err) : "";
}
async function json(url, opts) {
  const res = await fetch(url, opts);
  const text = await res.text();
  if (!res.ok) throw new Error(text);
  return text ? JSON.parse(text) : {};
}
async function boot() {
  try {
    const h = await json("/api/health");
    $("health").textContent = "service " + h.health.status + " / ready " + h.ready.status;
    showError("");
  } catch (err) {
    $("health").textContent = "service unreachable";
    showError(err);
  }
  await refresh();
}
async function refresh() {
  try {
    const listed = await json("/api/sessions");
    if (!sessionId && listed.items.length) sessionId = listed.items[0].id;
    $("session").textContent = JSON.stringify(listed, null, 2);
    if (!sessionId) {
      $("images").textContent = "[]";
      $("download").textContent = "";
      return;
    }
    const images = await json("/api/sessions/" + sessionId + "/images");
    $("images").textContent = JSON.stringify(images, null, 2);
    const first = images.items[0];
    $("download").innerHTML = first
      ? '<a href="/api/sessions/' + sessionId + '/images/' + first.id + '/download">download latest</a>'
      : "";
    showError("");
  } catch (err) {
    showError(err);
  }
}
$("create").onclick = async () => {
  try {
    const created = await json("/api/sessions", {method: "POST"});
    sessionId = created.id;
    await refresh();
  } catch (err) { showError(err); }
};
$("refresh").onclick = refresh;
$("delete").onclick = async () => {
  if (!sessionId) { showError("create a session first"); return; }
  try {
    await json("/api/sessions/" + sessionId, {method: "DELETE"});
    sessionId = null;
    await refresh();
  } catch (err) { showError(err); }
};
$("upload").onclick = async () => {
  if (!sessionId) { showError("create a session first"); return; }
  const file = $("file").files[0];
  if (!file) { showError("choose an image"); return; }
  const body = new FormData();
  body.append("file", file);
  try {
    const res = await fetch("/api/sessions/" + sessionId + "/images", {method: "POST", body});
    if (!res.ok) throw new Error(await res.text());
    await refresh();
  } catch (err) { showError(err); }
};
boot();
</script>
</body>
</html>
"""
