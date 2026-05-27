
// ─── Core State ────────────────────────────────────────────────
let sessionId = generateUUID();
let currentLanguage = 'en'; // Changed default to 'en' based on target design

function getPrivacyNoticeText() {
    const lang = currentLanguage || 'en';
    if (lang === 'hi' || lang === 'bho' || lang === 'mai') {
        return "यह चैटबॉट आपकी शिकायतों को हल करने में मदद करने के लिए उन्हें संग्रहीत करता है। कोई व्यक्तिगत डेटा तृतीय पक्षों के साथ साझा नहीं किया जाता है।";
    } else if (lang === 'ben') {
        return "এই চ্যাটবটটি আপনার অভিযোগগুলি সমাধান করতে সহায়তা করার জন্য সংরক্ষণ করে। কোনও ব্যক্তিগত তথ্য তৃতীয় পক্ষের সাথে ভাগ করা হয় না।";
    } else {
        return "This chatbot stores your grievances to help resolve them. No personal data is shared with third parties.";
    }
}
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
    
    const langSelect = $('lang-select');
    if (langSelect) {
        langSelect.addEventListener('change', (e) => {
            window.changeLanguage(e.target.value);
        });
        currentLanguage = langSelect.value || 'en';
    }
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
            isVoiceMode: isVoice,
            language: currentLanguage
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

        if (data.language && data.language !== currentLanguage) {
            window.changeLanguage(data.language);
        }

        if (data.structured && (data.structured.items?.length > 0 || data.structured.acknowledge || data.structured.dynamic_form)) {
            addStructuredMessage(data.structured, 'assistant', data.reply);
        } else {
            addMessage(data.reply || data.structured?.raw || 'Error', 'assistant');
        }
    } catch (error) {
        console.error('Chat Error:', error);
        const el = document.getElementById(typingId);
        if(el) el.remove();
        addMessage((currentLanguage === 'hi' || currentLanguage === 'bho' || currentLanguage === 'mai') ? 'सर्वर त्रुटि। कृपया बाद में प्रयास करें।' : 
                   (currentLanguage === 'ben') ? 'সার্ভার ত্রুটি। অনুগ্রহ করে পরে চেষ্টা করুন।' :
                   'Server error. Please try again later.', 'assistant');
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
    if (!text) return '';
    let cleanedText = text;
    // Strip [PRIVACY NOTICE] or translated labels from the start
    const privacyTagRegex = /^\[(PRIVACY NOTICE|सहमति सूचना|গোপনীয়তা বিজ্ঞপ্তি)\]\s*/i;
    cleanedText = cleanedText.replace(privacyTagRegex, '');

    if (typeof marked !== 'undefined') {
        return marked.parse(cleanedText);
    }
    let html = escapeHtml(cleanedText);
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
    const urlRegex = /(https?:\/\/[^\s]+|[a-z0-9.-]+\.(?:gov\.in|org\.in|nic\.in|org|com|in)\b(?:\/[^\s]*)?)/gi;
    html = html.replace(urlRegex, function(url) {
        let trailing = '';
        const matchTrailing = url.match(/[.,;:?]+$/);
        if (matchTrailing) {
            trailing = matchTrailing[0];
            url = url.substring(0, url.length - trailing.length);
        }
        let href = url;
        if (!/^https?:\/\//i.test(href)) {
            href = 'https://' + href;
        }
        return `<a href="${href}" target="_blank" rel="noopener">${url}</a>` + trailing;
    });
    return html;
}

