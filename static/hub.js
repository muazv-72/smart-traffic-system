// ==========================================
// 1. MENU & THEME LOGIC
// ==========================================
function toggleMenu() {
  document.getElementById("myDropdown").classList.toggle("show");
}

function toggleTheme() {
  const body = document.body;
  body.classList.toggle("dark-mode");
  localStorage.setItem("theme", body.classList.contains("dark-mode") ? "dark" : "light");
}

if (localStorage.getItem("theme") === "dark") {
  document.body.classList.add("dark-mode");
}

// Close menu/modals if clicked outside
window.onclick = function(event) {
  if (!event.target.matches('.menu-btn')) {
    const dropdowns = document.getElementsByClassName("dropdown-content");
    for (let i = 0; i < dropdowns.length; i++) {
      if (dropdowns[i].classList.contains('show')) dropdowns[i].classList.remove('show');
    }
  }
  const addModal = document.getElementById("addCameraModal");
  const editModal = document.getElementById("editCameraModal");
  if (event.target == addModal) closeAddCamera();
  if (event.target == editModal) closeEditModal();
}

// ==========================================
// 2. ADD CAMERA - ROI DRAWING LOGIC
// ==========================================
let canvas, ctx;
let img = new Image();
let points = []; 

function loadSnapshot() {
    const ip = document.getElementById("camPath").value;
    if(!ip) { alert("Enter Video Path first!"); return; }

    // Show loading text
    const btn = event.target; // The button that was clicked
    const oldText = btn.innerText;
    btn.innerText = "Loading...";

    fetch("/get_snapshot", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ ip: ip })
    })
    .then(res => res.json())
    .then(data => {
        btn.innerText = oldText; // Restore button text
        
        if(data.error) { 
            alert("❌ Error: " + data.error + "\n\nCheck if the file exists and the path is correct."); 
            return; 
        }
        
        document.getElementById("canvas-container").style.display = "block";
        canvas = document.getElementById("roiCanvas");
        ctx = canvas.getContext("2d");

        img.src = "data:image/jpeg;base64," + data.image;
        img.onload = function() {
            canvas.width = 600;
            canvas.height = (img.height / img.width) * 600; 
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            
            points = [];
            document.getElementById("roiData").value = "";
        }
        canvas.onclick = handleCanvasClick;
    })
    .catch(err => {
        btn.innerText = oldText;
        alert("❌ Network Error: Could not connect to server.");
        console.error(err);
    });
}

function handleCanvasClick(e) {
    if (points.length >= 4) return; 

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;

    points.push({ x, y });
    redrawCanvas();

    if (points.length === 4) {
        savePointsToInput();
    }
}

function redrawCanvas() {
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#e74c3c"; 
    for (let p of points) {
        ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, Math.PI * 2); ctx.fill();
    }
    if (points.length > 1) {
        ctx.strokeStyle = "#2ecc71"; 
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);
        for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
        if (points.length === 4) {
            ctx.lineTo(points[0].x, points[0].y);
            ctx.stroke();
            ctx.fillStyle = "rgba(46, 204, 113, 0.3)";
            ctx.fill();
        } else {
            ctx.stroke();
        }
    }
}

function savePointsToInput() {
    if (!img.width || !canvas.width) return;
    const scaleX = img.width / canvas.width;
    const scaleY = img.height / canvas.height;
    const coords = points.map(p => `${Math.floor(p.x * scaleX)},${Math.floor(p.y * scaleY)}`).join(",");
    document.getElementById("roiData").value = coords;
}

function resetROI() {
    points = [];
    document.getElementById("roiData").value = "";
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
}

// ==========================================
// 3. AUTO/MANUAL MODE LOGIC
// ==========================================
function setMode(mode) {
  fetch("/set_mode", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({hub_id:HUB_ID, mode: mode })
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      console.log("Mode changed to:", data.mode);
      const btns = document.querySelectorAll(".green-btn");
      btns.forEach(b => b.disabled = (data.mode === "auto"));
    }
  })
  .catch(console.error);
}

// ==========================================
// 4. CAMERA MANAGEMENT
// ==========================================
function setGreen(cameraId) {
  fetch("/set_green", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: cameraId })
  }).catch(console.error);
}

function setRed(camId){
  fetch("/set_red", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: camId })
  }).catch(console.error);
}

function openAddCamera() { document.getElementById("addCameraModal").style.display = "flex"; }
function closeAddCamera() { 
    document.getElementById("addCameraModal").style.display = "none";
    document.getElementById("canvas-container").style.display = "none";
    document.getElementById("roiData").value = "";
    document.getElementById("camPath").value = "";
    document.getElementById("camName").value = "";
}

