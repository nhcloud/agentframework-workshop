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

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        console.log('Making request to:', config.url);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => {
        return response;
      },
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  /**
   * Send message to single agent or multiple agents
   */
  async sendMessage(message, sessionId = null, agents = null, maxTurns = null, format = null) {
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

      const response = await this.api.post('/chat', payload);

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
      throw new Error(error.response?.data?.detail || 'Failed to send message');
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