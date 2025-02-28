from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime, timezone

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    credits = db.Column(db.Integer, default=20, nullable=False)
    last_reset = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    documents1 = db.relationship('Document1', backref='user', lazy=True)
    documents2 = db.relationship('Document2', backref='user', lazy=True)

    def reset_credits(self):
        if self.last_reset.date() < datetime.now(timezone.utc).date():
            self.credits = 20
            self.last_reset = datetime.now(timezone.utc)
            db.session.commit()
    
class Document1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<Document {self.filename}>"

class Document2(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<Document {self.filename}>"
    
class ComparisonResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    doc1_name = db.Column(db.String(255), nullable=False)
    doc2_id = db.Column(db.Integer, db.ForeignKey("document2.id"), nullable=False)
    doc2_name = db.Column(db.String(255), nullable=False)
    similarity_score = db.Column(db.Float, nullable=False)
    compared_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship("User", backref="comparisons", lazy=True)
    doc2 = db.relationship("Document2", backref="comparisons", lazy=True)

    def __repr__(self):
        return f"<ComparisonResult {self.doc1_name} vs {self.doc2_name} (ID: {self.doc2_id}): {self.similarity_score:.2f}>"

class CreditRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default="pending")
    requested_at = db.Column(db.DateTime, default=db.func.current_timestamp())
