using Swashbuckle.AspNetCore.SwaggerUI;
using DotNetEnv;
using DotNetAgentFramework.Configuration;
using DotNetAgentFramework.Services;
using OpenTelemetry.Trace;
using OpenTelemetry.Resources;
using Azure.Monitor.OpenTelemetry.Exporter;
using System.Diagnostics;

var builder = WebApplication.CreateBuilder(args);

// Load environment variables from .env file
Env.Load();

// Configure OpenTelemetry and Application Insights
var applicationInsightsConnectionString = Environment.GetEnvironmentVariable("APPLICATIONINSIGHTS_CONNECTION_STRING");
var serviceName = "DotNetAgentFramework";
var sourceName = Guid.NewGuid().ToString("N");

// Create ActivitySource for tracing
var activitySource = new ActivitySource(sourceName, "1.0.0");

// Configure OpenTelemetry
var tracerProviderBuilder = OpenTelemetry.Sdk.CreateTracerProviderBuilder()
    .SetResourceBuilder(ResourceBuilder.CreateDefault().AddService(serviceName))
    .AddSource(sourceName)
    .AddSource("DotNetAgentFramework.*") // Add sources for all agent framework activities
    .AddHttpClientInstrumentation() // Track HTTP calls
    .AddAspNetCoreInstrumentation() // Track ASP.NET Core requests
    .AddConsoleExporter(); // Always export to console for debugging

// Add Azure Monitor exporter if connection string is provided
if (!string.IsNullOrWhiteSpace(applicationInsightsConnectionString))
{
    tracerProviderBuilder.AddAzureMonitorTraceExporter(o => 
    {
        o.ConnectionString = applicationInsightsConnectionString;
    });
    
    builder.Logging.AddApplicationInsights(configureTelemetryConfiguration: (config) =>
        config.ConnectionString = applicationInsightsConnectionString,
        configureApplicationInsightsLoggerOptions: (options) => { });
    
    Console.WriteLine($"? Application Insights enabled: {applicationInsightsConnectionString.Substring(0, Math.Min(50, applicationInsightsConnectionString.Length))}...");
}
else
{
    Console.WriteLine("??  Application Insights not configured. Set APPLICATIONINSIGHTS_CONNECTION_STRING to enable telemetry.");
}

var tracerProvider = tracerProviderBuilder.Build();

// Register ActivitySource as singleton for dependency injection
builder.Services.AddSingleton(activitySource);

// Add YAML configuration support
builder.Configuration.AddYamlFile("config.yml", optional: true, reloadOnChange: true);

// Configure request timeout - increase from default 20 seconds to handle AI operations
builder.Services.Configure<Microsoft.AspNetCore.Server.Kestrel.Core.KestrelServerOptions>(options =>
{
    options.Limits.KeepAliveTimeout = TimeSpan.FromMinutes(10);
    options.Limits.RequestHeadersTimeout = TimeSpan.FromMinutes(5);
    // This is the key setting - controls how long the entire request can take
    options.Limits.MaxRequestBodySize = 52428800; // 50 MB
});

// Configure HttpClient with longer timeout for external API calls
builder.Services.AddHttpClient("AzureOpenAI", client =>
{
    client.Timeout = TimeSpan.FromMinutes(5); // 5 minutes for AI operations
});

// Add services to the container
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    // Avoid schema id collisions (anonymous/object responses across endpoints)
    c.CustomSchemaIds(type => type.FullName);
    // If multiple actions have same path+verb, pick the first to avoid conflicts
    c.ResolveConflictingActions(apiDescriptions => apiDescriptions.First());
    c.SupportNonNullableReferenceTypes();
});

// Configure CORS - more permissive for development
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        var frontendUrl = Environment.GetEnvironmentVariable("FRONTEND_URL") ?? 
                         builder.Configuration["FRONTEND_URL"] ?? 
                         "http://localhost:3001";
        
        if (builder.Environment.IsDevelopment())
        {
            // More permissive CORS for development
            policy.AllowAnyOrigin()
                  .AllowAnyMethod()
                  .AllowAnyHeader();
        }
        else
        {
            policy.WithOrigins(frontendUrl)
                  .AllowAnyMethod()
                  .AllowAnyHeader()
                  .AllowCredentials();
        }
    });
});

