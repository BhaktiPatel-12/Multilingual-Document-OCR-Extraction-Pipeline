import React, { useEffect, useRef, useState } from "react";
import "./Documents.css";

const API_BASE_URL = "http://127.0.0.1:8000";

const DOWNLOAD_ENDPOINTS = {
  json: "/api/download/{job_id}/json",
  txt: "/api/download/{job_id}/txt",
  structured_pdf: "/api/download/{job_id}/structured-pdf",
  language_highlighted_pdf:
    "/api/download/{job_id}/language-highlighted-pdf",
};

const PROCESSING_STAGES = [
  {
    id: "upload",
    label: "Document Uploaded",
    minProgress: 0,
  },
  {
    id: "pdf",
    label: "PDF Page Extraction",
    minProgress: 10,
  },
  {
    id: "preprocess",
    label: "Image Preprocessing",
    minProgress: 20,
  },
  {
    id: "layout",
    label: "Layout Detection",
    minProgress: 30,
  },
  {
    id: "ocr",
    label: "Text Detection & OCR",
    minProgress: 45,
  },
  {
    id: "language",
    label: "Language Detection",
    minProgress: 60,
  },
  {
    id: "structure",
    label: "Structure Reconstruction",
    minProgress: 72,
  },
  {
    id: "output",
    label: "Output Generation",
    minProgress: 85,
  },
  {
    id: "searchable",
    label: "Searchable PDF",
    minProgress: 95,
  },
];

const getStageIndexFromProgress = (
  currentProgress,
  message = ""
) => {
  const normalizedMessage = String(
    message || ""
  ).toLowerCase();

  if (
    normalizedMessage.includes("upload") ||
    normalizedMessage.includes("starting")
  ) {
    return 0;
  }

  if (
    normalizedMessage.includes("render") ||
    normalizedMessage.includes("page extraction") ||
    normalizedMessage.includes("extract")
  ) {
    return 1;
  }

  if (
    normalizedMessage.includes("preprocess") ||
    normalizedMessage.includes("pre-processing")
  ) {
    return 2;
  }

  if (
    normalizedMessage.includes("layout") ||
    normalizedMessage.includes("direction")
  ) {
    return 3;
  }

  if (
    normalizedMessage.includes("ocr") ||
    normalizedMessage.includes("text detection") ||
    normalizedMessage.includes("recognition")
  ) {
    return 4;
  }

  if (
    normalizedMessage.includes("language") ||
    normalizedMessage.includes("detecting language")
  ) {
    return 5;
  }

  if (
    normalizedMessage.includes("structure") ||
    normalizedMessage.includes("correction")
  ) {
    return 6;
  }

  if (
    normalizedMessage.includes("output") ||
    normalizedMessage.includes("generat")
  ) {
    return 7;
  }

  if (
    normalizedMessage.includes("searchable") ||
    normalizedMessage.includes("pdf")
  ) {
    return 8;
  }

  let index = 0;

  PROCESSING_STAGES.forEach(
    (stage, stageIndex) => {
      if (
        currentProgress >= stage.minProgress
      ) {
        index = stageIndex;
      }
    }
  );

  return Math.min(
    index,
    PROCESSING_STAGES.length - 1
  );
};