function saveCamera() {
  const name = document.getElementById("camName").value;
  const ip = document.getElementById("camPath").value;
  const hubId = document.getElementById("currentHubId").value;
  const roi = document.getElementById("roiData").value;

  if (!name || !ip) { alert("Fill all fields"); return; }

  fetch("/add_camera", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, ip, hub_id: hubId, roi: roi })
  }).then(res => res.json()).then(data => { if(data.ok) location.reload(); });
}

// ==========================================
// 5. NEW: EDIT CAMERA & ROI LOGIC
// ==========================================
let editCanvas, editCtx, editImg = new Image();
let editPoints = [];

// UPDATED: Automatically loads image when modal opens
function openEditModal(id, name, ip) {
  document.getElementById("editCamId").value = id;
  document.getElementById("editCamName").value = name;
  document.getElementById("editCamPath").value = ip;
  
  // Show Modal
  document.getElementById("editCameraModal").style.display = "flex";
  
  // Auto Load Image
  loadEditImage(ip);
}

function closeEditModal() { document.getElementById("editCameraModal").style.display = "none"; }

function loadEditImage(ip) {
    if(!ip) return;
    
    const container = document.getElementById("edit-canvas-container");
    resetEditROI(); // Clear previous drawing

    fetch("/get_snapshot", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ ip: ip })
    })
    .then(res => res.json())
    .then(data => {
        if(data.error) { 
            console.log("Snapshot error:", data.error);
            // Alert user so they know why it's blank
            alert("Could not load camera view: " + data.error);
            return; 
        }

        editCanvas = document.getElementById("editRoiCanvas");
        editCtx = editCanvas.getContext("2d");

        editImg.src = "data:image/jpeg;base64," + data.image;
        editImg.onload = function() {
            // Match canvas internal size to display size
            const rect = container.getBoundingClientRect();
            editCanvas.width = rect.width;
            editCanvas.height = rect.height;
            
            // Draw
            editCtx.drawImage(editImg, 0, 0, editCanvas.width, editCanvas.height);
            
            // Re-draw saved ROI if it exists
            const savedRoi = document.getElementById("editRoiData").value;
            if (savedRoi) {
                 // Logic to redraw saved ROI points could go here if needed
            }
        }
        
        editCanvas.onclick = function(e) {
            handleEditClick(e);
        };
    })
    .catch(err => console.error("Fetch Error:", err));
}

function handleEditClick(e) {
    if (editPoints.length >= 4) return;
    
    // Correct Scaling Math
    const rect = editCanvas.getBoundingClientRect();
    const scaleX = editCanvas.width / rect.width;
    const scaleY = editCanvas.height / rect.height;

    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    
    editPoints.push({ x, y });
    redrawEditCanvas(); 
    
    if (editPoints.length === 4) {
        // Save silently without alert
        const finalScaleX = editImg.width / editCanvas.width;
        const finalScaleY = editImg.height / editCanvas.height;
        const coords = editPoints.map(p => `${Math.floor(p.x * finalScaleX)},${Math.floor(p.y * finalScaleY)}`).join(",");
        document.getElementById("editRoiData").value = coords;
    }
}

function redrawEditCanvas() {
    editCtx.drawImage(editImg, 0, 0, editCanvas.width, editCanvas.height);
    
    editCtx.fillStyle = "#e74c3c"; 
    for (let p of editPoints) {
        editCtx.beginPath(); editCtx.arc(p.x, p.y, 4, 0, Math.PI * 2); editCtx.fill();
    }
    
    if (editPoints.length > 1) {
        editCtx.strokeStyle = "#f39c12"; 
        editCtx.lineWidth = 2;
        editCtx.beginPath();
        editCtx.moveTo(editPoints[0].x, editPoints[0].y);
        for (let i = 1; i < editPoints.length; i++) editCtx.lineTo(editPoints[i].x, editPoints[i].y);
        if (editPoints.length === 4) {
            editCtx.lineTo(editPoints[0].x, editPoints[0].y);
            editCtx.fillStyle = "rgba(243, 156, 18, 0.3)";
            editCtx.fill();
        }
        editCtx.stroke();
    }
}

function resetEditROI() {
    editPoints = [];
    document.getElementById("editRoiData").value = "";
    if(editCtx) editCtx.drawImage(editImg, 0, 0, editCanvas.width, editCanvas.height);
}

function saveEditCamera() {
  const id = document.getElementById("editCamId").value;
  const name = document.getElementById("editCamName").value;
  const ip = document.getElementById("editCamPath").value;
  const roi = document.getElementById("editRoiData").value;

  fetch("/edit_camera", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, name, ip, roi })
  }).then(res => res.json()).then(data => { if(data.success) location.reload(); });
}

function confirmDelete() {
  if(confirm("Delete this camera?")) {
    fetch("/delete_camera", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: document.getElementById("editCamId").value })
    }).then(res => res.json()).then(data => { if(data.success) location.reload(); });
  }
}

