import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from .. import db
from ..auth.decorators import role_required
from ..models import Assignment, Complaint, ComplaintStatusHistory, Department, User

from ..services.ml_service import GrievanceTriageEngine

from ..services.ml_service import GrievanceTriageEngine
from ..services.chatbot_service import ComplaintChatbot

from flask import send_from_directory, current_app
from ..models import ComplaintImage
from ..services.file_service import save_complaint_image

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

    # 1. AI Triage: Auto-predict category if absent or general
    if not category:
        category = GrievanceTriageEngine.predict_category(title, description)

    # 2. AI Triage: Priority & Urgency Scoring
    priority = GrievanceTriageEngine.evaluate_priority(title, description)

    # 3. Department Association
    department_id = None
    matched_dept = Department.query.filter(Department.name.ilike(f"%{category[:6]}%")).first()
    if matched_dept:
        department_id = matched_dept.id

    # 4. AI Triage: Duplicate Detection against active complaints
    active_complaints_query = Complaint.query.filter(
        Complaint.status.notin_(["resolved"])
    ).all()

    active_payload = [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "latitude": float(c.latitude) if c.latitude is not None else None,
            "longitude": float(c.longitude) if c.longitude is not None else None
        }
        for c in active_complaints_query
    ]

    lat_val = float(latitude) if latitude is not None else None
    lon_val = float(longitude) if longitude is not None else None

    is_dup, duplicate_of_id, sim_score, dist_m = GrievanceTriageEngine.detect_duplicate(
        new_title=title,
        new_desc=description,
        new_lat=lat_val,
        new_lon=lon_val,
        active_complaints=active_payload
    )

    complaint_number = generate_complaint_number()

    complaint = Complaint(
        complaint_number=complaint_number,
        citizen_id=user.id,
        title=title,
        description=description,
        latitude=lat_val,
        longitude=lon_val,
        address=address,
        category=category,
        priority=priority,
        status="submitted",
        department_id=department_id,
        is_duplicate=is_dup
    )

    db.session.add(complaint)
    db.session.flush()

    remarks = "Complaint filed by citizen"
    if is_dup and duplicate_of_id:
        remarks += f" [System Alert: Potential duplicate of #{duplicate_of_id} - Sim: {sim_score:.2f}]"

    status_entry = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status="submitted",
        remarks=remarks
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
            "is_duplicate": complaint.is_duplicate,
            "department_id": complaint.department_id,
            "latitude": float(complaint.latitude) if complaint.latitude is not None else None,
            "longitude": float(complaint.longitude) if complaint.longitude is not None else None,
            "address": complaint.address,
            "created_at": complaint.created_at.isoformat()
        }
    }), 201

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

    # Citizen can only view own; officer/admin can view any
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


@complaints_bp.get("/assigned")
@role_required("officer", "admin")
def get_assigned_complaints():
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user_role = claims.get("role")

    if user_role == "admin":
        complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    else:
        assigned_ids = db.select(Assignment.complaint_id).filter_by(officer_id=user_id)
        complaints = Complaint.query.filter(Complaint.id.in_(assigned_ids)).order_by(Complaint.created_at.desc()).all()
    result = []
    for c in complaints:
        result.append({
            "id": c.id,
            "complaint_number": c.complaint_number,
            "title": c.title,
            "status": c.status,
            "priority": c.priority,
            "category": c.category,
            "address": c.address,
            "latitude": float(c.latitude) if c.latitude is not None else None,
            "longitude": float(c.longitude) if c.longitude is not None else None,
            "created_at": c.created_at.isoformat()
        })

    return jsonify({
        "status": "success",
        "total": len(result),
        "complaints": result
    }), 200


@complaints_bp.patch("/<int:complaint_id>/status")
@role_required("officer", "admin")
def update_complaint_status(complaint_id):
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    new_status = data.get("status", "").strip().lower()
    remarks = data.get("remarks", "").strip() or f"Status changed to {new_status}"

    valid_statuses = {"submitted", "assigned", "under_review", "in_progress", "resolved"}
    if new_status not in valid_statuses:
        return jsonify({
            "status": "error",
            "message": f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}"
        }), 400

    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({
            "status": "error",
            "message": "Complaint not found"
        }), 404

    complaint.status = new_status
    complaint.updated_at = datetime.utcnow()

    # If resolving, close any active assignments
    if new_status == "resolved":
        active_assignment = Assignment.query.filter_by(
            complaint_id=complaint.id,
            completed_at=None
        ).first()
        if active_assignment:
            active_assignment.completed_at = datetime.utcnow()

    history_entry = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status=new_status,
        remarks=remarks,
        updated_by=user_id
    )
    db.session.add(history_entry)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Complaint status updated to {new_status}",
        "complaint": {
            "id": complaint.id,
            "complaint_number": complaint.complaint_number,
            "status": complaint.status,
            "updated_at": complaint.updated_at.isoformat()
        }
    }), 200


