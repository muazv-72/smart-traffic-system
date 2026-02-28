function toggleMenu() { document.getElementById("myDropdown").classList.toggle("show"); }
function toggleTheme() { document.body.classList.toggle("dark-mode"); localStorage.setItem("theme", document.body.classList.contains("dark-mode")?"dark":"light"); }
if (localStorage.getItem("theme") === "dark") document.body.classList.add("dark-mode");

function openUserModal() { document.getElementById("myDropdown").classList.remove("show"); document.getElementById("userModal").style.display="flex"; }
function closeUserModal() { document.getElementById("userModal").style.display="none"; }
function createUser() {
    fetch("/create_user", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            username: document.getElementById("new_user").value,
            password: document.getElementById("new_pass").value,
            role: document.getElementById("new_role").value,
            assigned_manager: document.getElementById("assign_manager")?.value
        })
    }).then(r=>r.json()).then(d=> { if(d.success) location.reload(); else alert(d.error); });
}

function openHubModal() { document.getElementById("hubModal").style.display="flex"; }
function closeHubModal() { document.getElementById("hubModal").style.display="none"; }
function submitNewHub() {
    fetch("/add_hub", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name:document.getElementById("new_hub_name").value}) })
    .then(r=>r.json()).then(d=> { if(d.success) location.reload(); });
}
function deleteHub(id) { if(confirm("Delete Hub?")) fetch("/delete_hub", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({id})}).then(r=> location.reload()); }

function openPasswordModal() { document.getElementById("myDropdown").classList.remove("show"); document.getElementById("passwordModal").style.display="flex"; }
function closePasswordModal() { document.getElementById("passwordModal").style.display="none"; }
function submitPasswordChange() {
    fetch("/change_password", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ old_password: document.getElementById("oldPass").value, new_password: document.getElementById("newPass").value })
    }).then(r=>r.json()).then(d=> { if(d.success) { alert("Updated!"); closePasswordModal(); } else alert(d.error); });
}

window.onclick = function(e) {
    if(e.target == document.getElementById("userModal")) closeUserModal();
    if(e.target == document.getElementById("hubModal")) closeHubModal();
    if(!e.target.matches('.menu-btn')) document.querySelectorAll(".dropdown-content").forEach(d=>d.classList.remove('show'));
}

function updateHubTraffic(){
    fetch("/api/hub-traffic")
    .then(response => response.json())
    .then(data => {
        data.forEach(hub => {
            const element = document.querySelector(
                `.hub-traffic[data-hub="${hub.hub_id}"]`
            );
            if(element){
                element.innerText = hub.traffic;
            }
        });
    });
}

setInterval(updateHubTraffic, 2000);
updateHubTraffic();