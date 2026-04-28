// frontend/static/dashboard.js

const API_BASE = window.location.origin; 
const AGENT_URL = "http://localhost:5001";

let terminalOutput = [];
let currentConfig = null;
let comPortSelected = null;

// UI Elements
const statusBox = document.getElementById("status");
const terminal = document.getElementById("terminal");
const configStatus = document.getElementById("configStatus");
const codePreview = document.getElementById("codePreview");
const comPort = document.getElementById("comPort");
const detectPortsBtn = document.getElementById("detectPortsBtn");
const portStatus = document.getElementById("portStatus");
const configGrid = document.getElementById("configGrid");
const saveConfigBtn = document.getElementById("saveConfigBtn");
const setupBanner = document.getElementById("setupBanner");
const agentStatusBadge = document.getElementById("agentStatusBadge");

// Workflow Buttons
const connectBtn = document.getElementById("connectBtn");
const pullBtn = document.getElementById("pullBtn");
const analyzeBtn = document.getElementById("analyzeBtn");
const convertBtn = document.getElementById("convertBtn");
const uploadBtn = document.getElementById("uploadBtn");
const runBtn = document.getElementById("runBtn");
const downloadBtn = document.getElementById("downloadBtn");

const PORT_LABELS = ["A", "B", "C", "D", "E", "F"];
const DEVICE_TYPES = [
    { id: "none", label: "None" },
    { id: "motor", label: "Motor" },
    { id: "distance_sensor", label: "Distance Sensor" },
    { id: "force_sensor", label: "Force Sensor" }
];

// ============================================================
// AGENT STATUS CHECK (SIMPLIFIED)
// ============================================================

