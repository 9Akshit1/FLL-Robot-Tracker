// frontend/static/dashboard.js

const API_BASE = "http://127.0.0.1:5000";
let terminalOutput = [];
let currentConfig = null;
let comPortSelected = null;

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
const comPort = document.getElementById("comPort");
const detectPortsBtn = document.getElementById("detectPortsBtn");
const portStatus = document.getElementById("portStatus");
const configGrid = document.getElementById("configGrid");

// Available device types per port
const PORT_LABELS = ["A", "B", "C", "D", "E", "F"];
const DEVICE_TYPES = [
    { id: "none", label: "None" },
    { id: "motor", label: "Motor" },
    { id: "distance_sensor", label: "Distance Sensor" },
    { id: "force_sensor", label: "Force Sensor" },
    { id: "color_sensor", label: "Color Sensor (Not Supported)" }
];

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
// COM PORT DETECTION
// ============================================================

async function detectPorts() {
    detectPortsBtn.disabled = true;
    portStatus.textContent = "[*] Scanning ports...";
    
    try {
        const response = await fetch(`${API_BASE}/detect_ports`);
        const data = await response.json();
        
        if (response.ok && data.ports.length > 0) {
            // Clear existing options
            comPort.innerHTML = "";
            
            // Add port options
            data.ports.forEach(portInfo => {
                const option = document.createElement("option");
                option.value = portInfo.port;
                option.textContent = `${portInfo.port} - ${portInfo.description || "Unknown Device"}`;
                comPort.appendChild(option);
            });
            
            portStatus.textContent = `✓ Found ${data.ports.length} port(s)`;
            comPort.disabled = false;
        } else {
            portStatus.textContent = "✗ No ports found. Make sure robot is connected.";
            comPort.innerHTML = '<option value="">No ports available</option>';
        }
    } catch (e) {
        portStatus.textContent = `✗ ${e.message}`;
    }
    
    detectPortsBtn.disabled = false;
}

comPort.addEventListener("change", () => {
    comPortSelected = comPort.value;
    if (comPortSelected) {
        generateConfigUI();
        portStatus.textContent = `✓ Port ${comPortSelected} selected`;
    }
});

detectPortsBtn.addEventListener("click", detectPorts);

// ============================================================
// DYNAMIC CONFIG UI
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
    
    // Add save button
    const buttonRow = document.createElement("div");
    buttonRow.className = "button-row";
    buttonRow.style.marginTop = "15px";
    buttonRow.innerHTML = `
        <button id="saveConfigBtn" class="btn" style="flex: 0 1 auto; min-width: 150px;">Save & Upload Config</button>
    `;
    configGrid.parentElement.appendChild(buttonRow);
    
    // Re-attach save button handler
    document.getElementById("saveConfigBtn").addEventListener("click", saveConfig);
}

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
        const value = select.value;
        
        if (value === "motor") {
            config.motors[port] = true;
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

async function saveConfig() {
    if (!comPortSelected) {
        portStatus.textContent = "✗ Please select a COM port first";
        return;
    }
    
    const config = buildConfigObject();
    
    // Validate
    if (Object.keys(config.motors).length === 0) {
        document.getElementById("configStatus").textContent = "✗ Please select at least one motor";
        return;
    }
    
    document.getElementById("saveConfigBtn").disabled = true;
    document.getElementById("configStatus").textContent = "[*] Saving configuration...";
    
    try {
        const response = await fetch(`${API_BASE}/config`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ config })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentConfig = config;
            document.getElementById("configStatus").textContent = "✓ Configuration saved and uploaded to hub";
            statusBox.textContent = "Configuration ready. Click 'Connect & Record' to begin.";
            connectBtn.disabled = false;
            addTerminal("[✓] Config saved");
        } else {
            document.getElementById("configStatus").textContent = `✗ ${data.message}`;
            document.getElementById("saveConfigBtn").disabled = false;
        }
    } catch (e) {
        document.getElementById("configStatus").textContent = `✗ ${e.message}`;
        document.getElementById("saveConfigBtn").disabled = false;
    }
}

// Initialize port detection
detectPorts();

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
            statusBox.textContent = "Analysis complete. Click 'Visualize' to see path or 'Generate' to create replay script.";
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