from flask import Flask, request, jsonify, send_file
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from bson.objectid import ObjectId
import os
import base64
import uuid
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import azure_config
from azure_storage import azure_storage

# --- Check if running directly (local environment) ---
# If app.py is executed directly, set AzureEnvironment to False
if __name__ == '__main__':
    azure_config.AzureEnvironment = False

# --- App Initialization ---
app = Flask(__name__)

# --- Configuration ---
# Use Azure Cosmos DB if AzureEnvironment is True and COSMOS_DB_URI is configured
# Otherwise use local MongoDB
if azure_config.AzureEnvironment and azure_config.COSMOS_DB_URI:
    # Using Azure Cosmos DB
    MONGO_URI = os.getenv('MONGO_URI') or azure_config.COSMOS_DB_URI
    # Extract database name from URI or use configured name
    if azure_config.COSMOS_DB_NAME:
        if MONGO_URI and '/' not in MONGO_URI.split('@')[-1].split('?')[0]:
            MONGO_URI = f"{MONGO_URI.rstrip('/')}/{azure_config.COSMOS_DB_NAME}"
else:
    # Using local MongoDB
    MONGO_URI = os.getenv('MONGO_URI') or "mongodb://localhost:27017/tododb"
    
app.config["MONGO_URI"] = MONGO_URI

# Upload folder: Use local folder if Azure Storage not configured or not in Azure environment
app.config['UPLOAD_FOLDER'] = 'uploads' if (not azure_config.AzureEnvironment or not azure_storage.is_configured()) else None
app.config['MAX_CONTENT_LENGTH'] = azure_config.MAX_CONTENT_LENGTH

# Create upload directory if not using Azure Storage
if app.config['UPLOAD_FOLDER']:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mongo = PyMongo(app)

# --- CORS Configuration ---
if not azure_config.AzureEnvironment:
    # Local development: Allow all origins for CORS and Socket.IO
    CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": "*"}}, supports_credentials=True)
    socketio = SocketIO(
        app, 
        cors_allowed_origins=[],  # Empty list allows all origins
        async_mode='threading', 
        logger=True, 
        engineio_logger=True,
        allow_upgrades=True,
        transports=['websocket', 'polling'],
        ping_timeout=60,
        ping_interval=25
    )
    print("Running in LOCAL DEVELOPMENT mode - CORS and Socket.IO allow all origins")
else:
    # Azure environment: Use configured origins
    cors_origins_list = azure_config.CORS_ORIGINS if isinstance(azure_config.CORS_ORIGINS, list) else azure_config.CORS_ORIGINS.split(',')
    
    if '*' in cors_origins_list or len(cors_origins_list) == 1 and cors_origins_list[0] == '*':
        # Allow all origins
        CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": "*"}}, supports_credentials=True)
        socketio = SocketIO(app, cors_allowed_origins=[], async_mode='threading')
    else:
        # Use specific origins
        CORS(app, origins=cors_origins_list, supports_credentials=True)
        socketio = SocketIO(app, cors_allowed_origins=cors_origins_list, async_mode='threading')
    print(f"Running in AZURE environment - CORS origins: {cors_origins_list}")

# Define the 'tasks' collection from MongoDB
tasks_collection = mongo.db.tasks

# ---------------------------------
# Online connections by storage (Socket.IO based)
# Structure: storage_connections = { storage_id: set([sid, ...]) }
storage_connections = {}
# Track which storages a sid has joined to clean up on disconnect
sid_to_storages = {}

def update_and_broadcast_online_count(storage_id: str):
    room = f'storage_{storage_id}'
    connections = storage_connections.get(storage_id, set())
    count = len(connections)
    socketio.emit('storage_online_count', {
        'storage_id': storage_id,
        'count': count
    }, room=room)

