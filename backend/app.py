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
# If app.py is executed directly, set AzureEnvironment to False
if __name__ == '__main__':
    azure_config.AzureEnvironment = False

# --- App Initialization ---
app = Flask(__name__, static_folder='static', static_url_path='')

# --- MongoDB Configuration ---
# Use Azure Cosmos DB if AzureEnvironment is True and COSMOS_DB_URI is configured
# Otherwise use MONGO_URI from environment or local MongoDB
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    if azure_config.AzureEnvironment and azure_config.COSMOS_DB_URI:
        # Using Azure Cosmos DB
        MONGO_URI = azure_config.COSMOS_DB_URI
        # Extract database name from URI or use configured name
        if azure_config.COSMOS_DB_NAME:
            if MONGO_URI and '/' not in MONGO_URI.split('@')[-1].split('?')[0]:
                MONGO_URI = f"{MONGO_URI.rstrip('/')}/{azure_config.COSMOS_DB_NAME}"
    else:
        # Using local MongoDB
        MONGO_URI = "mongodb://localhost:27017/tododb"

app.config["MONGO_URI"] = MONGO_URI

# --- Upload Folder Configuration ---
# Use local folder if Azure Storage not configured or not in Azure environment
if not azure_config.AzureEnvironment or not azure_storage.is_configured():
    app.config['UPLOAD_FOLDER'] = 'uploads'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
else:
    app.config['UPLOAD_FOLDER'] = None  # Use Azure Storage

app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("MAX_CONTENT_LENGTH", azure_config.MAX_CONTENT_LENGTH))

# --- Initialize PyMongo with error handling ---
try:
    mongo = PyMongo(
        app,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=20000,
        socketTimeoutMS=20000,
        maxPoolSize=10,
        retryWrites=False
    )
    mongo.db.command('ping')
    tasks_collection = mongo.db.tasks
    print("="*60)
    print("✅ MongoDB/Cosmos DB connection established")
    print(f"📊 Database: {mongo.db.name}")
    print(f"🌍 Environment: {os.environ.get('WEBSITE_SITE_NAME', 'local')}")
    print("="*60)
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    print("="*60)
    print(f"❌ MongoDB connection error: {e}")
    tasks_collection = None
except Exception as e:
    print(f"⚠️ MongoDB initialization warning: {e}")
    tasks_collection = None

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

# --- SocketIO Configuration ---
socketio = SocketIO(
    app,
    cors_allowed_origins=cors_config.SOCKETIO_CORS_ORIGINS if cors_config.USE_CORS else None,
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

if cors_config.USE_CORS:
    print(f"🔌 Socket.IO CORS enabled with origins: {cors_config.SOCKETIO_CORS_ORIGINS}")
else:
    print("⚠️ Socket.IO CORS is disabled")

# --- Online connections storage ---
storage_connections = {}
sid_to_storages = {}

def update_and_broadcast_online_count(storage_id: str):
    room = f'storage_{storage_id}'
    count = len(storage_connections.get(storage_id, set()))
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

# --- Health & Diagnostic ---
@app.route('/health')
def health():
    db_status = 'disconnected'
    db_error = None
    if tasks_collection is not None:
        try: mongo.db.command('ping'); db_status = 'connected'
        except Exception as e: db_status='error'; db_error=str(e)
    return jsonify({'status':'healthy' if db_status=='connected' else 'degraded',
                    'mongodb': db_status, 'error': db_error,
                    'environment': os.environ.get('WEBSITE_SITE_NAME','local')})

@app.route('/api/diagnostic', methods=['GET'])
def diagnostic():
    diagnostics = {
        'server':'running',
        'timestamp':datetime.utcnow().isoformat(),
        'environment':os.environ.get('WEBSITE_SITE_NAME','local'),
        'python_version':sys.version,
        'mongodb': {'configured': tasks_collection is not None,
                    'connection_string_prefix': MONGO_URI[:50]+'...' if MONGO_URI else 'None'}
    }
    if tasks_collection is not None:
        try:
            mongo.db.command('ping')
            diagnostics['mongodb'].update({'status':'connected','database':mongo.db.name,'collections':mongo.db.list_collection_names(),'task_count':mongo.db.tasks.count_documents({})})
        except Exception as e:
            diagnostics['mongodb'].update({'status':'error','error':str(e)})
    else:
        diagnostics['mongodb']['status'] = 'not configured'
    return jsonify(diagnostics)

# --- Static frontend ---
@app.route('/')
def index(): return send_from_directory('static','index.html')
@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join('static',path)): return send_from_directory('static',path)
    return send_from_directory('static','index.html')

