function log(msg){
    const t = document.getElementById("terminal");
    t.innerHTML += msg + "<br>";
    t.scrollTop = t.scrollHeight;
}

function connect(){
    fetch("/connect")
    .then(r=>r.json())
    .then(d=>log(d.status));
}

function startRecording(){
    fetch("/start_recording")
    .then(r=>r.json())
    .then(d=>log(d.status));
}

function stopRecording(){
    fetch("/stop_recording")
    .then(r=>r.json())
    .then(d=>log(d.status));
}

function convert(){
    fetch("/convert")
    .then(r=>r.json())
    .then(d=>log(d.status));
}

function download(){
    window.location = "/download";
}