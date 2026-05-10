"""
Report Routes (Blueprint: /api/reports)
PDF/Excel report generation, scheduled reports
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import json

from flask import Blueprint, request, jsonify, g, send_file
from sqlalchemy import and_

from database import get_db_session
from models import (
    Store, Product, Sale, Forecast, InventoryLevel,
    ScheduledReport, ReportOutput, ReportFormat
)
from services.report_service import ReportService
from auth_service import require_role, UserRole, get_current_user, log_auth_action

logger = logging.getLogger(__name__)

report_bp = Blueprint('report', __name__)


# ============= GENERATE REPORT =============
@report_bp.route('/generate', methods=['POST'])
@require_role(UserRole.ADMIN, UserRole.BUSINESS_ANALYST, UserRole.EXECUTIVE)
def generate_report():
    """
    Generate a one-off report

    Request Body:
        {
            "report_type": "executive_summary",
            "format": "pdf",
            "store_id": "S001",  # optional
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "include_forecasts": true,
            "include_inventory": true
        }

    Response (200) with file or JSON with download URL
    """
    user = g.current_user
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "error": "Request body required",
                "code": "INVALID_INPUT"
            }), 400

        report_type = data.get('report_type', 'executive_summary')
        format_str = data.get('format', 'pdf')
        store_id = data.get('store_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        include_forecasts = data.get('include_forecasts', True)
        include_inventory = data.get('include_inventory', True)

        # Validate format
        try:
            report_format = ReportFormat(format_str.lower())
        except ValueError:
            report_format = ReportFormat.PDF

        # Resolve store
        store_id_int = None
        if store_id:
            with get_db_session() as db:
                store = db.query(Store).filter_by(store_code=store_id).first()
                if store:
                    store_id_int = store.id

        # Generate report
        service = ReportService()
        report_path = service.generate_report(
            report_type=report_type,
            format=report_format,
            store_id=store_id_int,
            start_date=start_date,
            end_date=end_date,
            include_forecasts=include_forecasts,
            include_inventory=include_inventory,
            user_id=user.id
        )

        # Audit
        log_auth_action(
            user_id=user.id,
            action="report_generated",
            resource_type="report",
            details={
                "type": report_type,
                "format": format_str,
                "store_id": store_id
            }
        )

        # Return download URL or file
        return jsonify({
            "status": "success",
            "data": {
                "report_id": report_path.split('/')[-1].split('.')[0],
                "download_url": f"/api/reports/download/{report_path.split('/')[-1]}",
                "format": format_str
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Report generation error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to generate report",
            "code": "REPORT_ERROR"
        }), 500


# ============= DOWNLOAD REPORT =============
@report_bp.route('/download/<filename>', methods=['GET'])
@require_role(UserRole.ADMIN, UserRole.BUSINESS_ANALYST, UserRole.EXECUTIVE)
def download_report(filename: str):
    """Download generated report file"""
    try:
        # In production, files stored in S3 or secure file server
        reports_dir = 'reports'
        return send_file(
            f"{reports_dir}/{filename}",
            as_attachment=True,
            download_name=filename
        )
    except FileNotFoundError:
        return jsonify({
            "status": "error",
            "error": "Report not found",
            "code": "NOT_FOUND"
        }), 404


# ============= SCHEDULE REPORT =============
@report_bp.route('/schedule', methods=['POST'])
@require_role(UserRole.ADMIN, UserRole.BUSINESS_ANALYST)
def schedule_report():
    """
    Schedule recurring report generation

    Request Body:
        {
            "name": "Monthly Executive Summary",
            "report_type": "executive_summary",
            "format": "pdf",
            "frequency": "monthly",
            "cron_expression": "0 0 1 * *",  # optional, derived from frequency
            "parameters": {"store_id": "S001"},
            "recipients": ["exec@example.com"]
        }
    """
    user = g.current_user
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "error": "Request body required",
                "code": "INVALID_INPUT"
            }), 400

        name = str(data.get('name', '')).strip()
        report_type = str(data.get('report_type', '')).strip()
        format_str = str(data.get('format', 'pdf')).strip()
        frequency = str(data.get('frequency', 'weekly')).strip()
        cron_expr = data.get('cron_expression')
        parameters = data.get('parameters', {})
        recipients = data.get('recipients', [])

        if not name or not report_type or not recipients:
            return jsonify({
                "status": "error",
                "error": "Name, report_type, and recipients are required",
                "code": "VALIDATION_ERROR"
            }), 400

        try:
            report_format = ReportFormat(format_str.lower())
        except ValueError:
            report_format = ReportFormat.PDF

        # Calculate next run based on frequency
        next_run = ReportService.calculate_next_run(frequency, cron_expr)

        with get_db_session() as db:
            scheduled = ScheduledReport(
                name=name,
                report_type=report_type,
                format=report_format,
                frequency=frequency,
                cron_expression=cron_expr,
                parameters=json.dumps(parameters) if parameters else None,
                recipients=json.dumps(recipients),
                created_by=user.id,
                next_run=next_run
            )
            db.add(scheduled)
            db.commit()

            # Audit
            log_auth_action(
                user_id=user.id,
                action="report_scheduled",
                resource_type="scheduled_report",
                resource_id=str(scheduled.id),
                details={"name": name, "frequency": frequency}
            )

            return jsonify({
                "status": "success",
                "data": {
                    "id": scheduled.id,
                    "name": name,
                    "next_run": next_run.isoformat() if next_run else None
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 201

    except Exception as e:
        logger.error(f"Schedule report error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to schedule report",
            "code": "SCHEDULE_ERROR"
        }), 500


# ============= LIST SCHEDULED REPORTS =============
@report_bp.route('/scheduled', methods=['GET'])
@require_role(UserRole.ADMIN, UserRole.BUSINESS_ANALYST)
def list_scheduled_reports():
    """List all scheduled reports"""
    try:
        with get_db_session() as db:
            reports = db.query(ScheduledReport)\
                .filter_by(is_active=True)\
                .order_by(ScheduledReport.next_run.asc()).all()

            result = []
            for r in reports:
                creator = db.query(Store).get(r.created_by)  # User model
                result.append({
                    "id": r.id,
                    "name": r.name,
                    "report_type": r.report_type,
                    "format": r.format.value,
                    "frequency": r.frequency,
                    "recipients": json.loads(r.recipients) if r.recipients else [],
                    "next_run": r.next_run.isoformat() if r.next_run else None,
                    "last_run": r.last_run.isoformat() if r.last_run else None,
                    "created_by": creator.email if creator else "Unknown"
                })

            return jsonify({
                "status": "success",
                "data": {
                    "scheduled_reports": result,
                    "count": len(result)
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"List scheduled reports error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to retrieve scheduled reports",
            "code": "RETRIEVAL_ERROR"
        }), 500