# --- SocketIO handlers ---
@socketio.on('connect')
def on_connect(): print(f'✅ Client connected: {request.sid}')
@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    print(f"👋 Client disconnected: {sid}")
    storages = sid_to_storages.pop(sid,set())
    for storage_id in list(storages):
        s = storage_connections.get(storage_id)
        if s and sid in s: s.remove(sid)
        if not s: del storage_connections[storage_id]
        update_and_broadcast_online_count(storage_id)
@socketio.on('join_storage')
def on_join_storage(data):
    storage_id = data.get('storage_id')
    if storage_id:
        join_room(f'storage_{storage_id}')
        sid = request.sid
        storage_connections.setdefault(storage_id,set()).add(sid)
        sid_to_storages.setdefault(sid,set()).add(storage_id)
        update_and_broadcast_online_count(storage_id)
        emit('joined_storage', {'storage_id': storage_id})
@socketio.on('leave_storage')
def on_leave_storage(data):
    storage_id = data.get('storage_id')
    if storage_id:
        leave_room(f'storage_{storage_id}')
        sid = request.sid
        s = storage_connections.get(storage_id)
        if s and sid in s: s.remove(sid)
        if not s: del storage_connections[storage_id]
        else: storage_connections[storage_id]=s
        if sid in sid_to_storages and storage_id in sid_to_storages[sid]:
            sid_to_storages[sid].remove(storage_id)
            if not sid_to_storages[sid]: del sid_to_storages[sid]
        update_and_broadcast_online_count(storage_id)
@socketio.on('user_activity')
def on_user_activity(data):
    storage_id, user_id, activity = data.get('storage_id'), data.get('user_id'), data.get('activity')
    if storage_id and user_id:
        emit('user_activity_update',{'user_id':user_id,'activity':activity,'timestamp':datetime.utcnow().isoformat()},
             room=f'storage_{storage_id}', include_self=False)

# --- Example API endpoint using db ---
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    db_check = check_db_connection(); 
    if db_check: return db_check
    storage_id = request.args.get('storage_id')
    if not storage_id: return jsonify({'error':'Storage ID is required'}), 400
    try:
        tasks = [serialize_document(task) for task in tasks_collection.find({'storage_id': storage_id})]
        return jsonify(tasks)
    except Exception as e:
        print(f"❌ Error fetching tasks: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error':f'Failed to fetch tasks: {str(e)}'}), 500

@app.route('/api/tasks/stats', methods=['GET'])
def get_task_stats():
    db_check = check_db_connection()
    if db_check: return db_check
    storage_id = request.args.get('storage_id')
    if not storage_id: return jsonify({'error':'Storage ID is required'}), 400
    try:
        completed = tasks_collection.count_documents({'storage_id': storage_id, 'completed': True})
        pending = tasks_collection.count_documents({'storage_id': storage_id, 'completed': False})
        return jsonify({'completed': completed, 'pending': pending})
    except Exception as e:
        print(f"❌ Error fetching task stats: {e}")
        return jsonify({'error':f'Failed to fetch task stats: {str(e)}'}), 500

@app.route('/api/storage/online-count', methods=['GET'])
def get_online_count():
    storage_id = request.args.get('storage_id')
    if not storage_id: return jsonify({'error':'Storage ID is required'}), 400
    try:
        count = len(storage_connections.get(storage_id, set()))
        return jsonify({'count': count, 'storage_id': storage_id})
    except Exception as e:
        print(f"❌ Error fetching online count: {e}")
        return jsonify({'error':f'Failed to fetch online count: {str(e)}'}), 500

@app.route('/api/test-socket', methods=['GET'])
def test_socket():
    storage_id = request.args.get('storage_id')
    return jsonify({'status': 'ok', 'storage_id': storage_id, 'message': 'Socket.IO endpoint is working'})

# --- Add more routes as in your current code ---
# Upload files, audio, task CRUD, etc. remain identical to your code
# Just ensure no secrets are ever hardcoded, always use environment variables

# --- Run Flask App ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on port {port}")
    socketio.run(app, debug=True, host='0.0.0.0', port=port)
