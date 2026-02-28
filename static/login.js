function validateLogin() {
  const u = document.getElementById("username").value.trim();
  const p = document.getElementById("password").value.trim();
  if (!u || !p) { alert("Enter credentials"); return false; }
  return true;
}