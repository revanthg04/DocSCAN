from flask import (
    Blueprint, render_template, request, flash, url_for, 
    redirect, send_file, abort, jsonify, session
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timezone
from sqlalchemy.sql import func
import io
import Levenshtein

from . import db
from .models import Document1, Document2, User, CreditRequest, ComparisonResult


views = Blueprint('views', __name__)


#--------


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    # Reset credits at midnight automatically
    current_user.reset_credits()

    if request.method == "POST":
        if current_user.credits > 0:
            file1 = request.files.get("file1")  # User-uploaded document

            if file1 and file1.filename != "":
                filename1 = secure_filename(file1.filename)
                new_doc1 = Document1(
                    user_id=current_user.id,
                    filename=filename1,
                    file_data=file1.read(),
                    mime_type=file1.content_type
                )
                db.session.add(new_doc1)
                db.session.commit()
                flash("File uploaded successfully!", category="success")
            else:
                flash("Please upload a valid file.", category="danger")

    # Fetch logged-in user's documents
    documents1 = Document1.query.filter_by(user_id=current_user.id).all()
    documents2 = Document2.query.all()  # Admin-uploaded documents

    return render_template("home.html", user=current_user, documents1=documents1, documents2=documents2)

@views.route("/download/<int:doc_id>/<int:doc_type>")
@login_required
def download(doc_id, doc_type):
    if doc_type == 1:
        document = Document1.query.get_or_404(doc_id)
    else:
        document = Document2.query.get_or_404(doc_id)
    

    return send_file(
        io.BytesIO(document.file_data),
        mimetype=document.mime_type,
        as_attachment=True,
        download_name=document.filename
    )


@views.route("/delete/<int:doc_id>/<int:doc_type>", methods=["POST"])
@login_required
def delete_document(doc_id, doc_type):
    if doc_type == 1:
        document = Document1.query.filter_by(id=doc_id, user_id=current_user.id).first()
    else:
        document = Document2.query.filter_by(id=doc_id, user_id=current_user.id).first()

    if document:
        db.session.delete(document)
        db.session.commit()
        flash("Document deleted successfully!", category="success")
    else:
        flash("Document not found or unauthorized!", category="danger")

    return redirect(url_for("views.home"))

@views.route("/request-credits", methods=["POST"])
@login_required
def request_credits():
    existing_request = CreditRequest.query.filter_by(user_id=current_user.id, status="pending").first()
    if existing_request:
        flash("You already have a pending request.", category="warning")
    else:
        new_request = CreditRequest(user_id=current_user.id)
        db.session.add(new_request)
        db.session.commit()
        flash("Credit request submitted successfully!", category="success")
    
    return redirect(url_for("views.home"))



@views.route("/compare", methods=["POST"])
@login_required
def compare_documents():
    documents1 = Document1.query.filter_by(user_id=current_user.id).all()
    documents2 = Document2.query.all()

    if not documents1 or not documents2:
        flash("Both sets of documents must be uploaded first!", category="danger")
        return redirect(url_for("views.home"))

    if current_user.credits < len(documents1):
        flash("Not enough credits for comparison!", category="danger")
        return redirect(url_for("views.home"))

    best_comparisons = []

    for doc1 in documents1:
        highest_similarity = 0
        best_match = None

        for doc2 in documents2:
            text1 = doc1.file_data.decode("utf-8", errors="ignore")
            text2 = doc2.file_data.decode("utf-8", errors="ignore")

            distance = Levenshtein.distance(text1, text2)
            max_length = max(len(text1), len(text2))
            similarity = 1 - (distance / max_length) if max_length > 0 else 0
            similarity_percentage = round(similarity * 100, 2)

            if similarity_percentage > highest_similarity:
                highest_similarity = similarity_percentage
                best_match = {
                    "doc1_name": doc1.filename,
                    "doc2_id": doc2.id,  # Store doc2 ID
                    "doc2_name": doc2.filename,
                    "distance": distance,
                    "similarity": similarity_percentage
                }

        if best_match:
            # Store highest similarity comparison in the database
            comparison = ComparisonResult(
                user_id=current_user.id,
                doc1_name=best_match["doc1_name"],
                doc2_id=best_match["doc2_id"],  # Save doc2 ID
                doc2_name=best_match["doc2_name"],
                similarity_score=best_match["similarity"],
                compared_at=func.current_timestamp()
            )
            db.session.add(comparison)
            best_comparisons.append(best_match)

    current_user.credits -= len(documents1)
    db.session.commit()

    return render_template("home.html", results=best_comparisons, documents1=documents1, documents2=documents2, user=current_user)


@views.route("/history")
@login_required
def history():
    comparisons = ComparisonResult.query.filter_by(user_id=current_user.id).order_by(ComparisonResult.compared_at.desc()).all()
    return render_template("history.html", comparisons=comparisons, user=current_user)


@views.route("/clear_results")
@login_required
def clear_results():
    session.pop("results", None)
    return redirect(url_for("views.home"))

# 
# 
# 
# 


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function


@views.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    # Print admin user IDs
    users = User.query.all()
    credit_requests = {req.user_id: req for req in CreditRequest.query.filter_by(status="pending").all()}
    documents2 = Document2.query.all()  # Admin-uploaded documents 
    return render_template("admin.html", users=users, credit_requests=credit_requests, user=current_user,documents2=documents2)

@views.route("/admin/credit-requests")
@login_required
@admin_required
def manage_credit_requests():
    if not current_user.is_admin:
        abort(403)  # Forbidden for non-admins

    requests = CreditRequest.query.filter_by(status="pending").all()
    return render_template("admin.html", requests=requests)


@views.route("/admin/approve-request/<int:request_id>")
@login_required
@admin_required
def approve_credit_request(request_id):
    if not current_user.is_admin:
        abort(403)

    credit_request = CreditRequest.query.get_or_404(request_id)
    credit_request.status = "approved"
    user = User.query.get(credit_request.user_id)
    user.credits += 5  # Grant 5 credits (Modify as needed)

    db.session.commit()
    flash("Credit request approved!", category="success")
    return redirect(url_for("views.admin_dashboard"))


@views.route("/admin/deny-request/<int:request_id>")
@login_required
@admin_required
def deny_credit_request(request_id):
    if not current_user.is_admin:
        abort(403)

    credit_request = CreditRequest.query.get_or_404(request_id)
    credit_request.status = "denied"
    
    db.session.commit()
    flash("Credit request denied.", category="danger")
    return redirect(url_for("views.admin_dashboard"))


@views.route("/admin/upload", methods=["POST"])
@login_required
@admin_required
def upload_admin_document():
    file2 = request.files.get("file2")  # Admin-uploaded document

    if file2 and file2.filename != "":
        filename2 = secure_filename(file2.filename)
        new_doc2 = Document2(
            user_id=current_user.id,
            filename=filename2,
            file_data=file2.read(),
            mime_type=file2.content_type
        )
        db.session.add(new_doc2)
        db.session.commit()
        flash("Admin document uploaded successfully!", category="success")
    else:
        flash("Please upload a valid file.", category="error")
    documents2 = Document2.query.all() 
    return redirect(url_for("views.admin_dashboard"))

@views.route("/admin/delete/<int:doc_id>/<int:doc_type>", methods=["POST"])
@login_required
@admin_required  # Ensure only admins can access this route
def admin_delete_document(doc_id, doc_type):
    if doc_type == 1:
        document = Document1.query.filter_by(id=doc_id).first()  # Can delete any user document
    else:
        document = Document2.query.filter_by(id=doc_id).first()  # Can delete any admin document

    if document:
        db.session.delete(document)
        db.session.commit()
        flash("Document deleted successfully!", category="success")
    else:
        flash("Document not found!", category="danger")

    return redirect(url_for("views.admin_dashboard"))
