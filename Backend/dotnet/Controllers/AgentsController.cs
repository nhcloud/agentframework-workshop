using DotNetAgentFramework.Services;
using Microsoft.AspNetCore.Mvc;

namespace DotNetAgentFramework.Controllers;

[ApiController]
[Route("[controller]")]
[Produces("application/json")]
public class AgentsController(IAgentService agentService, ILogger<AgentsController> logger) : ControllerBase
{
    private readonly IAgentService _agentService = agentService;
    private readonly ILogger<AgentsController> _logger = logger;

    /// <summary>
    /// Get all available agents
    /// Returns agents with provider information and counts
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<object>> GetAgents()
    {
        try
        {
            var agents = await _agentService.GetAvailableAgentsAsync();
            var agentList = agents.Select(a => new
            {
                name = a.Name,
                type = GetAgentType(a.Name, a.AgentType),
                available = true,
                capabilities = a.Capabilities ?? new List<string>(),
                provider = GetProviderType(a.AgentType, a.Name)
            }).ToList();
            
            _logger.LogInformation("Retrieved {AgentCount} available agents", agentList.Count);
            
            return Ok(new { 
                agents = agentList,
                total = agentList.Count,
                available = agentList.Count(a => a.available)
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving agents");
            return StatusCode(500, new { detail = "Internal server error while retrieving agents" });
        }
    }

    private static string GetAgentType(string agentName, string agentType)
    {
        // Handle foundry agents
        if (agentName.StartsWith("foundry_"))
        {
            return "ms_foundry_agent";
        }
        
        return agentName switch
        {
            "azure_openai_agent" => "azure_openai_agent",
            "ms_foundry_people_agent" => "ms_foundry_agent",
            "bedrock_agent" => "bedrock_agent",
            "openai_agent" => "openai_agent",
            _ => agentName
        };
    }

    private static string GetProviderType(string agentType, string agentName)
    {
        // Check agent name patterns first
        if (agentName.StartsWith("foundry_") || agentName == "ms_foundry_people_agent")
        {
            return "ms_foundry";
        }
        
        if (agentName == "bedrock_agent")
        {
            return "aws";
        }
        
        if (agentName == "openai_agent")
        {
            return "openai";
        }
        
        if (agentName == "azure_openai_agent")
        {
            return "azure_openai";
        }
        
        // Fallback to agentType
        if (agentType == "Azure AI Foundry")
        {
            return "ms_foundry";
        }
        
        if (agentType == "AWS Bedrock")
        {
            return "aws";
        }
        
        if (agentType == "OpenAI")
        {
            return "openai";
        }
        
        return "azure_openai";
    }
}