
// ─── Core State ────────────────────────────────────────────────
let sessionId = generateUUID();
let currentLanguage = 'en'; // Changed default to 'en' based on target design
let isRecording = false;
let conversationStarted = false;
let recognition = null; // Native Web Speech API
window.grievanceMode = null; // 'register' | 'check' | null

// ─── DOM References ────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const chatArea       = $('messages') || $('chat-area');
const chatInput      = $('msg-input');
const sendBtn        = $('send-btn');
const voiceBtn       = $('mic-btn');
const languageToggle = document.querySelector('.lang-picker');
const themeToggle    = $('theme-toggle');

const welcomeSection = $('welcome');



// ─── UUID v4 Generator ────────────────────────────────────────
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

// ─── Initialise App ────────────────────────────────────────────
function initApp() {
    if(sendBtn) sendBtn.addEventListener('click', () => handleSend(false));
    if(voiceBtn) voiceBtn.addEventListener('click', toggleVoiceRecording);
    if(languageToggle) languageToggle.addEventListener('click', toggleLanguage);
    // if(themeToggle) themeToggle.addEventListener('click', toggleTheme); // removed to prevent double-firing

    if(chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend(false);
            }
        });
        
        // Active styling for send button
        chatInput.addEventListener('input', () => {
            if(chatInput.value.trim().length > 0) {
                sendBtn.classList.add('active');
            } else {
                sendBtn.classList.remove('active');
            }
        });
    }

    initSpeechRecognition();
    
    // Ensure the message container exists
    if (!chatArea && $('chat-area')) {
        const msgs = document.createElement('div');
        msgs.id = 'messages';
        $('chat-area').appendChild(msgs);
    }
}

