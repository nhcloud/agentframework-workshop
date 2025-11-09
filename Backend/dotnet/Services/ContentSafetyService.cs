using System.Text.Json;
using Azure;
using Azure.AI.ContentSafety;
using DotNetAgentFramework.Configuration;

namespace DotNetAgentFramework.Services;

public interface IContentSafetyService
{
    Task<ContentSafetyResult> AnalyzeTextAsync(string text, CancellationToken ct = default);
    Task<ContentSafetyResult> AnalyzeImageAsync(Stream imageStream, CancellationToken ct = default);
    bool IsSafe(ContentSafetyResult result);
    string FilterOutput(string original, ContentSafetyResult analysis);
    Task<(bool allowed, string? error)> CheckUserInputAsync(string text, CancellationToken ct = default);
}

public class ContentSafetyService : IContentSafetyService
{
    private readonly ILogger<ContentSafetyService> _logger;
    private readonly ContentSafetyClient? _client;
    private readonly ContentSafetyConfig? _config;
    private readonly Dictionary<string, int> _categoryThresholds;

    public ContentSafetyService(IOptions<AzureAIConfig> config, ILogger<ContentSafetyService> logger)
    {
        _logger = logger;
        _config = config.Value.ContentSafety;

        if (_config?.IsConfigured() == true && _config.Enabled)
        {
            var credential = new AzureKeyCredential(_config.ApiKey!);
            _client = new ContentSafetyClient(new Uri(_config.Endpoint!), credential);
            _logger.LogInformation("Content Safety enabled at {Endpoint}. Global threshold {Threshold}", _config.Endpoint, _config.SeverityThreshold);
        }
        else
        {
            _logger.LogWarning("Content Safety not configured or disabled. Proceeding without safety checks.");
        }

        _categoryThresholds = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase)
        {
            ["Hate"] = _config?.HateThreshold ?? _config?.SeverityThreshold ?? 5,
            ["SelfHarm"] = _config?.SelfHarmThreshold ?? _config?.SeverityThreshold ?? 5,
            ["Sexual"] = _config?.SexualThreshold ?? _config?.SeverityThreshold ?? 5,
            ["Violence"] = _config?.ViolenceThreshold ?? _config?.SeverityThreshold ?? 5
        };
    }

    public async Task<ContentSafetyResult> AnalyzeTextAsync(string text, CancellationToken ct = default)
    {
        if (_client == null || string.IsNullOrWhiteSpace(text))
            return ContentSafetyResult.NotConfigured;

        try
        {
            var request = new AnalyzeTextOptions(text);
            // Blocklists (if any)
            if (!string.IsNullOrWhiteSpace(_config?.Blocklists))
            {
                var names = _config.Blocklists.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                foreach (var name in names)
                    request.BlocklistNames.Add(name);
            }

            Response<AnalyzeTextResult> response = await _client.AnalyzeTextAsync(request, ct);
            var result = response.Value;
            return BuildResult(result, MediaType: "text");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Content Safety text analyze failed");
            return ContentSafetyResult.Failure(ex.Message);
        }
    }

    public async Task<ContentSafetyResult> AnalyzeImageAsync(Stream imageStream, CancellationToken ct = default)
    {
        if (_client == null || imageStream == null || !imageStream.CanRead)
            return ContentSafetyResult.NotConfigured;

        try
        {
            var imageBytes = await ReadAllBytesAsync(imageStream, ct);
            var imageData = new ContentSafetyImageData(new BinaryData(imageBytes));
            var request = new AnalyzeImageOptions(imageData);
            Response<AnalyzeImageResult> response = await _client.AnalyzeImageAsync(request, ct);
            var result = response.Value;
            return BuildResult(result, MediaType: "image");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Content Safety image analyze failed");
            return ContentSafetyResult.Failure(ex.Message);
        }
    }

    private static async Task<byte[]> ReadAllBytesAsync(Stream stream, CancellationToken ct)
    {
        using var ms = new MemoryStream();
        await stream.CopyToAsync(ms, ct);
        return ms.ToArray();
    }

    private ContentSafetyResult BuildResult(object rawResult, string MediaType)
    {
        int highest = 0;
        string? highestCategory = null;
        var categorySeverities = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        List<string> flaggedCategories = new();
        List<string> blocklistMatches = new();

        if (rawResult is AnalyzeTextResult textRes)
        {
            foreach (var item in textRes.CategoriesAnalysis)
            {
                int sev = item.Severity ?? 0;
                var cat = item.Category.ToString();
                categorySeverities[cat] = sev;
                if (sev > highest)
                {
                    highest = sev;
                    highestCategory = cat;
                }
                if (_categoryThresholds.TryGetValue(cat, out var thresh) && thresh != -1 && sev >= thresh)
                    flaggedCategories.Add(cat);
            }
            // Blocklist matches
            foreach (var bl in textRes.BlocklistsMatch)
            {
                if (!string.IsNullOrWhiteSpace(bl.BlocklistItemText))
                    blocklistMatches.Add(bl.BlocklistItemText);
            }
        }
        else if (rawResult is AnalyzeImageResult imgRes)
        {
            foreach (var item in imgRes.CategoriesAnalysis)
            {
                int sev = item.Severity ?? 0;
                var cat = item.Category.ToString();
                categorySeverities[cat] = sev;
                if (sev > highest)
                {
                    highest = sev;
                    highestCategory = cat;
                }
                if (_categoryThresholds.TryGetValue(cat, out var thresh) && thresh != -1 && sev >= thresh)
                    flaggedCategories.Add(cat);
            }
        }

        bool isSafe = flaggedCategories.Count == 0 && blocklistMatches.Count == 0;

        return new ContentSafetyResult
        {
            Enabled = true,
            HighestSeverity = highest,
            HighestCategory = highestCategory,
            Raw = rawResult,
            MediaType = MediaType,
            CategorySeverities = categorySeverities,
            FlaggedCategories = flaggedCategories,
            BlocklistMatches = blocklistMatches,
            IsSafe = isSafe
        };
    }

    public bool IsSafe(ContentSafetyResult result)
    {
        if (!result.Enabled) return true; // Not configured or errored: treat as safe
        return result.IsSafe;
    }

    public async Task<(bool allowed, string? error)> CheckUserInputAsync(string text, CancellationToken ct = default)
    {
        if (_config == null || !_config.Enabled || !_config.BlockUnsafeInput)
            return (true, null);

        var result = await AnalyzeTextAsync(text, ct);
        if (!IsSafe(result))
        {
            return (false, $"Input blocked due to unsafe content: {string.Join(", ", result.FlaggedCategories)}");
        }
        return (true, null);
    }

    public string FilterOutput(string original, ContentSafetyResult analysis)
    {
        if (_config == null || !_config.Enabled || !_config.FilterUnsafeOutput)
            return original;

        if (IsSafe(analysis)) return original;

        return _config.OutputAction.ToLowerInvariant() switch
        {
            "placeholder" => _config.PlaceholderText ?? "[Filtered]",
            "empty" => string.Empty,
            _ => RedactUnsafe(original, analysis)
        };
    }

    private static string RedactUnsafe(string original, ContentSafetyResult analysis)
    {
        // Simple strategy: replace entire content. Could add granular redaction.
        return "[Content removed due to safety policy]";
    }
}

public record ContentSafetyResult
{
    public bool Enabled { get; init; } = true;
    public int HighestSeverity { get; init; }
    public string? HighestCategory { get; init; }
    public object? Raw { get; init; }
    public string MediaType { get; init; } = "text";
    public Dictionary<string, int> CategorySeverities { get; init; } = new(StringComparer.OrdinalIgnoreCase);
    public List<string> FlaggedCategories { get; init; } = new();
    public List<string> BlocklistMatches { get; init; } = new();
    public bool IsSafe { get; init; } = true;
    public string? Error { get; init; }

    public static ContentSafetyResult NotConfigured => new() { Enabled = false };
    public static ContentSafetyResult Failure(string message) => new() { Enabled = false, Error = message };
}
