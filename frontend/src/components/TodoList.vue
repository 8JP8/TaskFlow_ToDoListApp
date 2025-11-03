<template>
  <div class="todo-app-container">
    <!-- STORAGE BUTTON (TOP LEFT) -->
    <button @click="showUserDialog = true" class="storage-toggle-btn" :aria-label="t('storageManagement')">
      <CircleStackIcon class="storage-icon" />
      <span class="storage-label">{{ t('storageManagement') }}</span>
    </button>

    <!-- THEME & LANGUAGE TOGGLE BUTTONS (TOP RIGHT) -->
    <div class="quick-toggles">
      <button @click="toggleLang" class="lang-toggle-btn" :aria-label="t('toggleLanguage')">
        {{ currentLang.toUpperCase() }}
      </button>
      <button @click="toggleTheme" class="theme-toggle-btn" :aria-label="t('toggleTheme')">
        <SunIcon v-if="isDarkMode" />
        <MoonIcon v-else />
      </button>
    </div>

    

    <!-- APP HEADER -->
    <header class="app-header" :style="{ marginBottom: (syncEnabled && otherOnlineCount > 1) ? 'var(--space-4)' : 'var(--space-8)' }" >
      <div class="header-icon-wrapper">
        <CheckCircleIcon />
      </div>
      <h1 class="app-title">{{ t('appTitle') }}</h1>
      <p class="app-subtitle">{{ t('appSubtitle') }}</p>
      
      <!-- MOVED HERE: Author/Course Information -->
      <div class="header-info">
        <p>João Oliveira 1240369</p>
        <p>RINTE - MEEC ISEP 2025/2026</p>
      </div>

      <!-- Online users line placed right after the course info -->
      <div class="online-users-line" v-if="syncEnabled && otherOnlineCount > 1">
        <UsersIcon />
        <span>{{ otherOnlineCount }} {{ t('activeUsers') }}</span>
      </div>
    </header>

    <main class="app-main-content">
      <!-- TASK INPUT FORM -->
      <section class="card task-input-card">
        <form @submit.prevent="addTask" class="task-form">
          <div class="input-group">
            <PlusIcon class="input-icon" />
            <input
              v-model="newTaskTitle"
              type="text"
              :placeholder="t('taskTitlePlaceholder')"
              required
              class="form-input"
            />
          </div>
          <div class="input-group">
            <DocumentTextIcon class="input-icon" />
            <textarea
              v-model="newTaskDescription"
              :placeholder="t('taskDescriptionPlaceholder')"
              class="form-textarea"
            ></textarea>
          </div>
          <button type="submit" class="btn btn-primary btn-submit">
            <PlusIcon />
            <span>{{ t('addTask') }}</span>
          </button>
        </form>
      </section>

      <!-- TASK STATISTICS -->
      <section class="task-stats-grid">
        <button 
          @click="setFilter('completed')" 
          class="card stat-card filter-button"
          :class="{ 'filter-active': currentFilter === 'completed' }"
          data-filter="completed"
        >
          <div class="stat-icon-wrapper success">
            <CheckCircleIcon />
          </div>
          <div>
            <div class="stat-number">{{ stats.completed }}</div>
            <div class="stat-label">{{ t('completed') }}</div>
          </div>
        </button>
        <button 
          @click="setFilter('pending')" 
          class="card stat-card filter-button"
          :class="{ 'filter-active': currentFilter === 'pending' }"
          data-filter="pending"
        >
          <div class="stat-icon-wrapper warning">
            <ClockIcon />
          </div>
          <div>
            <div class="stat-number">{{ stats.pending }}</div>
            <div class="stat-label">{{ t('pending') }}</div>
          </div>
        </button>
        <button 
          @click="setFilter('all')" 
          class="card stat-card filter-button"
          :class="{ 'filter-active': currentFilter === 'all' }"
          data-filter="all"
        >
          <div class="stat-icon-wrapper info">
            <ListBulletIcon />
          </div>
          <div>
            <div class="stat-number">{{ tasks.length }}</div>
            <div class="stat-label">{{ t('totalTasks') }}</div>
          </div>
        </button>
      </section>

      <!-- TASK LIST -->
      <section class="task-list-section">
        <TransitionGroup name="task-list" tag="div" class="task-list">
            <div
              v-for="task in filteredTasks"
              :key="task._id"
              class="card task-card"
              :class="{ 
                completed: task.completed,
                'is-backup': task.is_backup
              }"
            >
            <!-- Task Main Info -->
            <div class="task-header">
              <div class="task-main-info">
                <button
                  @click="toggleTask(task)"
                  class="task-checkbox"
                  :aria-checked="task.completed"
                >
                  <CheckIcon v-if="task.completed" class="checkmark" />
                </button>
                <div class="task-text-content">
                  <div v-if="!task.isEditing" class="task-title-row">
                    <h3 class="task-title">{{ task.title }}</h3>
                    <div v-if="task.is_backup" class="backup-indicator">
                      <span class="backup-badge">{{ t('backup') }}</span>
                    </div>
                  </div>
                  <div v-if="task.description && !task.isEditing" class="task-description-container">
                    <div 
                      v-if="!task.showDetails"
                      class="task-description task-description-preview"
                    >
                      {{ getFirstLine(task.description) }}{{ isContentTruncated(task.description) ? '...' : '' }}
                    </div>
                    <div 
                      v-else
                      class="task-description task-description-full"
                      v-html="formatDescription(task.description)"
                    ></div>
                  </div>
                  <div v-if="task.isEditing" class="edit-inline">
    <input v-model="task.editTitle" type="text" class="form-input edit-title-input" :placeholder="t('title')" />
    <textarea v-model="task.editDescription" class="form-textarea" :placeholder="t('description')"></textarea>
                    <div class="edit-actions">
                      <button @click="saveEdit(task)" class="btn btn-primary">{{ t('save') }}</button>
                      <button @click="cancelEdit(task)" class="btn btn-secondary">{{ t('cancel') }}</button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="task-actions">
                <button @click="toggleTaskDetails(task)" class="btn btn-secondary">
                  <EyeIcon v-if="!task.showDetails" />
                  <EyeSlashIcon v-else />
                </button>
                <!-- Show restore button for backup tasks, edit button for regular tasks -->
                <button 
                  v-if="task.is_backup" 
                  @click="restoreFromBackup(task)" 
                  class="btn btn-secondary" 
                  :title="t('restoreTask')"
                >
                  <ArrowPathIcon />
                </button>
                <button 
                  v-else
                  @click="task.isEditing ? cancelEdit(task) : startEdit(task)" 
                  class="btn btn-secondary" 
                  :title="task.isEditing ? t('cancel') : t('edit')"
                >
                  <template v-if="!task.isEditing">
                    <PencilSquareIcon />
                  </template>
                  <template v-else>
                    <XMarkIcon />
                  </template>
                </button>
                <button @click="deleteTask(task._id)" class="btn btn-danger">
                  <TrashIcon />
                </button>
              </div>
            </div>
            
            <!-- Task Meta -->
            <div class="task-meta">
                <div class="meta-item"><CalendarIcon /><span>{{ formatDate(task.created_at) }}</span></div>
                <div v-if="task.attachments?.length" class="meta-item"><PaperClipIcon /><span>{{ task.attachments.length }} {{ t('files') }}</span></div>
                <div v-if="task.audio_notes?.length" class="meta-item"><MicrophoneIcon /><span>{{ task.audio_notes.length }} {{ t('audioNotesShort') }}</span></div>
            </div>


            <!-- Task Details (Collapsible) -->
            <Transition name="slide-fade">
              <div v-if="task.showDetails" class="task-details-content">
                 <!-- Add Media Section -->
                <div class="add-media-grid">
                    <div class="media-upload-box">
                        <DocumentPlusIcon class="media-icon"/>
                        <h4>{{ t('addAttachment') }}</h4>
                        <p>{{ t('uploadFileHelp') }}</p>
                        <input type="file" @change="handleFileUpload($event, task._id)" :id="`file-input-${task._id}`" class="file-input"/>
                        <label :for="`file-input-${task._id}`" class="btn btn-outline">{{ t('chooseFile') }}</label>
                    </div>
                    <div class="media-upload-box">
                        <MicrophoneIcon class="media-icon"/>
                        <h4>{{ t('recordAudioNote') }}</h4>
                        <p>{{ t('addVoiceMemo') }}</p>
                        <button 
                            @click="isRecording && recordingTaskId === task._id ? stopRecording() : startRecording(task._id)" 
                            :disabled="isRecording && recordingTaskId !== task._id || isRequestingPermission"
                            class="btn btn-record"
                            :class="{ 
                                'is-recording': isRecording && recordingTaskId === task._id,
                                'is-requesting': isRequestingPermission
                            }"
                        >
                            <span class="record-dot"></span>
                          {{ isRequestingPermission ? 'Requesting...' : (isRecording && recordingTaskId === task._id) ? t('stop') : t('record') }}
                        </button>
                    </div>
                </div>

                <!-- Attachments and Audio Lists -->
                <div class="media-lists">
                    <!-- File Attachments -->
                    <div v-if="task.attachments?.length" class="media-list">
                      <h4>{{ t('attachments') }}</h4>
                      <div v-for="file in task.attachments" :key="file._id" class="media-item">
                        <div class="media-info"><DocumentIcon/><span>{{ file.filename }}</span></div>
                        <div class="media-actions">
                          <button @click="downloadFile(file)" class="btn btn-success"><ArrowDownTrayIcon/></button>
                          <button @click="deleteAttachment(task._id, file._id || file.unique_filename)" class="btn btn-danger"><TrashIcon/></button>
                        </div>
                      </div>
                    </div>

                    <!-- Audio Notes -->
                    <div v-if="task.audio_notes?.length" class="media-list">
                      <h4>{{ t('audioNotes') }}</h4>
                      <div v-for="audio in task.audio_notes" :key="audio._id" class="media-item">
                        <div class="media-info"><span class="audio-duration">{{ formatDuration(audio.duration) }}</span></div>
                        <div class="media-actions">
                          <button @click="playAudio(audio)" class="btn btn-success">
                            <PlayIcon v-if="currentAudio !== (audio.unique_filename || audio.filename)" />
                            <PauseIcon v-else />
                          </button>
                          <button @click="deleteAudio(task._id, audio._id || audio.filename)" class="btn btn-danger"><TrashIcon/></button>
                        </div>
                      </div>
                    </div>
                </div>

              </div>
            </Transition>
          </div>
        </TransitionGroup>
      </section>
    </main>
    
    <!-- Global Audio Player -->
    <audio ref="audioPlayer" @ended="currentAudio = null"></audio>
    
    
    <!-- User Management Dialog -->
    <Transition name="modal">
      <div v-if="showUserDialog" class="modal-overlay" @click="showUserDialog = false">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>
              <CircleStackIcon class="header-icon" />
              {{ t('storageManagement') }}
            </h3>
            <button @click="handleUserDialogClose" class="close-btn">
              <XMarkIcon />
            </button>
          </div>
          
          <div class="modal-body">
            <!-- Realtime Sync Toggle -->
            <div class="sync-toggle-section">
              <label class="sync-toggle-label">
                <input 
                  type="checkbox" 
                  v-model="syncEnabled" 
                  @change="toggleRealtimeSync"
                  class="sync-toggle-input"
                />
                <span class="sync-toggle-text">{{ t('enableRealtimeSync') }}</span>
              </label>
              <p class="sync-toggle-description">{{ t('realtimeSyncDescription') }}</p>
            </div>
            
            <!-- Tab Navigation -->
            <div class="tab-navigation">
              <button 
                @click="activeTab = 'storage'" 
                class="tab-btn" 
                :class="{ active: activeTab === 'storage' }"
              >
                <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                  <line x1="8" y1="21" x2="16" y2="21"/>
                  <line x1="12" y1="17" x2="12" y2="21"/>
                </svg>
                {{ t('myStorage') }}
              </button>
              <button 
                @click="activeTab = 'external'" 
                class="tab-btn" 
                :class="{ active: activeTab === 'external' }"
              >
                <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                  <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                </svg>
                {{ t('connectToUser') }}
              </button>
            </div>
            
            <!-- Tab Content -->
            <div class="tab-content">
              <!-- My Storage Tab -->
              <div v-if="activeTab === 'storage'" class="tab-panel">
                <div class="storage-info-section">
                  <!-- Warning Message -->
                  <div class="storage-warning">
                    <ExclamationTriangleIcon class="warning-icon" />
                    <div class="warning-content">
                      <p>{{ t('linkNewStorageWarningMessage') }}</p>
                    </div>
                  </div>
                  
                  <div class="storage-actions">
                    <button @click="copyStorageId" class="btn btn-primary copy-btn" :disabled="isRegenerating">
                      <PlusIcon class="copy-icon" />
                      {{ isRegenerating ? t('generating') : t('linkNewStorage') }}
                    </button>
                  </div>
                  
                  <!-- Generated ID Display -->
                  <div v-if="generatedId" class="generated-id-section">
                    <div class="generated-id-display">
                      <label>{{ t('newStorageId') }}:</label>
                      <div class="storage-id-container">
                        <span class="storage-id-text" :class="{ blurred: !showGeneratedId }">
                          {{ showGeneratedId ? generatedId : '••••••••••••••••••••••••••••••••' }}
                        </span>
                        <button @click="showGeneratedId = !showGeneratedId" class="eye-toggle-btn" :aria-label="showGeneratedId ? t('hideStorageId') : t('showStorageId')">
                          <EyeIcon v-if="!showGeneratedId" />
                          <EyeSlashIcon v-else />
                        </button>
                      </div>
                    </div>
                    
                    <div class="security-warning">
                      <ExclamationTriangleIcon class="warning-icon" />
                      <p>{{ t('storageIdWarning') }}</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Connect to User Tab -->
              <div v-if="activeTab === 'external'" class="tab-panel">
                <div class="external-id-section">
                  <div class="input-group">
                    <label>{{ t('enterStorageId') }}:</label>
                    <div class="input-with-icon">
                      <KeyIcon class="input-icon" />
                      <input 
                        v-model="_xs1d" 
                        type="text" 
                        :placeholder="t('storageIdPlaceholder')"
                        class="form-input external-id-input"
                        maxlength="16"
                      />
                    </div>
                  </div>
                  
                  <div class="external-id-info">
                    <InformationCircleIcon class="info-icon" />
                    <p>{{ t('externalIdInfo') }}</p>
                  </div>
                  
                  <div class="external-id-actions">
                    <button @click="useExternalStorageId" class="btn btn-primary" :disabled="!_xs1d || _xs1d.length < 8 || isUsingExternalId">
                      <LinkIcon class="link-icon" />
                      {{ isUsingExternalId ? t('connecting') : t('connectToStorage') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
    
    <!-- Custom Confirmation Dialog -->
    <Transition name="modal">
      <div v-if="showConfirmDialog" class="modal-overlay" @click="handleConfirmCancel">
        <div class="modal-content confirm-dialog" @click.stop>
          <div class="confirm-header">
            <svg class="confirm-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 16v-4"/>
              <path d="M12 8h.01"/>
            </svg>
            <h3>{{ confirmDialog.title }}</h3>
          </div>
          
          <div class="confirm-body">
            <p>{{ confirmDialog.message }}</p>
          </div>
          
          <div class="confirm-actions">
            <button @click="handleConfirmCancel" class="btn btn-secondary">
              {{ t('cancel') }}
            </button>
            <button @click="handleConfirmOk" class="btn btn-primary">
              {{ t('ok') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
    
    <!-- Toast Container -->
    <div class="toast-container">
      <TransitionGroup name="toast" tag="div">
        <div 
          v-for="toast in toasts" 
          :key="toast.id" 
          class="toast" 
          :class="toast.type"
        >
          <div class="toast-content">
            <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <!-- Success icon - checkmark in circle -->
              <template v-if="toast.type === 'success'">
                <circle cx="12" cy="12" r="10"/>
                <path d="M9 12l2 2 4-4"/>
              </template>
              
              <!-- Error icon - X in circle -->
              <template v-if="toast.type === 'error'">
                <circle cx="12" cy="12" r="10"/>
                <path d="M15 9l-6 6"/>
                <path d="M9 9l6 6"/>
              </template>
              
              <!-- Info icon - exclamation point in circle -->
              <template v-if="toast.type === 'info'">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 16v-4"/>
                <path d="M12 8h.01"/>
              </template>
              
              <!-- Warning icon - exclamation triangle -->
              <template v-if="toast.type === 'warning'">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </template>
            </svg>
            <div class="toast-text">
              <div class="toast-title">{{ toast.title }}</div>
              <div v-if="toast.message" class="toast-message">{{ toast.message }}</div>
            </div>
          </div>
          <button @click="removeToast(toast.id)" class="toast-close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import axios from 'axios';
import apiConfig from '../api-config.js';
import storageManager from '../storage-manager.js';
import realtimeSync from '../realtime-sync.js';
import {
  CheckCircleIcon, PlusIcon, DocumentTextIcon, ClockIcon, ListBulletIcon,
  CheckIcon, CalendarIcon, PaperClipIcon, MicrophoneIcon, EyeIcon, EyeSlashIcon,
  TrashIcon, DocumentIcon, ArrowDownTrayIcon, PlayIcon, PauseIcon, DocumentPlusIcon,
  SunIcon, MoonIcon, PencilSquareIcon, XMarkIcon, ExclamationTriangleIcon,
  InformationCircleIcon, KeyIcon, LinkIcon, CircleStackIcon, ArrowPathIcon, UsersIcon
} from '@heroicons/vue/24/outline';

// --- SEO & Social Media Meta Tags ---
const updateMetaTags = () => {
  const appTitle = 'TaskFlow - Real-Time Collaborative Task Management';
  const appDescription = 'A secure, multi-storage task management application with real-time synchronization. Create, edit, and collaborate on tasks across devices without login.';
  const appImage = 'https://i.postimg.cc/kXhw6b31/image.png';
  const appUrl = window.location.href;
  
  // Basic Meta Tags
  document.title = appTitle;
  
  // Open Graph (Facebook, LinkedIn)
  updateOrCreateMeta('og:title', appTitle);
  updateOrCreateMeta('og:description', appDescription);
  updateOrCreateMeta('og:image', appImage);
  updateOrCreateMeta('og:url', appUrl);
  updateOrCreateMeta('og:type', 'website');
  
  // Twitter
  updateOrCreateMeta('twitter:card', 'summary_large_image');
  updateOrCreateMeta('twitter:title', appTitle);
  updateOrCreateMeta('twitter:description', appDescription);
  updateOrCreateMeta('twitter:image', appImage);
  
  // Standard Meta
  updateOrCreateMeta('description', appDescription, 'name');
  updateOrCreateMeta('keywords', 'task management, real-time collaboration, notes, productivity, todo list', 'name');
  updateOrCreateMeta('author', 'João Oliveira', 'name');
  
  // Favicon
  updateFavicon();
};

const updateOrCreateMeta = (property, content, attribute = 'property') => {
  let meta = document.querySelector(`meta[${attribute}="${property}"]`);
  if (!meta) {
    meta = document.createElement('meta');
    meta.setAttribute(attribute, property);
    document.head.appendChild(meta);
  }
  meta.setAttribute('content', content);
};

const updateFavicon = () => {
  // Remove existing favicons
  const existingLinks = document.querySelectorAll('link[rel*="icon"]');
  existingLinks.forEach(link => link.remove());
  
  // SVG Favicon (inline checkmark icon)
  const svgFavicon = `data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='45' fill='%233b82f6'/><path d='M30 50 L45 65 L70 35' stroke='white' stroke-width='8' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>`;
  
  const link = document.createElement('link');
  link.rel = 'icon';
  link.type = 'image/svg+xml';
  link.href = svgFavicon;
  document.head.appendChild(link);
  
  // Apple Touch Icon (larger checkmark)
  const appleTouchIcon = document.createElement('link');
  appleTouchIcon.rel = 'apple-touch-icon';
  appleTouchIcon.href = svgFavicon;
  document.head.appendChild(appleTouchIcon);
};

// --- STATE MANAGEMENT ---
const tasks = ref([]);
const newTaskTitle = ref('');
const newTaskDescription = ref('');
const stats = reactive({ completed: 0, pending: 0 });
const currentFilter = ref('all'); // 'all', 'completed', 'pending'
const isDarkMode = ref(true);

// --- COMPUTED PROPERTIES ---
const filteredTasks = computed(() => {
  switch (currentFilter.value) {
    case 'completed':
      return tasks.value.filter(task => task.completed);
    case 'pending':
      return tasks.value.filter(task => !task.completed);
    default:
      return tasks.value;
  }
});

// --- FILTER FUNCTIONS ---
const setFilter = (filter) => {
  // If clicking the same filter, deselect it (show all tasks)
  if (currentFilter.value === filter) {
    currentFilter.value = 'all';
  } else {
    currentFilter.value = filter;
  }
};
const _s1d = ref(null);
const showUserDialog = ref(false);
const isRegenerating = ref(false);
const _xs1d = ref('');
const isUsingExternalId = ref(false);
const activeTab = ref('storage');
const toasts = ref([]);
const showConfirmDialog = ref(false);
const confirmDialog = ref({ title: '', message: '', onConfirm: null });
const generatedId = ref('');
const showGeneratedId = ref(false);
// Real-time sync state
const activeUsers = ref({});
const onlineCount = ref(0);
const otherOnlineCount = computed(() => Math.max(onlineCount.value - 1, 0));
const syncEnabled = ref(localStorage.getItem('realtimeSyncEnabled') !== 'false'); // Default to true, load from localStorage
const pendingUpdates = ref([]);
const userId = ref(null);
// Track the last action timestamp to identify our own changes
const lastActionTimestamp = ref(0);
// Track recent notifications to prevent spam
const recentNotifications = ref(new Set());
// --- I18N ---
const currentLang = ref(localStorage.getItem('lang') || 'pt');
const messages = {
  en: {
    appTitle: 'TaskFlow',
    appSubtitle: 'A modern To-Do list to supercharge your productivity.',
    toggleLanguage: 'Toggle language',
    toggleTheme: 'Toggle theme',
    addTask: 'Add Task',
    taskTitlePlaceholder: "What's the next big thing?",
    taskDescriptionPlaceholder: 'Add more details...',
    attachments: 'Attachments',
    audioNotes: 'Audio Notes',
    audioNotesShort: 'audio note(s)',
    files: 'file(s)',
    edit: 'Edit',
    save: 'Save',
    cancel: 'Cancel',
    title: 'Title',
    description: 'Description',
    completed: 'Completed',
    pending: 'Pending',
    totalTasks: 'Total Tasks',
    addAttachment: 'Add Attachment',
    uploadFileHelp: 'Upload a relevant file.',
    chooseFile: 'Choose File',
    recordAudioNote: 'Record Audio Note',
    addVoiceMemo: 'Add a voice memo.',
    record: 'Record',
    stop: 'Stop',
    linkStorage: 'Link Storage',
    currentStorageId: 'Current Storage ID',
    showStorageId: 'Show Storage ID',
    hideStorageId: 'Hide Storage ID',
    storageIdWarning: 'Warning: Anyone with your Storage ID can access your notes.',
    regenerateStorageId: 'Generate New Storage ID',
    regenerating: 'Generating...',
    storageIdRegenerated: 'Storage ID generated successfully!',
    useExternalId: 'Use External ID',
    useExternalStorageId: 'Use External Storage ID',
    enterStorageId: 'Enter Storage ID',
    storageIdPlaceholder: 'Enter 16-character ID',
    externalIdInfo: 'This will connect you to another storage. You will be able to view and add notes to that storage.',
    connectToStorage: 'Connect to Storage',
    connecting: 'Connecting...',
    externalIdConnected: 'Successfully connected to external storage!',
    invalidStorageId: 'Invalid storage ID. Please check and try again.',
    errorConnectingToStorage: 'Error connecting to storage. Please try again.',
    userManagement: 'User',
    storageManagement: 'Storage',
    myStorage: 'My Storage',
    connectToUser: 'Connect to Storage',
    copyStorageId: 'Copy Storage ID',
    generateNewStorage: 'Generate New Storage',
    linkNewStorage: 'Link New Storage',
    storageIdHidden: 'Hidden for security',
    generating: 'Generating...',
    linkNewStorageWarning: 'Link New Storage',
    linkNewStorageWarningMessage: 'This will generate a new storage ID and disconnect all other storages. You will need to manually update all your other storages with the new ID to access your notes on each one.',
    newStorageId: 'New Storage ID',
    newIdInfo: 'New ID generated and copied to clipboard. Update all your devices with this new ID.',
    ok: 'OK',
    // Confirmation dialogs
    confirmDeleteTask: 'Are you sure you want to delete this task?',
    confirmDeleteAttachment: 'Are you sure you want to delete this attachment?',
    confirmDeleteAudio: 'Are you sure you want to delete this audio note?',
    // File operations
    fileUploadSuccess: 'File uploaded',
    fileUploadError: 'Failed to upload file',
    fileDownloadSuccess: 'File downloaded',
    fileDownloadError: 'Failed to download file',
    fileDeleteSuccess: 'File deleted',
    fileDeleteError: 'Failed to delete file',
    // Audio operations
    audioRecordStart: 'Recording started',
    audioRecordStop: 'Recording stopped',
    audioRecordError: 'Recording failed',
    audioUploadSuccess: 'Audio note saved',
    audioUploadError: 'Failed to save audio note',
    audioDeleteSuccess: 'Audio note deleted',
    audioDeleteError: 'Failed to delete audio note',
    // Audio recording errors
    audioNotSupported: 'Audio recording is not supported in this browser',
    audioSecurityError: 'Recording requires HTTPS connection',
    audioPermissionDenied: 'Microphone permission denied. Please allow access in browser settings.',
    audioNoMicrophone: 'No microphone found on this device',
    audioMicrophoneInUse: 'Microphone is already in use by another app',
    audioConstraintError: 'Microphone does not meet requirements',
    audioRequiresHttps: 'Recording requires HTTPS or localhost',
    audioRecordingError: 'An error occurred during recording',
    audioProcessingError: 'Could not process audio data',
    audioNoData: 'No audio data captured',
    recordingInProgress: 'Recording...',
    speakNow: 'Speak now',
    cannotRecord: 'Cannot Record',
    uploadFailed: 'Upload Failed',
    processingFailed: 'Processing Failed',
    playbackError: 'Playback Error',
    cannotPlayAudio: 'Could not play audio file',
    // General notifications
    taskAdded: 'Task added',
    taskUpdated: 'Task updated',
    taskDeleted: 'Task deleted',
    taskCompleted: 'Task completed',
    taskUncompleted: 'Task marked as pending',
    // Storage operations
    storageIdGenerated: 'New storage ID generated',
    storageIdCopied: 'Storage ID copied to clipboard',
    storageMigrationSuccess: 'Storage migrated successfully',
    storageMigrationError: 'Failed to migrate storage',
    // Error messages
    networkError: 'Network error',
    networkError2: 'Please check your connection.',
    permissionDenied: 'Permission denied',
    invalidFile: 'Invalid file type',
    fileTooLarge: 'File too large',
    storageFull: 'Storage is full',
    securityError: 'Security Error',
    notSupported: 'Not Supported',
    // Real-time sync
    activeUsers: 'active user(s)',
    backup: 'Backup',
    editing: 'Editing',
    recording: 'Recording',
    idle: 'Idle',
    syncedFromAnotherDevice: 'Synced from another device',
    enableRealtimeSync: 'Enable Realtime Sync',
    realtimeSyncDescription: 'Sync changes instantly across all devices. Disable to update only on page refresh.',
    realtimeSyncEnabled: 'Realtime Sync Enabled',
    realtimeSyncEnabledDescription: 'Changes will sync instantly across all devices.',
    realtimeSyncDisabled: 'Realtime Sync Disabled',
    realtimeSyncDisabledDescription: 'Changes will only sync on page refresh.',
    realtimeSyncConnected: 'Realtime Sync Connected',
    realtimeSyncDisconnected: 'RealTime Sync Disconnected',
    restoreTask: 'Restore Task',
    taskRestored: 'Task Restored',
    taskRestoredFromBackup: 'Task restored from backup successfully.',
    restoreError: 'Restore Failed',
    cannotDeleteWhileRecording: 'Cannot Delete While Recording',
    stopRecordingFirst: 'Please stop recording first before deleting this task.',
    taskDeletedWhileRecording: 'Task Deleted While Recording',
    backupCreatedContinueRecording: 'A backup was created. You can continue recording.',
    backupWillBeCreatedAfterRecording: 'A backup will be created after recording ends.',
    backupCreatedAfterRecording: 'Backup Created After Recording',
    taskSavedAsBackup: 'Task saved as backup with all files and audio.',
    backupCreationError: 'Backup Creation Failed',
    dataValidationComplete: 'Data validation complete',
    invalidDataFiltered: 'Invalid data filtered out'
  },
  pt: {
    appTitle: 'TaskFlow',
    appSubtitle: 'Uma lista de tarefas moderna para impulsionar a produtividade.',
    toggleLanguage: 'Alternar idioma',
    toggleTheme: 'Alternar tema',
    addTask: 'Adicionar Tarefa',
    taskTitlePlaceholder: 'Qual é a próxima grande tarefa?',
    taskDescriptionPlaceholder: 'Adiciona mais detalhes...',
    attachments: 'Anexos',
    audioNotes: 'Notas de Áudio',
    audioNotesShort: 'nota(s) áudio',
    files: 'ficheiro(s)',
    edit: 'Editar',
    save: 'Guardar',
    cancel: 'Cancelar',
    title: 'Título',
    description: 'Descrição',
    completed: 'Concluídas',
    pending: 'Pendentes',
    totalTasks: 'Tarefas Totais',
    addAttachment: 'Adicionar Anexo',
    uploadFileHelp: 'Carrega um ficheiro relevante.',
    chooseFile: 'Escolher Ficheiro',
    recordAudioNote: 'Gravar Nota de Áudio',
    addVoiceMemo: 'Adicionar memo de voz.',
    record: 'Gravar',
    stop: 'Parar',
    linkStorage: 'Ligar Dispositivo',
    currentStorageId: 'ID do Dispositivo Atual',
    showStorageId: 'Mostrar ID do Dispositivo',
    hideStorageId: 'Ocultar ID do Dispositivo',
    storageIdWarning: 'Aviso: Qualquer pessoa com o seu ID de Dispositivo pode aceder às suas notas.',
    regenerateStorageId: 'Gerar Novo ID de Dispositivo',
    regenerating: 'A gerar...',
    storageIdRegenerated: 'ID de Dispositivo gerado com sucesso!',
    useExternalId: 'Usar ID Externo',
    useExternalStorageId: 'Usar ID de Dispositivo Externo',
    enterStorageId: 'Inserir ID de Armazenamento',
    storageIdPlaceholder: 'Inserir ID de 16 caracteres',
    externalIdInfo: 'Isto irá ligá-lo às notas de outro armazenamento. Poderá ver e adicionar notas a esse armazenamento.',
    connectToStorage: 'Ligar ao Armazenamento',
    connecting: 'A ligar...',
    externalIdConnected: 'Ligado ao armazenamento externo!',
    invalidStorageId: 'ID de armazenamento inválido. Verifique e tente novamente.',
    errorConnectingToStorage: 'Erro ao ligar ao armazenamento. Tente novamente.',
    userManagement: 'Utilizador',
    storageManagement: 'Armazenamento',
    myStorage: 'O Meu Armazenamento',
    connectToUser: 'Ligar a Armazenamento',
    copyStorageId: 'Copiar ID do Dispositivo',
    generateNewStorage: 'Gerar Novo Dispositivo',
    linkNewStorage: 'Ligar Novo Dispositivo',
    storageIdHidden: 'Oculto por segurança',
    generating: 'A gerar...',
    linkNewStorageWarning: 'Ligar Novo Dispositivo',
    linkNewStorageWarningMessage: 'Isto irá gerar um novo ID de armazenamento e desligar todos os outros dispositivos. Terá de atualizar manualmente todos os seus outros dispositivos com o novo ID para aceder às suas notas em cada um deles.',
    newStorageId: 'Novo ID de Dispositivo',
    newIdInfo: 'Novo ID gerado e copiado para a área de transferência. Atualize todos os seus dispositivos com este novo ID.',
    ok: 'OK',
    // Confirmation dialogs
    confirmDeleteTask: 'Tem a certeza de que pretende eliminar esta tarefa?',
    confirmDeleteAttachment: 'Tem a certeza de que pretende eliminar este anexo?',
    confirmDeleteAudio: 'Tem a certeza de que pretende eliminar esta nota de áudio?',
    // File operations
    fileUploadSuccess: 'Ficheiro carregado',
    fileUploadError: 'Falha ao carregar ficheiro',
    fileDownloadSuccess: 'Ficheiro descarregado',
    fileDownloadError: 'Falha ao descarregar ficheiro',
    fileDeleteSuccess: 'Ficheiro eliminado',
    fileDeleteError: 'Falha ao eliminar ficheiro',
    // Audio operations
    audioRecordStart: 'Gravação iniciada',
    audioRecordStop: 'Gravação parada',
    audioRecordError: 'Falha na gravação',
    audioUploadSuccess: 'Nota de áudio guardada',
    audioUploadError: 'Falha ao guardar nota de áudio',
    audioDeleteSuccess: 'Nota de áudio eliminada',
    audioDeleteError: 'Falha ao eliminar nota de áudio',
    // Audio recording errors
    audioNotSupported: 'Gravação de áudio não é suportada neste navegador',
    audioSecurityError: 'Gravação requer ligação HTTPS',
    audioPermissionDenied: 'Permissão de microfone negada. Por favor, permita o acesso nas definições do navegador.',
    audioNoMicrophone: 'Nenhum microfone encontrado neste dispositivo',
    audioMicrophoneInUse: 'Microfone já está a ser usado por outra aplicação',
    audioConstraintError: 'Microfone não cumpre os requisitos',
    audioRequiresHttps: 'Gravação requer HTTPS ou localhost',
    audioRecordingError: 'Ocorreu um erro durante a gravação',
    audioProcessingError: 'Não foi possível processar os dados de áudio',
    audioNoData: 'Nenhum dado de áudio capturado',
    recordingInProgress: 'A gravar...',
    speakNow: 'Fale agora',
    cannotRecord: 'Não é Possível Gravar',
    uploadFailed: 'Falha no Envio',
    processingFailed: 'Falha no Processamento',
    playbackError: 'Erro de Reprodução',
    cannotPlayAudio: 'Não foi possível reproduzir o ficheiro de áudio',
    // General notifications
    taskAdded: 'Tarefa adicionada',
    taskUpdated: 'Tarefa atualizada',
    taskDeleted: 'Tarefa eliminada',
    taskCompleted: 'Tarefa concluída',
    taskUncompleted: 'Tarefa marcada como pendente',
    // Storage operations
    storageIdGenerated: 'Novo ID de armazenamento gerado com sucesso',
    storageIdCopied: 'ID de armazenamento copiado para a área de transferência',
    storageMigrationSuccess: 'Armazenamento migrado com sucesso',
    storageMigrationError: 'Falha ao migrar armazenamento',
    // Error messages
    networkError: 'Erro de rede',
    networkError2: 'Verifique a sua ligação.',
    permissionDenied: 'Permissão negada',
    invalidFile: 'Tipo de ficheiro inválido',
    fileTooLarge: 'Ficheiro demasiado grande',
    storageFull: 'Armazenamento cheio',
    securityError: 'Erro de Segurança',
    notSupported: 'Não Suportado',
    // Real-time sync
    activeUsers: 'utilizador(es) ativo(s)',
    backup: 'Cópia de Segurança',
    editing: 'A Editar',
    recording: 'A Gravar',
    idle: 'Inativo',
    syncedFromAnotherDevice: 'Sincronizado de outro dispositivo',
    enableRealtimeSync: 'Ativar Sincronização em Tempo Real',
    realtimeSyncDescription: 'Sincroniza alterações instantaneamente entre todos os dispositivos. Desative para atualizar apenas ao atualizar a página.',
    realtimeSyncEnabled: 'Sincronização em Tempo Real Ativada',
    realtimeSyncEnabledDescription: 'As alterações serão sincronizadas instantaneamente entre todos os dispositivos.',
    realtimeSyncDisabled: 'Sincronização em Tempo Real Desativada',
    realtimeSyncDisabledDescription: 'As alterações serão sincronizadas apenas ao atualizar a página.',
    realtimeSyncConnected: 'Sincronização Conectada',
    realtimeSyncDisconnected: 'Sincronização Desconectada',
    restoreTask: 'Restaurar Tarefa',
    taskRestored: 'Tarefa Restaurada',
    taskRestoredFromBackup: 'Tarefa restaurada da cópia de segurança com sucesso.',
    restoreError: 'Falha na Restauração',
    cannotDeleteWhileRecording: 'Não Pode Eliminar Durante Gravação',
    stopRecordingFirst: 'Por favor pare a gravação primeiro antes de eliminar esta tarefa.',
    taskDeletedWhileRecording: 'Tarefa Eliminada Durante Gravação',
    backupCreatedContinueRecording: 'Foi criada uma cópia de segurança. Pode continuar a gravar.',
    backupWillBeCreatedAfterRecording: 'Será criada uma cópia de segurança após a gravação terminar.',
    backupCreatedAfterRecording: 'Cópia de Segurança Criada Após Gravação',
    taskSavedAsBackup: 'Tarefa salva como cópia de segurança com todos os ficheiros e áudio.',
    backupCreationError: 'Falha na Criação da Cópia de Segurança',
    dataValidationComplete: 'Validação de dados completa',
    invalidDataFiltered: 'Dados inválidos filtrados'
  }
};
const t = (key) => messages[currentLang.value][key] || key;
const toggleLang = () => {
  currentLang.value = currentLang.value === 'pt' ? 'en' : 'pt';
  localStorage.setItem('lang', currentLang.value);
};

// --- THEME ---
const loadTheme = () => {
  const savedTheme = localStorage.getItem('theme') || 'dark';
  isDarkMode.value = savedTheme === 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
};

const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value;
  const theme = isDarkMode.value ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
};

// --- API: TASKS ---
const fetchTasks = async () => {
  try {
    const apiUrl = await apiConfig.getApiUrl();
    const response = await axios.get(`${apiUrl}/tasks`, {
      params: { storage_id: _s1d.value }
    });
    tasks.value = response.data.map(task => ({
      ...task,
      showDetails: false,
      isEditing: false,
      editTitle: task.title,
      editDescription: task.description || ''
    }));
    
    // Check and resolve any existing duplicates
    checkAndResolveDuplicates();
  } catch (error) { console.error("Error fetching tasks:", error); }
};

const fetchTaskStats = async () => {
  try {
    const apiUrl = await apiConfig.getApiUrl();
    const response = await axios.get(`${apiUrl}/tasks/stats`, {
      params: { storage_id: _s1d.value }
    });
    stats.completed = response.data.completed;
    stats.pending = response.data.pending;
  } catch (error) { console.error("Error fetching task stats:", error); }
};

const addTask = async () => {
  if (newTaskTitle.value.trim() === '') return;
  try {
    // Track this action to prevent self-notifications
    lastActionTimestamp.value = Date.now();
    
    // Create new task object
    const newTaskData = {
      title: newTaskTitle.value,
      description: newTaskDescription.value,
      completed: false
    };
    
    // Check for duplicates before adding
    if (!preventDuplicateTask(newTaskData)) {
      console.log('Duplicate task prevented, not adding');
      return;
    }
    
    const apiUrl = await apiConfig.getApiUrl();
    const response = await axios.post(`${apiUrl}/tasks`, {
      title: newTaskData.title,
      description: newTaskData.description,
      storage_id: _s1d.value
    });
    
    // Add to local array immediately for instant UI feedback
    // The real-time sync will filter out the user's own task_created events
    const newTask = {
      ...response.data,
      showDetails: false,
      isEditing: false,
      editTitle: response.data.title,
      editDescription: response.data.description || ''
    };
    tasks.value.unshift(newTask);
    
    newTaskTitle.value = '';
    newTaskDescription.value = '';
    fetchTaskStats();
    addToast('success', t('taskAdded'));
  } catch (error) { 
    console.error("Error adding task:", error);
    addToast('error', t('networkError'), t('networkError2'));
  }
};

const toggleTask = async (task) => {
  try {
    // Track this action to prevent self-notifications
    lastActionTimestamp.value = Date.now();
    
    const apiUrl = await apiConfig.getApiUrl();
    await axios.put(`${apiUrl}/tasks/${task._id}`, { 
      completed: !task.completed,
      storage_id: _s1d.value
    });
    task.completed = !task.completed;
    fetchTaskStats();
    addToast('success', task.completed ? t('taskCompleted') : t('taskUncompleted'));
  } catch (error) { 
    console.error("Error updating task:", error);
    
    // If task was deleted (404 error), show appropriate message
    if (error.response?.status === 404) {
      addToast('info', 'Task Deleted', 'This task was deleted by another user.');
    } else {
      addToast('error', t('networkError'), t('networkError2'));
    }
  }
};

const deleteTask = async (taskId) => {
  if (!confirm(t('confirmDeleteTask'))) return;
  
  // Check if this task is currently being recorded
  if (recordingTaskId.value === taskId && mediaRecorder.value && mediaRecorder.value.state === 'recording') {
    addToast('info', t('cannotDeleteWhileRecording'), t('stopRecordingFirst'));
    return;
  }
  
  try {
    const apiUrl = await apiConfig.getApiUrl();
    await axios.delete(`${apiUrl}/tasks/${taskId}`, {
      params: { storage_id: _s1d.value }
    });
    tasks.value = tasks.value.filter(task => task._id !== taskId);
    fetchTaskStats();
    addToast('success', t('taskDeleted'));
  } catch (error) { 
    console.error("Error deleting task:", error);
    addToast('error', t('networkError'), t('networkError2'));
  }
};

// --- EDIT TASK (Inline) ---
const startEdit = (task) => {
  task.isEditing = true;
  task.editTitle = task.title;
  task.editDescription = task.description || '';
  
  // Update activity status
  realtimeSync.updateActivity('editing');
};
const cancelEdit = (task) => {
  task.isEditing = false;
  
  // Update activity status
  realtimeSync.updateActivity('idle');
  
  // Process any pending updates
  processPendingUpdates();
};
const saveEdit = async (task) => {
  try {
    // Track this action to prevent self-notifications
    lastActionTimestamp.value = Date.now();
    
    const apiUrl = await apiConfig.getApiUrl();
    await axios.put(`${apiUrl}/tasks/${task._id}`, {
      title: task.editTitle,
      description: task.editDescription,
      storage_id: _s1d.value
    });
    task.title = task.editTitle;
    task.description = task.editDescription;
    task.isEditing = false;
    
    // Update activity status
    realtimeSync.updateActivity('idle');
    
    // Process any pending updates
    await processPendingUpdates();
    
    addToast('success', t('taskUpdated'));
  } catch (error) { 
    console.error('Error saving task edits:', error);
    
    // If task was deleted (404 error), create backup instead
    if (error.response?.status === 404) {
      console.log('Task was deleted while editing, creating backup...');
      await createTaskBackup(task, 'task deleted while editing');
      // Remove the original task from the list after backup creation
      const taskIndex = tasks.value.findIndex(t => t._id === task._id);
      if (taskIndex !== -1) {
        tasks.value.splice(taskIndex, 1);
      }
      task.isEditing = false;
      addToast('info', 'Task Deleted', 'Your changes were saved as a backup because the task was deleted.');
    } else {
      addToast('error', t('networkError2'), t('networkError2'));
    }
  }
};

// --- API: FILE ATTACHMENTS ---
const handleFileUpload = async (event, taskId) => {
  const file = event.target.files[0];
  if (!file) return;
  
  // Check file size (100MB limit)
  if (file.size > 100 * 1024 * 1024) {
    addToast('error', t('fileUploadError'), t('fileTooLarge'));
    return;
  }
  
  // Track this action to prevent self-notifications
  lastActionTimestamp.value = Date.now();
  
  const formData = new FormData();
  formData.append('file', file);
  formData.append('storage_id', _s1d.value);
  try {
    const apiUrl = await apiConfig.getApiUrl();
    const resp = await axios.post(`${apiUrl}/tasks/${taskId}/upload`, formData);
    
    // Update local task immediately for instant feedback
    if (resp?.data?.file_info) {
      const task = tasks.value.find(t => t._id === taskId);
      if (task) {
        task.attachments = task.attachments || [];
        task.attachments.push(resp.data.file_info);
      }
      addToast('success', t('fileUploadSuccess'));
    }
  } catch (error) { 
    console.error("Error uploading file:", error);
    addToast('error', t('fileUploadError'), error.response?.data?.message || t('networkError2'));
  }
};

const downloadFile = async (fileInfo) => {
  try {
    // If file has blob_url (from Azure Storage), use it directly
    if (typeof fileInfo === 'object' && fileInfo.blob_url) {
      const link = document.createElement('a');
      link.href = fileInfo.blob_url;
      link.setAttribute('download', fileInfo.filename || 'download');
      link.setAttribute('target', '_blank');
      document.body.appendChild(link);
      link.click();
      link.remove();
      addToast('success', t('fileDownloadSuccess'));
      return;
    }
    
    // Otherwise, use the API endpoint
    const filename = typeof fileInfo === 'string' ? fileInfo : (fileInfo.unique_filename || fileInfo.filename);
    const apiUrl = await apiConfig.getApiUrl();
    const response = await axios.get(`${apiUrl}/files/${filename}`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename.split('_').slice(1).join('_')); // Clean filename for user
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    addToast('success', t('fileDownloadSuccess'));
  } catch (error) { 
    console.error("Error downloading file:", error);
    addToast('error', t('fileDownloadError'), t('networkError2'));
  }
};

const toIdString = (val) => {
  if (!val) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'object' && val.$oid) return val.$oid; // in case ObjectId serialized
  if (typeof val === 'object' && val.toString) return val.toString();
  return String(val);
};

const deleteAttachment = async (taskId, attachmentId) => {
  if (!confirm(t('confirmDeleteAttachment'))) return;
  try {
    const apiUrl = await apiConfig.getApiUrl();
    const idStr = toIdString(attachmentId);
    await axios.delete(`${apiUrl}/tasks/${taskId}/attachments/${idStr}`, {
      params: { storage_id: _s1d.value }
    });
    const task = tasks.value.find(t => t._id === taskId);
    if (task) {
      task.attachments = (task.attachments || []).filter(att => {
        const attId = toIdString(att._id);
        const matches = (attId && attId === idStr) || (att.unique_filename && att.unique_filename === idStr);
        return !matches;
      });
      addToast('success', t('fileDeleteSuccess'));
    }
  } catch (error) { 
    console.error("Error deleting attachment:", error);
    addToast('error', t('fileDeleteError'), t('networkError2'));
  }
};

// --- API: AUDIO RECORDING ---
const isRecording = ref(false);
const isRequestingPermission = ref(false);
const mediaRecorder = ref(null);
const recordingTaskId = ref(null);
const currentAudio = ref(null);
const audioPlayer = ref(null);
const recordingStream = ref(null);
const audioChunks = ref([]);

const cleanupRecording = () => {
    // Stop all tracks in the stream
    if (recordingStream.value) {
        recordingStream.value.getTracks().forEach(track => {
            track.stop();
        });
        recordingStream.value = null;
    }
    
    // Clear media recorder
    if (mediaRecorder.value) {
        mediaRecorder.value = null;
    }
    
    audioChunks.value = [];
    isRecording.value = false;
    isRequestingPermission.value = false;
};

const getMimeType = () => {
    // Check support in order of preference for mobile
    const types = [
        'audio/mp4',
        'audio/aac',
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/wav'
    ];
    
    for (const type of types) {
        if (MediaRecorder.isTypeSupported(type)) {
            console.log('Selected MIME type:', type);
            return type;
        }
    }
    
    console.log('Using default MIME type');
    return '';
};

const startRecording = async (taskId) => {
    // If already recording, stop it
    if (isRecording.value) {
        stopRecording();
        return;
    }

    // Check if we're on a secure context (required for mobile)
    if (!window.isSecureContext) {
        addToast('error', t('securityError'), t('audioRequiresHttps'));
        return;
    }

    // Check if getUserMedia is supported
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        addToast('error', t('notSupported'), t('audioNotSupported'));
        return;
    }

    isRequestingPermission.value = true;
    audioChunks.value = [];

    try {
        // Simple audio constraints for maximum mobile compatibility
        const constraints = {
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            }
        };

        console.log('Requesting microphone access...');
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        
        console.log('Microphone access granted');
        recordingStream.value = stream;
        
        // Get supported MIME type
        const mimeType = getMimeType();
        const options = mimeType ? { mimeType } : {};
        
        console.log('Creating MediaRecorder with options:', options);
        mediaRecorder.value = new MediaRecorder(stream, options);
        
        const startTime = Date.now();
        
        // Setup event handlers
        mediaRecorder.value.ondataavailable = (event) => {
            console.log('Data available:', event.data.size, 'bytes');
            if (event.data && event.data.size > 0) {
                audioChunks.value.push(event.data);
            }
        };
        
        mediaRecorder.value.onstart = () => {
            console.log('Recording started');
            isRecording.value = true;
            isRequestingPermission.value = false;
            recordingTaskId.value = taskId;
            
            // Update activity status
            realtimeSync.updateActivity('recording');
            
            addToast('info', t('recordingInProgress'), t('speakNow'));
        };
        
        mediaRecorder.value.onstop = async () => {
            console.log('Recording stopped, chunks:', audioChunks.value.length);
            
            const duration = (Date.now() - startTime) / 1000;
            
            if (audioChunks.value.length === 0) {
                addToast('error', t('audioRecordError'), t('audioNoData'));
                cleanupRecording();
                return;
            }
            
            // Determine blob type
            const detectedType = mediaRecorder.value.mimeType || mimeType || 'audio/webm';
            console.log('Creating blob with type:', detectedType);
            
            const audioBlob = new Blob(audioChunks.value, { type: detectedType });
            console.log('Audio blob created:', audioBlob.size, 'bytes');
            
            if (audioBlob.size === 0) {
                addToast('error', t('audioRecordError'), t('audioNoData'));
                cleanupRecording();
                return;
            }
            
            // Convert to base64
            const reader = new FileReader();
            
            reader.onloadend = async () => {
                try {
                    // Track this action to prevent self-notifications
                    lastActionTimestamp.value = Date.now();
                    
                    console.log('Uploading audio...');
                    const apiUrl = await apiConfig.getApiUrl();
                    const resp = await axios.post(`${apiUrl}/tasks/${recordingTaskId.value}/audio`, {
                        audio_data: reader.result,
                        duration: duration,
                        storage_id: _s1d.value
                    });
                    
                    console.log('Upload successful');
                    
                     // Update local task immediately for instant feedback
                     if (resp?.data?.audio_info) {
                       const task = tasks.value.find(t => t._id === recordingTaskId.value);
                       if (task) {
                         task.audio_notes = task.audio_notes || [];
                         task.audio_notes.push(resp.data.audio_info);
                         
                         // Check if this task was marked for backup after recording
                         if (task._pendingBackup) {
                           console.log('Creating backup after recording completed');
                           await createTaskBackupWithAllData(task, task._backupReason);
                           // Remove the original task from the list
                           const taskIndex = tasks.value.findIndex(t => t._id === recordingTaskId.value);
                           if (taskIndex !== -1) {
                             tasks.value.splice(taskIndex, 1);
                           }
                           addToast('success', t('backupCreatedAfterRecording'), t('taskSavedAsBackup'));
                         }
                       }
                       addToast('success', t('audioUploadSuccess'));
                     }
    } catch (error) {
        console.error("Upload error:", error);
        
        // Check if the task was deleted (404 error)
        if (error.response?.status === 404) {
            console.log('Task was deleted, creating backup with current audio data');
            const task = tasks.value.find(t => t._id === recordingTaskId.value);
            if (task) {
                // Add the audio data to the task before creating backup
                const audioInfo = {
                    _id: `temp_${Date.now()}`,
                    filename: `recording_${Date.now()}.webm`,
                    duration: duration,
                    recorded_at: new Date().toISOString(),
                    audio_data: reader.result
                };
                task.audio_notes = task.audio_notes || [];
                task.audio_notes.push(audioInfo);
                
                // Create backup with all data including the new audio
                await createTaskBackupWithAllData(task, 'task deleted during recording');
                
                // Remove the original task from the list
                const taskIndex = tasks.value.findIndex(t => t._id === recordingTaskId.value);
                if (taskIndex !== -1) {
                    tasks.value.splice(taskIndex, 1);
                }
                
                addToast('success', t('backupCreatedAfterRecording'), t('taskSavedAsBackup'));
            }
        } else {
            addToast('error', t('audioUploadError'), error.response?.data?.message || t('couldNotSaveAudioNote'));
        }
    } finally {
        cleanupRecording();
        // Update activity status
        realtimeSync.updateActivity('idle');
    }
};
            
            reader.onerror = () => {
                console.error('FileReader error');
                addToast('error', t('processingFailed'), t('couldNotProcessAudioData'));
                cleanupRecording();
            };
            
            reader.readAsDataURL(audioBlob);
        };
        
        mediaRecorder.value.onerror = (event) => {
            console.error("MediaRecorder error:", event);
            addToast('error', t('audioRecordError'), t('audioRecordingError'));
            cleanupRecording();
        };
        
        // Start recording - use short timeslice for mobile
        console.log('Starting MediaRecorder...');
        mediaRecorder.value.start(1000);
        
    } catch (error) {
        console.error("Recording error:", error);
        isRequestingPermission.value = false;
        
        let errorMessage = 'Could not start recording';
        
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            errorMessage = 'Microphone permission denied. Please allow access in browser settings.';
        } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
            errorMessage = 'No microphone found on this device';
        } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
            errorMessage = 'Microphone is already in use by another app';
        } else if (error.name === 'OverconstrainedError') {
            errorMessage = 'Microphone does not meet requirements';
        } else if (error.name === 'SecurityError') {
            errorMessage = 'Recording requires HTTPS or localhost';
        }
        
        addToast('error', t('cannotRecord'), errorMessage);
        cleanupRecording();
    }
};