// ─── Send Message ──────────────────────────────────────────────
async function handleSend(isVoice = false) {
    if (window.grievanceMode === 'register') {
        window.grievanceMode = null;
        handleGrievanceSubmit();
        return;
    }
    if (window.grievanceMode === 'check') {
        window.grievanceMode = null;
        handleTicketCheck();
        return;
    }
    const text = chatInput.value.trim();
    if (!text) return;

    if (text.toLowerCase() === 'grievance') {
        chatInput.value = '';
        if(sendBtn) sendBtn.classList.remove('active');
        addMessage(text, 'user');
        startGrievanceFlow();
        return;
    }

    if (text.toLowerCase() === 'grievance') {
        chatInput.value = '';
        if(sendBtn) sendBtn.classList.remove('active');
        addMessage(text, 'user');
        startGrievanceFlow();
        return;
    }

    if (!conversationStarted) {
        conversationStarted = true;
        if(welcomeSection) welcomeSection.style.display = 'none';
        const msgs = document.getElementById('messages');
        if(msgs) msgs.style.display = 'flex';
    }

    addMessage(text, 'user');
    chatInput.value = '';
    if(sendBtn) sendBtn.classList.remove('active');

    // Create a typing indicator row in the new format
    const typingId = 'typing-' + Date.now();
    const typingRow = document.createElement('div');
    typingRow.className = 'msg-row assistant';
    typingRow.id = typingId;
    typingRow.innerHTML = `
        <div class="avatar assistant">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                <path d="M5 10h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/>
                <path d="M8 14h.01M16 14h.01"/>
            </svg>
        </div>
        <div class="bubble assistant">
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    const msgsContainer = $('messages') || chatArea;
    msgsContainer.appendChild(typingRow);
    scrollToBottom();

    try {
        const payload = {
            message: text,
            sessionId: sessionId,
            isVoiceMode: isVoice
        };

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        
        // Remove typing indicator
        const el = document.getElementById(typingId);
        if(el) el.remove();

        if (data.structured && data.structured.items && data.structured.items.length > 0) {
            addStructuredMessage(data.structured, 'assistant');
        } else if (data.structured && data.structured.acknowledge) {
            addStructuredMessage(data.structured, 'assistant');
        } else {
            addMessage(data.reply || data.structured?.raw || 'Error', 'assistant');
        }
    } catch (error) {
        console.error('Chat Error:', error);
        const el = document.getElementById(typingId);
        if(el) el.remove();
        addMessage(currentLanguage === 'hi' ? 'सर्वर त्रुटि। कृपया बाद में प्रयास करें।' : 'Server error. Please try again later.', 'assistant');
    }
}

// ─── Add Message to UI ─────────────────────────────────────────
function addMessage(text, sender) {
    const isUser = sender === 'user';
    const row = document.createElement('div');
    row.className = `msg-row ${sender}`;
    
    const avatarHtml = isUser 
        ? `<div class="avatar user">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 100-8 4 4 0 0 0 0 8z" />
            </svg>
           </div>`
        : `<div class="avatar assistant">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                <path d="M5 10h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/>
                <path d="M8 14h.01M16 14h.01"/>
            </svg>
           </div>`;

    const bubbleHtml = `<div class="bubble ${sender}">${formatMessageContent(text)}</div>`;

    row.innerHTML = isUser ? bubbleHtml + avatarHtml : avatarHtml + bubbleHtml;
    
    const msgsContainer = $('messages') || chatArea;
    msgsContainer.appendChild(row);
    scrollToBottom();
}

function formatMessageContent(text) {
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    }
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function linkify(text) {
    if (!text) return text;
    let html = escapeHtml(text);
    // Parse bold markdown
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Parse URLs
    html = html.replace(/(https?:\/\/[^\s]+|[a-z0-9-]+\.gov\.in[^\s]*)/gi, '<a href="https://$1" target="_blank" rel="noopener">$1</a>');
    // Fix double https
    html = html.replace(/https:\/\/https:\/\//g, 'https://');
    return html;
}

// ─── Structured Response Renderer ──────────────────────────────
function addStructuredMessage(structured, sender) {
    // Fallback if structure is broken
    if (!structured || (!structured.acknowledge && !structured.items?.length)) {
        addMessage(structured?.raw || structured?.acknowledge || 'Error', sender);
        return;
    }

    const row = document.createElement('div');
    row.className = `msg-row ${sender}`;

    const avatarHtml = `<div class="avatar assistant">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
            <path d="M5 10h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/>
            <path d="M8 14h.01M16 14h.01"/>
        </svg>
    </div>`;

    let bubbleContent = '';

    // 1. Acknowledge line
    if (structured.acknowledge) {
        let ackText = structured.acknowledge.replace(/\*\*\[LIST\]\*\*/g, '').replace(/\[LIST\]/g, '').trim();
        if (ackText) {
            bubbleContent += `<p class="msme-ack">${linkify(ackText)}</p>`;
        }
    }

    // 2. List items
    if (structured.items && structured.items.length > 0) {
        let listContent = '';
        for (const item of structured.items) {
            if (item.label.includes('SHOW_WELCOME_CARDS') || (item.detail && item.detail.includes('SHOW_WELCOME_CARDS'))) {
                continue; // Handled separately below
            }
            if (!item.label && !item.detail && !item.badge) {
                continue; // Skip entirely empty list items (prevents empty boxes)
            }

            const badgeType = getBadgeType(item.badge);
            const badgeHtml = item.badge
                ? `<span class="msme-badge msme-badge--${badgeType}">${escapeHtml(item.badge)}</span>`
                : '';
            const metaHtml = item.meta
                ? `<p class="msme-item-meta"><svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>${linkify(item.meta)}</p>`
                : '';
            listContent += `<li class="msme-item">
                <div class="msme-item-header">
                    <span class="msme-item-label">${escapeHtml(item.label)}</span>
                    ${badgeHtml}
                </div>
                <p class="msme-item-detail">${linkify(item.detail)}</p>
                ${metaHtml}
            </li>`;
        }
        if (listContent) {
            bubbleContent += '<ol class="msme-list">' + listContent + '</ol>';
        }
    }

    // 2.5 Welcome Cards
    if (structured.raw && structured.raw.includes('[SHOW_WELCOME_CARDS]')) {
        const textForLang = (structured.acknowledge || '') + ' ' + (structured.next_step || '');
        const isDevanagari = /[\u0900-\u097F]/.test(textForLang);
        const hinglishRegex = /\b(kya|hai|bata|mujhe|yaar|karo|thoda|nahi|samjhao|chahiye|kal|aaj|matlab|toh|haan|theek|bilkul|bhai|waise|bas|mil|kaisa|kaise|kyun|abhi|pehle|baad|lagao|dena|lena|hoga|karein|batao|samajh|suno|kadam)\b/i;
        const isHinglish = hinglishRegex.test(textForLang);
        
        let c1_title = "Udyam Registration";
        let c1_sub = "Registration process";
        let c2_title = "PMEGP Loan";
        let c2_sub = "Scheme details";
        let c3_title = "Grievance";
        let c3_sub = "Support & Status";
        let c4_title = "MUDRA Loan";
        let c4_sub = "Scheme details";
        let c5_title = "Search Schemes";
        let c5_sub = "Find the right scheme";

        if (isDevanagari) {
            c1_title = "उद्यम पंजीकरण"; c1_sub = "पंजीकरण प्रक्रिया";
            c2_title = "PMEGP ऋण"; c2_sub = "योजना विवरण";
            c3_title = "शिकायत"; c3_sub = "शिकायत की स्थिति";
            c4_title = "MUDRA ऋण"; c4_sub = "योजना विवरण";
            c5_title = "योजनाएं खोजें"; c5_sub = "सही योजना खोजें";
        } else if (isHinglish) {
            c1_title = "Udyam Registration"; c1_sub = "Registration Process";
            c2_title = "PMEGP Loan"; c2_sub = "Scheme Ki Jaankari";
            c3_title = "Grievance"; c3_sub = "Grievance Status";
            c4_title = "MUDRA Loan"; c4_sub = "Scheme Ki Jaankari";
            c5_title = "Schemes Dekhein"; c5_sub = "Sahi Scheme Khojein";
        }

        bubbleContent += `
            <div id="suggestions" style="margin-top: 15px; margin-bottom: 15px;">
                <div class="suggestion-card" onclick="quickSend('${c1_title}')">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">📋</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title" id="card-1-title">${c1_title}</span>
                            <span class="s-sub" id="card-1-sub">${c1_sub}</span>
                        </div>
                    </div>
                </div>
                <div class="suggestion-card" onclick="quickSend('${c2_title}')">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">🏛️</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title" id="card-2-title">${c2_title}</span>
                            <span class="s-sub" id="card-2-sub">${c2_sub}</span>
                        </div>
                    </div>
                </div>
                <div class="suggestion-card" onclick="startGrievanceFlow()">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">📝</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title" id="card-3-title">${c3_title}</span>
                            <span class="s-sub" id="card-3-sub">${c3_sub}</span>
                        </div>
                    </div>
                </div>
                <div class="suggestion-card" onclick="quickSend('${c4_title}')">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">💰</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title" id="card-4-title">${c4_title}</span>
                            <span class="s-sub" id="card-4-sub">${c4_sub}</span>
                        </div>
                    </div>
                </div>
                <div class="suggestion-card" onclick="startSchemeSearch()">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">🔍</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title" id="card-5-title">${c5_title}</span>
                            <span class="s-sub" id="card-5-sub">${c5_sub}</span>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    // 3. Disclaimer
    if (structured.disclaimer) {
        bubbleContent += `<div class="msme-disclaimer">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
            <span>${escapeHtml(structured.disclaimer)}</span>
        </div>`;
    }

    // 4. Next step
    if (structured.next_step) {
        bubbleContent += `<p class="msme-next-step">${linkify(structured.next_step)}</p>`;
    }

    const bubbleHtml = `<div class="bubble assistant">${bubbleContent}</div>`;
    row.innerHTML = avatarHtml + bubbleHtml;

    const msgsContainer = document.getElementById('messages') || chatArea;

    // 5. Action buttons (below the bubble)
    if (structured.actions && structured.actions.length > 0) {
        // Create a wrapper to hold the row and the actions below it
        const wrapper = document.createElement('div');
        wrapper.style.display = 'flex';
        wrapper.style.flexDirection = 'column';
        wrapper.style.width = '100%';
        wrapper.style.marginBottom = '24px'; // add bottom margin for the whole block

        row.style.marginBottom = '4px'; // pull bubble closer to actions
        wrapper.appendChild(row);

        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'msme-actions-row';
        // Avatar is 32px + 14px gap = 46px. Align actions with the bubble.
        actionsDiv.style.paddingLeft = '46px'; 
        
        let btnsHtml = '';
        for (const action of structured.actions) {
            const escaped = action.replace(/'/g, "\\'");
            btnsHtml += `<button class="msme-action-btn" onclick="quickSend('${escaped}')">${escapeHtml(action)}</button>`;
        }
        actionsDiv.innerHTML = `<div class="msme-actions">${btnsHtml}</div>`;
        wrapper.appendChild(actionsDiv);

        msgsContainer.appendChild(wrapper);
    } else {
        msgsContainer.appendChild(row);
    }

    scrollToBottom();
}

function getBadgeType(badgeText) {
    const text = badgeText.toLowerCase();
    if (text.includes('free') || text.includes('निःशुल्क')) return 'badge-success';
    if (text.includes('mandatory') || text.includes('अनिवार्य')) return 'badge-warning';
    return 'badge-info';
}

// ─── Grievance Flow ──────────────────────────────────────────────

function startGrievanceFlow() {
    // 1. Hide welcome, show messages (same logic as handleSend does it)
    conversationStarted = true;
    if (welcomeSection) welcomeSection.style.display = 'none';
    const msgs = document.getElementById('messages');
    if (msgs) msgs.style.display = 'flex';

    // 2. Show assistant message
    addMessage('How would you like to proceed?', 'assistant');

    // 3. Append 2-button row into #messages
    const btnRow = document.createElement('div');
    btnRow.className = 'grievance-choice-row';
    btnRow.id = 'grievance-choice-btns';
    btnRow.innerHTML = `
        <button class="grievance-choice-btn" onclick="startRegisterComplaint()">Register Complaint</button>
        <button class="grievance-choice-btn" onclick="startCheckTicket()">Check Ticket Status</button>
    `;
    const msgsContainer = document.getElementById('messages');
    msgsContainer.appendChild(btnRow);
    scrollToBottom();
}

function startRegisterComplaint() {
    // 1. Remove the 2-button row
    const btnRow = document.getElementById('grievance-choice-btns');
    if (btnRow) btnRow.remove();

    // 2. Build assistant bubble with dropdown
    const row = document.createElement('div');
    row.className = 'msg-row assistant';

    // Use the exact same avatar HTML that addMessage() uses for assistant
    row.innerHTML = `
        <div class="avatar assistant">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                <path d="M5 10h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/>
                <path d="M8 14h.01M16 14h.01"/>
            </svg>
        </div>
        <div class="bubble assistant">
            <p class="grievance-label">Select your scheme:</p>
            <select class="grievance-scheme-select" id="grievance-scheme-select">
                <option value="">-- Select Scheme --</option>
                <option value="PMEGP">PMEGP</option>
                <option value="MUDRA Loan">MUDRA Loan</option>
                <option value="Udyam Registration">Udyam Registration</option>
                <option value="CGTMSE">CGTMSE</option>
                <option value="ZED Certification">ZED Certification</option>
                <option value="GeM">GeM</option>
                <option value="TReDS">TReDS</option>
                <option value="CHAMPIONS Portal">CHAMPIONS Portal</option>
            </select>
        </div>
    `;

    const msgsContainer = document.getElementById('messages');
    msgsContainer.appendChild(row);
    scrollToBottom();

    // 3. When scheme selected, auto-fill chatInput
    document.getElementById('grievance-scheme-select').addEventListener('change', function() {
        const selected = this.value;
        if (selected) {
            chatInput.value = `Scheme : ${selected}\nQuery : `;
            chatInput.focus();
            chatInput.setSelectionRange(chatInput.value.length, chatInput.value.length);
            if (sendBtn) sendBtn.classList.add('active');
        }
    });

    // 4. Set mode flag
    window.grievanceMode = 'register';
}

function startCheckTicket() {
    // 1. Remove the 2-button row
    const btnRow = document.getElementById('grievance-choice-btns');
    if (btnRow) btnRow.remove();

    // 2. Auto-fill chatInput
    chatInput.value = 'Ticket ID : ';
    chatInput.focus();
    chatInput.setSelectionRange(chatInput.value.length, chatInput.value.length);
    if (sendBtn) sendBtn.classList.add('active');

    // 3. Set mode flag
    window.grievanceMode = 'check';
}

function addFinalGrievanceMessage() {
    const structured = {
        acknowledge: "I can help you with a variety of MSME services. Please select an option below:",
        items: [
            { label: "[SHOW_WELCOME_CARDS]", badge: "", detail: "", meta: "" }
        ],
        next_step: "Tell me what you need help with. Note: I can only guide you — visit msme.gov.in",
        actions: [],
        raw: "[SHOW_WELCOME_CARDS]"
    };
    addStructuredMessage(structured, 'assistant');
}

async function handleGrievanceSubmit() {
    const raw = chatInput.value;

    // Parse scheme name and query from the input
    const lines = raw.split('\n');
    const schemeLine = lines[0] || '';
    const queryLine  = lines[1] || '';
    const schemeName = schemeLine.replace('Scheme : ', '').trim();
    const queryText  = queryLine.replace('Query : ', '').trim();

    if (!schemeName || !queryText) {
        addMessage('Please select a scheme and enter your query.', 'assistant');
        window.grievanceMode = 'register';
        return;
    }

    // Show user message
    addMessage(raw, 'user');
    chatInput.value = '';
    if (sendBtn) sendBtn.classList.remove('active');

    // Typing indicator
    const typingId = 'typing-' + Date.now();
    const typingRow = document.createElement('div');
    typingRow.className = 'msg-row assistant';
    typingRow.id = typingId;
    typingRow.innerHTML = `
        <div class="avatar assistant">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                <path d="M5 10h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/>
                <path d="M8 14h.01M16 14h.01"/>
            </svg>
        </div>
        <div class="bubble assistant"><div class="loading-dots"><span></span><span></span><span></span></div></div>
    `;
    document.getElementById('messages').appendChild(typingRow);
    scrollToBottom();

    try {
        const response = await fetch('/api/grievance/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scheme_name: schemeName, query: queryText })
        });
        const data = await response.json();
        document.getElementById(typingId)?.remove();
        addMessage('Your complaint has been registered. Your Ticket ID is: ' + data.ticket_id + '. Please save this for future reference.', 'assistant');
        addFinalGrievanceMessage();
    } catch (err) {
        document.getElementById(typingId)?.remove();
        addMessage('Sorry, could not submit your complaint. Please try again.', 'assistant');
        addFinalGrievanceMessage();
    }
}

