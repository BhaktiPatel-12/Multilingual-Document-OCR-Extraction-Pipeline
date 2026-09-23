import { useRef, useState } from "react";

import {
  Search,
  Bell,
  ChevronDown,
  Upload,
  Settings,
  AlignLeft,
  Download,
  FileText,
  Globe2,
  Check,
  Image as ImageIcon,
} from "lucide-react";

import "./App.css";

import Documents from "./Documents/Documents.jsx";
import Results from "./Results/Results.jsx";
import Chatbot from "./chatbot/Chatbot.jsx";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const fileInputRef = useRef(null);

  // ==========================================================
  // GLOBAL APP STATE
  // ==========================================================

  const [currentPage, setCurrentPage] = useState("home");

  const [selectedFile, setSelectedFile] = useState(null);

  const [dragging, setDragging] = useState(false);

  const [languages, setLanguages] = useState({
    english: true,
    hindi: false,
    gujarati: false,
  });

  const [processing, setProcessing] = useState(false);

  const [progress, setProgress] = useState(0);

  const [statusMessage, setStatusMessage] = useState("");

  // ==========================================================
  // ACTIVE DOCUMENT STATE
  // ==========================================================
  //
  // These states belong to App.jsx.
  //
  // They are NOT stored inside individual pages.
  //
  // Therefore:
  //
  // Home -> Documents -> Chatbot -> Results
  //
  // all use the SAME active document.
  //
  // Browser refresh intentionally resets these states.
  // ==========================================================

  const [jobId, setJobId] = useState(null);

  const [result, setResult] = useState(null);

  // ==========================================================
  // SESSION DOCUMENT HISTORY
  // ==========================================================
  //
  // This is intentionally kept only in React memory.
  //
  // It survives navbar/page changes because App remains mounted.
  //
  // It is NOT stored in localStorage.
  //
  // Browser refresh -> React starts again -> history resets.
  // ==========================================================

  const [documentsHistory, setDocumentsHistory] = useState([]);

  // ==========================================================
  // NAVIGATION
  // ==========================================================

  const goToPage = (page) => {
    // Do not allow navigation away while OCR is running.
    if (processing) {
      return;
    }

    // IMPORTANT:
    // Only change the page.
    //
    // Do NOT reset:
    // jobId
    // result
    // documentsHistory
    // selectedFile
    //
    // This is what keeps the document available across pages.
    setCurrentPage(page);
  };

  // ==========================================================
  // FILE VALIDATION
  // ==========================================================

  const handleFileSelect = (file) => {
    if (!file) {
      return;
    }

    const isPDF =
      file.type === "application/pdf" ||
      /\.pdf$/i.test(file.name);

    if (!isPDF) {
      alert("Please select a PDF file.");
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      alert("Maximum file size is 50 MB.");
      return;
    }

    // A NEW document is being selected.
    //
    // Replace only the active document.
    //
    // IMPORTANT:
    // documentsHistory is NOT cleared.
    setSelectedFile(file);
    setResult(null);
    setJobId(null);
    setProgress(0);
    setStatusMessage("");
  };

  const handleInputChange = (event) => {
    const file = event.target.files?.[0];

    if (file) {
      handleFileSelect(file);
    }
  };

  // ==========================================================
  // DRAG & DROP
  // ==========================================================

  const handleDragOver = (event) => {
    event.preventDefault();

    if (!processing) {
      setDragging(true);
    }
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (event) => {
    event.preventDefault();

    setDragging(false);

    if (processing) {
      return;
    }

    const file = event.dataTransfer.files?.[0];

    if (file) {
      handleFileSelect(file);
    }
  };

  // ==========================================================
  // LANGUAGE UI
  // ==========================================================

  const toggleLanguage = (language) => {
    setLanguages((current) => ({
      ...current,
      [language]: !current[language],
    }));
  };

  // ==========================================================
  // FILE PICKER
  // ==========================================================

  const openFilePicker = () => {
    if (processing) {
      return;
    }

    fileInputRef.current?.click();
  };

  // ==========================================================
  // START OCR
  // ==========================================================

  const startOCR = async () => {
    if (!selectedFile) {
      alert("Please select a PDF first.");
      return;
    }

    if (processing) {
      return;
    }

    setProcessing(true);
    setProgress(5);
    setStatusMessage("Uploading document...");

    // IMPORTANT:
    // Never clear documentsHistory here.
    //
    // Previous completed documents remain available
    // during this browser session.

    setResult(null);

    const formData = new FormData();

    formData.append("file", selectedFile);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/process`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        let errorMessage =
          "Could not start OCR processing.";

        try {
          const errorData = await response.json();

          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch {
          // Ignore JSON parsing errors.
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();

      if (!data.job_id) {
        throw new Error(
          "Backend did not return a job ID."
        );
      }

      // Store active job in App state.
      setJobId(data.job_id);

      setProgress(10);

      setStatusMessage(
        "Document uploaded. OCR processing started."
      );

      await monitorJob(
        data.job_id,
        selectedFile?.name
      );
    } catch (error) {
      console.error("OCR error:", error);

      setProcessing(false);

      setProgress(0);

      setStatusMessage("");

      alert(
        error.message ||
          "Something went wrong while processing the document."
      );
    }
  };

  // ==========================================================
  // MONITOR OCR JOB
  // ==========================================================

  const monitorJob = async (id, filename) => {
    while (true) {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/status/${id}`
        );

        if (!response.ok) {
          throw new Error(
            "Could not retrieve OCR processing status."
          );
        }

        const data = await response.json();

        const backendProgress =
          typeof data.progress === "number"
            ? data.progress
            : 0;

        setProgress(backendProgress);

        setStatusMessage(
          data.message ||
            "Processing document..."
        );

        // ======================================================
        // COMPLETED
        // ======================================================

        if (data.status === "completed") {
          const completedResult =
            data.result || null;

          // Store completed result globally in App.
          setResult(completedResult);

          // Keep active job globally available.
          setJobId(id);

          setProcessing(false);

          setProgress(100);

          setStatusMessage(
            "OCR processing completed successfully."
          );

          // ====================================================
          // ADD DOCUMENT TO SESSION HISTORY
          // ====================================================

          if (completedResult) {
            const historyItem = {
              jobId: id,

              filename:
                filename ||
                data.filename ||
                completedResult.filename ||
                "Processed document",

              result: completedResult,

              processedAt:
                new Date().toISOString(),
            };

            setDocumentsHistory(
              (currentHistory) => {
                const existingIndex =
                  currentHistory.findIndex(
                    (document) =>
                      document.jobId === id
                  );

                // Update existing job instead of
                // creating a duplicate.
                if (existingIndex !== -1) {
                  const updatedHistory = [
                    ...currentHistory,
                  ];

                  updatedHistory[
                    existingIndex
                  ] = historyItem;

                  return updatedHistory;
                }

                // Add new document while preserving
                // every previous document.
                return [
                  ...currentHistory,
                  historyItem,
                ];
              }
            );
          }

          return;
        }

        // ======================================================
        // FAILED
        // ======================================================

        if (data.status === "failed") {
          throw new Error(
            data.error ||
              data.message ||
              "OCR processing failed."
          );
        }

        // ======================================================
        // STILL PROCESSING
        // ======================================================

        await new Promise((resolve) =>
          setTimeout(resolve, 1500)
        );
      } catch (error) {
        console.error(
          "Status error:",
          error
        );

        setProcessing(false);

        setProgress(0);

        setStatusMessage("");

        alert(
          error.message ||
            "Could not monitor OCR processing."
        );

        return;
      }
    }
  };

  // ==========================================================
  // DOWNLOAD OUTPUT
  // ==========================================================

  const downloadResult = (type) => {
    if (!jobId) {
      alert(
        "No completed OCR job is available."
      );

      return;
    }

    const endpoints = {
      json: `/api/download/${jobId}/json`,

      txt: `/api/download/${jobId}/txt`,

      structured_pdf:
        `/api/download/${jobId}/structured-pdf`,

      language_highlighted_pdf:
        `/api/download/${jobId}/language-highlighted-pdf`,
    };

    const endpoint = endpoints[type];

    if (!endpoint) {
      return;
    }

    const downloadUrl =
      `${API_BASE_URL}${endpoint}`;

    window.open(
      downloadUrl,
      "_blank"
    );
  };

  // ==========================================================
  // RESET CURRENT DOCUMENT
  // ==========================================================

  const resetDocument = () => {
    if (processing) {
      return;
    }

    // IMPORTANT:
    //
    // This resets ONLY the active document.
    //
    // It does NOT clear documentsHistory.
    //
    // Example:
    //
    // Document A
    // Document B
    // Document C
    //
    // remain in session history after
    // "Process Another Document".

    setSelectedFile(null);

    setResult(null);

    setJobId(null);

    setProgress(0);

    setStatusMessage("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="astra-app">

      {/* =====================================================
          BACKGROUND
      ====================================================== */}

      <div className="background-shape background-shape-top" />

      <div className="background-shape background-shape-bottom" />

      <div className="background-dot dot-one" />

      <div className="background-dot dot-two" />

      <div className="background-dot dot-three" />

      {/* =====================================================
          HEADER
      ====================================================== */}

      <header className="topbar">
        <div className="topbar-inner">

          {/* BRAND */}

          <div className="brand">

            <div className="brand-logo">

              <div className="brand-logo-symbol">
                <span />
                <span />
                <span />
              </div>

            </div>

            <div className="brand-text">

              <div className="brand-name">
                ASTRA-OCR
              </div>

              <div className="brand-subtitle">
                Multilingual Document Intelligence
              </div>

            </div>

          </div>

          {/* NAVIGATION */}

          <nav className="navigation">

            <button
              className={`nav-item ${
                currentPage === "home"
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                goToPage("home")
              }
              type="button"
            >
              Home
            </button>

            <button
              className={`nav-item ${
                currentPage === "documents"
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                goToPage("documents")
              }
              type="button"
            >
              Documents
            </button>

            <button
              className={`nav-item ${
                currentPage === "Chatbot"
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                goToPage("Chatbot")
              }
              type="button"
            >
              Chatbot
            </button>

            <button
              className={`nav-item ${
                currentPage === "results"
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                goToPage("results")
              }
              type="button"
            >
              Data Hub
            </button>

            

          </nav>

          {/* HEADER ACTIONS */}

          <div className="header-actions">

            <div className="search-box">
              <Search size={17} />

              <input
                type="text"
                placeholder="Search documents..."
              />
            </div>

            <button
              className="header-icon-button"
              type="button"
            >
              <Bell size={19} />
            </button>

            <div className="profile">

              <div className="profile-avatar">
                B
              </div>

              <span className="profile-name">
                Bhakti
              </span>

              <ChevronDown size={14} />

            </div>

          </div>

        </div>
      </header>

      {/* =====================================================
          PAGE CONTENT
      ====================================================== */}

      {currentPage === "documents" ? (

        <Documents
  jobId={jobId}
  result={result}
  documentsHistory={documentsHistory}
  setJobId={setJobId}
  setResult={setResult}
  setDocumentsHistory={setDocumentsHistory}
/>

      ) : currentPage === "Chatbot" ? (

        <Chatbot
          jobId={jobId}
           
          result={result}
          documentsHistory={
            documentsHistory
          }
          setJobId={setJobId}
           setResult={setResult}
        />

      ) : currentPage === "results" ? (

        <Results
  result={result}
  jobId={jobId}
  documentsHistory={documentsHistory}
/>

      ) : (

        /* ===================================================
           HOME PAGE
        ==================================================== */

        <main className="home-content">

          {/* =================================================
              HERO
          ================================================== */}

          <section className="hero-section">

            <div className="hero-copy">

              <h1>

                <span className="hero-title-dark">
                  Multilingual
                </span>

                <span className="hero-title-light">
                  Document OCR
                </span>

              </h1>

              <p className="hero-description">
                Extract text from your documents in multiple languages
                <br />
                with high accuracy. Turn your PDFs and images into
                <br />
                structured, searchable, and machine-readable data.
              </p>

              <div className="process-steps">

                <div className="process-step">

                  <div className="step-icon">
                    <Upload size={19} />
                  </div>

                  <div className="step-text">

                    <div className="step-title">
                      Upload
                    </div>

                    <div className="step-subtitle">
                      PDF
                    </div>

                  </div>

                </div>

                <div className="step-arrow">
                  ›
                </div>

                <div className="process-step">

                  <div className="step-icon">
                    <Settings size={19} />
                  </div>

                  <div className="step-text">

                    <div className="step-title">
                      Process
                    </div>

                    <div className="step-subtitle">
                      AI Pipeline
                    </div>

                  </div>

                </div>

                <div className="step-arrow">
                  ›
                </div>

                <div className="process-step">

                  <div className="step-icon">
                    <AlignLeft size={19} />
                  </div>

                  <div className="step-text">

                    <div className="step-title">
                      Extract
                    </div>

                    <div className="step-subtitle">
                      Structured Data
                    </div>

                  </div>

                </div>

                <div className="step-arrow">
                  ›
                </div>

                <div className="process-step">

                  <div className="step-icon">
                    <Download size={19} />
                  </div>

                  <div className="step-text">

                    <div className="step-title active-step">
                      Export
                    </div>

                    <div className="step-subtitle">
                      JSON / TXT / PDF
                    </div>

                  </div>

                </div>

              </div>

            </div>

            {/* HERO ILLUSTRATION */}

            <div className="hero-illustration">

              <div className="illustration-pdf">

                <div className="pdf-label">
                  PDF
                </div>

                <div className="document-lines">
                  <span />
                  <span />
                  <span />
                  <span />
                  <span />
                </div>

              </div>

              <div className="illustration-image">

                <div className="image-placeholder">
                  <ImageIcon size={33} />
                </div>

                <div className="image-lines">
                  <span />
                  <span />
                  <span />
                </div>

              </div>

              <div className="illustration-language">

                <div className="language-english">
                  English
                </div>

                <div className="language-hindi">
                  हिंदी
                </div>

                <div className="language-gujarati">
                  ગુજરાતી
                </div>

              </div>

              <div className="illustration-arrow">

                <svg
                  viewBox="0 0 160 90"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >

                  <path
                    d="M5 15C45 10 92 15 125 60"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />

                  <path
                    d="M119 51L125 60L115 61"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                </svg>

              </div>

              <div className="illustration-output">
                <FileText size={34} />
              </div>

            </div>

          </section>

          {/* =================================================
              UPLOAD
          ================================================== */}

          <section
            className={`upload-section ${
              dragging
                ? "upload-dragging"
                : ""
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >

            <div className="upload-box">

              {!selectedFile ? (

                <>
                  <div className="upload-cloud">
                    <Upload size={35} />
                  </div>

                  <div className="upload-title">
                    Drag & drop your PDF here
                  </div>

                  <div className="upload-or">
                    or
                  </div>

                  <button
                    className="browse-button"
                    onClick={openFilePicker}
                    type="button"
                  >
                    Browse Files
                  </button>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,application/pdf"
                    onChange={handleInputChange}
                    hidden
                  />

                  <div className="upload-meta">
                    PDF
                    <span>•</span>
                    Max 50MB
                  </div>
                </>

              ) : (

                <div className="selected-file">

                  <div className="selected-file-icon">
                    <FileText size={29} />
                  </div>

                  <div className="selected-file-details">

                    <div className="selected-file-name">
                      {selectedFile.name}
                    </div>

                    <div className="selected-file-size">
                      {(
                        selectedFile.size /
                        (1024 * 1024)
                      ).toFixed(2)}{" "}
                      MB
                    </div>

                  </div>

                  <button
                    className="change-file-button"
                    onClick={openFilePicker}
                    disabled={processing}
                    type="button"
                  >
                    Change
                  </button>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,application/pdf"
                    onChange={handleInputChange}
                    hidden
                  />

                </div>

              )}

            </div>

          </section>

          {/* =================================================
              LANGUAGE
          ================================================== */}

          <section className="language-section">

            <div className="language-heading">

              <Globe2 size={15} />

              <span>
                Select Languages
              </span>

            </div>

            <div className="language-buttons">

              <button
                className={`language-button ${
                  languages.english
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  toggleLanguage("english")
                }
                type="button"
              >

                {languages.english && (
                  <Check size={13} />
                )}

                <span>
                  English
                </span>

              </button>

              <button
                className={`language-button ${
                  languages.hindi
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  toggleLanguage("hindi")
                }
                type="button"
              >

                {languages.hindi && (
                  <Check size={13} />
                )}

                <span>
                  हिंदी
                </span>

              </button>

              <button
                className={`language-button ${
                  languages.gujarati
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  toggleLanguage("gujarati")
                }
                type="button"
              >

                {languages.gujarati && (
                  <Check size={13} />
                )}

                <span>
                  ગુજરાતી
                </span>

              </button>

            </div>

          </section>

          {/* =================================================
              PROCESS CONTROL
          ================================================== */}

          {selectedFile && !result && (

            <section className="processing-panel">

              <button
                className="process-button"
                onClick={startOCR}
                disabled={processing}
                type="button"
              >
                {processing
                  ? "Processing..."
                  : "Process Document"}
              </button>

              {processing && (

                <div className="progress-container">

                  <div className="progress-track">

                    <div
                      className="progress-bar"
                      style={{
                        width: `${progress}%`,
                      }}
                    />

                  </div>

                  <div className="progress-info">

                    <span>
                      {statusMessage}
                    </span>

                    <span>
                      {progress}%
                    </span>

                  </div>

                </div>

              )}

            </section>

          )}

          {/* =================================================
              RESULTS
          ================================================== */}

          {result && (

            <section className="results-panel">

              <div className="results-title">
                OCR Complete
              </div>

              <div className="results-message">
                {statusMessage}
              </div>

              <div className="download-buttons">

                <button
                  onClick={() =>
                    downloadResult("json")
                  }
                  type="button"
                >
                  Download JSON
                </button>

                <button
                  onClick={() =>
                    downloadResult("txt")
                  }
                  type="button"
                >
                  Download TXT
                </button>

                <button
                  onClick={() =>
                    downloadResult(
                      "structured_pdf"
                    )
                  }
                  type="button"
                >
                  Structured PDF
                </button>

                <button
                  onClick={() =>
                    downloadResult(
                      "language_highlighted_pdf"
                    )
                  }
                  type="button"
                >
                  Highlighted PDF
                </button>

              </div>

              <button
                className="new-document-button"
                onClick={resetDocument}
                type="button"
              >
                Process Another Document
              </button>

            </section>

          )}

        </main>

      )}

    </div>
  );
}

export default App;