using DotNetAgentFramework.Services;
using Microsoft.AspNetCore.Mvc;

namespace DotNetAgentFramework.Controllers;

[ApiController]
[Route("[controller]")]
[Produces("application/json")]
public class ChatController(
    IAgentService agentService,
    ISessionManager sessionManager,
    IAgentWorkflowService workflowService,
    IGroupChatTemplateService templateService,
    IResponseFormatterService responseFormatter,
    IContentSafetyService contentSafety,
    ILogger<ChatController> logger) : ControllerBase
{
    private readonly IAgentService _agentService = agentService;
    private readonly ISessionManager _sessionManager = sessionManager;
    private readonly IAgentWorkflowService _workflowService = workflowService;
    private readonly IGroupChatTemplateService _templateService = templateService;
    private readonly IResponseFormatterService _responseFormatter = responseFormatter;
    private readonly IContentSafetyService _contentSafety = contentSafety;
    private readonly ILogger<ChatController> _logger = logger;

    /// <summary>
    /// Process a chat message - automatically orchestrates agents using AgentWorkflowService
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

            // Generate session ID if not provided
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

            // Use AgentWorkflowService to orchestrate automatically (replaces manual group chat selection)
            var workflowRequest = new GroupChatRequest
            {
                Message = request.Message,
                Agents = request.Agents,
                SessionId = sessionId,
                MaxTurns = request.MaxTurns ?? 3,
                Format = request.Format ?? "user_friendly",
                Context = request.Context
            };

            var workflowResponse = await _workflowService.OrchestrateAsync(workflowRequest, HttpContext.RequestAborted);

            var responseMessages = workflowResponse.Messages?.Where(m => m.Agent != "user").ToList() ?? new List<GroupChatMessage>();

            // Output Content Safety: scan generated content
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

            // Format response based on user preference
            var requestedFormat = request.Format?.ToLower() ?? "user_friendly";
            if (requestedFormat == "detailed")
            {
                return Ok(new
                {
                    conversation_id = sessionId,
                    total_turns = workflowResponse.TotalTurns,
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
                    summary = workflowResponse.Summary,
                    content = workflowResponse.Summary ?? responseMessages.LastOrDefault()?.Content,
                    metadata = new { 
                        group_chat_type = workflowResponse.GroupChatType,
                        agent_count = workflowResponse.AgentCount,
                        agents_used = request.Agents,
                        max_turns_used = request.MaxTurns ?? 3,
                        agent_framework = true,
                        terminated_agents = workflowResponse.TerminatedAgents ?? new List<string>(),
                        response_type = "detailed",
                        conversation_length = conversationHistory.Count
                    }
                });
            }
            else
            {
                // Return user-friendly formatted response (default)
                _logger.LogInformation("Returning user-friendly format using ResponseFormatterService");

                var formattedResponse = await _responseFormatter.FormatGroupChatResponseAsync(workflowResponse, request.Message);

                // Safety check synthesized content
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
                        total_turns = workflowResponse.TotalTurns,
                        response_type = "user_friendly",
                        conversation_length = conversationHistory.Count,
                        agent_framework = true
                    }
                });
            }
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