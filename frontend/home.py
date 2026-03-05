from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

robot_config = {
    "A": "None",
    "B": "None",
    "C": "None",
    "D": "None",
    "E": "None",
    "F": "None",
}

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>FLL Dashboard</title>
<style>
body { font-family: Arial; margin:0; background:#f4f6f8; }
header { background:#111827; color:white; padding:15px; font-size:20px; }

.container { display:flex; height:90vh; }
.left, .right { flex:1; padding:20px; overflow:auto; }

.card {
    background:white;
    padding:15px;
    border-radius:10px;
    margin-bottom:20px;
    box-shadow:0 2px 6px rgba(0,0,0,0.1);
}

button { padding:8px 12px; margin:5px 5px 5px 0; cursor:pointer; }

#terminal {
    background:black;
    color:lime;
    height:150px;
    overflow-y:auto;
    padding:10px;
    font-family:monospace;
}

#planner {
    position:relative;
    background:#e5e7eb;
    height:450px;
    border:2px dashed #999;
}

.robot, .obstacle {
    width:40px;
    height:40px;
    position:absolute;
    cursor:grab;
}

.robot { background:red; }
.obstacle { background:gray; }

/* Modal */
.modal {
    display:none;
    position:fixed;
    top:0; left:0;
    width:100%; height:100%;
    background:rgba(0,0,0,0.5);
}

.modal-content {
    background:white;
    padding:20px;
    width:400px;
    margin:100px auto;
    border-radius:10px;
}
</style>
</head>
<body>

<header>FLL Dashboard</header>

<div style="padding:10px;">
    <button onclick="connect()">Connect to Robot</button>
    <button onclick="openConfig()">Configure Robot</button>
</div>

<div class="container">

<div class="left">
<div class="card">
<h3>Robot Tracker</h3>
<button onclick="startTracking()">Start Tracking</button>
<button onclick="stopTracking()">Stop Tracking</button>
<button onclick="convertToCode()">Convert to Code</button>

<h4>Status Terminal</h4>
<div id="terminal"></div>
</div>
</div>

<div class="right">
<div class="card">
<h3>Path Planner</h3>
<button onclick="addObstacle()">Add Obstacle</button>
<button onclick="convertPath()">Convert Path</button>
<div id="planner">
    <div id="robot" class="robot" style="top:50px; left:50px;"></div>
</div>
</div>
</div>

</div>

<!-- CONFIG MODAL -->
<div id="configModal" class="modal">
<div class="modal-content">
<h3>Configure Robot Ports</h3>
<form id="configForm">
    <div id="ports"></div>
    <br>
    <button type="button" onclick="saveConfig()">Save</button>
    <button type="button" onclick="closeConfig()">Cancel</button>
</form>
</div>
</div>

<script>

function log(msg){
    const t = document.getElementById("terminal");
    t.innerHTML += msg + "<br>";
    t.scrollTop = t.scrollHeight;
}

function connect(){
    fetch("/connect").then(r=>r.json()).then(d=>log(d.status));
}

/* ---------------- THESE ARE THE FUNCTIONS NEEDED TO BE EDITED TO IMPLEMENT THE DIFFERENT FUNCTIONS ---------------- */
function startTracking(){ log("Tracking started."); }
function stopTracking(){ log("Tracking stopped."); }
function convertToCode(){ log("Converting tracked data to code..."); }
function convertPath(){ log("Converting path to code..."); }

/* ---------------- CONFIG ---------------- */

function openConfig(){
    fetch("/get_config")
    .then(r=>r.json())
    .then(config=>{
        const portsDiv = document.getElementById("ports");
        portsDiv.innerHTML = "";
        for (let port in config){
            portsDiv.innerHTML += `
                <label>Port ${port}:
                <select name="${port}">
                    <option ${config[port]=="None"?"selected":""}>None</option>
                    <option ${config[port]=="Motor"?"selected":""}>Motor</option>
                    <option ${config[port]=="Color Sensor"?"selected":""}>Color Sensor</option>
                    <option ${config[port]=="Distance Sensor"?"selected":""}>Distance Sensor</option>
                </select></label><br><br>`;
        }
        document.getElementById("configModal").style.display="block";
    });
}

function closeConfig(){
    document.getElementById("configModal").style.display="none";
}

function saveConfig(){
    const form = new FormData(document.getElementById("configForm"));
    const data = {};
    form.forEach((value,key)=>data[key]=value);

    fetch("/save_config",{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(data)
    })
    .then(r=>r.json())
    .then(d=>{
        log("Configuration saved.");
        closeConfig();
    });
}

/* ---------------- DRAGGING ---------------- */

function makeDraggable(el){
    el.onmousedown = function(event){
        event.preventDefault();
        document.onmousemove = function(e){
            el.style.left = e.pageX - el.parentElement.offsetLeft - 20 + "px";
            el.style.top = e.pageY - el.parentElement.offsetTop - 20 + "px";
        };
        document.onmouseup = function(){
            document.onmousemove = null;
        };
    };
}

makeDraggable(document.getElementById("robot"));

function addObstacle(){
    const planner = document.getElementById("planner");
    const obs = document.createElement("div");
    obs.className="obstacle";
    obs.style.top = Math.random()*350+"px";
    obs.style.left = Math.random()*350+"px";
    planner.appendChild(obs);
    makeDraggable(obs);
}

</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/connect")
def connect():
    return jsonify({"status":"Robot connected successfully!"})

@app.route("/get_config")
def get_config():
    return jsonify(robot_config)

@app.route("/save_config", methods=["POST"])
def save_config():
    global robot_config
    robot_config = request.json
    return jsonify({"status":"saved"})

if __name__ == "__main__":
    app.run(debug=True)