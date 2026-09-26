from datetime import datetime

from backend.app import db


class Complaint(db.Model):
    __tablename__ = "complaints"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    complaint_number = db.Column(
        db.String(30),
        unique=True,
        nullable=False
    )

    citizen_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=True
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=True
    )

    priority = db.Column(
        db.String(20),
        nullable=False,
        default="medium"
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="submitted"
    )

    latitude = db.Column(
        db.Numeric(10, 7),
        nullable=True
    )

    longitude = db.Column(
        db.Numeric(10, 7),
        nullable=True
    )

    address = db.Column(
        db.String(255),
        nullable=True
    )

    is_duplicate = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    is_flagged = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f"<Complaint {self.complaint_number}>"