// Add configuration - supporting both appsettings.json and environment variables
builder.Services.Configure<AzureAIConfig>(options =>
{
    // Try environment variables first (like Python version)
    var azureOpenAIEndpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT");
    var azureOpenAIApiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY");
    var azureOpenAIDeployment = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOYMENT_NAME");
    var azureOpenAIApiVersion = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_VERSION");
    
    var projectEndpoint = Environment.GetEnvironmentVariable("PROJECT_ENDPOINT");
    var peopleAgentId = Environment.GetEnvironmentVariable("PEOPLE_AGENT_ID");

    // ContentSafety
    var csEndpoint = Environment.GetEnvironmentVariable("CONTENT_SAFETY_ENDPOINT");
    var csApiKey = Environment.GetEnvironmentVariable("CONTENT_SAFETY_API_KEY");
    var csEnabled = Environment.GetEnvironmentVariable("CONTENT_SAFETY_ENABLED");
    var csThreshold = Environment.GetEnvironmentVariable("CONTENT_SAFETY_SEVERITY_THRESHOLD");
    var csHate = Environment.GetEnvironmentVariable("CONTENT_SAFETY_THRESHOLD_HATE");
    var csSelfHarm = Environment.GetEnvironmentVariable("CONTENT_SAFETY_THRESHOLD_SELFHARM");
    var csSexual = Environment.GetEnvironmentVariable("CONTENT_SAFETY_THRESHOLD_SEXUAL");
    var csViolence = Environment.GetEnvironmentVariable("CONTENT_SAFETY_THRESHOLD_VIOLENCE");
    var csBlockInput = Environment.GetEnvironmentVariable("CONTENT_SAFETY_BLOCK_UNSAFE_INPUT");
    var csFilterOutput = Environment.GetEnvironmentVariable("CONTENT_SAFETY_FILTER_UNSAFE_OUTPUT");
    var csBlocklists = Environment.GetEnvironmentVariable("CONTENT_SAFETY_BLOCKLISTS");
    var csOutputAction = Environment.GetEnvironmentVariable("CONTENT_SAFETY_OUTPUT_ACTION");
    var csPlaceholder = Environment.GetEnvironmentVariable("CONTENT_SAFETY_PLACEHOLDER_TEXT");
    
    if (!string.IsNullOrEmpty(azureOpenAIEndpoint) && !string.IsNullOrEmpty(azureOpenAIApiKey))
    {
        // Use environment variables (matching Python setup)
        options.AzureOpenAI = new AzureOpenAIConfig
        {
            Endpoint = azureOpenAIEndpoint,
            ApiKey = azureOpenAIApiKey,
            DeploymentName = azureOpenAIDeployment ?? "gpt-4o",
            ApiVersion = azureOpenAIApiVersion ?? "2024-10-21"
        };
    }
    else
    {
        // Fallback to appsettings.json
        var config = builder.Configuration.GetSection("AzureAI").Get<AzureAIConfig>();
        if (config?.AzureOpenAI != null)
        {
            options.AzureOpenAI = config.AzureOpenAI;
        }
    }
    
    // Azure AI Foundry configuration using new Agent Framework
    if (!string.IsNullOrEmpty(projectEndpoint))
    {
        options.AzureAIFoundry = new AzureAIFoundryConfig
        {
            ProjectEndpoint = projectEndpoint,
            ManagedIdentityClientId = Environment.GetEnvironmentVariable("MANAGED_IDENTITY_CLIENT_ID"), // Add Managed Identity Client ID support
            PeopleAgentId = peopleAgentId
        };
    }
    else
    {
        var config = builder.Configuration.GetSection("AzureAI").Get<AzureAIConfig>();
        if (config?.AzureAIFoundry != null)
        {
            options.AzureAIFoundry = config.AzureAIFoundry;
        }
    }

    // Azure Content Safety config
    if (!string.IsNullOrWhiteSpace(csEndpoint) && !string.IsNullOrWhiteSpace(csApiKey))
    {
        options.ContentSafety = new ContentSafetyConfig
        {
            Endpoint = csEndpoint,
            ApiKey = csApiKey,
            Enabled = string.IsNullOrWhiteSpace(csEnabled) ? true : bool.TryParse(csEnabled, out var e) && e,
            SeverityThreshold = int.TryParse(csThreshold, out var t) ? t : 5,
            HateThreshold = int.TryParse(csHate, out var h) ? h : 4,
            SelfHarmThreshold = int.TryParse(csSelfHarm, out var sh) ? sh : 4,
            SexualThreshold = int.TryParse(csSexual, out var sx) ? sx : 4,
            ViolenceThreshold = int.TryParse(csViolence, out var v) ? v : 4,
            BlockUnsafeInput = string.IsNullOrWhiteSpace(csBlockInput) ? true : bool.TryParse(csBlockInput, out var bi) && bi,
            FilterUnsafeOutput = string.IsNullOrWhiteSpace(csFilterOutput) ? true : bool.TryParse(csFilterOutput, out var fo) && fo,
            Blocklists = csBlocklists,
            OutputAction = string.IsNullOrWhiteSpace(csOutputAction) ? "redact" : csOutputAction,
            PlaceholderText = string.IsNullOrWhiteSpace(csPlaceholder) ? "[Content removed due to safety policy]" : csPlaceholder
        };
    }
    else
    {
        var config = builder.Configuration.GetSection("AzureAI").Get<AzureAIConfig>();
        if (config?.ContentSafety != null)
        {
            options.ContentSafety = config.ContentSafety;
        }
    }
});