function Documents({
  jobId: parentJobId = null,
  result: parentResult = null,
  documentsHistory: parentDocumentsHistory = null,
  setJobId: setParentJobId = null,
  setResult: setParentResult = null,
  setDocumentsHistory: setParentDocumentsHistory = null,
}) {
  const fileInputRef = useRef(null);

  /*
   * =========================================================
   * ACTIVE DOCUMENT STATE
   * =========================================================
   *
   * App.jsx is the source of truth when these props are passed.
   *
   * The local fallbacks only prevent this component from breaking
   * if Documents is temporarily rendered without the parent props.
   */

  const [localSelectedFile, setLocalSelectedFile] =
    useState(null);

  const [localJobId, setLocalJobId] =
    useState(null);

  const [localResult, setLocalResult] =
    useState(null);

  const [localDocumentsHistory, setLocalDocumentsHistory] =
    useState([]);

  const selectedFile = localSelectedFile;

  const jobId =
    parentJobId !== null &&
    parentJobId !== undefined
      ? parentJobId
      : localJobId;

  const result =
    parentResult !== null &&
    parentResult !== undefined
      ? parentResult
      : localResult;

  const documentsHistory =
    Array.isArray(parentDocumentsHistory)
      ? parentDocumentsHistory
      : localDocumentsHistory;

  const updateJobId = (value) => {
    if (typeof setParentJobId === "function") {
      setParentJobId(value);
    }

    setLocalJobId(value);
  };

  const updateResult = (value) => {
    if (typeof setParentResult === "function") {
      setParentResult(value);
    }

    setLocalResult(value);
  };

  const updateDocumentsHistory = (updater) => {
    if (typeof setParentDocumentsHistory === "function") {
      setParentDocumentsHistory(updater);
    }

    setLocalDocumentsHistory(updater);
  };

  /*
   * =========================================================
   * UI STATE
   * =========================================================
   */

  const [isDragging, setIsDragging] =
    useState(false);

  const [isProcessing, setIsProcessing] =
    useState(false);

  const [progress, setProgress] =
    useState(0);

  const [statusMessage, setStatusMessage] =
    useState("");

  const [errorMessage, setErrorMessage] =
    useState("");

  const [downloadStatus, setDownloadStatus] =
    useState("");

  /*
   * =========================================================
   * PREVIEW STATE
   * =========================================================
   */

  const [previewFile, setPreviewFile] =
    useState(null);

  const [previewLoading, setPreviewLoading] =
    useState(false);

  const [previewError, setPreviewError] =
    useState("");

  const [previewContent, setPreviewContent] =
    useState("");

  const [previewUrl, setPreviewUrl] =
    useState(null);

  /*
   * =========================================================
   * CURRENT PROCESSING STAGE
   * =========================================================
   */

  const currentStageIndex =
    getStageIndexFromProgress(
      progress,
      statusMessage
    );

  /*
   * =========================================================
   * CLEAN PREVIEW URL
   * =========================================================
   */

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  /*
   * =========================================================
   * CLOSE PREVIEW WITH ESC
   * =========================================================
   */

  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key === "Escape") {
        closePreview();
      }
    };

    document.addEventListener(
      "keydown",
      handleEscape
    );

    return () => {
      document.removeEventListener(
        "keydown",
        handleEscape
      );
    };
  }, [previewUrl]);

  /*
   * =========================================================
   * FILE VALIDATION
   * =========================================================
   */

  const handleFile = (file) => {
    if (!file) {
      return;
    }

    setErrorMessage("");
    setStatusMessage("");
    setDownloadStatus("");

    if (
      file.type !== "application/pdf" &&
      !file.name
        .toLowerCase()
        .endsWith(".pdf")
    ) {
      setErrorMessage(
        "Please select a PDF file."
      );
      return;
    }

    if (
      file.size >
      50 * 1024 * 1024
    ) {
      setErrorMessage(
        "File size must be less than 50 MB."
      );
      return;
    }

    /*
     * New file becomes the current document.
     *
     * IMPORTANT:
     * History is NOT touched.
     */

    setLocalSelectedFile(file);

    updateResult(null);
    updateJobId(null);

    setProgress(0);
    setStatusMessage("");
    setErrorMessage("");
    setDownloadStatus("");

    closePreview();
  };

  /*
   * =========================================================
   * BROWSE
   * =========================================================
   */

  const handleBrowse = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  /*
   * =========================================================
   * FILE CHANGE
   * =========================================================
   */

  const handleFileChange = (event) => {
    const file =
      event.target.files?.[0];

    if (file) {
      handleFile(file);
    }
  };

  /*
   * =========================================================
   * DRAG & DROP
   * =========================================================
   */

  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();

    setIsDragging(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    event.stopPropagation();

    setIsDragging(false);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();

    setIsDragging(false);

    const file =
      event.dataTransfer.files?.[0];

    if (file) {
      handleFile(file);
    }
  };

  /*
   * =========================================================
   * PROCESS DOCUMENT
   * =========================================================
   */

  const handleProcess = async () => {
    if (!selectedFile) {
      handleBrowse();
      return;
    }

    setIsProcessing(true);
    setProgress(5);
    setStatusMessage(
      "Uploading document..."
    );
    setErrorMessage("");
    setDownloadStatus("");

    updateResult(null);

    try {
      const formData =
        new FormData();

      formData.append(
        "file",
        selectedFile
      );

      const response =
        await fetch(
          `${API_BASE_URL}/api/process`,
          {
            method: "POST",
            body: formData,
          }
        );

      if (!response.ok) {
        let message =
          "Unable to start OCR processing.";

        try {
          const errorData =
            await response.json();

          message =
            errorData.detail ||
            message;
        } catch {
          // Keep default message.
        }

        throw new Error(message);
      }

      const data =
        await response.json();

      if (!data.job_id) {
        throw new Error(
          "The OCR server did not return a job ID."
        );
      }

      updateJobId(data.job_id);

      setProgress(10);

      setStatusMessage(
        "OCR processing started..."
      );

      await monitorJob(
        data.job_id,
        selectedFile.name
      );
    } catch (error) {
      console.error(
        "Processing error:",
        error
      );

      setIsProcessing(false);
      setProgress(0);

      if (
        error instanceof TypeError &&
        error.message
          .toLowerCase()
          .includes("fetch")
      ) {
        setErrorMessage(
          "The OCR server could not be reached. Please make sure the Astra-OCR API is running."
        );
      } else {
        setErrorMessage(
          error.message ||
            "Something went wrong while processing the document."
        );
      }

      setStatusMessage("");
    }
  };

  /*
   * =========================================================
   * POLL OCR JOB
   * =========================================================
   */

  const monitorJob = async (
    id,
    filename
  ) => {
    let consecutiveConnectionErrors = 0;

    while (true) {
      try {
        const response =
          await fetch(
            `${API_BASE_URL}/api/status/${id}`,
            {
              method: "GET",
              cache: "no-store",
            }
          );

        if (!response.ok) {
          throw new Error(
            `Status request failed with HTTP ${response.status}.`
          );
        }

        const data =
          await response.json();

        consecutiveConnectionErrors = 0;

        if (
          typeof data.progress ===
          "number"
        ) {
          setProgress(
            Math.min(
              Math.max(
                data.progress,
                0
              ),
              100
            )
          );
        }

        if (data.message) {
          setStatusMessage(
            data.message
          );
        }

        /*
         * =====================================================
         * COMPLETED
         * =====================================================
         */

        if (
          data.status ===
          "completed"
        ) {
          setProgress(100);

          setStatusMessage(
            "OCR completed. Your files are ready."
          );

          const completedResult =
            data.result || null;

          const completedJobId =
            data.job_id || id;

          updateJobId(
            completedJobId
          );

          updateResult(
            completedResult
          );

          setIsProcessing(false);

          /*
           * ===================================================
           * ADD / UPDATE HISTORY
           * ===================================================
           */

          if (completedResult) {
            updateDocumentsHistory(
              (currentHistory) => {
                const safeHistory =
                  Array.isArray(
                    currentHistory
                  )
                    ? currentHistory
                    : [];

                const existingIndex =
                  safeHistory.findIndex(
                    (document) =>
                      document.jobId ===
                      completedJobId
                  );

                const historyItem = {
                  jobId:
                    completedJobId,

                  filename:
                    filename ||
                    data.filename ||
                    "Processed document",

                  result:
                    completedResult,

                  processedAt:
                    new Date().toISOString(),
                };

                /*
                 * Existing document:
                 * update it instead of creating a duplicate.
                 */

                if (
                  existingIndex !==
                  -1
                ) {
                  const updatedHistory =
                    [
                      ...safeHistory,
                    ];

                  updatedHistory[
                    existingIndex
                  ] =
                    historyItem;

                  return updatedHistory;
                }

                /*
                 * New document:
                 * append to in-memory history.
                 */

                return [
                  ...safeHistory,
                  historyItem,
                ];
              }
            );
          }

          return;
        }

        /*
         * =====================================================
         * FAILED
         * =====================================================
         */

        if (
          data.status ===
          "failed"
        ) {
          throw new Error(
            data.error ||
              data.message ||
              "OCR processing failed on the server."
          );
        }

        await sleep(1000);
      } catch (error) {
        console.error(
          "Status check error:",
          error
        );

        consecutiveConnectionErrors += 1;

        if (
          consecutiveConnectionErrors <=
          5
        ) {
          setStatusMessage(
            "Waiting for OCR server... reconnecting"
          );

          await sleep(1500);

          continue;
        }

        setIsProcessing(false);

        if (
          error instanceof TypeError &&
          error.message
            .toLowerCase()
            .includes("fetch")
        ) {
          setErrorMessage(
            "The OCR server connection was lost while processing."
          );
        } else {
          setErrorMessage(
            error.message ||
              "Unable to retrieve OCR status."
          );
        }

        setStatusMessage("");

        return;
      }
    }
  };

  /*
   * =========================================================
   * SLEEP
   * =========================================================
   */

  const sleep = (milliseconds) => {
    return new Promise(
      (resolve) => {
        setTimeout(
          resolve,
          milliseconds
        );
      }
    );
  };

  /*
   * =========================================================
   * BUILD OUTPUT URL
   * =========================================================
   */

  const getOutputUrl = (
    type,
    customJobId = null
  ) => {
    const activeJobId =
      customJobId || jobId;

    if (!activeJobId) {
      return null;
    }

    const endpointTemplate =
      DOWNLOAD_ENDPOINTS[type];

    if (!endpointTemplate) {
      return null;
    }

    const endpoint =
      endpointTemplate.replace(
        "{job_id}",
        activeJobId
      );

    return `${API_BASE_URL}${endpoint}`;
  };

  /*
   * =========================================================
   * DOWNLOAD OUTPUT
   * =========================================================
   */

  const downloadFile = async (
    type,
    customJobId = null
  ) => {
    const url =
      getOutputUrl(
        type,
        customJobId
      );

    if (!url) {
      setDownloadStatus(
        "The OCR job is not ready yet."
      );

      return;
    }

    try {
      setDownloadStatus(
        "Preparing download..."
      );

      const response =
        await fetch(url);

      if (!response.ok) {
        throw new Error(
          `Download failed with HTTP ${response.status}.`
        );
      }

      const blob =
        await response.blob();

      const blobUrl =
        URL.createObjectURL(
          blob
        );

      const link =
        document.createElement(
          "a"
        );

      link.href = blobUrl;

      const extension =
        type === "json"
          ? "json"
          : type === "txt"
          ? "txt"
          : "pdf";

      link.download =
        `astra-ocr-${type}.${extension}`;

      document.body.appendChild(
        link
      );

      link.click();

      document.body.removeChild(
        link
      );

      URL.revokeObjectURL(
        blobUrl
      );

      setDownloadStatus("");
    } catch (error) {
      console.error(
        "Download error:",
        error
      );

      setDownloadStatus(
        error.message ||
          "Unable to download this output file."
      );
    }
  };

  /*
   * =========================================================
   * PREVIEW OUTPUT
   * =========================================================
   */

  const previewFileOutput = async (
    file,
    customJobId = null
  ) => {
    const activeJobId =
      customJobId || jobId;

    if (!activeJobId) {
      setPreviewError(
        "The OCR job is not ready yet."
      );

      return;
    }

    setPreviewFile(file);
    setPreviewLoading(true);
    setPreviewError("");
    setPreviewContent("");

    if (previewUrl) {
      URL.revokeObjectURL(
        previewUrl
      );

      setPreviewUrl(null);
    }

    try {
      const url =
        getOutputUrl(
          file.key,
          activeJobId
        );

      if (!url) {
        throw new Error(
          "Output URL could not be created."
        );
      }

      const response =
        await fetch(url);

      if (!response.ok) {
        throw new Error(
          `Preview failed with HTTP ${response.status}.`
        );
      }

      /*
       * =======================================================
       * JSON / TXT
       * =======================================================
       */

      if (
        file.key === "json" ||
        file.key === "txt"
      ) {
        const text =
          await response.text();

        if (
          file.key ===
          "json"
        ) {
          try {
            const parsed =
              JSON.parse(text);

            setPreviewContent(
              JSON.stringify(
                parsed,
                null,
                2
              )
            );
          } catch {
            setPreviewContent(
              text
            );
          }
        } else {
          setPreviewContent(
            text
          );
        }

        setPreviewLoading(
          false
        );

        return;
      }

      /*
       * =======================================================
       * PDF
       * =======================================================
       */

      const blob =
        await response.blob();

      const pdfBlob =
        new Blob(
          [blob],
          {
            type: "application/pdf",
          }
        );

      const objectUrl =
        URL.createObjectURL(
          pdfBlob
        );

      setPreviewUrl(
        objectUrl
      );

      setPreviewLoading(
        false
      );
    } catch (error) {
      console.error(
        "Preview error:",
        error
      );

      setPreviewError(
        error.message ||
          "Unable to preview this file."
      );

      setPreviewLoading(
        false
      );
    }
  };

  /*
   * =========================================================
   * CLOSE PREVIEW
   * =========================================================
   */

  const closePreview = () => {
    if (previewUrl) {
      URL.revokeObjectURL(
        previewUrl
      );
    }

    setPreviewUrl(null);
    setPreviewFile(null);
    setPreviewContent("");
    setPreviewError("");
    setPreviewLoading(false);
  };

  /*
   * =========================================================
   * REMOVE CURRENT FILE
   * =========================================================
   */

  const removeFile = () => {
    if (isProcessing) {
      return;
    }

    /*
     * IMPORTANT:
     *
     * Only the current document is cleared.
     *
     * History remains untouched.
     */

    setLocalSelectedFile(null);

    updateResult(null);
    updateJobId(null);

    setProgress(0);
    setStatusMessage("");
    setErrorMessage("");
    setDownloadStatus("");

    closePreview();

    if (fileInputRef.current) {
      fileInputRef.current.value =
        "";
    }
  };

  /*
   * =========================================================
   * NEW DOCUMENT
   * =========================================================
   */

  const startNewDocument = () => {
    if (isProcessing) {
      return;
    }

    /*
     * IMPORTANT:
     *
     * DO NOT clear documentsHistory.
     *
     * This is what keeps:
     *
     * Documents Processed
     *
     * from going back to zero.
     */

    setLocalSelectedFile(null);

    updateResult(null);
    updateJobId(null);

    setProgress(0);
    setStatusMessage("");
    setErrorMessage("");
    setDownloadStatus("");

    closePreview();

    if (fileInputRef.current) {
      fileInputRef.current.value =
        "";
    }

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  /*
   * =========================================================
   * SELECT HISTORY DOCUMENT
   * =========================================================
   */

  const openHistoryDocument = (
    documentItem
  ) => {
    if (!documentItem) {
      return;
    }

    /*
     * History contains the completed OCR result,
     * not the original browser File object.
     *
     * A lightweight PDF-like object is enough
     * for the existing UI.
     */

    setLocalSelectedFile({
      name:
        documentItem.filename ||
        "Processed document",

      size: 0,

      type: "application/pdf",
    });

    updateJobId(
      documentItem.jobId
    );

    updateResult(
      documentItem.result
    );

    setProgress(100);

    setStatusMessage(
      "OCR processing completed."
    );

    setErrorMessage("");
    setDownloadStatus("");

    closePreview();

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  /*
   * =========================================================
   * CLEAR HISTORY
   * =========================================================
   */

  const clearHistory = () => {
    if (isProcessing) {
      return;
    }

    const confirmed =
      window.confirm(
        "Clear all processed document history?"
      );

    if (!confirmed) {
      return;
    }

    updateDocumentsHistory([]);
  };

  /*
   * =========================================================
   * FILE HELPERS
   * =========================================================
   */

  const getFileType = () => {
    if (!selectedFile) {
      return "";
    }

    return "PDF";
  };

  const formatFileSize = (
    bytes
  ) => {
    if (!bytes) {
      return "0 KB";
    }

    if (
      bytes <
      1024 * 1024
    ) {
      return `${(
        bytes / 1024
      ).toFixed(1)} KB`;
    }

    return `${(
      bytes /
      (1024 * 1024)
    ).toFixed(1)} MB`;
  };

  /*
   * =========================================================
   * RESULT STATISTICS
   * =========================================================
   */

  const getPagesProcessedFromResult = (
    documentResult
  ) => {
    if (!documentResult) {
      return 0;
    }

    if (
      typeof documentResult.total_pages ===
      "number"
    ) {
      return documentResult.total_pages;
    }

    if (
      Array.isArray(
        documentResult.pages
      )
    ) {
      return documentResult.pages.length;
    }

    return 0;
  };

  const getLanguagesDetectedFromResult = (
    documentResult
  ) => {
    if (!documentResult) {
      return 0;
    }

    const languages =
      new Set();

    if (
      Array.isArray(
        documentResult.detected_languages
      )
    ) {
      documentResult.detected_languages.forEach(
        (language) => {
          if (language) {
            languages.add(
              String(
                language
              ).toLowerCase()
            );
          }
        }
      );
    }

    if (
      Array.isArray(
        documentResult.pages
      )
    ) {
      documentResult.pages.forEach(
        (page) => {
          if (
            Array.isArray(
              page.detected_languages
            )
          ) {
            page.detected_languages.forEach(
              (language) => {
                if (language) {
                  languages.add(
                    String(
                      language
                    ).toLowerCase()
                  );
                }
              }
            );
          }

          if (
            page.final_result
              ?.detected_languages
          ) {
            const pageLanguages =
              page.final_result
                .detected_languages;

            if (
              Array.isArray(
                pageLanguages
              )
            ) {
              pageLanguages.forEach(
                (language) => {
                  if (language) {
                    languages.add(
                      String(
                        language
                      ).toLowerCase()
                    );
                  }
                }
              );
            }
          }
        }
      );
    }

    return languages.size;
  };

  const getAccuracyFromResult = (
    documentResult
  ) => {
    if (!documentResult) {
      return 0;
    }

    if (
      documentResult.final_quality
    ) {
      const quality =
        documentResult.final_quality;

      if (
        typeof quality.score ===
        "number"
      ) {
        return quality.score;
      }

      if (
        typeof quality.quality_score ===
        "number"
      ) {
        return quality.quality_score;
      }

      if (
        typeof quality.total_score ===
        "number"
      ) {
        return quality.total_score;
      }
    }

    const scores = [];

    if (
      Array.isArray(
        documentResult.pages
      )
    ) {
      documentResult.pages.forEach(
        (page) => {
          const quality =
            page.final_quality;

          if (!quality) {
            return;
          }

          if (
            typeof quality.score ===
            "number"
          ) {
            scores.push(
              quality.score
            );
          } else if (
            typeof quality.quality_score ===
            "number"
          ) {
            scores.push(
              quality.quality_score
            );
          } else if (
            typeof quality.total_score ===
            "number"
          ) {
            scores.push(
              quality.total_score
            );
          }
        }
      );
    }

    if (
      scores.length > 0
    ) {
      return (
        scores.reduce(
          (sum, value) =>
            sum + value,
          0
        ) /
        scores.length
      );
    }

    return 0;
  };

  /*
   * =========================================================
   * TOTAL HISTORY STATISTICS
   * =========================================================
   */

  const documentsProcessed =
    documentsHistory.length;

  const pagesProcessed =
    documentsHistory.reduce(
      (total, documentItem) => {
        return (
          total +
          getPagesProcessedFromResult(
            documentItem.result
          )
        );
      },
      0
    );

  const languagesSet =
    new Set();

  documentsHistory.forEach(
    (documentItem) => {
      const historyResult =
        documentItem.result;

      if (!historyResult) {
        return;
      }

      /*
       * Top-level languages.
       */

      if (
        Array.isArray(
          historyResult.detected_languages
        )
      ) {
        historyResult.detected_languages.forEach(
          (language) => {
            if (language) {
              languagesSet.add(
                String(
                  language
                ).toLowerCase()
              );
            }
          }
        );
      }

      /*
       * Page-level languages.
       */

      if (
        Array.isArray(
          historyResult.pages
        )
      ) {
        historyResult.pages.forEach(
          (page) => {
            if (
              Array.isArray(
                page.detected_languages
              )
            ) {
              page.detected_languages.forEach(
                (language) => {
                  if (language) {
                    languagesSet.add(
                      String(
                        language
                      ).toLowerCase()
                    );
                  }
                }
              );
            }

            const pageLanguages =
              page.final_result
                ?.detected_languages;

            if (
              Array.isArray(
                pageLanguages
              )
            ) {
              pageLanguages.forEach(
                (language) => {
                  if (language) {
                    languagesSet.add(
                      String(
                        language
                      ).toLowerCase()
                    );
                  }
                }
              );
            }
          }
        );
      }
    }
  );

  const languagesDetected =
    languagesSet.size;

  /*
   * Average accuracy across all completed documents.
   */

  const documentAccuracyScores =
    documentsHistory
      .map(
        (documentItem) =>
          getAccuracyFromResult(
            documentItem.result
          )
      )
      .filter(
        (score) =>
          typeof score ===
            "number" &&
          score > 0
      );

  const accuracy =
    documentAccuracyScores.length >
    0
      ? documentAccuracyScores.reduce(
          (sum, value) =>
            sum + value,
          0
        ) /
        documentAccuracyScores.length
      : 0;

  /*
   * =========================================================
   * OUTPUT FILES
   * =========================================================
   */

  const outputFiles = [
    {
      key: "json",
      extension: "JSON",
      title: "OCR JSON",
      description:
        "Machine-readable OCR result containing extracted text, blocks and document data.",
      previewType: "text",
    },
    {
      key: "txt",
      extension: "TXT",
      title: "Plain Text",
      description:
        "Clean extracted text from the processed document.",
      previewType: "text",
    },
    {
      key: "structured_pdf",
      extension: "PDF",
      title: "Structured PDF",
      description:
        "Searchable structured PDF generated from the OCR result.",
      previewType: "pdf",
    },
    {
      key: "language_highlighted_pdf",
      extension: "PDF",
      title: "Language Highlighted PDF",
      description:
        "PDF output with language-specific text highlighting.",
      previewType: "pdf",
    },
  ];

  /*
   * =========================================================
   * RENDER
   * =========================================================
   */

  return (
    <div className="documents-page">
      <main className="documents-content">

        {/* =================================================
            STATISTICS
        ================================================= */}

        <section className="document-stats">

          <div className="stat-card">
            <div className="stat-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>

            <div className="stat-info">
              <span>
                Documents Processed
              </span>

              <strong>
                {documentsProcessed}
              </strong>

              <small>
                Total files
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                />

                <path d="M8 12l2.5 2.5L16 9" />
              </svg>
            </div>

            <div className="stat-info">
              <span>
                Pages Processed
              </span>

              <strong>
                {pagesProcessed}
              </strong>

              <small>
                Total pages
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                />

                <path d="M12 7v10" />

                <path d="M8.5 9.5c0-1.2 1.5-2 3.5-2s3.5.8 3.5 2-1.2 1.8-3.5 2.3-3.5 1.1-3.5 2.3 1.5 2 3.5 2 3.5-.8 3.5-2" />
              </svg>
            </div>

            <div className="stat-info">
              <span>
                Languages Detected
              </span>

              <strong>
                {languagesDetected}
              </strong>

              <small>
                Across processed documents
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                />

                <path d="M12 7v5l3 2" />
              </svg>
            </div>

            <div className="stat-info">
              <span>
                Extraction Accuracy
              </span>

              <strong>
                {accuracy > 0
                  ? `${accuracy.toFixed(
                      1
                    )}%`
                  : "0%"}
              </strong>

              <small>
                Average OCR quality
              </small>
            </div>
          </div>

        </section>

        {/* =================================================
            FILE PREVIEW
        ================================================= */}

        <section className="file-preview-card">

          <div className="preview-header">
            <div className="preview-title">

              <div className="preview-title-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />

                  <polyline points="14 2 14 8 20 8" />

                  <line
                    x1="8"
                    y1="13"
                    x2="16"
                    y2="13"
                  />

                  <line
                    x1="8"
                    y1="17"
                    x2="16"
                    y2="17"
                  />
                </svg>
              </div>

              <h2>
                File Preview
              </h2>

            </div>
          </div>

          <div
            className={`file-preview-area ${
              isDragging
                ? "dragging"
                : ""
            } ${
              selectedFile
                ? "has-file"
                : ""
            }`}
            onDragOver={
              handleDragOver
            }
            onDragLeave={
              handleDragLeave
            }
            onDrop={
              handleDrop
            }
          >

            {!selectedFile ? (
              <div className="empty-preview">

                <div className="empty-file-icon">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                  >
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />

                    <polyline points="14 2 14 8 20 8" />

                    <line
                      x1="8"
                      y1="13"
                      x2="16"
                      y2="13"
                    />

                    <line
                      x1="8"
                      y1="17"
                      x2="13"
                      y2="17"
                    />
                  </svg>
                </div>

                <div className="empty-preview-text">
                  <h3>
                    No file selected
                  </h3>

                  <p>
                    Drag &amp; drop a PDF here
                    or browse your files
                  </p>
                </div>

              </div>
            ) : (
              <div className="selected-file-preview">

                <div className="selected-file-icon">
                  <span>
                    {getFileType()}
                  </span>
                </div>

                <div className="selected-file-details">

                  <h3>
                    {selectedFile.name}
                  </h3>

                  <p>
                    {selectedFile.size
                      ? formatFileSize(
                          selectedFile.size
                        )
                      : "Processed document"}

                    <span className="file-dot">
                      •
                    </span>

                    {isProcessing
                      ? "Processing document..."
                      : result
                      ? "Processing completed"
                      : "Ready for processing"}
                  </p>

                </div>

                {!isProcessing && (
                  <button
                    className="remove-file-button"
                    onClick={
                      removeFile
                    }
                    title="Remove file"
                  >
                    ×
                  </button>
                )}

              </div>
            )}

          </div>

          {errorMessage && (
            <div className="document-error">

              <span className="error-icon">
                !
              </span>

              <span>
                {errorMessage}
              </span>

            </div>
          )}

          {!result && (
            <button
              className={`upload-process-button ${
                isProcessing
                  ? "processing"
                  : ""
              }`}
              onClick={
                handleProcess
              }
              disabled={
                isProcessing
              }
            >
              {isProcessing ? (
                <>
                  <span className="loading-spinner" />

                  Processing...
                </>
              ) : selectedFile ? (
                <>
                  Process Document

                  <span className="button-arrow">
                    →
                  </span>
                </>
              ) : (
                <>
                  Upload &amp; Process

                  <span className="button-arrow">
                    →
                  </span>
                </>
              )}
            </button>
          )}

          {isProcessing && (
            <div className="processing-panel">

              <div className="processing-header">
                <span>
                  {statusMessage ||
                    "Processing..."}
                </span>

                <strong>
                  {progress}%
                </strong>
              </div>

              <div className="progress-track">

                <div
                  className="progress-bar"
                  style={{
                    width: `${progress}%`,
                  }}
                />

              </div>

              <div className="processing-stages">

                {PROCESSING_STAGES.map(
                  (
                    stage,
                    index
                  ) => {

                    const isCompleted =
                      progress >=
                        100 ||
                      index <
                        currentStageIndex;

                    const isCurrent =
                      index ===
                        currentStageIndex &&
                      !isCompleted;

                    const isPending =
                      index >
                      currentStageIndex;

                    return (
                      <div
                        className={`processing-stage ${
                          isCompleted
                            ? "completed"
                            : ""
                        } ${
                          isCurrent
                            ? "current"
                            : ""
                        } ${
                          isPending
                            ? "pending"
                            : ""
                        }`}
                        key={
                          stage.id
                        }
                      >

                        <div className="stage-indicator">

                          {isCompleted ? (
                            <span className="stage-check">
                              ✓
                            </span>
                          ) : isCurrent ? (
                            <span className="stage-current-dot" />
                          ) : (
                            <span className="stage-pending-dot" />
                          )}

                        </div>

                        <div className="stage-content">

                          <span className="stage-label">
                            {stage.label}
                          </span>

                          <span className="stage-status">
                            {isCompleted
                              ? "Completed"
                              : isCurrent
                              ? "In Progress"
                              : "Pending"}
                          </span>

                        </div>

                      </div>
                    );
                  }
                )}

              </div>
            </div>
          )}

          {result &&
            !isProcessing && (
              <div className="processing-success">

                <div className="success-icon">
                  ✓
                </div>

                <div>
                  <strong>
                    OCR processing completed
                  </strong>

                  <span>
                    All four output files
                    are ready.
                  </span>
                </div>

              </div>
            )}

          {!result && (
            <div className="upload-help">

              <span>
                Supported format
              </span>

              <div className="format-list">
                <span>
                  PDF
                </span>
              </div>

              <span className="format-separator">
                •
              </span>

              <span>
                Maximum 50 MB
              </span>

            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={
              handleFileChange
            }
            hidden
          />

        </section>

        {/* =================================================
            GENERATED OUTPUTS
        ================================================= */}

        {result && (
          <section className="outputs-section">

            <div className="outputs-header">

              <div>
                <span className="section-eyebrow">
                  OCR OUTPUTS
                </span>

                <h2>
                  Generated Files
                </h2>

                <p>
                  Preview or download any
                  generated output.
                </p>
              </div>

              <div className="outputs-count">
                <span>
                  4
                </span>

                <small>
                  outputs
                </small>
              </div>

            </div>

            <div className="output-grid">

              {outputFiles.map(
                (file) => (
                  <div
                    className="output-card"
                    key={
                      file.key
                    }
                  >

                    <div className="output-card-top">

                      <div
                        className={`output-file-icon ${file.extension.toLowerCase()}`}
                      >
                        <span>
                          {
                            file.extension
                          }
                        </span>
                      </div>

                      <div className="output-file-info">

                        <h3>
                          {file.title}
                        </h3>

                        <span>
                          {
                            file.extension
                          }{" "}
                          output
                        </span>

                      </div>

                      <div className="output-ready">
                        ✓
                      </div>

                    </div>

                    <p className="output-description">
                      {
                        file.description
                      }
                    </p>

                    <div className="output-actions">

                      <button
                        className="preview-output-button"
                        onClick={() =>
                          previewFileOutput(
                            file
                          )
                        }
                      >
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        >
                          <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />

                          <circle
                            cx="12"
                            cy="12"
                            r="2.5"
                          />
                        </svg>

                        Preview
                      </button>

                      <button
                        className="download-output-button"
                        onClick={() =>
                          downloadFile(
                            file.key
                          )
                        }
                      >
                        <svg
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        >
                          <path d="M12 3v12" />

                          <path d="M7 10l5 5 5-5" />

                          <path d="M5 21h14" />
                        </svg>

                        Download
                      </button>

                    </div>

                  </div>
                )
              )}

            </div>

            {downloadStatus && (
              <div className="download-status">
                {downloadStatus}
              </div>
            )}

            <button
              className="new-document-button"
              onClick={
                startNewDocument
              }
              disabled={
                isProcessing
              }
            >
              Process Another
              Document

              <span>
                →
              </span>
            </button>

          </section>
        )}

        {/* =================================================
            PROCESSED DOCUMENT HISTORY
        ================================================= */}

        {documentsHistory.length >
          0 && (
          <section className="document-history-section">

            <div className="outputs-header">

              <div>
                <span className="section-eyebrow">
                  DOCUMENT HISTORY
                </span>

                <h2>
                  Processed Documents
                </h2>

                <p>
                  Your completed OCR documents
                  are available here.
                </p>
              </div>

              <div className="outputs-count">
                <span>
                  {
                    documentsHistory.length
                  }
                </span>

                <small>
                  documents
                </small>
              </div>

            </div>

            <div className="document-history-list">

              {documentsHistory
                .slice()
                .reverse()
                .map(
                  (
                    documentItem,
                    index
                  ) => {
                    const itemResult =
                      documentItem.result;

                    const itemPages =
                      getPagesProcessedFromResult(
                        itemResult
                      );

                    const itemLanguages =
                      getLanguagesDetectedFromResult(
                        itemResult
                      );

                    const itemAccuracy =
                      getAccuracyFromResult(
                        itemResult
                      );

                    return (
                      <div
                        className="document-history-card"
                        key={
                          documentItem.jobId ||
                          index
                        }
                      >

                        <div className="history-file-icon">
                          PDF
                        </div>

                        <div className="history-file-info">

                          <h3>
                            {
                              documentItem.filename
                            }
                          </h3>

                          <div className="history-meta">

                            <span>
                              ✓ Completed
                            </span>

                            <span>
                              {itemPages}{" "}
                              {itemPages ===
                              1
                                ? "page"
                                : "pages"}
                            </span>

                            <span>
                              {itemLanguages}{" "}
                              {itemLanguages ===
                              1
                                ? "language"
                                : "languages"}
                            </span>

                            {itemAccuracy >
                              0 && (
                              <span>
                                {itemAccuracy.toFixed(
                                  1
                                )}
                                % accuracy
                              </span>
                            )}

                          </div>

                        </div>

                        <div className="history-actions">

                          <button
                            className="history-view-button"
                            onClick={() =>
                              openHistoryDocument(
                                documentItem
                              )
                            }
                          >
                            View
                          </button>

                        </div>

                      </div>
                    );
                  }
                )}

            </div>

            <button
              className="history-clear-button"
              onClick={
                clearHistory
              }
              disabled={
                isProcessing
              }
            >
              Clear History
            </button>

          </section>
        )}

        {/* =================================================
            INFORMATION
        ================================================= */}

        <section className="document-info">

          <div className="info-item">

            <div className="info-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                />

                <line
                  x1="12"
                  y1="10"
                  x2="12"
                  y2="16"
                />

                <circle
                  cx="12"
                  cy="7"
                  r="0.6"
                  fill="currentColor"
                />
              </svg>
            </div>

            <div>
              <strong>
                Multilingual OCR
              </strong>

              <p>
                Extract text from
                English, Hindi,
                Gujarati and other
                supported languages.
              </p>
            </div>

          </div>

          <div className="info-item">

            <div className="info-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
              >
                <path d="M12 3v12" />

                <path d="M7 10l5 5 5-5" />

                <path d="M5 21h14" />
              </svg>
            </div>

            <div>
              <strong>
                Structured Output
              </strong>

              <p>
                Generate
                machine-readable JSON,
                TXT and searchable PDF
                documents.
              </p>
            </div>

          </div>

          <div className="info-item">

            <div className="info-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
              >
                <path d="M4 19V5" />

                <path d="M4 19h16" />

                <path d="M7 15l3-4 3 2 4-6" />
              </svg>
            </div>

            <div>
              <strong>
                High Accuracy
              </strong>

              <p>
                AI-powered document
                processing designed for
                reliable downstream
                systems.
              </p>
            </div>

          </div>

        </section>

      </main>

      {/* =====================================================
          OUTPUT PREVIEW MODAL
      ===================================================== */}

      {previewFile && (
        <div
          className="output-preview-overlay"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closePreview();
            }
          }}
        >

          <div className="output-preview-modal">

            <div className="output-preview-header">

              <div className="output-preview-heading">

                <div
                  className={`modal-file-icon ${previewFile.extension.toLowerCase()}`}
                >
                  {
                    previewFile.extension
                  }
                </div>

                <div>
                  <span>
                    OUTPUT PREVIEW
                  </span>

                  <h2>
                    {
                      previewFile.title
                    }
                  </h2>
                </div>

              </div>

              <button
                className="preview-close-button"
                onClick={
                  closePreview
                }
                aria-label="Close preview"
              >
                ×
              </button>

            </div>

            <div className="output-preview-body">

              {previewLoading && (
                <div className="preview-loading">

                  <span className="preview-spinner" />

                  <strong>
                    Loading preview...
                  </strong>

                  <small>
                    Preparing your
                    generated output
                  </small>

                </div>
              )}

              {previewError &&
                !previewLoading && (
                  <div className="preview-error">

                    <div>
                      !
                    </div>

                    <strong>
                      Unable to preview
                    </strong>

                    <span>
                      {
                        previewError
                      }
                    </span>

                  </div>
                )}

              {!previewLoading &&
                !previewError &&
                previewFile.previewType ===
                  "text" && (
                  <div className="text-preview-wrapper">

                    <div className="text-preview-toolbar">

                      <span>
                        {
                          previewFile.extension
                        } CONTENT
                      </span>

                      <button
                        onClick={() =>
                          navigator.clipboard.writeText(
                            previewContent
                          )
                        }
                      >
                        Copy
                      </button>

                    </div>

                    <pre className="text-preview">
                      {
                        previewContent
                      }
                    </pre>

                  </div>
                )}

              {!previewLoading &&
                !previewError &&
                previewFile.previewType ===
                  "pdf" &&
                previewUrl && (
                  <div className="pdf-preview-wrapper">

                    <iframe
                      src={
                        previewUrl
                      }
                      title={
                        previewFile.title
                      }
                      className="pdf-preview-frame"
                    />

                  </div>
                )}

            </div>

            <div className="output-preview-footer">

              <div>
                <span>
                  {
                    previewFile.extension
                  }{" "}
                  output
                </span>

                <small>
                  Generated by Astra-OCR
                </small>
              </div>

              <button
                className="modal-download-button"
                onClick={() =>
                  downloadFile(
                    previewFile.key
                  )
                }
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                >
                  <path d="M12 3v12" />

                  <path d="M7 10l5 5 5-5" />

                  <path d="M5 21h14" />
                </svg>

                Download
              </button>

            </div>

          </div>
        </div>
      )}

    </div>
  );
}

export default Documents;