// ─── Structured Response Renderer ──────────────────────────────
function addStructuredMessage(structured, sender, replyText = '') {
    // Fallback if structure is broken
    if (!structured || (!structured.acknowledge && !structured.items?.length && !structured.disclaimer && !structured.actions?.length && !structured.dynamic_form)) {
        addMessage(structured?.raw || replyText || 'Error', sender);
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

    // Render replyText (main conversational message) or structured.acknowledge
    let ackText = '';
    if (replyText) {
        // Extract only the introduction text before the first structural tag
        const tagRegex = /(\*\*\[[^\]]+\]\*\*|\[[^\]]+\])/g;
        const parts = replyText.split(tagRegex);
        ackText = parts[0].trim();
    } else if (structured.acknowledge) {
        ackText = structured.acknowledge;
    }

    if (ackText) {
        let cleanAck = ackText.replace(/\*\*\[LIST\]\*\*/g, '').replace(/\[LIST\]/g, '').replace(/\[SHOW_WELCOME_CARDS\]/g, '').replace(/\[GENERATE_TICKET\]/g, '').trim();
        if (cleanAck) {
            bubbleContent += `<p class="msme-ack">${linkify(cleanAck)}</p>`;
        }
    }

    // 2. List items
    if (structured.items && structured.items.length > 0) {
        let listContent = '';
        for (const item of structured.items) {
            if (item.label.includes('SHOW_WELCOME_CARDS') || (item.detail && item.detail.includes('SHOW_WELCOME_CARDS'))) {
                continue;
            }
            if (!item.label && !item.detail && !item.badge) {
                continue;
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
        const textForLang = replyText || (structured.acknowledge || '') + ' ' + (structured.next_step || '');
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

        const lang = currentLanguage || 'en';
        if (lang === 'hi') {
            c1_title = "उद्यम पंजीकरण"; c1_sub = "पंजीकरण प्रक्रिया";
            c2_title = "PMEGP ऋण"; c2_sub = "योजना विवरण";
            c3_title = "शिकायत"; c3_sub = "शिकायत की स्थिति";
            c4_title = "MUDRA ऋण"; c4_sub = "योजना विवरण";
            c5_title = "योजनाएं खोजें"; c5_sub = "सही योजना खोजें";
        } else if (lang === 'bho') {
            c1_title = "उद्यम पंजीकरण"; c1_sub = "पंजीकरण प्रक्रिया";
            c2_title = "PMEGP ऋण"; c2_sub = "योजना विवरण";
            c3_title = "शिकायत"; c3_sub = "शिकायत की स्थिति";
            c4_title = "MUDRA ऋण"; c4_sub = "योजना विवरण";
            c5_title = "योजनाएं खोजीं"; c5_sub = "सही योजना खोजीं";
        } else if (lang === 'mai') {
            c1_title = "उद्यम पंजीकरण"; c1_sub = "पंजीकरण प्रक्रिया";
            c2_title = "PMEGP ऋण"; c2_sub = "योजना विवरण";
            c3_title = "शिकायत"; c3_sub = "शिकायत की स्थिति";
            c4_title = "MUDRA ऋण"; c4_sub = "योजना विवरण";
            c5_title = "योजनाएं खोजू"; c5_sub = "सही योजना खोजू";
        } else if (lang === 'ben') {
            c1_title = "উদ্যম নিবন্ধন"; c1_sub = "নিবন্ধন প্রক্রিয়া";
            c2_title = "PMEGP ঋণ"; c2_sub = "প্রকল্পের বিবরণ";
            c3_title = "অভিযোগ"; c3_sub = "অভিযোগের স্থিতি";
            c4_title = "MUDRA ঋণ"; c4_sub = "প্রকল্পের বিবরণ";
            c5_title = "প্রকল্প অনুসন্ধান"; c5_sub = "সঠিক প্রকল্প খুঁজুন";
        } else if (lang === 'en') {
            // keep English defaults
        } else {
            // Fallback script detection if lang is unexpected
            const isBengaliScript = /[\u0980-\u09FF]/.test(textForLang);
            if (isBengaliScript) {
                c1_title = "উদ্যম নিবন্ধন"; c1_sub = "নিবন্ধন প্রক্রিয়া";
                c2_title = "PMEGP ঋণ"; c2_sub = "প্রকল্পের বিবরণ";
                c3_title = "অভিযোগ"; c3_sub = "অভিযোগের স্থিতি";
                c4_title = "MUDRA ঋণ"; c4_sub = "প্রকল্পের বিবরণ";
                c5_title = "প্রকল্প অনুসন্ধান"; c5_sub = "সঠিক প্রকল্প খুঁজুন";
            } else if (isDevanagari) {
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
        }

        bubbleContent += `
            <div id="suggestions" style="margin-top: 15px; margin-bottom: 15px;">
                <div class="suggestion-card" onclick="quickSend('${c1_title}')">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">📋</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title">${c1_title}</span>
                            <span class="s-sub">${c1_sub}</span>
                        </div>
                    </div>
                </div>
                <div class="suggestion-card" onclick="quickSend('${c2_title}')">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">🏛️</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title">${c2_title}</span>
                            <span class="s-sub">${c2_sub}</span>
                        </div>
                    </div>
                </div>
                <div class="suggestion-card" onclick="startGrievanceFlow()">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">📝</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title">${c3_title}</span>
                            <span class="s-sub">${c3_sub}</span>
                        </div>
                    </div>
                </div>
                <div class="suggestion-card" onclick="quickSend('${c4_title}')">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">💰</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title">${c4_title}</span>
                            <span class="s-sub">${c4_sub}</span>
                        </div>
                    </div>
                </div>
                <div class="suggestion-card" onclick="startSchemeSearch()">
                    <div class="suggestion-card-header">
                        <div class="suggestion-card-icon-container" style="background:transparent; padding:0; justify-content:flex-start;">
                            <span style="font-size: 28px;">🔍</span>
                        </div>
                        <div class="suggestion-card-titles">
                            <span class="s-title">${c5_title}</span>
                            <span class="s-sub">${c5_sub}</span>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    // 2.7 Dynamic Grievance Form
    if (structured.dynamic_form) {
        const formId = 'dyn-form-' + Date.now();
        let formFieldsHtml = '';
        
        structured.dynamic_form.fields.forEach(field => {
            if (field.type === 'select') {
                let optionsHtml = '<option value="">-- Select --</option>';
                field.options.forEach(opt => {
                    const val = typeof opt === 'object' ? opt.value : opt;
                    const label = typeof opt === 'object' ? opt.label : opt;
                    const isSelected = (val === field.value) ? 'selected' : '';
                    optionsHtml += `<option value="${escapeHtml(val)}" ${isSelected}>${escapeHtml(label)}</option>`;
                });
                formFieldsHtml += `
                    <label class="grievance-label" style="display:block; margin-top:8px;">${escapeHtml(field.label)} :</label>
                    <select class="grievance-scheme-select" id="${formId}-${field.name}">
                        ${optionsHtml}
                    </select>
                `;
            } else if (field.type === 'number') {
                const valAttr = field.value !== undefined && field.value !== null && field.value !== '' ? `value="${escapeHtml(String(field.value))}"` : '';
                formFieldsHtml += `
                    <label class="grievance-label" style="display:block; margin-top:8px;">${escapeHtml(field.label)} :</label>
                    <input type="number" class="grievance-scheme-select" id="${formId}-${field.name}" placeholder="${escapeHtml(field.placeholder || '')}" ${valAttr}>
                `;
            } else {
                const valAttr = field.value !== undefined && field.value !== null && field.value !== '' ? `value="${escapeHtml(String(field.value))}"` : '';
                formFieldsHtml += `
                    <label class="grievance-label" style="display:block; margin-top:8px;">${escapeHtml(field.label)} :</label>
                    <input type="text" class="grievance-scheme-select" id="${formId}-${field.name}" placeholder="${escapeHtml(field.placeholder || '')}" ${valAttr}>
                `;
            }
        });

        const escapedData = JSON.stringify(structured.dynamic_form).replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
        const submitLabel = currentLanguage === 'hi' ? 'शिकायत दर्ज करें' : 
                            currentLanguage === 'ben' ? 'অভিযোগ জমা দিন' : 
                            'Submit Complaint';
        
        bubbleContent += `
            <div class="dynamic-grievance-form-container" id="${formId}" style="margin-top:10px; border-top:1px solid rgba(123, 142, 175, 0.15); padding-top:10px;">
                ${formFieldsHtml}
                <button class="grievance-choice-btn" style="margin-top:16px; width:100%;" onclick="submitDynamicGrievanceForm('${formId}', '${escapedData}')">${submitLabel}</button>
            </div>
        `;
    }

    // 3. Disclaimer
    if (structured.disclaimer) {
        const text = structured.disclaimer;
        
        // Helper function to split warning/disclaimer text from "Note:" points
        const splitDisclaimerAndNote = (t) => {
            if (!t) return { warning: '', note: '' };
            const noteRegex = /(Note:|नोट:|विशेष দ্রষ্টব্য:)/i;
            const parts = t.split(noteRegex);
            if (parts.length >= 3) {
                let warning = parts[0].trim();
                // Strip raw markdown blockquote '>' and info icons 'ⓘ'
                warning = warning.replace(/^>\s*ⓘ?\s*/, '').trim();
                const note = (parts[1] + parts[2]).trim();
                return { warning, note };
            }
            let warning = t.trim().replace(/^>\s*ⓘ?\s*/, '').trim();
            return { warning, note: '' };
        };

        const privacyRegex = /^\[([^\]]+)\]\s*([\s\S]+?)(?=\n\n|\r?\n\r?\n|$)/i;
        const match = text.match(privacyRegex);
        
        let mainText = '';
        let noteText = '';
        
        if (match) {
            const privacyNoticeText = match[2].trim();
            let remainingDisclaimer = text.replace(match[0], '').trim();
            
            // Clean remainingDisclaimer: strip any [DISCLAIMER] tag if present
            remainingDisclaimer = remainingDisclaimer.replace(/^\[(DISCLAIMER|अस्वीकरण|অস্বীকৃতি)\]\s*/i, '');
            remainingDisclaimer = remainingDisclaimer.replace(/^\*\*\[(DISCLAIMER|अस्वीकरण|অস্বীকৃতি)\]\*\*\s*/i, '');
            
            const parsedRem = splitDisclaimerAndNote(remainingDisclaimer);
            mainText = privacyNoticeText;
            if (parsedRem.warning) {
                mainText += "\n\n" + parsedRem.warning;
            }
            noteText = parsedRem.note;
        } else {
            let cleanedDisclaimer = text;
            cleanedDisclaimer = cleanedDisclaimer.replace(/^\[(DISCLAIMER|अस्वीकरण|অস্বীকৃতি)\]\s*/i, '');
            cleanedDisclaimer = cleanedDisclaimer.replace(/^\*\*\[(DISCLAIMER|अस्वीकरण|অস্বীকৃতি)\]\*\*\s*/i, '');
            
            const parsed = splitDisclaimerAndNote(cleanedDisclaimer);
            mainText = parsed.warning;
            noteText = parsed.note;
        }

        bubbleContent += `
            <div class="msme-disclaimer" style="display: flex; align-items: flex-start; gap: 8px;">
                <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
                <div class="msme-disclaimer-content" style="display: flex; flex-direction: column; gap: 6px; width: 100%;">
                    ${mainText ? `<span class="privacy-text" style="color: var(--text-primary); font-weight: 500; display: block;">${linkify(mainText)}</span>` : ''}
                    ${noteText ? `<span class="note-text" style="display: block; ${mainText ? 'border-top: 1px solid rgba(123, 142, 175, 0.15); margin-top: 4px; padding-top: 4px;' : ''} color: var(--text-secondary); font-size: 11px;">${linkify(noteText)}</span>` : ''}
                </div>
            </div>
        `;
    }

    // 4. Next step
    if (structured.next_step) {
        let cleanNextStep = structured.next_step.replace(/\[GENERATE_TICKET\]/g, '').replace(/\[SHOW_WELCOME_CARDS\]/g, '').trim();
        if (cleanNextStep) {
            bubbleContent += `<p class="msme-next-step">${linkify(cleanNextStep)}</p>`;
        }
    }

    const bubbleHtml = `<div class="bubble assistant">${bubbleContent}</div>`;
    row.innerHTML = avatarHtml + bubbleHtml;

    const msgsContainer = document.getElementById('messages') || chatArea;

    // 5. Action buttons (below the bubble)
    if (structured.actions && structured.actions.length > 0) {
        const wrapper = document.createElement('div');
        wrapper.style.display = 'flex';
        wrapper.style.flexDirection = 'column';
        wrapper.style.width = '100%';
        wrapper.style.marginBottom = '24px';

        row.style.marginBottom = '4px';
        wrapper.appendChild(row);

        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'msme-actions-row';
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

    const lang = currentLanguage || 'en';
    const isHi = (lang === 'hi' || lang === 'bho' || lang === 'mai');
    const isBen = (lang === 'ben');

    const promptText = isHi ? 'आप आगे कैसे बढ़ना चाहेंगे?' :
                       isBen ? 'আপনি কীভাবে এগিয়ে যেতে চান?' :
                       'How would you like to proceed?';
    
    const registerLabel = isHi ? 'शिकायत दर्ज करें' :
                          isBen ? 'অভিযোগ নথিভুক্ত করুন' :
                          'Register Complaint';

    const checkLabel = isHi ? 'टिकट की स्थिति जांचें' :
                       isBen ? 'টিকিটের স্থিতি পরীক্ষা করুন' :
                       'Check Ticket Status';

    // 2. Show assistant message
    addMessage(promptText, 'assistant');

    // 3. Append 2-button row into #messages
    const btnRow = document.createElement('div');
    btnRow.className = 'grievance-choice-row';
    btnRow.id = 'grievance-choice-btns';
    btnRow.innerHTML = `
        <button class="grievance-choice-btn" onclick="startRegisterComplaint()">${registerLabel}</button>
        <button class="grievance-choice-btn" onclick="startCheckTicket()">${checkLabel}</button>
    `;
    const msgsContainer = document.getElementById('messages');
    msgsContainer.appendChild(btnRow);
    scrollToBottom();
}

function startRegisterComplaint() {
    // 1. Remove the 2-button row
    const btnRow = document.getElementById('grievance-choice-btns');
    if (btnRow) btnRow.remove();

    // 2. Build assistant bubble with the full grievance form directly
    const row = document.createElement('div');
    row.className = 'msg-row assistant';
    
    const formId = 'dyn-form-' + Date.now();
    
    const lang = currentLanguage || 'en';
    const isHi = (lang === 'hi' || lang === 'bho' || lang === 'mai');
    const isBen = (lang === 'ben');

    // Localization strings
    const labels = {
        title: isHi ? 'अपनी शिकायत दर्ज करने के लिए कृपया नीचे विवरण भरें:' : 
               isBen ? 'আপনার অভিযোগ নথিভুক্ত করতে অনুগ্রহ করে নিচে বিবরণ লিখুন:' : 
               'Please fill in the grievance details below to register your complaint:',
        scheme: isHi ? 'संबंधित सरकारी योजना * :' : 
                isBen ? 'সংশ্লিষ্ট সরকারি প্রকল্প * :' : 
                'Associated Government Scheme * :',
        selectScheme: isHi ? '-- योजना चुनें --' : 
                      isBen ? '-- প্রকল্প নির্বাচন করুন --' : 
                      '-- Select Scheme --',
        category: isHi ? 'शिकायत की श्रेणी * :' : 
                  isBen ? 'অভিযোগের বিভাগ * :' : 
                  'Grievance Category * :',
        selectCategory: isHi ? '-- श्रेणी चुनें --' : 
                        isBen ? '-- বিভাগ নির্বাচন করুন --' : 
                        '-- Select Category --',
        bank: isHi ? 'संबंधित बैंक का नाम (यदि लागू हो) :' : 
              isBen ? 'সংশ্লিষ্ট ব্যাংকের নাম (যদি প্রযোজ্য হয়) :' : 
              'Involved Bank Name (if applicable) :',
        amount: isHi ? 'शामिल राशि (यदि लागू हो) :' : 
                isBen ? 'জড়িত অর্থ বা পরিমাণ (যদি প্রযোজ্য হয়) :' : 
                'Amount Involved (if applicable) :',
        delay: isHi ? 'देरी की अवधि (दिनों में, यदि लागू हो) :' : 
               isBen ? 'বিলম্বের সময়কাল (দিনে, যদি প্রযোজ্য হয়) :' : 
               'Duration of Delay (in days, if applicable) :',
        bankPlaceholder: isHi ? 'जैसे - भारतीय स्टेट बैंक' :
                         isBen ? 'যেমন - স্টেট ব্যাঙ্ক অফ ইন্ডিয়া' :
                         'e.g. State Bank of India',
        amountPlaceholder: isHi ? 'जैसे - 10 लाख' :
                           isBen ? 'যেমন - ১০ লক্ষ' :
                           'e.g. 10 Lakhs',
        delayPlaceholder: isHi ? 'जैसे - 45' :
                          isBen ? 'যেমন - ৪৫' :
                          'e.g. 45',
        contactNumber: isHi ? 'भारतीय संपर्क नंबर * :' :
                       isBen ? 'भारतीय যোগাযোগের নম্বর * :' :
                       'Indian Contact Number * :',
        contactNumberPlaceholder: isHi ? 'जैसे - 9876543210' :
                                   isBen ? 'যেমন - 9876543210' :
                                   'e.g. 9876543210',
        desc: isHi ? 'शिकायत का विवरण * :' : 
              isBen ? 'অভিযোগের বিবরণ * :' : 
              'Description of Grievance * :',
        descPlaceholder: isHi ? 'कृपया अपनी शिकायत का विस्तार से वर्णन करें...' : 
                         isBen ? 'অনুগ্রহ করে আপনার অভিযোগটি বিস্তারিতভাবে বর্ণনা করুন...' : 
                         'Please describe your grievance in detail...',
        submit: isHi ? 'शिकायत दर्ज करें' : 
                isBen ? 'অভিযোগ জমা দিন' : 
                'Submit Complaint'
    };

    const categories = [
        { val: 'Loan Delay', label: isHi ? 'ऋण में देरी' : isBen ? 'ঋণ পেতে বিলম্ব' : 'Loan Delay' },
        { val: 'Rejection', label: isHi ? 'अस्वीकृति' : isBen ? 'প্রত্যাখ্যান' : 'Rejection' },
        { val: 'Portal Error', label: isHi ? 'पोर्टल त्रुटि' : isBen ? 'পোর্টাল ত্রুটি' : 'Portal Error' },
        { val: 'Documentation Issue', label: isHi ? 'दस्तावेज़ संबंधी समस्या' : isBen ? 'নথিপত্র সংক্রান্ত সমস্যা' : 'Documentation Issue' },
        { val: 'Harassment', label: isHi ? 'उत्पीड़न' : isBen ? 'হয়রানি' : 'Harassment' },
        { val: 'Other', label: isHi ? 'अन्य' : isBen ? 'অন্যান্য' : 'Other' }
    ];

    const schemes = [
        { val: 'PMEGP', label: 'PMEGP' },
        { val: 'MUDRA Loan', label: isHi ? 'मुद्रा ऋण (MUDRA Loan)' : isBen ? 'মুদ্রা ঋণ (MUDRA Loan)' : 'MUDRA Loan' },
        { val: 'Udyam Registration', label: isHi ? 'उद्यम पंजीकरण (Udyam)' : isBen ? 'উদ্যম নিবন্ধন (Udyam)' : 'Udyam Registration' },
        { val: 'CGTMSE', label: 'CGTMSE' },
        { val: 'PM SVANidhi', label: 'PM SVANidhi' },
        { val: 'ZED Certification', label: 'ZED Certification' },
        { val: 'GeM Portal', label: 'GeM Portal' },
        { val: 'TReDS', label: 'TReDS' },
        { val: 'Champions Portal', label: 'Champions Portal' },
        { val: 'Other', label: isHi ? 'अन्य' : isBen ? 'অন্যান্য' : 'Other' }
    ];

    let schemeOptions = `<option value="">${labels.selectScheme}</option>`;
    schemes.forEach(s => {
        schemeOptions += `<option value="${escapeHtml(s.val)}">${escapeHtml(s.label)}</option>`;
    });

    let catOptions = `<option value="">${labels.selectCategory}</option>`;
    categories.forEach(c => {
        catOptions += `<option value="${escapeHtml(c.val)}">${escapeHtml(c.label)}</option>`;
    });

    row.innerHTML = `
        <div class="avatar assistant">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                <path d="M5 10h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/>
                <path d="M8 14h.01M16 14h.01"/>
            </svg>
        </div>
        <div class="bubble assistant">
            <p class="grievance-label" style="font-weight: 600; margin-bottom: 12px; color: var(--text-primary);">${labels.title}</p>
            <div class="dynamic-grievance-form-container" id="${formId}">
                <label class="grievance-label" style="display:block; margin-top:8px;">${labels.scheme}</label>
                <select class="grievance-scheme-select" id="${formId}-scheme_name">
                    ${schemeOptions}
                </select>

                <label class="grievance-label" style="display:block; margin-top:8px;">${labels.category}</label>
                <select class="grievance-scheme-select" id="${formId}-grievance_type">
                    ${catOptions}
                </select>

                <label class="grievance-label" style="display:block; margin-top:8px;">${labels.bank}</label>
                <input type="text" class="grievance-scheme-select" id="${formId}-entity_bank" placeholder="${escapeHtml(labels.bankPlaceholder)}">

                <label class="grievance-label" style="display:block; margin-top:8px;">${labels.amount}</label>
                <input type="text" class="grievance-scheme-select" id="${formId}-entity_amount" placeholder="${escapeHtml(labels.amountPlaceholder)}">

                <label class="grievance-label" style="display:block; margin-top:8px;">${labels.delay}</label>
                <input type="number" class="grievance-scheme-select" id="${formId}-entity_duration_days" placeholder="${escapeHtml(labels.delayPlaceholder)}">

                <label class="grievance-label" style="display:block; margin-top:8px;">${labels.contactNumber}</label>
                <input type="text" class="grievance-scheme-select" id="${formId}-contact_number" placeholder="${escapeHtml(labels.contactNumberPlaceholder)}">

                <label class="grievance-label" style="display:block; margin-top:8px;">${labels.desc}</label>
                <textarea class="grievance-scheme-select" id="${formId}-raw_text" placeholder="${escapeHtml(labels.descPlaceholder)}" style="min-height: 80px; font-family: inherit; resize: vertical; padding: 8px; box-sizing: border-box;"></textarea>

                <button class="grievance-choice-btn" style="margin-top: 16px; width: 100%;" onclick="submitDirectGrievanceForm('${formId}')">${labels.submit}</button>
            </div>
        </div>
    `;

    const msgsContainer = document.getElementById('messages');
    msgsContainer.appendChild(row);
    scrollToBottom();
}

function startCheckTicket() {
    // 1. Remove the 2-button row
    const btnRow = document.getElementById('grievance-choice-btns');
    if (btnRow) btnRow.remove();

    const lang = currentLanguage || 'en';
    const isHi = (lang === 'hi' || lang === 'bho' || lang === 'mai');
    const isBen = (lang === 'ben');

    const ticketPrefix = isHi ? 'टिकट आईडी : ' :
                         isBen ? 'টিকিট আইডি : ' :
                         'Ticket ID : ';

    // 2. Auto-fill chatInput
    chatInput.value = ticketPrefix;
    chatInput.focus();
    chatInput.setSelectionRange(chatInput.value.length, chatInput.value.length);
    if (sendBtn) sendBtn.classList.add('active');

    // 3. Set mode flag
    window.grievanceMode = 'check';
}

function addFinalGrievanceMessage() {
    const lang = currentLanguage || 'en';
    const isHi = (lang === 'hi' || lang === 'bho' || lang === 'mai');
    const isBen = (lang === 'ben');

    const ackText = isHi ? 'मैं आपकी विभिन्न एमएसएमई सेवाओं में मदद कर सकता हूँ। कृपया नीचे एक विकल्प चुनें:' :
                    isBen ? 'আমি আপনাকে বিভিন্ন এমএসএমই পরিষেবাগুলিতে সহায়তা করতে পারি। অনুগ্রহ করে নিচের একটি বিকল্প বেছে নিন:' :
                    'I can help you with a variety of MSME services. Please select an option below:';

    const nextStepText = isHi ? 'मुझे बताएं कि आपको किस बारे में सहायता चाहिए। नोट: मैं केवल आपका मार्गदर्शन कर सकता हूँ — msme.gov.in पर जाएं' :
                         isBen ? 'আপনার কী বিষয়ে সাহায্য প্রয়োজন তা আমাকে জানান। দ্রষ্টব্য: আমি আপনাকে কেবল গাইড করতে পারি — msme.gov.in-এ যান' :
                         'Tell me what you need help with. Note: I can only guide you — visit msme.gov.in';

    const structured = {
        acknowledge: ackText,
        items: [
            { label: "[SHOW_WELCOME_CARDS]", badge: "", detail: "", meta: "" }
        ],
        next_step: nextStepText,
        actions: [],
        raw: "[SHOW_WELCOME_CARDS]"
    };
    addStructuredMessage(structured, 'assistant');
}

async function handleGrievanceSubmit() {
    const raw = chatInput.value;

    const lang = currentLanguage || 'en';
    const isHi = (lang === 'hi' || lang === 'bho' || lang === 'mai');
    const isBen = (lang === 'ben');

    // Parse scheme name and query from the input
    const lines = raw.split('\n');
    const schemeLine = lines[0] || '';
    const queryLine  = lines[1] || '';
    const schemeName = schemeLine.replace('Scheme : ', '').trim();
    const queryText  = queryLine.replace('Query : ', '').trim();

    if (!schemeName || !queryText) {
        const errorMsg = isHi ? 'कृपया एक योजना चुनें और अपनी शिकायत दर्ज करें।' :
                          isBen ? 'অনুগ্রহ করে একটি প্রকল্প নির্বাচন করুন এবং আপনার অনুসন্ধানটি লিখুন।' :
                          'Please select a scheme and enter your query.';
        addMessage(errorMsg, 'assistant');
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
        
        const successMsg = isHi ? `आपकी शिकायत दर्ज कर ली गई है। आपका टिकट आईडी है: ${data.ticket_id}। कृपया इसे भविष्य के संदर्भ के लिए सुरक्षित रखें।` :
                           isBen ? `আপনার অভিযোগ নথিভুক্ত করা হয়েছে। আপনার টিকিট আইডি হলো: ${data.ticket_id}। অনুগ্রহ করে এটি ভবিষ্যতের রেফারেন্সের জন্য সংরক্ষণ করুন।` :
                           'Your complaint has been registered. Your Ticket ID is: ' + data.ticket_id + '. Please save this for future reference.';
        addMessage(successMsg, 'assistant');
        addFinalGrievanceMessage();
    } catch (err) {
        document.getElementById(typingId)?.remove();
        const errorMsg = isHi ? 'क्षमा करें, आपकी शिकायत दर्ज नहीं की जा सकी। कृपया पुनः प्रयास करें।' :
                          isBen ? 'দুঃখিত, আপনার অভিযোগ জমা দেওয়া যায়নি। অনুগ্রহ করে আবার চেষ্টা করুন।' :
                          'Sorry, could not submit your complaint. Please try again.';
        addMessage(errorMsg, 'assistant');
        addFinalGrievanceMessage();
    }
}

async function handleTicketCheck() {
    const raw = chatInput.value;
    
    let ticketId = raw;
    const prefixes = [
        'Ticket ID :',
        'टिकट आईडी :',
        'টিকিট আইডি :'
    ];
    for (const prefix of prefixes) {
        if (ticketId.includes(prefix)) {
            ticketId = ticketId.replace(prefix, '');
        }
    }
    ticketId = ticketId.trim();

    const lang = currentLanguage || 'en';
    const isHi = (lang === 'hi' || lang === 'bho' || lang === 'mai');
    const isBen = (lang === 'ben');

    if (!ticketId) {
        const enterTicketMsg = isHi ? 'कृपया टिकट आईडी दर्ज करें।' :
                               isBen ? 'অনুগ্রহ করে টিকিট আইডি লিখুন।' :
                               'Please enter a Ticket ID.';
        addMessage(enterTicketMsg, 'assistant');
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
            const processingMsg = isHi ? 'इस शिकायत पर कार्रवाई की जा रही है, आपको जल्द ही सूचित किया जाएगा।' :
                                  isBen ? 'এই অভিযোগের ওপর কাজ চলছে, আপনাকে শীঘ্রই জানানো হবে।' :
                                  'Processing on this Grievance, you will be updated shortly';
            addMessage(processingMsg, 'assistant');
        } else {
            const invalidMsg = isHi ? 'उल्लेखित टिकट अमान्य है।' :
                               isBen ? 'উল্লেখিত টিকিটটি বৈধ নয়।' :
                               'mentioned ticket is not valid';
            addMessage(invalidMsg, 'assistant');
        }
        addFinalGrievanceMessage();
    } catch (err) {
        document.getElementById(typingId)?.remove();
        const errorMsg = isHi ? 'क्षमा करें, टिकट की स्थिति की जांच नहीं की जा सकी। कृपया पुनः प्रयास करें।' :
                          isBen ? 'দুঃখিত, টিকিটের স্থিতি পরীক্ষা করা যায়নি। অনুগ্রহ করে আবার চেষ্টা করুন।' :
                          'Sorry, could not check ticket status. Please try again.';
        addMessage(errorMsg, 'assistant');
        addFinalGrievanceMessage();
    }
}

// ─── Sync Language with Backend ────────────────────────────────
async function syncLanguageWithBackend(lang) {
    try {
        await fetch('/api/language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sessionId: sessionId, language: lang })
        });
    } catch (e) {
        console.error('Failed to sync language:', e);
    }
}

// ─── Change Chatbot Language ───────────────────────────────────
window.changeLanguage = function(lang) {
    currentLanguage = lang;

    // Update select element value if not matching
    const langSelect = document.getElementById('lang-select');
    if (langSelect && langSelect.value !== lang) {
        langSelect.value = lang;
    }

    const dict = {
        en: {
            title: 'MSME Saathi - Your MSME Assistant',
            placeholder: 'Type your question or ask anything...',
            welcome: 'How can I help you today?',
            home: 'Home',
            privacy: 'All conversations are confidential and secure',
            c1t: 'Udyam Registration',
            c1s: 'Registration process',
            c2t: 'PMEGP Loan',
            c2s: 'Scheme details',
            c3t: 'File Grievance',
            c3s: 'Register complaint',
            c4t: 'MUDRA Loan',
            c4s: 'Scheme details',
            c5t: 'Search Schemes',
            c5s: 'Find the right scheme'
        },
        hi: {
            title: 'एमएसएमई साथी',
            placeholder: 'अपना सवाल लिखें...',
            welcome: 'मैं आज आपकी कैसे मदद कर सकता हूँ?',
            home: 'होम',
            privacy: 'सभी बातचीत गोपनीय और सुरक्षित हैं',
            c1t: 'उद्यम रजिस्ट्रेशन',
            c1s: 'पंजीकरण प्रक्रिया',
            c2t: 'PMEGP लोन',
            c2s: 'योजना विवरण',
            c3t: 'शिकायत दर्ज करें',
            c3s: 'शिकायत पंजीकृत करें',
            c4t: 'MUDRA लोन',
            c4s: 'योजना विवरण',
            c5t: 'योजना खोजें',
            c5s: 'सही योजना खोजें'
        },
        bho: {
            title: 'एमएसएमई साथी',
            placeholder: 'अपन सवाल लिखीं...',
            welcome: 'हम आज रउआ कइसे मदद कर सकत बानी?',
            home: 'होम',
            privacy: 'सभ बातचीत गोपनीय अउर सुरक्षित बा',
            c1t: 'उद्यम रजिस्ट्रेशन',
            c1s: 'पंजीकरण प्रक्रिया',
            c2t: 'PMEGP लोन',
            c2s: 'योजना विवरण',
            c3t: 'शिकायत दर्ज करीं',
            c3s: 'शिकायत पंजीकृत करीं',
            c4t: 'MUDRA लोन',
            c4s: 'योजना विवरण',
            c5t: 'योजना खोजीं',
            c5s: 'सही योजना खोजीं'
        },
        mai: {
            title: 'एमएसएमई साथी',
            placeholder: 'अपन प्रश्न लिखू...',
            welcome: 'हम आज अहाँक कते मदद कऽ सकैत छी?',
            home: 'होम',
            privacy: 'सभ गप-सप गोपनीय आ सुरक्षित अछि',
            c1t: 'उद्यम रजिस्ट्रेशन',
            c1s: 'पंजीकरण प्रक्रिया',
            c2t: 'PMEGP लोन',
            c2s: 'योजना विवरण',
            c3t: 'शिकायत दर्ज करू',
            c3s: 'शिकायत पंजीकृत करू',
            c4t: 'MUDRA लोन',
            c4s: 'योजना विवरण',
            c5t: 'योजना खोजू',
            c5s: 'सही योजना खोजू'
        },
        ben: {
            title: 'এমএসএমই সাথী',
            placeholder: 'আপনার প্রশ্নটি লিখুন...',
            welcome: 'আমি আজ আপনাকে কীভাবে সাহায্য করতে পারি?',
            home: 'হোম',
            privacy: 'সমস্ত কথোপকথন গোপনীয় এবং নিরাপদ',
            c1t: 'উদ্যম রেজিস্ট্রেশন',
            c1s: 'নিবন্ধন প্রক্রিয়া',
            c2t: 'PMEGP লোন',
            c2s: 'প্রকল্পের বিবরণ',
            c3t: 'অভিযোগ জানান',
            c3s: 'অভিযোগ নথিভুক্ত করুন',
            c4t: 'MUDRA লোন',
            c4s: 'প্রকল্পের বিবরণ',
            c5t: 'স্কিম অনুসন্ধান',
            c5s: 'সঠিক প্রকল্প খুঁজুন'
        }
    };

    const t = dict[lang] || dict['en'];

    document.title = t.title;
    if(chatInput) chatInput.placeholder = t.placeholder;
    
    const welcomeTitle = document.getElementById('welcome-title');
    if(welcomeTitle) welcomeTitle.textContent = t.welcome;
    
    const viewTitle = document.getElementById('view-title');
    if(viewTitle) viewTitle.textContent = t.home;
    
    const privacyNotice = document.getElementById('privacy-notice');
    if(privacyNotice) privacyNotice.textContent = t.privacy;

    const c1t = document.getElementById('card-1-title');
    if(c1t) c1t.textContent = t.c1t;
    const c1s = document.getElementById('card-1-sub');
    if(c1s) c1s.textContent = t.c1s;

    const c2t = document.getElementById('card-2-title');
    if(c2t) c2t.textContent = t.c2t;
    const c2s = document.getElementById('card-2-sub');
    if(c2s) c2s.textContent = t.c2s;

    const c3t = document.getElementById('card-3-title');
    if(c3t) c3t.textContent = t.c3t;
    const c3s = document.getElementById('card-3-sub');
    if(c3s) c3s.textContent = t.c3s;

    const c4t = document.getElementById('card-4-title');
    if(c4t) c4t.textContent = t.c4t;
    const c4s = document.getElementById('card-4-sub');
    if(c4s) c4s.textContent = t.c4s;

    const c5t = document.getElementById('card-5-title');
    if(c5t) c5t.textContent = t.c5t;
    const c5s = document.getElementById('card-5-sub');
    if(c5s) c5s.textContent = t.c5s;

    if (recognition) {
        recognition.lang = (lang === 'hi' || lang === 'bho' || lang === 'mai') ? 'hi-IN' : 
                           (lang === 'ben') ? 'bn-IN' : 'en-IN';
    }

    syncLanguageWithBackend(lang);
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

window.submitDynamicGrievanceForm = async function(formId, escapedFormDataJson) {
    const decodedJson = escapedFormDataJson
        .replace(/&quot;/g, '"')
        .replace(/&#x27;/g, "'")
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');
        
    const formData = JSON.parse(decodedJson);
    const fields = formData.fields;
    const extractedData = formData.extracted_data;
    const rawText = formData.raw_text;
    
    const submission = { ...extractedData, raw_text: rawText, session_id: sessionId };
    let isValid = true;
    
    fields.forEach(field => {
        const inputEl = document.getElementById(`${formId}-${field.name}`);
        if (inputEl) {
            const val = inputEl.value.trim();
            const isRequired = field.name === 'scheme_name' || field.name === 'grievance_type' || field.name === 'contact_number';
            
            let fieldValid = true;
            if (isRequired && !val) {
                fieldValid = false;
            } else if (field.name === 'contact_number') {
                const phoneRegex = /^[6-9]\d{9}$/;
                if (!phoneRegex.test(val)) {
                    fieldValid = false;
                }
            }
            
            if (!fieldValid) {
                isValid = false;
                inputEl.style.borderColor = 'red';
            } else {
                inputEl.style.borderColor = '';
                submission[field.name] = val;
            }
        }
    });
    
    if (!isValid) {
        alert('Please fill out all required fields. Contact number must be a valid 10-digit Indian number (starting with 6-9).');
        return;
    }
    
    const submitBtn = document.querySelector(`#${formId} button`);
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
    }
    
    try {
        const response = await fetch('/api/grievance/submit_dynamic', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(submission)
        });
        
        if (!response.ok) {
            throw new Error('Server returned error status');
        }
        
        const data = await response.json();
        
        const container = document.getElementById(formId);
        if (container) {
            const lang = currentLanguage || 'en';
            const isHi = (lang === 'hi' || lang === 'bho' || lang === 'mai');
            const isBen = (lang === 'ben');

            const successHeader = isHi ? '✅ शिकायत सफलतापूर्वक पंजीकृत हो गई!' :
                                  isBen ? '✅ অভিযোগ সফলভাবে নথিভুক্ত করা হয়েছে!' :
                                  '✅ Grievance registered successfully!';
            const ticketLabel = isHi ? 'टिकट आईडी:' :
                                isBen ? 'টিকিট আইডি:' :
                                'Ticket ID:';
            const callLabel = isHi ? `हम आपकी शिकायत के लिए आपके संपर्क नंबर: <strong>${data.contact_number}</strong> पर जल्द ही कॉल शेड्यूल करेंगे।` :
                              isBen ? `আমরা আপনার অভিযোগের জন্য আপনার যোগাযোগ নম্বরে: <strong>${data.contact_number}</strong> একটি কল শিডিউল করব।` :
                              `We will schedule a call for your grievance on your contact number: <strong>${data.contact_number}</strong>.`;

            container.innerHTML = `
                <div style="background: rgba(76, 175, 80, 0.1); border: 1px solid #4CAF50; border-radius: 8px; padding: 12px; margin-top: 10px; color: #4CAF50; font-weight: 500;">
                    <p style="margin: 0; font-size: 14px;">${successHeader}</p>
                    <p style="margin: 4px 0 0 0; font-size: 13px;">${ticketLabel} <strong>${data.ticket_id}</strong></p>
                    <p style="margin: 6px 0 0 0; font-size: 12.5px; color: black; font-weight: 400;">${callLabel}</p>
                </div>
                <div class="message-footer-container" style="margin-top: 12px; border-top: 1px solid rgba(123, 142, 175, 0.15); padding-top: 8px;">
                    <div class="message-privacy-footer">
                        <svg class="privacy-lock-icon" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                        <span>${getPrivacyNoticeText()}</span>
                    </div>
                </div>
            `;
        }
        addFinalGrievanceMessage();
    } catch (err) {
        alert('Failed to submit grievance. Please try again.');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Complaint';
        }
    }
};

