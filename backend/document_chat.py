import os
import sys
import argparse
import re
from pathlib import Path

import pymupdf
from dotenv import load_dotenv
from groq import Groq


# ======================================================================
# CONFIGURATION
# ======================================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_CHAT_MODEL = os.getenv(
    "GROQ_CHAT_MODEL",
    "openai/gpt-oss-20b"
)

# Maximum document characters sent in one request.
#
# GPT-OSS-20B has a large context window, but keeping a practical
# application limit prevents unnecessarily huge requests.
MAX_DOCUMENT_CHARS = 350000

# Chunk size for very large documents.
CHUNK_SIZE = 60000

# Maximum conversation messages retained.
MAX_HISTORY_MESSAGES = 20


# ======================================================================
# ENVIRONMENT VALIDATION
# ======================================================================

def validate_environment():
    """
    Validate the Groq API configuration.
    """

    if not GROQ_API_KEY:

        print()
        print("=" * 70)
        print("ERROR: GROQ_API_KEY is not configured.")
        print("=" * 70)
        print()
        print("Add this to your .env file:")
        print()
        print("GROQ_API_KEY=your_groq_api_key")
        print()
        print("Get your API key from:")
        print("https://console.groq.com/keys")
        print()

        sys.exit(1)


# ======================================================================
# GROQ CLIENT
# ======================================================================

def create_groq_client():
    """
    Create and return the Groq client.
    """

    return Groq(
        api_key=GROQ_API_KEY
    )


# ======================================================================
# TEXT NORMALIZATION
# ======================================================================

def normalize_text(text):
    """
    Normalize extracted PDF text while preserving useful structure.
    """

    if not text:
        return ""

    text = str(text)

    # Remove null characters.
    text = text.replace(
        "\x00",
        ""
    )

    # Normalize line endings.
    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    # Normalize spaces and tabs.
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines.
    text = re.sub(
        r"\n{4,}",
        "\n\n",
        text
    )

    return text.strip()


# ======================================================================
# PDF TEXT EXTRACTION
# ======================================================================

def extract_pdf_text(pdf_path):
    """
    Extract selectable text directly from the supplied PDF.

    No OCR is performed here.

    The PDF is expected to already contain extracted text.
    """

    pdf_path = Path(
        pdf_path
    ).resolve()

    # --------------------------------------------------------------
    # Validate file
    # --------------------------------------------------------------

    if not pdf_path.exists():

        raise FileNotFoundError(
            f"PDF not found:\n{pdf_path}"
        )

    if not pdf_path.is_file():

        raise ValueError(
            f"Input path is not a file:\n{pdf_path}"
        )

    if pdf_path.suffix.lower() != ".pdf":

        raise ValueError(
            "Input file must be a PDF."
        )

    print()
    print("=" * 70)
    print("                    PDF TEXT EXTRACTION")
    print("=" * 70)
    print()

    print(
        f"File: {pdf_path.name}"
    )

    print()

    # --------------------------------------------------------------
    # Open PDF
    # --------------------------------------------------------------

    try:

        document = pymupdf.open(
            str(pdf_path)
        )

    except Exception as exc:

        raise RuntimeError(
            f"Could not open PDF:\n{exc}"
        )

    pages = []

    total_characters = 0

    try:

        # ----------------------------------------------------------
        # Extract every page
        # ----------------------------------------------------------

        for page_number, page in enumerate(
            document,
            start=1
        ):

            try:

                text = page.get_text(
                    "text"
                )

            except Exception as exc:

                print(
                    f"WARNING: Could not extract "
                    f"page {page_number}: {exc}"
                )

                text = ""

            text = normalize_text(
                text
            )

            page_data = {
                "page": page_number,
                "text": text,
                "characters": len(text)
            }

            pages.append(
                page_data
            )

            total_characters += len(
                text
            )

            print(
                f"Page {page_number:4d}: "
                f"{len(text):8,d} characters"
            )

    finally:

        document.close()

    # --------------------------------------------------------------
    # Build complete document text
    # --------------------------------------------------------------

    full_text_parts = []

    for page in pages:

        full_text_parts.append(
            f"\n\n===== PAGE {page['page']} =====\n\n"
            f"{page['text']}"
        )

    full_text = "".join(
        full_text_parts
    ).strip()

    # --------------------------------------------------------------
    # Check whether text exists
    # --------------------------------------------------------------

    has_text = (
        total_characters > 50
    )

    print()

    print(
        f"Total pages:        {len(pages)}"
    )

    print(
        f"Total characters:   {total_characters:,}"
    )

    print(
        "Text detected:      "
        f"{'YES' if has_text else 'NO'}"
    )

    print()

    if not has_text:

        print("=" * 70)
        print("WARNING")
        print("=" * 70)
        print()
        print(
            "No usable selectable text was found in this PDF."
        )
        print()
        print(
            "This chatbot expects a PDF that has already "
            "gone through your text extraction/OCR pipeline."
        )
        print()

    return {
        "filename": pdf_path.name,
        "filepath": str(pdf_path),
        "pages": pages,
        "full_text": full_text,
        "total_pages": len(pages),
        "total_characters": total_characters,
        "has_text": has_text,
        "source": "PyMuPDF"
    }