async function handleTicketCheck() {
    const raw = chatInput.value;
    const ticketId = raw.replace('Ticket ID : ', '').trim();

    if (!ticketId) {
        addMessage('Please enter a Ticket ID.', 'assistant');
        window.grievanceMode = 'check';
        return;
    }

    // Show user message
    addMessage(raw, 'user');
    chatInput.value = '';
    if (sendBtn) sendBtn.classList.remove('active');

    // Typing indicator
    const typingId = 'typing-' + Date.now();
    const typingRow = document.createElement('div');
    typingRow.className = 'msg-row assistant';
    typingRow.id = typingId;
    typingRow.innerHTML = `
        <div class="avatar assistant">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                <path d="M5 10h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/>
                <path d="M8 14h.01M16 14h.01"/>
            </svg>
        </div>
        <div class="bubble assistant"><div class="loading-dots"><span></span><span></span><span></span></div></div>
    `;
    document.getElementById('messages').appendChild(typingRow);
    scrollToBottom();

    try {
        const response = await fetch('/api/grievance/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticket_id: ticketId })
        });
        const data = await response.json();
        document.getElementById(typingId)?.remove();
        if (data.found === true) {
            addMessage('Processing on this Grievance , you will be updated shortly', 'assistant');
        } else {
            addMessage('mentioned ticket is not valid', 'assistant');
        }
        addFinalGrievanceMessage();
    } catch (err) {
        document.getElementById(typingId)?.remove();
        addMessage('Sorry, could not check ticket status. Please try again.', 'assistant');
        addFinalGrievanceMessage();
    }
}

