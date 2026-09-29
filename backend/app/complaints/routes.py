import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from .. import db
from ..models import Complaint, ComplaintStatusHistory, User

complaints_bp = Blueprint("complaints", __name__, url_prefix="/api/complaints")


def generate_complaint_number():
    """Generates a human-readable complaint identifier, e.g. RS-2026-A1B2C3D4"""
    year = datetime.utcnow().year
    suffix = uuid.uuid4().hex[:8].upper()
    return f"RS-{year}-{suffix}"


@complaints_bp.post("")
@jwt_required()
def create_complaint():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404

    data = request.get_json() or {}

    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    address = data.get("address", "").strip() or None
    category = data.get("category", "").strip() or None

    if not title or not description:
        return jsonify({
            "status": "error",
            "message": "Title and description are required"
        }), 400

    complaint_number = generate_complaint_number()

    complaint = Complaint(
        complaint_number=complaint_number,
        citizen_id=user.id,
        title=title,
        description=description,
        latitude=latitude,
        longitude=longitude,
        address=address,
        category=category,
        priority="medium",
        status="submitted"
    )

    db.session.add(complaint)
    db.session.flush()  # Flush so complaint.id is generated for history tracking

    # Audit history entry
    status_entry = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status="submitted",
        remarks="Complaint filed by citizen"
    )
    db.session.add(status_entry)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Complaint submitted successfully",
        "complaint": {
            "id": complaint.id,
            "complaint_number": complaint.complaint_number,
            "title": complaint.title,
            "description": complaint.description,
            "status": complaint.status,
            "priority": complaint.priority,
            "category": complaint.category,
            "latitude": float(complaint.latitude) if complaint.latitude is not None else None,
            "longitude": float(complaint.longitude) if complaint.longitude is not None else None,
            "address": complaint.address,
            "created_at": complaint.created_at.isoformat()
        }
    }), 201


@complaints_bp.get("/my")
@jwt_required()
def get_my_complaints():
    user_id = get_jwt_identity()

    complaints = Complaint.query.filter_by(citizen_id=user_id).order_by(Complaint.created_at.desc()).all()

    result = []
    for c in complaints:
        result.append({
            "id": c.id,
            "complaint_number": c.complaint_number,
            "title": c.title,
            "description": c.description,
            "status": c.status,
            "priority": c.priority,
            "category": c.category,
            "address": c.address,
            "created_at": c.created_at.isoformat()
        })

    return jsonify({
        "status": "success",
        "total": len(result),
        "complaints": result
    }), 200

from flask_jwt_extended import get_jwt


@complaints_bp.get("/<int:complaint_id>")
@jwt_required()
def get_complaint_details(complaint_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user_role = claims.get("role")

    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({
            "status": "error",
            "message": "Complaint not found"
        }), 404

    # Authorization: citizens can only view their own complaints; officers/admins can view any
    if user_role == "citizen" and complaint.citizen_id != user_id:
        return jsonify({
            "status": "error",
            "message": "Access denied"
        }), 403

    return jsonify({
        "status": "success",
        "complaint": {
            "id": complaint.id,
            "complaint_number": complaint.complaint_number,
            "title": complaint.title,
            "description": complaint.description,
            "status": complaint.status,
            "priority": complaint.priority,
            "category": complaint.category,
            "latitude": float(complaint.latitude) if complaint.latitude is not None else None,
            "longitude": float(complaint.longitude) if complaint.longitude is not None else None,
            "address": complaint.address,
            "department_id": complaint.department_id,
            "citizen_id": complaint.citizen_id,
            "is_duplicate": complaint.is_duplicate,
            "is_flagged": complaint.is_flagged,
            "created_at": complaint.created_at.isoformat(),
            "updated_at": complaint.updated_at.isoformat()
        }
    }), 200


@complaints_bp.get("/<int:complaint_id>/timeline")
@jwt_required()
def get_complaint_timeline(complaint_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user_role = claims.get("role")

    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({
            "status": "error",
            "message": "Complaint not found"
        }), 404

    if user_role == "citizen" and complaint.citizen_id != user_id:
        return jsonify({
            "status": "error",
            "message": "Access denied"
        }), 403

    history_records = ComplaintStatusHistory.query.filter_by(
        complaint_id=complaint.id
    ).order_by(ComplaintStatusHistory.created_at.asc()).all()

    timeline = []
    for h in history_records:
        timeline.append({
            "id": h.id,
            "status": h.status,
            "remarks": h.remarks,
            "updated_by": h.updated_by,
            "created_at": h.created_at.isoformat()
        })

    return jsonify({
        "status": "success",
        "complaint_number": complaint.complaint_number,
        "timeline": timeline
    }), 200

