// import React, {
//   useEffect,
//   useRef,
//   useState,
// } from "react";

// import "./Chatbot.css";

// const API_BASE_URL =
//   "http://127.0.0.1:8000";

// const quickQuestions = [
//   "What is OCRFlow?",
//   "Supported file formats?",
//   "How to extract text?",
//   "What languages are supported?",
// ];

// const features = [
//   {
//     icon: "▣",
//     title: "Document Understanding",
//     description:
//       "Get detailed insights about your documents.",
//   },
//   {
//     icon: "◎",
//     title: "Multi-language Support",
//     description:
//       "Works with 90+ languages.",
//   },
//   {
//     icon: "▤",
//     title: "Structured Data",
//     description:
//       "Extract and organize data in JSON, tables, etc.",
//   },
//   {
//     icon: "▧",
//     title: "Easy Integration",
//     description:
//       "Use the extracted data for your workflows.",
//   },
// ];

// function Chatbot() {
//   /*
//    * =========================================================
//    * CHAT MESSAGES
//    * =========================================================
//    */

//   const [
//     messages,
//     setMessages,
//   ] = useState([
//     {
//       role: "assistant",
//       content:
//         "OCRFlow supports 90+ languages for document processing and OCR. Our live demonstration focuses on English, Hindi and Gujarati, but the system can handle a wide range of other languages as well.",
//       details: [
//         "90+ languages (global support)",
//         "Demo languages: English, Hindi, Gujarati",
//         "Includes major international and Indian languages",
//       ],
//       time: "10:24 AM",
//     },
//   ]);

//   const [
//     message,
//     setMessage,
//   ] = useState("");

//   const [
//     loading,
//     setLoading,
//   ] = useState(false);

//   /*
//    * =========================================================
//    * CHAT DOCUMENT
//    * =========================================================
//    *
//    * This is the ALREADY GENERATED STRUCTURED PDF.
//    *
//    * IMPORTANT:
//    *
//    * This chatbot does NOT run OCR.
//    *
//    * The PDF is uploaded to:
//    *
//    *     POST /api/chat/upload
//    *
//    * The backend extracts selectable text from the PDF using
//    * PyMuPDF and creates a chatbot document session.
//    */

//   const [
//     selectedPDF,
//     setSelectedPDF,
//   ] = useState(null);

//   const [
//     chatDocumentId,
//     setChatDocumentId,
//   ] = useState(null);

//   const [
//     documentChatStarted,
//     setDocumentChatStarted,
//   ] = useState(false);

//   const [
//     uploading,
//     setUploading,
//   ] = useState(false);

//   const [
//     uploadMessage,
//     setUploadMessage,
//   ] = useState("");

//   const fileInputRef =
//     useRef(null);

//   const messagesContainerRef =
//     useRef(null);

//   /*
//    * =========================================================
//    * SCROLL CHAT CONTAINER
//    * =========================================================
//    */

//   useEffect(() => {
//     const container =
//       messagesContainerRef.current;

//     if (!container) {
//       return;
//     }

//     container.scrollTo({
//       top: container.scrollHeight,
//       behavior: "smooth",
//     });
//   }, [messages, loading]);

//   /*
//    * =========================================================
//    * OPEN PDF PICKER
//    * =========================================================
//    */

//   const handleAttachmentClick = () => {
//     if (
//       loading ||
//       uploading ||
//       fileInputRef.current === null
//     ) {
//       return;
//     }

//     fileInputRef.current.click();
//   };

//   /*
//    * =========================================================
//    * UPLOAD STRUCTURED PDF TO CHATBOT
//    * =========================================================
//    *
//    * IMPORTANT:
//    *
//    * This does NOT call /api/process.
//    *
//    * Therefore:
//    *
//    * NO OCR
//    * NO Surya
//    * NO preprocessing
//    * NO OCR pipeline
//    * NO status polling
//    *
//    * The backend only extracts text from the already-generated
//    * structured PDF.
//    * =========================================================
//    */

//   const uploadPDFForChat = async (
//     file
//   ) => {
//     if (!file) {
//       return null;
//     }

//     setUploading(true);
//     setUploadMessage(
//       "Loading PDF for chatbot..."
//     );

//     try {
//       const formData =
//         new FormData();

//       formData.append(
//         "file",
//         file
//       );

//       const response =
//         await fetch(
//           `${API_BASE_URL}/api/chat/upload`,
//           {
//             method: "POST",
//             body: formData,
//           }
//         );

//       let data = null;

//       try {
//         data =
//           await response.json();
//       } catch {
//         data = null;
//       }

//       if (!response.ok) {
//         throw new Error(
//           data?.detail ||
//             "Unable to load the PDF for chatbot."
//         );
//       }

//       if (!data?.success) {
//         throw new Error(
//           data?.detail ||
//             "Unable to load the PDF for chatbot."
//         );
//       }

//       /*
//        * The corrected backend returns chat_id.
//        *
//        * Accept a few compatible names so the frontend is
//        * tolerant of the response structure.
//        */

//       const returnedChatId =
//         data?.chat_id ||
//         data?.document_id ||
//         data?.chat_document_id;

