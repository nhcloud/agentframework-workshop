using DotNetAgentFramework.Configuration;

namespace DotNetAgentFramework.Services;

public interface IAgentWorkflowService
{
    Task<GroupChatResponse> OrchestrateAsync(GroupChatRequest request, CancellationToken cancellationToken = default);
}

internal enum OrchestrationMode
{
    Single,
    Parallel,
    Sequential,
    Hybrid
}

public class AgentWorkflowService(
    IAgentService agentService,
    ISessionManager sessionManager,
    ILogger<AgentWorkflowService> logger,
    IOptions<AzureAIConfig> azureConfig) : IAgentWorkflowService
{
    private readonly IAgentService _agentService = agentService;
    private readonly ISessionManager _sessionManager = sessionManager;
    private readonly ILogger<AgentWorkflowService> _logger = logger;
    private readonly AzureAIConfig _azureConfig = azureConfig.Value;

    public async Task<GroupChatResponse> OrchestrateAsync(GroupChatRequest request, CancellationToken cancellationToken = default)
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        cts.CancelAfter(TimeSpan.FromMinutes(4));
        var ct = cts.Token;

        var startTime = DateTime.UtcNow;
        var sessionId = request.SessionId ?? await _sessionManager.CreateSessionAsync();
        var messages = new List<GroupChatMessage>();

        // Initial user message
        var userMessage = new GroupChatMessage
        {
            Content = request.Message,
            Agent = "user",
            Timestamp = DateTime.UtcNow,
            Turn = 0,
            MessageId = Guid.NewGuid().ToString()
        };
        messages.Add(userMessage);
        await _sessionManager.AddMessageToSessionAsync(sessionId, userMessage);

        var agentNames = request.Agents ?? new List<string>();
        if (agentNames.Count == 0)
        {
            _logger.LogInformation("No agents provided. Selecting a default agent.");
            agentNames = ["azure_openai_agent"]; // fallback
        }

        var mode = SelectMode(request.Message, agentNames);
        _logger.LogInformation("Selected orchestration mode: {Mode}", mode);

        switch (mode)
        {
            case OrchestrationMode.Single:
                await RunSingleAsync(request, sessionId, messages, ct);
                break;
            case OrchestrationMode.Parallel:
                await RunParallelAsync(request, sessionId, messages, agentNames, ct);
                break;
            case OrchestrationMode.Sequential:
                await RunSequentialAsync(request, sessionId, messages, PlanSequentialOrder(agentNames, request.Message), ct);
                break;
            case OrchestrationMode.Hybrid:
                await RunHybridAsync(request, sessionId, messages, agentNames, ct);
                break;
        }

        // Build response
        var totalProcessingTime = (int)(DateTime.UtcNow - startTime).TotalMilliseconds;
        var turns = messages.Count(m => m.Agent != "user");
        var distinctAgents = messages.Where(m => m.Agent != "user").Select(m => m.Agent).Distinct().Count();
        var summary = await SummarizeAsync(messages, ct);

        return new GroupChatResponse
        {
            Messages = messages,
            SessionId = sessionId,
            TotalTurns = turns,
            Summary = summary,
            GroupChatType = $"Workflow:{mode}",
            AgentCount = distinctAgents,
            TerminatedAgents = new List<string>(),
            TotalProcessingTimeMs = totalProcessingTime
        };
    }

    private OrchestrationMode SelectMode(string message, List<string> agents)
    {
        if (agents.Count <= 1) return OrchestrationMode.Single;

        var lower = message.ToLowerInvariant();
        var parallelSignals = new[] { "compare", "pros", "cons", "alternatives", "options", "summarize", "overview", "analyze", "research" };
        var sequentialSignals = new[] { "then", "step", "first", "next", "after", "pipeline", "compose", "draft", "send" };

        if (parallelSignals.Any(k => lower.Contains(k))) return OrchestrationMode.Parallel;
        if (sequentialSignals.Any(k => lower.Contains(k))) return OrchestrationMode.Sequential;

        // Heuristic: many agents -> parallel first, few agents -> hybrid
        return agents.Count >= 3 ? OrchestrationMode.Parallel : OrchestrationMode.Hybrid;
    }

    private List<string> PlanSequentialOrder(List<string> agents, string message)
    {
        // Prefer specialist first, generic last
        var order = new List<string>();
        var lower = message.ToLowerInvariant();

        string? specialist = null;
        if (agents.Contains("ms_foundry_people_agent") && (lower.Contains("who") || lower.Contains("contact") || lower.Contains("email") || lower.Contains("reach")))
            specialist = "ms_foundry_people_agent";
        else if (agents.Contains("knowledge_finder") && (lower.Contains("policy") || lower.Contains("document") || lower.Contains("find") || lower.Contains("search")))
            specialist = "knowledge_finder";

        if (specialist != null)
        {
            order.Add(specialist);
        }

        // Add other specialists (exclude generic for now)
        foreach (var a in agents)
        {
            if (a == specialist) continue;
            if (!a.Equals("azure_openai_agent", StringComparison.OrdinalIgnoreCase))
                order.Add(a);
        }

        // Put azure_openai_agent at end if present
        if (agents.Any(a => a.Equals("azure_openai_agent", StringComparison.OrdinalIgnoreCase)))
            order.Add("azure_openai_agent");

        // Ensure all provided agents are represented
        foreach (var a in agents)
            if (!order.Contains(a)) order.Add(a);

        return order;
    }

    private async Task RunSingleAsync(GroupChatRequest request, string sessionId, List<GroupChatMessage> messages, CancellationToken ct)
    {
        var agentName = request.Agents?.FirstOrDefault() ?? "azure_openai_agent";
        var agent = await _agentService.GetAgentAsync(agentName);
        if (agent == null)
        {
            _logger.LogWarning("Agent {Agent} not found", agentName);
            return;
        }
        var content = await agent.RespondAsync(request.Message, request.Context);
        var msg = MakeAgentMessage(agentName, content, 1);
        messages.Add(msg);
        await _sessionManager.AddMessageToSessionAsync(sessionId, msg);
    }

    private async Task RunParallelAsync(GroupChatRequest request, string sessionId, List<GroupChatMessage> messages, List<string> agents, CancellationToken ct)
    {
        var turn = 1;
        var tasks = agents.Select(async name =>
        {
            try
            {
                ct.ThrowIfCancellationRequested();
                var agent = await _agentService.GetAgentAsync(name);
                if (agent == null) return (name, (string?)null);
                var content = await agent.RespondAsync(request.Message, request.Context);
                return (name, content);
            }
            catch
            {
                return (name, (string?)null);
            }
        }).ToList();

        var results = await Task.WhenAll(tasks);
        foreach (var (name, content) in results)
        {
            var msg = MakeAgentMessage(name, content ?? "", turn++);
            messages.Add(msg);
            await _sessionManager.AddMessageToSessionAsync(sessionId, msg);
        }
    }

    private async Task RunSequentialAsync(GroupChatRequest request, string sessionId, List<GroupChatMessage> messages, List<string> order, CancellationToken ct)
    {
        string? context = request.Context;
        var turn = 1;
        foreach (var name in order)
        {
            ct.ThrowIfCancellationRequested();
            var agent = await _agentService.GetAgentAsync(name);
            if (agent == null) continue;

            var content = await agent.RespondAsync(request.Message, context);
            var msg = MakeAgentMessage(name, content, turn++);
            messages.Add(msg);
            await _sessionManager.AddMessageToSessionAsync(sessionId, msg);

            // Handoff: pass along latest content as context to next agent
            context = content;

            // Early-exit if agent indicates termination
            if (IsTerminated(content)) break;
        }
    }

    private async Task RunHybridAsync(GroupChatRequest request, string sessionId, List<GroupChatMessage> messages, List<string> agents, CancellationToken ct)
    {
        // Parallel first round
        await RunParallelAsync(request, sessionId, messages, agents, ct);

        // Pick best response (simple heuristic: longest non-terminated)
        var agentResponses = messages.Where(m => m.Agent != "user").ToList();
        var best = agentResponses
            .Where(m => !IsTerminated(m.Content))
            .OrderByDescending(m => (m.Content?.Length ?? 0))
            .FirstOrDefault();

        if (best == null) return;

        // Follow-up with generic agent if available to finalize with a clean response
        if (agents.Any(a => a.Equals("azure_openai_agent", StringComparison.OrdinalIgnoreCase)))
        {
            var generic = await _agentService.GetAgentAsync("azure_openai_agent");
            if (generic != null)
            {
                var content = await generic.RespondAsync(request.Message, context: best.Content);
                var msg = MakeAgentMessage("azure_openai_agent", content, agentResponses.Count + 1);
                messages.Add(msg);
                await _sessionManager.AddMessageToSessionAsync(sessionId, msg);
            }
        }
    }

    private static GroupChatMessage MakeAgentMessage(string agent, string? content, int turn) => new()
    {
        Content = content ?? string.Empty,
        Agent = agent,
        Timestamp = DateTime.UtcNow,
        Turn = turn,
        MessageId = Guid.NewGuid().ToString(),
        IsTerminated = IsTerminated(content),
        AgentType = "Workflow"
    };

    private static bool IsTerminated(string? content)
        => !string.IsNullOrWhiteSpace(content) && content.Trim().StartsWith("TERMINATED", StringComparison.OrdinalIgnoreCase);

    private async Task<string> SummarizeAsync(List<GroupChatMessage> messages, CancellationToken ct)
    {
        try
        {
            var agentMsgs = messages.Where(m => m.Agent != "user").ToList();
            if (agentMsgs.Count == 0) return "No agent responses.";

            var participants = string.Join(", ", agentMsgs.Select(m => m.Agent).Distinct());
            var last = agentMsgs.Last().Content;
            return await Task.FromResult($"Workflow summary with {agentMsgs.Count} responses from {participants}. Finalized by {agentMsgs.Last().Agent}.");
        }
        catch
        {
            return "";
        }
    }
}
