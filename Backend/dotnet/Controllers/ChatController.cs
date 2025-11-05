using DotNetAgentFramework.Services;
using Microsoft.AspNetCore.Mvc;

namespace DotNetAgentFramework.Controllers;

[ApiController]
[Route("[controller]")]
[Produces("application/json")]
public class ChatController(
    IAgentService agentService,
    ISessionManager sessionManager,
    IGroupChatService groupChatService,
    IGroupChatTemplateService templateService,
    IResponseFormatterService responseFormatter,
    IContentSafetyService contentSafety,
    ILogger<ChatController> logger) : ControllerBase
{
    private readonly IAgentService _agentService = agentService;
    private readonly ISessionManager _sessionManager = sessionManager;
    private readonly IGroupChatService _groupChatService = groupChatService;
    private readonly IGroupChatTemplateService _templateService = templateService;
    private readonly IResponseFormatterService _responseFormatter = responseFormatter;
    private readonly IContentSafetyService _contentSafety = contentSafety;
    private readonly ILogger<ChatController> _logger = logger;

    /// <summary>
    /// Process a chat message - automatically handles both single and multiple agents using Microsoft Agent Framework
    /// Frontend payload: { message, session_id?, agents? }
    /// Automatically uses group chat when multiple agents are selected
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<object>> Chat([FromBody] ChatRequest request)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(request.Message))
            {
                return BadRequest(new { detail = "Message is required" });
            }

            // Content Safety - analyze user message
            var userSafety = await _contentSafety.AnalyzeAsync(request.Message, HttpContext.RequestAborted);
            if (!_contentSafety.IsSafe(userSafety))
            {
                _logger.LogWarning("User message blocked by content safety. Highest severity {Severity} in {Category}", userSafety.HighestSeverity, userSafety.HighestCategory);
                return BadRequest(new { detail = "Your message appears to contain unsafe content. Please rephrase and try again." });
            }

            // Generate session ID if not provided (matching frontend expectation)
            var sessionId = request.SessionId ?? Guid.NewGuid().ToString();

            // Retrieve conversation history for the session
            List<GroupChatMessage> conversationHistory = new();
            if (!string.IsNullOrEmpty(request.SessionId))
            {
                try
                {
                    conversationHistory = await _sessionManager.GetSessionHistoryAsync(request.SessionId);
                    _logger.LogInformation("Retrieved {MessageCount} messages from session {SessionId}", conversationHistory.Count, request.SessionId);
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Could not retrieve session history for {SessionId}, starting fresh", request.SessionId);
                    conversationHistory = new List<GroupChatMessage>();
                }
            }

            // Auto-select agents if none specified
            if (request.Agents == null || request.Agents.Count == 0)
            {
                _logger.LogInformation("No agents specified, auto-selecting based on message content");
                
                var availableAgents = await _agentService.GetAvailableAgentsAsync();
                var agentsList = availableAgents.ToList();
                
                // For now, select the first available agent, but this could be enhanced with intelligent routing
                if (agentsList.Any())
                {
                    request.Agents = new List<string> { agentsList.First().Name };
                    _logger.LogInformation("Auto-selected agent: {Agent}", request.Agents[0]);
                }
                else
                {
                    return StatusCode(503, new { detail = "No agents available to process the request" });
                }
            }

            // Check if multiple agents were specified (frontend sends agents array)
            if (request.Agents != null && request.Agents.Count > 1)
            {
                // Route to group chat for multiple agents using Agent Framework
                // Use provided max turns or adjust based on agent count for optimal performance
                var maxTurns = request.MaxTurns ?? (request.Agents.Count > 3 ? 2 : 3);
                
                var groupRequest = new GroupChatRequest
                {
                    Message = request.Message,
                    Agents = request.Agents,
                    SessionId = sessionId,
                    MaxTurns = maxTurns,
                    Format = request.Format ?? "user_friendly" // Default to synthesized response
                };

                var groupResponse = await _groupChatService.StartGroupChatAsync(groupRequest);
                var responseMessages = groupResponse.Messages?.Where(m => m.Agent != "user").ToList() ?? new List<GroupChatMessage>();
                
                // Output Content Safety: scan synthesized or detailed content
                if (responseMessages.Count > 0)
                {
                    // If detailed, check each; otherwise we'll check synthesized below
                    foreach (var m in responseMessages)
                    {
                        var outSafety = await _contentSafety.AnalyzeAsync(m.Content, HttpContext.RequestAborted);
                        if (!_contentSafety.IsSafe(outSafety))
                        {
                            _logger.LogWarning("Blocked unsafe agent output from {Agent} with severity {Severity}", m.Agent, outSafety.HighestSeverity);
                            m.Content = "[Content removed due to safety policy]";
                            m.IsTerminated = true;
                        }
                    }
                }
                
                // Check if user wants detailed format
                var requestedFormat = request.Format?.ToLower() ?? "user_friendly";
                
                if (requestedFormat == "detailed")
                {
                    // Return detailed response with full conversation history
                    _logger.LogInformation("Returning detailed format with {MessageCount} agent messages", responseMessages.Count);
                    
                    return Ok(new
                    {
                        conversation_id = sessionId,
                        total_turns = groupResponse.TotalTurns,
                        active_participants = responseMessages.Select(m => m.Agent).Distinct().ToList(),
                        responses = responseMessages.Select(m => new
                        {
                            agent = m.Agent,
                            content = m.Content,
                            message_id = m.MessageId,
                            is_terminated = m.IsTerminated,
                            metadata = new { 
                                turn = m.Turn, 
                                agent_type = m.AgentType, 
                                timestamp = m.Timestamp.ToString("O"),
                                terminated = m.IsTerminated
                            }
                        }).ToList(),
                        summary = groupResponse.Summary,
                        content = groupResponse.Summary ?? responseMessages.LastOrDefault()?.Content,
                        metadata = new { 
                            group_chat_type = groupResponse.GroupChatType,
                            agent_count = groupResponse.AgentCount,
                            agents_used = request.Agents,
                            max_turns_used = maxTurns,
                            agent_framework = true,
                            early_termination = groupResponse.TotalTurns < maxTurns * request.Agents.Count,
                            terminated_agents = groupResponse.TerminatedAgents ?? new List<string>(),
                            response_type = "detailed",
                            conversation_length = conversationHistory.Count
                        }
                    });
                }
                else
                {
                    // Return user-friendly formatted response (default)
                    _logger.LogInformation("Returning user-friendly format using ResponseFormatterService");
                    
                    var formattedResponse = await _responseFormatter.FormatGroupChatResponseAsync(groupResponse, request.Message);

                    // Safety scan synthesized content
                    var synthSafety = await _contentSafety.AnalyzeAsync(formattedResponse.Content, HttpContext.RequestAborted);
                    var safeContent = _contentSafety.IsSafe(synthSafety)
                        ? formattedResponse.Content
                        : "I’m sorry, I can’t share that. The generated content was flagged by safety checks.";
                    
                    return Ok(new
                    {
                        content = safeContent,
                        agent = formattedResponse.Metadata?.PrimaryAgent ?? "system",
                        session_id = sessionId,
                        timestamp = DateTime.UtcNow.ToString("O"),
                        format = formattedResponse.Format,
                        metadata = new { 
                            agent_count = formattedResponse.Metadata?.AgentCount ?? request.Agents.Count,
                            primary_agent = formattedResponse.Metadata?.PrimaryAgent,
                            contributing_agents = formattedResponse.Metadata?.ContributingAgents ?? responseMessages.Select(m => m.Agent).Distinct().ToList(),
                            is_group_chat = true,
                            total_turns = groupResponse.TotalTurns,
                            response_type = "user_friendly",
                            conversation_length = conversationHistory.Count,
                            agent_framework = true
                        }
                    });
                }
            }

            // Single agent handling with conversation history
            var agentName = request.Agents?.FirstOrDefault() ?? "generic_agent";
            
            _logger.LogInformation("Chat request for agent {AgentName} with {HistoryCount} previous messages: {Message}", 
                agentName, conversationHistory.Count, request.Message);

            // Filter conversation history to only include relevant messages for this agent
            var relevantHistory = conversationHistory
                .Where(m => m.Agent == "user" || m.Agent == agentName)
                .ToList();

            var response = await _agentService.ChatWithAgentAsync(agentName, request, relevantHistory);

            // Output safety for single response
            var outResult = await _contentSafety.AnalyzeAsync(response.Content, HttpContext.RequestAborted);
            if (!_contentSafety.IsSafe(outResult))
            {
                _logger.LogWarning("Blocked unsafe output from {Agent}", response.Agent);
                response.Content = "I’m sorry, I can’t share that. The generated content was flagged by safety checks.";
            }
            
            // Store conversation in session
            var userMessage = new GroupChatMessage
            {
                Content = request.Message,
                Agent = "user",
                Timestamp = DateTime.UtcNow,
                Turn = conversationHistory.Count,
                MessageId = Guid.NewGuid().ToString()
            };
            
            var agentMessage = new GroupChatMessage
            {
                Content = response.Content,
                Agent = response.Agent,
                Timestamp = response.Timestamp,
                Turn = conversationHistory.Count + 1,
                MessageId = Guid.NewGuid().ToString()
            };

            await _sessionManager.AddMessageToSessionAsync(sessionId, userMessage);
            await _sessionManager.AddMessageToSessionAsync(sessionId, agentMessage);

            // Return frontend-compatible single chat response
            return Ok(new
            {
                content = response.Content,
                agent = response.Agent,
                session_id = sessionId,
                timestamp = DateTime.UtcNow.ToString("O"),
                metadata = new { 
                    usage = response.Usage,
                    processing_time_ms = response.ProcessingTimeMs,
                    conversation_length = conversationHistory.Count + 2, // +2 for new user and agent messages
                    history_used = relevantHistory.Count,
                    agent_framework = true
                }
            });
        }
        catch (ArgumentException ex)
        {
            var agentName = request.Agents?.FirstOrDefault() ?? "unknown";
            _logger.LogWarning(ex, "Agent not found: {AgentName}", agentName);
            return NotFound(new { detail = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in chat");
            return StatusCode(500, new { detail = "Internal server error during chat" });
        }
    }

    /// <summary>
    /// Get available chat templates (supports both single and multi-agent configurations)
    /// Frontend expects: { templates: [] }
    /// </summary>
    [HttpGet("templates")]
    public async Task<ActionResult<object>> GetChatTemplates()
    {
        try
        {
            var templates = await _templateService.GetAvailableTemplatesAsync();
            
            return Ok(new { 
                templates = templates
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving chat templates");
            return StatusCode(500, new { detail = "Internal server error while retrieving templates" });
        }
    }

    /// <summary>
    /// Get detailed information about a specific template
    /// </summary>
    [HttpGet("templates/{templateName}")]
    public async Task<ActionResult<object>> GetChatTemplate(string templateName)
    {
        try
        {
            var templateDetails = await _templateService.GetTemplateDetailsAsync(templateName);
            
            if (templateDetails == null)
            {
                return NotFound(new { detail = $"Template '{templateName}' not found" });
            }
            
            return Ok(templateDetails);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting template {TemplateName}", templateName);
            return StatusCode(500, new { detail = "Internal server error while retrieving template" });
        }
    }

    /// <summary>
    /// Create chat session from template (supports both single and multi-agent)
    /// </summary>
    [HttpPost("from-template")]
    public async Task<ActionResult<object>> CreateChatFromTemplate([FromBody] CreateFromTemplateRequest request)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(request.TemplateName))
            {
                return BadRequest(new { detail = "Template name is required" });
            }

            var templateRequest = await _templateService.CreateFromTemplateAsync(request.TemplateName);
            
            if (templateRequest == null)
            {
                return NotFound(new { detail = $"Template '{request.TemplateName}' not found" });
            }

            var templateDetails = await _templateService.GetTemplateDetailsAsync(request.TemplateName);

            return Ok(new
            {
                session_id = Guid.NewGuid().ToString(),
                template_name = request.TemplateName,
                name = templateDetails?.Name ?? request.TemplateName,
                description = templateDetails?.Description ?? "",
                participants = templateRequest.Agents,
                status = "created",
                config = templateRequest.Config
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating chat from template {TemplateName}", request.TemplateName);
            return StatusCode(500, new { detail = "Internal server error while creating chat from template" });
        }
    }

    /// <summary>
    /// Get active chat sessions (both single and multi-agent conversations)
    /// Frontend expects: { sessions: [] }
    /// </summary>
    [HttpGet("sessions")]
    public async Task<ActionResult<object>> GetActiveChatSessions()
    {
        try
        {
            var activeSessions = await _sessionManager.GetActiveSessionsAsync();
            var sessions = new List<object>();
            
            foreach (var sessionId in activeSessions)
            {
                try
                {
                    var sessionInfo = await _sessionManager.GetSessionInfoAsync(sessionId);
                    sessions.Add(new
                    {
                        session_id = sessionId,
                        created_at = sessionInfo.CreatedAt.ToString("O"),
                        last_activity = sessionInfo.LastActivity.ToString("O"),
                        message_count = sessionInfo.MessageCount,
                        agent_types = sessionInfo.AgentTypes,
                        is_group_chat = sessionInfo.AgentTypes?.Count > 1
                    });
                }
                catch
                {
                    // Skip invalid sessions
                }
            }
            
            return Ok(new { 
                sessions = sessions
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving active chat sessions");
            return StatusCode(500, new { detail = "Internal server error while retrieving sessions" });
        }
    }
}