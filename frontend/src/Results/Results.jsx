import React, {
  useEffect,
  useMemo,
  useState,
} from "react";

import "./Results.css";

const API_BASE_URL =
  "http://127.0.0.1:8000";

const DOWNLOAD_ENDPOINTS = {
  json:
    "/api/download/{job_id}/json",
};

/* =========================================================
   HELPERS
   ========================================================= */

const safeString = (value) => {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  if (
    typeof value === "string"
  ) {
    return value;
  }

  return String(value);
};

const getPageArray = (result) => {
  if (!result) {
    return [];
  }

  if (
    Array.isArray(result.pages)
  ) {
    return result.pages;
  }

  if (
    result.pages &&
    typeof result.pages === "object"
  ) {
    return Object.values(result.pages);
  }

  if (
    result.result &&
    Array.isArray(result.result.pages)
  ) {
    return result.result.pages;
  }

  return [];
};

const getBlocksFromResult = (result) => {
  const pages =
    getPageArray(result);

  const blocks = [];

  pages.forEach(
    (page, pageIndex) => {
      let pageBlocks = [];

      if (
        Array.isArray(page.blocks)
      ) {
        pageBlocks =
          page.blocks;
      } else if (
        Array.isArray(page.ocr_blocks)
      ) {
        pageBlocks =
          page.ocr_blocks;
      } else if (
        Array.isArray(page.text_blocks)
      ) {
        pageBlocks =
          page.text_blocks;
      } else if (
        page.final_result &&
        Array.isArray(
          page.final_result.results
        )
      ) {
        pageBlocks =
          page.final_result.results;
      }

      pageBlocks.forEach(
        (block, blockIndex) => {
          let text = "";

          if (
            typeof block === "string"
          ) {
            text = block;
          } else {
            text =
              safeString(
                block?.text
              ) ||
              safeString(
                block?.content
              ) ||
              safeString(
                block?.html
              ) ||
              safeString(
                block?.value
              );
          }

          if (!text.trim()) {
            return;
          }

          blocks.push({
            ...(typeof block === "object"
              ? block
              : {}),
            text:
              text.trim(),
            page:
              Number(
                page?.page_number ??
                  pageIndex + 1
              ),
            blockIndex,
          });
        }
      );
    }
  );

  return blocks;
};

const getAllText = (result) => {
  if (!result) {
    return "";
  }

  const blocks =
    getBlocksFromResult(result);

  if (
    blocks.length > 0
  ) {
    return blocks
      .map(
        (block) =>
          block.text
      )
      .join("\n");
  }

  if (
    typeof result.text ===
    "string"
  ) {
    return result.text;
  }

  if (
    typeof result.extracted_text ===
    "string"
  ) {
    return result.extracted_text;
  }

  return "";
};

const getPagesCount = (result) => {
  if (!result) {
    return 0;
  }

  if (
    typeof result.total_pages ===
    "number"
  ) {
    return result.total_pages;
  }

  const pages =
    getPageArray(result);

  return pages.length;
};

const getLanguages = (result) => {
  const languages =
    new Set();

  const addLanguages = (value) => {
    if (!value) {
      return;
    }

    if (
      Array.isArray(value)
    ) {
      value.forEach(
        (language) => {
          if (language) {
            languages.add(
              String(language)
            );
          }
        }
      );

      return;
    }

    if (
      typeof value ===
      "string"
    ) {
      value
        .split(/[,+/&|]/)
        .map(
          (item) =>
            item.trim()
        )
        .filter(Boolean)
        .forEach(
          (language) =>
            languages.add(
              language
            )
        );
    }
  };

  addLanguages(
    result?.detected_languages
  );

  addLanguages(
    result?.languages
  );

  addLanguages(
    result?.language
  );

  getPageArray(result).forEach(
    (page) => {
      addLanguages(
        page?.detected_languages
      );

      addLanguages(
        page?.languages
      );

      addLanguages(
        page?.language
      );

      addLanguages(
        page?.final_result
          ?.detected_languages
      );
    }
  );

  return Array.from(
    languages
  );
};

/* =========================================================
   OCR CONFIDENCE
   ========================================================= */

const getAccuracy = (result) => {
  if (!result) {
    return 0;
  }

  const candidates = [
    result?.final_quality?.quality_score,
    result?.final_quality?.score,
    result?.final_quality?.total_score,
    result?.quality_score,
    result?.accuracy,
  ];

  for (
    const value of candidates
  ) {
    const number =
      Number(value);

    if (
      !Number.isNaN(number) &&
      number > 0
    ) {
      return number <= 1
        ? number * 100
        : number;
    }
  }

  const pages =
    getPageArray(result);

  const pageScores = [];

  pages.forEach(
    (page) => {
      const pageCandidates = [
        page?.quality_score,
        page?.quality?.score,
        page?.final_quality?.quality_score,
        page?.final_quality?.score,
        page?.final_result?.quality_score,
        page?.final_result?.quality?.score,
      ];

      for (
        const value of pageCandidates
      ) {
        const number =
          Number(value);

        if (
          !Number.isNaN(number) &&
          number > 0
        ) {
          pageScores.push(
            number <= 1
              ? number * 100
              : number
          );

          break;
        }
      }
    }
  );

  if (
    pageScores.length > 0
  ) {
    return (
      pageScores.reduce(
        (sum, value) =>
          sum + value,
        0
      ) /
      pageScores.length
    );
  }

  const blocks =
    getBlocksFromResult(result);

  const confidenceValues =
    blocks
      .map(
        (block) =>
          Number(
            block?.confidence ??
              block?.score ??
              block?.text_score ??
              block?.rec_score ??
              0
          )
      )
      .filter(
        (value) =>
          !Number.isNaN(value) &&
          value > 0
      );

  if (
    confidenceValues.length > 0
  ) {
    const average =
      confidenceValues.reduce(
        (sum, value) =>
          sum + value,
        0
      ) /
      confidenceValues.length;

    return average <= 1
      ? average * 100
      : average;
  }

  return 0;
};

/* =========================================================
   SEARCH JSON HIGHLIGHT
   ========================================================= */

const escapeRegExp = (value) => {
  return String(value).replace(
    /[.*+?^${}()|[\]\\]/g,
    "\\$&"
  );
};

const renderHighlightedJSON = (
  jsonString,
  query
) => {
  if (
    !query ||
    !query.trim()
  ) {
    return jsonString;
  }

  const cleanQuery =
    query.trim();

  const parts =
    jsonString.split(
      new RegExp(
        `(${escapeRegExp(
          cleanQuery
        )})`,
        "gi"
      )
    );

  return parts.map(
    (part, index) => {
      if (
        part.toLowerCase() ===
        cleanQuery.toLowerCase()
      ) {
        return (
          <mark
            key={`json-match-${index}`}
          >
            {part}
          </mark>
        );
      }

      return (
        <React.Fragment
          key={`json-text-${index}`}
        >
          {part}
        </React.Fragment>
      );
    }
  );
};

/* =========================================================
   DATA ENTRY EXTRACTION
   ========================================================= */