window.submitDirectGrievanceForm = async function(formId) {
    const schemeEl = document.getElementById(`${formId}-scheme_name`);
    const typeEl = document.getElementById(`${formId}-grievance_type`);
    const bankEl = document.getElementById(`${formId}-entity_bank`);
    const amountEl = document.getElementById(`${formId}-entity_amount`);
    const durationEl = document.getElementById(`${formId}-entity_duration_days`);
    const contactEl = document.getElementById(`${formId}-contact_number`);
    const textEl = document.getElementById(`${formId}-raw_text`);

    let isValid = true;

    // Validate required fields
    [schemeEl, typeEl, contactEl, textEl].forEach(el => {
        if (el) {
            if (!el.value.trim()) {
                isValid = false;
                el.style.borderColor = 'red';
            } else {
                el.style.borderColor = '';
            }
        }
    });

    if (contactEl) {
        const phoneRegex = /^[6-9]\d{9}$/;
        if (!phoneRegex.test(contactEl.value.trim())) {
            isValid = false;
            contactEl.style.borderColor = 'red';
        }
    }

    const lang = currentLanguage || 'en';
    const isHi = (lang === 'hi' || lang === 'bho' || lang === 'mai');
    const isBen = (lang === 'ben');

    if (!isValid) {
        alert(isHi ? 'कृपया सभी आवश्यक फ़ील्ड भरें। संपर्क नंबर एक मान्य 10-अंकीय भारतीय नंबर होना चाहिए (6-9 से शुरू होने वाला)।' :
              isBen ? 'দয়া করে সমস্ত প্রয়োজনীয় ক্ষেত্র পূরণ করুন। যোগাযোগের নম্বরটি অবশ্যই একটি বৈধ 10-সংখ্যার ভারতীয় নম্বর হতে হবে (6-9 দিয়ে শুরু)।' :
              'Please fill out all required fields. Contact number must be a valid 10-digit Indian number (starting with 6-9).');
        return;
    }

    const submitBtn = document.querySelector(`#${formId} button`);
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = isHi ? 'शिकायत भेजी जा रही है...' :
                               isBen ? 'অভিযোগ জমা দেওয়া হচ্ছে...' :
                               'Submitting...';
    }

    const payload = {
        session_id: sessionId,
        scheme_name: schemeEl.value.trim(),
        grievance_type: typeEl.value.trim(),
        entity_bank: bankEl ? bankEl.value.trim() : null,
        entity_amount: amountEl ? amountEl.value.trim() : null,
        entity_duration_days: (durationEl && durationEl.value.trim()) ? parseInt(durationEl.value.trim()) : null,
        contact_number: contactEl.value.trim(),
        raw_text: textEl.value.trim()
    };

    try {
        const response = await fetch('/api/grievance/submit_dynamic', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error('Server returned error status');
        }

        const data = await response.json();

        const successHeader = isHi ? '✅ शिकायत सफलतापूर्वक पंजीकृत हो गई!' :
                              isBen ? '✅ অভিযোগ সফলভাবে নথিভুক্ত করা হয়েছে!' :
                              '✅ Grievance registered successfully!';
        const ticketLabel = isHi ? 'टिकट आईडी:' :
                            isBen ? 'টিকিট আইডি:' :
                            'Ticket ID:';
        const callLabel = isHi ? `हम आपकी शिकायत के लिए आपके संपर्क नंबर: <strong>${data.contact_number}</strong> पर जल्द ही कॉल शेड्यूल करेंगे।` :
                          isBen ? `আমরা আপনার অভিযোগের জন্য আপনার যোগাযোগ নম্বরে: <strong>${data.contact_number}</strong> একটি কল শিডিউল করব।` :
                          `We will schedule a call for your grievance on your contact number: <strong>${data.contact_number}</strong>.`;

        const container = document.getElementById(formId);
        if (container) {
            container.innerHTML = `
                <div style="background: rgba(76, 175, 80, 0.1); border: 1px solid #4CAF50; border-radius: 8px; padding: 12px; margin-top: 10px; color: #4CAF50; font-weight: 500;">
                    <p style="margin: 0; font-size: 14px;">${successHeader}</p>
                    <p style="margin: 4px 0 0 0; font-size: 13px;">${ticketLabel} <strong>${data.ticket_id}</strong></p>
                    <p style="margin: 6px 0 0 0; font-size: 12.5px; color: black; font-weight: 400;">${callLabel}</p>
                </div>
                <div class="message-footer-container" style="margin-top: 12px; border-top: 1px solid rgba(123, 142, 175, 0.15); padding-top: 8px;">
                    <div class="message-privacy-footer">
                        <svg class="privacy-lock-icon" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                        <span>${getPrivacyNoticeText()}</span>
                    </div>
                </div>
            `;
        }

        addFinalGrievanceMessage();
    } catch (err) {
        alert(isHi ? 'शिकायत दर्ज करने में विफल। कृपया पुनः प्रयास करें।' :
              isBen ? 'অভিযোগ জমা দিতে ব্যর্থ হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।' :
              'Failed to submit grievance. Please try again.');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = isHi ? 'शिकायत दर्ज करें' :
                                   isBen ? 'অভিযোগ জমা दिन' :
                                   'Submit Complaint';
        }
    }
};

