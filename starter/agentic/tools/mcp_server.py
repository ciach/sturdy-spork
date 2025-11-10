"""
FastMCP Server for CultPass Support Operations.
Provides specialized tools for common support tasks using MCP protocol.
"""

import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from fastmcp import FastMCP
except ImportError:
    print("Warning: fastmcp not installed. MCP tools will not be available.")
    FastMCP = None

from agentic.tools.database_tools import (
    get_user_info,
    get_subscription_status,
    get_reservations,
    cancel_reservation,
    check_account_status,
    request_refund,
)


# Initialize FastMCP server
if FastMCP:
    mcp = FastMCP("CultPass Support Tools")
else:
    mcp = None


# ============================================================================
# USER MANAGEMENT TOOLS
# ============================================================================

if mcp:

    @mcp.tool()
    def lookup_user(user_id: str) -> Dict[str, Any]:
        """
        Look up comprehensive user information.

        Args:
            user_id: The user's unique identifier (6-character alphanumeric)

        Returns:
            Complete user profile including account status and subscription
        """
        # Get user info
        user_result = get_user_info(user_id)

        if not user_result.get("success"):
            return user_result

        # Get subscription info
        subscription_result = get_subscription_status(user_id)

        # Get reservations
        reservations_result = get_reservations(user_id)

        # Combine all information
        return {
            "success": True,
            "user_id": user_id,
            "user_info": user_result,
            "subscription": (
                subscription_result if subscription_result.get("success") else None
            ),
            "reservations_count": (
                reservations_result.get("count", 0)
                if reservations_result.get("success")
                else 0
            ),
            "account_status": "blocked" if user_result.get("is_blocked") else "active",
        }

    @mcp.tool()
    def check_user_eligibility(user_id: str, action: str) -> Dict[str, Any]:
        """
        Check if user is eligible for a specific action.

        Args:
            user_id: The user's unique identifier
            action: Action to check (e.g., 'reserve_event', 'request_refund', 'cancel_subscription')

        Returns:
            Eligibility status with reasons
        """
        # Get user and subscription info
        user_info = get_user_info(user_id)

        if not user_info.get("success"):
            return {"success": False, "eligible": False, "reason": "User not found"}

        # Check if account is blocked
        if user_info.get("is_blocked"):
            return {
                "success": True,
                "eligible": False,
                "reason": "Account is blocked",
                "action_required": "Contact support to unblock account",
            }

        subscription_info = get_subscription_status(user_id)

        if not subscription_info.get("success"):
            return {
                "success": True,
                "eligible": False,
                "reason": "No active subscription",
                "action_required": "Subscribe to CultPass to access features",
            }

        # Check subscription status
        if subscription_info.get("status") != "active":
            return {
                "success": True,
                "eligible": False,
                "reason": f"Subscription is {subscription_info.get('status')}",
                "action_required": "Reactivate subscription",
            }

        # Action-specific checks
        if action == "reserve_event":
            # Check if user has quota available
            return {
                "success": True,
                "eligible": True,
                "reason": "User can reserve events",
                "monthly_quota": subscription_info.get("monthly_quota"),
                "tier": subscription_info.get("tier"),
            }

        elif action == "request_refund":
            # Check if user has reservations
            reservations = get_reservations(user_id)
            if reservations.get("count", 0) == 0:
                return {
                    "success": True,
                    "eligible": False,
                    "reason": "No reservations found",
                }

            return {
                "success": True,
                "eligible": True,
                "reason": "User can request refunds for premium events",
            }

        else:
            return {
                "success": True,
                "eligible": True,
                "reason": f"User is eligible for {action}",
            }


# ============================================================================
# SUBSCRIPTION MANAGEMENT TOOLS
# ============================================================================

