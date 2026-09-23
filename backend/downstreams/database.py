"""
Astra-OCR Database Layer
========================

MySQL connection and database helper functions.

This module does NOT run OCR.

Environment variables:

ASTRA_DB_HOST
ASTRA_DB_PORT
ASTRA_DB_USER
ASTRA_DB_PASSWORD
ASTRA_DB_NAME
"""

import os
from contextlib import contextmanager
from typing import Any, Dict, Iterable, Optional

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


load_dotenv()


# ==============================================================
# CONFIGURATION
# ==============================================================

DB_HOST = os.getenv("ASTRA_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("ASTRA_DB_PORT", "3306"))
DB_USER = os.getenv("ASTRA_DB_USER", "root")
DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "")
DB_NAME = os.getenv("ASTRA_DB_NAME", "astra_ocr")


# ==============================================================
# CONNECTION
# ==============================================================

def get_connection():
    """
    Create a new MySQL connection.

    A new connection is intentionally created for each
    operation because FastAPI requests and background tasks
    may execute independently.
    """

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=False,
    )


@contextmanager
def database_connection():
    """
    Context manager for MySQL connections.
    """

    connection = None

    try:
        connection = get_connection()
        yield connection

    except Exception:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass

        raise

    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


# ==============================================================
# BASIC HELPERS
# ==============================================================

def execute(
    query: str,
    params: Optional[Iterable[Any]] = None,
):
    """
    Execute one INSERT/UPDATE/DELETE statement.

    Returns the inserted ID where applicable.
    """

    with database_connection() as connection:

        cursor = connection.cursor()

        try:

            cursor.execute(
                query,
                params or (),
            )

            last_id = cursor.lastrowid

            connection.commit()

            return last_id

        finally:

            cursor.close()


def fetch_one(
    query: str,
    params: Optional[Iterable[Any]] = None,
):
    """
    Fetch one database row.
    """

    with database_connection() as connection:

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            cursor.execute(
                query,
                params or (),
            )

            return cursor.fetchone()

        finally:

            cursor.close()


def fetch_all(
    query: str,
    params: Optional[Iterable[Any]] = None,
):
    """
    Fetch all database rows.
    """

    with database_connection() as connection:

        cursor = connection.cursor(
            dictionary=True
        )

        try:

            cursor.execute(
                query,
                params or (),
            )

            return cursor.fetchall()

        finally:

            cursor.close()


# ==============================================================
# DATABASE HEALTH
# ==============================================================

def test_connection() -> Dict[str, Any]:
    """
    Test the configured MySQL connection.
    """

    try:

        with database_connection() as connection:

            cursor = connection.cursor()

            try:

                cursor.execute(
                    "SELECT 1"
                )

                cursor.fetchone()

            finally:

                cursor.close()

        return {
            "connected": True,
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME,
        }

    except Error as exc:

        return {
            "connected": False,
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME,
            "error": str(exc),
        }