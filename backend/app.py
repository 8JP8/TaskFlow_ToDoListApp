from flask import Flask, request, jsonify, send_file
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from bson.objectid import ObjectId
import os
import base64
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

# --- App Initialization ---
app = Flask(__name__)

# --- Configuration ---
app.config["MONGO_URI"] = "mongodb://localhost:27017/tododb"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mongo = PyMongo(app)

# --- CORS Configuration ---
# Enable Cross-Origin Resource Sharing to allow the Vue.js frontend to communicate with this API
CORS(app)

# --- SocketIO Configuration ---
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Define the 'tasks' collection from MongoDB
tasks_collection = mongo.db.tasks

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

@socketio.on('join_storage')
def on_join_storage(data):
    storage_id = data.get('storage_id')
    print(f"User joining storage room: {storage_id}")
    if storage_id:
        join_room(f'storage_{storage_id}')
        emit('joined_storage', {'storage_id': storage_id})

@socketio.on('leave_storage')
def on_leave_storage(data):
    storage_id = data.get('storage_id')
    if storage_id:
        leave_room(f'storage_{storage_id}')

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
    
    # Emit a test event
    socketio.emit('test_event', {
        'message': 'Test from server',
        'storage_id': storage_id,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'storage_{storage_id}')
    
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
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Store file info in database (include subdocument _id for reliable deletion)
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
            '_id': str(file_obj_id),
            'filename': filename,
            'unique_filename': unique_filename,
            'file_path': file_path,
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
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        # Store audio info in database (include subdocument _id for reliable deletion)
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
            '_id': str(audio_obj_id),
            'filename': unique_filename,
            'file_path': file_path,
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
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

# [AUDIO PLAY] Stream audio file
@app.route('/api/audio/<filename>')
def stream_audio(filename):
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

    # Delete file from filesystem
    if os.path.exists(target['file_path']):
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

    # Delete file from filesystem
    if os.path.exists(target['file_path']):
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
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)