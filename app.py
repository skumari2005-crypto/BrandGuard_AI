
import os
import json
import sqlite3

from datetime import datetime
from flask import Flask, render_template, request, jsonify

from rules_engine import analyze_brand_content
from gemini_service import analyze_with_gemini


app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "brandguard.db")
)


def get_db_connection():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content_type TEXT,
            content TEXT,
            issues TEXT,
            suggestions TEXT,
            analysis TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT,
            gemini_success INTEGER DEFAULT 0,
            gemini_message TEXT
        )
    """)

    existing_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(reviews)"
        ).fetchall()
    }

    required_columns = {
        "analysis": "TEXT",
        "gemini_success": "INTEGER DEFAULT 0",
        "gemini_message": "TEXT"
    }

    for column, column_type in required_columns.items():
        if column not in existing_columns:
            connection.execute(
                f"ALTER TABLE reviews ADD COLUMN {column} {column_type}"
            )

    connection.commit()
    connection.close()


def safe_json(value, default):
    try:
        return json.loads(value) if value else default
    except (ValueError, TypeError):
        return default


def serialize_review(row):
    return {
        "id": row["id"],
        "title": row["title"] or "",
        "content_type": row["content_type"] or "General",
        "content": row["content"] or "",
        "issues": safe_json(row["issues"], []),
        "suggestions": safe_json(row["suggestions"], []),
        "analysis": row["analysis"] or "",
        "status": row["status"] or "Pending",
        "created_at": row["created_at"] or "",
        "gemini_success": bool(row["gemini_success"]),
        "gemini_message": row["gemini_message"] or ""
    }


def json_error(message, status_code=400):
    return jsonify({
        "success": False,
        "message": message
    }), status_code


def validate_content(data):

    if not isinstance(data, dict):
        return None, json_error("Invalid request data.")

    title = str(data.get("title", "")).strip()
    content = str(data.get("content", "")).strip()

    content_type = str(
        data.get("content_type", "General")
    ).strip() or "General"

    if not title:
        return None, json_error(
            "Please enter a content title."
        )

    if not content:
        return None, json_error(
            "Please enter content to analyze."
        )

    guidelines = data.get("guidelines", {})

    if not isinstance(guidelines, dict):
        guidelines = {}

    return {
        "title": title,
        "content": content,
        "content_type": content_type,
        "guidelines": guidelines
    }, None


def perform_analysis(data):

    rules_issues, rules_suggestions = analyze_brand_content(
        data["content"],
        data["guidelines"]
    )

    gemini_result = analyze_with_gemini(
        data["content"],
        data["title"],
        data["content_type"],
        data["guidelines"]
    )

    ai_issues = gemini_result.get("issues", [])
    ai_suggestions = gemini_result.get("suggestions", [])

    issues = rules_issues + ai_issues
    suggestions = rules_suggestions + ai_suggestions

    return {
        "issues": issues,
        "suggestions": suggestions,
        "analysis": gemini_result.get("analysis", ""),
        "gemini_success": gemini_result.get("success", False),
        "gemini_message": gemini_result.get("message", "")
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    try:
        data, error = validate_content(
            request.get_json(silent=True) or {}
        )

        if error:
            return error

        result = perform_analysis(data)

        connection = get_db_connection()

        cursor = connection.execute("""
            INSERT INTO reviews (
                title, content_type, content,
                issues, suggestions, analysis,
                status, created_at,
                gemini_success, gemini_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["title"],
            data["content_type"],
            data["content"],
            json.dumps(result["issues"]),
            json.dumps(result["suggestions"]),
            result["analysis"],
            "Pending",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            int(result["gemini_success"]),
            result["gemini_message"]
        ))

        review_id = cursor.lastrowid

        connection.commit()

        row = connection.execute(
            "SELECT * FROM reviews WHERE id = ?",
            (review_id,)
        ).fetchone()

        connection.close()

        return jsonify({
            "success": True,
            "message": "Content analyzed successfully.",
            "review": serialize_review(row)
        })

    except Exception as error:

        app.logger.exception("Analyze route failed")

        return json_error(
            "Analysis failed: " + str(error),
            500
        )


@app.route("/review/<int:review_id>", methods=["PUT"])
def edit_review(review_id):

    try:
        data, error = validate_content(
            request.get_json(silent=True) or {}
        )

        if error:
            return error

        connection = get_db_connection()

        existing = connection.execute(
            "SELECT id FROM reviews WHERE id = ?",
            (review_id,)
        ).fetchone()

        if not existing:
            connection.close()
            return json_error("Review not found.", 404)

        result = perform_analysis(data)

        connection.execute("""
            UPDATE reviews
            SET title = ?,
                content_type = ?,
                content = ?,
                issues = ?,
                suggestions = ?,
                analysis = ?,
                status = ?,
                created_at = ?,
                gemini_success = ?,
                gemini_message = ?
            WHERE id = ?
        """, (
            data["title"],
            data["content_type"],
            data["content"],
            json.dumps(result["issues"]),
            json.dumps(result["suggestions"]),
            result["analysis"],
            "Pending",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            int(result["gemini_success"]),
            result["gemini_message"],
            review_id
        ))

        connection.commit()

        row = connection.execute(
            "SELECT * FROM reviews WHERE id = ?",
            (review_id,)
        ).fetchone()

        connection.close()

        return jsonify({
            "success": True,
            "message": "Review updated and re-analyzed successfully.",
            "review": serialize_review(row)
        })

    except Exception as error:

        app.logger.exception("Edit review failed")

        return json_error(
            "Review update failed: " + str(error),
            500
        )


@app.route("/review/<int:review_id>", methods=["DELETE"])
def delete_review(review_id):

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            "DELETE FROM reviews WHERE id = ?",
            (review_id,)
        )

        connection.commit()

        if cursor.rowcount == 0:
            return json_error("Review not found.", 404)

        return jsonify({
            "success": True,
            "message": "Review deleted successfully."
        })

    except Exception as error:

        app.logger.exception("Delete review failed")

        return json_error(
            "Review deletion failed: " + str(error),
            500
        )

    finally:
        connection.close()


@app.route("/approve/<int:review_id>", methods=["POST"])
def approve_review(review_id):

    connection = get_db_connection()

    try:
        cursor = connection.execute("""
            UPDATE reviews
            SET status = 'Approved'
            WHERE id = ? AND status = 'Pending'
        """, (review_id,))

        connection.commit()

        if cursor.rowcount == 0:
            return json_error(
                "Review not found or already approved.",
                404
            )

        return jsonify({
            "success": True,
            "message": "Content approved successfully."
        })

    except Exception as error:

        app.logger.exception("Approve review failed")

        return json_error(
            "Approval failed: " + str(error),
            500
        )

    finally:
        connection.close()


@app.route("/reviews", methods=["GET"])
def get_reviews():

    connection = get_db_connection()

    try:
        rows = connection.execute(
            "SELECT * FROM reviews ORDER BY id DESC"
        ).fetchall()

        return jsonify([
            serialize_review(row)
            for row in rows
        ])

    except Exception as error:

        app.logger.exception("Get reviews failed")

        return json_error(
            "Could not load reviews: " + str(error),
            500
        )

    finally:
        connection.close()


@app.errorhandler(404)
def handle_not_found(error):
    return json_error("Requested API route was not found.", 404)


@app.errorhandler(500)
def handle_server_error(error):
    app.logger.exception("Internal server error")
    return json_error("Internal server error.", 500)


initialize_database()


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
