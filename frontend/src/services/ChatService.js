import axios from 'axios';

const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '' 
  : 'http://localhost:8000';

class ChatService {
  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 120000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.uploadApi = axios.create({
      baseURL: API_BASE_URL,
      timeout: 120000,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    // track the active request controller to allow cancel/stop
    this.currentController = null;

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        console.log('Making request to:', config.url);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  beginRequest() {
    // cancel any previous pending request before starting a new one
    if (this.currentController) {
      try { this.currentController.abort(); } catch {}
    }
    this.currentController = new AbortController();
    return this.currentController;
  }

  cancelCurrentRequest() {
    if (this.currentController) {
      try { this.currentController.abort(); } catch {}
      this.currentController = null;
    }
  }

  /**
   * Send message to single agent or multiple agents
   */
  async sendMessage(message, sessionId = null, agents = null, maxTurns = null, format = null, enableMemory = null) {
    const controller = this.beginRequest();
    try {
      // Handle single agent (backward compatibility)
      if (typeof agents === 'string') {
        agents = [agents];
      }

      const payload = {
        message,
        session_id: sessionId,
        agents: agents // Array of agent names or null for auto-routing
      };

      // Add max_turns if provided
      if (maxTurns !== null && maxTurns !== undefined) {
        payload.max_turns = maxTurns;
      }

      // Add format if provided
      if (format !== null && format !== undefined) {
        payload.format = format;
      }

      // Add enable_memory if provided
      if (enableMemory !== null && enableMemory !== undefined) {
        payload.enable_memory = enableMemory;
      }

      const response = await this.api.post('/chat', payload, { signal: controller.signal });

      // Return full response data, including detailed format fields if present
      return {
        content: response.data.content,
        agent: response.data.agent,
        sessionId: response.data.session_id || response.data.conversation_id,
        timestamp: response.data.timestamp || new Date().toISOString(),
        metadata: response.data.metadata || {},
        format: response.data.format,
        // Detailed format fields
        responses: response.data.responses, // Array of agent responses for detailed format
        total_turns: response.data.total_turns,
        conversation_id: response.data.conversation_id,
        active_participants: response.data.active_participants
      };
    } catch (error) {
      if (axios.isCancel?.(error) || error?.name === 'CanceledError' || error?.message === 'canceled') {
        throw new Error('Request canceled');
      }
      throw new Error(error.response?.data?.detail || 'Failed to send message');
    } finally {
      this.currentController = null;
    }
  }

  /**
   * Send message with image to single agent or multiple agents
   */
  async sendMessageWithImage({ message, imageFile, sessionId = null, agents = null, maxTurns = null, format = null, enableMemory = null }) {
    const controller = this.beginRequest();
    try {
      const form = new FormData();
      form.append('Message', message);
      if (imageFile) form.append('Image', imageFile);
      if (sessionId) form.append('SessionId', sessionId);
      if (agents) form.append('Agents', Array.isArray(agents) ? JSON.stringify(agents) : agents);
      if (maxTurns !== null && maxTurns !== undefined) form.append('MaxTurns', String(maxTurns));
      if (format) form.append('Format', format);
      if (enableMemory !== null && enableMemory !== undefined) form.append('EnableMemory', String(enableMemory));

      const response = await this.uploadApi.post('/chat/with-image', form, { signal: controller.signal });
      return {
        content: response.data.content,
        agent: response.data.agent,
        sessionId: response.data.session_id || response.data.conversation_id,
        timestamp: response.data.timestamp || new Date().toISOString(),
        metadata: response.data.metadata || {},
        format: response.data.format,
        responses: response.data.responses,
        total_turns: response.data.total_turns,
        conversation_id: response.data.conversation_id,
        active_participants: response.data.active_participants
      };
    } catch (error) {
      if (axios.isCancel?.(error) || error?.name === 'CanceledError' || error?.message === 'canceled') {
        throw new Error('Request canceled');
      }
      throw new Error(error.response?.data?.detail || 'Failed to send message with image');
    } finally {
      this.currentController = null;
    }
  }

  /**
   * Send message to group chat (DEPRECATED - use sendMessage with multiple agents instead)
   * This method is kept for backward compatibility but now redirects to sendMessage
   */
  async sendGroupChatMessage(message, sessionId = null, config = null, summarize = true, mode = 'sequential', agents = null) {
    console.warn('sendGroupChatMessage is deprecated. Use sendMessage with agents array instead.');
    // Redirect to the unified sendMessage method
    return this.sendMessage(message, sessionId, agents);
  }

  /**
   * Create group chat from template
   * Now uses the unified /chat endpoint
   */
  async createGroupChatFromTemplate(templateName) {
    try {
      const response = await this.api.post('/chat/group-chat/from-template', {
        template_name: templateName
      });

      return {
        sessionId: response.data.session_id,
        templateName: response.data.template_name,
        name: response.data.name,
        description: response.data.description,
        participants: response.data.participants,
        status: response.data.status
      };
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to create group chat from template');
    }
  }

  /**
   * Get available agents
   */
  async getAvailableAgents() {
    try {
      const response = await this.api.get('/agents');
      return response.data.agents || [];
    } catch (error) {
      console.error('Failed to get agents:', error);
      throw new Error(error.response?.data?.detail || 'Failed to connect to server');
    }
  }

  /**
   * Get available group chat templates
   * Now uses the unified /chat endpoint
   */
  async getGroupChatTemplates() {
    try {
      const response = await this.api.get('/chat/group-chat/templates');
      return response.data.templates || [];
    } catch (error) {
      console.error('Failed to get group chat templates:', error);
      return [];
    }
  }

  /**
   * Get active group chats (sessions)
   * Now uses the unified /chat endpoint
   */
  async getActiveGroupChats() {
    try {
      const response = await this.api.get('/chat/group-chats');
      return response.data.group_chats || [];
    } catch (error) {
      console.error('Failed to get active group chats:', error);
      return [];
    }
  }

  /**
   * Reset chat session
   */
  async resetSession(sessionId) {
    try {
      const response = await this.api.post('/reset', {
        session_id: sessionId
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to reset session');
    }
  }

  /**
   * Reset group chat session (DEPRECATED - use resetSession instead)
   */
  async resetGroupChat(sessionId) {
    console.warn('resetGroupChat is deprecated. Use resetSession instead.');
    return this.resetSession(sessionId);
  }

  /**
   * Delete group chat session (DEPRECATED - sessions are now managed automatically)
   */
  async deleteGroupChat(sessionId) {
    console.warn('deleteGroupChat is deprecated. Sessions are now managed automatically.');
    // For now, just reset the session
    return this.resetSession(sessionId);
  }

  /**
   * Get health status
   */
  async getHealth() {
    try {
      const response = await this.api.get('/health');
      return response.data;
    } catch (error) {
      return { status: 'error', message: error.message };
    }
  }

  /**
   * Stream chat response (for future implementation)
   */
  async streamMessage(message, sessionId = null, agents = null, onChunk = null) {
    // This would be implemented for streaming responses
    // For now, we'll use the regular sendMessage method
    return this.sendMessage(message, sessionId, agents);
  }
}

export default ChatService;