//       if (!returnedChatId) {
//         throw new Error(
//           "Chatbot backend did not return a chat ID."
//         );
//       }

//       setChatDocumentId(
//         String(returnedChatId)
//       );

//       setDocumentChatStarted(
//         false
//       );

//       setUploadMessage(
//         "PDF loaded successfully. Click Send to generate the document summary and answer your question."
//       );

//       return String(
//         returnedChatId
//       );
//     } catch (error) {
//       console.error(
//         "Chatbot PDF upload error:",
//         error
//       );

//       setUploadMessage("");

//       setMessages((previous) => [
//         ...previous,
//         {
//           role: "assistant",
//           content:
//             error?.message ||
//             "Unable to load the PDF for chatbot.",
//           time:
//             getCurrentTime(),
//         },
//       ]);

//       return null;
//     } finally {
//       setUploading(false);
//     }
//   };

//   /*
//    * =========================================================
//    * PDF SELECTION
//    * =========================================================
//    */

//   const handleFileChange = async (
//     event
//   ) => {
//     const file =
//       event.target.files?.[0];

//     /*
//      * Allow selecting the same file again.
//      */

//     event.target.value = "";

//     if (!file) {
//       return;
//     }

//     /*
//      * =======================================================
//      * PDF VALIDATION
//      * =======================================================
//      */

//     const isPDF =
//       file.type ===
//         "application/pdf" ||
//       file.name
//         .toLowerCase()
//         .endsWith(".pdf");

//     if (!isPDF) {
//       setMessages((previous) => [
//         ...previous,
//         {
//           role: "assistant",
//           content:
//             "Please select a PDF file.",
//           time:
//             getCurrentTime(),
//         },
//       ]);

//       return;
//     }

//     /*
//      * =======================================================
//      * 50 MB LIMIT
//      * =======================================================
//      */

//     if (
//       file.size >
//       50 * 1024 * 1024
//     ) {
//       setMessages((previous) => [
//         ...previous,
//         {
//           role: "assistant",
//           content:
//             "File size must be less than 50 MB.",
//           time:
//             getCurrentTime(),
//         },
//       ]);

//       return;
//     }

//     /*
//      * =======================================================
//      * STORE SELECTED PDF
//      * =======================================================
//      */

//     setSelectedPDF(file);

//     /*
//      * A new PDF means a completely new chatbot session.
//      */

//     setChatDocumentId(null);

//     setDocumentChatStarted(
//       false
//     );

//     setUploadMessage("");

//     setMessages((previous) => [
//       ...previous,
//       {
//         role: "user",
//         content:
//           `Uploaded: ${file.name}`,
//         time:
//           getCurrentTime(),
//       },
//     ]);

//     /*
//      * =======================================================
//      * SEND PDF TO CHATBOT BACKEND
//      * =======================================================
//      *
//      * This is NOT OCR.
//      *
//      * The backend only:
//      *
//      * PDF
//      * ↓
//      * PyMuPDF text extraction
//      * ↓
//      * chatbot document session
//      *
//      */

//     await uploadPDFForChat(
//       file
//     );
//   };

//   /*
//    * =========================================================
//    * SEND MESSAGE
//    * =========================================================
//    */

//   const sendMessage = async (
//     text = message
//   ) => {
//     const question =
//       String(text || "").trim();

//     if (
//       !question ||
//       loading ||
//       uploading
//     ) {
//       return;
//     }

//     /*
//      * =======================================================
//      * NO PDF
//      * =======================================================
//      */

//     if (!selectedPDF) {
//       setMessages((previous) => [
//         ...previous,

//         {
//           role: "user",
//           content: question,
//           time:
//             getCurrentTime(),
//         },

//         {
//           role: "assistant",
//           content:
//             "Please upload the generated PDF first so I can answer questions about that document.",
//           time:
//             getCurrentTime(),
//         },
//       ]);

//       setMessage("");

//       return;
//     }

//     /*
//      * =======================================================
//      * MAKE SURE PDF HAS BEEN LOADED
//      * =======================================================
//      */

//     let activeChatId =
//       chatDocumentId;

//     /*
//      * Normally this is already available because the PDF is
//      * uploaded immediately when selected.
//      *
//      * This fallback handles the case where upload is still
//      * needed.
//      */

//     if (!activeChatId) {
//       activeChatId =
//         await uploadPDFForChat(
//           selectedPDF
//         );

//       if (!activeChatId) {
//         setMessage("");
//         return;
//       }
//     }

//     /*
//      * =======================================================
//      * USER MESSAGE
//      * =======================================================
//      */

//     const userMessage = {
//       role: "user",
//       content: question,
//       time:
//         getCurrentTime(),
//     };

//     /*
//      * =======================================================
//      * CONVERSATION HISTORY
//      * =======================================================
//      */

//     const previousMessages =
//       documentChatStarted
//         ? messages
//             .filter(
//               (item) =>
//                 item &&
//                 (
//                   item.role ===
//                     "user" ||
//                   item.role ===
//                     "assistant"
//                 ) &&
//                 item.content
//             )
//             .map((item) => ({
//               role: item.role,
//               content:
//                 String(
//                   item.content
//                 ),
//             }))
//         : [];

