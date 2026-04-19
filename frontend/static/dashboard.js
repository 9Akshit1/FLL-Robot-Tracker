// frontend/static/dashboard.js

const API_BASE = "http://127.0.0.1:5000";
let terminalOutput = [];
let currentConfig = null;

const saveConfigBtn = document.getElementById("saveConfigBtn");
const connectBtn = document.getElementById("connectBtn");
const pullBtn = document.getElementById("pullBtn");
const analyzeBtn = document.getElementById("analyzeBtn");
const convertBtn = document.getElementById("convertBtn");
const uploadBtn = document.getElementById("uploadBtn");
const runBtn = document.getElementById("runBtn");
const downloadBtn = document.getElementById("downloadBtn");

const statusBox = document.getElementById("status");
const terminal = document.getElementById("terminal");
const configStatus = document.getElementById("configStatus");
const codePreview = document.getElementById("codePreview");

// ============================================================
// TERMINAL
// ============================================================

function addTerminal(text) {
    terminalOutput.push(text);
    terminal.textContent = terminalOutput.join("\n");
    terminal.scrollTop = terminal.scrollHeight;
}

function clearTerminal() {
    terminalOutput = [];
    terminal.textContent = "Waiting...";
}

// ============================================================
// CONFIG MANAGEMENT
// ============================================================

function buildConfigObject() {
    return {
        motors: {
            A: document.getElementById("motorA").value !== "none" ? document.getElementById("motorA").value : null,
            B: document.getElementById("motorB").value !== "none" ? document.getElementById("motorB").value : null,
            C: document.getElementById("motorC").value !== "none" ? document.getElementById("motorC").value : null,
        },
        sensors: {
            distance: document.getElementById("sensorDist").value !== "none" ? document.getElementById("sensorDist").value : null,
            force: document.getElementById("sensorForce").value !== "none" ? document.getElementById("sensorForce").value : null,
            color: document.getElementById("sensorColor").value !== "none" ? document.getElementById("sensorColor").value : null,
        }
    };
}

saveConfigBtn.addEventListener("click", async () => {
    const config = buildConfigObject();
    
    // Validate
    const motorCount = Object.values(config.motors).filter(v => v !== null).length;
    if (motorCount === 0) {
        configStatus.textContent = "✗ Please select at least one motor";
        return;
    }
    
    saveConfigBtn.disabled = true;
    configStatus.textContent = "[*] Saving configuration...";
    
    try {
        const response = await fetch(`${API_BASE}/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ config })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentConfig = config;
            configStatus.textContent = "✓ Configuration saved and uploaded to hub";
            statusBox.textContent = "Configuration ready. Click 'Connect & Record' to begin.";
            connectBtn.disabled = false;
            addTerminal("[✓] Config saved");
        } else {
            configStatus.textContent = `✗ ${data.message}`;
            saveConfigBtn.disabled = false;
        }
    } catch (e) {
        configStatus.textContent = `✗ ${e.message}`;
        saveConfigBtn.disabled = false;
    }
});

// ============================================================
// HANDLERS
// ============================================================

connectBtn.addEventListener("click", async () => {
    connectBtn.disabled = true;
    clearTerminal();
    addTerminal("[*] Uploading code...");
    addTerminal("[*] Press LEFT to start, RIGHT to stop");
    
    try {
        const response = await fetch(`${API_BASE}/connect`);
        const data = await response.json();
        if (response.ok) {
            addTerminal("[✓] Recording complete");
            pullBtn.disabled = false;
            statusBox.textContent = "Recording done. Ready to pull data.";
        } else {
            addTerminal(`[✗] ${data.message}`);
            connectBtn.disabled = false;
        }
    } catch (e) {
        addTerminal(`[✗] ${e.message}`);
        connectBtn.disabled = false;
    }
});

pullBtn.addEventListener("click", async () => {
    pullBtn.disabled = true;
    addTerminal("\n[*] Pulling CSV...");
    
    try {
        const response = await fetch(`${API_BASE}/pull_csv`);
        const data = await response.json();
        if (response.ok) {
            addTerminal(`[✓] CSV pulled (${data.csv_size} bytes)`);
            analyzeBtn.disabled = false;
            statusBox.textContent = "Data ready. Click 'Analyze' to proceed.";
        } else {
            addTerminal(`[✗] ${data.message}`);
            pullBtn.disabled = false;
        }
    } catch (e) {
        addTerminal(`[✗] ${e.message}`);
        pullBtn.disabled = false;
    }
});

analyzeBtn.addEventListener("click", async () => {
    analyzeBtn.disabled = true;
    addTerminal("\n[*] Analyzing movement...");
    
    try {
        const response = await fetch(`${API_BASE}/analyze`);
        const data = await response.json();
        if (response.ok) {
            addTerminal(data.output);
            convertBtn.disabled = false;
            statusBox.textContent = "Analysis complete. Click 'Generate' to create replay script.";
        } else {
            addTerminal(`[✗] ${data.message}`);
            analyzeBtn.disabled = false;
        }
    } catch (e) {
        addTerminal(`[✗] ${e.message}`);
        analyzeBtn.disabled = false;
    }
});

convertBtn.addEventListener("click", async () => {
    convertBtn.disabled = true;
    addTerminal("\n[*] Generating script...");
    
    try {
        const response = await fetch(`${API_BASE}/convert`);
        const data = await response.json();
        if (response.ok) {
            addTerminal(data.output);
            if (data.script_content) {
                codePreview.innerHTML = `<pre>${escapeHtml(data.script_content)}</pre>`;
            }
            uploadBtn.disabled = false;
            downloadBtn.disabled = false;
            statusBox.textContent = "Script generated. Click 'Upload' or 'Download'.";
        } else {
            addTerminal(`[✗] ${data.message}`);
            convertBtn.disabled = false;
        }
    } catch (e) {
        addTerminal(`[✗] ${e.message}`);
        convertBtn.disabled = false;
    }
});

uploadBtn.addEventListener("click", async () => {
    uploadBtn.disabled = true;
    addTerminal("\n[*] Uploading script...");
    
    try {
        const response = await fetch(`${API_BASE}/upload_script`);
        const data = await response.json();
        if (response.ok) {
            addTerminal(data.output);
            runBtn.disabled = false;
            statusBox.textContent = "Script uploaded. Click 'Run' to execute.";
        } else {
            addTerminal(`[✗] ${data.message}`);
            uploadBtn.disabled = false;
        }
    } catch (e) {
        addTerminal(`[✗] ${e.message}`);
        uploadBtn.disabled = false;
    }
});

runBtn.addEventListener("click", async () => {
    runBtn.disabled = true;
    addTerminal("\n[*] Running script...");
    addTerminal("[*] Watch your robot!");
    
    try {
        const response = await fetch(`${API_BASE}/run_script`);
        const data = await response.json();
        if (response.ok) {
            addTerminal(data.output);
            addTerminal("[✓] Done");
            statusBox.textContent = "Complete!";
        } else {
            addTerminal(`[✗] ${data.message}`);
            runBtn.disabled = false;
        }
    } catch (e) {
        addTerminal(`[✗] ${e.message}`);
        runBtn.disabled = false;
    }
});

downloadBtn.addEventListener("click", async () => {
    try {
        const response = await fetch(`${API_BASE}/download`);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'replay.py';
            a.click();
            addTerminal("[✓] Downloaded");
        }
    } catch (e) {
        addTerminal(`[✗] ${e.message}`);
    }
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize
addTerminal("Configure your robot in the settings above");