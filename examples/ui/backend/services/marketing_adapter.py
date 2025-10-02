"""Marketing Analytics Platform Adapter.

This module bridges the Panda AGI chat UI with the Wine Marketing Analytics platform.
It supports two modes:
1. In-process (local): Direct Python import from the marketing platform
2. HTTP: REST API calls to the Flask marketing service

Environment Variables:
    MARKETING_MODE: 'local' (default) or 'http'
    MARKETING_API_URL: Base URL for HTTP mode (e.g., http://localhost:5001)
    MARKETING_API_KEY: API key for HTTP authentication
    MARKETING_PLATFORM_PATH: Path to omt-pai-4 project for local mode
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import asdict

logger = logging.getLogger("panda_agi_api.marketing")


class MarketingAdapter:
    """Adapter for Wine Marketing Analytics platform integration."""

    def __init__(self):
        """Initialize the adapter based on configuration."""
        self.mode = os.getenv("MARKETING_MODE", "local").lower()
        self.api_url = os.getenv("MARKETING_API_URL", "http://localhost:5001")
        self.api_key = os.getenv("MARKETING_API_KEY", "")

        if self.mode == "local":
            self._init_local_mode()
        elif self.mode == "http":
            self._init_http_mode()
        else:
            raise ValueError(f"Invalid MARKETING_MODE: {self.mode}. Must be 'local' or 'http'")

        logger.info(f"MarketingAdapter initialized in {self.mode} mode")

    def _init_local_mode(self):
        """Initialize in-process Python import mode."""
        platform_path = os.getenv(
            "MARKETING_PLATFORM_PATH",
            "/Users/andreyzherditskiy/work/bc/omt-pai-4"
        )

        if not os.path.exists(platform_path):
            raise RuntimeError(
                f"Marketing platform not found at {platform_path}. "
                "Set MARKETING_PLATFORM_PATH environment variable."
            )

        # Add platform to Python path
        if platform_path not in sys.path:
            sys.path.insert(0, platform_path)

        try:
            # Import marketing service components
            from agent.services import MarketingService, FilterRequest
            from agent.customers_agent import CustomerAnalyticsAgent

            # Initialize the analytics agent and service
            self.agent = CustomerAnalyticsAgent()
            self.service = MarketingService(self.agent)
            self.FilterRequest = FilterRequest

            logger.info(f"Loaded marketing service from {platform_path}")
        except Exception as e:
            logger.error(f"Failed to import marketing service: {e}")
            raise RuntimeError(
                f"Failed to load marketing platform from {platform_path}: {e}"
            )

    def _init_http_mode(self):
        """Initialize HTTP REST API mode."""
        try:
            import httpx
            self.http_client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            logger.info(f"HTTP client initialized for {self.api_url}")
        except ImportError:
            raise RuntimeError(
                "httpx library required for HTTP mode. Install with: pip install httpx"
            )

    async def query(self, query_text: str, limit: int = 100) -> Dict[str, Any]:
        """
        Execute a marketing query and return formatted response.

        Args:
            query_text: Natural language query or preset filter name
            limit: Maximum number of results to return

        Returns:
            Dict containing query results in standard format
        """
        if self.mode == "local":
            return await self._query_local(query_text, limit)
        else:
            return await self._query_http(query_text, limit)

    async def _query_local(self, query_text: str, limit: int) -> Dict[str, Any]:
        """Execute query using in-process Python import."""
        try:
            # Create filter request
            request = self.FilterRequest(
                filter_label=query_text if self._is_preset_filter(query_text) else None,
                custom_query=query_text if not self._is_preset_filter(query_text) else None,
                format="full",
                limit=limit
            )

            # Execute query
            response = self.service.filter_customers(request)

            # Convert response to dict
            result = {
                "success": response.success,
                "query": query_text,
                "engine_used": response.metadata.get("engine_used", "unknown"),
                "tokens_used": response.metadata.get("tokens_used", 0),
                "execution_time": response.metadata.get("execution_time", 0),
                "count": response.count,
                "customer_ids": response.customer_ids,
                "customers": [asdict(c) for c in response.customers],
                "sql": response.sql or "",
                "code": response.code or "",
                "metadata": response.metadata
            }

            logger.info(
                f"Local query executed: engine={result['engine_used']}, "
                f"count={result['count']}, time={result['execution_time']:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Local query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query_text
            }

    async def _query_http(self, query_text: str, limit: int) -> Dict[str, Any]:
        """Execute query using HTTP REST API."""
        try:
            # Determine if this is a preset filter or custom query
            is_preset = self._is_preset_filter(query_text)

            payload = {
                "format": "full",
                "limit": limit
            }

            if is_preset:
                payload["filter"] = query_text
            else:
                payload["query"] = query_text

            # Make HTTP request
            response = await self.http_client.post("/marketing/filter", json=payload)
            response.raise_for_status()

            result = response.json()
            result["query"] = query_text

            logger.info(
                f"HTTP query executed: status={response.status_code}, "
                f"count={result.get('count', 0)}"
            )

            return result

        except Exception as e:
            logger.error(f"HTTP query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query_text
            }

    def _is_preset_filter(self, query: str) -> bool:
        """Check if query matches a known preset filter."""
        preset_filters = {
            "VIP customers only",
            "High value customers (Average Order > $300)",
            "Active customers in last 30 days",
            "Frequent buyers (10+ purchases)",
            "Churn risk customers (inactive 90+ days)"
        }
        return query in preset_filters

    async def get_filters(self) -> List[str]:
        """Get list of available preset filters."""
        if self.mode == "local":
            return [
                "VIP customers only",
                "High value customers (Average Order > $300)",
                "Active customers in last 30 days",
                "Frequent buyers (10+ purchases)",
                "Churn risk customers (inactive 90+ days)"
            ]
        else:
            try:
                response = await self.http_client.get("/marketing/filters")
                response.raise_for_status()
                data = response.json()
                return list(data.get("filters", {}).keys())
            except Exception as e:
                logger.error(f"Failed to get filters: {e}")
                return []

    async def get_summary(self) -> Dict[str, Any]:
        """Get customer summary statistics."""
        if self.mode == "local":
            try:
                summary = self.service.get_customer_summary()
                return summary
            except Exception as e:
                logger.error(f"Failed to get summary: {e}")
                return {}
        else:
            try:
                response = await self.http_client.get("/marketing/summary")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get summary: {e}")
                return {}

    async def close(self):
        """Cleanup resources."""
        if self.mode == "http" and hasattr(self, 'http_client'):
            await self.http_client.aclose()
            logger.info("HTTP client closed")