// ==========================================
// 6. LIVE UPDATES
// ==========================================
function pollState() {
  fetch("/state").then(res => res.json()).then(data => {
    // Update Mode
    const modeSelect = document.querySelector(".mode-select");
    if(modeSelect && modeSelect.value !== data.mode) {
        modeSelect.value = data.mode;
    }
    // Update Cameras
    Object.entries(data.cameras).forEach(([id, cam]) => {
      const card = document.querySelector(`.card[data-cid="${id}"]`);
      if (card) {
        card.classList.remove("red", "yellow", "green"); card.classList.add(cam.light);
        const dot = card.querySelector(".status-dot");
        if(dot) { dot.classList.remove("red", "yellow", "green"); dot.classList.add(cam.light); }
        const text = card.querySelector(".light-text");
        if (text) text.innerText = cam.light.toUpperCase();
        const count = card.querySelector("b");
        if (count) count.innerText = cam.vehicles;
      }

      if (currentViewId === id) {
          const modalContent = document.querySelector(".view-modal-content");
          const countSpan = document.getElementById("viewVehicleCount");
          const statusSpan = document.getElementById("viewLightStatus");

          // Update Border Color
          modalContent.style.borderColor = getColorCode(cam.light);
          
          // Update Text
          if(countSpan) countSpan.innerText = cam.vehicles;
          if(statusSpan) {
              statusSpan.innerText = cam.light.toUpperCase();
              statusSpan.style.color = getColorCode(cam.light);
          }
      }
    });
  }).catch(() => {
      // Silent catch for poll error to avoid console spam when server restarts
  });
}


// ==========================================
// 7. FOCUS VIEW (Maximize Video)
// ==========================================
// Global variable to track which camera is focused
let currentViewId = null; 

function openViewModal(id, name, ip) {
    currentViewId = id;
    const modal = document.getElementById("viewModal");
    const img = document.getElementById("largeVideoFeed");
    const title = document.getElementById("viewRoadName");

    // Set Static Info
    img.src = "/video/" + id;
    title.innerText = name;
    
    // Show Modal
    modal.style.display = "flex";

    // Trigger an immediate poll to set colors/counts
    pollState();
}

function closeViewModal() {
    currentViewId = null;
    const modal = document.getElementById("viewModal");
    const img = document.getElementById("largeVideoFeed");
    
    modal.style.display = "none";
    img.src = ""; // Stop loading video to save bandwidth
}

function getColorCode(light) {
    if (light === "red") return "#e74c3c";
    if (light === "yellow") return "#f1c40f";
    if (light === "green") return "#2ecc71";
    return "#ccc";
}

function updateCameraStatus(){
  const hubId = document.getElementById("currentHubId").value;

  fetch(`/api/camera-status/${hubId}`)
  .then(response => response.json())
  .then(data => {

    document.querySelectorAll(".card").forEach(card =>{

      const camId = card.getAttribute("data-cid");

      if(data[camId]){

        const vehicleElement = card.querySelector(".vehicle-count");
        if(vehicleElement){
          vehicleElement.innerText = data[camId].vehicles;
        }

        const lightElement = card.querySelector(".light-text");
        if(lightElement){
          lightElement.innerText =
              data[camId].light.toUpperCase();
        }

        card.classList.remove("red","green","yellow");
        card.classList.add(data[camId].light);


        const dot = card.querySelector(".status-dot");
        if(dot){
          dot.classList.remove("red","green","yellow");
          dot.classList.add(data[camId].light);
        }


        // ⭐ BUTTON TEXT AUTO CHANGE
        const btn = card.querySelector(".green-btn");

        if(btn){

            if(data[camId].light === "green"){
                btn.innerText = "Set RED";
            }
            else{
                btn.innerText = "Set GREEN";
            }

        }

      }
    });

  });
}

function toggleLight(camId) {
    fetch("/toggle_light", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            camera_id: camId,
            hub_id: HUB_ID
        })
    })
    .then(res =>res.json())
    .then(data =>{

      if(data.success){
        location.reload();
      }else{
        alert("Failed to change signal");
      }
    });

}

setInterval(function(){

  fetch("/state")
  .then(res => res.json())
  .then(data => {
    let cams = data.cameras;

    for(let camId in cams){
      let light = cams[camId].light;
      let video = document.getElementById("video_"+camId);

      if(!video) continue;

      if(light === "red"){
        if(video.src !== ""){
            video.src = "";
        }

        video.style.opacity = "0.4";
      }

      if(light === "green" || light === "yellow"){
        if(video.src === ""){
          video.src = "/video/" + camId;        
        }
        video.style.opacity = "1";
      }
    }
  });
},1000);

setInterval(updateCameraStatus, 2000);

updateCameraStatus();
