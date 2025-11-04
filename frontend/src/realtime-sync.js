import { io } from 'socket.io-client';
import apiConfig from './api-config.js';

class RealtimeSync {
  constructor() {
    this.socket = null;
    this._s1d = null;
    this.userId = null;
    this.isConnected = false;
    this.activityTimeout = null;
    this.lastActivity = Date.now();
    this.isIdle = true;
    this.isEditing = false;
    this.isRecording = false;
    this.callbacks = {
      onTaskCreated: null,
      onTaskUpdated: null,
      onTaskDeleted: null,
      onUserActivity: null,
      onConnectionChange: null,
      onStorageOnlineCount: null
    };
  }

  async connect(_s1d, userId) {
    try {
      const baseUrl = await apiConfig.getBaseUrl();
      // Use the base URL for Socket.IO (not the /api endpoint)
      const socketUrl = baseUrl;
      
      console.log('Connecting to Socket.IO at:', socketUrl);
      
      this.socket = io(socketUrl, {
        transports: ['websocket', 'polling'],
        autoConnect: true,
        forceNew: true,
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 10000,
        timeout: 20000
      });

      this._s1d = _s1d;
      this.userId = userId;

      this.setupEventListeners();
      
      return true;
    } catch (error) {
      console.error('Failed to connect to real-time sync:', error);
      return false;
    }
  }

  setupEventListeners() {
    this.socket.on('connect', () => {
      this.isConnected = true;
      this.callbacks.onConnectionChange?.(true);
      console.log('DEBUG: Real-time sync connected');
      console.log('DEBUG: Socket ID:', this.socket.id);
      this.joinStorageRoom();
      this.startIdleDetection();
      this.startPresenceHeartbeat();
    });

    this.socket.on('disconnect', () => {
      this.isConnected = false;
      this.callbacks.onConnectionChange?.(false);
      console.log('DEBUG: Real-time sync disconnected');
      this.stopPresenceHeartbeat();
    });

    // Reconnection lifecycle logging and state bridging
    if (this.socket && this.socket.io) {
      this.socket.io.on('reconnect_attempt', (attempt) => {
        console.log('DEBUG: Reconnect attempt', attempt);
      });
      this.socket.io.on('reconnect', (attempt) => {
        console.log('DEBUG: Reconnected after attempts:', attempt);
        // Room rejoin happens on 'connect' listener
      });
      this.socket.io.on('reconnect_error', (err) => {
        console.warn('DEBUG: Reconnect error:', err?.message || err);
      });
      this.socket.io.on('error', (err) => {
        console.warn('DEBUG: Socket.IO error:', err?.message || err);
      });
    }

    this.socket.on('connect_error', (err) => {
      console.warn('DEBUG: Connect error:', err?.message || err);
      this.callbacks.onConnectionChange?.(false);
    });

    this.socket.on('joined_storage', () => {
      console.log('DEBUG: Joined storage room');
    });

    this.socket.on('task_created', (data) => {
      console.log('Received task_created event');
      if (data.storage_id === this._s1d) {
        console.log('Processing task_created for current storage');
        this.callbacks.onTaskCreated?.(data.task);
      } else {
        console.log('Ignoring task_created for different storage');
      }
    });

    this.socket.on('task_updated', (data) => {
      console.log('DEBUG: Received task_updated event');
      console.log('DEBUG: Update type:', data.update_type);
      if (data.storage_id === this._s1d) {
        console.log('DEBUG: Processing task_updated for current storage');
        console.log('DEBUG: Calling onTaskUpdated callback');
        this.callbacks.onTaskUpdated?.(data);
      } else {
        console.log('DEBUG: Ignoring task_updated for different storage');
      }
    });

    this.socket.on('task_deleted', (data) => {
      console.log('Received task_deleted event');
      if (data.storage_id === this._s1d) {
        console.log('Processing task_deleted for current storage');
        this.callbacks.onTaskDeleted?.(data.task_id);
      } else {
        console.log('Ignoring task_deleted for different storage');
      }
    });

    this.socket.on('user_activity_update', (data) => {
      if (data.user_id !== this.userId) {
        this.callbacks.onUserActivity?.(data);
      }
    });

    this.socket.on('storage_online_count', (data) => {
      console.log('DEBUG: Received storage_online_count event');
      console.log('DEBUG: Event storage_id:', data.storage_id);
      console.log('DEBUG: Current _s1d:', this._s1d);
      console.log('DEBUG: Count:', data.count);
      if (data.storage_id === this._s1d) {
        console.log('DEBUG: Calling onStorageOnlineCount callback');
        this.callbacks.onStorageOnlineCount?.(data);
      } else {
        console.log('DEBUG: Ignoring storage_online_count for different storage');
      }
    });

    this.socket.on('test_event', (data) => {
      console.log('Received test event');
      if (data.storage_id === this._s1d) {
        console.log('Test event for current storage:', data.message);
      }
    });

    // Add a catch-all event listener for debugging
    this.socket.onAny((eventName) => {
      console.log('DEBUG: Received Socket.IO event:', eventName);
      if (eventName === 'task_updated') {
        console.log('DEBUG: task_updated event received');
      }
    });
  }