# ======================================================================
# DOCUMENT INFORMATION
# ======================================================================

def print_document_information(
    document_data
):
    """
    Display basic information about the loaded PDF.
    """

    print()
    print("=" * 70)
    print("                    DOCUMENT LOADED")
    print("=" * 70)
    print()

    print(
        f"Document:           "
        f"{document_data['filename']}"
    )

    print(
        f"Pages:              "
        f"{document_data['total_pages']}"
    )

    print(
        f"Characters:         "
        f"{document_data['total_characters']:,}"
    )

    print(
        f"Text source:        "
        f"{document_data['source']}"
    )

    print()


# ======================================================================
# PAGE RELEVANCE
# ======================================================================

def score_page_relevance(
    page_text,
    query
):
    """
    Calculate a lightweight lexical relevance score.

    This is only used for very large documents where the complete
    document cannot efficiently be included in every question.
    """

    if not page_text:

        return 0

    if not query:

        return 0

    query = query.strip().lower()

    if not query:

        return 0

    words = re.findall(
        r"\w+",
        query,
        flags=re.UNICODE
    )

    if not words:

        return 0

    text = page_text.lower()

    score = 0

    for word in words:

        # Ignore extremely short words.
        if len(word) < 2:
            continue

        occurrences = text.count(
            word
        )

        if occurrences:

            score += min(
                occurrences,
                5
            )

    return score


def get_relevant_pages(
    document_data,
    query,
    max_pages=30
):
    """
    Select the most relevant pages for a question.
    """

    pages = document_data[
        "pages"
    ]

    scored_pages = []

    for page in pages:

        score = score_page_relevance(
            page["text"],
            query
        )

        scored_pages.append(
            (
                score,
                page["page"],
                page["text"]
            )
        )

    # Pages containing query terms.
    relevant_pages = [
        item
        for item in scored_pages
        if item[0] > 0
    ]

    relevant_pages.sort(
        key=lambda item: (
            -item[0],
            item[1]
        )
    )

    selected_pages = relevant_pages[
        :max_pages
    ]

    # If no lexical match exists, use the first pages
    # rather than returning an empty context.
    if not selected_pages:

        selected_pages = scored_pages[
            :max_pages
        ]

    # Restore document page order.
    selected_pages.sort(
        key=lambda item: item[1]
    )

    return selected_pages


# ======================================================================
# CONTEXT BUILDING
# ======================================================================

def build_complete_context(
    document_data
):
    """
    Build the complete document context.

    Used when the document is within the configured size limit.
    """

    return document_data[
        "full_text"
    ]


def build_pages_context(
    selected_pages
):
    """
    Build context from selected pages.
    """

    parts = []

    for (
        score,
        page_number,
        text
    ) in selected_pages:

        parts.append(
            f"\n===== PAGE {page_number} =====\n\n"
            f"{text}"
        )

    return "\n".join(
        parts
    )


# ======================================================================
# GROQ REQUEST
# ======================================================================

def call_groq(
    client,
    messages,
    temperature=0.2,
    max_completion_tokens=4096
):
    """
    Send a request to Groq Chat Completions.
    """

    try:

        response = client.chat.completions.create(
            model=GROQ_CHAT_MODEL,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            stream=False,
            include_reasoning=False
        )

        if not response.choices:

            raise RuntimeError(
                "Groq returned no response choices."
            )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:

            raise RuntimeError(
                "Groq returned an empty response."
            )

        return content.strip()

    except Exception as exc:

        print()
        print("=" * 70)
        print("                         GROQ API ERROR")
        print("=" * 70)
        print()
        print(str(exc))
        print()

        raise


# ======================================================================
# DOCUMENT SUMMARY
# ======================================================================

