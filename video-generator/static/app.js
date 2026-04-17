/* HealBotics 3D Video Studio – Frontend */

const EXAMPLES = [
  `Erstelle ein 3D-Erklärvideo über die Pathophysiologie des Herzinfarkts für Allgemeinmediziner.
Zeige wie ein Koronararterienverschluss entsteht, welche Rolle Atherosklerose und Thromben spielen
und wie sich dies auf das Myokard auswirkt. Ton: professionell-sachlich. Dauer ca. 90 Sekunden.`,

  `Erstelle ein 3D-Erklärvideo über den Insulin-Signalweg bei Typ-2-Diabetes für Fachärzte.
Erkläre den normalen Insulinrezeptor-Signalweg (PI3K/Akt), zeige wie Insulinresistenz entsteht
und welche molekularen Ziele für Medikamente bestehen. Dauer ca. 2 Minuten.`,

  `Erstelle ein 3D-Erklärvideo über den Wirkmechanismus von Penicillin-Antibiotika für Medizinstudenten.
Zeige die bakterielle Zellwandsynthese (Peptidoglykan), wie Beta-Lactame die Transpeptidase hemmen
und warum Bakterien dadurch absterben. Visueller Stil: dunkel und modern. Dauer 90 Sekunden.`,

  `Erstelle ein 3D-Erklärvideo über synaptische Übertragung und Neurotransmitter für Pflegepersonal.
Erkläre wie ein Aktionspotenzial die Synapse erreicht, Vesikelfusion und Neurotransmitter-Ausschüttung,
Rezeptorbindung auf der Postsynapse. Einfache, verständliche Sprache. Dauer ca. 60 Sekunden.`
];

let currentSource = null;
let isGenerating = false;

// ── Example prompts ──────────────────────────────────────────────────────────

function setExample(idx) {
  document.getElementById('promptInput').value = EXAMPLES[idx];
  updateCharCount();
}

function updateCharCount() {
  const len = document.getElementById('promptInput').value.length;
  document.getElementById('charCount').textContent = `${len} / 2000`;
}

// ── Script-only generation ───────────────────────────────────────────────────

async function generateScriptOnly() {
  const prompt = getPrompt();
  if (!prompt) return;

  setButtonsDisabled(true);
  showSection('scriptCard');
  hideSection('progressCard');
  hideSection('resultCard');
  hideSection('errorCard');

  document.getElementById('scriptTitle').textContent = '⏳ Skript wird generiert...';
  document.getElementById('scriptMeta').textContent = '';
  document.getElementById('scenesList').innerHTML = '<div style="color:var(--text-muted);padding:12px">Generiere mit Claude AI...</div>';

  try {
    const response = await fetch('/api/script-only', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, options: getOptions() })
    });
    const data = await response.json();

    if (data.error) throw new Error(data.error);

    renderScript(data.script);
  } catch (err) {
    document.getElementById('scriptTitle').textContent = '⚠️ Fehler';
    document.getElementById('scenesList').innerHTML = `<div style="color:var(--error);padding:12px">${err.message}</div>`;
  } finally {
    setButtonsDisabled(false);
  }
}

// ── Full video generation ────────────────────────────────────────────────────

async function startVideoGeneration() {
  const prompt = getPrompt();
  if (!prompt) return;
  if (isGenerating) return;

  isGenerating = true;
  setButtonsDisabled(true);
  resetSteps();
  updateProgress(0, 'Initialisierung...');

  showSection('progressCard');
  hideSection('scriptCard');
  hideSection('resultCard');
  hideSection('errorCard');

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, options: getOptions() })
    });
    const { job_id, error } = await response.json();

    if (error) throw new Error(error);

    connectSSE(job_id);
  } catch (err) {
    showError(err.message);
    isGenerating = false;
    setButtonsDisabled(false);
  }
}

function connectSSE(jobId) {
  if (currentSource) currentSource.close();

  currentSource = new EventSource(`/api/status/${jobId}`);

  currentSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleUpdate(data, jobId);
    } catch {}
  };

  currentSource.onerror = () => {
    showError('Verbindung zum Server unterbrochen. Bitte Seite neu laden.');
    currentSource.close();
    isGenerating = false;
    setButtonsDisabled(false);
  };
}

function handleUpdate(data, jobId) {
  if (data.heartbeat || data.done) {
    if (data.done) {
      currentSource?.close();
    }
    return;
  }

  if (data.step === 'error') {
    showError(data.message || 'Unbekannter Fehler');
    currentSource?.close();
    isGenerating = false;
    setButtonsDisabled(false);
    return;
  }

  if (typeof data.progress === 'number') {
    updateProgress(data.progress, data.message);
  }

  if (data.step && data.step !== 'complete') {
    updateStep(data.step, data.status, data.message);
  }

  if (data.step === 'script' && data.status === 'done' && data.data) {
    renderScript(data.data);
    showSection('scriptCard');
  }

  if (data.step === 'complete') {
    showVideo(data.download_url);
    isGenerating = false;
    setButtonsDisabled(false);
  }
}

