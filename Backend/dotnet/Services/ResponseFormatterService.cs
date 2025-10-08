namespace DotNetAgentFramework.Services;

/// <summary>
/// Service for formatting multi-agent responses into user-friendly formats
/// </summary>
public interface IResponseFormatterService
{
    /// <summary>
    /// Format group chat responses into a clean, user-friendly format
    /// </summary>
    Task<FormattedResponse> FormatGroupChatResponseAsync(GroupChatResponse groupChatResponse, string userQuery);
}

public class ResponseFormatterService(ILogger<ResponseFormatterService> logger) : IResponseFormatterService
{
    private readonly ILogger<ResponseFormatterService> _logger = logger;

    public async Task<FormattedResponse> FormatGroupChatResponseAsync(GroupChatResponse groupChatResponse, string userQuery)
    {
        try
        {
            _logger.LogInformation("Starting response formatting for session {SessionId}", groupChatResponse?.SessionId ?? "unknown");
            
            if (groupChatResponse == null)
            {
                _logger.LogWarning("GroupChatResponse is null");
                return new FormattedResponse
                {
                    Content = "No response data available.",
                    Format = "text",
                    SessionId = string.Empty
                };
            }

            if (string.IsNullOrWhiteSpace(userQuery))
            {
                _logger.LogWarning("User query is null or empty");
                userQuery = string.Empty;
            }

            var agentMessages = groupChatResponse.Messages?
                .Where(m => m.Agent != "user" && !m.IsTerminated)
                .OrderBy(m => m.Turn)
                .ToList() ?? new List<GroupChatMessage>();

            _logger.LogInformation("Found {MessageCount} agent messages (non-terminated, non-user)", agentMessages.Count);

            if (!agentMessages.Any())
            {
                _logger.LogWarning("No agent messages found to format");
                return new FormattedResponse
                {
                    Content = "I apologize, but I couldn't generate a response to your query.",
                    Format = "text",
                    SessionId = groupChatResponse.SessionId
                };
            }

            // Determine the best formatting strategy based on the responses
            var formatStrategy = DetermineFormatStrategy(agentMessages, userQuery);
            _logger.LogInformation("Selected format strategy: {Strategy}", formatStrategy);

            FormattedResponse result;
            try
            {
                result = formatStrategy switch
                {
                    FormatStrategy.SingleAgent => FormatSingleAgentResponse(agentMessages, groupChatResponse),
                    FormatStrategy.Synthesis => await SynthesizeMultiAgentResponseAsync(agentMessages, groupChatResponse, userQuery),
                    FormatStrategy.Structured => FormatStructuredResponse(agentMessages, groupChatResponse),
                    _ => FormatDefaultResponse(agentMessages, groupChatResponse)
                };
            }
            catch (Exception strategyEx)
            {
                _logger.LogError(strategyEx, "Error in format strategy {Strategy}, falling back to default", formatStrategy);
                result = FormatDefaultResponse(agentMessages, groupChatResponse);
            }

            _logger.LogInformation("Response formatting completed successfully. Content length: {Length}", result?.Content?.Length ?? 0);
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error formatting group chat response. Message: {Message}, StackTrace: {StackTrace}", 
                ex.Message, ex.StackTrace);
            
            return new FormattedResponse
            {
                Content = $"An error occurred while formatting the response: {ex.Message}",
                Format = "text",
                SessionId = groupChatResponse?.SessionId ?? string.Empty
            };
        }
    }

    private FormatStrategy DetermineFormatStrategy(List<GroupChatMessage> messages, string userQuery)
    {
        try
        {
            if (messages == null || !messages.Any())
            {
                _logger.LogWarning("No messages provided to DetermineFormatStrategy");
                return FormatStrategy.SingleAgent;
            }

            // If only one agent responded, use single agent format
            var distinctAgents = messages.Where(m => !string.IsNullOrWhiteSpace(m.Agent))
                .Select(m => m.Agent)
                .Distinct()
                .Count();
            
            if (distinctAgents == 1)
            {
                return FormatStrategy.SingleAgent;
            }

            // If query is about information retrieval or RAG-style queries, synthesize
            if (!string.IsNullOrWhiteSpace(userQuery))
            {
                var ragKeywords = new[] { "what", "who", "when", "where", "how", "find", "search", "lookup", "tell me", "email", "contact", "information" };
                if (ragKeywords.Any(keyword => userQuery.ToLower().Contains(keyword)))
                {
                    return FormatStrategy.Synthesis;
                }
            }

            // If agents provided complementary information, use structured format
            if (distinctAgents > 2 || messages.Count > 3)
            {
                return FormatStrategy.Structured;
            }

            return FormatStrategy.Synthesis;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in DetermineFormatStrategy, defaulting to Synthesis");
            return FormatStrategy.Synthesis;
        }
    }

    private FormattedResponse FormatSingleAgentResponse(List<GroupChatMessage> messages, GroupChatResponse groupChatResponse)
    {
        var lastMessage = messages.LastOrDefault();
        if (lastMessage == null)
        {
            return new FormattedResponse
            {
                Content = "No response available.",
                Format = "text",
                SessionId = groupChatResponse.SessionId
            };
        }

        return new FormattedResponse
        {
            Content = lastMessage.Content,
            Format = "text",
            SessionId = groupChatResponse.SessionId,
            Metadata = new FormattedResponseMetadata
            {
                AgentCount = 1,
                PrimaryAgent = lastMessage.Agent,
                ResponseCount = messages.Count
            }
        };
    }

    private async Task<FormattedResponse> SynthesizeMultiAgentResponseAsync(
        List<GroupChatMessage> messages,
        GroupChatResponse groupChatResponse,
        string userQuery)
    {
        try
        {
            // Strategy: Create a coherent synthesized response from multiple agent contributions
            var synthesizedContent = new System.Text.StringBuilder();

            // Group messages by agent to find the most relevant contributions
            var messagesByAgent = messages.GroupBy(m => m.Agent).ToList();

            // Check if we have a clear answer from a specialist agent (e.g., people_lookup found contact info)
            var specialistAgents = new[] { "foundry_people_lookup", "foundry_knowledge_finder" };
            var specialistResponses = messagesByAgent
                .Where(g => specialistAgents.Any(sa => g.Key?.Contains(sa, StringComparison.OrdinalIgnoreCase) ?? false))
                .SelectMany(g => g)
                .Where(m => m.Content != null)
                .OrderByDescending(m => m.Turn)
                .ToList();

            // Check for actionable results (e.g., "email has been sent", "found contact")
            var actionableResponse = specialistResponses.FirstOrDefault(m =>
                (m.Content?.Contains("has been sent", StringComparison.OrdinalIgnoreCase) ?? false) ||
                (m.Content?.Contains("email sent", StringComparison.OrdinalIgnoreCase) ?? false) ||
                (m.Content?.Contains("found", StringComparison.OrdinalIgnoreCase) ?? false) ||
                (m.Content?.Contains("located", StringComparison.OrdinalIgnoreCase) ?? false));

            if (actionableResponse != null && !string.IsNullOrWhiteSpace(actionableResponse.Content))
            {
                // Extract the key information from the specialist response
                var cleanedContent = CleanAgentResponse(actionableResponse.Content);
                if (!string.IsNullOrWhiteSpace(cleanedContent))
                {
                    synthesizedContent.AppendLine(cleanedContent);

                    // Add any complementary information from other agents
                    var otherRelevantInfo = messages
                        .Where(m => m.Agent != actionableResponse.Agent && m.Turn >= actionableResponse.Turn - 1)
                        .Where(m => !string.IsNullOrWhiteSpace(m.Content))
                        .Select(m => ExtractKeyInformation(m.Content))
                        .Where(info => !string.IsNullOrWhiteSpace(info))
                        .FirstOrDefault();

                    if (!string.IsNullOrWhiteSpace(otherRelevantInfo) && otherRelevantInfo.Length < 200)
                    {
                        synthesizedContent.AppendLine();
                        synthesizedContent.AppendLine(otherRelevantInfo);
                    }
                }
            }
            else
            {
                // No clear actionable response, synthesize from all agents
                // Take the most recent, substantive response from each agent
                var keyResponses = messagesByAgent
                    .Where(g => g.Any())
                    .Select(g => g.OrderByDescending(m => m.Turn).First())
                    .Where(m => !string.IsNullOrWhiteSpace(m.Content))
                    .OrderBy(m => m.Turn)
                    .ToList();

                if (keyResponses.Count == 1)
                {
                    var cleanedResponse = CleanAgentResponse(keyResponses[0].Content);
                    if (!string.IsNullOrWhiteSpace(cleanedResponse))
                    {
                        synthesizedContent.Append(cleanedResponse);
                    }
                }
                else if (keyResponses.Any())
                {
                    // Combine responses intelligently
                    var primaryResponse = keyResponses.LastOrDefault();
                    if (primaryResponse != null && !string.IsNullOrWhiteSpace(primaryResponse.Content))
                    {
                        var cleanedResponse = CleanAgentResponse(primaryResponse.Content);
                        if (!string.IsNullOrWhiteSpace(cleanedResponse))
                        {
                            synthesizedContent.AppendLine(cleanedResponse);
                        }
                    }
                }
            }

            // Ensure we have some content
            var finalContent = synthesizedContent.ToString().Trim();
            if (string.IsNullOrWhiteSpace(finalContent))
            {
                _logger.LogWarning("Synthesized content is empty, using fallback");
                finalContent = messages.LastOrDefault()?.Content ?? "No content available.";
            }

            return new FormattedResponse
            {
                Content = finalContent,
                Format = "text",
                SessionId = groupChatResponse.SessionId,
                Metadata = new FormattedResponseMetadata
                {
                    AgentCount = messagesByAgent.Count,
                    PrimaryAgent = messages.LastOrDefault()?.Agent ?? "unknown",
                    ResponseCount = messages.Count,
                    ContributingAgents = messagesByAgent.Select(g => g.Key).ToList()
                }
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in SynthesizeMultiAgentResponseAsync");
            throw;
        }

        await Task.CompletedTask; // For potential async operations in future
    }

    private FormattedResponse FormatStructuredResponse(List<GroupChatMessage> messages, GroupChatResponse groupChatResponse)
    {
        try
        {
            // When multiple agents contribute significantly, provide a structured format
            var content = new System.Text.StringBuilder();

            var messagesByAgent = messages.GroupBy(m => m.Agent).ToList();

            // If there's a clear primary answer, show it first
            var lastMessage = messages.LastOrDefault();
            if (lastMessage != null && !string.IsNullOrWhiteSpace(lastMessage.Content))
            {
                var cleanedContent = CleanAgentResponse(lastMessage.Content);
                if (!string.IsNullOrWhiteSpace(cleanedContent) && cleanedContent.Length > 100) // Substantial response
                {
                    content.AppendLine(cleanedContent);
                    content.AppendLine();

                    // Add supporting information from other agents
                    var otherAgents = messagesByAgent.Where(g => g.Key != lastMessage.Agent).ToList();
                    if (otherAgents.Any())
                    {
                        content.AppendLine("**Additional Information:**");
                        foreach (var agentGroup in otherAgents)
                        {
                            var agentResponse = agentGroup.OrderByDescending(m => m.Turn).FirstOrDefault();
                            if (agentResponse != null && !string.IsNullOrWhiteSpace(agentResponse.Content))
                            {
                                var keyInfo = ExtractKeyInformation(agentResponse.Content);
                                if (!string.IsNullOrWhiteSpace(keyInfo))
                                {
                                    content.AppendLine($"- {keyInfo}");
                                }
                            }
                        }
                    }
                }
                else
                {
                    // Responses are too short, combine them
                    foreach (var agentGroup in messagesByAgent)
                    {
                        var agentResponse = agentGroup.OrderByDescending(m => m.Turn).FirstOrDefault();
                        if (agentResponse != null && !string.IsNullOrWhiteSpace(agentResponse.Content))
                        {
                            var cleanedAgentContent = CleanAgentResponse(agentResponse.Content);
                            if (!string.IsNullOrWhiteSpace(cleanedAgentContent))
                            {
                                content.AppendLine(cleanedAgentContent);
                                content.AppendLine();
                            }
                        }
                    }
                }
            }

            var finalContent = content.ToString().Trim();
            if (string.IsNullOrWhiteSpace(finalContent))
            {
                _logger.LogWarning("Structured content is empty, using fallback");
                finalContent = messages.LastOrDefault()?.Content ?? "No content available.";
            }

            return new FormattedResponse
            {
                Content = finalContent,
                Format = "markdown",
                SessionId = groupChatResponse.SessionId,
                Metadata = new FormattedResponseMetadata
                {
                    AgentCount = messagesByAgent.Count,
                    ResponseCount = messages.Count,
                    ContributingAgents = messagesByAgent.Select(g => g.Key).ToList()
                }
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in FormatStructuredResponse");
            throw;
        }
    }

    private FormattedResponse FormatDefaultResponse(List<GroupChatMessage> messages, GroupChatResponse groupChatResponse)
    {
        // Fallback: Return the last substantive message
        var lastMessage = messages.LastOrDefault();
        if (lastMessage == null)
        {
            return new FormattedResponse
            {
                Content = "No response available.",
                Format = "text",
                SessionId = groupChatResponse.SessionId
            };
        }

        return new FormattedResponse
        {
            Content = CleanAgentResponse(lastMessage.Content),
            Format = "text",
            SessionId = groupChatResponse.SessionId,
            Metadata = new FormattedResponseMetadata
            {
                AgentCount = messages.Select(m => m.Agent).Distinct().Count(),
                ResponseCount = messages.Count
            }
        };
    }

    private string CleanAgentResponse(string content)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(content))
                return string.Empty;

            // Remove agent meta-instructions and internal communication
            var lines = content.Split('\n')
                .Where(line => !line.TrimStart().StartsWith("According to", StringComparison.OrdinalIgnoreCase))
                .Where(line => !line.TrimStart().StartsWith("Building on what", StringComparison.OrdinalIgnoreCase))
                .Where(line => !line.TrimStart().StartsWith("As the", StringComparison.OrdinalIgnoreCase))
                .Where(line => !line.Contains("my unique value", StringComparison.OrdinalIgnoreCase))
                .Where(line => !line.Contains("I must", StringComparison.OrdinalIgnoreCase) || line.Contains("inform", StringComparison.OrdinalIgnoreCase))
                .Where(line => !string.IsNullOrWhiteSpace(line))
                .ToList();

            // Find the main content (usually starts after meta-discussion)
            var contentStartIndex = 0;
            for (int i = 0; i < lines.Count; i++)
            {
                if (lines[i].Contains("Subject:", StringComparison.OrdinalIgnoreCase) ||
                    lines[i].Contains("Dear", StringComparison.OrdinalIgnoreCase) ||
                    lines[i].Contains("Here", StringComparison.OrdinalIgnoreCase) ||
                    lines[i].Contains("The email", StringComparison.OrdinalIgnoreCase) ||
                    lines[i].Length > 50) // Likely content line
                {
                    contentStartIndex = i;
                    break;
                }
            }

            var cleanedLines = lines.Skip(contentStartIndex).ToList();

            // Remove citation references like ?5:1†filename.txt?
            var cleaned = string.Join("\n", cleanedLines);
            cleaned = System.Text.RegularExpressions.Regex.Replace(cleaned, @"?[^?]+?", "");

            return cleaned.Trim();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error cleaning agent response, returning original content");
            return content ?? string.Empty;
        }
    }

    private string ExtractKeyInformation(string content)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(content))
                return string.Empty;

            // Extract the most important sentence or piece of information
            var sentences = content.Split(new[] { ". ", ".\n", "!\n", "?\n" }, StringSplitOptions.RemoveEmptyEntries);
            
            // Look for sentences with key information indicators
            var keyInfo = sentences.FirstOrDefault(s =>
                s.Contains("@", StringComparison.OrdinalIgnoreCase) ||
                s.Contains("found", StringComparison.OrdinalIgnoreCase) ||
                s.Contains("located", StringComparison.OrdinalIgnoreCase) ||
                s.Contains("confirmed", StringComparison.OrdinalIgnoreCase) ||
                s.Contains("email", StringComparison.OrdinalIgnoreCase));

            if (!string.IsNullOrWhiteSpace(keyInfo))
            {
                return keyInfo.Trim() + ".";
            }

            // Otherwise return first substantial sentence
            var firstSubstantial = sentences.FirstOrDefault(s => s.Length > 30);
            return firstSubstantial != null ? firstSubstantial.Trim() + "." : string.Empty;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error extracting key information");
            return string.Empty;
        }
    }

    private enum FormatStrategy
    {
        SingleAgent,
        Synthesis,
        Structured
    }
}

/// <summary>
/// Formatted response model for user-friendly output
/// </summary>
public class FormattedResponse
{
    public string Content { get; set; } = string.Empty;
    public string Format { get; set; } = "text"; // text, markdown, html
    public string SessionId { get; set; } = string.Empty;
    public FormattedResponseMetadata? Metadata { get; set; }
}

public class FormattedResponseMetadata
{
    public int AgentCount { get; set; }
    public string? PrimaryAgent { get; set; }
    public int ResponseCount { get; set; }
    public List<string>? ContributingAgents { get; set; }
}