// ─── Strict Language Toggle ────────────────────────────────────
function toggleLanguage() {
    currentLanguage = currentLanguage === 'hi' ? 'en' : 'hi';

    const langSpan = languageToggle.querySelector('span');
    if(langSpan) {
        langSpan.textContent = currentLanguage === 'hi' ? 'हिंदी' : 'English';
    }

    const welcomeTitle = document.getElementById('welcome-title');
    const viewTitle = document.getElementById('view-title');
    const privacyNotice = document.getElementById('privacy-notice');
    const c1t = document.getElementById('card-1-title');
    const c1s = document.getElementById('card-1-sub');
    const c2t = document.getElementById('card-2-title');
    const c2s = document.getElementById('card-2-sub');
    const c3t = document.getElementById('card-3-title');
    const c3s = document.getElementById('card-3-sub');
    const c4t = document.getElementById('card-4-title');
    const c4s = document.getElementById('card-4-sub');
    const c5t = document.getElementById('card-5-title');
    const c5s = document.getElementById('card-5-sub');

    if (currentLanguage === 'en') {
        document.title = 'MSME Saathi - Your MSME Assistant';
        if(chatInput) chatInput.placeholder = 'Type your question or ask anything...';
        if(welcomeTitle) welcomeTitle.textContent = 'How can I help you today?';
        if(viewTitle) viewTitle.textContent = 'Home';
        if(privacyNotice) privacyNotice.textContent = 'All conversations are confidential and secure';
        
        if(c1t) c1t.textContent = 'Udyam Registration';
        if(c1s) c1s.textContent = 'Registration process';
        
        if(c2t) c2t.textContent = 'PMEGP Loan';
        if(c2s) c2s.textContent = 'Scheme details';
        
        if(c3t) c3t.textContent = 'File Grievance';
        if(c3s) c3s.textContent = 'Register complaint';
        
        if(c4t) c4t.textContent = 'MUDRA Loan';
        if(c4s) c4s.textContent = 'Scheme details';
        
        if(c5t) c5t.textContent = 'Search Schemes';
        if(c5s) c5s.textContent = 'Find the right scheme';
    } else {
        document.title = 'एमएसएमई साथी';
        if(chatInput) chatInput.placeholder = 'अपना सवाल लिखें...';
        if(welcomeTitle) welcomeTitle.textContent = 'मैं आज आपकी कैसे मदद कर सकता हूँ?';
        if(viewTitle) viewTitle.textContent = 'होम';
        if(privacyNotice) privacyNotice.textContent = 'सभी बातचीत गोपनीय और सुरक्षित हैं';
        
        if(c1t) c1t.textContent = 'उद्यम रजिस्ट्रेशन';
        if(c1s) c1s.textContent = 'पंजीकरण प्रक्रिया';
        
        if(c2t) c2t.textContent = 'PMEGP लोन';
        if(c2s) c2s.textContent = 'योजना विवरण';
        
        if(c3t) c3t.textContent = 'शिकायत दर्ज करें';
        if(c3s) c3s.textContent = 'शिकायत पंजीकृत करें';
        
        if(c4t) c4t.textContent = 'MUDRA लोन';
        if(c4s) c4s.textContent = 'योजना विवरण';
        
        if(c5t) c5t.textContent = 'योजना खोजें';
        if(c5s) c5s.textContent = 'सही योजना खोजें';
    }

    if (recognition) {
        recognition.lang = currentLanguage === 'hi' ? 'hi-IN' : 'en-IN';
    }
}

