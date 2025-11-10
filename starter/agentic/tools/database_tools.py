"""
Database tools for UDA-Hub agent system.
These tools provide abstraction over CultPass database operations.
"""

import os
from typing import Dict, List, Optional, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from data.models import cultpass


# Database path - using absolute path from project root
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "external",
    "cultpass.db",
)


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_user_info(user_id: str) -> Dict[str, Any]:
    """
    Lookup user information by user ID.

    Args:
        user_id: The user's unique identifier

    Returns:
        Dictionary containing user information or error message
    """
    try:
        with get_db_session() as session:
            user = session.query(cultpass.User).filter_by(user_id=user_id).first()

            if not user:
                return {
                    "success": False,
                    "error": f"User with ID {user_id} not found",
                    "user_id": user_id,
                }

            return {
                "success": True,
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "is_blocked": user.is_blocked,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Database error: {str(e)}",
            "user_id": user_id,
        }


def get_subscription_status(user_id: str) -> Dict[str, Any]:
    """
    Get subscription information for a user.

    Args:
        user_id: The user's unique identifier

    Returns:
        Dictionary containing subscription details or error message
    """
    try:
        with get_db_session() as session:
            user = session.query(cultpass.User).filter_by(user_id=user_id).first()

            if not user:
                return {"success": False, "error": f"User with ID {user_id} not found"}

            subscription = user.subscription

            if not subscription:
                return {
                    "success": False,
                    "error": f"No subscription found for user {user_id}",
                }

            return {
                "success": True,
                "subscription_id": subscription.subscription_id,
                "user_id": subscription.user_id,
                "status": subscription.status,
                "tier": subscription.tier,
                "monthly_quota": subscription.monthly_quota,
                "started_at": (
                    subscription.started_at.isoformat()
                    if subscription.started_at
                    else None
                ),
                "ended_at": (
                    subscription.ended_at.isoformat() if subscription.ended_at else None
                ),
            }
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}


def get_reservations(user_id: str, status: Optional[str] = None) -> Dict[str, Any]:
    """
    Get reservations for a user, optionally filtered by status.

    Args:
        user_id: The user's unique identifier
        status: Optional status filter (e.g., 'reserved', 'cancelled', 'completed')

    Returns:
        Dictionary containing list of reservations or error message
    """
    try:
        with get_db_session() as session:
            user = session.query(cultpass.User).filter_by(user_id=user_id).first()

            if not user:
                return {"success": False, "error": f"User with ID {user_id} not found"}

            query = session.query(cultpass.Reservation).filter_by(user_id=user_id)

            if status:
                query = query.filter_by(status=status)

            reservations = query.all()

            reservation_list = []
            for res in reservations:
                experience = res.experience
                reservation_list.append(
                    {
                        "reservation_id": res.reservation_id,
                        "status": res.status,
                        "created_at": (
                            res.created_at.isoformat() if res.created_at else None
                        ),
                        "experience": (
                            {
                                "experience_id": experience.experience_id,
                                "title": experience.title,
                                "description": experience.description,
                                "location": experience.location,
                                "when": (
                                    experience.when.isoformat()
                                    if experience.when
                                    else None
                                ),
                                "is_premium": experience.is_premium,
                            }
                            if experience
                            else None
                        ),
                    }
                )

            return {
                "success": True,
                "user_id": user_id,
                "count": len(reservation_list),
                "reservations": reservation_list,
            }
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}


def cancel_reservation(user_id: str, reservation_id: str) -> Dict[str, Any]:
    """
    Cancel a reservation for a user.

    Args:
        user_id: The user's unique identifier
        reservation_id: The reservation ID to cancel

    Returns:
        Dictionary containing cancellation result
    """
    try:
        with get_db_session() as session:
            reservation = (
                session.query(cultpass.Reservation)
                .filter_by(reservation_id=reservation_id, user_id=user_id)
                .first()
            )

            if not reservation:
                return {
                    "success": False,
                    "error": f"Reservation {reservation_id} not found for user {user_id}",
                }

            if reservation.status == "cancelled":
                return {
                    "success": False,
                    "error": f"Reservation {reservation_id} is already cancelled",
                }

            # Update reservation status
            reservation.status = "cancelled"
            session.commit()

            return {
                "success": True,
                "message": f"Reservation {reservation_id} has been cancelled successfully",
                "reservation_id": reservation_id,
                "previous_status": "reserved",
                "new_status": "cancelled",
            }
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}


