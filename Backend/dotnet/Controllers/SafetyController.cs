using DotNetAgentFramework.Services;
using Microsoft.AspNetCore.Mvc;

namespace DotNetAgentFramework.Controllers;

[ApiController]
[Route("safety")]
public class SafetyController(IContentSafetyService contentSafety, ILogger<SafetyController> logger) : ControllerBase
{
    private readonly IContentSafetyService _contentSafety = contentSafety;
    private readonly ILogger<SafetyController> _logger = logger;

    [HttpPost("scan-text")]
    public async Task<IActionResult> ScanText([FromBody] TextScanRequest req, CancellationToken ct)
    {
        if (req == null || string.IsNullOrWhiteSpace(req.Text))
            return BadRequest(new { detail = "Text is required" });

        var result = await _contentSafety.AnalyzeTextAsync(req.Text, ct);
        return Ok(new
        {
            isSafe = result.IsSafe,
            highestSeverity = result.HighestSeverity,
            highestCategory = result.HighestCategory,
            categorySeverities = result.CategorySeverities,
            flaggedCategories = result.FlaggedCategories,
            blocklistMatches = result.BlocklistMatches
        });
    }

    [HttpPost("scan-image")]
    [RequestSizeLimit(52_428_800)] // 50 MB
    [Consumes("multipart/form-data")]
    public async Task<IActionResult> ScanImage(IFormFile file, CancellationToken ct)
    {
        if (file == null || file.Length == 0)
            return BadRequest(new { detail = "Image file is required" });

        await using var stream = file.OpenReadStream();
        var result = await _contentSafety.AnalyzeImageAsync(stream, ct);
        return Ok(new
        {
            isSafe = result.IsSafe,
            highestSeverity = result.HighestSeverity,
            highestCategory = result.HighestCategory,
            categorySeverities = result.CategorySeverities,
            flaggedCategories = result.FlaggedCategories
        });
    }
}

public class TextScanRequest
{
    public string Text { get; set; } = string.Empty;
}