const stopRecording = () => {
    console.log('Stopping recording...');
    
    if (!mediaRecorder.value) {
        cleanupRecording();
        return;
    }
    
    if (mediaRecorder.value.state === 'recording') {
        try {
            mediaRecorder.value.stop();
            // Don't cleanup here - let onstop handler do it
        } catch (error) {
            console.error("Error stopping recording:", error);
            cleanupRecording();
        }
    } else {
        cleanupRecording();
    }
};

const playAudio = async (audioInfo) => {
  const audioId = typeof audioInfo === 'string' ? audioInfo : (audioInfo.unique_filename || audioInfo.filename);
  
  if (currentAudio.value === audioId) {
    audioPlayer.value.pause();
    currentAudio.value = null;
  } else {
    try {
      // If audio has blob_url (from Azure Storage), use it directly
      if (typeof audioInfo === 'object' && audioInfo.blob_url) {
        audioPlayer.value.src = audioInfo.blob_url;
      } else {
        // Otherwise, use the API endpoint
        const filename = typeof audioInfo === 'string' ? audioInfo : (audioInfo.unique_filename || audioInfo.filename);
        const apiUrl = await apiConfig.getApiUrl();
        audioPlayer.value.src = `${apiUrl}/audio/${filename}`;
      }
      await audioPlayer.value.play();
      currentAudio.value = audioId;
    } catch (error) {
      console.error("Error playing audio:", error);
      addToast('error', t('playbackError'), t('cannotPlayAudio'));
      currentAudio.value = null;
    }
  }
};