//     /*
//      * =======================================================
//      * SHOW USER MESSAGE
//      * =======================================================
//      */

//     setMessages((previous) => [
//       ...previous,
//       userMessage,
//     ]);

//     setMessage("");
//     setLoading(true);
//     setUploadMessage("");

//     const isFirstDocumentRequest =
//       !documentChatStarted;

//     try {
//       /*
//        * =====================================================
//        * CHAT WITH ALREADY LOADED PDF
//        * =====================================================
//        *
//        * IMPORTANT:
//        *
//        * We DO NOT send the PDF again.
//        *
//        * We DO NOT call /api/process.
//        *
//        * We DO NOT run OCR.
//        *
//        * We only send:
//        *
//        *     message
//        *     history
//        *
//        * to the chatbot session.
//        */

//       const response =
//         await fetch(
//           `${API_BASE_URL}/api/chat/${encodeURIComponent(
//             activeChatId
//           )}`,
//           {
//             method: "POST",

//             headers: {
//               "Content-Type":
//                 "application/json",
//             },

//             body: JSON.stringify({
//               message:
//                 question,

//               history:
//                 previousMessages,
//             }),
//           }
//         );

//       /*
//        * =====================================================
//        * READ RESPONSE
//        * =====================================================
//        */

//       let data = null;

//       try {
//         data =
//           await response.json();
//       } catch {
//         data = null;
//       }

//       /*
//        * =====================================================
//        * HANDLE HTTP ERROR
//        * =====================================================
//        */

//       if (!response.ok) {
//         throw new Error(
//           data?.detail ||
//             "Unable to contact the chatbot."
//         );
//       }

//       /*
//        * =====================================================
//        * HANDLE API ERROR
//        * =====================================================
//        */

//       if (!data?.success) {
//         throw new Error(
//           data?.detail ||
//             "Unable to contact the chatbot."
//         );
//       }

//       /*
//        * =====================================================
//        * FIRST REQUEST
//        * =====================================================
//        *
//        * First Send:
//        *
//        * Summary
//        * +
//        * Answer
//        *
//        * Later Sends:
//        *
//        * Answer
//        */

//       setMessages((previous) => {
//         const newMessages = [];

//         if (
//           isFirstDocumentRequest &&
//           data?.summary &&
//           String(
//             data.summary
//           ).trim()
//         ) {
//           newMessages.push({
//             role: "assistant",
//             content:
//               String(
//                 data.summary
//               ),
//             time:
//               getCurrentTime(),
//           });
//         }

//         newMessages.push({
//           role: "assistant",
//           content:
//             data?.answer ||
//             "I could not generate an answer.",
//           time:
//             getCurrentTime(),
//         });

//         return [
//           ...previous,
//           ...newMessages,
//         ];
//       });

//       setDocumentChatStarted(
//         true
//       );
//     } catch (error) {
//       console.error(
//         "Chatbot error:",
//         error
//       );

//       setMessages((previous) => [
//         ...previous,
//         {
//           role: "assistant",
//           content:
//             error?.message ||
//             "Something went wrong while contacting the chatbot.",
//           time:
//             getCurrentTime(),
//         },
//       ]);
//     } finally {
//       setLoading(false);
//     }
//   };

//   /*
//    * =========================================================
//    * FORM SUBMIT
//    * =========================================================
//    */

//   const handleSubmit = (
//     event
//   ) => {
//     event.preventDefault();

//     sendMessage();
//   };

//   /*
//    * =========================================================
//    * RENDER
//    * =========================================================
//    */

//   return (
//     <div className="chatbot-page">

//       <div className="chatbot-header">

//         <div className="chatbot-header-icon">
//           <span>▣</span>
//         </div>

//         <div>
//           <h1>Chatbot</h1>

//           <p>
//             Ask anything about your documents, specifications, or get help with the OCRFlow system.
//           </p>
//         </div>

//       </div>

//       <div className="chatbot-layout">

//         <section className="chatbot-main-card">

//           <div
//             className="chatbot-messages"
//             ref={
//               messagesContainerRef
//             }
//           >

//             {messages.map(
//               (item, index) => (
//                 <div
//                   className={`chat-message ${
//                     item.role ===
//                     "user"
//                       ? "chat-message-user"
//                       : "chat-message-assistant"
//                   }`}
//                   key={`${item.role}-${index}`}
//                 >

//                   {item.role ===
//                     "assistant" && (
//                     <div className="assistant-avatar">
//                       ✦
//                     </div>
//                   )}

//                   <div className="chat-message-content">

//                     <div className="chat-bubble">

//                       <div className="chat-text">
//                         {
//                           item.content
//                         }
//                       </div>

//                       {item.details && (
//                         <div className="chat-details">

//                           <strong>
//                             Supported Languages
//                           </strong>

//                           <ul>
//                             {item.details.map(
//                               (
//                                 detail,
//                                 detailIndex
//                               ) => (
//                                 <li
//                                   key={
//                                     detailIndex
//                                   }
//                                 >
//                                   {
//                                     detail
//                                   }
//                                 </li>
//                               )
//                             )}
//                           </ul>

