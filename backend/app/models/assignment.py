from datetime import datetime

from backend.app import db


class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    complaint_id = db.Column(
        db.Integer,
        db.ForeignKey("complaints.id"),
        nullable=False
    )

    officer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    assigned_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    def __repr__(self):
        return f"<Assignment complaint={self.complaint_id} officer={self.officer_id}>"