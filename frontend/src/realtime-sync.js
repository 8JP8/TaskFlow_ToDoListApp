import { io } from 'socket.io-client';
import apiConfig from './api-config.js';

class RealtimeSync {
  constructor() {
    this.socket = null;
    this.storageId = null;
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
      onConnectionChange: null
    };
  }

  async connect(storageId, userId) {
    try {
      const baseUrl = await apiConfig.getBaseUrl();
      // Use the base URL for Socket.IO (not the /api endpoint)
      const socketUrl = baseUrl;
      
      console.log('Connecting to Socket.IO at:', socketUrl);
      
      this.socket = io(socketUrl, {
        transports: ['websocket', 'polling'],
        autoConnect: true,
        forceNew: true
      });

      this.storageId = storageId;
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
      console.log('Real-time sync connected');
      console.log('Socket ID:', this.socket.id);
      this.joinStorageRoom();
      this.startIdleDetection();
    });

    this.socket.on('disconnect', () => {
      this.isConnected = false;
      this.callbacks.onConnectionChange?.(false);
      console.log('Real-time sync disconnected');
    });

    this.socket.on('joined_storage', (data) => {
      console.log('Joined storage room:', data.storage_id);
    });

    this.socket.on('task_created', (data) => {
      console.log('Received task_created event:', data);
      if (data.storage_id === this.storageId) {
        console.log('Processing task_created for current storage');
        this.callbacks.onTaskCreated?.(data.task);
      } else {
        console.log('Ignoring task_created for different storage:', data.storage_id);
      }
    });

    this.socket.on('task_updated', (data) => {
      console.log('Received task_updated event:', data);
      if (data.storage_id === this.storageId) {
        console.log('Processing task_updated for current storage');
        console.log('Task data:', data.task);
        console.log('Update type:', data.update_type);
        this.callbacks.onTaskUpdated?.(data);
      } else {
        console.log('Ignoring task_updated for different storage:', data.storage_id);
      }
    });

    this.socket.on('task_deleted', (data) => {
      console.log('Received task_deleted event:', data);
      if (data.storage_id === this.storageId) {
        console.log('Processing task_deleted for current storage');
        this.callbacks.onTaskDeleted?.(data.task_id);
      } else {
        console.log('Ignoring task_deleted for different storage:', data.storage_id);
      }
    });

    this.socket.on('user_activity_update', (data) => {
      if (data.user_id !== this.userId) {
        this.callbacks.onUserActivity?.(data);
      }
    });

    this.socket.on('test_event', (data) => {
      console.log('Received test event:', data);
      if (data.storage_id === this.storageId) {
        console.log('Test event for current storage:', data.message);
      }
    });

    // Add a catch-all event listener for debugging
    this.socket.onAny((eventName, ...args) => {
      console.log('Received Socket.IO event:', eventName, args);
    });
  }

  joinStorageRoom() {
    if (this.socket && this.storageId) {
      console.log('Joining storage room:', this.storageId);
      this.socket.emit('join_storage', { storage_id: this.storageId });
    }
  }

  leaveStorageRoom() {
    if (this.socket && this.storageId) {
      this.socket.emit('leave_storage', { storage_id: this.storageId });
    }
  }

  updateActivity(activity) {
    if (!this.socket || !this.storageId || !this.userId) return;

    this.isIdle = activity === 'idle';
    this.isEditing = activity === 'editing';
    this.isRecording = activity === 'recording';

    this.socket.emit('user_activity', {
      storage_id: this.storageId,
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
    if (!this.socket || !this.storageId) {
      console.log('Cannot test connection - not connected or no storage ID');
      return false;
    }
    
    try {
      const apiUrl = await apiConfig.getApiUrl();
      const response = await fetch(`${apiUrl}/test-socket?storage_id=${this.storageId}`);
      const result = await response.json();
      console.log('Test socket response:', result);
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