//                         </div>
//                       )}

//                     </div>

//                     <span className="chat-time">
//                       {
//                         item.time
//                       }
//                     </span>

//                   </div>

//                 </div>
//               )
//             )}

//             {loading && (
//               <div className="chat-message chat-message-assistant">

//                 <div className="assistant-avatar">
//                   ✦
//                 </div>

//                 <div className="chat-message-content">

//                   <div className="chat-bubble chatbot-loading-bubble">

//                     <span className="typing-dot"></span>
//                     <span className="typing-dot"></span>
//                     <span className="typing-dot"></span>

//                   </div>

//                 </div>

//               </div>
//             )}

//             {uploading && (
//               <div className="chat-message chat-message-assistant">

//                 <div className="assistant-avatar">
//                   ✦
//                 </div>

//                 <div className="chat-message-content">

//                   <div className="chat-bubble chatbot-loading-bubble">

//                     <span className="typing-dot"></span>
//                     <span className="typing-dot"></span>
//                     <span className="typing-dot"></span>

//                   </div>

//                 </div>

//               </div>
//             )}

//           </div>

//           <div className="chat-suggestions">

//             <button
//               type="button"
//               onClick={() =>
//                 sendMessage(
//                   "What is OCRFlow?"
//                 )
//               }
//               disabled={
//                 loading ||
//                 uploading
//               }
//             >
//               What is OCRFlow?
//             </button>

//             <button
//               type="button"
//               onClick={() =>
//                 sendMessage(
//                   "Supported file formats?"
//                 )
//               }
//               disabled={
//                 loading ||
//                 uploading
//               }
//             >
//               Supported file formats?
//             </button>

//             <button
//               type="button"
//               onClick={() =>
//                 sendMessage(
//                   "How to extract text?"
//                 )
//               }
//               disabled={
//                 loading ||
//                 uploading
//               }
//             >
//               How to extract text
//             </button>

//             <button
//               type="button"
//               onClick={() =>
//                 sendMessage(
//                   "Show me the pipeline"
//                 )
//               }
//               disabled={
//                 loading ||
//                 uploading
//               }
//             >
//               Show me the pipeline
//             </button>

//           </div>

//           <form
//             className="chat-input-area"
//             onSubmit={
//               handleSubmit
//             }
//           >

//             <span
//               className="chat-attachment-icon"
//               onClick={
//                 handleAttachmentClick
//               }
//               role="button"
//               tabIndex={0}
//               onKeyDown={(
//                 event
//               ) => {
//                 if (
//                   event.key ===
//                     "Enter" ||
//                   event.key ===
//                     " "
//                 ) {
//                   event.preventDefault();

//                   handleAttachmentClick();
//                 }
//               }}
//               title="Upload PDF"
//               aria-label="Upload PDF"
//             >
//               📎
//             </span>

//             <input
//               ref={fileInputRef}
//               type="file"
//               accept="application/pdf,.pdf"
//               onChange={
//                 handleFileChange
//               }
//               style={{
//                 display: "none",
//               }}
//             />

//             <input
//               type="text"
//               value={message}
//               onChange={(
//                 event
//               ) =>
//                 setMessage(
//                   event.target.value
//                 )
//               }
//               placeholder="Type your message..."
//               disabled={
//                 loading ||
//                 uploading
//               }
//             />

//             <button
//               type="submit"
//               className="chat-send-button"
//               disabled={
//                 loading ||
//                 uploading ||
//                 !message.trim()
//               }
//               aria-label="Send message"
//             >
//               ➤
//             </button>

//           </form>

//           {uploadMessage && (
//             <div
//               style={{
//                 padding:
//                   "0 20px 12px",
//                 fontSize:
//                   "13px",
//                 opacity: 0.75,
//               }}
//             >
//               {
//                 uploadMessage
//               }
//             </div>
//           )}

//         </section>

//         <aside className="chatbot-sidebar">

//           <div className="chatbot-sidebar-card">

//             <div className="sidebar-title">

//               <span>ϟ</span>

//               <span>
//                 Quick Questions
//               </span>

//             </div>

//             <div className="quick-question-list">

//               {quickQuestions.map(
//                 (question) => (
//                   <button
//                     key={question}
//                     type="button"
//                     className="quick-question-button"
//                     onClick={() =>
//                       sendMessage(
//                         question
//                       )
//                     }
//                     disabled={
//                       loading ||
//                       uploading
//                     }
//                   >

//                     <span>
//                       {
//                         question
//                       }
//                     </span>

//                     <span>
//                       ›
//                     </span>

//                   </button>
//                 )
//               )}

//             </div>

//           </div>

//           <div className="chatbot-sidebar-card">

//             <div className="sidebar-title">

//               <span>✣</span>

//               <span>
//                 Features
//               </span>

//             </div>

//             <div className="feature-list">

//               {features.map(
//                 (feature) => (
//                   <div
//                     className="feature-item"
//                     key={
//                       feature.title
//                     }
//                   >

//                     <div className="feature-icon">
//                       {
//                         feature.icon
//                       }
//                     </div>

//                     <div className="feature-content">

//                       <strong>
//                         {
//                           feature.title
//                         }
//                       </strong>