const deleteAudio = async (taskId, audioId) => {
  if (!confirm(t('confirmDeleteAudio'))) return;
  try {
    const apiUrl = await apiConfig.getApiUrl();
    const idStr = toIdString(audioId);
    await axios.delete(`${apiUrl}/tasks/${taskId}/audio/${idStr}`, {
      params: { storage_id: _s1d.value }
    });
    const task = tasks.value.find(t => t._id === taskId);
    if (task) {
      task.audio_notes = (task.audio_notes || []).filter(a => {
        const aId = toIdString(a._id);
        const matches = (aId && aId === idStr) || (a.filename && a.filename === idStr);
        return !matches;
      });
      addToast('success', t('audioDeleteSuccess'));
    }
    } catch (error) { 
      console.error("Error deleting audio note:", error);
      addToast('error', t('audioDeleteError'), t('networkError2'));
    }
};

// --- HELPERS ---
const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric'
  });
};
const formatDuration = (seconds) => {
  if (isNaN(seconds) || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

// --- DESCRIPTION FORMATTING ---
const formatDescription = (description) => {
  if (!description) return '';
  
  // Convert line breaks to HTML
  return description.replace(/\n/g, '<br>');
};

const getFirstLine = (description) => {
  if (!description) return '';
  
  // Get the first line, removing any leading/trailing whitespace
  const firstLine = description.split('\n')[0].trim();
  
  // Truncate if too long to fit in container (shorter on mobile - 40 characters)
  const maxLength = window.innerWidth <= 640 ? 40 : 80;
  if (firstLine.length > maxLength) {
    return firstLine.substring(0, maxLength - 3);
  }
  
  return firstLine;
};

const isContentTruncated = (description) => {
  if (!description) return false;
  
  // Check if content has multiple lines or if first line is too long
  const lines = description.split('\n');
  const firstLine = lines[0].trim();
  
  // Truncated if multiple lines OR first line is too long (shorter on mobile)
  const maxLength = window.innerWidth <= 640 ? 40 : 80;
  return lines.length > 1 || firstLine.length > maxLength;
};

const toggleTaskDetails = (task) => {
  task.showDetails = !task.showDetails;
};

// --- REAL-TIME SYNC METHODS ---
const initializeRealtimeSync = async () => {
  if (!_s1d.value) return;
  
  // Generate a unique user ID for this session
  userId.value = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  // Set up real-time sync callbacks
  realtimeSync.setCallback('onTaskCreated', handleRemoteTaskCreated);
  realtimeSync.setCallback('onTaskUpdated', handleRemoteTaskUpdated);
  realtimeSync.setCallback('onTaskDeleted', handleRemoteTaskDeleted);
  realtimeSync.setCallback('onUserActivity', handleUserActivity);
  realtimeSync.setCallback('onConnectionChange', handleConnectionChange);
  
  // Connect to real-time sync
  await realtimeSync.connect(_s1d.value, userId.value);
  
  // Update activity status
  realtimeSync.updateActivity('idle');

  // Fetch current online count and subscribe to live updates
  await fetchOnlineCount();
  setupOnlineCountListener();
  
  // Start periodic sync to verify all changes
  startPeriodicSync();
  // Start presence prune safety net
  startActiveUsersPrune();
  
  // Add manual sync trigger for immediate verification
  window.manualSync = async () => {
    console.log('Manual sync triggered');
    await verifyAndSyncAllTasks();
  };
  
  // Add debug functions for testing
  window.debugSocket = () => {
    console.log('DEBUG: Socket connection status:', realtimeSync.isConnected);
    console.log('DEBUG: User ID:', userId.value);
    console.log('DEBUG: Sync enabled:', syncEnabled.value);
  };
  
  window.testSocket = async () => {
    console.log('DEBUG: Testing Socket.IO connection...');
    const apiUrl = await apiConfig.getApiUrl();
    try {
      const response = await fetch(`${apiUrl}/test-socket?storage_id=${_s1d.value}`);
      const result = await response.json();
      // Filter out storage_id from response before logging
      const filteredResult = { ...result };
      delete filteredResult.storage_id;
      console.log('DEBUG: Test socket response:', filteredResult);
    } catch (error) {
      console.error('DEBUG: Test socket error:', error);
    }
  };
  
  // Test the connection after a short delay
  setTimeout(async () => {
    console.log('Testing Socket.IO connection...');
    await realtimeSync.testConnection();
    
    // Test if we can receive events
    console.log('Socket.IO connection status:', realtimeSync.isConnected);
    
    // Add a global test function for debugging
    window.testSocketIO = () => {
      console.log('Manual Socket.IO test');
      realtimeSync.testConnection();
    };
  }, 2000);
};

// (Removed) old online users fetch by presence; replaced by online-count approach

const handleRemoteTaskCreated = (task) => {
  if (!syncEnabled.value) return;
  
  console.log('Remote task created:', task);
  
  // Check if task already exists (prevent duplicates)
  const existingTask = tasks.value.find(t => t._id === task._id);
  if (existingTask) {
    console.log('Task already exists, skipping duplicate:', task._id);
    return;
  }
  
  // Check if this is a recent local creation (within last 2 seconds) to prevent self-duplication
  const now = Date.now();
  const isRecentLocalCreation = (now - lastActionTimestamp.value) < 2000;
  
  if (isRecentLocalCreation) {
    console.log('Ignoring recent local task creation to prevent duplication');
    return;
  }
  
  // Create new task object for duplicate checking
  const newTaskData = {
    title: task.title,
    description: task.description || '',
    completed: task.completed || false
  };
  
  // Check for duplicates before adding
  if (!preventDuplicateTask(newTaskData)) {
    console.log('Duplicate remote task prevented, not adding');
    return;
  }
  
  // Add the new task to the local list
  const newTask = {
    ...task,
    title: newTaskData.title, // Use potentially renamed title
    showDetails: false,
    isEditing: false,
    editTitle: newTaskData.title,
    editDescription: newTaskData.description
  };
  
  tasks.value.unshift(newTask);
  fetchTaskStats();
  addToast('info', t('taskAdded'), t('syncedFromAnotherDevice'));
};

const handleRemoteTaskUpdated = async (data) => {
  if (!syncEnabled.value) return;
  
  console.log('DEBUG: Remote task updated:', data);
  console.log('DEBUG: Update type:', data.update_type);
  console.log('DEBUG: Task ID:', data.task_id);
  console.log('DEBUG: Full data object:', JSON.stringify(data, null, 2));
  
  // Check if this update was made by the current user (within last 2 seconds)
  const now = Date.now();
  const isOwnUpdate = (now - lastActionTimestamp.value) < 2000;
  
  if (isOwnUpdate) {
    console.log('Ignoring own update to prevent self-notification');
    return;
  }
  
  const taskIndex = tasks.value.findIndex(t => t._id === data.task_id);
  if (taskIndex === -1) {
    console.log('Task not found for update:', data.task_id);
    return;
  }
  
  const task = tasks.value[taskIndex];
  
  // Don't update if user is currently editing this task
  if (task.isEditing) {
    // Check if there are unsaved changes
    const hasUnsavedChanges = task.editTitle !== task.title || task.editDescription !== task.description;
    
    if (hasUnsavedChanges) {
      // Handle edit conflict by creating backup and applying update
      await handleEditConflict(task, data);
      return;
    } else {
      // Store the update for later
      pendingUpdates.value.push(data);
      return;
    }
  }
  
  // Update the task
  if (data.task) {
    // Full task update - preserve UI state but update all data
    console.log('Updating full task data:', data.task);
    tasks.value[taskIndex] = {
      ...data.task,
      showDetails: task.showDetails,
      isEditing: false,
      editTitle: data.task.title,
      editDescription: data.task.description || ''
    };
    addToast('info', t('taskUpdated'), t('syncedFromAnotherDevice'));
  } else if (data.update_type && data.update_type.includes('_deleted')) {
    // Handle deletion updates by updating the full task data
    console.log('Handling deletion update:', data.update_type, data.task);
    if (data.task) {
      tasks.value[taskIndex] = {
        ...data.task,
        showDetails: task.showDetails,
        isEditing: false,
        editTitle: data.task.title,
        editDescription: data.task.description || ''
      };
    }
    addToast('info', t('taskUpdated'), t('syncedFromAnotherDevice'));
  } else if (data.update_type === 'attachment_added') {
    // Add attachment to existing task
    console.log('Adding attachment:', data.file_info);
    task.attachments = task.attachments || [];
    // Convert the file_info to proper format
    const newAttachment = {
      ...data.file_info,
      uploaded_at: data.file_info.uploaded_at || new Date().toISOString()
    };
    task.attachments.push(newAttachment);
    addToast('info', t('fileUploadSuccess'), t('syncedFromAnotherDevice'));
  } else if (data.update_type === 'audio_added') {
    // Add audio to existing task
    console.log('Adding audio:', data.audio_info);
    task.audio_notes = task.audio_notes || [];
    // Convert the audio_info to proper format
    const newAudio = {
      ...data.audio_info,
      recorded_at: data.audio_info.recorded_at || new Date().toISOString()
    };
    task.audio_notes.push(newAudio);
    addToast('info', t('audioUploadSuccess'), t('syncedFromAnotherDevice'));
  } else if (data.update_type === 'attachment_deleted') {
    // Handle attachment deletion - update the full task data
    console.log('DEBUG: Processing attachment_deleted event');
    console.log('DEBUG: Task before update:', task);
    console.log('DEBUG: New task data:', data.task);
    console.log('DEBUG: Task attachments before:', task.attachments?.length || 0);
    console.log('DEBUG: Task attachments after:', data.task?.attachments?.length || 0);
    
    tasks.value[taskIndex] = {
      ...data.task,
      showDetails: task.showDetails,
      isEditing: false,
      editTitle: data.task.title,
      editDescription: data.task.description || ''
    };
    console.log('DEBUG: Task updated successfully in local state');
    addToast('info', t('fileDeleteSuccess'), t('syncedFromAnotherDevice'));
  } else if (data.update_type === 'audio_deleted') {
    // Handle audio deletion - update the full task data
    console.log('Audio deleted, updating task:', data.task);
    tasks.value[taskIndex] = {
      ...data.task,
      showDetails: task.showDetails,
      isEditing: false,
      editTitle: data.task.title,
      editDescription: data.task.description || ''
    };
    addToast('info', t('audioDeleteSuccess'), t('syncedFromAnotherDevice'));
  }
  
  fetchTaskStats();
};

const handleRemoteTaskDeleted = async (taskId) => {
  if (!syncEnabled.value) return;
  
  console.log('Remote task deleted:', taskId);
  
  const taskIndex = tasks.value.findIndex(t => t._id === taskId);
  if (taskIndex === -1) {
    console.log('Task not found for deletion:', taskId);
    return;
  }
  
  const task = tasks.value[taskIndex];
  
  // Check if this task is currently being recorded
  if (recordingTaskId.value === taskId && mediaRecorder.value && mediaRecorder.value.state === 'recording') {
    console.log('Task is being recorded, marking for backup after recording ends');
    // Mark the task for backup after recording ends
    task._pendingBackup = true;
    task._backupReason = 'task deleted while recording';
    // Don't remove the task - let the user finish recording
    addToast('warning', t('taskDeletedWhileRecording'), t('backupWillBeCreatedAfterRecording'));
    return;
  }
  
  // Don't delete if user is currently editing this task
  if (task.isEditing) {
    // Check if there are unsaved changes
    const hasUnsavedChanges = task.editTitle !== task.title || task.editDescription !== task.description;
    
    if (hasUnsavedChanges) {
      // Create backup and then remove from list
      await createTaskBackup(task, 'task deleted while editing');
      tasks.value.splice(taskIndex, 1);
      addToast('info', t('taskDeleted'), t('syncedFromAnotherDevice'));
    } else {
      // Store the deletion for later
      pendingUpdates.value.push({ type: 'delete', task_id: taskId });
      return;
    }
  } else {
    // Remove the task
    tasks.value.splice(taskIndex, 1);
    addToast('info', t('taskDeleted'), t('syncedFromAnotherDevice'));
  }
  
  fetchTaskStats();
};

const handleUserActivity = (data) => {
  activeUsers.value[data.user_id] = {
    user_id: data.user_id,
    activity: data.activity,
    timestamp: data.timestamp
  };
  
  // Clean up old user activities (older than 90 seconds)
  const ninetySecondsAgo = Date.now() - (90 * 1000);
  Object.keys(activeUsers.value).forEach(userId => {
    if (new Date(activeUsers.value[userId].timestamp).getTime() < ninetySecondsAgo) {
      delete activeUsers.value[userId];
    }
  });
};

const handleConnectionChange = (connected) => {
  if (connected) {
    addToast('success', t('realtimeSyncConnected'));
    // Refresh online users list on reconnect
    fetchOnlineCount();
  } else {
    addToast('error', t('realtimeSyncDisconnected'));
  }
};

const processPendingUpdates = async () => {
  if (pendingUpdates.value.length === 0) return;
  
  const updates = [...pendingUpdates.value];
  pendingUpdates.value = [];
  
  for (const update of updates) {
    if (update.type === 'delete') {
      await handleRemoteTaskDeleted(update.task_id);
    } else {
      await handleRemoteTaskUpdated(update);
    }
  }
};

// --- PERIODIC SYNC SYSTEM ---
let periodicSyncInterval = null;
let activeUsersPruneInterval = null;

const startPeriodicSync = () => {
  // Clear any existing interval
  if (periodicSyncInterval) {
    clearInterval(periodicSyncInterval);
  }
  
  // Sync every 30 seconds to verify all changes
  periodicSyncInterval = setInterval(async () => {
    if (syncEnabled.value && realtimeSync.isConnected) {
      console.log('Performing periodic sync to verify all changes...');
      await verifyAndSyncAllTasks();
    }
  }, 30000); // 30 seconds
};

// Periodically prune inactive users (client-side safety net)
const startActiveUsersPrune = () => {
  if (activeUsersPruneInterval) {
    clearInterval(activeUsersPruneInterval);
  }
  activeUsersPruneInterval = setInterval(() => {
    const cutoff = Date.now() - (90 * 1000);
    Object.keys(activeUsers.value).forEach(uid => {
      if (new Date(activeUsers.value[uid].timestamp).getTime() < cutoff) {
        delete activeUsers.value[uid];
      }
    });
  }, 30000);
};

const verifyAndSyncAllTasks = async () => {
  try {
    const apiUrl = await apiConfig.getApiUrl();
    const response = await axios.get(`${apiUrl}/tasks`, {
      params: { storage_id: _s1d.value }
    });
    
    if (response.data && response.data.tasks) {
      const serverTasks = response.data.tasks;
      const localTasks = tasks.value;
      
      // Check for tasks that exist on server but not locally
      for (const serverTask of serverTasks) {
        const localTask = localTasks.find(t => t._id === serverTask._id);
        if (!localTask) {
          console.log('Found missing task on server, adding locally:', serverTask._id);
          const newTask = {
            ...serverTask,
            showDetails: false,
            isEditing: false,
            editTitle: serverTask.title,
            editDescription: serverTask.description || ''
          };
          tasks.value.unshift(newTask);
        } else {
          // Check if server task has more recent updates
          const serverUpdated = new Date(serverTask.updated_at || serverTask.created_at);
          const localUpdated = new Date(localTask.updated_at || localTask.created_at);
          
          if (serverUpdated > localUpdated) {
            console.log('Server task is more recent, updating locally:', serverTask._id);
            const taskIndex = localTasks.findIndex(t => t._id === serverTask._id);
            if (taskIndex !== -1) {
              tasks.value[taskIndex] = {
                ...serverTask,
                showDetails: localTask.showDetails,
                isEditing: false,
                editTitle: serverTask.title,
                editDescription: serverTask.description || ''
              };
            }
          }
        }
      }
      
      // Check for tasks that exist locally but not on server (might have been deleted)
      for (let i = localTasks.length - 1; i >= 0; i--) {
        const localTask = localTasks[i];
        const serverTask = serverTasks.find(t => t._id === localTask._id);
        if (!serverTask && !localTask.isEditing) {
          console.log('Found deleted task on server, removing locally:', localTask._id);
          tasks.value.splice(i, 1);
        }
      }
      
      fetchTaskStats();
    }
  } catch (error) {
    console.error('Error during periodic sync:', error);
  }
};

// --- VERSION CONTROL SYSTEM ---
// --- DATA VALIDATION SYSTEM ---


const validateTaskDataForBackup = async (task) => {
  console.log('Validating task data for backup (skip server checks):', task._id);
  
  const validatedTask = {
    ...task,
    attachments: [],
    audio_notes: []
  };
  
  // Validate attachments - only check structure, not server existence
  if (task.attachments && task.attachments.length > 0) {
    console.log('Validating attachments for backup:', task.attachments.length);
    for (const attachment of task.attachments) {
      // Only check if attachment has required fields
      if (attachment._id && attachment.filename && attachment.uploaded_at) {
        validatedTask.attachments.push(attachment);
        console.log('Valid attachment for backup:', attachment.filename);
      } else {
        console.log('Invalid attachment filtered out:', attachment.filename);
      }
    }
  }
  
  // Validate audio notes - only check structure, not server existence
  if (task.audio_notes && task.audio_notes.length > 0) {
    console.log('Validating audio notes for backup:', task.audio_notes.length);
    for (const audioNote of task.audio_notes) {
      // Only check if audio has required fields and valid duration
      if (audioNote._id && audioNote.filename && audioNote.recorded_at && 
          audioNote.duration && audioNote.duration > 0) {
        validatedTask.audio_notes.push(audioNote);
        console.log('Valid audio for backup:', audioNote.filename);
      } else {
        console.log('Invalid audio filtered out:', audioNote.filename);
      }
    }
  }
  
  console.log(`Backup validation complete: ${validatedTask.attachments.length} valid attachments, ${validatedTask.audio_notes.length} valid audio notes`);
  return validatedTask;
};


const createTaskBackupWithAllData = async (task, reason) => {
  try {
    console.log('Creating backup with all data for task:', task._id);
    
    // Validate task data before creating backup (skip server checks for deleted tasks)
    const validatedTask = await validateTaskDataForBackup(task);
    
    // Log validation results
    const originalAttachments = task.attachments ? task.attachments.length : 0;
    const originalAudioNotes = task.audio_notes ? task.audio_notes.length : 0;
    const validAttachments = validatedTask.attachments.length;
    const validAudioNotes = validatedTask.audio_notes.length;
    
    console.log(`Validation results: ${validAttachments}/${originalAttachments} attachments valid, ${validAudioNotes}/${originalAudioNotes} audio notes valid`);
    
    // Create backup task object with validated data only
    const backupTaskData = {
      title: validatedTask.title + ' backup',
      description: validatedTask.description,
      completed: validatedTask.completed,
      storage_id: _s1d.value,
      attachments: validatedTask.attachments, // Only valid attachments
      audio_notes: validatedTask.audio_notes,  // Only valid audio notes
      is_backup: true,
      original_id: task._id,
      backup_reason: reason
    };
    
    const apiUrl = await apiConfig.getApiUrl();
    const response = await axios.post(`${apiUrl}/tasks`, backupTaskData);
    
    // Add the backup task to the local list
    const backupTask = {
      ...response.data,
      showDetails: false,
      isEditing: false,
      editTitle: response.data.title,
      editDescription: response.data.description || ''
    };
    
    tasks.value.unshift(backupTask);
    fetchTaskStats();
    
    console.log('Backup created successfully:', backupTask._id);
    console.log(`Backup contains: ${validAttachments} valid attachments, ${validAudioNotes} valid audio notes`);
    
    // Show user-friendly message about validation results
    if (originalAttachments > validAttachments || originalAudioNotes > validAudioNotes) {
      addToast('info', t('backupCreatedAfterRecording'), `${t('taskSavedAsBackup')} ${t('invalidDataFiltered')}`);
    } else {
      addToast('success', t('backupCreatedAfterRecording'), t('taskSavedAsBackup'));
    }
  } catch (error) {
    console.error('Error creating backup with all data:', error);
    addToast('error', t('backupCreationError'), t('networkError2'));
  }
};

const createTaskBackup = async (task, reason) => {
  try {
    // Create backup with proper naming
    const backupTitle = `${task.editTitle || task.title} backup`;
    const backupDescription = task.editDescription || task.description;
    
    // Save backup to database
    const apiUrl = await apiConfig.getApiUrl();
    const response = await axios.post(`${apiUrl}/tasks`, {
      title: backupTitle,
      description: backupDescription,
      completed: task.completed,
      storage_id: _s1d.value,
      attachments: task.attachments || [],
      audio_notes: task.audio_notes || [],
      is_backup: true,
      original_id: task._id,
      backup_reason: reason
    });
    
    // Add to local tasks list
    const backup = {
      ...response.data,
      showDetails: false,
      isEditing: false,
      editTitle: response.data.title,
      editDescription: response.data.description || ''
    };
    
    tasks.value.unshift(backup);
    fetchTaskStats();
    
    addToast('info', 'Backup Created', `Task backed up due to ${reason}`);
    return backup;
  } catch (error) {
    console.error('Error creating backup:', error);
    addToast('error', 'Backup Failed', 'Could not create backup task');
    return null;
  }
};

const handleEditConflict = async (task, remoteUpdate) => {
  // Create a backup of the current edit
  await createTaskBackup(task, 'edit conflict');
  
  // Apply the remote update to the original task
  if (remoteUpdate.task) {
    task.title = remoteUpdate.task.title;
    task.description = remoteUpdate.task.description;
    task.editTitle = remoteUpdate.task.title;
    task.editDescription = remoteUpdate.task.description;
    task.isEditing = false; // Stop editing mode
  }
  
  // Show conflict resolution dialog
  addToast('info', 'Edit Conflict', 'Your changes were saved as a backup. The latest version is now displayed.');
};

const restoreFromBackup = async (backupTask) => {
  try {
    // Create a new task from the backup
    const apiUrl = await apiConfig.getApiUrl();
    const response = await axios.post(`${apiUrl}/tasks`, {
      title: backupTask.title.replace(' backup', ''), // Remove backup suffix
      description: backupTask.description,
      completed: backupTask.completed,
      storage_id: _s1d.value,
      attachments: backupTask.attachments || [],
      audio_notes: backupTask.audio_notes || []
    });
    
    // Add the restored task to the local list
    const restoredTask = {
      ...response.data,
      showDetails: false,
      isEditing: false,
      editTitle: response.data.title,
      editDescription: response.data.description || ''
    };
    
    tasks.value.unshift(restoredTask);
    
    // Delete the backup task from database and local list
    await axios.delete(`${apiUrl}/tasks/${backupTask._id}?storage_id=${_s1d.value}`);
    const backupIndex = tasks.value.findIndex(t => t._id === backupTask._id);
    if (backupIndex !== -1) {
      tasks.value.splice(backupIndex, 1);
    }
    
    fetchTaskStats();
    
    addToast('success', t('taskRestored'), t('taskRestoredFromBackup'));
  } catch (error) {
    console.error('Error restoring task:', error);
    addToast('error', t('restoreError'), t('networkError2'));
  }
};

// --- DUPLICATE PREVENTION SYSTEM ---
const checkAndResolveDuplicates = () => {
  const seenTasks = new Map();
  const tasksToRemove = [];
  const tasksToRename = [];
  
  tasks.value.forEach((task, index) => {
    const key = `${task.title}_${task.description || ''}`;
    
    if (seenTasks.has(key)) {
      const existingTask = seenTasks.get(key);
      
      // If content is identical, mark for removal
      if (task.description === existingTask.description && 
          task.completed === existingTask.completed) {
        tasksToRemove.push(index);
        console.log('Removing duplicate task:', task.title);
      } else {
        // If content is different, rename the newer one
        const newName = `${task.title}_2`;
        tasksToRename.push({ index, newName });
        console.log('Renaming duplicate task:', task.title, 'to', newName);
      }
    } else {
      seenTasks.set(key, task);
    }
  });
  
  // Remove duplicates (in reverse order to maintain indices)
  tasksToRemove.reverse().forEach(index => {
    tasks.value.splice(index, 1);
  });
  
  // Rename duplicates
  tasksToRename.forEach(({ index, newName }) => {
    tasks.value[index].title = newName;
    tasks.value[index].editTitle = newName;
  });
  
  if (tasksToRemove.length > 0 || tasksToRename.length > 0) {
    console.log(`Resolved ${tasksToRemove.length} duplicates and renamed ${tasksToRename.length} tasks`);
    fetchTaskStats();
  }
};

const preventDuplicateTask = (newTask) => {
  // Check if a task with the same title already exists
  const existingTask = tasks.value.find(t => 
    t.title.toLowerCase().trim() === newTask.title.toLowerCase().trim()
  );
  
  if (existingTask) {
    // If content is identical, don't add the new task
    if (existingTask.description === newTask.description && 
        existingTask.completed === newTask.completed) {
      console.log('Preventing duplicate task:', newTask.title);
      return false;
    } else {
      // If content is different, rename the new task
      let counter = 2;
      let newName = `${newTask.title}_${counter}`;
      
      while (tasks.value.some(t => t.title === newName)) {
        counter++;
        newName = `${newTask.title}_${counter}`;
      }
      
      newTask.title = newName;
      newTask.editTitle = newName;
      console.log('Renamed duplicate task to:', newName);
    }
  }
  
  return true;
};

const toggleRealtimeSync = async () => {
  // Save setting to localStorage
  localStorage.setItem('realtimeSyncEnabled', syncEnabled.value.toString());
  
  if (syncEnabled.value) {
    // Enable real-time sync
    await initializeRealtimeSync();
    addToast('success', t('realtimeSyncEnabled'), t('realtimeSyncEnabledDescription'));
  } else {
    // Disable real-time sync
    if (realtimeSync) {
      realtimeSync.disconnect();
    }
    addToast('info', t('realtimeSyncDisabled'), t('realtimeSyncDisabledDescription'));
  }
};

// --- TOAST SYSTEM ---
const addToast = (type, title, message = '') => {
  // Create a unique key for this notification to prevent spam
  const notificationKey = `${type}-${title}-${message}`;
  
  // Check if we already showed this notification recently (within 3 seconds)
  if (recentNotifications.value.has(notificationKey)) {
    return;
  }
  
  // Add to recent notifications and remove after 3 seconds
  recentNotifications.value.add(notificationKey);
  setTimeout(() => {
    recentNotifications.value.delete(notificationKey);
  }, 3000);
  
  const id = Date.now() + Math.random();
  const toast = { id, type, title, message };
  toasts.value.push(toast);
  
  // Auto remove after 5 seconds
  setTimeout(() => {
    removeToast(id);
  }, 5000);
};

const removeToast = (id) => {
  const index = toasts.value.findIndex(toast => toast.id === id);
  if (index > -1) {
    toasts.value.splice(index, 1);
  }
};

// --- CUSTOM CONFIRM DIALOG ---
const handleConfirmOk = () => {
  showConfirmDialog.value = false;
  if (confirmDialog.value.onConfirm) {
    confirmDialog.value.onConfirm(true);
  }
};

const handleConfirmCancel = () => {
  showConfirmDialog.value = false;
  if (confirmDialog.value.onConfirm) {
    confirmDialog.value.onConfirm(false);
  }
};

// --- DIALOG CLOSE HANDLER ---
const handleUserDialogClose = () => {
  showUserDialog.value = false;
  // Hide generated ID when dialog closes
  generatedId.value = '';
  showGeneratedId.value = false;
};

// --- CLIPBOARD COPY ---
const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      document.body.removeChild(textArea);
      return true;
    } catch (err) {
      document.body.removeChild(textArea);
      return false;
    }
  }
};