// ─── Theme Toggle ──────────────────────────────────────────────
function toggleTheme() {
    const body = document.body;
    body.classList.toggle('light');
    
    const themeIconSvg = document.querySelector('#theme-toggle svg');
    if(themeIconSvg) {
        if(body.classList.contains('light')) {
            themeIconSvg.innerHTML = '<path id="theme-toggle-icon" d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />';
        } else {
            themeIconSvg.innerHTML = '<circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />';
        }
    }
}

window.quickSend = function(text) {
    if(chatInput) {
        chatInput.value = text;
        if(sendBtn) sendBtn.classList.add('active');
        handleSend(false);
    }
};

// ─── Search Schemes Flow ───────────────────────────────────────
function startSchemeSearch() {
    conversationStarted = true;
    const msgsContainer = document.getElementById('messages');
    if (msgsContainer) msgsContainer.style.display = 'flex';
    if (welcomeSection) welcomeSection.style.display = 'none';

    // Build the assistant bubble with the form
    const row = document.createElement('div');
    row.className = 'msg-row assistant';
    row.id = 'ss-form-row';

    row.innerHTML = `
        <div class="avatar assistant">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                <path d="M5 10h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/>
                <path d="M8 14h.01M16 14h.01"/>
            </svg>
        </div>
        <div class="bubble assistant" style="width: 100%; max-width: 450px;">
            <p class="grievance-label">Please fill in the following details so I can find all schemes that apply to you:</p>
            
            <label class="grievance-label" style="display:block; margin-top:8px;">Are you a Student or Entrepreneur/Business Owner :</label>
            <select class="grievance-scheme-select" id="ss-role">
                <option value="">-- Select --</option>
                <option value="Student">Student</option>
                <option value="Entrepreneur">Entrepreneur</option>
                <option value="Business Owner">Business Owner</option>
            </select>

            <label class="grievance-label" style="display:block; margin-top:8px;">State of Residence :</label>
            <input type="text" class="grievance-scheme-select" id="ss-state" placeholder="e.g. Bihar">

            <label class="grievance-label" style="display:block; margin-top:8px;">Gender :</label>
            <select class="grievance-scheme-select" id="ss-gender">
                <option value="">-- Select --</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
            </select>

            <label class="grievance-label" style="display:block; margin-top:8px;">Social Category (General / SC / ST / OBC / EBC / Minority / PwD) :</label>
            <select class="grievance-scheme-select" id="ss-social">
                <option value="">-- Select --</option>
                <option value="General">General</option>
                <option value="SC">SC</option>
                <option value="ST">ST</option>
                <option value="OBC">OBC</option>
                <option value="EBC">EBC</option>
                <option value="Minority">Minority</option>
                <option value="PwD">PwD</option>
            </select>

            <label class="grievance-label" style="display:block; margin-top:8px;">Is your business/venture new or existing :</label>
            <select class="grievance-scheme-select" id="ss-new-existing">
                <option value="">-- Select --</option>
                <option value="New">New</option>
                <option value="Existing">Existing</option>
            </select>

            <label class="grievance-label" style="display:block; margin-top:8px;">Business Type (Manufacturing / Agro / Tech-Innovation / Service / Other) :</label>
            <select class="grievance-scheme-select" id="ss-biz-type">
                <option value="">-- Select --</option>
                <option value="Manufacturing">Manufacturing</option>
                <option value="Agro">Agro</option>
                <option value="Tech-Innovation">Tech-Innovation</option>
                <option value="Service">Service</option>
                <option value="Other">Other</option>
            </select>

            <button class="grievance-choice-btn" style="margin-top: 16px; width: 100%;" onclick="submitSchemeSearchForm()">Submit</button>
        </div>
    `;

    msgsContainer.appendChild(row);
    scrollToBottom();
}