  joinStorageRoom() {
    if (this.socket && this._s1d) {
      console.log('DEBUG: Joining storage room');
      this.socket.emit('join_storage', { storage_id: this._s1d });
      console.log('DEBUG: join_storage event emitted');
    } else {
      console.log('DEBUG: Cannot join storage room - socket:', !!this.socket);
    }
  }

  leaveStorageRoom() {
    if (this.socket && this._s1d) {
      this.socket.emit('leave_storage', { storage_id: this._s1d });
    }
  }

  updateActivity(activity) {
    if (!this.socket || !this._s1d || !this.userId) return;

    this.isIdle = activity === 'idle';
    this.isEditing = activity === 'editing';
    this.isRecording = activity === 'recording';

    this.socket.emit('user_activity', {
      storage_id: this._s1d,
      user_id: this.userId,
      activity: activity
    });

    this.lastActivity = Date.now();
  }

  startIdleDetection() {
    // Check for idle state every 30 seconds
    setInterval(() => {
      const timeSinceActivity = Date.now() - this.lastActivity;
      const isCurrentlyIdle = timeSinceActivity > 30000; // 30 seconds

      if (isCurrentlyIdle && !this.isIdle) {
        this.updateActivity('idle');
      }
    }, 30000);
  }

  // Periodically emit presence so other clients don't consider us offline
  startPresenceHeartbeat() {
    if (this.presenceInterval) {
      clearInterval(this.presenceInterval);
    }
    this.presenceInterval = setInterval(() => {
      if (!this.socket || !this.isConnected || !this._s1d || !this.userId) return;
      const activity = this.isRecording ? 'recording' : (this.isEditing ? 'editing' : (this.isIdle ? 'idle' : 'idle'));
      this.socket.emit('user_activity', {
        storage_id: this._s1d,
        user_id: this.userId,
        activity
      });
    }, 30000); // 30s heartbeat for faster presence updates
  }

  stopPresenceHeartbeat() {
    if (this.presenceInterval) {
      clearInterval(this.presenceInterval);
      this.presenceInterval = null;
    }
  }

  // Check if it's safe to sync (user is not actively editing/recording)
  canSync() {
    return this.isIdle && !this.isEditing && !this.isRecording;
  }

  // Check if other users are active
  hasActiveUsers(activeUsers) {
    return Object.values(activeUsers).some(user => 
      user.activity !== 'idle' && user.user_id !== this.userId
    );
  }

  setCallback(event, callback) {
    this.callbacks[event] = callback;
  }

  // Test the Socket.IO connection
  async testConnection() {
    if (!this.socket || !this._s1d) {
      console.log('Cannot test connection - not connected');
      return false;
    }
    
    try {
      const apiUrl = await apiConfig.getApiUrl();
      const response = await fetch(`${apiUrl}/test-socket?storage_id=${this._s1d}`);
      const result = await response.json();
      // Filter out storage_id from response before logging
      const filteredResult = { ...result };
      delete filteredResult.storage_id;
      console.log('Test socket response:', filteredResult);
      return true;
    } catch (error) {
      console.error('Test socket failed:', error);
      return false;
    }
  }

  disconnect() {
    if (this.socket) {
      this.leaveStorageRoom();
      this.socket.disconnect();
      this.socket = null;
    }
    this.isConnected = false;
  }
}

export default new RealtimeSync();