// --- DEVICE ID MANAGEMENT ---
const copyStorageId = async () => {
  isRegenerating.value = true;
  
  try {
    const apiUrl = await apiConfig.getApiUrl();
    const _os1d = _s1d.value;
    
    // Generate new storage ID
    const _ns1d = storageManager.generateStorageId();
    
    // Migrate all tasks to new storage ID
    const response = await axios.post(`${apiUrl}/storage/migrate`, {
      old_storage_id: _os1d,
      new_storage_id: _ns1d
    });
    
    if (response.data.success) {
      // Update local storage ID
      _s1d.value = _ns1d;
      storageManager.setStorageId(_ns1d);
      
      // Store the generated ID for display
      generatedId.value = _ns1d;
      showGeneratedId.value = false; // Hidden by default
      
      // Copy to clipboard
      const copied = await copyToClipboard(_ns1d);
      
      // Refresh tasks and stats
      await fetchTasks();
      await fetchTaskStats();
      
      if (copied) {
        addToast('success', t('storageIdRegenerated'), t('newIdInfo'));
      } else {
        addToast('error', t('storageIdRegenerated'), 'Failed to copy to clipboard');
      }
      
    } else {
      throw new Error(response.data.error || 'Migration failed');
    }
  } catch (error) {
    console.error('Error regenerating storage ID:', error);
    addToast('error', 'Error', 'Error regenerating storage ID. Please try again.');
  } finally {
    isRegenerating.value = false;
  }
};