def summarize_document(
    client,
    document_data
):
    """
    Generate a comprehensive document summary.

    For normal-sized documents, the entire document is supplied.

    For very large documents, the document is summarized in chunks
    and the individual summaries are combined into a final summary.
    """

    print()
    print("=" * 70)
    print("                       PDF SUMMARY")
    print("=" * 70)
    print()

    if not document_data[
        "has_text"
    ]:

        return (
            "No usable text was found in the PDF. "
            "Please provide the text-extracted PDF."
        )

    full_text = document_data[
        "full_text"
    ]

    print(
        "Generating summary..."
    )

    print()

    # ==============================================================
    # NORMAL-SIZED DOCUMENT
    # ==============================================================

    if len(full_text) <= MAX_DOCUMENT_CHARS:

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert multilingual document "
                    "analysis assistant.\n\n"

                    "You will receive the complete text of a "
                    "PDF document.\n\n"

                    "Create an accurate, well-structured summary "
                    "using ONLY the information contained in the "
                    "document.\n\n"

                    "Do not invent facts.\n"
                    "Do not assume information that is not present.\n"
                    "Preserve important names, dates, numbers, "
                    "organizations, technical terms and "
                    "requirements.\n\n"

                    "The document may contain English, Hindi, "
                    "Gujarati or other languages. Understand "
                    "multilingual content correctly.\n\n"

                    "Use clear headings and bullet points."
                )
            },
            {
                "role": "user",
                "content": (
                    "Summarize the following PDF document.\n\n"

                    "Include:\n"
                    "1. Document purpose\n"
                    "2. Main topics\n"
                    "3. Important facts\n"
                    "4. Important names, numbers and dates\n"
                    "5. Key findings or conclusions\n"
                    "6. Important requirements or actions\n"
                    "7. A short overall summary\n\n"

                    "DOCUMENT:\n\n"
                    f"{full_text}"
                )
            }
        ]

        return call_groq(
            client,
            messages,
            temperature=0.2,
            max_completion_tokens=5000
        )

    # ==============================================================
    # LARGE DOCUMENT
    # ==============================================================

    print(
        "Large document detected."
    )

    print(
        "Processing the document in sections..."
    )

    print()

    chunks = []

    start = 0

    while start < len(full_text):

        end = min(
            start + CHUNK_SIZE,
            len(full_text)
        )

        chunks.append(
            full_text[
                start:end
            ]
        )

        start = end

    section_summaries = []

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        print(
            f"Summarizing section "
            f"{index}/{len(chunks)}..."
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert multilingual document "
                    "analyst.\n\n"

                    "Summarize ONLY the supplied section of "
                    "the document.\n\n"

                    "Preserve important facts, names, dates, "
                    "numbers, requirements and conclusions.\n\n"

                    "Do not invent information."
                )
            },
            {
                "role": "user",
                "content": (
                    f"DOCUMENT SECTION {index}\n\n"
                    f"{chunk}"
                )
            }
        ]

        section_summary = call_groq(
            client,
            messages,
            temperature=0.2,
            max_completion_tokens=3000
        )

        section_summaries.append(
            section_summary
        )

    combined_summaries = "\n\n".join(
        f"===== SECTION SUMMARY {index} =====\n"
        f"{summary}"
        for index, summary in enumerate(
            section_summaries,
            start=1
        )
    )

    print()
    print(
        "Creating final combined summary..."
    )

    final_messages = [
        {
            "role": "system",
            "content": (
                "You are an expert multilingual document "
                "analyst.\n\n"

                "Combine the supplied section summaries into "
                "one accurate final summary.\n\n"

                "Do not invent information.\n"
                "Do not add facts that are not supported by "
                "the section summaries.\n\n"

                "Use clear headings and concise bullet points."
            )
        },
        {
            "role": "user",
            "content": (
                "Create the final summary of the document.\n\n"

                "Include:\n"
                "1. Document purpose\n"
                "2. Main topics\n"
                "3. Important facts\n"
                "4. Important names, numbers and dates\n"
                "5. Key findings or conclusions\n"
                "6. Important requirements or actions\n"
                "7. Overall summary\n\n"

                f"{combined_summaries}"
            )
        }
    ]

    return call_groq(
        client,
        final_messages,
        temperature=0.2,
        max_completion_tokens=5000
    )


# ======================================================================
# QUESTION ANSWERING
# ======================================================================

