using Microsoft.Agents.AI;
using System.Text;
using System.Text.Json;

namespace DotNetAgentFramework.Agents;

internal sealed class UserInfoMemory : AIContextProvider
{
    private readonly IChatClient _chatClient;
    private bool _hasAskedForName = false;
    private bool _hasAskedForPersona = false;

    public UserInfoMemory(IChatClient chatClient, UserInfo? userInfo = null)
    {
        _chatClient = chatClient;
        UserInfo = userInfo ?? new UserInfo();
    }

    public UserInfoMemory(IChatClient chatClient, JsonElement serializedState, JsonSerializerOptions? jsonSerializerOptions = null)
    {
        _chatClient = chatClient;

        if (serializedState.ValueKind == JsonValueKind.Object)
        {
            UserInfo = serializedState.Deserialize<UserInfo>(jsonSerializerOptions) ?? new UserInfo();
            
            // Restore the "asked" flags from serialized state if available
            _hasAskedForName = !string.IsNullOrEmpty(UserInfo.UserName) || UserInfo.HasAskedForName;
            _hasAskedForPersona = !string.IsNullOrEmpty(UserInfo.UserPersona) || UserInfo.HasAskedForPersona;
        }
        else
        {
            UserInfo = new UserInfo();
        }
    }

    public UserInfo UserInfo { get; set; }

    public override async ValueTask InvokedAsync(InvokedContext context, CancellationToken cancellationToken = default)
    {
        // Only try to extract user info if we don't have it already and there are user messages
        if ((UserInfo.UserName is null || UserInfo.UserPersona is null) && 
            context.RequestMessages.Any(x => x.Role == ChatRole.User))
        {
            try
            {
                // Get the last user message to check for name/persona
                var lastUserMessage = context.RequestMessages.LastOrDefault(x => x.Role == ChatRole.User);
                if (lastUserMessage != null)
                {
                    var messageText = lastUserMessage.Text ?? string.Empty;
                    
                    // Only extract if the message seems to contain personal information
                    // This prevents unnecessary API calls on every request
                    if (CouldContainUserInfo(messageText))
                    {
                        var result = await _chatClient.GetResponseAsync<UserInfo>(
                            context.RequestMessages,
                            new ChatOptions()
                            {
                                Instructions = "Extract ONLY the user's name and persona/age from the message if explicitly provided. Return nulls if not clearly stated. Examples: 'My name is John' → UserName='John', 'I'm a developer' → UserPersona='developer', 'I'm 25' → UserPersona='25 years old'"
                            },
                            cancellationToken: cancellationToken);

                        // Only update if we actually got new information
                        if (!string.IsNullOrEmpty(result.Result.UserName))
                        {
                            UserInfo.UserName = result.Result.UserName;
                        }
                        
                        if (!string.IsNullOrEmpty(result.Result.UserPersona))
                        {
                            UserInfo.UserPersona = result.Result.UserPersona;
                        }
                    }
                }
            }
            catch (Exception)
            {
                // If extraction fails, just continue without user info
                // Don't block the conversation
            }
        }
    }

    public override ValueTask<AIContext> InvokingAsync(InvokingContext context, CancellationToken cancellationToken = default)
    {
        StringBuilder instructions = new();

        // Provide information we have, and gently ask for missing info (but don't block)
        if (UserInfo.UserName is not null)
        {
            instructions.AppendLine($"The user's name is {UserInfo.UserName}.");
        }
        else if (!_hasAskedForName)
        {
            instructions.AppendLine("If appropriate and natural in the conversation, you may ask the user for their name. But DO NOT block answering their questions.");
            _hasAskedForName = true;
            UserInfo.HasAskedForName = true;
        }

        if (UserInfo.UserPersona is not null)
        {
            instructions.AppendLine($"The user's persona/background: {UserInfo.UserPersona}.");
        }
        else if (!_hasAskedForPersona && UserInfo.UserName is not null)
        {
            instructions.AppendLine("If it feels natural, you may ask about their role or background. But DO NOT block answering their questions.");
            _hasAskedForPersona = true;
            UserInfo.HasAskedForPersona = true;
        }

        // If we have user info, encourage personalized responses
        if (UserInfo.UserName is not null || UserInfo.UserPersona is not null)
        {
            instructions.AppendLine("Use this information to personalize your responses when appropriate.");
        }

        return new ValueTask<AIContext>(new AIContext
        {
            Instructions = instructions.ToString()
        });
    }

    public override JsonElement Serialize(JsonSerializerOptions? jsonSerializerOptions = null)
    {
        return JsonSerializer.SerializeToElement(UserInfo, jsonSerializerOptions);
    }

    /// <summary>
    /// Check if a message might contain user information to avoid unnecessary extraction calls
    /// </summary>
    private static bool CouldContainUserInfo(string message)
    {
        var lowerMessage = message.ToLowerInvariant();
        
        // Check for common patterns that indicate user info
        return lowerMessage.Contains("name") ||
               lowerMessage.Contains("i'm ") ||
               lowerMessage.Contains("i m ") ||
               lowerMessage.Contains("i am ") ||
               lowerMessage.Contains("persona");
    }
}

internal sealed class UserInfo
{
    public string? UserName { get; set; }
    public string? UserPersona { get; set; }
    
    /// <summary>
    /// Track if we've already asked for name to avoid asking repeatedly
    /// </summary>
    public bool HasAskedForName { get; set; } = false;
    
    /// <summary>
    /// Track if we've already asked for persona to avoid asking repeatedly
    /// </summary>
    public bool HasAskedForPersona { get; set; } = false;
}