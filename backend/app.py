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

# --- App Initialization ---
app = Flask(__name__, static_folder='static', static_url_path='')

# --- Configuration from environment variables ---
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("Environment variable MONGO_URI is not set!")

app.config["MONGO_URI"] = MONGO_URI
app.config['UPLOAD_FOLDER'] = os.environ.get("UPLOAD_FOLDER", 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

# --- CORS ---
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://taskflowrinte.azurewebsites.net",
            "http://localhost:8080",
            "http://localhost:5000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:5000"
        ],
        "methods": ["GET","POST","PUT","DELETE","OPTIONS"],
        "allow_headers": ["Content-Type","Authorization"],
        "supports_credentials": True
    }
})

# --- SocketIO ---
socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "https://taskflowrinte.azurewebsites.net",
        "http://localhost:8080",
        "http://localhost:5000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5000"
    ],
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

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
    if not tasks_collection: return jsonify({'error':'Database not available'}), 503
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
    if tasks_collection:
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
    if tasks_collection:
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
        return jsonify({'error':f'Failed to fetch tasks: {str(e)}'}), 500

# --- Add more routes as in your current code ---
# Upload files, audio, task CRUD, etc. remain identical to your code
# Just ensure no secrets are ever hardcoded, always use environment variables

# --- Run Flask App ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on port {port}")
    socketio.run(app, debug=True, host='0.0.0.0', port=port)