def ask_question(
    client,
    document_data,
    question,
    conversation_history=None
):
    """
    Answer a question using the PDF as the primary source.
    """

    if not document_data[
        "has_text"
    ]:

        return (
            "No usable text was found in this PDF."
        )

    if conversation_history is None:

        conversation_history = []

    # ==============================================================
    # BUILD DOCUMENT CONTEXT
    # ==============================================================

    if document_data[
        "total_characters"
    ] <= MAX_DOCUMENT_CHARS:

        document_context = (
            build_complete_context(
                document_data
            )
        )

    else:

        selected_pages = (
            get_relevant_pages(
                document_data,
                question,
                max_pages=30
            )
        )

        document_context = (
            build_pages_context(
                selected_pages
            )
        )

    # ==============================================================
    # SYSTEM INSTRUCTION
    # ==============================================================

    system_message = {
        "role": "system",
        "content": (
            "You are a professional multilingual PDF "
            "document assistant.\n\n"

            "Answer the user's questions using the supplied "
            "document as the primary source.\n\n"

            "STRICT RULES:\n"
            "1. Do not fabricate information.\n"
            "2. Do not assume facts that are not in the document.\n"
            "3. If the answer is not available in the document, "
            "clearly say that it is not stated in the document.\n"
            "4. Preserve exact names, dates, numbers and "
            "important terminology.\n"
            "5. Understand English, Hindi, Gujarati and other "
            "languages appearing in the document.\n"
            "6. Answer in the language used by the user unless "
            "the user requests another language.\n"
            "7. Mention the relevant page number when useful.\n"
            "8. Be concise but sufficiently detailed.\n"
            "9. Use the conversation history when the user asks "
            "follow-up questions."
        )
    }

    messages = [
        system_message
    ]

    # ==============================================================
    # CONVERSATION HISTORY
    # ==============================================================

    if conversation_history:

        messages.extend(
            conversation_history[
                -MAX_HISTORY_MESSAGES:
            ]
        )

    # ==============================================================
    # CURRENT QUESTION
    # ==============================================================

    messages.append(
        {
            "role": "user",
            "content": (
                "DOCUMENT CONTENT:\n\n"
                f"{document_context}\n\n"

                "==================================================\n\n"

                "USER QUESTION:\n"
                f"{question}"
            )
        }
    )

    return call_groq(
        client,
        messages,
        temperature=0.2,
        max_completion_tokens=4000
    )


# ======================================================================
# INTERACTIVE CHATBOT
# ======================================================================

def interactive_chat(
    client,
    document_data
):
    """
    Start an interactive chatbot session.
    """

    print()
    print("=" * 70)
    print("                    PDF DOCUMENT CHAT")
    print("=" * 70)
    print()

    print(
        f"Document:   "
        f"{document_data['filename']}"
    )

    print(
        f"Pages:      "
        f"{document_data['total_pages']}"
    )

    print(
        f"Characters: "
        f"{document_data['total_characters']:,}"
    )

    print()

    print(
        "Document loaded successfully."
    )

    print()
    print(
        "You can now ask questions about the PDF."
    )

    print()

    print("Commands:")
    print(
        "  /summary  - generate document summary"
    )
    print(
        "  /pages    - show document page count"
    )
    print(
        "  /clear    - clear conversation history"
    )
    print(
        "  /exit     - exit chatbot"
    )

    print()

    print("-" * 70)

    conversation_history = []

    while True:

        try:

            question = input(
                "\nYou: "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print()
            print(
                "Exiting chatbot..."
            )

            break

        # ----------------------------------------------------------
        # Empty input
        # ----------------------------------------------------------

        if not question:

            continue

        # ----------------------------------------------------------
        # Exit
        # ----------------------------------------------------------

        if question.lower() == "/exit":

            print()
            print(
                "Goodbye."
            )

            break

        # ----------------------------------------------------------
        # Clear
        # ----------------------------------------------------------

        if question.lower() == "/clear":

            conversation_history = []

            print()
            print(
                "Conversation history cleared."
            )

            continue

        # ----------------------------------------------------------
        # Pages
        # ----------------------------------------------------------

        if question.lower() == "/pages":

            print()
            print(
                f"This document contains "
                f"{document_data['total_pages']} pages."
            )

            continue

        # ----------------------------------------------------------
        # Summary
        # ----------------------------------------------------------

        if question.lower() == "/summary":

            try:

                print()
                print(
                    "Generating summary..."
                )

                result = summarize_document(
                    client,
                    document_data
                )

                print()
                print("=" * 70)
                print("                         SUMMARY")
                print("=" * 70)
                print()
                print(result)
                print()
                print("=" * 70)

            except Exception as exc:

                print()
                print(
                    f"ERROR: {exc}"
                )

            continue

        # ----------------------------------------------------------
        # Normal question
        # ----------------------------------------------------------

        print()
        print(
            "Assistant: ",
            end="",
            flush=True
        )

        try:

            answer = ask_question(
                client,
                document_data,
                question,
                conversation_history
            )

            print(
                answer
            )

            # Save conversation.
            conversation_history.append(
                {
                    "role": "user",
                    "content": question
                }
            )

            conversation_history.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )

        except Exception as exc:

            print()
            print(
                f"ERROR: {exc}"
            )


