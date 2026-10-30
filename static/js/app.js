// document.addEventListener("DOMContentLoaded", () => {

//     // DOM ELEMENTS
//     const chatForm = document.getElementById("chatForm");
//     const messageInput = document.getElementById("messageInput");
//     const sendButton = document.getElementById("sendButton");

//     const welcomeScreen = document.getElementById("welcomeScreen");
//     const messagesContainer = document.getElementById("messagesContainer");

//     const studyNav = document.getElementById("studyNav");
//     const interviewNav = document.getElementById("interviewNav");
//     const newChatButton = document.getElementById("newChatButton");

//     const topbarTitle = document.getElementById("topbarTitle");
//     const breadcrumbMode = document.getElementById("breadcrumbMode");

//     const welcomeTitle = document.getElementById("welcomeTitle");
//     const welcomeDescription = document.getElementById("welcomeDescription");
//     const suggestionGrid = document.getElementById("suggestionGrid");

//     // APPLICATION STATE
//     let currentMode = "study";
//     let currentSessionId = null;
//     let conversationHistory = [];
//     let isCreatingSession = false;

//     const modeSettings = {
//         study: {
//             title: "ATSWA Study Assistant",
//             breadcrumb: "STUDY ASSISTANT",
//             welcomeTitle: 'Master accounting.<br><span>Build your confidence.</span>',
//             description:
//                 "Your intelligent ATSWA study companion. Ask questions, understand difficult concepts and prepare confidently for your examinations.",
//             placeholder: "Ask anything about accounting..."
//         },

//         interview: {
//             title: "ATSWA AI Interviewer",
//             breadcrumb: "AI INTERVIEWER",
//             welcomeTitle: 'Prepare for success.<br><span>Prove your knowledge.</span>',
//             description:
//                 "Experience a professional accounting interview. Answer technical questions, demonstrate your knowledge and receive constructive feedback.",
//             placeholder: "Start your accounting interview..."
//         }
//     };


//     // CREATE A BACKEND SESSION
//     async function createSession() {

//         currentSessionId = null;
//         isCreatingSession = true;
//         sendButton.disabled = true;

//         try {

//             const response = await fetch("/api/session", {
//                 method: "POST",
//                 headers: {
//                     "Content-Type": "application/json"
//                 },
//                 body: JSON.stringify({
//                     mode: currentMode,
//                     job_role: "Junior Auditor"
//                 })
//             });

//             const data = await response.json();

//             if (!response.ok || !data.success) {
//                 throw new Error(
//                     data.error || "Unable to create a conversation session."
//                 );
//             }

//             currentSessionId = data.session_id;

//             console.log(
//                 `${currentMode} session created:`,
//                 currentSessionId
//             );

//         } catch (error) {

//             console.error("Session creation error:", error);

//             addMessage(
//                 "ai",
//                 `**Unable to start a conversation.**\n\n${error.message}\n\nPlease refresh the page and try again.`
//             );

//         } finally {

//             isCreatingSession = false;
//             sendButton.disabled = false;

//         }
//     }


//     // SWITCH MODES
//     async function switchMode(mode) {

//         if (!modeSettings[mode]) return;

//         if (currentMode === mode && currentSessionId) return;

//         currentMode = mode;

//         const settings = modeSettings[mode];

//         topbarTitle.textContent = settings.title;
//         breadcrumbMode.textContent = settings.breadcrumb;

//         welcomeTitle.innerHTML = settings.welcomeTitle;
//         welcomeDescription.textContent = settings.description;

//         messageInput.placeholder = settings.placeholder;

//         studyNav.classList.toggle("active", mode === "study");
//         interviewNav.classList.toggle("active", mode === "interview");

//         resetConversation();

//         if (mode === "interview") {

//             suggestionGrid.innerHTML = `
//                 <button class="suggestion-card" data-question="Start an ATSWA technical accounting interview.">
//                     <span class="suggestion-icon">✦</span>
//                     <strong>Start an Interview</strong>
//                     <p>Begin a professional accounting interview.</p>
//                 </button>

