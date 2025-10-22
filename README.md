# TaskFlow - Real-Time Collaborative Note Management

A secure, multi-storage note-taking application with real-time synchronization that uses storage-based isolation for privacy without requiring user login.

## 🚀 Key Features

### 📝 **Note Management**
- Create, edit, and delete tasks with rich descriptions
- Mark tasks as completed or pending
- Real-time statistics tracking
- Persistent storage across browser sessions
- **Real-time synchronization** across all devices with same storage ID
- **Conflict resolution** with automatic backup system
- **Version control** to prevent data loss

### 🔒 **Storage-Based Security**
- **No Login Required**: Each storage gets a unique identifier automatically
- **Complete Data Isolation**: Notes are private to each storage
- **Secure Access**: Only the storage that created notes can access them
- **Multi-Storage Support**: Use different storages with separate note collections

### 🔗 **Storage Linking**
- **Link New Storage**: Generate new storage IDs for additional storages
- **Cross-Storage Access**: Connect to existing storage IDs to share notes
- **Automatic Migration**: Seamlessly transfer notes between storages
- **Security Warnings**: Clear notifications about storage access implications

### 🎨 **Modern Interface**
- **Dark/Light Mode**: Automatic theme switching
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Multilingual Support**: English and Portuguese
- **Intuitive Navigation**: Clean, user-friendly interface
- **Real-time Indicators**: Live sync status and active user count
- **Mobile Optimized**: Shorter previews prevent layout issues

### 📱 **Cross-Platform**
- **Web-Based**: Works in any modern browser
- **No Installation**: Access directly from any storage
- **Offline Capable**: Notes persist locally and sync when online
- **Mobile Friendly**: Optimized for touch interfaces

## 🔄 Real-Time Collaboration Features

### **Live Synchronization**
- **Instant Updates**: Changes appear immediately across all devices
- **Multi-Device Support**: Unlimited devices can connect with same storage ID
- **Activity Awareness**: See when other users are editing or recording
- **Connection Status**: Visual indicators for sync status and active users

### **Smart Conflict Resolution**
- **Edit Protection**: Prevents interruptions while users are actively editing
- **Automatic Backups**: Creates backup copies when conflicts occur
- **Zero Data Loss**: All user work is preserved through version control
- **Seamless Integration**: Conflicts are resolved automatically without user intervention

### **Activity Tracking**
- **Idle Detection**: Automatically detects when users become inactive
- **Edit State Protection**: Prevents updates while users are editing tasks
- **Recording Protection**: Prevents interruptions during audio recording
- **Pending Updates Queue**: Stores updates until users become available

## 🛠️ Technical Features

### **Frontend (Vue.js)**
- Modern Vue 3 with Composition API
- Reactive state management
- Component-based architecture
- Responsive CSS with CSS variables
- Internationalization (i18n) support
- **Real-time WebSocket integration** with Socket.IO
- **Conflict resolution system** with automatic backups
- **Activity tracking** for editing and recording states

### **Backend (Flask + MongoDB)**
- RESTful API design
- MongoDB for document storage
- Storage-based data filtering
- Secure file upload handling
- CORS-enabled for cross-origin requests
- **Flask-SocketIO** for real-time WebSocket communication
- **Real-time event broadcasting** for all CRUD operations
- **User activity tracking** and synchronization

### **Security Implementation**
- Storage fingerprinting for unique identification
- Secure local storage with obfuscation
- Backend validation for all operations
- No cross-storage data leakage
- Automatic session management

## 🚀 Getting Started

### **For Users**
1. Open the application in your browser
2. Start creating notes immediately
3. Each storage maintains its own note collection
4. Use "Link New Storage" to generate IDs for other storages
5. Share storage IDs to access notes across storages

### **For Developers**
1. Clone the repository
2. Install dependencies: 
   - Frontend: `npm install` (includes socket.io-client)
   - Backend: `pip install -r requirements.txt` (includes flask-socketio)
3. Start the backend: `python app.py`
4. Start the frontend: `npm run serve`
5. Access at `http://localhost:8080`

### **New Dependencies**
- **Frontend**: `socket.io-client` for real-time WebSocket communication
- **Backend**: `flask-socketio` for WebSocket server functionality

## 📋 Usage Examples

### **Single Storage Usage**
- Open the app and start taking notes
- All notes are automatically saved to your storage
- No configuration or setup required

### **Multi-Storage Setup**
1. Generate a new storage ID on your primary storage
2. Copy the storage ID to your secondary storage
3. Use "Connect to User" to link the secondary storage
4. Both storages now share the same note collection

### **Real-Time Collaboration**
1. Multiple devices can connect using the same storage ID
2. Changes appear instantly across all connected devices
3. Visual indicators show active users and sync status
4. Automatic conflict resolution preserves all user work
5. Backup system ensures no data loss during conflicts

### **Storage Migration**
1. Click "Link New Storage" to generate a new ID
2. The old storage ID becomes invalid
3. Update all other storages with the new ID
4. All notes are automatically migrated

## 🔧 API Endpoints

All endpoints require a `storage_id` parameter for security:

### **REST API**
- `GET /api/tasks` - Retrieve tasks for a storage
- `POST /api/tasks` - Create a new task
- `PUT /api/tasks/{id}` - Update a task
- `DELETE /api/tasks/{id}` - Delete a task
- `POST /api/storage/migrate` - Migrate tasks between storages

### **WebSocket Events**
- `join_storage` - Join a storage room for real-time updates
- `leave_storage` - Leave a storage room
- `user_activity` - Broadcast user activity status
- `task_created` - Real-time task creation notifications
- `task_updated` - Real-time task update notifications
- `task_deleted` - Real-time task deletion notifications

## 🛡️ Security & Privacy

### **Data Protection**
- Each storage has completely isolated data
- No user authentication required
- Storage IDs are generated using browser fingerprinting
- Local storage uses obfuscation techniques

### **Access Control**
- Backend validates storage ownership for all operations
- No cross-storage data access possible
- Automatic storage ID regeneration for security
- Clear warnings about storage access implications

## 🌐 Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+
- Mobile browsers (iOS Safari, Chrome Mobile)

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📞 Support

For questions or support, please open an issue in the repository or contact the development team.
