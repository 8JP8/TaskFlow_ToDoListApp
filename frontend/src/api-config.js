// Dynamic API configuration that auto-detects the server IP
import axios from 'axios';

class ApiConfig {
  constructor() {
    this.baseURL = null;
    this.isInitialized = false;
  }

  // Try to detect the server IP automatically
  async detectServerIP() {
    // First, try to get server info from the current host
    const currentHost = window.location.hostname;
    
    // If we're on localhost, try to get the server IP from the backend
    if (currentHost === 'localhost' || currentHost === '127.0.0.1') {
      try {
        // Try to connect to the backend on the same host
        const protocol = window.location.protocol;
        const response = await axios.get(`${protocol}//${currentHost}:5000/api/server/info`, { timeout: 2000 });
        return response.data.server_ip;
      } catch (error) {
        console.log('Could not auto-detect server IP, using fallback');
        return null;
      }
    }
    
    // If we're accessing from another storage, use the current hostname
    return currentHost;
  }

  // Initialize the API configuration
  async initialize() {
    if (this.isInitialized) return this.baseURL;

    try {
      const serverIP = await this.detectServerIP();
      
      // Detect if we're running on HTTPS
      const isHTTPS = window.location.protocol === 'https:';
      const protocol = isHTTPS ? 'https:' : 'http:';
      
      if (serverIP) {
        // For HTTPS, don't include port (uses default 443)
        // For HTTP, include port 5000
        if (isHTTPS) {
          this.baseURL = `${protocol}//${serverIP}`;
        } else {
          this.baseURL = `${protocol}//${serverIP}:5000`;
        }
        console.log(`Auto-detected server IP: ${serverIP}`);
      } else {
        // Fallback to localhost for development
        if (isHTTPS) {
          this.baseURL = 'https://localhost:5000';
        } else {
          this.baseURL = 'http://localhost:5000';
        }
        console.log('Using fallback: localhost');
      }
      
      this.isInitialized = true;
      return this.baseURL;
    } catch (error) {
      console.error('Error initializing API config:', error);
      const isHTTPS = window.location.protocol === 'https:';
      this.baseURL = isHTTPS ? 'https://localhost:5000' : 'http://localhost:5000';
      this.isInitialized = true;
      return this.baseURL;
    }
  }

  // Get the API URL
  async getApiUrl() {
    if (!this.isInitialized) {
      await this.initialize();
    }
    return `${this.baseURL}/api`;
  }

  // Get the base URL
  async getBaseUrl() {
    if (!this.isInitialized) {
      await this.initialize();
    }
    return this.baseURL;
  }
}

// Create a singleton instance
const apiConfig = new ApiConfig();

export default apiConfig;