async function checkAgentStatus() {
    try {
        console.log("[AGENT] Checking status at", AGENT_URL);
        
        const response = await fetch(`${AGENT_URL}/agent/ping`, {
            method: "GET",
            timeout: 3000
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log("[AGENT] Agent is ONLINE");
            showAgentOnline();
            return true;
        } else {
            console.log("[AGENT] Agent responded with error:", response.status);
            showAgentOffline();
            return false;
        }
    } catch (error) {
        console.log("[AGENT] Agent check failed:", error.message);
        showAgentOffline();
        return false;
    }
}

function showAgentOnline() {
    console.log("[UI] Showing agent ONLINE");
    if (setupBanner) setupBanner.classList.remove("show");
    if (agentStatusBadge) {
        agentStatusBadge.classList.remove("disconnected");
        agentStatusBadge.classList.add("connected");
        agentStatusBadge.textContent = "Agent: Online";
    }
    if (comPort) comPort.disabled = false;
    if (detectPortsBtn) detectPortsBtn.disabled = false;
}

function showAgentOffline() {
    console.log("[UI] Showing agent OFFLINE");
    if (setupBanner) setupBanner.classList.add("show");
    if (agentStatusBadge) {
        agentStatusBadge.classList.remove("connected");
        agentStatusBadge.classList.add("disconnected");
        agentStatusBadge.textContent = "Agent: Offline";
    }
    if (comPort) comPort.disabled = true;
    if (detectPortsBtn) detectPortsBtn.disabled = true;
    if (portStatus) portStatus.textContent = "⚠️ Local agent not running. See setup banner above.";
}

// ============================================================
// INITIALIZATION
// ============================================================

function init() {
    console.log("[INIT] Starting initialization");
    
    // 1. Generate config UI
    generateConfigUI();
    
    // 2. Load saved preferences
    loadSavedPreferences();
    
    // 3. Check agent status NOW
    console.log("[INIT] Checking agent status...");
    checkAgentStatus();
    
    // 4. Auto-check every 3 seconds
    setInterval(() => {
        console.log("[AUTO] Checking agent status...");
        checkAgentStatus();
    }, 3000);
    
    addTerminal("System initialized. Checking for local agent...");
}

// ============================================================
// LOCAL STORAGE
// ============================================================

function saveToLocalStorage() {
    const config = buildConfigObject();
    localStorage.setItem("fll_robot_config", JSON.stringify(config));
}

function loadSavedPreferences() {
    const saved = localStorage.getItem("fll_robot_config");
    if (!saved) return;

    try {
        const config = JSON.parse(saved);
        comPortSelected = config.com_port;
        
        PORT_LABELS.forEach(port => {
            const select = document.getElementById(`port${port}`);
            if (!select) return;

            select.value = "none";

            if (config.motors && config.motors[port]) {
                select.value = "motor";
            } 
            else if (config.sensors) {
                for (const [sensorType, assignedPort] of Object.entries(config.sensors)) {
                    if (assignedPort === port) {
                        if (sensorType === "distance") select.value = "distance_sensor";
                        if (sensorType === "force") select.value = "force_sensor";
                    }
                }
            }
        });

        if (comPortSelected && comPort) {
            comPort.value = comPortSelected;
            portStatus.textContent = `✓ Loaded saved port: ${comPortSelected}`;
        }
    } catch (e) {
        console.error("Failed to load saved config", e);
    }
}

// ============================================================
// CONFIG UI
// ============================================================

function generateConfigUI() {
    configGrid.innerHTML = "";
    
    PORT_LABELS.forEach(port => {
        const item = document.createElement("div");
        item.className = "config-item";
        item.innerHTML = `
            <label>Port ${port}</label>
            <select id="port${port}">
                ${DEVICE_TYPES.map(type => 
                    `<option value="${type.id}">${type.label}</option>`
                ).join("")}
            </select>
        `;
        configGrid.appendChild(item);
    });
}

// ============================================================
// PORT DETECTION
// ============================================================

async function detectPorts() {
    console.log("[PORTS] Detect ports clicked");
    
    // Check agent first
    const agentOk = await checkAgentStatus();
    if (!agentOk) {
        console.log("[PORTS] Agent not OK, returning");
        portStatus.textContent = "✗ Local agent not running. Please start local_agent.py";
        return;
    }

    detectPortsBtn.disabled = true;
    portStatus.textContent = "[*] Scanning ports via local agent...";
    
    try {
        console.log("[PORTS] Fetching from", `${AGENT_URL}/agent/detect_ports`);
        
        const response = await fetch(`${AGENT_URL}/agent/detect_ports`);
        const result = await response.json();
        
        console.log("[PORTS] Response:", result);
        
        if (result.error) {
            console.log("[PORTS] Error in response:", result.error);
            portStatus.textContent = `✗ ${result.error}`;
            detectPortsBtn.disabled = false;
            return;
        }

        const ports = result.ports || [];
        console.log("[PORTS] Found ports:", ports);
        
        if (ports.length > 0) {
            comPort.innerHTML = '<option value="">-- Select Port --</option>';
            
            ports.forEach(portInfo => {
                const option = document.createElement("option");
                option.value = portInfo.port;
                option.textContent = `${portInfo.port} - ${portInfo.description || "Serial Port"}`;
                comPort.appendChild(option);
            });
            
            portStatus.textContent = `✓ Found ${ports.length} port(s). Select one above.`;
            comPort.disabled = false;
        } else {
            console.log("[PORTS] No ports found");
            portStatus.textContent = "✗ No ports found. Connect a device via USB and try again.";
            comPort.innerHTML = '<option value="">No ports available</option>';
            comPort.disabled = true;
        }
    } catch (e) {
        console.log("[PORTS] Exception:", e);
        portStatus.textContent = `✗ ${e.message}`;
    }
    detectPortsBtn.disabled = false;
}

if (comPort) comPort.addEventListener("change", () => {
    comPortSelected = comPort.value;
    saveToLocalStorage();
    if (comPortSelected) {
        portStatus.textContent = `✓ Port ${comPortSelected} selected`;
    }
});

if (detectPortsBtn) detectPortsBtn.addEventListener("click", detectPorts);

// ============================================================
// CONFIG MANAGEMENT
// ============================================================

function buildConfigObject() {
    const config = {
        com_port: comPortSelected,
        motors: {},
        sensors: {}
    };
    
    PORT_LABELS.forEach(port => {
        const select = document.getElementById(`port${port}`);
        if (!select) return;
        const value = select.value;
        
        if (value === "motor") {
            config.motors[port] = true;
        } else if (value === "distance_sensor") {
            config.sensors.distance = port;
        } else if (value === "force_sensor") {
            config.sensors.force = port;
        } 
    });
    
    return config;
}

async function saveConfig() {
    if (!comPortSelected) {
        portStatus.textContent = "✗ Please select a COM port first";
        return;
    }
    
    const config = buildConfigObject();
    
    if (Object.keys(config.motors).length === 0) {
        configStatus.textContent = "✗ Please select at least one motor";
        return;
    }
    
    saveConfigBtn.disabled = true;
    configStatus.textContent = "[*] Saving configuration...";
    saveToLocalStorage();
    
    try {
        const response = await fetch(`${AGENT_URL}/agent/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ config })
        });
        
        if (response.ok) {
            currentConfig = config;
            configStatus.textContent = "✓ Configuration saved";
            statusBox.textContent = "Configuration ready. Click 'Connect & Record' to begin.";
            connectBtn.disabled = false;
            addTerminal("[✓] Config saved and synced");
        } else {
            const data = await response.json();
            configStatus.textContent = `✗ ${data.message}`;
        }
    } catch (e) {
        configStatus.textContent = `✗ ${e.message}`;
    } finally {
        saveConfigBtn.disabled = false;
    }
}

if (saveConfigBtn) saveConfigBtn.addEventListener("click", saveConfig);

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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================
// WORKFLOW
// ============================================================

if (connectBtn) {
    connectBtn.addEventListener("click", async () => {
        connectBtn.disabled = true;
        clearTerminal();
        addTerminal("[*] Getting script...");
        
        try {
            // First: Get the script from the server
            const scriptRes = await fetch('/connect');
            if (!scriptRes.ok) {
                const errorText = await scriptRes.text();
                console.error("Failed to get script:", errorText);
                throw new Error(`Failed to get script: ${scriptRes.status}`);
            }
            const scriptData = await scriptRes.json();
            
            addTerminal("[*] Uploading code...");
            
            // Second: Send to agent
            const response = await fetch(`${AGENT_URL}/agent/connect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    script_content: scriptData.script_content,
                    com_port: scriptData.com_port
                })
            });
            // Add this check BEFORE calling .json()
            if (!response.ok) {
                const errorText = await response.text(); // Get the HTML error as text
                console.error("Server returned an error:", errorText);
                throw new Error(`Server Error: ${response.status}`);
            }

            const data = await response.json();
            if (response.ok) {
                addTerminal("[✓] Recording complete");
                if (pullBtn) pullBtn.disabled = false;
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
}

