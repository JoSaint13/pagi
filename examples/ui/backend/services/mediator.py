"""Mediator for Wine Marketing Analytics Platform integration.

This module bridges the Panda AGI chat UI with the Wine Marketing Analytics platform.
It transforms marketing queries into streaming events compatible with the Panda UI.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Optional

from .marketing_adapter import MarketingAdapter

logger = logging.getLogger("panda_agi_api.mediator")

STREAM_EVENT_TYPE = "tool_end"


def _utc_timestamp() -> str:
    """Return an ISO8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


class AgentMediator:
    """Marketing Analytics Platform mediator for the chat UI.

    Bridges natural language marketing queries to the Wine Marketing Analytics
    platform and streams results in a format compatible with the Panda UI.
    """

    def __init__(self, conversation_id: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.api_key = api_key
        self.adapter = MarketingAdapter()
        logger.info(f"AgentMediator initialized for conversation {self.conversation_id}")

    async def stream(self, query: str) -> AsyncGenerator[Dict, None]:
        """Stream marketing query results as Panda-compatible events."""

        # Echo the user message
        yield self._wrap_event(
            data={
                "type": "user_send_message",
                "input_params": {
                    "text": query,
                    "attachments": [],
                },
            }
        )

        await asyncio.sleep(0.05)

        try:
            # Execute marketing query
            logger.info(f"Executing marketing query: {query}")
            result = await self.adapter.query(query, limit=100)

            if not result.get("success", False):
                # Emit error event
                yield self._wrap_event(
                    data={
                        "type": "error",
                        "tool_name": "omt.marketing.error",
                        "error": result.get("error", "Unknown error"),
                        "payload": result,
                    }
                )
                return

            # Emit marketing response event
            yield self._wrap_event(
                data={
                    "type": "marketing_response",
                    "tool_name": "omt.marketing.filter",
                    "payload": {
                        "query": result.get("query", query),
                        "engine_used": result.get("engine_used", "unknown"),
                        "tokens_used": result.get("tokens_used", 0),
                        "execution_time": result.get("execution_time", 0),
                        "count": result.get("count", 0),
                        "customer_ids": result.get("customer_ids", []),
                        "customers": result.get("customers", [])[:20],  # Limit to first 20 for display
                        "sql": result.get("sql", ""),
                        "code": result.get("code", ""),
                        "metadata": result.get("metadata", {}),
                    },
                }
            )

            # Emit summary if we have customers
            if result.get("count", 0) > 0:
                customers = result.get("customers", [])
                total_ltv = sum(c.get("lifetime_value", 0) for c in customers)
                avg_ltv = total_ltv / len(customers) if customers else 0

                summary_text = (
                    f"**Query Results Summary**\n\n"
                    f"- **Total Customers**: {result.get('count', 0)}\n"
                    f"- **Total Lifetime Value**: ${total_ltv:,.2f}\n"
                    f"- **Average Lifetime Value**: ${avg_ltv:,.2f}\n"
                    f"- **Execution Time**: {result.get('execution_time', 0):.2f}s\n"
                    f"- **Engine Used**: {result.get('engine_used', 'unknown')}\n"
                )

                if result.get('tokens_used', 0) > 0:
                    summary_text += f"- **Tokens Used**: {result.get('tokens_used', 0)}\n"

                yield self._wrap_event(
                    data={
                        "type": "marketing_summary",
                        "tool_name": "omt.marketing.summary",
                        "payload": {
                            "text": summary_text,
                            "total_customers": result.get("count", 0),
                            "total_lifetime_value": total_ltv,
                            "average_lifetime_value": avg_ltv,
                        },
                    }
                )

        except Exception as e:
            logger.error(f"Marketing query failed: {e}", exc_info=True)
            yield self._wrap_event(
                data={
                    "type": "error",
                    "tool_name": "omt.marketing.error",
                    "error": f"Marketing query failed: {str(e)}",
                    "payload": {"query": query},
                }
            )

    def _wrap_event(self, *, data: Dict) -> Dict:
        """Attach identifiers, timestamps, and top-level metadata."""
        timestamp = _utc_timestamp()
        event_id = str(uuid.uuid4())

        payload = {
            "timestamp": timestamp,
            "id": event_id,
            **data,
        }

        # Ensure we always have a tool name so the UI can label the card
        if "tool_name" not in payload and payload.get("type") not in {"user_send_message", "error"}:
            payload["tool_name"] = payload.get("type", "bridge_event")

        return {
            "event_type": STREAM_EVENT_TYPE,
            "timestamp": timestamp,
            "data": payload,
        }

    async def cleanup(self):
        """Cleanup adapter resources."""
        await self.adapter.close()