// ── UI updates ───────────────────────────────────────────────────────────────

function updateProgress(pct, label) {
  document.getElementById('progressFill').style.width = `${pct}%`;
  document.getElementById('progressPct').textContent = `${pct}%`;
  if (label) {
    document.getElementById('progressTitle').textContent =
      pct === 100 ? '✅ Fertig!' : `Generierung läuft... ${pct}%`;
  }
}

function updateStep(stepName, status, message) {
  const step = document.getElementById(`step-${stepName}`);
  const badge = document.getElementById(`badge-${stepName}`);
  const msg = document.getElementById(`msg-${stepName}`);

  if (!step) return;

  step.className = 'step ' + (status === 'done' ? 'done' : status === 'running' ? 'running' : '');

  if (badge) {
    badge.className = 'step-badge';
    badge.textContent = status === 'done' ? '✅' : status === 'running' ? '⏳' : '–';
    if (status === 'running') badge.classList.add('running');
  }

  if (msg && message) msg.textContent = message;
}

function resetSteps() {
  ['script', 'tts', 'video', 'assemble'].forEach(name => {
    updateStep(name, 'idle', 'Warte...');
  });
  updateProgress(0, '');
  document.getElementById('progressTitle').textContent = 'Generierung läuft...';
}

function renderScript(script) {
  document.getElementById('scriptTitle').textContent =
    `📋 ${script.title || 'Generiertes Skript'}`;

  const meta = [
    script.duration_estimate && `Dauer: ~${script.duration_estimate} Min.`,
    script.target_audience && `Zielgruppe: ${script.target_audience}`,
    script.scenes && `${script.scenes.length} Szenen`,
  ].filter(Boolean).join(' · ');

  document.getElementById('scriptMeta').textContent = meta;

  const container = document.getElementById('scenesList');
  container.innerHTML = '';

  const typeLabels = {
    intro: 'Intro', content: 'Inhalt', highlight: 'Highlight',
    comparison: 'Vergleich', summary: 'Zusammenfassung', outro: 'Abschluss'
  };

  (script.scenes || []).forEach(scene => {
    const div = document.createElement('div');
    div.className = 'scene-item';
    div.innerHTML = `
      <div class="scene-header">
        <span class="scene-num">${scene.id}</span>
        <span class="scene-type">${typeLabels[scene.type] || scene.type}</span>
        <span class="scene-duration">${scene.duration}s</span>
      </div>
      ${scene.narration ? `<div class="scene-narration">"${scene.narration}"</div>` : ''}
      ${scene.visual_prompt ? `<div class="scene-visual">🎬 ${scene.visual_prompt}</div>` : ''}
    `;
    container.appendChild(div);
  });
}

function showVideo(downloadUrl) {
  showSection('resultCard');
  const video = document.getElementById('videoPlayer');
  const downloadBtn = document.getElementById('downloadBtn');
  video.src = downloadUrl;
  downloadBtn.href = downloadUrl;
  video.load();
}

function showError(message) {
  hideSection('progressCard');
  showSection('errorCard');
  document.getElementById('errorMsg').textContent = message;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getPrompt() {
  const prompt = document.getElementById('promptInput').value.trim();
  if (!prompt) {
    document.getElementById('promptInput').focus();
    document.getElementById('promptInput').style.borderColor = 'var(--error)';
    setTimeout(() => {
      document.getElementById('promptInput').style.borderColor = '';
    }, 2000);
    return null;
  }
  return prompt;
}

function getOptions() {
  return {
    audience: document.getElementById('audienceSelect').value,
    duration: parseInt(document.getElementById('durationSelect').value),
    style: { color_scheme: document.getElementById('styleSelect').value }
  };
}

function setButtonsDisabled(disabled) {
  document.getElementById('scriptBtn').disabled = disabled;
  document.getElementById('videoBtn').disabled = disabled;
}

function showSection(id) { document.getElementById(id).style.display = ''; }
function hideSection(id) { document.getElementById(id).style.display = 'none'; }

function resetTool() {
  if (currentSource) { currentSource.close(); currentSource = null; }
  isGenerating = false;
  setButtonsDisabled(false);
  hideSection('progressCard');
  hideSection('scriptCard');
  hideSection('resultCard');
  hideSection('errorCard');
  resetSteps();
  document.getElementById('promptInput').focus();
}