//                 <button class="suggestion-card" data-question="Ask me interview questions on financial accounting.">
//                     <span class="suggestion-icon">◈</span>
//                     <strong>Financial Accounting</strong>
//                     <p>Test your financial accounting knowledge.</p>
//                 </button>

//                 <button class="suggestion-card" data-question="Interview me on auditing and assurance.">
//                     <span class="suggestion-icon">⌘</span>
//                     <strong>Auditing and Assurance</strong>
//                     <p>Demonstrate your auditing knowledge.</p>
//                 </button>

//                 <button class="suggestion-card" data-question="Interview me on taxation and Nigerian tax principles.">
//                     <span class="suggestion-icon">◎</span>
//                     <strong>Taxation</strong>
//                     <p>Test your knowledge of taxation.</p>
//                 </button>
//             `;

//         } else {

//             suggestionGrid.innerHTML = `
//                 <button class="suggestion-card" data-question="Explain the fundamental accounting concepts.">
//                     <span class="suggestion-icon">✦</span>
//                     <strong>Accounting Concepts</strong>
//                     <p>Understand fundamental accounting principles.</p>
//                 </button>

//                 <button class="suggestion-card" data-question="What are the responsibilities of an external auditor?">
//                     <span class="suggestion-icon">◈</span>
//                     <strong>Auditing and Assurance</strong>
//                     <p>Explore auditing responsibilities and procedures.</p>
//                 </button>

//                 <button class="suggestion-card" data-question="Explain the difference between financial accounting and management accounting.">
//                     <span class="suggestion-icon">⌘</span>
//                     <strong>Financial Reporting</strong>
//                     <p>Learn how financial information is prepared.</p>
//                 </button>

//                 <button class="suggestion-card" data-question="Give me five ATSWA examination practice questions on taxation.">
//                     <span class="suggestion-icon">◎</span>
//                     <strong>Practice Questions</strong>
//                     <p>Test your knowledge with exam-style questions.</p>
//                 </button>
//             `;

//         }

//         await createSession();
//     }


//     // RESET CONVERSATION
//     function resetConversation() {

//         currentSessionId = null;
//         conversationHistory = [];

//         messagesContainer.innerHTML = "";
//         messagesContainer.style.display = "none";

//         welcomeScreen.style.display = "block";
//     }


//     // DISPLAY MESSAGE
//     function addMessage(role, content, sources = []) {

//         welcomeScreen.style.display = "none";
//         messagesContainer.style.display = "block";

//         const messageElement = document.createElement("div");

//         messageElement.className = `message ${role}-message`;

//         const avatar = document.createElement("div");
//         avatar.className = "message-avatar";
//         avatar.textContent = role === "user" ? "Y" : "A";

//         const messageContent = document.createElement("div");
//         messageContent.className = "message-content";

//         if (role === "ai") {

//             const parsedHTML = marked.parse(content || "");
//             messageContent.innerHTML = DOMPurify.sanitize(parsedHTML);

//             if (sources.length > 0) {

//                 const sourceContainer = document.createElement("div");
//                 sourceContainer.className = "message-meta";

//                 const sourceTitle = document.createElement("strong");
//                 sourceTitle.textContent = "References: ";

//                 sourceContainer.appendChild(sourceTitle);

//                 const sourceNames = sources
//                     .map(source => source.source)
//                     .filter(Boolean);

//                 sourceContainer.appendChild(
//                     document.createTextNode(sourceNames.join(", "))
//                 );

//                 messageContent.appendChild(sourceContainer);
//             }

//         } else {

//             messageContent.textContent = content;

//         }

//         messageElement.appendChild(avatar);
//         messageElement.appendChild(messageContent);

//         messagesContainer.appendChild(messageElement);

//         messagesContainer.scrollTop = messagesContainer.scrollHeight;
//     }


//     // LOADING INDICATOR
//     function showLoading() {

//         const loading = document.createElement("div");

//         loading.id = "loadingIndicator";
//         loading.className = "message ai-message";

//         loading.innerHTML = `
//             <div class="message-avatar">A</div>
//             <div class="message-content typing-indicator">
//                 ATSWA AI is thinking...
//             </div>
//         `;

//         messagesContainer.appendChild(loading);