// Add agent configuration from YAML
builder.Services.Configure<AppConfig>(builder.Configuration);

// Register agent instructions service
builder.Services.AddSingleton<AgentInstructionsService>();

// Register Content Safety service
builder.Services.AddSingleton<IContentSafetyService, ContentSafetyService>();

// Register Workflow service
builder.Services.AddScoped<IAgentWorkflowService, AgentWorkflowService>();

// Add Agent Framework services - simplified for the new Agent Framework pattern
builder.Services.AddScoped<IAgentService, AgentService>();
builder.Services.AddScoped<IGroupChatService, GroupChatService>();
builder.Services.AddSingleton<ISessionManager, SessionManager>();
builder.Services.AddScoped<IGroupChatTemplateService, GroupChatTemplateService>();
builder.Services.AddScoped<IResponseFormatterService, ResponseFormatterService>();

// Add logging
builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();

// Enable static file hosting for test UI
builder.Services.AddDirectoryBrowser();

var app = builder.Build();

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
    app.UseSwagger();
    app.UseSwaggerUI(c => 
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", ".NET Agent Framework API V1");
        c.RoutePrefix = string.Empty; // Make Swagger the default page
        c.DisplayRequestDuration();
        c.EnableTryItOutByDefault();
        c.EnableDeepLinking();
        c.EnableFilter();
        c.ShowExtensions();
        c.EnableValidator();
        c.SupportedSubmitMethods(SubmitMethod.Get, SubmitMethod.Post, SubmitMethod.Put, SubmitMethod.Delete, SubmitMethod.Patch);
    });
}

// Important: Use CORS before other middleware
app.UseCors("AllowFrontend");

// Only use HTTPS redirection in production or when explicitly configured
if (!app.Environment.IsDevelopment() || builder.Configuration.GetValue<bool>("ForceHttps"))
{
    app.UseHttpsRedirection();
}

app.UseStaticFiles();
app.UseAuthorization();
app.MapControllers();

// Health check
app.MapGet("/health", () => Results.Ok(new { status = "healthy", timestamp = DateTime.UtcNow }))
   .ExcludeFromDescription()
   .WithName("GetHealth")
   .WithTags("Health");

// Start the application and keep it running
Console.WriteLine("?? Starting .NET Agent Framework API...");
Console.WriteLine("?? Swagger UI available at: http://localhost:8000");
Console.WriteLine("?? Health endpoint: http://localhost:8000/health");

app.Run();

// Cleanup on shutdown
tracerProvider?.Dispose();
activitySource?.Dispose();activitySource?.Dispose();