def check_account_status(user_id: str) -> Dict[str, Any]:
    """
    Check if a user account is blocked or active.

    Args:
        user_id: The user's unique identifier

    Returns:
        Dictionary containing account status
    """
    try:
        with get_db_session() as session:
            user = session.query(cultpass.User).filter_by(user_id=user_id).first()

            if not user:
                return {"success": False, "error": f"User with ID {user_id} not found"}

            return {
                "success": True,
                "user_id": user.user_id,
                "is_blocked": user.is_blocked,
                "status": "blocked" if user.is_blocked else "active",
                "email": user.email,
            }
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}


def request_refund(user_id: str, reservation_id: str, reason: str) -> Dict[str, Any]:
    """
    Request a refund for a reservation (requires approval).

    Args:
        user_id: The user's unique identifier
        reservation_id: The reservation ID for refund
        reason: Reason for refund request

    Returns:
        Dictionary containing refund request result
    """
    try:
        with get_db_session() as session:
            reservation = (
                session.query(cultpass.Reservation)
                .filter_by(reservation_id=reservation_id, user_id=user_id)
                .first()
            )

            if not reservation:
                return {
                    "success": False,
                    "error": f"Reservation {reservation_id} not found for user {user_id}",
                }

            experience = reservation.experience

            # Check if it's a premium event (only premium events may be refundable)
            if not experience.is_premium:
                return {
                    "success": False,
                    "error": "Refunds are only available for premium events",
                }

            # In a real system, this would create a refund request ticket
            # For now, we'll return a pending status
            return {
                "success": True,
                "message": "Refund request submitted successfully. Requires approval from support lead.",
                "reservation_id": reservation_id,
                "user_id": user_id,
                "reason": reason,
                "status": "pending_approval",
                "note": "Refunds are processed within 5-7 business days after approval",
            }
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}


# Tool descriptions for LLM
TOOL_DESCRIPTIONS = {
    "get_user_info": {
        "name": "get_user_info",
        "description": "Lookup user information by user ID. Returns user details including name, email, and account status.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's unique identifier",
                }
            },
            "required": ["user_id"],
        },
    },
    "get_subscription_status": {
        "name": "get_subscription_status",
        "description": "Get subscription information for a user including tier, status, and quota.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's unique identifier",
                }
            },
            "required": ["user_id"],
        },
    },
    "get_reservations": {
        "name": "get_reservations",
        "description": "Get all reservations for a user, optionally filtered by status.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's unique identifier",
                },
                "status": {
                    "type": "string",
                    "description": "Optional status filter (reserved, cancelled, completed)",
                    "enum": ["reserved", "cancelled", "completed"],
                },
            },
            "required": ["user_id"],
        },
    },
    "cancel_reservation": {
        "name": "cancel_reservation",
        "description": "Cancel a specific reservation for a user.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's unique identifier",
                },
                "reservation_id": {
                    "type": "string",
                    "description": "The reservation ID to cancel",
                },
            },
            "required": ["user_id", "reservation_id"],
        },
    },
    "check_account_status": {
        "name": "check_account_status",
        "description": "Check if a user account is blocked or active.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's unique identifier",
                }
            },
            "required": ["user_id"],
        },
    },
    "request_refund": {
        "name": "request_refund",
        "description": "Request a refund for a premium event reservation. Requires approval from support lead.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's unique identifier",
                },
                "reservation_id": {
                    "type": "string",
                    "description": "The reservation ID for refund",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for refund request",
                },
            },
            "required": ["user_id", "reservation_id", "reason"],
        },
    },
}


# Export all tools as a dictionary for easy access
AVAILABLE_TOOLS = {
    "get_user_info": get_user_info,
    "get_subscription_status": get_subscription_status,
    "get_reservations": get_reservations,
    "cancel_reservation": cancel_reservation,
    "check_account_status": check_account_status,
    "request_refund": request_refund,
}