// --- EXTERNAL DEVICE ID MANAGEMENT ---
const useExternalStorageId = async () => {
  if (!_xs1d.value || _xs1d.value.length < 8) {
    addToast('error', 'Invalid Input', t('storageIdPlaceholder'));
    return;
  }
  
  isUsingExternalId.value = true;
  
  try {
    const apiUrl = await apiConfig.getApiUrl();
    
    // Test if the external storage ID exists by trying to get tasks
    await axios.get(`${apiUrl}/tasks`, {
      params: { storage_id: _xs1d.value }
    });
    
    // If we get here, the storage ID exists
    // Update local storage ID to the external one
    _s1d.value = _xs1d.value;
    storageManager.setStorageId(_xs1d.value);
    
    // Refresh tasks and stats
    await fetchTasks();
    await fetchTaskStats();
    
    addToast('success', t('externalIdConnected'));
    showUserDialog.value = false;
    _xs1d.value = '';
    
  } catch (error) {
    console.error('Error connecting to external storage:', error);
    if (error.response?.status === 400) {
      addToast('error', 'Invalid Storage ID', t('invalidStorageId'));
    } else {
      addToast('error', 'Connection Error', t('errorConnectingToStorage'));
    }
  } finally {
    isUsingExternalId.value = false;
  }
};

