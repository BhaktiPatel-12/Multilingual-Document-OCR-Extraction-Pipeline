import React, {
  useEffect,
  useRef,
  useState,
} from "react";

import "./Chatbot.css";

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

function Chatbot() {
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
        "OCRFlow supports 90+ languages for document processing and OCR. Our live demonstration focuses on English, Hindi and Gujarati, but the system can handle a wide range of other languages as well.",
      details: [
        "90+ languages (global support)",
        "Demo languages: English, Hindi, Gujarati",
        "Includes major international and Indian languages",
      ],
      time: "10:24 AM",
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

  /*
   * =========================================================
   * CHAT DOCUMENT
   * =========================================================
   *
   * This is the ALREADY GENERATED STRUCTURED PDF.
   *
   * IMPORTANT:
   *
   * This chatbot does NOT run OCR.
   *
   * The PDF is uploaded to:
   *
   *     POST /api/chat/upload
   *
   * The backend extracts selectable text from the PDF using
   * PyMuPDF and creates a chatbot document session.
   */

  const [
    selectedPDF,
    setSelectedPDF,
  ] = useState(null);

  const [
    chatDocumentId,
    setChatDocumentId,
  ] = useState(null);

  const [
    documentChatStarted,
    setDocumentChatStarted,
  ] = useState(false);

  const [
    uploading,
    setUploading,
  ] = useState(false);

  const [
    uploadMessage,
    setUploadMessage,
  ] = useState("");

  const fileInputRef =
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
   * OPEN PDF PICKER
   * =========================================================
   */

  const handleAttachmentClick = () => {
    if (
      loading ||
      uploading ||
      fileInputRef.current === null
    ) {
      return;
    }

    fileInputRef.current.click();
  };

  /*
   * =========================================================
   * UPLOAD STRUCTURED PDF TO CHATBOT
   * =========================================================
   *
   * IMPORTANT:
   *
   * This does NOT call /api/process.
   *
   * Therefore:
   *
   * NO OCR
   * NO Surya
   * NO preprocessing
   * NO OCR pipeline
   * NO status polling
   *
   * The backend only extracts text from the already-generated
   * structured PDF.
   * =========================================================
   */

  const uploadPDFForChat = async (
    file
  ) => {
    if (!file) {
      return null;
    }

    setUploading(true);
    setUploadMessage(
      "Loading PDF for chatbot..."
    );

    try {
      const formData =
        new FormData();

      formData.append(
        "file",
        file
      );

      const response =
        await fetch(
          `${API_BASE_URL}/api/chat/upload`,
          {
            method: "POST",
            body: formData,
          }
        );

      let data = null;

      try {
        data =
          await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Unable to load the PDF for chatbot."
        );
      }

      if (!data?.success) {
        throw new Error(
          data?.detail ||
            "Unable to load the PDF for chatbot."
        );
      }

      /*
       * The corrected backend returns chat_id.
       *
       * Accept a few compatible names so the frontend is
       * tolerant of the response structure.
       */

      const returnedChatId =
        data?.chat_id ||
        data?.document_id ||
        data?.chat_document_id;

      if (!returnedChatId) {
        throw new Error(
          "Chatbot backend did not return a chat ID."
        );
      }

      setChatDocumentId(
        String(returnedChatId)
      );

      setDocumentChatStarted(
        false
      );

      setUploadMessage(
        "PDF loaded successfully. Click Send to generate the document summary and answer your question."
      );

      return String(
        returnedChatId
      );
    } catch (error) {
      console.error(
        "Chatbot PDF upload error:",
        error
      );

      setUploadMessage("");

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            error?.message ||
            "Unable to load the PDF for chatbot.",
          time:
            getCurrentTime(),
        },
      ]);

      return null;
    } finally {
      setUploading(false);
    }
  };

  /*
   * =========================================================
   * PDF SELECTION
   * =========================================================
   */

  const handleFileChange = async (
    event
  ) => {
    const file =
      event.target.files?.[0];

    /*
     * Allow selecting the same file again.
     */

    event.target.value = "";

    if (!file) {
      return;
    }

    /*
     * =======================================================
     * PDF VALIDATION
     * =======================================================
     */

    const isPDF =
      file.type ===
        "application/pdf" ||
      file.name
        .toLowerCase()
        .endsWith(".pdf");

    if (!isPDF) {
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            "Please select a PDF file.",
          time:
            getCurrentTime(),
        },
      ]);

      return;
    }

    /*
     * =======================================================
     * 50 MB LIMIT
     * =======================================================
     */

    if (
      file.size >
      50 * 1024 * 1024
    ) {
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            "File size must be less than 50 MB.",
          time:
            getCurrentTime(),
        },
      ]);

      return;
    }

    /*
     * =======================================================
     * STORE SELECTED PDF
     * =======================================================
     */

    setSelectedPDF(file);

    /*
     * A new PDF means a completely new chatbot session.
     */

    setChatDocumentId(null);

    setDocumentChatStarted(
      false
    );

    setUploadMessage("");

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content:
          `Uploaded: ${file.name}`,
        time:
          getCurrentTime(),
      },
    ]);

    /*
     * =======================================================
     * SEND PDF TO CHATBOT BACKEND
     * =======================================================
     *
     * This is NOT OCR.
     *
     * The backend only:
     *
     * PDF
     * ↓
     * PyMuPDF text extraction
     * ↓
     * chatbot document session
     *
     */

    await uploadPDFForChat(
      file
    );
  };

  /*
   * =========================================================
   * SEND MESSAGE
   * =========================================================
   */

  const sendMessage = async (
    text = message
  ) => {
    const question =
      String(text || "").trim();

    if (
      !question ||
      loading ||
      uploading
    ) {
      return;
    }

    /*
     * =======================================================
     * NO PDF
     * =======================================================
     */

    if (!selectedPDF) {
      setMessages((previous) => [
        ...previous,

        {
          role: "user",
          content: question,
          time:
            getCurrentTime(),
        },

        {
          role: "assistant",
          content:
            "Please upload the generated PDF first so I can answer questions about that document.",
          time:
            getCurrentTime(),
        },
      ]);

      setMessage("");

      return;
    }

    /*
     * =======================================================
     * MAKE SURE PDF HAS BEEN LOADED
     * =======================================================
     */

    let activeChatId =
      chatDocumentId;

    /*
     * Normally this is already available because the PDF is
     * uploaded immediately when selected.
     *
     * This fallback handles the case where upload is still
     * needed.
     */

    if (!activeChatId) {
      activeChatId =
        await uploadPDFForChat(
          selectedPDF
        );

      if (!activeChatId) {
        setMessage("");
        return;
      }
    }

    /*
     * =======================================================
     * USER MESSAGE
     * =======================================================
     */

    const userMessage = {
      role: "user",
      content: question,
      time:
        getCurrentTime(),
    };

    /*
     * =======================================================
     * CONVERSATION HISTORY
     * =======================================================
     */

    const previousMessages =
      documentChatStarted
        ? messages
            .filter(
              (item) =>
                item &&
                (
                  item.role ===
                    "user" ||
                  item.role ===
                    "assistant"
                ) &&
                item.content
            )
            .map((item) => ({
              role: item.role,
              content:
                String(
                  item.content
                ),
            }))
        : [];

    /*
     * =======================================================
     * SHOW USER MESSAGE
     * =======================================================
     */

    setMessages((previous) => [
      ...previous,
      userMessage,
    ]);

    setMessage("");
    setLoading(true);
    setUploadMessage("");

    const isFirstDocumentRequest =
      !documentChatStarted;

    try {
      /*
       * =====================================================
       * CHAT WITH ALREADY LOADED PDF
       * =====================================================
       *
       * IMPORTANT:
       *
       * We DO NOT send the PDF again.
       *
       * We DO NOT call /api/process.
       *
       * We DO NOT run OCR.
       *
       * We only send:
       *
       *     message
       *     history
       *
       * to the chatbot session.
       */

      const response =
        await fetch(
          `${API_BASE_URL}/api/chat/${encodeURIComponent(
            activeChatId
          )}`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              message:
                question,

              history:
                previousMessages,
            }),
          }
        );

      /*
       * =====================================================
       * READ RESPONSE
       * =====================================================
       */

      let data = null;

      try {
        data =
          await response.json();
      } catch {
        data = null;
      }

      /*
       * =====================================================
       * HANDLE HTTP ERROR
       * =====================================================
       */

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Unable to contact the chatbot."
        );
      }

      /*
       * =====================================================
       * HANDLE API ERROR
       * =====================================================
       */

      if (!data?.success) {
        throw new Error(
          data?.detail ||
            "Unable to contact the chatbot."
        );
      }

      /*
       * =====================================================
       * FIRST REQUEST
       * =====================================================
       *
       * First Send:
       *
       * Summary
       * +
       * Answer
       *
       * Later Sends:
       *
       * Answer
       */

      setMessages((previous) => {
        const newMessages = [];

        if (
          isFirstDocumentRequest &&
          data?.summary &&
          String(
            data.summary
          ).trim()
        ) {
          newMessages.push({
            role: "assistant",
            content:
              String(
                data.summary
              ),
            time:
              getCurrentTime(),
          });
        }

        newMessages.push({
          role: "assistant",
          content:
            data?.answer ||
            "I could not generate an answer.",
          time:
            getCurrentTime(),
        });

        return [
          ...previous,
          ...newMessages,
        ];
      });

      setDocumentChatStarted(
        true
      );
    } catch (error) {
      console.error(
        "Chatbot error:",
        error
      );

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            error?.message ||
            "Something went wrong while contacting the chatbot.",
          time:
            getCurrentTime(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  /*
   * =========================================================
   * FORM SUBMIT
   * =========================================================
   */

  const handleSubmit = (
    event
  ) => {
    event.preventDefault();

    sendMessage();
  };

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

          <p>
            Ask anything about your documents, specifications, or get help with the OCRFlow system.
          </p>
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

                  <div className="chat-message-content">

                    <div className="chat-bubble">

                      <div className="chat-text">
                        {
                          item.content
                        }
                      </div>

                      {item.details && (
                        <div className="chat-details">

                          <strong>
                            Supported Languages
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

                </div>

              </div>
            )}

            {uploading && (
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

                </div>

              </div>
            )}

          </div>

          <div className="chat-suggestions">

            <button
              type="button"
              onClick={() =>
                sendMessage(
                  "What is OCRFlow?"
                )
              }
              disabled={
                loading ||
                uploading
              }
            >
              What is OCRFlow?
            </button>

            <button
              type="button"
              onClick={() =>
                sendMessage(
                  "Supported file formats?"
                )
              }
              disabled={
                loading ||
                uploading
              }
            >
              Supported file formats?
            </button>

            <button
              type="button"
              onClick={() =>
                sendMessage(
                  "How to extract text?"
                )
              }
              disabled={
                loading ||
                uploading
              }
            >
              How to extract text
            </button>

            <button
              type="button"
              onClick={() =>
                sendMessage(
                  "Show me the pipeline"
                )
              }
              disabled={
                loading ||
                uploading
              }
            >
              Show me the pipeline
            </button>

          </div>

          <form
            className="chat-input-area"
            onSubmit={
              handleSubmit
            }
          >

            <span
              className="chat-attachment-icon"
              onClick={
                handleAttachmentClick
              }
              role="button"
              tabIndex={0}
              onKeyDown={(
                event
              ) => {
                if (
                  event.key ===
                    "Enter" ||
                  event.key ===
                    " "
                ) {
                  event.preventDefault();

                  handleAttachmentClick();
                }
              }}
              title="Upload PDF"
              aria-label="Upload PDF"
            >
              📎
            </span>

            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={
                handleFileChange
              }
              style={{
                display: "none",
              }}
            />

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
              disabled={
                loading ||
                uploading
              }
            />

            <button
              type="submit"
              className="chat-send-button"
              disabled={
                loading ||
                uploading ||
                !message.trim()
              }
              aria-label="Send message"
            >
              ➤
            </button>

          </form>

          {uploadMessage && (
            <div
              style={{
                padding:
                  "0 20px 12px",
                fontSize:
                  "13px",
                opacity: 0.75,
              }}
            >
              {
                uploadMessage
              }
            </div>
          )}

        </section>

        <aside className="chatbot-sidebar">

          <div className="chatbot-sidebar-card">

            <div className="sidebar-title">

              <span>ϟ</span>

              <span>
                Quick Questions
              </span>

            </div>

            <div className="quick-question-list">

              {quickQuestions.map(
                (question) => (
                  <button
                    key={question}
                    type="button"
                    className="quick-question-button"
                    onClick={() =>
                      sendMessage(
                        question
                      )
                    }
                    disabled={
                      loading ||
                      uploading
                    }
                  >

                    <span>
                      {
                        question
                      }
                    </span>

                    <span>
                      ›
                    </span>

                  </button>
                )
              )}

            </div>

          </div>

          <div className="chatbot-sidebar-card">

            <div className="sidebar-title">

              <span>✣</span>

              <span>
                Features
              </span>

            </div>

            <div className="feature-list">

              {features.map(
                (feature) => (
                  <div
                    className="feature-item"
                    key={
                      feature.title
                    }
                  >

                    <div className="feature-icon">
                      {
                        feature.icon
                      }
                    </div>

                    <div className="feature-content">

                      <strong>
                        {
                          feature.title
                        }
                      </strong>

                      <span>
                        {
                          feature.description
                        }
                      </span>

                    </div>

                  </div>
                )
              )}

            </div>

          </div>

          <div className="chatbot-help-card">

            <div className="help-icon">
              ⓘ
            </div>

            <div>

              <strong>
                Need help?
              </strong>

              <p>
                Ask anything about OCRFlow or your documents.
                <br />
                I'm here to help.
              </p>

            </div>

          </div>

        </aside>

      </div>

    </div>
  );
}

function getCurrentTime() {
  return new Date().toLocaleTimeString(
    [],
    {
      hour: "numeric",
      minute: "2-digit",
    }
  );
}

export default Chatbot;