# Helper function to serialize MongoDB documents for JSON
def serialize_document(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if not doc:
        return doc
    
    # Convert ObjectId to string
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    
    # Convert datetime objects to ISO strings
    for key, value in doc.items():
        if hasattr(value, 'isoformat'):  # datetime objects
            doc[key] = value.isoformat()
        elif isinstance(value, list):
            # Handle arrays (like attachments, audio_notes)
            for item in value:
                if isinstance(item, dict):
                    serialize_document(item)
    
    return doc

# --- WebSocket Event Handlers ---
@socketio.on('connect')
def on_connect():
    print('Client connected to Socket.IO')

@socketio.on('disconnect')
def on_disconnect():
    print('Client disconnected from Socket.IO')
    sid = request.sid
    # Remove sid from all storages it was part of
    storages = sid_to_storages.pop(sid, set())
    for storage_id in list(storages):
        s = storage_connections.get(storage_id)
        if s and sid in s:
            s.remove(sid)
            if not s:
                del storage_connections[storage_id]
            else:
                storage_connections[storage_id] = s
        update_and_broadcast_online_count(storage_id)

@socketio.on('join_storage')
def on_join_storage(data):
    storage_id = data.get('storage_id')
    print(f"DEBUG: User joining storage room: {storage_id}")
    if storage_id:
        room_name = f'storage_{storage_id}'
        print(f"DEBUG: Joining room: {room_name}")
        join_room(room_name)
        emit('joined_storage', {'storage_id': storage_id})
        print(f"DEBUG: User successfully joined storage room: {storage_id}")
        # Track active socket connections
        sid = request.sid
        storage_connections.setdefault(storage_id, set()).add(sid)
        sid_to_storages.setdefault(sid, set()).add(storage_id)
        # Broadcast updated count
        update_and_broadcast_online_count(storage_id)

@socketio.on('leave_storage')
def on_leave_storage(data):
    storage_id = data.get('storage_id')
    if storage_id:
        leave_room(f'storage_{storage_id}')
        sid = request.sid
        # Remove tracking
        s = storage_connections.get(storage_id)
        if s and sid in s:
            s.remove(sid)
            if not s:
                del storage_connections[storage_id]
            else:
                storage_connections[storage_id] = s
        if sid in sid_to_storages and storage_id in sid_to_storages[sid]:
            sid_to_storages[sid].remove(storage_id)
            if not sid_to_storages[sid]:
                del sid_to_storages[sid]
        update_and_broadcast_online_count(storage_id)

@socketio.on('user_activity')
def on_user_activity(data):
    storage_id = data.get('storage_id')
    user_id = data.get('user_id')
    activity = data.get('activity')  # 'editing', 'recording', 'idle'
    
    print(f"User activity: {user_id} is {activity} in storage {storage_id}")
    
    if storage_id and user_id:
        emit('user_activity_update', {
            'user_id': user_id,
            'activity': activity,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'storage_{storage_id}', include_self=False)

# --- API Endpoints (Routes) ---


# [READ] Get all tasks for a specific storage
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    tasks = []
    # Find all documents for the specific storage
    for task in tasks_collection.find({'storage_id': storage_id}):
        task['_id'] = str(task['_id'])
        # Convert datetime objects to ISO format strings
        if 'created_at' in task and task['created_at']:
            task['created_at'] = task['created_at'].isoformat()
        if 'updated_at' in task and task['updated_at']:
            task['updated_at'] = task['updated_at'].isoformat()
        tasks.append(task)
    return jsonify(tasks)

# [CREATE] Add a new task
@app.route('/api/tasks', methods=['POST'])
def add_task():
    task_data = request.get_json()
    storage_id = task_data.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    new_task = {
        'title': task_data['title'],
        'description': task_data.get('description', ''),
        'completed': task_data.get('completed', False),
        'storage_id': storage_id,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'attachments': task_data.get('attachments', []),
        'audio_notes': task_data.get('audio_notes', []),
        'is_backup': task_data.get('is_backup', False),
        'original_id': task_data.get('original_id'),
        'backup_reason': task_data.get('backup_reason')
    }
    result = tasks_collection.insert_one(new_task)
    # Find the newly created task to return it with its ID
    created_task = tasks_collection.find_one({'_id': result.inserted_id})
    # Serialize the document for JSON transmission
    created_task = serialize_document(created_task)
    
    # Emit real-time update to all clients in the storage room
    print(f"Emitting task_created event for storage: {storage_id}")
    socketio.emit('task_created', {
        'task': created_task,
        'storage_id': storage_id
    }, room=f'storage_{storage_id}')
    
    return jsonify(created_task)

# [UPDATE] Update a task's status (toggle completion)
@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    task_data = request.get_json()
    storage_id = task_data.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    # Verify the task belongs to the storage
    task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404
    
    update_data = {
        'updated_at': datetime.utcnow()
    }
    
    # Update completion status
    if 'completed' in task_data:
        update_data['completed'] = task_data['completed']
    
    # Update title and description
    if 'title' in task_data:
        update_data['title'] = task_data['title']
    if 'description' in task_data:
        update_data['description'] = task_data['description']
    
    # Update the document that matches the provided ObjectId and storage_id
    tasks_collection.update_one(
        {'_id': ObjectId(task_id), 'storage_id': storage_id},
        {'$set': update_data}
    )
    
    # Get updated task for real-time sync
    updated_task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    if updated_task:
        # Serialize the document for JSON transmission
        updated_task = serialize_document(updated_task)
        
        # Emit real-time update
        print(f"Emitting task_updated event for storage: {storage_id}")
        socketio.emit('task_updated', {
            'task': updated_task,
            'task_id': task_id,
            'storage_id': storage_id
        }, room=f'storage_{storage_id}')
    
    return jsonify({'message': 'Task updated successfully'})

# [DELETE] Delete a task
@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    # Verify the task belongs to the storage before deleting
    task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404
    
    # Delete the document that matches the provided ObjectId and storage_id
    tasks_collection.delete_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    
    # Emit real-time update
    print(f"Emitting task_deleted event for storage: {storage_id}")
    socketio.emit('task_deleted', {
        'task_id': task_id,
        'storage_id': storage_id
    }, room=f'storage_{storage_id}')
    
    return jsonify({'message': 'Task deleted successfully'})

# [SERVER INFO] Get server information including IP
@app.route('/api/server/info', methods=['GET'])
def get_server_info():
    import socket
    try:
        # Get the local IP address
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return jsonify({
            'server_ip': local_ip,
            'hostname': hostname,
            'port': 5000
        })
    except Exception as e:
        return jsonify({'error': f'Could not get server info: {str(e)}'}), 500

# [TEST] Test Socket.IO connection
@app.route('/api/test-socket', methods=['GET'])
def test_socket():
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    print(f"DEBUG: Testing Socket.IO connection for storage: {storage_id}")
    room_name = f'storage_{storage_id}'
    print(f"DEBUG: Emitting test event to room: {room_name}")
    
    # Emit a test event
    socketio.emit('test_event', {
        'message': 'Test from server',
        'storage_id': storage_id,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room_name)
    
    print(f"DEBUG: Test event emitted successfully to room: {room_name}")
    return jsonify({'message': 'Test event emitted', 'storage_id': storage_id})

# [DEVICE INFO] Get storage information for debugging
@app.route('/api/storage/info', methods=['GET'])
def get_storage_info():
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    # Get task count for this storage
    task_count = tasks_collection.count_documents({'storage_id': storage_id})
    
    return jsonify({
        'storage_id': storage_id,
        'task_count': task_count,
        'timestamp': datetime.utcnow().isoformat()
    })

# [ONLINE COUNT] Get current active websocket connections for a storage
@app.route('/api/storage/online-count', methods=['GET'])
def get_online_count():
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    count = len(storage_connections.get(storage_id, set()))
    return jsonify({
        'storage_id': storage_id,
        'count': count
    })

# [AGGREGATION] Get task statistics for a specific storage
# This endpoint demonstrates MongoDB's aggregation capabilities
@app.route('/api/tasks/stats', methods=['GET'])
def get_task_stats():
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    # Define an aggregation pipeline with storage filter
    pipeline = [
        {'$match': {'storage_id': storage_id}},  # Filter by storage_id first
        {
            '$group': {
                '_id': '$completed',  # Group documents by the 'completed' field
                'count': {'$sum': 1}    # Count the number of documents in each group
            }
        }
    ]
    stats = list(tasks_collection.aggregate(pipeline))
    
    # Format the result for easier frontend consumption
    result = {
        'completed': 0,
        'pending': 0
    }
    for stat in stats:
        if stat['_id'] == True:
            result['completed'] = stat['count']
        else:
            result['pending'] = stat['count']
            
    return jsonify(result)

# [FILE UPLOAD] Upload file to a task
@app.route('/api/tasks/<task_id>/upload', methods=['POST'])
def upload_file(task_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    storage_id = request.form.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    # Verify the task belongs to the storage
    task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        
        # Upload to Azure Storage if configured, otherwise use local storage
        if azure_storage.is_configured():
            upload_result = azure_storage.upload_file(file, filename)
            if upload_result:
                file_info = {
                    '_id': ObjectId(),
                    'filename': upload_result['filename'],
                    'unique_filename': upload_result['unique_filename'],
                    'blob_url': upload_result['blob_url'],
                    'uploaded_at': datetime.utcnow(),
                    'file_size': len(file.read()) if hasattr(file, 'read') else 0
                }
                # Reset file pointer
                if hasattr(file, 'seek'):
                    file.seek(0)
            else:
                return jsonify({'error': 'Failed to upload file to Azure Storage'}), 500
        else:
            # Local storage fallback
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            file_obj_id = ObjectId()
            file_info = {
                '_id': file_obj_id,
                'filename': filename,
                'unique_filename': unique_filename,
                'file_path': file_path,
                'uploaded_at': datetime.utcnow(),
                'file_size': os.path.getsize(file_path)
            }
        
        tasks_collection.update_one(
            {'_id': ObjectId(task_id), 'storage_id': storage_id},
            {'$push': {'attachments': file_info}, '$set': {'updated_at': datetime.utcnow()}}
        )
        
        # Convert ObjectId to string for JSON serialization
        file_info_json = {
            '_id': str(file_info['_id']),
            'filename': file_info['filename'],
            'unique_filename': file_info['unique_filename'],
            'blob_url': file_info.get('blob_url'),
            'file_path': file_info.get('file_path'),
            'uploaded_at': file_info['uploaded_at'].isoformat(),
            'file_size': file_info['file_size']
        }
        
        # Emit real-time update
        socketio.emit('task_updated', {
            'task_id': task_id,
            'storage_id': storage_id,
            'update_type': 'attachment_added',
            'file_info': file_info_json
        }, room=f'storage_{storage_id}')
        
        return jsonify({'message': 'File uploaded successfully', 'file_info': file_info})
    
    return jsonify({'error': 'File upload failed'}), 500

# [AUDIO UPLOAD] Upload audio note to a task
@app.route('/api/tasks/<task_id>/audio', methods=['POST'])
def upload_audio(task_id):
    data = request.get_json()
    if 'audio_data' not in data:
        return jsonify({'error': 'No audio data provided'}), 400
    
    storage_id = data.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    # Verify the task belongs to the storage
    task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404
    
    try:
        # Decode base64 audio data
        audio_data = base64.b64decode(data['audio_data'].split(',')[1])
        unique_filename = f"audio_{uuid.uuid4()}.webm"
        
        # Upload to Azure Storage if configured, otherwise use local storage
        if azure_storage.is_configured():
            from io import BytesIO
            audio_file = BytesIO(audio_data)
            upload_result = azure_storage.upload_file(audio_file, unique_filename)
            if upload_result:
                audio_info = {
                    '_id': ObjectId(),
                    'filename': upload_result['unique_filename'],
                    'blob_url': upload_result['blob_url'],
                    'recorded_at': datetime.utcnow(),
                    'duration': data.get('duration', 0),
                    'file_size': len(audio_data)
                }
            else:
                return jsonify({'error': 'Failed to upload audio to Azure Storage'}), 500
        else:
            # Local storage fallback
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            audio_obj_id = ObjectId()
            audio_info = {
                '_id': audio_obj_id,
                'filename': unique_filename,
                'file_path': file_path,
                'recorded_at': datetime.utcnow(),
                'duration': data.get('duration', 0),
                'file_size': len(audio_data)
            }
        
        tasks_collection.update_one(
            {'_id': ObjectId(task_id), 'storage_id': storage_id},
            {'$push': {'audio_notes': audio_info}, '$set': {'updated_at': datetime.utcnow()}}
        )
        
        # Convert ObjectId to string for JSON serialization
        audio_info_json = {
            '_id': str(audio_info['_id']),
            'filename': audio_info['filename'],
            'blob_url': audio_info.get('blob_url'),
            'file_path': audio_info.get('file_path'),
            'recorded_at': audio_info['recorded_at'].isoformat(),
            'duration': audio_info['duration'],
            'file_size': audio_info['file_size']
        }
        
        # Emit real-time update
        socketio.emit('task_updated', {
            'task_id': task_id,
            'storage_id': storage_id,
            'update_type': 'audio_added',
            'audio_info': audio_info_json
        }, room=f'storage_{storage_id}')
        
        return jsonify({'message': 'Audio uploaded successfully', 'audio_info': audio_info})
    
    except Exception as e:
        return jsonify({'error': f'Audio upload failed: {str(e)}'}), 500

# [FILE DOWNLOAD] Download uploaded file
@app.route('/api/files/<filename>')
def download_file(filename):
    if azure_storage.is_configured():
        # Get file URL from Azure Storage
        blob_url = azure_storage.get_file_url(filename)
        if blob_url:
            # Redirect to Azure blob URL
            from flask import redirect
            return redirect(blob_url, code=302)
        return jsonify({'error': 'File not found in Azure Storage'}), 404
    else:
        # Local storage fallback
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        return jsonify({'error': 'File not found'}), 404

# [AUDIO PLAY] Stream audio file
@app.route('/api/audio/<filename>')
def stream_audio(filename):
    if azure_storage.is_configured():
        # Get file URL from Azure Storage
        blob_url = azure_storage.get_file_url(filename)
        if blob_url:
            # Redirect to Azure blob URL
            from flask import redirect
            return redirect(blob_url, code=302)
        return jsonify({'error': 'Audio file not found in Azure Storage'}), 404
    else:
        # Local storage fallback
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='audio/webm')
        return jsonify({'error': 'Audio file not found'}), 404

# [DELETE ATTACHMENT] Delete file attachment
# Supports both subdocument ObjectId and unique_filename for backward compatibility
@app.route('/api/tasks/<task_id>/attachments/<attachment_id>', methods=['DELETE'])
def delete_attachment(task_id, attachment_id):
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404
    
    # Find and remove the attachment
    target = None
    match_by_object_id = False
    for attachment in task.get('attachments', []):
        # Match either by subdocument _id or by unique filename
        if str(attachment.get('_id', '')) == attachment_id:
            target = attachment
            match_by_object_id = True
            break
        if attachment.get('unique_filename') == attachment_id:
            target = attachment
            match_by_object_id = False
            break

    if target is None:
        return jsonify({'error': 'Attachment not found'}), 404

    # Delete file from storage (Azure or local)
    if azure_storage.is_configured() and target.get('unique_filename'):
        azure_storage.delete_file(target['unique_filename'])
    elif target.get('file_path') and os.path.exists(target['file_path']):
        os.remove(target['file_path'])

    # Remove from database
    if match_by_object_id and target.get('_id'):
        pull_query = {'_id': target['_id']}
    else:
        pull_query = {'unique_filename': target.get('unique_filename')}

    tasks_collection.update_one(
        {'_id': ObjectId(task_id), 'storage_id': storage_id},
        {'$pull': {'attachments': pull_query},
         '$set': {'updated_at': datetime.utcnow()}}
    )
    
    # Emit real-time update to notify other users
    updated_task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    if updated_task:
        print(f"DEBUG: Emitting attachment_deleted event for task {task_id} in storage {storage_id}")
        print(f"DEBUG: Updated task attachments count: {len(updated_task.get('attachments', []))}")
        room_name = f'storage_{storage_id}'
        print(f"DEBUG: Emitting to room: {room_name}")
        event_data = {
            'task': serialize_document(updated_task),
            'task_id': task_id,
            'storage_id': storage_id,
            'update_type': 'attachment_deleted'
        }
        print(f"DEBUG: Event data: {event_data}")
        socketio.emit('task_updated', event_data, room=room_name)
        print(f"DEBUG: Attachment deletion event emitted successfully to room {room_name}")
    
    return jsonify({'message': 'Attachment deleted successfully'})
    
    return jsonify({'error': 'Attachment not found'}), 404

# [DELETE AUDIO] Delete audio note
# Supports both subdocument ObjectId and filename for backward compatibility
@app.route('/api/tasks/<task_id>/audio/<audio_id>', methods=['DELETE'])
def delete_audio(task_id, audio_id):
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    
    task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404
    
    # Find and remove the audio note
    target = None
    match_by_object_id = False
    for audio in task.get('audio_notes', []):
        # Match either by subdocument _id or by stored filename
        if str(audio.get('_id', '')) == audio_id:
            target = audio
            match_by_object_id = True
            break
        if audio.get('filename') == audio_id:
            target = audio
            match_by_object_id = False
            break

    if target is None:
        return jsonify({'error': 'Audio note not found'}), 404

    # Delete file from storage (Azure or local)
    if azure_storage.is_configured() and target.get('filename'):
        azure_storage.delete_file(target['filename'])
    elif target.get('file_path') and os.path.exists(target['file_path']):
        os.remove(target['file_path'])

    # Remove from database
    if match_by_object_id and target.get('_id'):
        pull_query = {'_id': target['_id']}
    else:
        pull_query = {'filename': target.get('filename')}

    tasks_collection.update_one(
        {'_id': ObjectId(task_id), 'storage_id': storage_id},
        {'$pull': {'audio_notes': pull_query}, 
         '$set': {'updated_at': datetime.utcnow()}}
    )
    
    # Emit real-time update to notify other users
    updated_task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
    if updated_task:
        print(f"DEBUG: Emitting audio_deleted event for task {task_id} in storage {storage_id}")
        print(f"DEBUG: Updated task audio_notes count: {len(updated_task.get('audio_notes', []))}")
        socketio.emit('task_updated', {
            'task': serialize_document(updated_task),
            'task_id': task_id,
            'storage_id': storage_id,
            'update_type': 'audio_deleted'
        }, room=f'storage_{storage_id}')
        print(f"DEBUG: Audio deletion event emitted successfully")
    
    return jsonify({'message': 'Audio note deleted successfully'})

# [DEVICE MIGRATION] Migrate all tasks from old storage ID to new storage ID
@app.route('/api/storage/migrate', methods=['POST'])
def migrate_storage():
    data = request.get_json()
    old_storage_id = data.get('old_storage_id')
    new_storage_id = data.get('new_storage_id')
    
    if not old_storage_id or not new_storage_id:
        return jsonify({'error': 'Both old and new storage IDs are required'}), 400
    
    if old_storage_id == new_storage_id:
        return jsonify({'error': 'Old and new storage IDs must be different'}), 400
    
    try:
        # Find all tasks with the old storage ID
        old_tasks = list(tasks_collection.find({'storage_id': old_storage_id}))
        
        # Update all tasks to use the new storage ID (even if no tasks exist)
        result = tasks_collection.update_many(
            {'storage_id': old_storage_id},
            {'$set': {'storage_id': new_storage_id, 'updated_at': datetime.utcnow()}}
        )
        
        return jsonify({
            'success': True,
            'message': f'Successfully migrated {result.modified_count} tasks to new storage ID',
            'migrated_count': result.modified_count,
            'old_storage_id': old_storage_id,
            'new_storage_id': new_storage_id
        })
        
    except Exception as e:
        return jsonify({'error': f'Migration failed: {str(e)}'}), 500

# --- Run the Flask App ---
if __name__ == '__main__':
    socketio.run(app, debug=azure_config.FLASK_DEBUG, host='0.0.0.0', port=azure_config.PORT)