//                       <span>
//                         {
//                           feature.description
//                         }
//                       </span>

//                     </div>

//                   </div>
//                 )
//               )}

//             </div>

//           </div>

//           <div className="chatbot-help-card">

//             <div className="help-icon">
//               ⓘ
//             </div>

//             <div>

//               <strong>
//                 Need help?
//               </strong>

//               <p>
//                 Ask anything about OCRFlow or your documents.
//                 <br />
//                 I'm here to help.
//               </p>

//             </div>

//           </div>

//         </aside>

//       </div>

//     </div>
//   );
// }

// function getCurrentTime() {
//   return new Date().toLocaleTimeString(
//     [],
//     {
//       hour: "numeric",
//       minute: "2-digit",
//     }
//   );
// }

// export default Chatbot;






























import React, {
  useEffect,
  useRef,
  useState,
} from "react";

import "./Chatbot.css";
// import "./ChatbotExtraction.css";

const API_BASE_URL =
  "http://127.0.0.1:8000";

const quickQuestions = [
  "What is OCRFlow?",
  "Supported file formats?",
  "How to extract text?",
  "What languages are supported?",
];

const features = [
  {
    icon: "▣",
    title: "Document Understanding",
    description:
      "Get detailed insights about your documents.",
  },
  {
    icon: "◎",
    title: "Multi-language Support",
    description:
      "Works with 90+ languages.",
  },
  {
    icon: "▤",
    title: "Structured Data",
    description:
      "Extract and organize data in JSON, tables, etc.",
  },
  {
    icon: "▧",
    title: "Easy Integration",
    description:
      "Use the extracted data for your workflows.",
  },
];

/*
 * =========================================================
 * THE THREE ACTION BUTTONS
 * =========================================================
 *
 * All three work on the document that was ALREADY scanned
 * (the latest one, or the one passed as the `jobId` prop).
 * Nothing is uploaded.
 *
 * 1. fields -> backend sends the scanned document text to the
 *              Groq API; Groq decides which fields matter and
 *              returns fields + values.
 * 2. json   -> the database-ready JSON of that Groq result.
 * 3. save   -> stores that Groq result in MySQL
 *              (tables are created automatically if missing).
 */

const ACTIONS = {
  fields: {
    label: "Show fields & values",
    userText:
      "Show the fields and values of the scanned document",
    status:
      "Groq is reading the document and extracting the important fields...",
  },

  json: {
    label: "Get database-ready JSON",
    userText:
      "Give me the database-ready JSON of the extracted fields",
    status:
      "Preparing the database-ready JSON...",
  },

  save: {
    label: "Save to database",
    userText:
      "Save the extracted fields to the database",
    status:
      "Saving the extracted fields to MySQL...",
  },
};

const NO_DOCUMENT_MESSAGE =
  "No scanned document found yet. Scan a document on the Documents page first, then come back here.";

/*
 * =========================================================
 * HELPERS
 * =========================================================
 */

function getCurrentTime() {
  return new Date().toLocaleTimeString(
    [],
    {
      hour: "numeric",
      minute: "2-digit",
    }
  );
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function errorText(data, fallback) {
  const detail = data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => item?.msg || JSON.stringify(item))
      .join("; ");
  }

  return fallback;
}

function humanize(text) {
  return String(text || "document")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}

function pageRange(doc) {
  const start = doc?.page_start;
  const end = doc?.page_end;

  if (start == null) {
    return "";
  }

  if (end == null || end === start) {
    return `Page ${start}`;
  }

  return `Pages ${start}-${end}`;
}