// --- LIFECYCLE HOOKS ---
// Handle page visibility changes (e.g., when user switches tabs)
const handleVisibilityChange = () => {
  if (document.hidden && isRecording.value) {
    // If page becomes hidden while recording, stop recording
    console.log('Page hidden while recording, stopping...');
    stopRecording();
  }
};

onMounted(async () => {
  // --- SEO & Social Media Meta Tags ---
  updateMetaTags();
  
  // Initialize storage ID
  _s1d.value = storageManager.getStorageId();
  //console.log('Storage ID:', _s1d.value);
  
  loadTheme();
  fetchTasks();
  fetchTaskStats();
  
  // Initialize real-time sync only if enabled
  if (syncEnabled.value) {
    await initializeRealtimeSync();
  }
  
  document.addEventListener('visibilitychange', handleVisibilityChange);
});

onBeforeUnmount(() => {
  // Ensure all recording is stopped and cleaned up
  if (isRecording.value) {
    cleanupRecording();
  }
  
  // Stop any playing audio
  if (audioPlayer.value) {
    audioPlayer.value.pause();
    audioPlayer.value.src = '';
  }
  
  // Clean up periodic sync
  if (periodicSyncInterval) {
    clearInterval(periodicSyncInterval);
    periodicSyncInterval = null;
  }
  if (activeUsersPruneInterval) {
    clearInterval(activeUsersPruneInterval);
    activeUsersPruneInterval = null;
  }
  
  // Disconnect real-time sync
  realtimeSync.disconnect();
  
  // Clean up event listeners
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});

