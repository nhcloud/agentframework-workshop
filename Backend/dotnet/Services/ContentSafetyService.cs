using System.Text.Json;
using Azure;
using Azure.AI.ContentSafety;
using DotNetAgentFramework.Configuration;

namespace DotNetAgentFramework.Services;

public interface IContentSafetyService
{
    Task<ContentSafetyResult> AnalyzeAsync(string text, CancellationToken ct = default);
    bool IsSafe(ContentSafetyResult result);
}

public class ContentSafetyService : IContentSafetyService
{
    private readonly ILogger<ContentSafetyService> _logger;
    private readonly ContentSafetyClient? _client;
    private readonly int _threshold;

    public ContentSafetyService(IOptions<AzureAIConfig> config, ILogger<ContentSafetyService> logger)
    {
        _logger = logger;
        var cs = config.Value.ContentSafety;
        _threshold = cs?.SeverityThreshold ?? 5;

        if (cs?.IsConfigured() == true)
        {
            var credential = new AzureKeyCredential(cs.ApiKey!);
            _client = new ContentSafetyClient(new Uri(cs.Endpoint!), credential);
            _logger.LogInformation("Content Safety enabled at {Endpoint} with threshold {Threshold}", cs.Endpoint, _threshold);
        }
        else
        {
            _logger.LogWarning("Content Safety not configured. Proceeding without safety checks.");
        }
    }

    public async Task<ContentSafetyResult> AnalyzeAsync(string text, CancellationToken ct = default)
    {
        if (_client == null || string.IsNullOrWhiteSpace(text))
        {
            return ContentSafetyResult.NotConfigured;
        }

        try
        {
            var request = new AnalyzeTextOptions(text);
            Response<AnalyzeTextResult> response = await _client.AnalyzeTextAsync(request, ct);
            var result = response.Value;

            // Highest severity across categories
            int highest = 0;
            string? category = null;

            foreach (var item in result.CategoriesAnalysis)
            {
                int sev = item.Severity ?? 0;
                if (sev > highest)
                {
                    highest = sev;
                    category = item.Category.ToString();
                }
            }

            return new ContentSafetyResult
            {
                HighestSeverity = highest,
                HighestCategory = category,
                Raw = result
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Content Safety analyze failed");
            return ContentSafetyResult.Failure(ex.Message);
        }
    }

    public bool IsSafe(ContentSafetyResult result)
    {
        if (!result.Enabled) return true; // Not configured or errored: treat as safe to not block
        return result.HighestSeverity < _threshold;
    }
}

public record ContentSafetyResult
{
    public bool Enabled { get; init; } = true;
    public int HighestSeverity { get; init; }
    public string? HighestCategory { get; init; }
    public AnalyzeTextResult? Raw { get; init; }
    public string? Error { get; init; }

    public static ContentSafetyResult NotConfigured => new() { Enabled = false };
    public static ContentSafetyResult Failure(string message) => new() { Enabled = false, Error = message };
}