window.submitSchemeSearchForm = function() {
    const role = document.getElementById('ss-role').value;
    const state = document.getElementById('ss-state').value;
    const gender = document.getElementById('ss-gender').value;
    const social = document.getElementById('ss-social').value;
    const newEx = document.getElementById('ss-new-existing').value;
    const bizType = document.getElementById('ss-biz-type').value;

    if (!role || !state || !gender || !social || !newEx || !bizType) {
        alert('Please fill in all fields before submitting.');
        return;
    }

    const payloadText = [
        `Are you a Student or Entrepreneur/Business Owner : ${role}`,
        `State of Residence : ${state}`,
        `Gender : ${gender}`,
        `Social Category (General / SC / ST / OBC / EBC / Minority / PwD) : ${social}`,
        `Is your business/venture new or existing : ${newEx}`,
        `Business Type (Manufacturing / Agro / Tech-Innovation / Service / Other) : ${bizType}`
    ].join('  \n');

    // Remove the form from UI
    const formRow = document.getElementById('ss-form-row');
    if (formRow) formRow.remove();

    chatInput.value = payloadText;
    handleSend(false);
};

// ─── STT Integration ───────────────────────────────────────────
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn('Speech Recognition API not supported in this browser.');
        if(voiceBtn) voiceBtn.style.display = 'none';
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = currentLanguage === 'hi' ? 'hi-IN' : 'en-IN';

    recognition.onstart = function () {
        isRecording = true;
        if(voiceBtn) voiceBtn.style.color = 'var(--color-primary)';
        if(chatInput) chatInput.placeholder = currentLanguage === 'hi' ? 'सुन रहा हूँ...' : 'Listening...';
    };

    recognition.onresult = function (event) {
        const transcript = event.results[0][0].transcript;
        if(chatInput) chatInput.value = transcript;
        handleSend(true);
    };

    recognition.onerror = function (event) {
        console.error('Speech recognition error:', event.error);
        stopRecording();
    };

    recognition.onend = function () {
        stopRecording();
    };
}

function toggleVoiceRecording() {
    if (!recognition) return;
    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

function stopRecording() {
    isRecording = false;
    if(voiceBtn) voiceBtn.style.color = 'var(--text-muted)';
    if(chatInput) chatInput.placeholder = currentLanguage === 'hi' ? 'अपना सवाल लिखें...' : 'Type your question...';
}

function scrollToBottom() {
    const chatContainer = $('chat-area');
    if(chatContainer) {
        requestAnimationFrame(() => {
            chatContainer.scrollTo({
                top: chatContainer.scrollHeight,
                behavior: 'smooth',
            });
        });
    }
}

// Initialize on DOM Load
document.addEventListener('DOMContentLoaded', initApp);