// Fetch current online connections count for the active storage
const fetchOnlineCount = async () => {
  try {
    const apiUrl = await apiConfig.getApiUrl();
    const res = await fetch(`${apiUrl}/storage/online-count?storage_id=${encodeURIComponent(_s1d.value)}`);
    if (!res.ok) return;
    const data = await res.json();
    onlineCount.value = Number(data.count || 0);
  } catch (e) {
    // ignore
  }
};

// Listen to socket event that broadcasts online counts
const setupOnlineCountListener = () => {
  if (!realtimeSync || !realtimeSync.socket) return;
  realtimeSync.socket.off?.('storage_online_count');
  realtimeSync.socket.on('storage_online_count', (data) => {
    if (data?.storage_id === _s1d.value) {
      onlineCount.value = Number(data.count || 0);
    }
  });
};

</script>

<style>
/* ------------------------------- */
/* --- DESIGN SYSTEM & THEMES --- */
/* ------------------------------- */
:root {
  /* Spacing & Sizing */
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem; --space-4: 1rem;
  --space-5: 1.25rem; --space-6: 1.5rem; --space-8: 2rem; --space-10: 2.5rem;
  
  /* Border Radius */
  --radius-sm: 0.25rem; --radius-md: 0.5rem; --radius-lg: 0.75rem; --radius-xl: 1rem;
  
  /* Transitions */
  --transition-fast: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* --- Dark Theme (Default) --- */
:root, [data-theme="dark"] {
  --bg-primary: #111217;      /* page background */
  --bg-secondary: #1e293b;  /* card background */
  --bg-tertiary: #334155;    /* hover, inputs */
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --border-color: #334155;
  --shadow-color: rgba(0, 0, 0, 0.2);

  --primary: #3b82f6; --primary-light: #1e3a8a;
  --success: #10b981; --success-light: #064e3b;
  --warning: #f59e0b; --warning-light: #78350f; --warning-bg: #78350f; --warning-border: #f59e0b;
  --danger: #ef4444;  --danger-light: #7f1d1d;
  --info: #6366f1;    --info-light: #3730a3;
}

/* --- Light Theme --- */
[data-theme="light"] {
  --bg-primary: #f1f5f9;
  --bg-secondary: #ffffff;
  --bg-tertiary: #e2e8f0;
  --text-primary: #0f172a;
  --text-secondary: #64748b;
  --border-color: #e2e8f0;
  --shadow-color: rgba(0, 0, 0, 0.08);
  
  --primary-light: #dbeafe; --success-light: #d1fae5;
  --warning-light: #fef3c7; --warning-bg: #fef3c7; --warning-border: #f59e0b; --danger-light: #fee2e2;
  --info-light: #e0e7ff;
}

/* ------------------------------- */
/* --- GLOBAL & RESET STYLES --- */
/* ------------------------------- */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 16px; scroll-behavior: smooth; }
body {
  font-family: 'Inter', sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.3s, color 0.3s;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
svg { width: 1.25rem; height: 1.25rem; }

/* ------------------------------- */
/* --- LAYOUT & MAIN ELEMENTS --- */
/* ------------------------------- */
.todo-app-container {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-4);
}

.quick-toggles {
  position: fixed; top: var(--space-4); right: var(--space-4); z-index: 10;
  display: flex; gap: var(--space-2);
}

.storage-toggle-btn {
  position: fixed;
  top: var(--space-4);
  left: var(--space-4);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  height: 2.5rem;
}

.storage-toggle-btn:hover {
  background-color: var(--bg-hover);
  border-color: var(--primary);
  transform: translateY(-1px);
  color: var(--text-primary);
}

.storage-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  color: var(--text-secondary);
}

.storage-toggle-btn:hover .storage-icon {
  color: var(--text-primary);
}

.storage-label {
  white-space: nowrap;
}

.sync-status {
  position: fixed; top: var(--space-4); left: var(--space-4); z-index: 10;
}

.sync-indicator {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background-color: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  font-size: 0.875rem;
  box-shadow: 0 4px 8px var(--shadow-color);
  flex-direction: column;
  align-items: flex-start;
  min-width: 200px;
}

.user-activity-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-top: var(--space-2);
  width: 100%;
}

.user-activity-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.75rem;
}

.activity-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.activity-dot.editing {
  background-color: var(--warning);
  animation: pulse-dot 1.5s infinite;
}

.activity-dot.recording {
  background-color: var(--danger);
  animation: pulse-dot 1s infinite;
}

.activity-dot.idle {
  background-color: var(--success);
}

.activity-text {
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.sync-dot {
  width: 0.5rem; height: 0.5rem;
  background-color: var(--success);
  border-radius: 50%;
  animation: pulse-dot 2s infinite;
}

/* --- Active users footer (plain text) --- */
.online-users-line {
  margin-top: var(--space-1);
  color: var(--text-secondary);
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}
.lang-toggle-btn {
  display: flex; align-items: center; justify-content: center;
  height: 2.5rem; padding: 0 var(--space-3);
  background-color: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  cursor: pointer; transition: var(--transition-fast);
  box-shadow: 0 4px 8px var(--shadow-color);
}
.lang-toggle-btn:hover { color: var(--text-primary); border-color: var(--primary); }

.theme-toggle-btn {
  position: static;
  display: flex; align-items: center; justify-content: center;
  width: 2.5rem; height: 2.5rem;
  background-color: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: var(--transition-fast);
  box-shadow: 0 4px 8px var(--shadow-color);
}
.theme-toggle-btn:hover {
  color: var(--text-primary);
  transform: translateY(-2px);
  border-color: var(--primary);
}

.app-header { text-align: center; }
.header-icon-wrapper {
    display: inline-flex;
    padding: var(--space-4);
    background-color: var(--primary); /* Use the main accent color for the background */
    color: white;                     /* Make the icon inside pure white */
    border-radius: var(--radius-xl);
    margin-bottom: var(--space-2);
    /* Optional: Add a subtle glow effect */
    box-shadow: 0 0 20px rgba(79, 70, 229, 0.4);
}
.header-icon-wrapper svg { width: 2rem; height: 2rem; }
.app-title { font-size: 2.5rem; font-weight: 800; }
.app-subtitle { color: var(--text-secondary); margin-top: var(--space-2); font-size: 1.1rem; }

/* --- ADDED: Styles for the new header info --- */
.header-info {
  margin-top: var(--space-4);
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: 1.5;
}
.header-info p {
  margin: 0;
}
.storage-info {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-style: italic;
  margin-top: var(--space-1);
}

.app-main-content { display: grid; gap: var(--space-6); }
.card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: 0 4px 12px var(--shadow-color);
  transition: var(--transition-fast);
}

/* ------------------------------- */
/* --- FORMS & INPUTS --- */
/* ------------------------------- */
.task-form { display: grid; gap: var(--space-4); }
.input-group { 
  position: relative; 
  width: 100%;
  max-width: none;
}
.input-icon {
  position: absolute;
  top: 50%;
  left: var(--space-4);
  transform: translateY(-50%);
  color: var(--text-secondary);
  pointer-events: none;
}
.form-input, .form-textarea {
  width: 100%;
  max-width: none;
  background-color: var(--bg-tertiary);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  /* Keep extra left padding for leading icons in non-edit fields */
  padding: var(--space-3) var(--space-4) var(--space-3) 3rem;
  color: var(--text-primary);
  font-family: inherit;
  font-size: 1rem;
  transition: var(--transition-fast);
}
.edit-inline .form-input, .edit-inline .form-textarea { padding-left: var(--space-4); }
.form-input:focus, .form-textarea:focus {
  outline: none;
  border-color: var(--primary);
  background-color: var(--bg-primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}
.form-textarea { resize: vertical; min-height: 80px; }

/* Spacing between inline edit inputs */
.edit-inline { 
  display: grid; 
  gap: var(--space-2);
  width: 100%;
  max-width: none;
}
.edit-title-input { 
  margin-bottom: var(--space-1);
  width: 100%;
  max-width: none;
}
.edit-actions { 
  display: flex; 
  gap: var(--space-4);
  justify-content: flex-start;
}

/* ------------------------------- */
/* --- BUTTONS --- */
/* ------------------------------- */
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-fast);
  white-space: nowrap;
}
.btn:hover { transform: translateY(-2px); }
.btn:active { transform: translateY(0); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-primary { background-color: var(--primary); color: white; }
.btn-primary:hover { filter: brightness(1.1); }
.btn-submit { padding: var(--space-3) var(--space-6); font-size: 1rem; }

.btn-secondary { background-color: var(--bg-tertiary); color: var(--text-secondary); }
.btn-secondary:hover { background-color: var(--border-color); color: var(--text-primary); }

.btn-danger { background-color: var(--danger); color: white; }
.btn-danger:hover { background-color: var(--danger-light); color: var(--danger); }

.btn-success { background-color: var(--success); color: white; }
.btn-success:hover { background-color: var(--success-light); color: var(--success); }

.btn-outline { background-color: transparent; color: var(--text-secondary); border-color: var(--border-color); }
.btn-outline:hover { border-color: var(--primary); color: var(--primary); }

/* ------------------------------- */
/* --- TASK STATS & LIST --- */
/* ------------------------------- */
.task-stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--space-4); }
.stat-card { display: flex; align-items: center; gap: var(--space-4); }

/* Filter Button Styles */
.filter-button {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  background: var(--bg-secondary);
  text-align: left;
}

.filter-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--shadow-color);
}

.filter-active {
  border-color: var(--success);
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2), 0 4px 20px rgba(34, 197, 94, 0.15);
}

.filter-active[data-filter="pending"] {
  border-color: var(--warning);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2), 0 4px 20px rgba(245, 158, 11, 0.15);
}

/* All filter shows purple outline that stays lit then fades away */
.filter-active[data-filter="all"] {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(147, 51, 234, 0.2), 0 4px 20px rgba(147, 51, 234, 0.15);
  animation: fadeOutline 2s ease-out forwards;
}

@keyframes fadeOutline {
  0% {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(147, 51, 234, 0.2), 0 4px 20px rgba(147, 51, 234, 0.15);
  }
  50% {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(147, 51, 234, 0.2), 0 4px 20px rgba(147, 51, 234, 0.15);
  }
  100% {
    border-color: transparent;
    box-shadow: none;
  }
}

/* Keep original number styling */
.filter-button .stat-number {
  color: var(--text-primary);
  font-weight: 600;
}

.filter-button .stat-label {
  color: var(--text-secondary);
}
.stat-icon-wrapper {
  display: flex; padding: var(--space-3); border-radius: var(--radius-lg);
}
.stat-icon-wrapper.success { background-color: var(--success-light); color: var(--success); }
.stat-icon-wrapper.warning { background-color: var(--warning-light); color: var(--warning); }
.stat-icon-wrapper.info    { background-color: var(--info-light);    color: var(--info); }
.stat-number { font-size: 1.75rem; font-weight: 700; line-height: 1; }
.stat-label { font-size: 0.875rem; color: var(--text-secondary); }

.task-list-section { display: grid; gap: var(--space-4); }
.task-card { transition: var(--transition-slow); }
.task-card.completed { opacity: 0.6; }
.task-card.completed .task-title { text-decoration: line-through; }
.task-card.is-backup { 
  border-left: 4px solid var(--warning);
  background-color: var(--warning-light);
}

