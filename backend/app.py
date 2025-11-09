import os
import sys
import uuid
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import azure_config
from azure_storage import azure_storage
import cors_config

# --- Check if running directly (local environment) ---
if __name__ == '__main__':
    azure_config.AzureEnvironment = False

# --- App Initialization ---
app = Flask(__name__, static_folder='static', static_url_path='')

# --- CORS Configuration ---
# Conditionally enable CORS based on USE_CORS configuration
if cors_config.USE_CORS:
    CORS(app, resources={
        r"/*": {
            "origins": cors_config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    print(f"✅ CORS enabled with origins: {cors_config.CORS_ORIGINS}")
else:
    print("⚠️ CORS is disabled")

# --- MongoDB Configuration ---
MONGO_URI = os.environ.get("MONGO_URI")
db_type = "environment variable"
if not MONGO_URI:
    if azure_config.AzureEnvironment and azure_config.COSMOS_DB_URI:
        MONGO_URI = azure_config.COSMOS_DB_URI
        db_type = "Azure Cosmos DB"
        if azure_config.COSMOS_DB_NAME and '/' not in MONGO_URI.split('@')[-1].split('?')[0]:
            MONGO_URI = f"{MONGO_URI.rstrip('/')}/{azure_config.COSMOS_DB_NAME}"
    else:
        MONGO_URI = "mongodb://localhost:27017/tododb"
        db_type = "local MongoDB"
app.config["MONGO_URI"] = MONGO_URI
print(f"📊 MongoDB URI source: {db_type}")

# --- Upload Folder Configuration ---
local_uploads_folder = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(local_uploads_folder, exist_ok=True)
if azure_config.AzureEnvironment and azure_storage.is_configured():
    app.config['UPLOAD_FOLDER'] = None
    print("☁️ Using Azure Storage for file uploads")
else:
    app.config['UPLOAD_FOLDER'] = local_uploads_folder
    print(f"📁 Using local storage: {local_uploads_folder}")
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("MAX_CONTENT_LENGTH", azure_config.MAX_CONTENT_LENGTH))

# --- Initialize PyMongo with error handling ---
try:
    mongo = PyMongo(app, serverSelectionTimeoutMS=10000, connectTimeoutMS=20000, socketTimeoutMS=20000, maxPoolSize=10, retryWrites=False)
    mongo.db.command('ping')
    tasks_collection = mongo.db.tasks
    print("="*60)
    print("✅ MongoDB/Cosmos DB connection established")
    print(f"📊 Database: {mongo.db.name}")
    print(f"🔗 Connection Type: {db_type}")
    print(f"🌍 Environment: {os.environ.get('WEBSITE_SITE_NAME', 'local')}")
    print(f"📍 MongoDB URI: {MONGO_URI.split('@')[0] if '@' in MONGO_URI else MONGO_URI.split('//')[1].split('/')[0] if '//' in MONGO_URI else 'hidden'}...")
    print("="*60)
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    print("="*60, f"❌ MongoDB connection error: {e}", "="*60, sep="\n")
    tasks_collection = None
except Exception as e:
    print(f"⚠️ MongoDB initialization warning: {e}")
    tasks_collection = None

# --- SocketIO Configuration ---
# Determine async_mode based on environment and available packages
# For Azure/production: use eventlet if available
# For local development: use threading (default, no extra packages needed)
async_mode = 'threading'  # Default fallback

# Check if eventlet is available
try:
    import eventlet  # noqa: F401
    eventlet_available = True
except ImportError:
    eventlet_available = False

if azure_config.AzureEnvironment:
    # Azure/production: prefer eventlet if available
    if eventlet_available:
        async_mode = 'eventlet'
        print("✅ Using eventlet for Socket.IO (Azure/production mode)")
    else:
        async_mode = 'threading'
        print("⚠️ eventlet not available, using threading for Socket.IO")
else:
    # Local development: default to threading, but allow eventlet override
    use_eventlet = os.environ.get('USE_EVENTLET', '').lower() in ('true', '1', 'yes')
    if eventlet_available and use_eventlet:
        async_mode = 'eventlet'
        print("✅ Using eventlet for Socket.IO (local development)")
    else:
        async_mode = 'threading'
        print("✅ Using threading for Socket.IO (local development)")

socketio = SocketIO(
    app,
    cors_allowed_origins=cors_config.SOCKETIO_CORS_ORIGINS if cors_config.USE_CORS else None,
    async_mode=async_mode,
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

if cors_config.USE_CORS:
    print(f"🔌 Socket.IO CORS enabled with origins: {cors_config.SOCKETIO_CORS_ORIGINS}")
else:
    print("⚠️ Socket.IO CORS is disabled")

# --- Helper Functions & State ---
storage_connections = {}
sid_to_storages = {}

def update_and_broadcast_online_count(storage_id: str):
    room = f'storage_{storage_id}'
    count = len(storage_connections.get(storage_id, set()))
    print(f"📊 Broadcasting online count for storage {storage_id[:8]}...: {count} users")
    socketio.emit('storage_online_count', {'storage_id': storage_id, 'count': count}, room=room)

def serialize_document(doc):
    if not doc: return doc
    if '_id' in doc: doc['_id'] = str(doc['_id'])
    for key, value in doc.items():
        if hasattr(value, 'isoformat'):
            doc[key] = value.isoformat()
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict): serialize_document(item)
    return doc

def check_db_connection():
    if tasks_collection is None: return jsonify({'error':'Database not available'}), 503
    try:
        mongo.db.command('ping')
        return None
    except Exception as e:
        print(f"❌ Database connection lost: {e}")
        return jsonify({'error': 'Database connection lost'}), 503

def toIdString(id_val):
    """Convert various ID formats to string"""
    if id_val is None:
        return ''
    if isinstance(id_val, ObjectId):
        return str(id_val)
    if isinstance(id_val, str):
        return id_val
    return str(id_val)

# --- Static & Health Routes ---
@app.route('/')
def index(): return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join('static', path)): return send_from_directory('static', path)
    return send_from_directory('static', 'index.html')

@app.route('/health')
def health():
    db_status = 'disconnected'
    db_error = None
    if tasks_collection is not None:
        try:
            mongo.db.command('ping')
            db_status = 'connected'
        except Exception as e:
            db_status = 'error'
            db_error = str(e)
    return jsonify({
        'status': 'healthy' if db_status == 'connected' else 'degraded',
        'mongodb': db_status,
        'error': db_error,
        'environment': os.environ.get('WEBSITE_SITE_NAME', 'local')
    })

@app.route('/api/diagnostic', methods=['GET'])
def diagnostic():
    diagnostics = {
        'server': 'running',
        'timestamp': datetime.utcnow().isoformat(),
        'environment': os.environ.get('WEBSITE_SITE_NAME', 'local'),
        'python_version': sys.version,
        'mongodb': {
            'configured': tasks_collection is not None,
            'connection_string_prefix': MONGO_URI[:50] + '...' if MONGO_URI else 'None'
        },
        'azure_storage': azure_storage.get_container_info()
    }
    if tasks_collection is not None:
        try:
            mongo.db.command('ping')
            diagnostics['mongodb'].update({
                'status': 'connected',
                'database': mongo.db.name,
                'collections': mongo.db.list_collection_names(),
                'task_count': mongo.db.tasks.count_documents({})
            })
        except Exception as e:
            diagnostics['mongodb'].update({'status': 'error', 'error': str(e)})
    else:
        diagnostics['mongodb']['status'] = 'not configured'
    
    # Add Azure Storage file list if configured
    if azure_storage.is_configured():
        files = azure_storage.list_files(max_results=50)
        if files is not None:
            diagnostics['azure_storage']['files'] = files
            diagnostics['azure_storage']['file_count'] = len(files)
    
    return jsonify(diagnostics)

@app.route('/api/storage/files', methods=['GET'])
def list_storage_files():
    """List all files in Azure Storage container"""
    try:
        if not azure_storage.is_configured():
            return jsonify({
                'error': 'Azure Storage not configured',
                'info': azure_storage.get_container_info()
            }), 404
        
        max_results = int(request.args.get('max', 100))
        files = azure_storage.list_files(max_results=max_results)
        
        if files is None:
            return jsonify({'error': 'Failed to list files'}), 500
        
        container_info = azure_storage.get_container_info()
        return jsonify({
            'container': container_info.get('container_name'),
            'account': container_info.get('account_name'),
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        print(f"❌ Error listing storage files: {e}")
        return jsonify({'error': f'Failed to list files: {str(e)}'}), 500

# --- SocketIO Handlers (FIXED & VERIFIED for real-time user count) ---
@socketio.on('connect')
def on_connect():
    print(f'✅ Client connected: {request.sid}')

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    print(f"👋 Client disconnected: {sid}")
    storages = sid_to_storages.pop(sid, set())
    for storage_id in list(storages):
        s = storage_connections.get(storage_id)
        if s and sid in s:
            s.remove(sid)
            if not s: del storage_connections[storage_id]
        # This broadcast is crucial for real-time updates
        update_and_broadcast_online_count(storage_id)

@socketio.on('join_storage')
def on_join_storage(data):
    storage_id = data.get('storage_id')
    if storage_id:
        print(f"🔌 Client {request.sid} joining storage room: {storage_id[:8]}...")
        join_room(f'storage_{storage_id}')
        sid = request.sid
        storage_connections.setdefault(storage_id, set()).add(sid)
        sid_to_storages.setdefault(sid, set()).add(storage_id)
        print(f"📊 Storage {storage_id[:8]}... now has {len(storage_connections[storage_id])} connection(s)")
        update_and_broadcast_online_count(storage_id)
        emit('joined_storage', {'storage_id': storage_id})

@socketio.on('leave_storage')
def on_leave_storage(data):
    storage_id = data.get('storage_id')
    if storage_id:
        leave_room(f'storage_{storage_id}')
        sid = request.sid
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
    storage_id, user_id, activity = data.get('storage_id'), data.get('user_id'), data.get('activity')
    if storage_id and user_id:
        emit('user_activity_update', {'user_id': user_id, 'activity': activity, 'timestamp': datetime.utcnow().isoformat()}, room=f'storage_{storage_id}', include_self=False)

# --- Task API Endpoints ---
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    db_check = check_db_connection()
    if db_check:
        return db_check
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    try:
        tasks = [serialize_document(task) for task in tasks_collection.find({'storage_id': storage_id})]
        return jsonify(tasks)
    except Exception as e:
        print(f"❌ Error fetching tasks: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to fetch tasks: {str(e)}'}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    db_check = check_db_connection()
    if db_check:
        return db_check
    try:
        data = request.get_json()
        storage_id = data.get('storage_id')
        if not storage_id:
            return jsonify({'error': 'Storage ID is required'}), 400
        
        task_data = {
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'completed': False,
            'storage_id': storage_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'attachments': [],
            'audio_notes': [],
            'is_backup': data.get('is_backup', False),
            'original_id': data.get('original_id'),
            'backup_reason': data.get('backup_reason')
        }
        
        result = tasks_collection.insert_one(task_data)
        task_data['_id'] = str(result.inserted_id)
        
        # Emit Socket.IO event for real-time sync
        print(f"📤 Emitting task_created event to room storage_{storage_id[:8]}...")
        socketio.emit('task_created', {
            'task': serialize_document(task_data),
            'storage_id': storage_id
        }, room=f'storage_{storage_id}')
        
        return jsonify(serialize_document(task_data)), 201
    except Exception as e:
        print(f"❌ Error creating task: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create task: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    db_check = check_db_connection()
    if db_check:
        return db_check
    try:
        data = request.get_json()
        storage_id = data.get('storage_id')
        if not storage_id:
            return jsonify({'error': 'Storage ID is required'}), 400
        
        # Find the task to ensure it exists and belongs to the storage
        task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Build update data
        update_data = {'updated_at': datetime.utcnow()}
        if 'title' in data:
            update_data['title'] = data['title']
        if 'description' in data:
            update_data['description'] = data.get('description', '')
        if 'completed' in data:
            update_data['completed'] = data['completed']
        
        # Update the task
        tasks_collection.update_one(
            {'_id': ObjectId(task_id), 'storage_id': storage_id},
            {'$set': update_data}
        )
        
        # Fetch updated task
        updated_task = tasks_collection.find_one({'_id': ObjectId(task_id)})
        
        # Emit Socket.IO event for real-time sync
        update_type = 'completed' if 'completed' in data else 'updated'
        print(f"📤 Emitting task_updated event (type: {update_type}) to room storage_{storage_id[:8]}...")
        socketio.emit('task_updated', {
            'task': serialize_document(updated_task),
            'storage_id': storage_id,
            'update_type': update_type
        }, room=f'storage_{storage_id}')
        
        return jsonify(serialize_document(updated_task))
    except Exception as e:
        print(f"❌ Error updating task: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to update task: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    db_check = check_db_connection()
    if db_check:
        return db_check
    try:
        storage_id = request.args.get('storage_id')
        if not storage_id:
            return jsonify({'error': 'Storage ID is required'}), 400
        
        # Find the task to ensure it exists and belongs to the storage
        task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Delete the task
        tasks_collection.delete_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
        
        # Emit Socket.IO event for real-time sync
        print(f"📤 Emitting task_deleted event to room storage_{storage_id[:8]}...")
        socketio.emit('task_deleted', {
            'task_id': task_id,
            'storage_id': storage_id
        }, room=f'storage_{storage_id}')
        
        return jsonify({'message': 'Task deleted successfully'})
    except Exception as e:
        print(f"❌ Error deleting task: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to delete task: {str(e)}'}), 500

@app.route('/api/tasks/stats', methods=['GET'])
def get_task_stats():
    db_check = check_db_connection()
    if db_check:
        return db_check
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    try:
        completed = tasks_collection.count_documents({'storage_id': storage_id, 'completed': True})
        pending = tasks_collection.count_documents({'storage_id': storage_id, 'completed': False})
        return jsonify({'completed': completed, 'pending': pending})
    except Exception as e:
        print(f"❌ Error fetching task stats: {e}")
        return jsonify({'error': f'Failed to fetch task stats: {str(e)}'}), 500

@app.route('/api/storage/online-count', methods=['GET'])
def get_online_count():
    storage_id = request.args.get('storage_id')
    if not storage_id:
        return jsonify({'error': 'Storage ID is required'}), 400
    try:
        count = len(storage_connections.get(storage_id, set()))
        return jsonify({'count': count, 'storage_id': storage_id})
    except Exception as e:
        print(f"❌ Error fetching online count: {e}")
        return jsonify({'error': f'Failed to fetch online count: {str(e)}'}), 500

@app.route('/api/test-socket', methods=['GET'])
def test_socket():
    storage_id = request.args.get('storage_id')
    return jsonify({'status': 'ok', 'storage_id': storage_id, 'message': 'Socket.IO endpoint is working'})

@app.route('/api/server/info', methods=['GET'])
def server_info():
    """Return server information for frontend auto-detection"""
    import socket
    try:
        # Get the server's IP address
        hostname = socket.gethostname()
        server_ip = socket.gethostbyname(hostname)
        # Try to get a more accessible IP (sometimes gethostbyname returns 127.0.0.1)
        if server_ip == '127.0.0.1':
            # Try to get actual local network IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Connect to a dummy address to determine local IP
                s.connect(('8.8.8.8', 80))
                server_ip = s.getsockname()[0]
            except Exception:
                pass
            finally:
                s.close()
    except Exception:
        server_ip = 'localhost'
    
    return jsonify({
        'server_ip': server_ip,
        'environment': os.environ.get('WEBSITE_SITE_NAME', 'local'),
        'mongodb_configured': tasks_collection is not None,
        'database_name': mongo.db.name if tasks_collection is not None else None
    })

# --- File and Media Endpoints ---
@app.route('/api/tasks/<task_id>/upload', methods=['POST'])
def upload_file(task_id):
    db_check = check_db_connection()
    if db_check:
        return db_check
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        storage_id = request.form.get('storage_id')
        if not storage_id:
            return jsonify({'error': 'Storage ID is required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Find the task to ensure it exists and belongs to the storage
        task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Upload file (Azure or local)
        # Get file size before upload
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        print(f"📤 File upload request:")
        print(f"   📋 Original filename: {file.filename}")
        print(f"   📏 File size: {file_size} bytes")
        print(f"   🔧 Azure Storage configured: {azure_storage.is_configured()}")
        print(f"   🌍 Azure Environment: {azure_config.AzureEnvironment}")
        
        if azure_storage.is_configured():
            print(f"   ☁️ Using Azure Storage for upload")
            upload_result = azure_storage.upload_file(file)
            if not upload_result:
                print(f"❌ Azure Storage upload returned None")
                return jsonify({'error': 'Failed to upload file to Azure Storage'}), 500
            print(f"   ✅ Upload result received: {upload_result.get('unique_filename')}")
            file_info = {
                '_id': str(uuid.uuid4()),
                'filename': upload_result.get('filename'),
                'unique_filename': upload_result.get('unique_filename'),
                'blob_url': upload_result.get('blob_url'),
                'uploaded_at': datetime.utcnow().isoformat(),
                'size': file_size
            }
        else:
            # Local file storage
            print(f"   📁 Using local file storage")
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            unique_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            filepath = os.path.join(upload_folder, unique_filename)
            print(f"   📍 Saving to: {filepath}")
            file.save(filepath)
            print(f"   ✅ File saved locally")
            file_info = {
                '_id': str(uuid.uuid4()),
                'filename': secure_filename(file.filename),
                'unique_filename': unique_filename,
                'uploaded_at': datetime.utcnow().isoformat(),
                'size': os.path.getsize(filepath)
            }
        
        # Add attachment to task
        tasks_collection.update_one(
            {'_id': ObjectId(task_id), 'storage_id': storage_id},
            {'$push': {'attachments': file_info}, '$set': {'updated_at': datetime.utcnow()}}
        )
        
        # Fetch updated task
        updated_task = tasks_collection.find_one({'_id': ObjectId(task_id)})
        
        # Emit Socket.IO event for real-time sync
        socketio.emit('task_updated', {
            'task': serialize_document(updated_task),
            'storage_id': storage_id,
            'update_type': 'attachment_added'
        }, room=f'storage_{storage_id}')
        
        return jsonify({'file_info': file_info})
    except Exception as e:
        print(f"❌ Error uploading file: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to upload file: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>/audio', methods=['POST'])
def upload_audio(task_id):
    db_check = check_db_connection()
    if db_check:
        return db_check
    try:
        data = request.get_json()
        storage_id = data.get('storage_id')
        if not storage_id:
            return jsonify({'error': 'Storage ID is required'}), 400
        
        audio_data = data.get('audio_data')
        duration = data.get('duration', 0)
        
        if not audio_data:
            return jsonify({'error': 'Audio data is required'}), 400
        
        # Find the task to ensure it exists and belongs to the storage
        task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Decode base64 audio data
        try:
            audio_bytes = base64.b64decode(audio_data.split(',')[-1] if ',' in audio_data else audio_data)
        except Exception as e:
            return jsonify({'error': f'Invalid audio data: {str(e)}'}), 400
        
        # Upload audio file (Azure or local)
        unique_filename = f"audio_{uuid.uuid4()}.webm"
        
        print(f"🎤 Audio upload request:")
        print(f"   📏 Audio size: {len(audio_bytes)} bytes")
        print(f"   🔧 Azure Storage configured: {azure_storage.is_configured()}")
        print(f"   🌍 Azure Environment: {azure_config.AzureEnvironment}")
        
        if azure_storage.is_configured():
            print(f"   ☁️ Using Azure Storage for audio upload")
            from io import BytesIO
            audio_file = BytesIO(audio_bytes)
            audio_file.name = unique_filename
            upload_result = azure_storage.upload_file(audio_file, filename=unique_filename)
            if not upload_result:
                print(f"❌ Azure Storage audio upload returned None")
                return jsonify({'error': 'Failed to upload audio to Azure Storage'}), 500
            print(f"   ✅ Audio upload result received: {upload_result.get('unique_filename')}")
            audio_info = {
                '_id': str(uuid.uuid4()),
                'filename': upload_result.get('filename', unique_filename),
                'unique_filename': upload_result.get('unique_filename'),
                'blob_url': upload_result.get('blob_url'),
                'duration': duration,
                'recorded_at': datetime.utcnow().isoformat(),
                'size': len(audio_bytes)
            }
            print(f"   📋 Audio info saved to DB: filename={audio_info['filename']}, unique_filename={audio_info['unique_filename']}")
            print(f"   🔗 Blob URL: {audio_info['blob_url']}")
        else:
            # Local file storage
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, unique_filename)
            with open(filepath, 'wb') as f:
                f.write(audio_bytes)
            audio_info = {
                '_id': str(uuid.uuid4()),
                'filename': unique_filename,
                'unique_filename': unique_filename,
                'duration': duration,
                'recorded_at': datetime.utcnow().isoformat(),
                'size': len(audio_bytes)
            }
        
        # Add audio recording to task
        tasks_collection.update_one(
            {'_id': ObjectId(task_id), 'storage_id': storage_id},
            {'$push': {'audio_notes': audio_info}, '$set': {'updated_at': datetime.utcnow()}}
        )
        
        # Fetch updated task
        updated_task = tasks_collection.find_one({'_id': ObjectId(task_id)})
        
        # Emit Socket.IO event for real-time sync
        socketio.emit('task_updated', {
            'task': serialize_document(updated_task),
            'storage_id': storage_id,
            'update_type': 'audio_added'
        }, room=f'storage_{storage_id}')
        
        return jsonify({'audio_info': audio_info})
    except Exception as e:
        print(f"❌ Error uploading audio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to upload audio: {str(e)}'}), 500

@app.route('/api/files/<filename>', methods=['GET'])
def download_file(filename):
    try:
        if azure_storage.is_configured():
            # Get file from Azure Blob Storage
            blob_url = azure_storage.get_file_url(filename)
            if not blob_url:
                return jsonify({'error': 'File not found'}), 404
            # Return redirect to Azure blob URL
            from flask import redirect
            return redirect(blob_url)
        else:
            # Local file storage
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            filepath = os.path.join(upload_folder, filename)
            if not os.path.exists(filepath):
                return jsonify({'error': 'File not found'}), 404
            return send_file(filepath, as_attachment=True)
    except Exception as e:
        print(f"❌ Error downloading file: {e}")
        return jsonify({'error': f'Failed to download file: {str(e)}'}), 500

@app.route('/api/audio/<filename>', methods=['GET'])
def stream_audio(filename):
    """Stream audio file from Azure Storage or local storage"""
    try:
        if azure_storage.is_configured():
            # Get audio file from Azure Blob Storage
            blob_url = azure_storage.get_file_url(filename)
            if not blob_url:
                return jsonify({'error': 'Audio file not found'}), 404
            # Return redirect to Azure blob URL
            from flask import redirect
            return redirect(blob_url)
        else:
            # Local file storage
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            filepath = os.path.join(upload_folder, filename)
            if not os.path.exists(filepath):
                return jsonify({'error': 'Audio file not found'}), 404
            # Stream audio file with proper content type
            return send_file(filepath, mimetype='audio/webm')
    except Exception as e:
        print(f"❌ Error streaming audio: {e}")
        return jsonify({'error': f'Failed to stream audio: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>/attachments/<attachment_id>', methods=['DELETE'])
def delete_attachment(task_id, attachment_id):
    db_check = check_db_connection()
    if db_check:
        return db_check
    try:
        storage_id = request.args.get('storage_id')
        if not storage_id:
            return jsonify({'error': 'Storage ID is required'}), 400
        
        # Find the task
        task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Find the attachment
        attachments = task.get('attachments', [])
        attachment = None
        for att in attachments:
            att_id = toIdString(att.get('_id', ''))
            if att_id == attachment_id or att.get('unique_filename') == attachment_id:
                attachment = att
                break
        
        if not attachment:
            return jsonify({'error': 'Attachment not found'}), 404
        
        # Delete file from storage
        unique_filename = attachment.get('unique_filename')
        if unique_filename:
            if azure_storage.is_configured():
                azure_storage.delete_file(unique_filename)
            else:
                upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
                filepath = os.path.join(upload_folder, unique_filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
        
        # Remove attachment from task
        tasks_collection.update_one(
            {'_id': ObjectId(task_id), 'storage_id': storage_id},
            {'$pull': {'attachments': {'_id': attachment.get('_id')}}, '$set': {'updated_at': datetime.utcnow()}}
        )
        
        # Fetch updated task
        updated_task = tasks_collection.find_one({'_id': ObjectId(task_id)})
        
        # Emit Socket.IO event for real-time sync
        socketio.emit('task_updated', {
            'task': serialize_document(updated_task),
            'storage_id': storage_id,
            'update_type': 'attachment_deleted'
        }, room=f'storage_{storage_id}')
        
        return jsonify({'message': 'Attachment deleted successfully'})
    except Exception as e:
        print(f"❌ Error deleting attachment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to delete attachment: {str(e)}'}), 500

@app.route('/api/tasks/<task_id>/audio/<audio_id>', methods=['DELETE'])
def delete_audio(task_id, audio_id):
    db_check = check_db_connection()
    if db_check:
        return db_check
    try:
        storage_id = request.args.get('storage_id')
        if not storage_id:
            return jsonify({'error': 'Storage ID is required'}), 400
        
        # Find the task
        task = tasks_collection.find_one({'_id': ObjectId(task_id), 'storage_id': storage_id})
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Find the audio recording
        audio_notes = task.get('audio_notes', [])
        audio = None
        for aud in audio_notes:
            aud_id = toIdString(aud.get('_id', ''))
            if aud_id == audio_id or aud.get('unique_filename') == audio_id:
                audio = aud
                break
        
        if not audio:
            return jsonify({'error': 'Audio recording not found'}), 404
        
        # Delete file from storage
        unique_filename = audio.get('unique_filename')
        if unique_filename:
            if azure_storage.is_configured():
                azure_storage.delete_file(unique_filename)
            else:
                upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
                filepath = os.path.join(upload_folder, unique_filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
        
        # Remove audio recording from task
        tasks_collection.update_one(
            {'_id': ObjectId(task_id), 'storage_id': storage_id},
            {'$pull': {'audio_notes': {'_id': audio.get('_id')}}, '$set': {'updated_at': datetime.utcnow()}}
        )
        
        # Fetch updated task
        updated_task = tasks_collection.find_one({'_id': ObjectId(task_id)})
        
        # Emit Socket.IO event for real-time sync
        socketio.emit('task_updated', {
            'task': serialize_document(updated_task),
            'storage_id': storage_id,
            'update_type': 'audio_deleted'
        }, room=f'storage_{storage_id}')
        
        return jsonify({'message': 'Audio recording deleted successfully'})
    except Exception as e:
        print(f"❌ Error deleting audio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to delete audio: {str(e)}'}), 500

@app.route('/api/storage/migrate', methods=['POST'])
def migrate_storage():
    db_check = check_db_connection()
    if db_check:
        return db_check
    try:
        data = request.get_json()
        old_storage_id = data.get('old_storage_id')
        new_storage_id = data.get('new_storage_id')
        
        if not old_storage_id or not new_storage_id:
            return jsonify({'error': 'Both old_storage_id and new_storage_id are required'}), 400
        
        if old_storage_id == new_storage_id:
            return jsonify({'error': 'Old and new storage IDs must be different'}), 400
        
        # Migrate all tasks from old storage to new storage
        result = tasks_collection.update_many(
            {'storage_id': old_storage_id},
            {'$set': {'storage_id': new_storage_id, 'updated_at': datetime.utcnow()}}
        )
        
        # Migrate socket connections
        if old_storage_id in storage_connections:
            old_connections = storage_connections.pop(old_storage_id, set())
            storage_connections.setdefault(new_storage_id, set()).update(old_connections)
            
            # Update sid_to_storages mapping
            for sid in old_connections:
                if sid in sid_to_storages:
                    sid_to_storages[sid].discard(old_storage_id)
                    sid_to_storages[sid].add(new_storage_id)
        
        # Update broadcast counts
        update_and_broadcast_online_count(new_storage_id)
        
        return jsonify({
            'success': True,
            'message': f'Migration completed successfully',
            'tasks_migrated': result.modified_count
        })
    except Exception as e:
        print(f"❌ Error migrating storage: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to migrate storage: {str(e)}'}), 500

# --- Run Flask App ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on http://0.0.0.0:{port}")
    socketio.run(app, debug=True, host='0.0.0.0', port=port)
