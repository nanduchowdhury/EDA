

///////////////////////////////////////////////////
// Handle Python class enrollment form
//////////////////////////////////////////////////
document.getElementById('enrollForm').onsubmit = async function(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const response = await fetch(form.action, {
        method: 'POST',
        body: formData
    });
    const message = await response.text();
    alert(message); // Show popup with server response
    form.reset();
};


