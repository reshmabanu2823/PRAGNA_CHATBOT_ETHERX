// API response status codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  GONE: 410,
  CONFLICT: 409,
  INTERNAL_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
}

// Message types
export const MESSAGE_TYPES = {
  TEXT: 'text',
  IMAGE: 'image',
  FILE: 'file',
  VIDEO: 'video',
  VOICE: 'voice',
  SYSTEM: 'system',
}

// Chat actions (for activity log)
export const CHAT_ACTIONS = {
  CREATED: 'chat_created',
  RENAMED: 'chat_renamed',
  PINNED: 'chat_pinned',
  UNPINNED: 'chat_unpinned',
  ARCHIVED: 'chat_archived',
  UNARCHIVED: 'chat_unarchived',
  DELETED: 'chat_deleted',
  RESTORED: 'chat_restored',
  USER_ADDED: 'user_added',
  USER_REMOVED: 'user_removed',
  ADMIN_PROMOTED: 'admin_promoted',
  ADMIN_DEMOTED: 'admin_demoted',
  SETTINGS_CHANGED: 'group_settings_changed',
  SHARED: 'chat_shared',
  SHARE_REVOKED: 'share_link_revoked',
}

// Socket.IO events
export const SOCKET_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  USER_IDENTIFIED: 'user_identified',
  JOIN_CHAT: 'join_chat',
  LEAVE_CHAT: 'leave_chat',
  USER_TYPING: 'user_typing',
  USER_STOP_TYPING: 'user_stop_typing',
  MESSAGE_SENT: 'message_sent',
  MESSAGE_EDITED: 'message_edited',
  MESSAGE_DELETED: 'message_deleted',
  MESSAGE_REACTED: 'message_reacted',
  MESSAGE_READ: 'message_read',
  USER_ONLINE: 'user_online',
  USER_OFFLINE: 'user_offline',
}

// Validation limits
export const LIMITS = {
  CHAT_TITLE_MIN: 1,
  CHAT_TITLE_MAX: 100,
  CHAT_DESC_MAX: 500,
  MESSAGE_CONTENT_MIN: 1,
  MESSAGE_CONTENT_MAX: 5000,
  USER_NAME_MIN: 1,
  USER_NAME_MAX: 50,
  USER_EMAIL_MIN: 5,
  USER_EMAIL_MAX: 100,
  PAGINATION_DEFAULT: 20,
  PAGINATION_MAX: 100,
  FILE_SIZE_MAX: 10 * 1024 * 1024, // 10MB
}

// Redis cache TTL (in seconds)
export const CACHE_TTL = {
  CHAT: 600, // 10 minutes
  USER_CHATS: 300, // 5 minutes
  MESSAGES: 300, // 5 minutes
  USER: 3600, // 1 hour
}

// Sort options
export const SORT_OPTIONS = {
  CHAT: {
    UPDATED_AT: 'updated_at',
    CREATED_AT: 'created_at',
    NAME: 'name',
  },
  MESSAGE: {
    CREATED_ASC: 'created_asc',
    CREATED_DESC: 'created_desc',
  },
}

// Error messages
export const ERROR_MESSAGES = {
  INVALID_TOKEN: 'Invalid or expired token',
  NO_TOKEN: 'No authorization token provided',
  UNAUTHORIZED: 'You do not have permission to perform this action',
  NOT_FOUND: 'Resource not found',
  BAD_REQUEST: 'Invalid request parameters',
  INTERNAL_ERROR: 'An internal server error occurred',
  CHAT_NOT_FOUND: 'Chat not found',
  MESSAGE_NOT_FOUND: 'Message not found',
  USER_NOT_FOUND: 'User not found',
  USER_ALREADY_EXISTS: 'User already exists',
  INVALID_CREDENTIALS: 'Invalid email or password',
  IMAGE_NOT_FOUND: 'Image not found',
  FILE_TOO_LARGE: 'File size exceeds maximum limit',
  INVALID_FILE_TYPE: 'Invalid file type',
  SHARE_LINK_EXPIRED: 'Share link has expired',
  DUPLICATE_PARTICIPANT: 'User is already a participant',
  SELF_ACTION_ERROR: 'Cannot perform this action on yourself',
}

// API Endpoints
export const API_ENDPOINTS = {
  CHATS: '/api/chats',
  MESSAGES: '/api/messages',
  USERS: '/api/users',
  AUTH: '/api/auth',
  SEARCH: '/api/search',
}

// Default pagination
export const DEFAULT_PAGINATION = {
  PAGE: 1,
  LIMIT: 20,
}
