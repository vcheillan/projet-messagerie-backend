const API = "http://127.0.0.1:8000";
let ws = null, users = {};

async function refresh() {
    const res = await fetch(`${API}/users/`);
    const data = await res.json();
    const selMe = document.getElementById('me'), selTo = document.getElementById('to');
    selMe.innerHTML = selTo.innerHTML = '<option value="">-- Choisir --</option>';
    data.forEach(u => {
        users[u.id] = u.name;
        selMe.add(new Option(u.name, u.id));
        selTo.add(new Option(u.name, u.id));
    });
}

async function addUser() {
    const name = document.getElementById('n').value, email = document.getElementById('e').value;
    if(!name || !email) return alert("Remplissez tout !");
    await fetch(`${API}/users/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ name, email })
    });
    refresh();
    document.getElementById('n').value = ""; document.getElementById('e').value = "";
}

function connect() {
    const id = document.getElementById('me').value;
    if (!id) return;
    if (ws) ws.close();
    ws = new WebSocket(`ws://127.0.0.1:8000/ws/${id}`);
    ws.onmessage = (e) => {
        const m = JSON.parse(e.data);
        if (m.type === "USER_LIST") {
            document.getElementById('list').innerHTML = m.data.map(uid => `
                <li class="flex items-center gap-2 text-sm text-slate-700 font-medium">
                    <span class="w-2.5 h-2.5 rounded-full bg-green-500 shadow-sm shadow-green-200"></span>
                    ${users[uid] || 'ID: ' + uid}
                </li>
            `).join('');
        }
        if (m.type === "NEW_MESSAGE") load();
    };
}

// UTILISATION DE : GET /messages/{message_id}
async function getMessageInfo(msgId) {
    const res = await fetch(`${API}/messages/${msgId}`);
    const content = await res.json();
    alert(`Contenu brut du serveur pour le message #${msgId} :\n\n"${content}"`);
}

// UTILISATION DE : DELETE /messages/{message_id}
async function deleteMessage(msgId) {
    if(!confirm("Supprimer ce message définitivement ?")) return;
    await fetch(`${API}/messages/${msgId}`, { method: 'DELETE' });
    load();
}

// UTILISATION DE : PATCH /messages/{message_id}/read
async function markAsRead(msgId) {
    await fetch(`${API}/messages/${msgId}/read`, { method: 'PATCH' });
    load(); // Le message va disparaître à cause de la fonction messages_non_lus() du backend !
}

async function load() {
    const me = document.getElementById('me').value, to = document.getElementById('to').value;
    if (!me || !to) return;
    
    const userRes = await fetch(`${API}/users/${to}`);
    const userData = await userRes.json();
    document.getElementById('chat-title').innerText = userData.name;
    document.getElementById('chat-email').innerText = userData.email;

    const [r1, r2] = await Promise.all([
        fetch(`${API}/users/${me}/inbox`), 
        fetch(`${API}/users/${me}/sent`)
    ]);
    
    const all = [...(await r1.json()), ...(await r2.json())].sort((a,b) => a.id_mess - b.id_mess);
    
    const container = document.getElementById('msgs');
    container.innerHTML = all.filter(m => (m.exp_id==me && m.dest_id==to) || (m.exp_id==to && m.dest_id==me))
        .map(m => {
            const isMe = m.exp_id == me;
            
            const actions = `
                <div class="actions-message">
                    ${!isMe ? `<button onclick="markAsRead(${m.id_mess})" style="color: #2563eb;">Lu</button>` : ''}
                    <button onclick="getMessageInfo(${m.id_mess})">Info</button>
                    <button onclick="deleteMessage(${m.id_mess})" style="color: #ef4444;"><i class="fas fa-trash"></i></button>
                </div>
            `;

            // Le HTML généré est maintenant beaucoup plus clair
            return `
                <div class="ligne-message ${isMe ? 'message-moi' : 'message-autre'}">
                    <div class="conteneur-bulle">
                        <div class="bulle ${isMe ? 'bulle-envoyee' : 'bulle-recue'}">
                            <p>${m.mess_content}</p>
                        </div>
                        ${actions}
                    </div>
                </div>
            `;
        }).join('');
    container.scrollTop = container.scrollHeight;
}

async function send() {
    const me = document.getElementById('me').value, to = document.getElementById('to').value, txt = document.getElementById('in').value;
    if(!txt || !to) return;

    await fetch(`${API}/messages/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ 
            exp_id: parseInt(me), 
            dest_id: parseInt(to), 
            mess_content: txt, 
            // La date sera gérée par le backend par défaut (datetime.now)
            mess_status: "non_lu" 
        })
    });
    document.getElementById('in').value = "";
    load();
}

window.onload = refresh;