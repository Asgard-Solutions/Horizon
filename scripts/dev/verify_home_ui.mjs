import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, rename, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const base = "http://127.0.0.1:8767";
const dataRoot = path.join(root, "data", "home-integration-check");
const output = path.join(dataRoot, "results");
await mkdir(output, { recursive: true });
const api = async (route, method = "GET", body) => {
  const response = await fetch(base + route, { method, headers: { "X-MC-Client": "ui-verification", "Content-Type": "application/json" }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  const result = await response.json();
  assert(response.ok, `${route}: ${response.status} ${JSON.stringify(result)}`);
  return result;
};
const system = await api("/api/system");
assert.equal(path.resolve(system.data_dir).toLowerCase(), dataRoot.toLowerCase(), "Refusing to change a non-test database");
for (const library of await api("/api/libraries")) await api(`/api/libraries/${library.id}`, "DELETE");
const profile = await mkdtemp(path.join(tmpdir(), "horizon-app-check-"));
const browser = spawn(process.env.HORIZON_REVIEW_CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe", [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--autoplay-policy=no-user-gesture-required",
  "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"
], { windowsHide: true, stdio: ["ignore", "ignore", "pipe"] });
const pause = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
let socket;
let sequence = 0;
let sessionId;
const pending = new Map();
const exceptions = [];
const results = [];
const stalledRequests = [];
let libraryId;
let mediaRoot;
let offlineRoot;
let sourceMoved = false;

function call(method, params = {}, session = sessionId) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Protocol timeout: ${method}`)); }, 20000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params, ...(session ? { sessionId: session } : {}) }));
  });
}
async function evaluate(expression) {
  const result = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  assert(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function wait(expression, label = expression, timeout = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { if (await evaluate(expression)) return; await pause(40); }
  throw new Error(`Timed out: ${label}; ${await evaluate("JSON.stringify({url:location.href,focus:document.activeElement?.id,text:document.body.innerText.slice(0,1200)})")}`);
}
const focus = async selector => { await wait(`!!document.querySelector(${JSON.stringify(selector)})`); return evaluate(`document.querySelector(${JSON.stringify(selector)}).focus()`); };
async function click(selector) {
  await wait(`!!document.querySelector(${JSON.stringify(selector)})`);
  const point = await evaluate(`(() => { const element=document.querySelector(${JSON.stringify(selector)}); element.scrollIntoView({block:'nearest',inline:'nearest'}); const box=element.getBoundingClientRect(); return {x:box.x+box.width/2,y:box.y+box.height/2}; })()`);
  await call("Input.dispatchMouseEvent", { type:"mousePressed",...point,button:"left",clickCount:1 });
  await call("Input.dispatchMouseEvent", { type:"mouseReleased",...point,button:"left",clickCount:1 });
}
async function key(value, repeat = false) {
  const code = { ArrowLeft:37, ArrowUp:38, ArrowRight:39, ArrowDown:40, Enter:13, Escape:27, Tab:9, " ":32 }[value] ?? 0;
  await call("Input.dispatchKeyEvent", { type:"keyDown", key:value, code:value === " " ? "Space" : value, windowsVirtualKeyCode:code, autoRepeat:repeat });
  await call("Input.dispatchKeyEvent", { type:"keyUp", key:value, code:value === " " ? "Space" : value, windowsVirtualKeyCode:code });
}
async function navigate(route, selector) {
  const marker = `navigation-${Date.now()}-${Math.random()}`;
  await evaluate(`window.__testNavigationEpoch=${JSON.stringify(marker)}`);
  await call("Page.navigate", { url:base + route });
  const scene = route === "/" ? " && !!document.querySelector('[data-testid=home-page]')"
    : route.startsWith("/home/") ? ` && document.querySelector('[data-testid=media-home-page]')?.dataset.mediaType===${JSON.stringify(route.slice(6))}` : "";
  await wait(`window.__testNavigationEpoch!==${JSON.stringify(marker)} && document.readyState === "complete" && location.pathname === ${JSON.stringify(route.split("?")[0])} && !!document.querySelector(${JSON.stringify(selector)})${scene}`);
}
async function screenshot(name) {
  const result = await call("Page.captureScreenshot", { format:"png", captureBeyondViewport:false });
  await writeFile(path.join(output, name + ".png"), Buffer.from(result.data, "base64"));
}
async function check(name, action) {
  await action();
  results.push(name);
  console.log(`PASS: ${name}`);
}
async function pad(button, held = 100) {
  await evaluate(`window.__uiPad = window.__uiPad || {index:0,axes:[0,0],buttons:Array.from({length:17},()=>({pressed:false,value:0}))}; window.__uiPad.buttons[${button}].pressed=true`);
  await pause(held);
  await evaluate(`window.__uiPad.buttons[${button}].pressed=false`);
  await pause(80);
}

try {
  const endpoint = await new Promise((resolve, reject) => {
    let text = "";
    const timer = setTimeout(() => reject(new Error("No browser debugging endpoint")), 15000);
    browser.on("error", reject);
    browser.stderr.on("data", chunk => {
      text += chunk.toString();
      const match = text.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) { clearTimeout(timer); resolve(match[1]); }
    });
  });
  socket = new WebSocket(endpoint);
  await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once:true }); socket.addEventListener("error", reject, { once:true }); });
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    if (message.method === "Fetch.requestPaused") stalledRequests.push(message.params.requestId);
    if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails);
    const entry = pending.get(message.id);
    if (!entry) return;
    clearTimeout(entry.timer);
    pending.delete(message.id);
    if (message.error) entry.reject(new Error(JSON.stringify(message.error)));
    else entry.resolve(message.result);
  });
  const target = await call("Target.createTarget", { url:"about:blank" }, null);
  ({ sessionId } = await call("Target.attachToTarget", { targetId:target.targetId, flatten:true }, null));
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Network.enable");
  await call("Page.addScriptToEvaluateOnNewDocument", { source:"window.__uiPad=null; Object.defineProperty(navigator,'getGamepads',{value:()=>window.__uiPad?[window.__uiPad]:[]});" });
  await call("Emulation.setDeviceMetricsOverride", { width:1920,height:1080,deviceScaleFactor:1,mobile:false });

  await check("empty launch uses real counts and focuses Movies", async () => {
    await navigate("/", "#home-movies");
    await wait("document.activeElement.id === 'home-movies'");
    await wait("document.body.innerText.includes('No sources configured')");
    assert.equal(await evaluate("document.querySelectorAll('.hub-card').length"), 2);
    assert.equal(await evaluate("!!document.querySelector('[data-testid=continue-watching]')"), false);
    await screenshot("home-empty-1920x1080");
  });
  await check("TV destination and Back preserve selected type and exact hub focus", async () => {
    await key("ArrowRight");
    await key("Enter");
    await wait("location.pathname==='/home/tv' && document.activeElement.id==='hub-atlas'");
    await key("ArrowRight");
    await key("Enter");
    await wait("location.pathname==='/discover' && !!document.querySelector('[data-testid=discover-page]') && new URLSearchParams(location.search).get('media')==='tv'");
    await key("Escape");
    await wait("location.pathname==='/home/tv' && document.activeElement.id==='hub-discover'");
    await key("Escape");
    await wait("location.pathname==='/' && document.activeElement.id==='home-tv'");
  });
  await check("Retry keeps focus during a pending request then restores a valid control", async () => {
    await call("Network.setBlockedURLs", { urls:[base+"/api/home*"] });
    await evaluate("window.dispatchEvent(new Event('focus'))");
    await wait("!!document.querySelector('#hub-retry')");
    await focus("#home-tv");
    await key("ArrowDown");
    assert.equal(await evaluate("document.activeElement.id"),"hub-retry");
    await call("Network.setBlockedURLs", { urls:[] });
    await call("Network.emulateNetworkConditions", { offline:false,latency:600,downloadThroughput:-1,uploadThroughput:-1 });
    await key("Enter");
    await pause(120);
    assert.equal(await evaluate("document.activeElement.id"),"hub-retry");
    assert.equal(await evaluate("document.querySelector('#hub-retry')?.getAttribute('aria-disabled')"),"true");
    await wait("!document.querySelector('#hub-retry') && document.activeElement.id==='home-tv'");
    await call("Network.emulateNetworkConditions", { offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1 });
  });
  await check("Settings is the only utility and library management has one destination", async () => {
    assert.equal(await evaluate("document.querySelectorAll('[data-testid=nav-sources]').length"),0);
    await key("ArrowUp");
    assert.equal(await evaluate("document.activeElement.id"), "global-settings");
    await key("Enter");
    await wait("!!document.querySelector('[data-testid=settings-page]')");
    await wait("!!document.activeElement.closest('main')", "Settings entry moves focus into its real controls");
    await focus("[data-testid=settings-cat-libraries]");
    await key("Escape");
    await wait("location.pathname==='/' && document.activeElement.id==='global-settings'");
    await key("ArrowLeft");
    assert.equal(await evaluate("document.activeElement.id"),"global-home");
    await key("ArrowRight");
    assert.equal(await evaluate("document.activeElement.id"),"global-settings");
    await call("Page.navigate",{url:base+"/sources?media=tv"});
    await wait("location.pathname==='/settings' && !!document.querySelector('[data-testid=settings-cat-libraries]')");
    assert.equal(await evaluate("new URLSearchParams(location.search).get('section')"),"libraries");
    assert.equal(await evaluate("new URLSearchParams(location.search).get('media')"),"tv");
  });
  await check("mouse returns Home neutral and highlights only while hovering", async () => {
    await navigate("/", "#home-movies");
    for (const id of ["home-movies", "home-tv"]) {
      await click(".hub-footer-status");
      await click(`#${id}`);
      await wait("!!document.querySelector('[data-testid=media-home-page]')");
      await click("#hub-back");
      await wait(`location.pathname==='/' && document.activeElement.id===${JSON.stringify(id)}`);
      await pause(150);
      const returned = await evaluate(`(() => {const el=document.getElementById(${JSON.stringify(id)});const other=document.getElementById(${JSON.stringify(id === "home-movies" ? "home-tv" : "home-movies")});return {hover:el.matches(':hover'),focused:el===document.activeElement,input:document.body.dataset.input,shadow:getComputedStyle(el).boxShadow,neutral:getComputedStyle(other).boxShadow};})()`);
      assert.equal(returned.input,"mouse");
      assert.equal(returned.hover,false);
      assert.equal(returned.focused,true);
      assert.notEqual(returned.shadow,"none","The neutral card frame must remain visible");
      assert.equal(returned.shadow,returned.neutral,"Mouse Back must not leave the remembered card highlighted");
      const point = await evaluate(`(() => {const r=document.getElementById(${JSON.stringify(id)}).getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
      await call("Input.dispatchMouseEvent", {type:"mouseMoved",...point});
      await pause(150);
      const card = await evaluate(`(() => {const el=document.getElementById(${JSON.stringify(id)});return {hover:el.matches(':hover'),focused:el===document.activeElement,visibleFocus:el.matches(':focus-visible'),input:document.body.dataset.input,shadow:getComputedStyle(el).boxShadow};})()`);
      assert.equal(card.input,"mouse");
      assert.equal(card.hover,true);
      assert.equal(card.focused,true);
      assert.notEqual(card.shadow,"none","Hover must retain the card frame");
      assert.notEqual(card.shadow,returned.neutral,"Hover must highlight the card");
      const away = await evaluate("(() => {const r=document.querySelector('.hub-heading').getBoundingClientRect();return {x:r.x+10,y:r.y+10};})()");
      await call("Input.dispatchMouseEvent", {type:"mouseMoved",...away});
      await pause(150);
      const left = await evaluate(`(() => {const el=document.getElementById(${JSON.stringify(id)});return {hover:el.matches(':hover'),focused:el===document.activeElement,shadow:getComputedStyle(el).boxShadow};})()`);
      assert.equal(left.hover,false);
      assert.equal(left.focused,true);
      assert.equal(left.shadow,returned.neutral,"Moving off the card must restore the neutral frame");
    }
  });
  await check("held gamepad A activates only one screen; B restores Movies", async () => {
    await navigate("/", "#home-movies");
    await focus("#home-movies");
    await pad(0, 750);
    assert.equal(await evaluate("location.pathname"), "/home/movie");
    await pad(1);
    await wait("location.pathname==='/' && document.activeElement.id==='home-movies'");
    await pad(15);
    assert.equal(await evaluate("document.activeElement.id"), "home-tv");
    assert.equal(await evaluate("document.body.dataset.input"), "pad");
  });
  await check("keyboard activation holds do not cascade into a destination", async () => {
    await focus("#home-movies");
    await key("Enter");
    await wait("location.pathname==='/home/movie'");
    await key("Enter", true);
    assert.equal(await evaluate("location.pathname"), "/home/movie");
  });
  await check("compact and TV layouts keep controls and rings inside the viewport", async () => {
    for (const [width,height] of [[1920,1080],[1280,720],[3840,2160],[1366,768],[1920,800],[1024,768],[800,600],[390,844]]) {
      await call("Emulation.setDeviceMetricsOverride", { width,height,deviceScaleFactor:1,mobile:false });
      for (const route of ["/", "/home/movie", "/home/tv"]) {
        await navigate(route, ".hub-card");
        const geometry = await evaluate("JSON.stringify({page:document.documentElement.scrollWidth,width:innerWidth,boxes:[...document.querySelectorAll('.hub-card,.hub-brand,.hub-utility,.hub-heading,.hub-footer')].map(element=>{const box=element.getBoundingClientRect();return {name:element.className,x:box.x,right:box.right,top:box.top,bottom:box.bottom}})})");
        const observed = JSON.parse(geometry);
        assert(observed.page<=width+1, `${width}x${height}${route}: page overflow ${geometry}`);
        for (const box of observed.boxes) assert(box.x>=-1 && box.right<=width+1, `${width}x${height}${route}: clipped ${JSON.stringify(box)}`);
      }
    }
    await call("Emulation.setDeviceMetricsOverride", { width:1920,height:1080,deviceScaleFactor:1,mobile:false });
    await navigate("/", "#home-movies");
    await focus("#home-movies");
    await call("Emulation.setDeviceMetricsOverride", { width:390,height:844,deviceScaleFactor:1,mobile:false });
    await wait("!!document.querySelector('.home-shell--stacked-home')");
    assert.equal(await evaluate("document.activeElement.id"),"home-movies");
    await key("ArrowDown");
    assert.equal(await evaluate("document.activeElement.id"), "home-tv");
    await click("#home-tv");
    await wait("location.pathname==='/home/tv'");
    await focus("#hub-atlas");
    await key("ArrowDown");
    assert.equal(await evaluate("document.activeElement.id"), "hub-discover");
    await call("Emulation.setDeviceMetricsOverride", { width:1920,height:1080,deviceScaleFactor:1,mobile:false });
  });
  await check("manual text scaling increases Home text and keeps utility controls reachable", async () => {
    await navigate("/", "#home-movies");
    const normalHeading = await evaluate("document.querySelector('.hub-heading').getBoundingClientRect().height");
    for (const scale of ["1.25","2"]) {
      await evaluate(`localStorage.setItem('horizon.uiScale',${JSON.stringify(scale)})`);
      await navigate("/", "#home-movies");
      await wait(`document.documentElement.dataset.uiScale===${JSON.stringify(scale)}`);
      const geometry = await evaluate("(() => ({page:document.documentElement.scrollWidth,width:innerWidth,heading:document.querySelector('.hub-heading').getBoundingClientRect().height,controls:[...document.querySelectorAll('.hub-card,.hub-utility')].map(element=>{const box=element.getBoundingClientRect();return {left:box.left,right:box.right}})}))()");
      assert(geometry.page<=geometry.width+1, `manual ${scale}: horizontal overflow`);
      assert(geometry.controls.every(box=>box.left>=0 && box.right<=geometry.width+1), `manual ${scale}: inaccessible controls`);
      if (scale==="2") assert(geometry.heading>normalHeading*1.2,"200% text scaling must enlarge text rather than cancel its scale");
    }
    await evaluate("localStorage.removeItem('horizon.uiScale')");
    await navigate("/", "#home-movies");
  });

  mediaRoot = await mkdtemp(path.join(dataRoot, "ui-media-"));
  offlineRoot = mediaRoot + "-offline";
  for (const candidate of [mediaRoot, offlineRoot]) assert(!path.relative(dataRoot,candidate).startsWith(".."), "Fixture path escaped test directory");
  await mkdir(path.join(mediaRoot,"Movies"), { recursive:true });
  await mkdir(path.join(mediaRoot,"TV","Verification series","Season 01"), { recursive:true });
  await writeFile(path.join(mediaRoot,"Movies","Verification movie.webm"), Buffer.alloc(2048));
  await writeFile(path.join(mediaRoot,"Movies","poster.jpg"), Buffer.from("intentionally invalid test artwork"));
  await writeFile(path.join(mediaRoot,"TV","Verification series","Season 01","Verification series S01E01.webm"), Buffer.alloc(2048));
  const library = await api("/api/libraries", "POST", { path:mediaRoot });
  libraryId = library.id;
  const movies = await api("/api/movies");
  const shows = await api("/api/shows");
  assert.equal(movies.length,1);
  const show = await api(`/api/shows/${shows[0].id}`);
  const episode = show.seasons[0].episodes[0];
  await api(`/api/progress/${movies[0].file_id}`, "PUT", { position:30,duration:100 });
  await api(`/api/progress/${episode.file_id}`, "PUT", { position:40,duration:100 });

  await check("real indexed test files and saved history populate only the selected type", async () => {
    await navigate("/home/movie", "[data-testid=continue-watching]");
    assert.equal(await evaluate("document.querySelectorAll('.hub-resume-card').length"),1);
    assert.equal(await evaluate("document.querySelector('.hub-resume-card').id"),`resume-${movies[0].file_id}`);
    await wait("!!document.querySelector('.hub-art-fallback')", "broken poster becomes a neutral fallback");
    await navigate("/home/tv", "[data-testid=continue-watching]");
    assert.equal(await evaluate("document.querySelector('.hub-resume-card').id"),`resume-${episode.file_id}`);
    await focus("#hub-atlas");
    await click(`#resume-${episode.file_id}`);
    await wait("!!document.querySelector('[data-testid=resume-dialog]')");
    await wait("!!document.querySelector('[data-testid=hub-start-over]')");
    await key("Escape");
    await wait(`!document.querySelector('[data-testid=resume-dialog]') && document.activeElement.id==='resume-${episode.file_id}'`);
  });
  await check("completing the focused last item removes its row and recovers focus", async () => {
    await api(`/api/progress/${episode.file_id}`, "PUT", { position:100,duration:100 });
    await evaluate("window.dispatchEvent(new Event('focus'))");
    await wait("!document.querySelector('[data-testid=continue-watching]') && document.activeElement.id==='hub-atlas'");
  });
  await check("modal close restores a valid control after its opener disappears", async () => {
    await api(`/api/progress/${episode.file_id}`, "PUT", { position:40,duration:100 });
    await evaluate("window.dispatchEvent(new Event('focus'))");
    await wait(`!!document.querySelector('#resume-${episode.file_id}')`);
    await click(`#resume-${episode.file_id}`);
    await wait("!!document.querySelector('[data-testid=hub-start-over]')");
    await api(`/api/progress/${episode.file_id}`, "PUT", { position:100,duration:100 });
    await evaluate("window.dispatchEvent(new Event('focus'))");
    await wait("!document.querySelector('[data-testid=continue-watching]')");
    await key("Escape");
    await wait("!document.querySelector('[data-testid=resume-dialog]') && document.activeElement.id==='hub-atlas'");
  });
  await check("Search keeps scope and native caret movement; Atlas drill-down stays scoped", async () => {
    await navigate("/home/tv", "#hub-search");
    await click("#hub-search");
    await wait("!!document.querySelector('[data-testid=search-input]')");
    await focus("[data-testid=search-input]");
    await call("Input.insertText", { text:"Verification" });
    await wait("!!document.querySelector('[data-testid=search-section-shows]')");
    assert.equal(await evaluate("!!document.querySelector('[data-testid=search-section-movies]')"),false);
    await key("ArrowLeft");
    assert.equal(await evaluate("document.activeElement.dataset.testid"),"search-input");
    assert.equal(await evaluate("document.activeElement.selectionStart"),11);
    assert.equal(await evaluate("new URLSearchParams(location.search).get('media')"),"tv");
    await pad(13);
    await wait("!!document.activeElement.closest('.osk')", "gamepad can leave the text input for its keyboard");
    await navigate("/atlas?media=movie", "[data-testid=atlas-page]");
    await wait("!!document.querySelector('[data-testid=atlas-mode-toggle]')");
    await click("[data-testid=atlas-mode-toggle]");
    await wait("!!document.querySelector('[data-testid=atlas-grid]')");
    const typeButton = await evaluate("document.querySelector('[data-testid=atlas-grid] button')?.dataset.testid");
    await click(`[data-testid='${typeButton}']`);
    await wait("!!document.querySelector('.atlas-grid [data-testid^=discover-card-movie]')", "Atlas scoped group opens real movie cards");
  });
  await check("switching type cancels a delayed movie request before TV data renders", async () => {
    await navigate("/", "#home-movies");
    stalledRequests.length=0;
    await call("Fetch.enable", { patterns:[{urlPattern:"*/api/home?media_type=movie*",requestStage:"Request"}] });
    await click("#home-movies");
    await wait("document.querySelector('[data-testid=media-home-page]')?.dataset.mediaType==='movie'");
    for (let attempt=0; attempt<100 && stalledRequests.length===0; attempt++) await pause(20);
    assert(stalledRequests.length>0,"movie request was delayed at the network boundary");
    await click("#hub-back");
    await wait("!!document.querySelector('#home-tv')");
    await click("#home-tv");
    await wait("document.querySelector('[data-testid=media-home-page]')?.dataset.mediaType==='tv' && document.body.innerText.includes('1 TV shows')");
    for (const requestId of stalledRequests) try { await call("Fetch.continueRequest", {requestId}); } catch {}
    await call("Fetch.disable");
    await pause(100);
    assert.equal(await evaluate("!!document.querySelector('[data-testid=continue-watching]')"),false);
    assert.equal(await evaluate("document.querySelector('[data-testid=media-home-page]').dataset.mediaType"),"tv");
  });
  await check("unreachable source keeps history and recovers through library Settings", async () => {
    await rename(mediaRoot, offlineRoot);
    sourceMoved = true;
    await navigate("/home/movie", "[data-testid=continue-watching]");
    await wait("document.body.innerText.includes('source unavailable')");
    await click(`#resume-${movies[0].file_id}`);
    await wait("document.querySelector('[data-testid=resume-dialog]')?.textContent.includes('unavailable')");
    assert.equal(await evaluate("!!document.querySelector('[data-testid=hub-resume]')"),false);
    await click("[data-testid=resume-library-settings]");
    await wait("location.pathname==='/settings' && !!document.querySelector('[data-testid=settings-cat-libraries]')");
    assert.equal(await evaluate("new URLSearchParams(location.search).get('media')"),"movie");
    await click("[data-testid=nav-back]");
    await wait("location.pathname==='/home/movie' && !!document.querySelector('[data-testid=continue-watching]')");
    await rename(offlineRoot, mediaRoot);
    sourceMoved = false;
    assert.equal((await api("/api/home?media_type=movie")).continue_watching.length,1);
  });
  await check("return from failed startup keeps saved progress and makes reordered resume focus visible", async () => {
    await mkdir(path.join(mediaRoot,"Extra movies"), { recursive:true });
    for (let index=1; index<=6; index++) await writeFile(path.join(mediaRoot,"Extra movies",`Verification clip ${index}.webm`), Buffer.alloc(2048));
    await api(`/api/libraries/${libraryId}/scan`, "POST");
    for (const movie of await api("/api/movies")) if (movie.file_id!==movies[0].file_id) await api(`/api/progress/${movie.file_id}`, "PUT", {position:20,duration:100});
    await navigate("/home/movie", "[data-testid=continue-watching]");
    await focus(`#resume-${movies[0].file_id}`);
    await evaluate(`document.querySelector('#resume-${movies[0].file_id}').scrollIntoView({block:'nearest',inline:'nearest'})`);
    await wait("document.querySelector('.hub-resume-row').scrollLeft>0");
    await click(`#resume-${movies[0].file_id}`);
    await wait("!!document.querySelector('[data-testid=hub-start-over]')");
    await click("[data-testid=hub-start-over]");
    await wait("['error','blocked'].includes(document.querySelector('[data-testid=player-page]')?.dataset.phase)", "invalid test file reaches the real player's failure state");
    assert.equal((await api(`/api/files/${movies[0].file_id}/playback`)).progress.position,30);
    await api(`/api/progress/${movies[0].file_id}`, "PUT", {position:31,duration:100});
    await key("Escape");
    await wait(`location.pathname==='/home/movie' && document.activeElement.id==='resume-${movies[0].file_id}'`);
    const visible = await evaluate("(() => { const card=document.activeElement.getBoundingClientRect(); const row=document.querySelector('.hub-resume-row').getBoundingClientRect(); return card.left>=row.left-1 && card.right<=row.right+1; })()");
    assert.equal(visible,true,"reordered focused card must remain fully visible");
  });

  await api(`/api/libraries/${libraryId}`, "DELETE");
  libraryId = null;
  await navigate("/", "#home-movies");
  await wait("document.body.innerText.includes('No sources configured')");
  await screenshot("home-final-empty-1920x1080");
  await navigate("/home/movie", "#hub-atlas");
  await wait("!!document.querySelector('[data-testid=hub-empty-library]')");
  await screenshot("movies-final-empty-1920x1080");
  assert.deepEqual(exceptions, [], "Uncaught browser exceptions");
  await writeFile(path.join(output,"home-ui-results.json"),JSON.stringify({checkedAt:new Date().toISOString(),results,scope:"Actual local app and isolated indexed test files; simulated Gamepad API and locally simulated source outage. Physical gamepad/NAS and successful video playback not verified."},null,2)+"\n");
  console.log(`PASS: ${results.length} actual-app checks. No production library or media files were changed.`);
} catch (error) {
  if (socket?.readyState===WebSocket.OPEN && sessionId) try { await screenshot("failure"); } catch {}
  throw error;
} finally {
  if (sourceMoved) await rename(offlineRoot, mediaRoot);
  if (libraryId) await api(`/api/libraries/${libraryId}`, "DELETE");
  if (socket?.readyState===WebSocket.OPEN) {
    try { await call("Browser.close",{},null); } catch {}
    socket.close();
  }
  if (browser.exitCode===null) browser.kill();
}
