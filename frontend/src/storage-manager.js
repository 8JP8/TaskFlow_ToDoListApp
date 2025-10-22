// Storage Manager - Handles storage identification and isolation with secure storage
class StorageManager {
  constructor() {
    this.storageId = null;
    this.storageKeys = {
      main: 'tf_dev_main',
      part1: 'tf_dev_p1',
      part2: 'tf_dev_p2',
      part3: 'tf_dev_p3',
      hash: 'tf_dev_hash'
    };
  }

  // Simple hash function for obfuscation
  simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(36);
  }

  // Scatter storage ID across multiple storage entries
  scatterStorageId(storageId) {
    const parts = [];
    const chunkSize = Math.ceil(storageId.length / 3);
    
    for (let i = 0; i < 3; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, storageId.length);
      parts.push(storageId.substring(start, end));
    }
    
    // Add random padding to each part
    const paddedParts = parts.map((part) => {
      const randomPrefix = Math.random().toString(36).substring(2, 8);
      const randomSuffix = Math.random().toString(36).substring(2, 8);
      return `${randomPrefix}_${part}_${randomSuffix}`;
    });
    
    return paddedParts;
  }

  // Reconstruct storage ID from scattered parts
  reconstructStorageId(scatteredParts) {
    const cleanParts = scatteredParts.map(part => {
      const parts = part.split('_');
      return parts[1]; // Extract the actual storage ID part
    });
    return cleanParts.join('');
  }

  // Store storage ID securely
  storeStorageIdSecurely(storageId) {
    try {
      // Scatter the storage ID
      const scatteredParts = this.scatterStorageId(storageId);
      
      // Store each part separately
      localStorage.setItem(this.storageKeys.part1, scatteredParts[0]);
      localStorage.setItem(this.storageKeys.part2, scatteredParts[1]);
      localStorage.setItem(this.storageKeys.part3, scatteredParts[2]);
      
      // Store a hash for verification
      const hash = this.simpleHash(storageId);
      localStorage.setItem(this.storageKeys.hash, hash);
      
      // Store a flag indicating secure storage is used
      localStorage.setItem(this.storageKeys.main, 'secure');
      
      console.log('Storage ID stored securely');
    } catch (error) {
      console.error('Error storing storage ID securely:', error);
      // Fallback to simple storage
      localStorage.setItem(this.storageKeys.main, storageId);
    }
  }

  // Retrieve storage ID from secure storage
  retrieveStorageIdSecurely() {
    try {
      // Check if secure storage is used
      const storageType = localStorage.getItem(this.storageKeys.main);
      
      if (storageType === 'secure') {
        // Retrieve scattered parts
        const part1 = localStorage.getItem(this.storageKeys.part1);
        const part2 = localStorage.getItem(this.storageKeys.part2);
        const part3 = localStorage.getItem(this.storageKeys.part3);
        const storedHash = localStorage.getItem(this.storageKeys.hash);
        
        if (part1 && part2 && part3 && storedHash) {
          const scatteredParts = [part1, part2, part3];
          const storageId = this.reconstructStorageId(scatteredParts);
          
          // Verify hash
          const computedHash = this.simpleHash(storageId);
          if (computedHash === storedHash) {
            return storageId;
          } else {
            console.warn('Storage ID hash verification failed');
            this.clearSecureStorage();
            return null;
          }
        }
      } else if (storageType && storageType !== 'secure') {
        // Legacy storage format
        return storageType;
      }
      
      return null;
    } catch (error) {
      console.error('Error retrieving storage ID securely:', error);
      return null;
    }
  }

  // Clear secure storage
  clearSecureStorage() {
    Object.values(this.storageKeys).forEach(key => {
      localStorage.removeItem(key);
    });
  }

  // Generate a unique storage ID
  generateStorageId() {
    // Create a random ID with letters and numbers only
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    
    // Generate 16-character random ID
    for (let i = 0; i < 16; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    
    return result;
  }

  // Get or create storage ID
  getStorageId() {
    if (this.storageId) {
      return this.storageId;
    }

    // Try to get existing storage ID from secure storage
    const storedId = this.retrieveStorageIdSecurely();
    if (storedId) {
      this.storageId = storedId;
      return this.storageId;
    }

    // Generate new storage ID
    this.storageId = this.generateStorageId();
    this.storeStorageIdSecurely(this.storageId);
    
    console.log('Generated new storage ID:', this.storageId);
    return this.storageId;
  }

  // Set a new storage ID
  setStorageId(newStorageId) {
    this.storageId = newStorageId;
    this.storeStorageIdSecurely(newStorageId);
    console.log('Storage ID updated:', newStorageId);
  }

  // Reset storage ID (for testing purposes)
  resetStorageId() {
    this.clearSecureStorage();
    this.storageId = null;
    console.log('Storage ID reset');
  }

  // Get storage info for debugging
  getStorageInfo() {
    return {
      storageId: this.getStorageId(),
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      timestamp: new Date().toISOString()
    };
  }
}

// Create singleton instance
const storageManager = new StorageManager();

export default storageManager;