if (pullBtn) {
    pullBtn.addEventListener("click", async () => {
        pullBtn.disabled = true;
        addTerminal("\n[*] Pulling CSV...");

        try {
            const response = await fetch(`${AGENT_URL}/agent/pull`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ com_port: comPortSelected })
            });
            const data = await response.json();
            if (response.ok) {
                addTerminal(`[✓] CSV pulled (${data.csv_size} bytes)`);
                if (analyzeBtn) analyzeBtn.disabled = false;
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
}

if (analyzeBtn) {
    analyzeBtn.addEventListener("click", async () => {
        analyzeBtn.disabled = true;
        addTerminal("\n[*] Analyzing movement...");
        
        try {
            const response = await fetch(`${API_BASE}/analyze`);
            const data = await response.json();
            if (response.ok) {
                addTerminal(data.output);
                if (convertBtn) convertBtn.disabled = false;
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
}

if (convertBtn) {
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
                if (uploadBtn) uploadBtn.disabled = false;
                if (downloadBtn) downloadBtn.disabled = false;
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
}

if (uploadBtn) {
    uploadBtn.addEventListener("click", async () => {
        uploadBtn.disabled = true;
        addTerminal("\n[*] Uploading script...");
        
        try {
            // First: Get the generated script from PythonAnywhere
            const scriptRes = await fetch(`${API_BASE}/get_generated_script`); 
            const scriptData = await scriptRes.json();
            // Second: Send it to the local agent
            const response = await fetch(`${AGENT_URL}/agent/upload`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ script: scriptData.script })
            });
            const data = await response.json();
            if (response.ok) {
                addTerminal(data.output);
                if (runBtn) runBtn.disabled = false;
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
}

if (runBtn) {
    runBtn.addEventListener("click", async () => {
        runBtn.disabled = true;
        addTerminal("\n[*] Running script...");
        addTerminal("[*] Watch your robot!");
        
        try {
            const response = await fetch(`${AGENT_URL}/agent/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ com_port: comPortSelected })
            });
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
}

if (downloadBtn) {
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
}

// ============================================================
// RUN INIT
// ============================================================

init();