//         messagesContainer.scrollTop = messagesContainer.scrollHeight;
//     }


//     // REMOVE LOADING INDICATOR
//     function removeLoading() {

//         const loading = document.getElementById("loadingIndicator");

//         if (loading) {
//             loading.remove();
//         }
//     }


//     // SEND MESSAGE TO FLASK BACKEND
//     async function sendMessage(question) {

//         if (!question.trim() || sendButton.disabled) return;

//         if (!currentSessionId || isCreatingSession) {

//             addMessage(
//                 "ai",
//                 "**Your conversation is still starting.** Please try again in a moment."
//             );

//             return;
//         }

//         addMessage("user", question);

//         messageInput.value = "";
//         messageInput.style.height = "auto";

//         sendButton.disabled = true;

//         showLoading();

//         try {

//             const response = await fetch("/api/chat", {

//                 method: "POST",

//                 headers: {
//                     "Content-Type": "application/json"
//                 },

//                 body: JSON.stringify({
//                     question: question,
//                     mode: currentMode,
//                     session_id: currentSessionId
//                 })

//             });

//             const data = await response.json();

//             removeLoading();

//             if (!response.ok || !data.success) {

//                 throw new Error(
//                     data.error || "Unable to generate a response."
//                 );

//             }

//             addMessage(
//                 "ai",
//                 data.answer,
//                 data.sources || []
//             );

//             conversationHistory = data.conversation_history || [];

//         } catch (error) {

//             removeLoading();

//             addMessage(
//                 "ai",
//                 `**Something went wrong.**\n\n${error.message}\n\nPlease try again.`
//             );

//             console.error("ATSWA AI Error:", error);

//         } finally {

//             sendButton.disabled = false;
//             messageInput.focus();

//         }
//     }


//     // FORM SUBMISSION
//     chatForm.addEventListener("submit", (event) => {

//         event.preventDefault();

//         const question = messageInput.value.trim();

//         if (!question || sendButton.disabled) return;

//         sendMessage(question);

//     });


//     // ENTER TO SEND, SHIFT + ENTER FOR NEW LINE
//     messageInput.addEventListener("keydown", (event) => {

//         if (
//             event.key === "Enter" &&
//             !event.shiftKey &&
//             !event.isComposing
//         ) {

//             event.preventDefault();
//             chatForm.requestSubmit();

//         }

//     });


//     // AUTO-RESIZE TEXTAREA
//     messageInput.addEventListener("input", () => {

//         messageInput.style.height = "auto";

//         messageInput.style.height =
//             Math.min(messageInput.scrollHeight, 150) + "px";

//     });


//     // SIDEBAR NAVIGATION
//     studyNav.addEventListener("click", () => {
//         switchMode("study");
//     });

//     interviewNav.addEventListener("click", () => {
//         switchMode("interview");
//     });


//     // NEW CONVERSATION
//     newChatButton.addEventListener("click", async () => {

//         resetConversation();

//         await createSession();

//         messageInput.focus();

//     });


//     // SUGGESTED QUESTIONS
//     suggestionGrid.addEventListener("click", (event) => {

//         const card = event.target.closest("[data-question]");

//         if (!card) return;

//         const question = card.dataset.question;

//         sendMessage(question);

//     });


//     // INITIALIZE APPLICATION
//     switchMode("study");

//     console.log("ATSWA AI frontend initialized successfully.");

// });