function downloadJsonFile(record, filename) {
  const baseName = String(filename || "document")
    .replace(/\.[^.]+$/, "")
    .replace(/[^\w.-]+/g, "_");

  const blob = new Blob(
    [JSON.stringify(record, null, 2)],
    { type: "application/json" }
  );

  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");

  link.href = url;
  link.download = `${baseName}_extracted.json`;

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

/*
 * =========================================================
 * RESULT CARD: FIELDS & VALUES
 * =========================================================
 */

function FieldsCard({ data }) {
  const documents = data?.documents || [];

  return (
    <div className="extraction-card">

      <div className="extraction-meta">
        {data?.filename ? `${data.filename} · ` : ""}
        {data?.document_count} document(s) ·{" "}
        {data?.field_count} fields · extracted by{" "}
        {data?.model || "Groq"}
      </div>

      {documents.map((doc) => (
        <div
          className="extraction-doc"
          key={doc.document_index}
        >

          <div className="extraction-doc-header">
            <strong>
              Document {doc.document_index}:{" "}
              {humanize(doc.document_type)}
            </strong>

            <span>{pageRange(doc)}</span>
          </div>

          {doc.title && (
            <div className="extraction-doc-title">
              {doc.title}
            </div>
          )}

          {doc.summary && (
            <p className="extraction-doc-summary">
              {doc.summary}
            </p>
          )}

          <div className="extraction-table-wrap">
            <table className="extraction-table">

              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th>Type</th>
                  <th>Page</th>
                </tr>
              </thead>

              <tbody>
                {(doc.fields || []).map((field) => (
                  <tr key={field.key}>

                    <td title={field.key}>
                      {field.label}
                    </td>

                    <td>
                      {field.value}

                      {field.normalized_value &&
                        field.normalized_value !==
                          field.value && (
                          <div className="extraction-normalized">
                            → {field.normalized_value}
                          </div>
                        )}
                    </td>

                    <td>{field.data_type}</td>

                    <td>{field.page ?? "-"}</td>

                  </tr>
                ))}
              </tbody>

            </table>
          </div>

          {(doc.tables || []).map((table, tableIndex) => (
            <div
              className="extraction-subtable"
              key={`${table.name}-${tableIndex}`}
            >

              <div className="extraction-subtable-title">
                {table.name}
              </div>

              <div className="extraction-table-wrap">
                <table className="extraction-table">

                  <thead>
                    <tr>
                      {table.columns.map(
                        (column, columnIndex) => (
                          <th key={columnIndex}>
                            {column}
                          </th>
                        )
                      )}
                    </tr>
                  </thead>

                  <tbody>
                    {table.rows.map(
                      (row, rowIndex) => (
                        <tr key={rowIndex}>
                          {row.map(
                            (cell, cellIndex) => (
                              <td key={cellIndex}>
                                {cell}
                              </td>
                            )
                          )}
                        </tr>
                      )
                    )}
                  </tbody>

                </table>
              </div>

            </div>
          ))}

        </div>
      ))}

    </div>
  );
}

/*
 * =========================================================
 * RESULT CARD: DATABASE-READY JSON
 * =========================================================
 */

function JsonCard({ record }) {
  const [copied, setCopied] = useState(false);

  const text = JSON.stringify(record, null, 2);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="extraction-card">

      <div className="extraction-toolbar">

        <span className="extraction-meta">
          {record?.document_count} document(s) ·{" "}
          {record?.field_count} fields
        </span>

        <div className="extraction-toolbar-buttons">

          <button
            type="button"
            onClick={handleCopy}
          >
            {copied ? "Copied" : "Copy JSON"}
          </button>

          <button
            type="button"
            onClick={() =>
              downloadJsonFile(
                record,
                record?.filename
              )
            }
          >
            Download .json
          </button>

        </div>

      </div>

      <pre className="extraction-json">
        {text}
      </pre>

    </div>
  );
}

/*
 * =========================================================
 * RESULT CARD: SAVED TO DATABASE
 * =========================================================
 */

function SavedCard({ data }) {
  return (
    <div className="extraction-card">

      <div className="extraction-saved-title">
        ✔ Saved to MySQL
      </div>

      <ul className="extraction-saved-list">
        <li>
          Extraction ID: {data?.extraction_id}
        </li>
        <li>
          Documents saved: {data?.document_count}
        </li>
        <li>
          Fields saved: {data?.field_count}
        </li>
        <li>
          Tables:{" "}
          {(data?.tables || []).join(", ")}
        </li>
      </ul>

    </div>
  );
}