# ======================================================================
# MAIN
# ======================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Standalone Groq-powered PDF "
            "summary and chatbot"
        )
    )

    parser.add_argument(
        "pdf",
        nargs="?",
        help="Path to the text-extracted PDF"
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate a summary of the PDF"
    )

    parser.add_argument(
        "--ask",
        type=str,
        help="Ask one question about the PDF"
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive PDF chatbot"
    )

    args = parser.parse_args()

    # ==================================================================
    # HELP
    # ==================================================================

    if not args.pdf:

        parser.print_help()

        print()
        print("=" * 70)
        print("EXAMPLES")
        print("=" * 70)
        print()

        print(
            "Summary:"
        )

        print(
            "  python document_chat.py "
            "Input_sample.pdf --summary"
        )

        print()

        print(
            "Single question:"
        )

        print(
            "  python document_chat.py "
            "Input_sample.pdf --ask "
            "\"What is this document about?\""
        )

        print()

        print(
            "Interactive chatbot:"
        )

        print(
            "  python document_chat.py "
            "Input_sample.pdf --interactive"
        )

        print()

        sys.exit(0)

    # ==================================================================
    # VALIDATE ENVIRONMENT
    # ==================================================================

    validate_environment()

    # ==================================================================
    # CREATE GROQ CLIENT
    # ==================================================================

    client = create_groq_client()

    # ==================================================================
    # HEADER
    # ==================================================================

    print()
    print("=" * 70)
    print("                 GROQ DOCUMENT CHATBOT")
    print("=" * 70)
    print()

    print(
        f"Model: {GROQ_CHAT_MODEL}"
    )

    print()

    # ==================================================================
    # LOAD PDF
    # ==================================================================

    try:

        document_data = extract_pdf_text(
            args.pdf
        )

    except Exception as exc:

        print()
        print("=" * 70)
        print("                         ERROR")
        print("=" * 70)
        print()

        print(
            str(exc)
        )

        print()

        sys.exit(1)

    # ==================================================================
    # NO TEXT
    # ==================================================================

    if not document_data[
        "has_text"
    ]:

        print(
            "The chatbot cannot continue because "
            "the supplied PDF does not contain usable "
            "selectable text."
        )

        print()

        print(
            "Please provide the PDF generated after "
            "your text-extraction/OCR stage."
        )

        print()

        sys.exit(1)

    # ==================================================================
    # DOCUMENT INFORMATION
    # ==================================================================

    print_document_information(
        document_data
    )

    # ==================================================================
    # SUMMARY MODE
    # ==================================================================

    if args.summary:

        try:

            result = summarize_document(
                client,
                document_data
            )

            print()
            print("=" * 70)
            print("                         RESULT")
            print("=" * 70)
            print()
            print(result)
            print()
            print("=" * 70)

        except Exception as exc:

            print()
            print(
                f"ERROR: {exc}"
            )

        return

    # ==================================================================
    # SINGLE QUESTION MODE
    # ==================================================================

    if args.ask:

        try:

            answer = ask_question(
                client,
                document_data,
                args.ask
            )

            print()
            print("=" * 70)
            print("                         ANSWER")
            print("=" * 70)
            print()
            print(answer)
            print()
            print("=" * 70)

        except Exception as exc:

            print()
            print(
                f"ERROR: {exc}"
            )

        return

    # ==================================================================
    # INTERACTIVE MODE
    # ==================================================================

    if args.interactive:

        interactive_chat(
            client,
            document_data
        )

        return

    # ==================================================================
    # DEFAULT BEHAVIOR
    # ==================================================================

    print()
    print("=" * 70)
    print("                    NO OPERATION SELECTED")
    print("=" * 70)
    print()

    print(
        "Choose one of the following:"
    )

    print()

    print(
        "1. Summary:"
    )

    print(
        "   python document_chat.py "
        "Input_sample.pdf --summary"
    )

    print()

    print(
        "2. Ask a question:"
    )

    print(
        "   python document_chat.py "
        "Input_sample.pdf --ask "
        "\"What is this document about?\""
    )

    print()

    print(
        "3. Interactive chatbot:"
    )

    print(
        "   python document_chat.py "
        "Input_sample.pdf --interactive"
    )

    print()


# ======================================================================
# ENTRY POINT
# ======================================================================

if __name__ == "__main__":

    main()