.task-header { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-4); }
.task-main-info { display: flex; align-items: flex-start; gap: var(--space-4); flex-grow: 1; }
.task-checkbox {
  flex-shrink: 0;
  width: 1.5rem; height: 1.5rem;
  border: 2px solid var(--border-color);
  border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  background-color: var(--bg-primary);
  transition: var(--transition-fast);
}
.task-card:hover .task-checkbox { border-color: var(--primary); }
.task-card.completed .task-checkbox { background-color: var(--success); border-color: var(--success); }
.checkmark { color: white; }
.task-text-content {
    padding-top: 2px;
    width: 100%;
    flex: 1;
}
.task-title { font-weight: 600; font-size: 1.1rem; margin-bottom: var(--space-1); }
.task-title-row { display: flex; align-items: center; gap: var(--space-2); }
.backup-indicator { display: flex; align-items: center; }
.backup-badge {
  background-color: var(--warning);
  color: white;
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;
}
.task-description { color: var(--text-secondary); font-size: 0.9rem; }

/* Description container and text wrapping */
.task-description-container {
  margin-top: var(--space-1);
}

.task-description {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.4;
  word-wrap: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
  box-sizing: border-box;
}

.task-description-preview {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-description-full {
  white-space: pre-wrap;
  word-break: break-word;
}
.task-actions { display: flex; gap: var(--space-2); }
.task-actions .btn { padding: var(--space-2); } /* smaller icon buttons */
.task-actions .btn svg { width: 1rem; height: 1rem; }

.task-meta {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2) var(--space-4);
    margin-top: var(--space-4);
    padding-left: calc(1.5rem + var(--space-4)); /* align with text */
    font-size: 0.8rem;
    color: var(--text-secondary);
}
.meta-item {
    display: flex;
    align-items: center;
    gap: var(--space-2);
}
.meta-item svg {
    width: 0.875rem;
    height: 0.875rem;
}

/* ------------------------------- */
/* --- TASK DETAILS & MEDIA --- */
/* ------------------------------- */
.task-details-content {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-color);
  display: grid;
  gap: var(--space-6);
}
.add-media-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
.media-upload-box {
    background-color: var(--bg-tertiary);
    border: 2px dashed var(--border-color);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    text-align: center;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: var(--space-2);
    transition: var(--transition-fast);
}
.media-upload-box:hover { border-color: var(--primary); }
.media-upload-box h4 { font-size: 0.9rem; }
.media-upload-box p { font-size: 0.8rem; color: var(--text-secondary); margin-bottom: var(--space-2); }
.media-icon { color: var(--text-secondary); width: 1.5rem; height: 1.5rem; }
.file-input { width: 0.1px; height: 0.1px; opacity: 0; overflow: hidden; position: absolute; z-index: -1; }
.file-input + label { cursor: pointer; display: inline-block; }

.btn-record { background-color: var(--success); color: white; }
.btn-record.is-recording { background-color: var(--danger); animation: pulse-bg 1.5s infinite; }
.btn-record.is-requesting { background-color: var(--warning); animation: pulse-bg 1.5s infinite; }
.btn-record:disabled { opacity: 0.6; cursor: not-allowed; }
.record-dot {
    width: 0.5rem; height: 0.5rem;
    background-color: white;
    border-radius: 50%;
    transition: var(--transition-fast);
}
.btn-record.is-recording .record-dot {
    animation: pulse-dot 1.5s infinite;
}

.media-lists { display: grid; gap: var(--space-4); }
.media-list h4 { margin-bottom: var(--space-2); font-size: 1rem; }
.media-item {
    display: flex; justify-content: space-between; align-items: center;
    background-color: var(--bg-tertiary);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-md);
}
.media-info { display: flex; align-items: center; gap: var(--space-2); font-size: 0.9rem; }
.audio-duration { font-style: italic; color: var(--text-secondary); }
.media-actions { display: flex; gap: var(--space-2); }
.media-actions .btn { padding: var(--space-2); }
.media-actions .btn svg { width: 1rem; height: 1rem; }

/* ------------------------------- */
/* --- ANIMATIONS & TRANSITIONS --- */
/* ------------------------------- */
.task-list-enter-active,
.task-list-leave-active { transition: all 0.5s ease; }
.task-list-enter-from,
.task-list-leave-to { opacity: 0; transform: translateX(30px); }

.slide-fade-enter-active { transition: all 0.3s ease-out; }
.slide-fade-leave-active { transition: all 0.3s cubic-bezier(1, 0.5, 0.8, 1); }
.slide-fade-enter-from,
.slide-fade-leave-to { transform: translateY(-10px); opacity: 0; }

@keyframes pulse-bg {
  0% { box-shadow: 0 0 0 0 var(--danger-light); }
  70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

@keyframes pulse-dot {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

/* ------------------------------- */
/* --- USER MANAGEMENT --- */
/* ------------------------------- */
.user-management-btn {
  position: fixed;
  bottom: var(--space-4);
  left: var(--space-4);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background-color: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: var(--transition-fast);
  box-shadow: 0 4px 12px var(--shadow-color);
  font-size: 0.875rem;
  font-weight: 500;
}

.user-management-btn:hover {
  color: var(--text-primary);
  border-color: var(--primary);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px var(--shadow-color);
}

.user-icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* Sync Toggle Section */
.sync-toggle-section {
  margin-bottom: var(--space-6);
  padding: var(--space-4);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.sync-toggle-label {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
  font-weight: 500;
}

.sync-toggle-input {
  width: 1.25rem;
  height: 1.25rem;
  accent-color: var(--primary-color);
}

.sync-toggle-text {
  color: var(--text-primary);
}

.sync-toggle-description {
  margin-top: var(--space-2);
  margin-left: calc(1.25rem + var(--space-3));
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

/* Tab Navigation */
.tab-navigation {
  display: flex;
  gap: var(--space-1);
  margin-bottom: var(--space-6);
  padding: var(--space-1);
  background-color: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background-color: transparent;
  color: var(--text-secondary);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: 0.875rem;
  font-weight: 500;
}

.tab-btn:hover {
  background-color: var(--bg-primary);
  color: var(--text-primary);
}

.tab-btn.active {
  background-color: var(--primary);
  color: white;
}

.tab-icon {
  width: 1rem;
  height: 1rem;
}

/* Tab Content */
.tab-content {
  min-height: 300px;
}

.tab-panel {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Generated ID Section */
.generated-id-section {
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-color);
}

.generated-id-display {
  display: grid;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.generated-id-display label {
  font-weight: 500;
  color: var(--text-primary);
}

.generated-id-info {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background-color: var(--success-light);
  border: 1px solid var(--success);
  border-radius: var(--radius-md);
}

.generated-id-info .info-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: var(--success);
  flex-shrink: 0;
  margin-top: 2px;
}

.generated-id-info p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--success);
  line-height: 1.4;
}

/* Dark mode overrides for generated ID info */
[data-theme="dark"] .generated-id-info .info-icon,
[data-theme="dark"] .generated-id-info p {
  color: #ffffff;
}

.copy-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  font-size: 1rem;
}

.copy-icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* Custom Confirm Dialog */
.confirm-dialog {
  max-width: 400px;
}

.confirm-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.confirm-icon {
  width: 1.5rem;
  height: 1.5rem;
  color: var(--warning);
}

.confirm-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.confirm-body {
  margin-bottom: var(--space-6);
}

.confirm-body p {
  margin: 0;
  line-height: 1.5;
  color: var(--text-secondary);
}

.confirm-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: flex-end;
}

/* Toast System */
.toast-container {
  position: fixed;
  bottom: var(--space-4);
  right: var(--space-4);
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 400px;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 24px var(--shadow-color);
  min-width: 300px;
  backdrop-filter: blur(8px);
  animation: toastSlideIn 0.3s ease-out;
}

@keyframes toastSlideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.toast.success {
  border-left: 4px solid var(--success);
  background-color: var(--success-light);
}

.toast.error {
  border-left: 4px solid var(--danger);
  background-color: var(--danger-light);
}

.toast.info {
  border-left: 4px solid var(--info);
  background-color: var(--info-light);
}

.toast.warning {
  border-left: 4px solid var(--warning);
  background-color: var(--warning-light);
}

.toast-content {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  flex: 1;
}

.toast-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
  margin-top: 2px;
}

.toast.success .toast-icon {
  color: var(--success);
}

.toast.error .toast-icon {
  color: var(--danger);
}

.toast.info .toast-icon {
  color: var(--info);
}

.toast.warning .toast-icon {
  color: var(--warning);
}

/* Dark mode overrides for toast notifications */
[data-theme="dark"] .toast.success .toast-icon,
[data-theme="dark"] .toast.success .toast-message {
  color: #ffffff;
}

[data-theme="dark"] .toast.warning .toast-icon,
[data-theme="dark"] .toast.warning .toast-message {
  color: #ffffff;
}

[data-theme="dark"] .toast.info .toast-icon,
[data-theme="dark"] .toast.info .toast-message {
  color: #ffffff;
}

[data-theme="dark"] .toast.error .toast-icon,
[data-theme="dark"] .toast.error .toast-message {
  color: #ffffff;
}

/* Dark mode override for toast message text */
[data-theme="dark"] .toast-message {
  color: #ffffff;
}

.toast-text {
  flex: 1;
}

.toast-title {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.toast-message {
  font-size: 0.875rem;
  color: #000000;
  line-height: 1.4;
}

.toast-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  background-color: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
  flex-shrink: 0;
}

.toast-close:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.toast-close svg {
  width: 1rem;
  height: 1rem;
}

/* Toast Transitions */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.toast-move {
  transition: transform 0.3s ease;
}

/* External ID Dialog Styles */
.external-id-section {
  display: grid;
  gap: var(--space-6);
}

.external-id-section .input-group {
  display: grid;
  gap: var(--space-2);
  width: 100%;
  max-width: none;
}

.external-id-section .input-group label {
  font-weight: 500;
  color: var(--text-primary);
}

.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  max-width: none;
}

.input-with-icon .input-icon {
  position: absolute;
  left: var(--space-3);
  width: 1.25rem;
  height: 1.25rem;
  color: var(--text-secondary);
  z-index: 1;
  pointer-events: none;
}

.external-id-input {
  font-family: 'Courier New', monospace;
  font-size: 1rem;
  text-align: center;
  letter-spacing: 0.1em;
  padding-left: 3rem;
  width: 100%;
  max-width: none;
}

.external-id-info {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background-color: var(--info-light);
  border: 1px solid var(--info);
  border-radius: var(--radius-md);
}

.info-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: var(--info);
  flex-shrink: 0;
  margin-top: 2px;
}

.external-id-info p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--info);
  line-height: 1.4;
  font-weight: 500;
}

/* Dark mode overrides for info containers */
[data-theme="dark"] .external-id-info .info-icon,
[data-theme="dark"] .external-id-info p {
  color: #ffffff;
}

.external-id-actions {
  display: flex;
  justify-content: center;
}

.external-id-actions .btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  font-size: 1rem;
}

.external-id-actions .link-icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--space-6);
  backdrop-filter: blur(4px);
}

.modal-content {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 40px var(--shadow-color);
  max-width: 500px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  animation: modalSlideIn 0.3s ease-out;
  margin: 0;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.header-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: var(--text-primary);
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background-color: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.close-btn:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--space-4) var(--space-6) var(--space-6);
  background-color: var(--bg-secondary);
  min-height: 200px;
  width: 100%;
}

.storage-info-section {
  display: grid;
  gap: var(--space-4);
}

.storage-warning {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  background-color: var(--warning-bg);
  border: 1px solid var(--warning-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
}

.storage-warning .warning-icon {
  width: 1.5rem;
  height: 1.5rem;
  color: var(--warning);
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.warning-content p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--warning);
  line-height: 1.6;
  text-align: justify;
  flex: 1;
  font-weight: 500;
}

/* Dark mode overrides for warning containers */
[data-theme="dark"] .storage-warning .warning-icon,
[data-theme="dark"] .warning-content p {
  color: #ffffff;
}

.storage-id-display {
  display: grid;
  gap: var(--space-2);
}

.storage-id-display label {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.storage-id-container {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  min-height: 3rem;
}

.storage-id-text {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  color: var(--text-primary);
  word-break: break-all;
  flex: 1;
  font-weight: 500;
}

.storage-id-text.blurred {
  filter: blur(4px);
  user-select: none;
}

.eye-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background-color: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
  flex-shrink: 0;
}

.eye-toggle-btn:hover {
  background-color: var(--bg-primary);
  color: var(--text-primary);
  border-color: var(--primary);
}

.security-warning {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background-color: var(--warning-light);
  border: 1px solid var(--warning);
  border-radius: var(--radius-md);
}

.warning-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: var(--warning);
  flex-shrink: 0;
  margin-top: 2px;
}

.security-warning p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--warning);
  line-height: 1.4;
  font-weight: 500;
}

/* Dark mode overrides for security warning */
[data-theme="dark"] .security-warning .warning-icon,
[data-theme="dark"] .security-warning p {
  color: #ffffff;
}

.storage-actions {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-2);
}

.copy-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  font-size: 1rem;
  font-weight: 500;
  width: auto;
  justify-content: center;
}

.regenerate-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  font-size: 1rem;
}

.refresh-icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* Modal Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.9) translateY(-20px);
}

.modal-enter-to .modal-content,
.modal-leave-from .modal-content {
  transform: scale(1) translateY(0);
}

/* ------------------------------- */
/* --- RESPONSIVE DESIGN --- */
/* ------------------------------- */
@media (max-width: 640px) {
  .app-title { font-size: 2rem; }
  .task-stats-grid { grid-template-columns: 1fr; }
  .add-media-grid { grid-template-columns: 1fr; }
  .task-header { flex-direction: column; align-items: stretch; }
  .task-actions { align-self: flex-end; }
  .task-meta { padding-left: 0; }
  
  .storage-toggle-btn {
    padding: var(--space-2);
    min-width: 2.5rem;
    justify-content: center;
  }
  
  .storage-label {
    display: none;
  }
  
  .user-management-btn {
    bottom: var(--space-2);
    left: var(--space-2);
    padding: var(--space-2) var(--space-3);
    font-size: 0.8rem;
  }
  
  .tab-navigation {
    flex-direction: column;
    gap: var(--space-2);
  }
  
  .tab-btn {
    padding: var(--space-2) var(--space-3);
    font-size: 0.8rem;
  }
  
  .toast-container {
    bottom: var(--space-2);
    right: var(--space-2);
    left: var(--space-2);
    max-width: none;
  }
  
  .toast {
    min-width: auto;
  }
  
  .modal-overlay {
    padding: var(--space-2);
  }
  
  .modal-header,
  .modal-body {
    padding: var(--space-4);
  }
}
</style>