document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // DOM ELEMENTS
    // ==========================================

    const chatForm = document.getElementById("chatForm");
    const messageInput = document.getElementById("messageInput");
    const sendButton = document.getElementById("sendButton");

    const welcomeScreen = document.getElementById("welcomeScreen");
    const messagesContainer = document.getElementById("messagesContainer");

    const studyNav = document.getElementById("studyNav");
    const interviewNav = document.getElementById("interviewNav");
    const newChatButton = document.getElementById("newChatButton");

    const topbarTitle = document.getElementById("topbarTitle");
    const breadcrumbMode = document.getElementById("breadcrumbMode");

    const welcomeTitle = document.getElementById("welcomeTitle");
    const welcomeDescription = document.getElementById("welcomeDescription");
    const suggestionGrid = document.getElementById("suggestionGrid");


    // ==========================================
    // APPLICATION STATE
    // ==========================================

    let currentMode = "study";
    let currentSessionId = null;
    let currentJobRole = null;

    let conversationHistory = [];

    let isCreatingSession = false;
    let isSendingMessage = false;

    const modeSettings = {

        study: {
            title: "ATSWA Study Assistant",
            breadcrumb: "STUDY ASSISTANT",

            welcomeTitle:
                'Master accounting.<br><span>Build your confidence.</span>',

            description:
                "Your intelligent ATSWA study companion. Ask questions, understand difficult concepts and prepare confidently for your examinations.",

            placeholder:
                "Ask anything about accounting..."
        },

        interview: {
            title: "ATSWA AI Interviewer",
            breadcrumb: "AI INTERVIEWER",

            welcomeTitle:
                'Prepare for success.<br><span>Prove your knowledge.</span>',

            description:
                "Experience a professional job interview. Answer technical questions, demonstrate your knowledge and receive constructive feedback.",

            placeholder:
                "Answer your interview question..."
        }

    };


    // ==========================================
    // INTERVIEW SUGGESTIONS
    // ==========================================

    function renderInterviewSuggestions() {

        suggestionGrid.innerHTML = `

            <button class="suggestion-card"
                data-question="Start my interview. Please introduce yourself and begin with the first relevant interview question.">

                <span class="suggestion-icon">✦</span>
                <strong>Start Interview</strong>
                <p>Begin your professional interview.</p>

            </button>


            <button class="suggestion-card"
                data-question="Ask me technical questions relevant to my job role.">

                <span class="suggestion-icon">◈</span>
                <strong>Technical Questions</strong>
                <p>Test your professional knowledge.</p>

            </button>


            <button class="suggestion-card"
                data-question="Ask me practical scenario-based questions relevant to my job role.">

                <span class="suggestion-icon">⌘</span>
                <strong>Practical Scenarios</strong>
                <p>Test how you handle workplace situations.</p>

            </button>


            <button class="suggestion-card"
                data-question="Assess my professional knowledge and ask challenging questions relevant to my job role.">

                <span class="suggestion-icon">◎</span>
                <strong>Professional Assessment</strong>
                <p>Evaluate your professional knowledge.</p>

            </button>

        `;

    }


    // ==========================================
    // STUDY SUGGESTIONS
    // ==========================================

    function renderStudySuggestions() {

        suggestionGrid.innerHTML = `

            <button class="suggestion-card"
                data-question="Explain the fundamental accounting concepts.">

                <span class="suggestion-icon">✦</span>
                <strong>Accounting Concepts</strong>
                <p>Understand fundamental accounting principles.</p>

            </button>


            <button class="suggestion-card"
                data-question="What are the responsibilities of an external auditor?">

                <span class="suggestion-icon">◈</span>
                <strong>Auditing and Assurance</strong>
                <p>Explore auditing responsibilities and procedures.</p>

            </button>


            <button class="suggestion-card"
                data-question="Explain the difference between financial accounting and management accounting.">

                <span class="suggestion-icon">⌘</span>
                <strong>Financial Reporting</strong>
                <p>Learn how financial information is prepared.</p>

            </button>


            <button class="suggestion-card"
                data-question="Give me five ATSWA examination practice questions on taxation.">

                <span class="suggestion-icon">◎</span>
                <strong>Practice Questions</strong>
                <p>Test your knowledge with exam-style questions.</p>

            </button>

        `;

    }


    // ==========================================
    // CREATE BACKEND SESSION
    // ==========================================

    async function createSession(jobRole = null) {

        currentSessionId = null;

        isCreatingSession = true;
        sendButton.disabled = true;

        try {

            const response = await fetch("/api/session", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    mode: currentMode,

                    job_role:
                        currentMode === "interview"
                            ? jobRole
                            : null

                })

            });


            const data = await response.json();


            if (!response.ok || !data.success) {

                throw new Error(
                    data.error || "Unable to create your conversation session."
                );

            }


            currentSessionId = data.session_id;

            currentJobRole = jobRole;


            console.log("SESSION CREATED");

            console.log("Mode:", currentMode);

            console.log("Session ID:", currentSessionId);

            console.log("Job Role:", currentJobRole);


            return true;


        } catch (error) {

            console.error("Session creation error:", error);

            addMessage(
                "ai",
                `**Unable to start your conversation.**\n\n${error.message}`
            );

            return false;


        } finally {

            isCreatingSession = false;

            sendButton.disabled = false;

        }

    }


    // ==========================================
    // SELECT INTERVIEW ROLE
    // ==========================================

    function requestJobRole() {

        const role = window.prompt(

            "What job position would you like to be interviewed for?\n\nExamples:\n\nJunior Accountant\nExternal Auditor\nFinancial Analyst\nTax Associate\nManagement Accountant\nFinance Manager\nInternal Auditor\n\nYou can enter any job title."

        );


        if (role === null) {
            return null;
        }


        const cleanedRole = role.trim();


        if (!cleanedRole) {

            alert("Please enter a valid job position.");

            return requestJobRole();

        }


        return cleanedRole;

    }


    // ==========================================
    // RESET CONVERSATION
    // ==========================================

    function resetConversation() {

        currentSessionId = null;

        conversationHistory = [];

        messagesContainer.innerHTML = "";

        messagesContainer.style.display = "none";

        welcomeScreen.style.display = "block";

    }


    // ==========================================
    // SWITCH APPLICATION MODES
    // ==========================================

    async function switchMode(mode, forceNew = false) {

        if (!modeSettings[mode]) return;


        if (
            currentMode === mode &&
            currentSessionId &&
            !forceNew
        ) {
            return;
        }


        // Ask for a role before changing to interview mode.
        let selectedRole = null;


        if (mode === "interview") {

            selectedRole = requestJobRole();

            if (!selectedRole) {
                return;
            }

        }


        currentMode = mode;

        currentJobRole = selectedRole;


        const settings = modeSettings[mode];


        // Update interface.

        topbarTitle.textContent = settings.title;

        breadcrumbMode.textContent = settings.breadcrumb;

        welcomeTitle.innerHTML = settings.welcomeTitle;

        welcomeDescription.textContent = settings.description;

        messageInput.placeholder = settings.placeholder;


        studyNav.classList.toggle(
            "active",
            mode === "study"
        );

        interviewNav.classList.toggle(
            "active",
            mode === "interview"
        );


        resetConversation();


        // Update suggestions.

        if (mode === "interview") {

            renderInterviewSuggestions();

            welcomeDescription.textContent =
                `Prepare for your ${selectedRole} interview. Your questions will be tailored to this position.`;


        } else {

            renderStudySuggestions();

        }


        // Create the new backend session.

        const created = await createSession(selectedRole);


        if (created) {

            messageInput.focus();

        }

    }


    // ==========================================
    // DISPLAY MESSAGES
    // ==========================================

    function addMessage(role, content, sources = []) {

        welcomeScreen.style.display = "none";

        messagesContainer.style.display = "block";


        const messageElement = document.createElement("div");

        messageElement.className = `message ${role}-message`;


        const avatar = document.createElement("div");

        avatar.className = "message-avatar";

        avatar.textContent = role === "user" ? "Y" : "A";


        const messageContent = document.createElement("div");

        messageContent.className = "message-content";


        if (role === "ai") {

            const parsedHTML = marked.parse(content || "");

            messageContent.innerHTML =
                DOMPurify.sanitize(parsedHTML);


            if (sources.length > 0) {

                const sourceContainer =
                    document.createElement("div");

                sourceContainer.className = "message-meta";


                const sourceTitle =
                    document.createElement("strong");

                sourceTitle.textContent = "References: ";

                sourceContainer.appendChild(sourceTitle);


                const sourceNames = sources
                    .map(source => source.source)
                    .filter(Boolean);


                sourceContainer.appendChild(

                    document.createTextNode(
                        [...new Set(sourceNames)].join(", ")
                    )

                );


                messageContent.appendChild(sourceContainer);

            }

        } else {

            messageContent.textContent = content;

        }


        messageElement.appendChild(avatar);

        messageElement.appendChild(messageContent);

        messagesContainer.appendChild(messageElement);


        messagesContainer.scrollTop =
            messagesContainer.scrollHeight;

    }


    // ==========================================
    // LOADING INDICATOR
    // ==========================================

    function showLoading() {

        const loading = document.createElement("div");

        loading.id = "loadingIndicator";

        loading.className = "message ai-message";


        loading.innerHTML = `

            <div class="message-avatar">A</div>

            <div class="message-content typing-indicator">
                ATSWA AI is thinking...
            </div>

        `;


        messagesContainer.appendChild(loading);

        messagesContainer.scrollTop =
            messagesContainer.scrollHeight;

    }


    function removeLoading() {

        const loading =
            document.getElementById("loadingIndicator");

        if (loading) {
            loading.remove();
        }

    }


    // ==========================================
    // SEND MESSAGE TO FLASK
    // ==========================================

    async function sendMessage(question) {

        if (!question.trim()) return;

        if (isSendingMessage || sendButton.disabled) return;


        if (!currentSessionId || isCreatingSession) {

            addMessage(
                "ai",
                "**Your conversation is not ready yet.** Please try again shortly."
            );

            return;

        }


        isSendingMessage = true;

        sendButton.disabled = true;


        addMessage("user", question);


        messageInput.value = "";

        messageInput.style.height = "auto";


        showLoading();


        try {

            const response = await fetch("/api/chat", {

                method: "POST",

                headers: {

                    "Content-Type": "application/json"

                },

                body: JSON.stringify({

                    question: question,

                    mode: currentMode,

                    session_id: currentSessionId

                })

            });


            const data = await response.json();


            removeLoading();


            if (!response.ok || !data.success) {

                throw new Error(
                    data.error || "Unable to generate a response."
                );

            }


            addMessage(

                "ai",

                data.answer,

                data.sources || []

            );


            conversationHistory =
                data.conversation_history || [];


        } catch (error) {

            removeLoading();


            addMessage(

                "ai",

                `**Something went wrong.**\n\n${error.message}\n\nPlease try again.`

            );


            console.error("ATSWA AI Error:", error);


        } finally {

            isSendingMessage = false;

            sendButton.disabled = false;

            messageInput.focus();

        }

    }


    // ==========================================
    // FORM SUBMISSION
    // ==========================================

    chatForm.addEventListener("submit", (event) => {

        event.preventDefault();


        const question = messageInput.value.trim();


        if (!question) return;

        sendMessage(question);

    });


    // ==========================================
    // ENTER TO SEND
    // SHIFT + ENTER FOR NEW LINE
    // ==========================================

    messageInput.addEventListener("keydown", (event) => {

        if (

            event.key === "Enter" &&

            !event.shiftKey &&

            !event.isComposing

        ) {

            event.preventDefault();

            chatForm.requestSubmit();

        }

    });


    // ==========================================
    // AUTO RESIZE TEXTAREA
    // ==========================================

    messageInput.addEventListener("input", () => {

        messageInput.style.height = "auto";

        messageInput.style.height =
            Math.min(messageInput.scrollHeight, 150) + "px";

    });


    // ==========================================
    // SIDEBAR NAVIGATION
    // ==========================================

    studyNav.addEventListener("click", () => {

        switchMode("study");

    });


    interviewNav.addEventListener("click", () => {

        switchMode("interview");

    });


    // ==========================================
    // NEW CONVERSATION
    // ==========================================

    newChatButton.addEventListener("click", async () => {

        await switchMode(currentMode, true);

        messageInput.focus();

    });


    // ==========================================
    // SUGGESTED QUESTIONS
    // ==========================================

    suggestionGrid.addEventListener("click", (event) => {

        const card = event.target.closest("[data-question]");

        if (!card) return;


        const question = card.dataset.question;

        sendMessage(question);

    });


    // ==========================================
    // INITIALIZE APPLICATION
    // ==========================================

    renderStudySuggestions();

    switchMode("study");

    console.log(
        "ATSWA AI frontend initialized successfully."
    );

});