if mcp:

    @mcp.tool()
    def get_subscription_details(user_id: str) -> Dict[str, Any]:
        """
        Get detailed subscription information with usage statistics.

        Args:
            user_id: The user's unique identifier

        Returns:
            Detailed subscription info including tier, quota, and usage
        """
        subscription = get_subscription_status(user_id)

        if not subscription.get("success"):
            return subscription

        # Get reservations to calculate usage
        reservations = get_reservations(user_id, status="reserved")

        monthly_quota = subscription.get("monthly_quota", 0)
        used_quota = reservations.get("count", 0) if reservations.get("success") else 0
        remaining_quota = max(monthly_quota - used_quota, 0)

        return {
            "success": True,
            "user_id": user_id,
            "tier": subscription.get("tier"),
            "status": subscription.get("status"),
            "monthly_quota": monthly_quota,
            "used_quota": used_quota,
            "remaining_quota": remaining_quota,
            "usage_percentage": (
                (used_quota / monthly_quota * 100) if monthly_quota > 0 else 0
            ),
            "started_at": subscription.get("started_at"),
            "ended_at": subscription.get("ended_at"),
        }

    @mcp.tool()
    def compare_subscription_tiers() -> Dict[str, Any]:
        """
        Compare available subscription tiers and their benefits.

        Returns:
            Comparison of Basic and Premium tiers
        """
        return {
            "success": True,
            "tiers": {
                "basic": {
                    "name": "Basic",
                    "monthly_quota": 4,
                    "price": "Standard pricing",
                    "features": [
                        "4 experiences per month",
                        "Access to standard events",
                        "Standard customer support",
                    ],
                    "limitations": [
                        "No access to premium events",
                        "No priority booking",
                    ],
                },
                "premium": {
                    "name": "Premium",
                    "monthly_quota": 10,
                    "price": "Premium pricing",
                    "features": [
                        "10 experiences per month",
                        "Priority access to all events",
                        "Access to exclusive premium events",
                        "Early booking for high-demand experiences",
                        "Priority customer support",
                        "Discounts on additional premium events",
                    ],
                    "limitations": [],
                },
            },
            "recommendation": "Premium tier recommended for frequent users",
        }


# ============================================================================
# RESERVATION MANAGEMENT TOOLS
# ============================================================================

