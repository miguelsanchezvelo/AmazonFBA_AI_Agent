/**
 * WebSocket Client for Real-time Updates
 * 
 * Manages WebSocket connection to backend for real-time events
 */

import type { WebSocketEvent } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

type EventHandler = (event: WebSocketEvent) => void;
type ConnectionHandler = () => void;
type ErrorHandler = (error: Event) => void;

/**
 * WebSocket client class
 * Handles connection, reconnection, and event dispatching
 */
class WebSocketClient {
  private ws: WebSocket | null = null;
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private disconnectionHandlers: Set<ConnectionHandler> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;
  private shouldReconnect = true;

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }

    this.isConnecting = true;
    console.log('[WebSocket] Connecting to:', WS_URL);

    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      this.isConnecting = false;
      this.attemptReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    console.log('[WebSocket] Disconnecting...');
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Send message to server
   */
  send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] Cannot send message, not connected');
    }
  }

  /**
   * Subscribe to specific event type
   */
  on(eventType: string, handler: EventHandler): () => void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    this.eventHandlers.get(eventType)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.eventHandlers.get(eventType)?.delete(handler);
    };
  }

  /**
   * Subscribe to connection events
   */
  onConnect(handler: ConnectionHandler): () => void {
    this.connectionHandlers.add(handler);
    return () => {
      this.connectionHandlers.delete(handler);
    };
  }

  /**
   * Subscribe to disconnection events
   */
  onDisconnect(handler: ConnectionHandler): () => void {
    this.disconnectionHandlers.add(handler);
    return () => {
      this.disconnectionHandlers.delete(handler);
    };
  }

  /**
   * Subscribe to error events
   */
  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => {
      this.errorHandlers.delete(handler);
    };
  }

  /**
   * Get connection status
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // ======== Private Methods ========

  private handleOpen(): void {
    console.log('[WebSocket] Connected');
    this.isConnecting = false;
    this.reconnectAttempts = 0;

    // Notify connection handlers
    this.connectionHandlers.forEach((handler) => handler());
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const data: WebSocketEvent = JSON.parse(event.data);
      console.log('[WebSocket] Received event:', data.type);

      // Dispatch to specific event handlers
      const handlers = this.eventHandlers.get(data.type);
      if (handlers) {
        handlers.forEach((handler) => handler(data));
      }

      // Dispatch to wildcard handlers
      const wildcardHandlers = this.eventHandlers.get('*');
      if (wildcardHandlers) {
        wildcardHandlers.forEach((handler) => handler(data));
      }
    } catch (error) {
      console.error('[WebSocket] Error parsing message:', error);
    }
  }

  private handleError(event: Event): void {
    console.error('[WebSocket] Error:', event);
    this.errorHandlers.forEach((handler) => handler(event));
  }

  private handleClose(): void {
    console.log('[WebSocket] Disconnected');
    this.isConnecting = false;

    // Notify disconnection handlers
    this.disconnectionHandlers.forEach((handler) => handler());

    // Attempt reconnection if enabled
    if (this.shouldReconnect) {
      this.attemptReconnect();
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(
      `[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect();
      }
    }, delay);
  }
}

// Export singleton instance
export const wsClient = new WebSocketClient();

// Auto-connect on module load
if (typeof window !== 'undefined') {
  wsClient.connect();
}

// Export type for use in other files
export type { WebSocketClient };