function buildDataRecords(result) {
  if (
    !result ||
    !Array.isArray(result.pages)
  ) {
    return [];
  }

  const allBlocks = [];

  for (
    const page of result.pages
  ) {
    if (
      !page ||
      !page.final_result
    ) {
      continue;
    }

    const finalResult =
      page.final_result;

    if (
      Array.isArray(
        finalResult.results
      )
    ) {
      for (
        const item of
          finalResult.results
      ) {
        if (!item) {
          continue;
        }

        let text = "";

        if (
          typeof item ===
          "string"
        ) {
          text = item;
        } else if (
          typeof item.text ===
          "string"
        ) {
          text = item.text;
        } else if (
          typeof item.html ===
          "string"
        ) {
          text =
            item.html.replace(
              /<[^>]*>/g,
              " "
            );
        } else if (
          typeof item.content ===
          "string"
        ) {
          text =
            item.content;
        }

        text = text
          .replace(
            /<[^>]*>/g,
            " "
          )
          .replace(
            /\s+/g,
            " "
          )
          .trim();

        if (text) {
          allBlocks.push({
            text,
            pageNumber:
              page.page_number ||
              null,
          });
        }
      }
    }
  }

  if (
    !allBlocks.length
  ) {
    return [];
  }

  const fullText =
    allBlocks
      .map(
        (block) =>
          block.text
      )
      .join(" ")
      .replace(
        /\s+/g,
        " "
      )
      .trim();

  const records = [];

  const addRecord = (
    name,
    value,
    type = "Text",
    confidence = 95
  ) => {
    const cleanName =
      String(
        name || ""
      ).trim();

    const cleanValue =
      String(
        value || ""
      ).trim();

    if (
      !cleanName ||
      !cleanValue
    ) {
      return;
    }

    if (
      records.some(
        (record) =>
          record.name
            .toLowerCase() ===
          cleanName.toLowerCase()
      )
    ) {
      return;
    }

    records.push({
      name:
        cleanName,
      type,
      value:
        cleanValue,
      confidence,
      status:
        "Ready",
    });
  };

  const extractField = (
    labelPatterns,
    fieldName,
    type = "Text"
  ) => {
    for (
      const pattern of
        labelPatterns
    ) {
      const match =
        fullText.match(
          pattern
        );

      if (
        match &&
        match[1]
      ) {
        const value =
          match[1]
            .replace(
              /[|]+/g,
              " "
            )
            .replace(
              /\s+/g,
              " "
            )
            .trim();

        if (value) {
          addRecord(
            fieldName,
            value,
            type
          );

          return;
        }
      }
    }
  };

  extractField(
    [
      /(?:student'?s?\s+name|candidate'?s?\s+name|name\s+of\s+student)\s*[:\-]?\s*([A-Z][A-Za-z .'-]{2,80}?)(?=\s+(?:father|mother|roll|registration|regn|date|dob|school)\b|$)/i,
    ],
    "Name"
  );

  extractField(
    [
      /father(?:'s)?\s*(?:\/\s*guardian)?\s*name\s*[:\-]?\s*([A-Za-z .'-]{2,100}?)(?=\s+(?:mother|roll|registration|regn|date|dob|school)\b|$)/i,
      /father'?s?\s+name\s*[:\-]?\s*([A-Za-z .'-]{2,100}?)(?=\s|$)/i,
    ],
    "Father's Name"
  );

  extractField(
    [
      /mother(?:'s)?\s*name\s*[:\-]?\s*([A-Za-z .'-]{2,100}?)(?=\s+(?:father|roll|registration|regn|date|dob|school)\b|$)/i,
    ],
    "Mother's Name"
  );

  extractField(
    [
      /roll\s*(?:no|number)\s*[:\-]?\s*([A-Za-z0-9\/-]+)/i,
    ],
    "Roll Number",
    "Number"
  );

  extractField(
    [
      /(?:regn|regn\.|registration)\s*(?:no|number)?\s*[:\-]?\s*([A-Za-z0-9\/-]+)/i,
      /registration\s*(?:no|number)\s*[:\-]?\s*([A-Za-z0-9\/-]+)/i,
    ],
    "Registration Number",
    "Number"
  );

  extractField(
    [
      /date\s+of\s+birth\s*[:\-]?\s*(\d{1,2}[\/.-]\d{1,2}[\/.-]\d{2,4})/i,
      /\bdob\b\s*[:\-]?\s*(\d{1,2}[\/.-]\d{1,2}[\/.-]\d{2,4})/i,
    ],
    "Date of Birth",
    "Date"
  );

  extractField(
    [
      /school\s*(?:name)?\s*[:\-]?\s*([A-Za-z0-9 .,'&()\/-]{3,150}?)(?=\s+(?:year|date|dob|roll|registration|regn)\b|$)/i,
    ],
    "School"
  );

  const yearMatch =
    fullText.match(
      /\b(20\d{2})\b/
    );

  if (yearMatch) {
    addRecord(
      "Year",
      yearMatch[1],
      "Number"
    );
  }

  if (
    Array.isArray(result.pages)
  ) {
    const languages =
      new Set();

    for (
      const page of result.pages
    ) {
      if (
        Array.isArray(
          page.detected_languages
        )
      ) {
        page.detected_languages.forEach(
          (language) => {
            if (language) {
              languages.add(
                String(language)
              );
            }
          }
        );
      }
    }

    if (
      languages.size
    ) {
      addRecord(
        "Languages",
        Array.from(
          languages
        ).join(", "),
        "Text"
      );
    }
  }

  addRecord(
    "Pages",
    String(
      result.total_pages ||
        result.pages.length
    ),
    "Number"
  );

  if (
    !records.length
  ) {
    allBlocks
      .slice(0, 12)
      .forEach(
        (
          block,
          index
        ) => {
          addRecord(
            `Extracted Text ${
              index + 1
            }`,
            block.text,
            "Text"
          );
        }
      );
  }

  return records.slice(
    0,
    12
  );
}

/* =========================================================
   COMPLIANCE HELPERS
   ========================================================= */

const normalizeText = (value) => {
  return safeString(value)
    .toLowerCase()
    .replace(
      /\s+/g,
      " "
    )
    .trim();
};

const getPageText = (page) => {
  if (!page) {
    return "";
  }

  let pageBlocks = [];

  if (
    Array.isArray(page.blocks)
  ) {
    pageBlocks =
      page.blocks;
  } else if (
    Array.isArray(page.ocr_blocks)
  ) {
    pageBlocks =
      page.ocr_blocks;
  } else if (
    Array.isArray(page.text_blocks)
  ) {
    pageBlocks =
      page.text_blocks;
  } else if (
    Array.isArray(
      page.final_result?.results
    )
  ) {
    pageBlocks =
      page.final_result.results;
  }

  return pageBlocks
    .map(
      (block) => {
        if (
          typeof block ===
          "string"
        ) {
          return block;
        }

        return (
          safeString(
            block?.text
          ) ||
          safeString(
            block?.content
          ) ||
          safeString(
            block?.html
          ) ||
          safeString(
            block?.value
          )
        );
      }
    )
    .join(" ")
    .replace(
      /<[^>]*>/g,
      " "
    )
    .replace(
      /\s+/g,
      " "
    )
    .trim();
};

const getBlockConfidenceValues = (
  result
) => {
  return getBlocksFromResult(
    result
  )
    .map(
      (block) =>
        Number(
          block?.confidence ??
            block?.score ??
            block?.text_score ??
            block?.rec_score ??
            0
        )
    )
    .filter(
      (value) =>
        !Number.isNaN(value) &&
        value > 0
    )
    .map(
      (value) =>
        value <= 1
          ? value * 100
          : value
    );
};

const getRequiredFieldStatus = (
  result,
  records
) => {
  const text =
    getAllText(result);

  const lowerText =
    text.toLowerCase();

  const possibleFields = [
    {
      name: "Name",
      patterns: [
        /student'?s?\s+name/i,
        /candidate'?s?\s+name/i,
        /name\s+of\s+student/i,
      ],
    },
    {
      name: "Father's Name",
      patterns: [
        /father'?s?\s+name/i,
        /father\s*\/\s*guardian/i,
      ],
    },
    {
      name: "Mother's Name",
      patterns: [
        /mother'?s?\s+name/i,
      ],
    },
    {
      name: "Roll Number",
      patterns: [
        /roll\s*(?:no|number)/i,
      ],
    },
    {
      name: "Registration Number",
      patterns: [
        /registration\s*(?:no|number)?/i,
        /regn\.?\s*(?:no|number)?/i,
      ],
    },
    {
      name: "Date of Birth",
      patterns: [
        /date\s+of\s+birth/i,
        /\bdob\b/i,
      ],
    },
    {
      name: "School",
      patterns: [
        /\bschool\b/i,
      ],
    },
  ];

  const detectedFields =
    possibleFields.filter(
      (field) =>
        field.patterns.some(
          (pattern) =>
            pattern.test(
              lowerText
            )
        )
    );

  if (
    detectedFields.length === 0
  ) {
    return {
      status: "warning",
      description:
        "No standard structured fields were identified for validation.",
    };
  }

  const recordNames =
    records.map(
      (record) =>
        normalizeText(
          record.name
        )
    );

  const missingFields =
    detectedFields.filter(
      (field) =>
        !recordNames.includes(
          normalizeText(
            field.name
          )
        )
    );

  if (
    missingFields.length === 0
  ) {
    return {
      status: "passed",
      description:
        `${detectedFields.length} detected document field${
          detectedFields.length === 1
            ? ""
            : "s"
        } were successfully extracted.`,
    };
  }

  if (
    missingFields.length <
    detectedFields.length
  ) {
    return {
      status: "warning",
      description:
        `${detectedFields.length -
          missingFields.length} of ${
          detectedFields.length
        } detected fields were extracted. Missing: ${missingFields
          .map(
            (field) =>
              field.name
          )
          .join(", ")}.`,
    };
  }

  return {
    status: "error",
    description:
      "Standard document fields were detected, but none could be extracted reliably.",
  };
};

const getDuplicateStatus = (
  blocks
) => {
  const normalizedTexts =
    blocks
      .map(
        (block) =>
          normalizeText(
            block.text
          )
      )
      .filter(
        Boolean
      );

  const counts =
    new Map();

  normalizedTexts.forEach(
    (text) => {
      counts.set(
        text,
        (counts.get(text) ||
          0) + 1
      );
    }
  );

  const duplicateGroups =
    Array.from(
      counts.values()
    ).filter(
      (count) =>
        count > 1
    );

  if (
    duplicateGroups.length === 0
  ) {
    return {
      status: "passed",
      description:
        "No duplicate OCR text blocks were detected.",
    };
  }

  const duplicateCount =
    duplicateGroups.reduce(
      (sum, count) =>
        sum + count - 1,
      0
    );

  return {
    status: "warning",
    description:
      `${duplicateCount} duplicate OCR ${
        duplicateCount === 1
          ? "record"
          : "records"
      } detected across ${duplicateGroups.length} repeated ${
        duplicateGroups.length === 1
          ? "group"
          : "groups"
      }.`,
  };
};

const getUnreadableRegionStatus = (
  result
) => {
  const pages =
    getPageArray(result);

  if (
    pages.length === 0
  ) {
    return {
      status: "error",
      description:
        "No pages were available for readability validation.",
    };
  }

  const unreadablePages =
    [];

  pages.forEach(
    (page, index) => {
      const text =
        getPageText(
          page
        );

      if (
        text.length < 15
      ) {
        unreadablePages.push(
          index + 1
        );
      }
    }
  );

  if (
    unreadablePages.length === 0
  ) {
    return {
      status: "passed",
      description:
        "All processed pages contain meaningful readable OCR text.",
    };
  }

  if (
    unreadablePages.length ===
    pages.length
  ) {
    return {
      status: "error",
      description:
        "All processed pages contain insufficient readable OCR text.",
    };
  }

  return {
    status: "warning",
    description:
      `${unreadablePages.length} page${
        unreadablePages.length === 1
          ? ""
          : "s"
      } may contain unreadable or empty regions: Page ${unreadablePages.join(
        ", "
      )}.`,
  };
};

const getOCRTextQualityStatus = (
  result
) => {
  const blocks =
    getBlocksFromResult(
      result
    );

  const text =
    getAllText(result);

  if (
    !text.trim()
  ) {
    return {
      status: "error",
      description:
        "No OCR text is available for quality analysis.",
    };
  }

  let suspiciousBlocks = 0;

  blocks.forEach(
    (block) => {
      const blockText =
        safeString(
          block.text
        ).trim();

      if (
        blockText.length < 3
      ) {
        suspiciousBlocks++;
        return;
      }

      const meaningfulCharacters =
        (
          blockText.match(
            /[\p{L}\p{N}]/gu
          ) || []
        ).length;

      const suspiciousCharacters =
        (
          blockText.match(
            /[^\p{L}\p{N}\s.,:;'"!?%()\/&+\-]/gu
          ) || []
        ).length;

      const totalCharacters =
        blockText.length;

      const suspiciousRatio =
        totalCharacters > 0
          ? suspiciousCharacters /
            totalCharacters
          : 0;

      const meaningfulRatio =
        totalCharacters > 0
          ? meaningfulCharacters /
            totalCharacters
          : 0;

      if (
        suspiciousRatio > 0.35 ||
        meaningfulRatio < 0.25
      ) {
        suspiciousBlocks++;
      }
    }
  );

  if (
    blocks.length === 0
  ) {
    return {
      status: "warning",
      description:
        "OCR text exists, but structured text blocks are unavailable.",
    };
  }

  const suspiciousRatio =
    suspiciousBlocks /
    blocks.length;

  if (
    suspiciousRatio === 0
  ) {
    return {
      status: "passed",
      description:
        "OCR text contains no significant signs of suspicious or malformed text.",
    };
  }

  if (
    suspiciousRatio < 0.25
  ) {
    return {
      status: "warning",
      description:
        `${suspiciousBlocks} of ${blocks.length} OCR blocks may contain unusual or unreliable characters.`,
    };
  }

  return {
    status: "error",
    description:
      `${suspiciousBlocks} of ${blocks.length} OCR blocks contain potentially unreliable text.`,
  };
};

const getConsistencyStatus = (
  result,
  records
) => {
  const text =
    normalizeText(
      getAllText(result)
    );

  const meaningfulRecords =
    records.filter(
      (record) =>
        record.name !==
          "Pages" &&
        record.name !==
          "Languages" &&
        safeString(
          record.value
        ).trim()
    );

  if (
    meaningfulRecords.length === 0
  ) {
    return {
      status: "warning",
      description:
        "No structured fields were available for OCR-to-data consistency validation.",
    };
  }

  const missingValues =
    meaningfulRecords.filter(
      (record) => {
        const value =
          normalizeText(
            record.value
          );

        if (!value) {
          return true;
        }

        return !text.includes(
          value
        );
      }
    );

  if (
    missingValues.length === 0
  ) {
    return {
      status: "passed",
      description:
        "All extracted structured values were found in the OCR text.",
    };
  }

  if (
    missingValues.length <
    meaningfulRecords.length
  ) {
    return {
      status: "warning",
      description:
        `${meaningfulRecords.length -
          missingValues.length} of ${
          meaningfulRecords.length
        } extracted values matched the OCR text. Review: ${missingValues
          .map(
            (record) =>
              record.name
          )
          .join(", ")}.`,
    };
  }

  return {
    status: "error",
    description:
      "The extracted structured values could not be consistently matched against the OCR text.",
  };
};

/* =========================================================
   COMPLIANCE
   ========================================================= */

const buildComplianceChecks = (
  result
) => {
  const text =
    getAllText(result);

  const pages =
    getPagesCount(result);

  const accuracy =
    getAccuracy(result);

  const languages =
    getLanguages(result);

  const blocks =
    getBlocksFromResult(
      result
    );

  const records =
    buildDataRecords(
      result
    );

  const checks = [];

  /* -------------------------------------------------------
     1. DOCUMENT TEXT EXTRACTED
     ------------------------------------------------------- */

  checks.push({
    title:
      "Document text extracted",

    status:
      text.trim().length > 0
        ? "passed"
        : "error",

    description:
      text.trim().length > 0
        ? "OCR text was successfully extracted from the document."
        : "No readable text was found in the OCR result.",
  });

  /* -------------------------------------------------------
     2. REQUIRED FIELDS
     ------------------------------------------------------- */

  const requiredFieldCheck =
    getRequiredFieldStatus(
      result,
      records
    );

  checks.push({
    title:
      "Required fields are present",

    status:
      requiredFieldCheck.status,

    description:
      requiredFieldCheck.description,
  });

  /* -------------------------------------------------------
     3. PAGE INFORMATION
     ------------------------------------------------------- */

  const pageArray =
    getPageArray(result);

  const validPageNumbers =
    pageArray.every(
      (page, index) =>
        Number(
          page?.page_number ??
            index + 1
        ) > 0
    );

  checks.push({
    title:
      "Page information available",

    status:
      pages > 0 &&
      validPageNumbers
        ? "passed"
        : "error",

    description:
      pages > 0 &&
      validPageNumbers
        ? `${pages} page${
            pages === 1
              ? ""
              : "s"
          } processed successfully with valid page information.`
        : "Page information could not be determined reliably.",
  });

  /* -------------------------------------------------------
     4. LANGUAGE DETECTED
     ------------------------------------------------------- */

  checks.push({
    title:
      "Language detected",

    status:
      languages.length > 0
        ? "passed"
        : "warning",

    description:
      languages.length > 0
        ? `Detected: ${languages.join(
            ", "
          )}.`
        : "No language information was found in the OCR result.",
  });

  /* -------------------------------------------------------
     5. OCR CONFIDENCE
     ------------------------------------------------------- */

  if (
    accuracy > 0
  ) {
    checks.push({
      title:
        "OCR confidence",

      status:
        accuracy >= 90
          ? "passed"
          : accuracy >= 75
          ? "warning"
          : "error",

      description:
        `Overall OCR confidence is ${accuracy.toFixed(
          1
        )}%.`,
    });
  } else {
    const blockConfidence =
      getBlockConfidenceValues(
        result
      );

    if (
      blockConfidence.length > 0
    ) {
      const average =
        blockConfidence.reduce(
          (sum, value) =>
            sum + value,
          0
        ) /
        blockConfidence.length;

      checks.push({
        title:
          "OCR confidence",

        status:
          average >= 90
            ? "passed"
            : average >= 75
            ? "warning"
            : "error",

        description:
          `Average OCR block confidence is ${average.toFixed(
            1
          )}%.`,
      });
    } else {
      checks.push({
        title:
          "OCR confidence",

        status:
          "warning",

        description:
          "No confidence score is available for this OCR result.",
      });
    }
  }

  /* -------------------------------------------------------
     6. DUPLICATE RECORDS
     ------------------------------------------------------- */

  const duplicateCheck =
    getDuplicateStatus(
      blocks
    );

  checks.push({
    title:
      "Duplicate records",

    status:
      duplicateCheck.status,

    description:
      duplicateCheck.description,
  });

  /* -------------------------------------------------------
     7. DOCUMENT STRUCTURE
     ------------------------------------------------------- */

  const structuredBlocks =
    blocks.filter(
      (block) =>
        Array.isArray(
          block?.polygon
        ) ||
        Array.isArray(
          block?.bbox
        ) ||
        Array.isArray(
          block?.box
        )
    );

  if (
    blocks.length === 0
  ) {
    checks.push({
      title:
        "Document structure",

      status:
        "error",

      description:
        "No structured OCR blocks are available.",
    });
  } else if (
    structuredBlocks.length ===
    blocks.length
  ) {
    checks.push({
      title:
        "Document structure",

      status:
        "passed",

      description:
        "OCR layout, text blocks and positional information are available.",
    });
  } else {
    checks.push({
      title:
        "Document structure",

      status:
        "warning",

      description:
        `${structuredBlocks.length} of ${blocks.length} OCR blocks contain positional structure.`,
    });
  }

  /* -------------------------------------------------------
     8. UNREADABLE / EMPTY REGIONS
     ------------------------------------------------------- */

  const unreadableCheck =
    getUnreadableRegionStatus(
      result
    );

  checks.push({
    title:
      "Unreadable / empty regions",

    status:
      unreadableCheck.status,

    description:
      unreadableCheck.description,
  });

  /* -------------------------------------------------------
     9. OCR TEXT QUALITY
     ------------------------------------------------------- */

  const textQualityCheck =
    getOCRTextQualityStatus(
      result
    );

  checks.push({
    title:
      "OCR text quality",

    status:
      textQualityCheck.status,

    description:
      textQualityCheck.description,
  });

  /* -------------------------------------------------------
     10. DATA EXTRACTION CONSISTENCY
     ------------------------------------------------------- */

  const consistencyCheck =
    getConsistencyStatus(
      result,
      records
    );

  checks.push({
    title:
      "Data extraction consistency",

    status:
      consistencyCheck.status,

    description:
      consistencyCheck.description,
  });

  return checks;
};

/* =========================================================
   COMPONENT
   ========================================================= */

/*
 * IMPORTANT:
 *
 * Result, jobId and filename are now received from App.jsx.
 *
 * Results.jsx NO LONGER reads:
 *
 *   astra_ocr_result
 *   astra_ocr_job_id
 *   astra_ocr_filename
 *
 * from localStorage.
 *
 * This means the same processed document stays available
 * while navigating between pages because App.jsx remains
 * the source of truth.
 *
 * A manual browser refresh resets the in-memory App state,
 * which is the behavior requested.
 */

export default function Results({
  result: resultProp = null,
  jobId: jobIdProp = null,
  filename: filenameProp = "",
  documentsHistory = [],
}) {
  const result =
    resultProp;

  const jobId =
    jobIdProp;

  /*
   * Resolve filename without localStorage.
   *
   * Priority:
   *
   * 1. filename supplied by App
   * 2. matching document history item
   * 3. result filename/input PDF
   * 4. fallback
   */

  const filename = useMemo(() => {
    if (
      filenameProp &&
      String(
        filenameProp
      ).trim()
    ) {
      return String(
        filenameProp
      );
    }

    if (
      Array.isArray(
        documentsHistory
      ) &&
      jobId
    ) {
      const historyItem =
        documentsHistory.find(
          (item) =>
            String(
              item?.jobId ??
                item?.job_id ??
                ""
            ) ===
            String(jobId)
        );

      if (
        historyItem?.filename
      ) {
        return String(
          historyItem.filename
        );
      }
    }

    const possibleFilename =
      result?.filename ||
      result?.file_name ||
      result?.input_filename ||
      result?.input_file ||
      result?.input_pdf;

    if (
      possibleFilename
    ) {
      const value =
        String(
          possibleFilename
        );

      const parts =
        value.split(
          /[\\/]/g
        );

      return (
        parts[
          parts.length - 1
        ] ||
        value
      );
    }

    return "Processed Document";
  }, [
    filenameProp,
    documentsHistory,
    jobId,
    result,
  ]);

  const [
    searchQuery,
    setSearchQuery,
  ] = useState("");

  const [
    indexSearchQuery,
    setIndexSearchQuery,
  ] = useState("");

  const [
    indexSearchResults,
    setIndexSearchResults,
  ] = useState([]);

  const [
    searchLoading,
    setSearchLoading,
  ] = useState(false);

  const [
    searchError,
    setSearchError,
  ] = useState("");

  /*
   * IMPORTANT:
   *
   * This state belongs ONLY to Search Indexing.
   *
   * It is intentionally separate from Data Entry JSON.
   */

  const [
    selectedIndexSearchResult,
    setSelectedIndexSearchResult,
  ] = useState(null);

  const [
    searchPerformed,
    setSearchPerformed,
  ] = useState(false);

  const [
    jsonVisible,
    setJsonVisible,
  ] = useState(true);

  const [
    searchJsonVisible,
    setSearchJsonVisible,
  ] = useState(true);

  const [
    saveLoading,
    setSaveLoading,
  ] = useState(false);

  const [
    saveMessage,
    setSaveMessage,
  ] = useState("");

  const [
    saveError,
    setSaveError,
  ] = useState("");

  /* -------------------------------------------------------
     RESET SEARCH WHEN ACTIVE DOCUMENT CHANGES
     ------------------------------------------------------- */

  useEffect(() => {
    setIndexSearchQuery("");
    setIndexSearchResults([]);
    setSelectedIndexSearchResult(null);
    setSearchPerformed(false);
    setSearchError("");
    setSearchJsonVisible(true);
  }, [jobId]);

  /* -------------------------------------------------------
     DERIVED DATA
     ------------------------------------------------------- */

  const allText =
    useMemo(
      () =>
        getAllText(result),
      [result]
    );

  const blocks =
    useMemo(
      () =>
        getBlocksFromResult(
          result
        ),
      [result]
    );

  const dataRecords =
    useMemo(
      () =>
        buildDataRecords(
          result
        ),
      [result]
    );

  const complianceChecks =
    useMemo(
      () =>
        buildComplianceChecks(
          result
        ),
      [result]
    );

  /* -------------------------------------------------------
     DATA ENTRY SEARCH
     ------------------------------------------------------- */

  const filteredDataRecords =
    useMemo(() => {
      if (
        !searchQuery.trim()
      ) {
        return dataRecords;
      }

      const query =
        searchQuery
          .toLowerCase()
          .trim();

      return dataRecords.filter(
        (record) =>
          safeString(
            record.name
          )
            .toLowerCase()
            .includes(query) ||
          safeString(
            record.value
          )
            .toLowerCase()
            .includes(query) ||
          safeString(
            record.type
          )
            .toLowerCase()
            .includes(query)
      );
    }, [
      dataRecords,
      searchQuery,
    ]);

  /* -------------------------------------------------------
     LOCAL OCR BLOCK SEARCH
     ------------------------------------------------------- */

  const localSearchResults =
    useMemo(() => {
      if (
        !indexSearchQuery.trim()
      ) {
        return blocks.slice(
          0,
          8
        );
      }

      const query =
        indexSearchQuery
          .toLowerCase()
          .trim();

      return blocks.filter(
        (block) =>
          safeString(
            block.text
          )
            .toLowerCase()
            .includes(query)
      );
    }, [
      blocks,
      indexSearchQuery,
    ]);

  const searchResults =
    indexSearchQuery.trim() &&
    searchPerformed
      ? indexSearchResults
      : indexSearchQuery.trim()
      ? localSearchResults
      : blocks.slice(
          0,
          8
        );

  /* =======================================================
     SEARCH JSON
     ======================================================= */

  const createSearchJSON = (
    item,
    query,
    index
  ) => {
    if (
      item &&
      item.json_details &&
      typeof item.json_details ===
        "object"
    ) {
      return item.json_details;
    }

    if (
      item &&
      item.jsonDetails &&
      typeof item.jsonDetails ===
        "object"
    ) {
      return item.jsonDetails;
    }

    return {
      query:
        query,

      matched_text:
        safeString(
          item?.text ??
            item?.text_content ??
            item?.content ??
            item?.html ??
            item?.value
        ).trim(),

      page_number:
        Number(
          item?.page ??
            item?.page_number ??
            1
        ),

      block_number:
        Number(
          item?.blockIndex ??
            item?.block_number ??
            index
        ),

      ocr_block:
        item?.ocr_block ||
        item?.block ||
        item?.ocr_data ||
        null,

      page:
        item?.page_data ||
        item?.page_result ||
        item?.page ||
        null,
    };
  };

  /* -------------------------------------------------------
     DATABASE SEARCH
     ------------------------------------------------------- */

  const searchDatabase =
    async () => {
      const query =
        indexSearchQuery.trim();

      if (!query) {
        setIndexSearchResults(
          []
        );

        setSelectedIndexSearchResult(
          null
        );

        setSearchPerformed(
          false
        );

        setSearchError(
          ""
        );

        return;
      }

      if (!jobId) {
        setSearchError(
          "No OCR job ID is available. Please process the document again."
        );

        return;
      }

      setSearchLoading(
        true
      );

      setSearchError(
        ""
      );

      try {
        const endpoint =
          `${API_BASE_URL}/api/search/${encodeURIComponent(
            jobId
          )}?q=${encodeURIComponent(
            query
          )}`;

        console.log(
          "SEARCH INDEX REQUEST:",
          endpoint
        );

        const response =
          await fetch(
            endpoint
          );

        const data =
          await response.json();

        console.log(
          "SEARCH INDEX RESPONSE:",
          data
        );

        if (
          !response.ok
        ) {
          throw new Error(
            data.detail ||
              data.message ||
              "Search failed."
          );
        }

        const rawResults =
          Array.isArray(
            data.results
          )
            ? data.results
            : [];

        const normalizedResults =
          rawResults.map(
            (
              item,
              index
            ) => {
              const pageNumber =
                Number(
                  item?.page ??
                    item?.page_number ??
                    1
                );

              const blockNumber =
                Number(
                  item?.blockIndex ??
                    item?.block_number ??
                    index
                );

              const text =
                safeString(
                  item?.text ??
                    item?.text_content ??
                    item?.content ??
                    item?.html ??
                    item?.value
                ).trim();

              const jsonDetails =
                createSearchJSON(
                  item,
                  query,
                  index
                );

              return {
                ...item,

                page:
                  pageNumber,

                page_number:
                  pageNumber,

                blockIndex:
                  blockNumber,

                block_number:
                  blockNumber,

                text,

                type:
                  item?.type ||
                  item?.label ||
                  "Text Block",

                json_details:
                  jsonDetails,
              };
            }
          );

        setIndexSearchResults(
          normalizedResults
        );

        setSearchPerformed(
          true
        );

        setSearchJsonVisible(
          true
        );

        /*
         * IMPORTANT:
         *
         * This updates ONLY Search Indexing.
         *
         * It does NOT touch the Data Entry
         * JSON preview state.
         */

        if (
          normalizedResults.length >
          0
        ) {
          setSelectedIndexSearchResult(
            normalizedResults[0]
          );
        } else {
          setSelectedIndexSearchResult(
            null
          );
        }

        /*
         * Search results are intentionally NOT saved
         * into localStorage.
         *
         * The active document itself is owned by App.jsx.
         */

      } catch (
        error
      ) {
        console.error(
          "Search Indexing failed:",
          error
        );

        setIndexSearchResults(
          []
        );

        setSelectedIndexSearchResult(
          null
        );

        setSearchPerformed(
          true
        );

        setSearchError(
          error.message ||
            "Could not search the database."
        );
      } finally {
        setSearchLoading(
          false
        );
      }
    };

  /* -------------------------------------------------------
     SEARCH ON ENTER
     ------------------------------------------------------- */

  const handleSearchKeyDown =
    (event) => {
      if (
        event.key ===
        "Enter"
      ) {
        searchDatabase();
      }
    };

  /* -------------------------------------------------------
     LANGUAGES / STATS
     ------------------------------------------------------- */

  const languages =
    getLanguages(result);

  const pages =
    getPagesCount(result);

  const accuracy =
    getAccuracy(result);

  const passedChecks =
    complianceChecks.filter(
      (check) =>
        check.status ===
        "passed"
    ).length;

  const warningChecks =
    complianceChecks.filter(
      (check) =>
        check.status ===
        "warning"
    ).length;

  const errorChecks =
    complianceChecks.filter(
      (check) =>
        check.status ===
        "error"
    ).length;

  /* -------------------------------------------------------
     DATA ENTRY JSON
     ------------------------------------------------------- */

  /*
   * IMPORTANT:
   *
   * Data Entry JSON always uses the original OCR result.
   *
   * Search Indexing NEVER changes this.
   */

  const formattedJSON =
    result
      ? JSON.stringify(
          result,
          null,
          2
        )
      : JSON.stringify(
          {
            message:
              "No OCR result available.",
          },
          null,
          2
        );

  /* =======================================================
     SEARCH INDEXING JSON PREVIEW
     ======================================================= */

  const searchPreviewJSON =
    selectedIndexSearchResult
      ? JSON.stringify(
          selectedIndexSearchResult.json_details ||
            selectedIndexSearchResult,
          null,
          2
        )
      : "";

  /* -------------------------------------------------------
     DOWNLOAD JSON
     ------------------------------------------------------- */

  const downloadJSON =
    async () => {
      try {
        if (jobId) {
          const endpoint =
            DOWNLOAD_ENDPOINTS.json.replace(
              "{job_id}",
              jobId
            );

          const response =
            await fetch(
              `${API_BASE_URL}${endpoint}`
            );

          if (
            response.ok
          ) {
            const blob =
              await response.blob();

            const url =
              window.URL.createObjectURL(
                blob
              );

            const link =
              document.createElement(
                "a"
              );

            link.href =
              url;

            link.download =
              `${filename.replace(
                /\.pdf$/i,
                ""
              )}_ocr.json`;

            document.body.appendChild(
              link
            );

            link.click();

            link.remove();

            window.URL.revokeObjectURL(
              url
            );

            return;
          }
        }

        const blob =
          new Blob(
            [
              formattedJSON,
            ],
            {
              type:
                "application/json",
            }
          );

        const url =
          window.URL.createObjectURL(
            blob
          );

        const link =
          document.createElement(
            "a"
          );

        link.href =
          url;

        link.download =
          `${filename.replace(
            /\.pdf$/i,
            ""
          )}_ocr.json`;

        document.body.appendChild(
          link
        );

        link.click();

        link.remove();

        window.URL.revokeObjectURL(
          url
        );
      } catch (
        error
      ) {
        console.error(
          "JSON download failed:",
          error
        );
      }
    };

  /* -------------------------------------------------------
     DOWNLOAD SEARCH JSON
     ------------------------------------------------------- */

  const downloadSearchJSON =
    () => {
      if (
        !selectedIndexSearchResult
      ) {
        return;
      }

      try {
        const json =
          JSON.stringify(
            selectedIndexSearchResult.json_details ||
              selectedIndexSearchResult,
            null,
            2
          );

        const blob =
          new Blob(
            [json],
            {
              type:
                "application/json",
            }
          );

        const url =
          window.URL.createObjectURL(
            blob
          );

        const link =
          document.createElement(
            "a"
          );

        link.href =
          url;

        link.download =
          `${filename.replace(
            /\.pdf$/i,
            ""
          )}_search_${indexSearchQuery
            .trim()
            .replace(
              /\s+/g,
              "_"
            )}.json`;

        document.body.appendChild(
          link
        );

        link.click();

        link.remove();

        window.URL.revokeObjectURL(
          url
        );
      } catch (
        error
      ) {
        console.error(
          "Search JSON download failed:",
          error
        );
      }
    };

  /* -------------------------------------------------------
     SAVE ALL TO DATABASE
     ------------------------------------------------------- */

  const saveToDatabase =
    async () => {
      console.log(
        "========================================"
      );

      console.log(
        "SAVE ALL TO DATABASE BUTTON CLICKED"
      );

      console.log(
        "========================================"
      );

      console.log(
        "result:",
        result
      );

      console.log(
        "jobId:",
        jobId
      );

      console.log(
        "dataRecords:",
        dataRecords
      );

      if (!result) {
        console.error(
          "SAVE STOPPED: No OCR result"
        );

        setSaveError(
          "No OCR result is available to save."
        );

        return;
      }

      if (!jobId) {
        console.error(
          "SAVE STOPPED: No job ID"
        );

        setSaveError(
          "No OCR job ID is available. Please process the document again."
        );

        return;
      }

      if (
        !dataRecords.length
      ) {
        console.error(
          "SAVE STOPPED: No data records"
        );

        setSaveError(
          "No extracted data entries are available to save."
        );

        return;
      }

      setSaveLoading(
        true
      );

      setSaveMessage(
        ""
      );

      setSaveError(
        ""
      );

      const payload = {
        job_id:
          jobId,

        entries:
          dataRecords.map(
            (record) => ({
              name:
                record.name,

              type:
                record.type,

              value:
                record.value,

              confidence:
                Number(
                  record.confidence ||
                    0
                ),

              status:
                record.status ||
                "Ready",
            })
          ),
      };

      console.log(
        "DATA ENTRY PAYLOAD:"
      );

      console.log(
        payload
      );

      try {
        console.log(
          "Calling:",
          `${API_BASE_URL}/api/data-entry/save`
        );

        const response =
          await fetch(
            `${API_BASE_URL}/api/data-entry/save`,
            {
              method:
                "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body:
                JSON.stringify(
                  payload
                ),
            }
          );

        console.log(
          "Response status:",
          response.status
        );

        console.log(
          "Response OK:",
          response.ok
        );

        const data =
          await response.json();

        console.log(
          "Backend response:",
          data
        );

        if (
          !response.ok
        ) {
          throw new Error(
            data.detail ||
              data.message ||
              "Data Entry database save failed."
          );
        }

        const dataEntry =
          data.data_entry ||
          data;

        console.log(
          "DATA ENTRY SAVE SUCCESSFUL"
        );

        console.log(
          "Saved count:",
          dataEntry.saved_count
        );

        console.log(
          "Document ID:",
          dataEntry.document_id
        );

        setSaveMessage(
          `Saved successfully. ${Number(
            dataEntry.saved_count ||
              0
          )} data entries saved. Document ID: ${
            dataEntry.document_id ||
            "—"
          }`
        );

        /*
         * Database-save response is intentionally not used
         * as the source of OCR document state.
         *
         * App.jsx remains the source of truth.
         */
      } catch (
        error
      ) {
        console.error(
          "Data Entry database save failed:",
          error
        );

        setSaveError(
          error.message ||
            "Could not save data entries to database."
        );
      } finally {
        setSaveLoading(
          false
        );
      }
    };

  /* =========================================================
     RENDER
     ========================================================= */

  return (
    <main className="results-page">

      {/* ===================================================
          HEADER
          =================================================== */}

      <section className="results-page-header">

        <div className="results-page-title-wrap">

          <div className="results-main-icon">
            ✦
          </div>

          <div>

            <h1>
              Document Intelligence
            </h1>

            <p>
              Turn your extracted data into actionable
              insights with Search Indexing, Data Entry
              and Compliance.
            </p>

          </div>

        </div>

        <div className="results-document-badge">

          <span className="results-document-dot" />

          {filename}

        </div>

      </section>

      {/* ===================================================
          EMPTY STATE
          =================================================== */}

      {!result ? (

        <section className="results-empty-state">

          <div className="results-empty-icon">
            ⌕
          </div>

          <h2>
            No processed document available
          </h2>

          <p>
            Process a document from the Documents page
            first. The generated OCR JSON will
            automatically appear here.
          </p>

        </section>

      ) : (

        <>

          {/* =================================================
              1. DATA ENTRY
              ================================================= */}

          <section className="intelligence-section data-entry-section">

            <div className="intelligence-section-header">

              <div className="intelligence-title-wrap">

                <div className="section-icon data-entry-icon">
                  ▤
                </div>

                <div>

                  <h2>
                    Data Entry
                  </h2>

                  <p>
                    Extracted data is organized and ready
                    to be saved as structured records in
                    your database.
                  </p>

                </div>

              </div>

            </div>

            <div className="data-entry-layout">

              {/* EXTRACTED RECORDS */}

              <div className="records-panel">

                <div className="panel-topbar">

                  <div className="panel-title-group">

                    <strong>
                      Extracted Records
                    </strong>

                    <span className="record-count">
                      {filteredDataRecords.length} records
                    </span>

                  </div>

                  <div className="records-actions">

                    <div className="small-search">

                      <span>
                        ⌕
                      </span>

                      <input
                        type="text"
                        placeholder="Search records..."
                        value={
                          searchQuery
                        }
                        onChange={(
                          event
                        ) =>
                          setSearchQuery(
                            event.target.value
                          )
                        }
                      />

                    </div>

                    <button
                      className="primary-small-button"
                      onClick={
                        saveToDatabase
                      }
                      disabled={
                        saveLoading
                      }
                    >
                      {saveLoading
                        ? "Saving..."
                        : "▣  Save All to Database"}
                    </button>

                  </div>

                </div>

                <div className="records-table-wrapper">

                  <table className="records-table">

                    <thead>

                      <tr>

                        <th className="checkbox-column">
                          <input
                            type="checkbox"
                            disabled
                          />
                        </th>

                        <th>
                          Name
                        </th>

                        <th>
                          Type
                        </th>

                        <th>
                          Value
                        </th>

                        <th>
                          Confidence
                        </th>

                        <th>
                          Status
                        </th>

                      </tr>

                    </thead>

                    <tbody>

                      {filteredDataRecords.length === 0 ? (

                        <tr>

                          <td
                            colSpan="6"
                            className="table-empty"
                          >
                            No structured records
                            could be extracted.
                          </td>

                        </tr>

                      ) : (

                        filteredDataRecords.map(
                          (
                            record,
                            index
                          ) => (

                            <tr
                              key={`${record.name}-${index}`}
                            >

                              <td className="checkbox-column">

                                <input
                                  type="checkbox"
                                  disabled
                                />

                              </td>

                              <td className="record-name">
                                {record.name}
                              </td>

                              <td>

                                <span className="type-label">
                                  {record.type}
                                </span>

                              </td>

                              <td
                                className="record-value"
                                title={
                                  record.value
                                }
                              >
                                {record.value}
                              </td>

                              <td>

                                <span className="confidence-value">
                                  {Number(
                                    record.confidence ||
                                      0
                                  ).toFixed(
                                    1
                                  )}
                                  %
                                </span>

                              </td>

                              <td>

                                <span className="status-pill ready">
                                  ✓ Ready
                                </span>

                              </td>

                            </tr>

                          )
                        )

                      )}

                    </tbody>

                  </table>

                </div>

              </div>

              {/* JSON PREVIEW */}

              <div className="record-preview-panel">

                <div className="record-preview-header">

                  <div className="preview-heading">

                    <div className="preview-small-icon">
                      {"{}"}
                    </div>

                    <strong>
                      JSON Preview
                    </strong>

                  </div>

                  <span className="record-count">
                    {pages} page
                    {pages === 1
                      ? ""
                      : "s"}
                  </span>

                </div>

                <div className="json-tabs">

                  <button
                    className={
                      jsonVisible
                        ? "active"
                        : ""
                    }
                    onClick={() =>
                      setJsonVisible(
                        true
                      )
                    }
                  >
                    JSON
                  </button>

                  <button
                    className={
                      !jsonVisible
                        ? "active"
                        : ""
                    }
                    onClick={() =>
                      setJsonVisible(
                        false
                      )
                    }
                  >
                    Structured Data
                  </button>

                </div>

                <div className="json-viewer">

                  {jsonVisible ? (

                    <pre>
                      {formattedJSON}
                    </pre>

                  ) : (

                    <div className="structured-json-view">

                      <div className="json-stat-card">

                        <span>
                          Pages
                        </span>

                        <strong>
                          {pages}
                        </strong>

                      </div>

                      <div className="json-stat-card">

                        <span>
                          Languages
                        </span>

                        <strong>
                          {languages.length}
                        </strong>

                      </div>

                      <div className="json-stat-card">

                        <span>
                          OCR Blocks
                        </span>

                        <strong>
                          {blocks.length}
                        </strong>

                      </div>

                      <div className="json-stat-card">

                        <span>
                          Accuracy
                        </span>

                        <strong>
                          {accuracy > 0
                            ? `${accuracy.toFixed(
                                1
                              )}%`
                            : "—"}
                        </strong>

                      </div>

                      <div className="structured-json-summary">

                        <h3>
                          Detected Languages
                        </h3>

                        {languages.length > 0 ? (

                          <div className="language-tags">

                            {languages.map(
                              (
                                language
                              ) => (

                                <span
                                  key={
                                    language
                                  }
                                >
                                  {language}
                                </span>

                              )
                            )}

                          </div>

                        ) : (

                          <p>
                            No language information
                            available.
                          </p>

                        )}

                      </div>

                    </div>

                  )}

                </div>

                <button
                  className="json-download-button"
                  onClick={
                    downloadJSON
                  }
                >
                  ↓ &nbsp; Download JSON
                </button>

              </div>

            </div>

            {(saveMessage ||
              saveError) && (

              <div
                className={
                  saveError
                    ? "database-save-status error"
                    : "database-save-status success"
                }
              >

                <span>
                  {saveError
                    ? "×"
                    : "✓"}
                </span>

                <div>

                  <strong>
                    {saveError
                      ? "Database save failed"
                      : "Database save successful"}
                  </strong>

                  <p>
                    {saveError ||
                      saveMessage}
                  </p>

                </div>

              </div>

            )}

          </section>

          {/* =================================================
              2. SEARCH INDEXING
              ================================================= */}

          <section className="intelligence-section search-indexing-section">

            <div className="intelligence-section-header">

              <div className="intelligence-title-wrap">

                <div className="section-icon search-icon">
                  ⌕
                </div>

                <div>

                  <h2>
                    Search Indexing
                  </h2>

                  <p>
                    Search and find information from
                    your extracted document using
                    keywords, names, IDs or any text.
                  </p>

                </div>

              </div>

            </div>

            <div className="search-indexing-layout">

              {/* SEARCH RESULTS */}

              <div className="search-results-panel">

                <div className="search-input-row">

                  <div className="large-search">

                    <span>
                      ⌕
                    </span>

                    <input
                      type="text"
                      placeholder="Search by keyword, name, ID, or content..."
                      value={
                        indexSearchQuery
                      }
                      onChange={(
                        event
                      ) => {

                        setIndexSearchQuery(
                          event.target.value
                        );

                        setIndexSearchResults(
                          []
                        );

                        /*
                         * IMPORTANT:
                         *
                         * Reset ONLY Search Indexing
                         * selection.
                         */

                        setSelectedIndexSearchResult(
                          null
                        );

                        setSearchPerformed(
                          false
                        );

                        setSearchError(
                          ""
                        );

                      }}
                      onKeyDown={
                        handleSearchKeyDown
                      }
                    />

                  </div>

                  <button
                    className="search-button"
                    onClick={
                      searchDatabase
                    }
                    disabled={
                      searchLoading
                    }
                  >
                    {searchLoading
                      ? "Searching..."
                      : "Search"}
                  </button>

                </div>

                {searchError && (

                  <div className="search-empty">

                    <div>
                      ×
                    </div>

                    <p>
                      {searchError}
                    </p>

                  </div>

                )}

                <div className="search-results-heading">

                  <strong>
                    Search Results
                  </strong>

                  <span>
                    {indexSearchQuery.trim()
                      ? `${searchResults.length} matches`
                      : `${blocks.length} extracted blocks`}
                  </span>

                </div>

                <div className="search-results-list">

                  {searchResults.length === 0 ? (

                    <div className="search-empty">

                      <div>
                        ⌕
                      </div>

                      <p>
                        No matching text was
                        found in the processed
                        document.
                      </p>

                    </div>

                  ) : (

                    searchResults.map(
                      (
                        block,
                        index
                      ) => (

                        <div
                          className="search-result-card"
                          key={`${block.page}-${block.blockIndex}-${index}`}
                          onClick={() => {

                            const selectedBlock = {
                              ...block,

                              json_details:
                                block.json_details ||
                                createSearchJSON(
                                  block,
                                  indexSearchQuery.trim(),
                                  index
                                ),
                            };

                            /*
                             * IMPORTANT:
                             *
                             * ONLY Search Indexing JSON
                             * gets updated here.
                             *
                             * Data Entry JSON is untouched.
                             */

                            setSelectedIndexSearchResult(
                              selectedBlock
                            );

                            setSearchJsonVisible(
                              true
                            );

                            /*
                             * Keep existing
                             * highlighted PDF behavior.
                             */

                            if (
                              jobId &&
                              indexSearchQuery.trim()
                            ) {
                              const pdfUrl =
                                `${API_BASE_URL}/api/search/${encodeURIComponent(
                                  jobId
                                )}/pdf?q=${encodeURIComponent(
                                  indexSearchQuery.trim()
                                )}`;

                              window.open(
                                pdfUrl,
                                "_blank",
                                "noopener,noreferrer"
                              );
                            }

                          }}
                        >

                          <div className="search-result-icon">
                            ▤
                          </div>

                          <div className="search-result-content">

                            <div className="search-result-title">
                              Page {block.page}
                            </div>

                            <div className="search-result-text">
                              {block.text}
                            </div>

                            <div className="search-result-meta">

                              Page {block.page}

                              <span>
                                •
                              </span>

                              {block.type ||
                                block.label ||
                                "Text Block"}

                            </div>

                          </div>

                          <div className="search-result-arrow">
                            &gt;
                          </div>

                        </div>

                      )
                    )

                  )}

                </div>

              </div>

              {/* =================================================
                  SEARCH INDEXING JSON PREVIEW
                  ================================================= */}

              <div className="json-output-panel">

                <div className="json-output-header">

                  <div className="json-output-title">

                    <div className="json-file-icon">
                      {"{}"}
                    </div>

                    <strong>
                      JSON Preview
                    </strong>

                  </div>

                </div>

                <div className="json-tabs">

                  <button
                    className={
                      searchJsonVisible
                        ? "active"
                        : ""
                    }
                    onClick={() =>
                      setSearchJsonVisible(
                        true
                      )
                    }
                  >
                    JSON
                  </button>

                  <button
                    className={
                      !searchJsonVisible
                        ? "active"
                        : ""
                    }
                    onClick={() =>
                      setSearchJsonVisible(
                        false
                      )
                    }
                  >
                    Structured Data
                  </button>

                </div>

                <div className="json-viewer">

                  {searchJsonVisible ? (

                    selectedIndexSearchResult ? (

                      <pre>
                        {renderHighlightedJSON(
                          searchPreviewJSON,
                          indexSearchQuery
                        )}
                      </pre>

                    ) : (

                      <div className="search-empty">

                        <div>
                          ⌕
                        </div>

                        <p>
                          Search the document to
                          preview matching JSON.
                        </p>

                      </div>

                    )

                  ) : (

                    <div className="structured-json-view">

                      <div className="json-stat-card">

                        <span>
                          Page
                        </span>

                        <strong>
                          {selectedIndexSearchResult?.page ??
                            "—"}
                        </strong>

                      </div>

                      <div className="json-stat-card">

                        <span>
                          Block
                        </span>

                        <strong>
                          {selectedIndexSearchResult?.block_number ??
                            "—"}
                        </strong>

                      </div>

                      <div className="json-stat-card">

                        <span>
                          Matches
                        </span>

                        <strong>
                          {searchResults.length}
                        </strong>

                      </div>

                      <div className="json-stat-card">

                        <span>
                          Query
                        </span>

                        <strong>
                          {indexSearchQuery ||
                            "—"}
                        </strong>

                      </div>

                    </div>

                  )}

                </div>

                <button
                  className="json-download-button"
                  onClick={
                    downloadSearchJSON
                  }
                  disabled={
                    !selectedIndexSearchResult
                  }
                >
                  ↓ &nbsp; Download JSON
                </button>

              </div>

            </div>

          </section>

          {/* =================================================
              3. COMPLIANCE
              ================================================= */}

          <section className="intelligence-section compliance-section">

            <div className="intelligence-section-header">

              <div className="intelligence-title-wrap">

                <div className="section-icon compliance-icon">
                  ♢
                </div>

                <div>

                  <h2>
                    Compliance
                  </h2>

                  <p>
                    Validate your documents against
                    predefined rules and identify
                    any issues or missing information.
                  </p>

                </div>

              </div>

            </div>

            <div className="compliance-layout">

              {/* SUMMARY */}

              <div className="compliance-summary-panel">

                <h3>
                  Compliance Checks
                </h3>

                <div className="compliance-stat-grid">

                  <div className="compliance-stat">

                    <span className="stat-symbol">
                      ✣
                    </span>

                    <small>
                      Total Checks
                    </small>

                    <strong>
                      {complianceChecks.length}
                    </strong>

                  </div>

                  <div className="compliance-stat passed">

                    <span className="stat-symbol">
                      ✓
                    </span>

                    <small>
                      Passed
                    </small>

                    <strong>
                      {passedChecks}
                    </strong>

                  </div>

                  <div className="compliance-stat warning">

                    <span className="stat-symbol">
                      △
                    </span>

                    <small>
                      Warnings
                    </small>

                    <strong>
                      {warningChecks}
                    </strong>

                  </div>

                  <div className="compliance-stat error">

                    <span className="stat-symbol">
                      ×
                    </span>

                    <small>
                      Errors
                    </small>

                    <strong>
                      {errorChecks}
                    </strong>

                  </div>

                </div>

              </div>

              {/* CHECKLIST */}

              <div className="compliance-checklist-panel">

                <h3>
                  Checklist
                </h3>

                <div className="checklist">

                  {complianceChecks.map(
                    (
                      check,
                      index
                    ) => (

                      <div
                        className="checklist-row"
                        key={`${check.title}-${index}`}
                      >

                        <div className="checklist-document-icon">
                          ▤
                        </div>

                        <div className="checklist-text">

                          <span>
                            {check.title}
                          </span>

                        </div>

                        <span
                          className={`check-status ${check.status}`}
                        >

                          {check.status ===
                            "passed" &&
                            "✓ Passed"}

                          {check.status ===
                            "warning" &&
                            "△ Warning"}

                          {check.status ===
                            "error" &&
                            "× Error"}

                        </span>

                      </div>

                    )
                  )}

                </div>

              </div>

              {/* ISSUES */}

              <div className="issues-panel">

                <h3>
                  Issues & Suggestions
                </h3>

                {warningChecks === 0 &&
                errorChecks === 0 ? (

                  <div className="issue-card success-issue">

                    <div className="issue-icon">
                      ✓
                    </div>

                    <div>

                      <strong>
                        Document looks good
                      </strong>

                      <p>
                        No major compliance issues
                        were detected in the
                        processed OCR result.
                      </p>

                    </div>

                  </div>

                ) : (

                  <>

                    {complianceChecks
                      .filter(
                        (
                          check
                        ) =>
                          check.status ===
                            "warning" ||
                          check.status ===
                            "error"
                      )
                      .map(
                        (
                          check,
                          index
                        ) => (

                          <div
                            className={`issue-card ${
                              check.status ===
                              "error"
                                ? "error-issue"
                                : "warning-issue"
                            }`}
                            key={`${check.title}-${index}`}
                          >

                            <div className="issue-icon">

                              {check.status ===
                              "error"
                                ? "×"
                                : "△"}

                            </div>

                            <div>

                              <strong>
                                {check.title}
                              </strong>

                              <p>
                                {check.description}
                              </p>

                            </div>

                          </div>

                        )
                      )}

                  </>

                )}

              </div>

            </div>

          </section>

        </>

      )}

    </main>
  );
}