if mcp:

    @mcp.tool()
    def manage_reservation(
        user_id: str, reservation_id: str, action: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manage user reservations (cancel, refund request).

        Args:
            user_id: The user's unique identifier
            reservation_id: The reservation ID to manage
            action: Action to perform ('cancel' or 'refund')
            reason: Optional reason for the action

        Returns:
            Result of the reservation management action
        """
        if action == "cancel":
            result = cancel_reservation(user_id, reservation_id)

            if result.get("success"):
                return {
                    **result,
                    "note": "Cancellation successful. Quota restored if canceled 24+ hours before event.",
                }
            return result

        elif action == "refund":
            if not reason:
                reason = "Customer requested refund"

            result = request_refund(user_id, reservation_id, reason)

            if result.get("success"):
                return {
                    **result,
                    "note": "Refund request submitted. Requires approval from support lead. Processing time: 5-7 business days.",
                }
            return result

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. Use 'cancel' or 'refund'.",
            }

    @mcp.tool()
    def get_reservation_history(
        user_id: str, status_filter: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get user's reservation history with optional filtering.

        Args:
            user_id: The user's unique identifier
            status_filter: Optional status filter ('reserved', 'cancelled', 'completed')
            limit: Maximum number of reservations to return

        Returns:
            Reservation history with details
        """
        result = get_reservations(user_id, status=status_filter)

        if not result.get("success"):
            return result

        reservations = result.get("reservations", [])[:limit]

        # Categorize reservations
        upcoming = []
        past = []
        cancelled = []

        for res in reservations:
            if res["status"] == "cancelled":
                cancelled.append(res)
            elif res["status"] == "completed":
                past.append(res)
            else:
                upcoming.append(res)

        return {
            "success": True,
            "user_id": user_id,
            "total_count": result.get("count", 0),
            "showing": len(reservations),
            "upcoming": upcoming,
            "past": past,
            "cancelled": cancelled,
            "summary": {
                "upcoming_count": len(upcoming),
                "past_count": len(past),
                "cancelled_count": len(cancelled),
            },
        }


# ============================================================================
# ACCOUNT MANAGEMENT TOOLS
# ============================================================================

if mcp:

    @mcp.tool()
    def diagnose_account_issue(user_id: str) -> Dict[str, Any]:
        """
        Diagnose common account issues and provide recommendations.

        Args:
            user_id: The user's unique identifier

        Returns:
            Diagnosis with issues found and recommended actions
        """
        issues = []
        recommendations = []

        # Check account status
        account_status = check_account_status(user_id)

        if not account_status.get("success"):
            return {
                "success": False,
                "error": "Unable to check account status",
                "user_id": user_id,
            }

        # Check if blocked
        if account_status.get("is_blocked"):
            issues.append(
                {
                    "type": "account_blocked",
                    "severity": "critical",
                    "description": "Account is blocked",
                }
            )
            recommendations.append(
                {
                    "action": "escalate_to_support",
                    "description": "Escalate to support team to review and unblock account",
                    "priority": "high",
                }
            )

        # Check subscription
        subscription = get_subscription_status(user_id)

        if subscription.get("success"):
            if subscription.get("status") != "active":
                issues.append(
                    {
                        "type": "inactive_subscription",
                        "severity": "high",
                        "description": f"Subscription is {subscription.get('status')}",
                    }
                )
                recommendations.append(
                    {
                        "action": "reactivate_subscription",
                        "description": "Guide user to reactivate subscription",
                        "priority": "high",
                    }
                )
        else:
            issues.append(
                {
                    "type": "no_subscription",
                    "severity": "high",
                    "description": "No subscription found",
                }
            )
            recommendations.append(
                {
                    "action": "create_subscription",
                    "description": "Help user subscribe to CultPass",
                    "priority": "high",
                }
            )

        # Check for quota issues
        if subscription.get("success") and subscription.get("status") == "active":
            reservations = get_reservations(user_id, status="reserved")
            if reservations.get("success"):
                used = reservations.get("count", 0)
                quota = subscription.get("monthly_quota", 0)

                if used >= quota:
                    issues.append(
                        {
                            "type": "quota_exceeded",
                            "severity": "medium",
                            "description": f"Monthly quota fully used ({used}/{quota})",
                        }
                    )
                    recommendations.append(
                        {
                            "action": "upgrade_tier",
                            "description": "Suggest upgrading to Premium tier for more quota",
                            "priority": "medium",
                        }
                    )

        return {
            "success": True,
            "user_id": user_id,
            "account_healthy": len(issues) == 0,
            "issues_found": len(issues),
            "issues": issues,
            "recommendations": recommendations,
            "overall_status": (
                "critical"
                if account_status.get("is_blocked")
                else "needs_attention" if issues else "healthy"
            ),
        }

    @mcp.tool()
    def generate_account_summary(user_id: str) -> Dict[str, Any]:
        """
        Generate a comprehensive account summary for support agents.

        Args:
            user_id: The user's unique identifier

        Returns:
            Complete account summary with all relevant information
        """
        # Gather all information
        user_info = get_user_info(user_id)
        subscription = get_subscription_status(user_id)
        reservations = get_reservations(user_id)
        account_status = check_account_status(user_id)

        # Build summary
        summary = {
            "success": True,
            "user_id": user_id,
            "generated_at": datetime.now().isoformat(),
            "account_overview": {
                "name": (
                    user_info.get("full_name")
                    if user_info.get("success")
                    else "Unknown"
                ),
                "email": (
                    user_info.get("email") if user_info.get("success") else "Unknown"
                ),
                "status": "blocked" if account_status.get("is_blocked") else "active",
                "created_at": (
                    user_info.get("created_at") if user_info.get("success") else None
                ),
            },
            "subscription_overview": {
                "tier": (
                    subscription.get("tier") if subscription.get("success") else "None"
                ),
                "status": (
                    subscription.get("status")
                    if subscription.get("success")
                    else "No subscription"
                ),
                "monthly_quota": (
                    subscription.get("monthly_quota")
                    if subscription.get("success")
                    else 0
                ),
            },
            "activity_overview": {
                "total_reservations": (
                    reservations.get("count", 0) if reservations.get("success") else 0
                ),
                "active_reservations": (
                    len(
                        [
                            r
                            for r in reservations.get("reservations", [])
                            if r["status"] == "reserved"
                        ]
                    )
                    if reservations.get("success")
                    else 0
                ),
            },
            "quick_actions": [],
        }

        # Add quick actions based on status
        if account_status.get("is_blocked"):
            summary["quick_actions"].append("Unblock account")

        if subscription.get("success") and subscription.get("status") != "active":
            summary["quick_actions"].append("Reactivate subscription")

        if reservations.get("success") and reservations.get("count", 0) > 0:
            summary["quick_actions"].append("View reservations")

        return summary


# ============================================================================
# SERVER INITIALIZATION
# ============================================================================


def get_mcp_server():
    """Get the FastMCP server instance."""
    return mcp


def list_mcp_tools() -> List[str]:
    """List all available MCP tools."""
    if not mcp:
        return []

    return [
        "lookup_user",
        "check_user_eligibility",
        "get_subscription_details",
        "compare_subscription_tiers",
        "manage_reservation",
        "get_reservation_history",
        "diagnose_account_issue",
        "generate_account_summary",
    ]


if __name__ == "__main__":
    if mcp:
        # Run the MCP server
        mcp.run()
    else:
        print("FastMCP not available. Install with: pip install fastmcp")
