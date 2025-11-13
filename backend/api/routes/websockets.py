#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket API Routes.

Endpoints para comunicación en tiempo real.
"""

import json
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime

from backend.models.events import EventSubscription, EventType
from backend.api.config import settings


router = APIRouter()


# Active WebSocket connections manager
class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts.
    
    Attributes:
        active_connections: Set of active WebSocket connections
        subscriptions: Mapping of connection to event subscriptions
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, EventSubscription] = {}
    
    async def connect(self, websocket: WebSocket):
        """
        Accept and register new WebSocket connection.
        
        Args:
            websocket: WebSocket connection to accept
        """
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to specific connection.
        
        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all active connections.
        
        Args:
            message: Message dictionary to broadcast
        """
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                # Check subscription filters
                subscription = self.subscriptions.get(connection)
                if subscription and not self._matches_subscription(message, subscription):
                    continue
                
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    def _matches_subscription(self, message: dict, subscription: EventSubscription) -> bool:
        """
        Check if message matches subscription filters.
        
        Args:
            message: Message to check
            subscription: Subscription filters
            
        Returns:
            True if message should be sent to subscriber
        """
        # Check event type filter
        if subscription.event_types:
            event_type = message.get("event_type")
            if event_type not in subscription.event_types:
                return False
        
        # Check ASIN filter
        if subscription.asins:
            asin = message.get("payload", {}).get("asin")
            if asin not in subscription.asins:
                return False
        
        # Check priority filter
        if subscription.min_priority:
            priority = message.get("priority", "normal")
            priority_levels = ["low", "normal", "high", "critical"]
            min_level = priority_levels.index(subscription.min_priority.value)
            msg_level = priority_levels.index(priority)
            if msg_level < min_level:
                return False
        
        return True


# Global connection manager
manager = ConnectionManager()


@router.websocket("/updates")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None, description="JWT token for authentication")
):
    """
    WebSocket endpoint for real-time updates.
    
    Clients connect here to receive real-time events from agents.
    
    Protocol:
        1. Client connects with JWT token
        2. Client sends subscription preferences
        3. Server streams events matching subscription
        4. Client can update subscription anytime
    
    Args:
        websocket: WebSocket connection
        token: JWT token for authentication (optional for now)
        
    Examples:
        >>> ws = new WebSocket("ws://localhost:8000/api/v2/ws/updates");
        >>> ws.onmessage = (event) => {
        >>>   const data = JSON.parse(event.data);
        >>>   console.log("Event received:", data);
        >>> };
    """
    await manager.connect(websocket)
    
    # Send welcome message
    await manager.send_personal_message({
        "type": "connection",
        "status": "connected",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Connected to Amazon FBA AI Agent V2",
        "instructions": {
            "subscribe": "Send {type: 'subscribe', filters: {...}} to set event filters",
            "ping": "Send {type: 'ping'} for heartbeat"
        }
    }, websocket)
    
    try:
        # Keep connection alive and handle messages
        while True:
            # Wait for client messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Respond to heartbeat
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
                
                elif message_type == "subscribe":
                    # Update subscription filters
                    filters = message.get("filters", {})
                    subscription = EventSubscription(**filters)
                    manager.subscriptions[websocket] = subscription
                    
                    await manager.send_personal_message({
                        "type": "subscription_updated",
                        "filters": filters,
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
                
                elif message_type == "unsubscribe":
                    # Remove subscription filters
                    manager.subscriptions.pop(websocket, None)
                    
                    await manager.send_personal_message({
                        "type": "subscription_removed",
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
                
                else:
                    # Unknown message type
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
            
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client disconnected. Active connections: {len(manager.active_connections)}")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/stats")
async def get_websocket_stats():
    """
    Get WebSocket statistics.
    
    Returns:
        Statistics about active connections
        
    Examples:
        >>> GET /api/v2/ws/stats
    """
    return {
        "active_connections": len(manager.active_connections),
        "max_connections": settings.ws_max_connections,
        "subscriptions": len(manager.subscriptions)
    }


async def broadcast_event(event: dict):
    """
    Broadcast event to all WebSocket connections.
    
    This function is called by agents/services to push events to clients.
    
    Args:
        event: Event dictionary to broadcast
        
    Examples:
        >>> await broadcast_event({
        >>>     "event_type": "product_discovered",
        >>>     "payload": {"asin": "B08N5WRWNW", ...}
        >>> })
    """
    await manager.broadcast(event)