@complaints_bp.post("/<int:complaint_id>/assign")
@role_required("admin")
def assign_complaint(complaint_id):
    admin_id = int(get_jwt_identity())
    data = request.get_json() or {}

    officer_id = data.get("officer_id")
    department_id = data.get("department_id")
    notes = data.get("notes", "").strip() or None

    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({
            "status": "error",
            "message": "Complaint not found"
        }), 404

    if officer_id:
        officer = User.query.filter_by(id=officer_id, role="officer").first()
        if not officer:
            return jsonify({
                "status": "error",
                "message": "Target officer not found or user is not an officer"
            }), 404

    if department_id:
        dept = Department.query.get(department_id)
        if not dept:
            return jsonify({
                "status": "error",
                "message": "Target department not found"
            }), 404
        complaint.department_id = dept.id

    assignment = Assignment(
        complaint_id=complaint.id,
        officer_id=officer_id,
        remarks=notes
    )
    complaint.status = "assigned"
    complaint.updated_at = datetime.utcnow()

    history_entry = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status="assigned",
        remarks=f"Assigned to officer {officer_id}" if officer_id else "Assigned to department",
        updated_by=admin_id
    )

    db.session.add(assignment)
    db.session.add(history_entry)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Complaint assigned successfully",
        "assignment": {
            "complaint_id": complaint.id,
            "officer_id": officer_id,
            "department_id": complaint.department_id,
            "status": complaint.status
        }
    }), 200

@complaints_bp.post("/<int:complaint_id>/chat")
@jwt_required()
def chat_with_complaint_assistant(complaint_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user_role = claims.get("role")

    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({
            "status": "error",
            "message": "Complaint not found"
        }), 404

    # Security check: citizen can only query their own complaint
    if user_role == "citizen" and complaint.citizen_id != user_id:
        return jsonify({
            "status": "error",
            "message": "Access denied"
        }), 403

    data = request.get_json() or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "status": "error",
            "message": "Message is required"
        }), 400

    complaint_data = {
        "complaint_number": complaint.complaint_number,
        "title": complaint.title,
        "description": complaint.description,
        "category": complaint.category,
        "priority": complaint.priority,
        "status": complaint.status,
        "address": complaint.address,
        "is_duplicate": complaint.is_duplicate,
        "created_at": complaint.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }

    history_records = ComplaintStatusHistory.query.filter_by(
        complaint_id=complaint.id
    ).order_by(ComplaintStatusHistory.created_at.asc()).all()

    timeline_events = [
        {
            "status": h.status,
            "remarks": h.remarks,
            "created_at": h.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for h in history_records
    ]

    result = ComplaintChatbot.generate_response(
        complaint_data=complaint_data,
        timeline_events=timeline_events,
        user_message=user_message
    )

    if result.get("status") == "error":
        return jsonify(result), 500

    return jsonify({
        "status": "success",
        "complaint_number": complaint.complaint_number,
        "reply": result.get("reply")
    }), 200

@complaints_bp.post("/<int:complaint_id>/images")
@jwt_required()
def upload_complaint_image(complaint_id):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user_role = claims.get("role")

    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({"status": "error", "message": "Complaint not found"}), 404

    # Access control: citizen can only upload to their complaint; officers/admin can upload resolution evidence
    if user_role == "citizen" and complaint.citizen_id != user_id:
        return jsonify({"status": "error", "message": "Access denied"}), 403

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file part in request"}), 400

    file = request.files["file"]

    try:
        unique_filename, file_url = save_complaint_image(file, complaint_id=complaint.id)
    except ValueError as err:
        return jsonify({"status": "error", "message": str(err)}), 400

    complaint_image = ComplaintImage(
        complaint_id=complaint.id,
        file_name=unique_filename,
        file_path=file_url
    )
    db.session.add(complaint_image)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Image uploaded successfully",
        "image": {
            "id": complaint_image.id,
            "complaint_id": complaint_image.complaint_id,
            "file_name": complaint_image.file_name,
            "file_path": complaint_image.file_path,
            "uploaded_at": complaint_image.uploaded_at.isoformat() if complaint_image.uploaded_at else None
        }
    }), 201

    # Authorization: citizens can only upload to their own complaints; officers/admins can upload resolution proof
    if user_role == "citizen" and complaint.citizen_id != user_id:
        return jsonify({"status": "error", "message": "Access denied"}), 403

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file part in request"}), 400

    file = request.files["file"]

    try:
        image_url = save_complaint_image(file, complaint_id=complaint.id)
    except ValueError as err:
        return jsonify({"status": "error", "message": str(err)}), 400

    complaint_image = ComplaintImage(
        complaint_id=complaint.id,
        image_url=image_url
    )
    db.session.add(complaint_image)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Image uploaded successfully",
        "image": {
            "id": complaint_image.id,
            "complaint_id": complaint_image.complaint_id,
            "image_url": complaint_image.image_url,
            "created_at": complaint_image.created_at.isoformat()
        }
    }), 201


@complaints_bp.get("/uploads/<filename>")
def serve_uploaded_file(filename):
    upload_dir = get_upload_dir()
    return send_from_directory(upload_dir, filename)

from ..services.file_service import save_complaint_image, get_upload_dir