function Chatbot({ jobId: jobIdProp = null }) {
  /*
   * =========================================================
   * CHAT MESSAGES
   * =========================================================
   */

  const [
    messages,
    setMessages,
  ] = useState([
    {
      role: "assistant",
      content:
        "OCRFlow supports 90+ languages for document processing and OCR.",
      details: [
        "translate documents",
        "summary of a document",
        "shows important fields and values",
        "gives structured json",
        "saves fields into database"
        
      ],
      
    },
  ]);

  const [
    message,
    setMessage,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    statusText,
    setStatusText,
  ] = useState("");

  /*
   * =========================================================
   * ACTIVE (ALREADY SCANNED) DOCUMENT
   * =========================================================
   *
   * No upload. The chatbot works on:
   *
   *   1. the `jobId` prop, if the parent passes one
   *   2. ?job_id=... in the page URL
   *   3. the most recently scanned document
   *      (GET /api/extract/latest-job)
   */

  const [
    activeJob,
    setActiveJob,
  ] = useState(null);

  const [
    jobLookupFailed,
    setJobLookupFailed,
  ] = useState(false);

  /*
   * Job id for which free-text chat (summary + answers)
   * has already started.
   */

  const chatStartedForJobRef =
    useRef(null);

  const messagesContainerRef =
    useRef(null);

  /*
   * =========================================================
   * SCROLL CHAT CONTAINER
   * =========================================================
   */

  useEffect(() => {
    const container =
      messagesContainerRef.current;

    if (!container) {
      return;
    }

    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  /*
   * =========================================================
   * FIND THE SCANNED DOCUMENT
   * =========================================================
   */

  const resolveActiveJob = async () => {
    if (jobIdProp) {
      const job = {
        job_id: String(jobIdProp),
        filename: null,
      };

      setActiveJob((previous) =>
        previous?.job_id === job.job_id
          ? previous
          : job
      );

      setJobLookupFailed(false);

      return job;
    }

    const params = new URLSearchParams(
      window.location.search
    );

    const urlJobId =
      params.get("job_id") ||
      params.get("jobId");

    if (urlJobId) {
      const job = {
        job_id: String(urlJobId),
        filename: null,
      };

      setActiveJob((previous) =>
        previous?.job_id === job.job_id
          ? previous
          : job
      );

      setJobLookupFailed(false);

      return job;
    }

    let response;

    try {
      response = await fetch(
        `${API_BASE_URL}/api/extract/latest-job`
      );
    } catch {
      setJobLookupFailed(true);

      throw new Error(
        `Could not reach the backend at ${API_BASE_URL}. Make sure the API server is running.`
      );
    }

    const data = await readJson(response);

    if (!response.ok || !data?.job_id) {
      setActiveJob(null);
      setJobLookupFailed(true);

      throw new Error(
        errorText(
          data,
          NO_DOCUMENT_MESSAGE
        )
      );
    }

    const job = {
      job_id: String(data.job_id),
      filename: data.filename || null,
    };

    setActiveJob(job);
    setJobLookupFailed(false);

    return job;
  };

  /*
   * Show which document the chatbot is working on as soon
   * as the page opens.
   */

  useEffect(() => {
    resolveActiveJob().catch(() => {});

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobIdProp]);

  /*
   * =========================================================
   * ADD A MESSAGE
   * =========================================================
   */

  const addMessage = (item) => {
    setMessages((previous) => [
      ...previous,
      {
        time: getCurrentTime(),
        ...item,
      },
    ]);
  };

  /*
   * =========================================================
   * THE THREE ACTION BUTTONS
   * =========================================================
   */

  const runAction = async (action) => {
    if (loading) {
      return;
    }

    const config = ACTIONS[action];

    if (!config) {
      return;
    }

    addMessage({
      role: "user",
      kind: "action",
      content: config.userText,
    });

    setLoading(true);
    setStatusText(config.status);

    try {
      const job =
        await resolveActiveJob();

      const base = `${API_BASE_URL}/api/extract/${encodeURIComponent(
        job.job_id
      )}`;

      let response;

      try {
        if (action === "fields") {
          response = await fetch(
            `${base}/fields?refresh=true`,
            { method: "POST" }
          );
        } else if (action === "json") {
          response = await fetch(
            `${base}/json`
          );
        } else {
          response = await fetch(
            `${base}/save`,
            { method: "POST" }
          );
        }
      } catch {
        throw new Error(
          `Could not reach the backend at ${API_BASE_URL}. Make sure the API server is running.`
        );
      }

      const data =
        await readJson(response);

      if (!response.ok || !data?.success) {
        throw new Error(
          errorText(
            data,
            "The request failed. Please try again."
          )
        );
      }

      if (action === "fields") {
        addMessage({
          role: "assistant",
          kind: "fields",
          content: `Groq extracted ${data.field_count} fields from ${data.document_count} document(s).`,
          payload: data,
        });
      } else if (action === "json") {
        addMessage({
          role: "assistant",
          kind: "json",
          content:
            "Database-ready JSON generated by Groq:",
          payload: data.record,
        });
      } else {
        addMessage({
          role: "assistant",
          kind: "saved",
          content:
            "The extracted fields were saved to the database.",
          payload: data,
        });
      }
    } catch (error) {
      console.error(
        "Extraction action error:",
        error
      );

      addMessage({
        role: "assistant",
        content:
          error?.message ||
          "Something went wrong.",
      });
    } finally {
      setLoading(false);
      setStatusText("");
    }
  };

  /*
   * =========================================================
   * FREE-TEXT QUESTIONS ABOUT THE DOCUMENT
   * =========================================================
   */

  const sendMessage = async (
    text = message
  ) => {
    const question =
      String(text || "").trim();

    if (!question || loading) {
      return;
    }

    setMessage("");

    addMessage({
      role: "user",
      content: question,
    });

    setLoading(true);
    setStatusText("");

    try {
      const job =
        await resolveActiveJob();

      const isFirstDocumentRequest =
        chatStartedForJobRef.current !==
        job.job_id;

      const previousMessages =
        isFirstDocumentRequest
          ? []
          : messages
              .filter(
                (item) =>
                  item &&
                  !item.kind &&
                  (item.role === "user" ||
                    item.role ===
                      "assistant") &&
                  item.content
              )
              .map((item) => ({
                role: item.role,
                content: String(
                  item.content
                ),
              }));

      let response;

      try {
        response = await fetch(
          `${API_BASE_URL}/api/chat/${encodeURIComponent(
            job.job_id
          )}`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              message: question,
              history: previousMessages,
            }),
          }
        );
      } catch {
        throw new Error(
          `Could not reach the backend at ${API_BASE_URL}. Make sure the API server is running.`
        );
      }

      const data =
        await readJson(response);

      if (!response.ok || !data?.success) {
        throw new Error(
          errorText(
            data,
            "Unable to contact the chatbot."
          )
        );
      }

      const newMessages = [];

      if (
        isFirstDocumentRequest &&
        data?.summary &&
        String(data.summary).trim()
      ) {
        newMessages.push({
          role: "assistant",
          content: String(data.summary),
          time: getCurrentTime(),
        });
      }

      newMessages.push({
        role: "assistant",
        content:
          data?.answer ||
          "I could not generate an answer.",
        time: getCurrentTime(),
      });

      setMessages((previous) => [
        ...previous,
        ...newMessages,
      ]);

      chatStartedForJobRef.current =
        job.job_id;
    } catch (error) {
      console.error(
        "Chatbot error:",
        error
      );

      addMessage({
        role: "assistant",
        content:
          error?.message ||
          "Something went wrong while contacting the chatbot.",
      });
    } finally {
      setLoading(false);
    }
  };

  /*
   * =========================================================
   * FORM SUBMIT
   * =========================================================
   */

  const handleSubmit = (event) => {
    event.preventDefault();

    sendMessage();
  };

  /*
   * =========================================================
   * RENDER ONE MESSAGE BODY
   * =========================================================
   */

  const renderBody = (item) => {
    if (item.kind === "fields") {
      return (
        <>
          <div className="chat-text">
            {item.content}
          </div>

          <FieldsCard
            data={item.payload}
          />
        </>
      );
    }

    if (item.kind === "json") {
      return (
        <>
          <div className="chat-text">
            {item.content}
          </div>

          <JsonCard
            record={item.payload}
          />
        </>
      );
    }

    if (item.kind === "saved") {
      return (
        <>
          <div className="chat-text">
            {item.content}
          </div>

          <SavedCard
            data={item.payload}
          />
        </>
      );
    }

    return (
      <div className="chat-text">
        {item.content}
      </div>
    );
  };

  const isRich = (item) =>
    item.kind === "fields" ||
    item.kind === "json" ||
    item.kind === "saved";

  /*
   * =========================================================
   * RENDER
   * =========================================================
   */

  return (
    <div className="chatbot-page">

      <div className="chatbot-header">

        <div className="chatbot-header-icon">
          <span>▣</span>
        </div>

        <div>
          <h1>Chatbot</h1>

          
        </div>

      </div>

      <div className="chatbot-layout">

        <section className="chatbot-main-card">

          <div
            className="chatbot-messages"
            ref={
              messagesContainerRef
            }
          >

            {messages.map(
              (item, index) => (
                <div
                  className={`chat-message ${
                    item.role ===
                    "user"
                      ? "chat-message-user"
                      : "chat-message-assistant"
                  }`}
                  key={`${item.role}-${index}`}
                >

                  {item.role ===
                    "assistant" && (
                    <div className="assistant-avatar">
                      ✦
                    </div>
                  )}

                  <div
                    className={`chat-message-content${
                      isRich(item)
                        ? " chat-message-content-wide"
                        : ""
                    }`}
                  >

                    <div
                      className={`chat-bubble${
                        isRich(item)
                          ? " chat-bubble-wide"
                          : ""
                      }`}
                    >

                      {renderBody(item)}

                      {item.details && (
                        <div className="chat-details">

                          <strong>
                            Supported Features
                          </strong>

                          <ul>
                            {item.details.map(
                              (
                                detail,
                                detailIndex
                              ) => (
                                <li
                                  key={
                                    detailIndex
                                  }
                                >
                                  {
                                    detail
                                  }
                                </li>
                              )
                            )}
                          </ul>

                        </div>
                      )}

                    </div>

                    <span className="chat-time">
                      {
                        item.time
                      }
                    </span>

                  </div>

                </div>
              )
            )}

            {loading && (
              <div className="chat-message chat-message-assistant">

                <div className="assistant-avatar">
                  ✦
                </div>

                <div className="chat-message-content">

                  <div className="chat-bubble chatbot-loading-bubble">

                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>

                  </div>

                  {statusText && (
                    <span className="chat-status-text">
                      {statusText}
                    </span>
                  )}

                </div>

              </div>
            )}

          </div>

          <div className="chat-suggestions extraction-actions">

            <button
              type="button"
              onClick={() =>
                runAction("fields")
              }
              disabled={loading}
            >
              {ACTIONS.fields.label}
            </button>

            <button
              type="button"
              onClick={() =>
                runAction("json")
              }
              disabled={loading}
            >
              {ACTIONS.json.label}
            </button>

            <button
              type="button"
              onClick={() =>
                runAction("save")
              }
              disabled={loading}
            >
              {ACTIONS.save.label}
            </button>

          </div>

          <div className="extraction-active-doc">

            {activeJob ? (
              <>
                Working on:{" "}
                <strong>
                  {activeJob.filename ||
                    activeJob.job_id}
                </strong>
              </>
            ) : jobLookupFailed ? (
              "No scanned document found yet. Scan one on the Documents page."
            ) : (
              "Looking for the latest scanned document..."
            )}

          </div>

          <form
            className="chat-input-area"
            onSubmit={
              handleSubmit
            }
          >

            <input
              type="text"
              value={message}
              onChange={(
                event
              ) =>
                setMessage(
                  event.target.value
                )
              }
              placeholder="Type your message..."
              disabled={loading}
            />

            <button
              type="submit"
              className="chat-send-button"
              disabled={
                loading ||
                !message.trim()
              }
              aria-label="Send message"
            >
              ➤
            </button>

          </form>

        </section>

        

      </div>

    </div>
  );
}

export { FieldsCard, JsonCard, SavedCard };

export default Chatbot;