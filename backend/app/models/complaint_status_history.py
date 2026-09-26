from datetime import datetime

from backend.app import db


class ComplaintStatusHistory(db.Model):
    __tablename__ = "complaint_status_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    complaint_id = db.Column(
        db.Integer,
        db.ForeignKey("complaints.id"),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    updated_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f"<ComplaintStatusHistory {self.complaint_id} - {self.status}>"
    