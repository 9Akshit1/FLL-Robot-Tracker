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
    { id: "none", label: "Not Used", disabled: true },
    { id: "left_drive", label: "Left Drive Motor" },
    { id: "right_drive", label: "Right Drive Motor" },
    { id: "attachment", label: "Attachment Motor" },
    { id: "distance_sensor", label: "Distance Sensor" },
    { id: "force_sensor", label: "Force Sensor" },
    { id: "color_sensor", label: "Color Sensor" }
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
    if (portStatus) portStatus.textContent = "Local agent not running. See setup banner above.";
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
                const motorRole = config.motors[port];
                if (motorRole === "left_drive") select.value = "left_drive";
                else if (motorRole === "right_drive") select.value = "right_drive";
                else if (motorRole === "attachment") select.value = "attachment";
            } 
            else if (config.sensors) {
                for (const [sensorType, assignedPort] of Object.entries(config.sensors)) {
                    if (assignedPort === port) {
                        if (sensorType === "distance") select.value = "distance_sensor";
                        if (sensorType === "force") select.value = "force_sensor";
                        if (sensorType === "color") select.value = "color_sensor";
                    }
                }
            }
        });

        if (comPortSelected && comPort) {
            comPort.value = comPortSelected;
            portStatus.textContent = "Loaded saved port: " + comPortSelected;
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
        
        const selectHTML = DEVICE_TYPES.map(type => {
            const disabled = type.disabled ? 'disabled' : '';
            return `<option value="${type.id}" ${disabled}>${type.label}</option>`;
        }).join("");
        
        item.innerHTML = `
            <label>Port ${port}</label>
            <select id="port${port}">
                ${selectHTML}
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
        portStatus.textContent = "Local agent not running. Please start local_agent.py";
        return;
    }

    detectPortsBtn.disabled = true;
    portStatus.textContent = "Scanning ports via local agent...";
    
    try {
        console.log("[PORTS] Fetching from", `${AGENT_URL}/agent/detect_ports`);
        
        const response = await fetch(`${AGENT_URL}/agent/detect_ports`);
        const result = await response.json();
        
        console.log("[PORTS] Response:", result);
        
        if (result.error) {
            console.log("[PORTS] Error in response:", result.error);
            portStatus.textContent = "Error: " + result.error;
            detectPortsBtn.disabled = false;
            return;
        }

        if (result.ports && result.ports.length > 0) {
            console.log("[PORTS] Found ports:", result.ports);
            comPort.innerHTML = result.ports
                .map(p => `<option value="${p.port}">${p.port} - ${p.description}</option>`)
                .join("");
            portStatus.textContent = "Found " + result.ports.length + " port(s)";
        } else {
            console.log("[PORTS] No ports found");
            comPort.innerHTML = "<option value=\"\">No ports detected</option>";
            portStatus.textContent = "No ports detected. Connect your robot and try again.";
        }
    } catch (e) {
        console.error("[PORTS] Fetch error:", e);
        portStatus.textContent = "Error: " + e.message;
    } finally {
        detectPortsBtn.disabled = false;
    }
}

if (detectPortsBtn) {
    detectPortsBtn.addEventListener("click", detectPorts);
}

// ============================================================
// BUILD CONFIG OBJECT
// ============================================================

function buildConfigObject() {
    const config = {
        com_port: comPort ? comPort.value : "",
        motors: {},
        sensors: {}
    };

    PORT_LABELS.forEach(port => {
        const select = document.getElementById(`port${port}`);
        if (!select) return;

        const value = select.value;
        
        if (value === "left_drive" || value === "right_drive" || value === "attachment") {
            config.motors[port] = value;
        } else if (value === "distance_sensor") {
            config.sensors.distance = port;
        } else if (value === "force_sensor") {
            config.sensors.force = port;
        } else if (value === "color_sensor") {
            config.sensors.color = port;
        }
    });

    return config;
}

// ============================================================
// SAVE CONFIG
// ============================================================

if (saveConfigBtn) {
    saveConfigBtn.addEventListener("click", async () => {
        saveConfigBtn.disabled = true;
        configStatus.textContent = "Saving configuration...";

        try {
            const config = buildConfigObject();

            if (!config.com_port) {
                configStatus.textContent = "Error: No COM port selected";
                saveConfigBtn.disabled = false;
                return;
            }

            const response = await fetch("/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ config: config })
            });

            const data = await response.json();

            if (response.ok) {
                saveToLocalStorage();
                currentConfig = config;
                configStatus.textContent = "Configuration saved and uploaded to robot";
                
                if (connectBtn) connectBtn.disabled = false;
                statusBox.textContent = "Ready to record. Click 'Connect & Record' to start.";
                addTerminal("\n[*] Robot configured successfully");
            } else {
                configStatus.textContent = "Error: " + (data.message || "Failed to save");
            }
        } catch (e) {
            configStatus.textContent = "Error: " + e.message;
        } finally {
            saveConfigBtn.disabled = false;
        }
    });
}

// ============================================================
// TERMINAL FUNCTIONS
// ============================================================

function addTerminal(text) {
    terminalOutput.push(text);
    if (terminal) {
        terminal.textContent = terminalOutput.join("\n");
        terminal.scrollTop = terminal.scrollHeight;
    }
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ============================================================
// WORKFLOW BUTTONS
// ============================================================

if (connectBtn) {
    connectBtn.addEventListener("click", async () => {
        connectBtn.disabled = true;
        addTerminal("\n[*] Connecting to robot...");

        try {
            if (!comPortSelected) {
                comPortSelected = comPort.value;
            }

            if (!comPortSelected) {
                addTerminal("[Error] No COM port selected");
                connectBtn.disabled = false;
                return;
            }

            // First: Get the script from the server
            const scriptRes = await fetch('/connect');
            if (!scriptRes.ok) {
                const errorText = await scriptRes.text();
                console.error("Failed to get script:", errorText);
                throw new Error("Failed to get script: " + scriptRes.status);
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

            if (!response.ok) {
                const errorText = await response.text();
                console.error("Server returned an error:", errorText);
                throw new Error("Server Error: " + response.status);
            }

            const data = await response.json();
            if (response.ok) {
                addTerminal("[OK] Recording complete");
                if (pullBtn) pullBtn.disabled = false;
                statusBox.textContent = "Recording done. Ready to pull data.";
            } else {
                addTerminal("[Error] " + data.message);
                connectBtn.disabled = false;
            }
        } catch (e) {
            addTerminal("[Error] " + e.message);
            connectBtn.disabled = false;
        }
    });
}

if (pullBtn) {
    pullBtn.addEventListener("click", async () => {
        pullBtn.disabled = true;
        addTerminal("\n[*] Pulling CSV...");

        try {
            // Step 1: Pull from local agent
            const response = await fetch(`${AGENT_URL}/agent/pull`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ com_port: comPortSelected })
            });
            const data = await response.json();
            if (!response.ok) {
                addTerminal("[Error] " + data.message);
                pullBtn.disabled = false;
                return;
            }
            
            addTerminal("[OK] CSV pulled from agent (" + data.csv_size + " bytes)");
            
            // Step 2: Save CSV to PythonAnywhere server
            addTerminal("[*] Saving to server...");
            const saveRes = await fetch(`${API_BASE}/save_csv`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ csv_content: data.csv_content })
            });
            const saveData = await saveRes.json();
            if (saveRes.ok) {
                addTerminal("[OK] Saved to server");
                if (analyzeBtn) analyzeBtn.disabled = false;
                statusBox.textContent = "Data ready. Click 'Analyze' to proceed.";
            } else {
                addTerminal("[Error] Save failed: " + saveData.message);
                pullBtn.disabled = false;
            }
        } catch (e) {
            addTerminal("[Error] " + e.message);
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
                addTerminal("[Error] " + data.message);
                analyzeBtn.disabled = false;
            }
        } catch (e) {
            addTerminal("[Error] " + e.message);
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
                    codePreview.innerHTML = "<pre>" + escapeHtml(data.script_content) + "</pre>";
                }
                if (uploadBtn) uploadBtn.disabled = false;
                if (downloadBtn) downloadBtn.disabled = false;
                statusBox.textContent = "Script generated. Click 'Upload' or 'Download'.";
            } else {
                addTerminal("[Error] " + data.message);
                convertBtn.disabled = false;
            }
        } catch (e) {
            addTerminal("[Error] " + e.message);
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
                body: JSON.stringify({ script: scriptData.script, com_port: comPortSelected })
            });
            const data = await response.json();
            if (response.ok) {
                addTerminal(data.output);
                if (runBtn) runBtn.disabled = false;
                statusBox.textContent = "Script uploaded. Click 'Run' to execute.";
            } else {
                addTerminal("[Error] " + data.message);
                uploadBtn.disabled = false;
            }
        } catch (e) {
            addTerminal("[Error] " + e.message);
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
                addTerminal("[OK] Done");
                statusBox.textContent = "Complete!";
            } else {
                addTerminal("[Error] " + data.message);
                runBtn.disabled = false;
            }
        } catch (e) {
            addTerminal("[Error] " + e.message);
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
                addTerminal("[OK] Downloaded");
            }
        } catch (e) {
            addTerminal("[Error] " + e.message);
        }
    });
}

// ============================================================
// RUN INIT
// ============================================================

init();