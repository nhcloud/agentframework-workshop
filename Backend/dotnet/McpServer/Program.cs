using DotNetAgentFramework.McpServer;
using DotNetAgentFramework.McpServer.Tools;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;

// Build configuration
var configuration = new ConfigurationBuilder()
    .SetBasePath(Directory.GetCurrentDirectory())
    .AddJsonFile("appsettings.json", optional: true)
    .AddEnvironmentVariables()
    .Build();

// Determine transport mode from args or environment
var transportMode = args.FirstOrDefault() ?? configuration["MCP_TRANSPORT"] ?? "stdio";

// Get configuration values
var demoApiBaseUrl = configuration["DEMO_API_BASE_URL"] ?? "http://localhost:8000";
var authToken = configuration["DEMO_API_AUTH_TOKEN"] ?? "Bearer demo-token-12345";

// Remote API configuration (for external REST APIs)
var remoteApiBaseUrl = configuration["RemoteApi:BaseUrl"] ?? configuration["REMOTE_API_BASE_URL"];
var remoteApiAuthToken = configuration["RemoteApi:AuthToken"] ?? configuration["REMOTE_API_AUTH_TOKEN"];

Console.Error.WriteLine($"?? Starting MCP Server");
Console.Error.WriteLine($"?? Transport Mode: {transportMode}");
Console.Error.WriteLine($"?? Demo API Base URL: {demoApiBaseUrl}");
if (!string.IsNullOrEmpty(remoteApiBaseUrl))
{
    Console.Error.WriteLine($"?? Remote API Base URL: {remoteApiBaseUrl}");
}

// ???????????????????????????????????????????????????????????????????????
// STDIO MODE - Run as a process spawned by MCP client
// This is the standard way to run MCP servers
// ???????????????????????????????????????????????????????????????????????
var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddSingleton<IConfiguration>(configuration);

builder.Services.AddHttpClient("DemoApi", client =>
{
    client.BaseAddress = new Uri(demoApiBaseUrl);
    client.DefaultRequestHeaders.Add("Accept", "application/json");
    if (!string.IsNullOrEmpty(authToken))
    {
        client.DefaultRequestHeaders.Add("Authorization", authToken);
    }
});

if (!string.IsNullOrEmpty(remoteApiBaseUrl))
{
    builder.Services.AddHttpClient("RemoteApi", client =>
    {
        client.BaseAddress = new Uri(remoteApiBaseUrl);
        client.DefaultRequestHeaders.Add("Accept", "application/json");
        if (!string.IsNullOrEmpty(remoteApiAuthToken))
        {
            client.DefaultRequestHeaders.Add("Authorization", remoteApiAuthToken);
        }
    });
    builder.Services.AddSingleton<RemoteApiClient>();
}

builder.Logging.AddConsole(options => options.LogToStandardErrorThreshold = LogLevel.Trace);
builder.Logging.SetMinimumLevel(LogLevel.Information);

builder.Services.AddSingleton<DemoApiClient>();

builder.Services.AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

Console.Error.WriteLine("? MCP Server running in STDIO mode");
Console.Error.WriteLine("?? Ready and listening on stdio...");

var host = builder.Build();
await host.RunAsync();
