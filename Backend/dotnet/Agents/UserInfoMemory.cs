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

        UserInfo = serializedState.ValueKind == JsonValueKind.Object ?
            serializedState.Deserialize<UserInfo>(jsonSerializerOptions)! :
            new UserInfo();
    }

    public UserInfo UserInfo { get; set; }

    public override async ValueTask InvokedAsync(InvokedContext context, CancellationToken cancellationToken = default)
    {
        if ((UserInfo.UserName is null || UserInfo.UserPersona is null) && context.RequestMessages.Any(x => x.Role == ChatRole.User))
        {
            var result = await _chatClient.GetResponseAsync<UserInfo>(
                context.RequestMessages,
                new ChatOptions()
                {
                    Instructions = "Extract the user's name and persona from the message if present. If not present return nulls."
                },
                cancellationToken: cancellationToken);

            UserInfo.UserName ??= result.Result.UserName;
            UserInfo.UserPersona ??= result.Result.UserPersona;
        }
    }

    public override ValueTask<AIContext> InvokingAsync(InvokingContext context, CancellationToken cancellationToken = default)
    {
        StringBuilder instructions = new();
        // If we don't already know the user's name and persona, add instructions to ask for them, otherwise just provide what we have to the context.
        instructions
            .AppendLine(
                UserInfo.UserName is null ?
                    "Ask the user for their name and politely decline to answer any questions until they provide it." :
                    $"The user's name is {UserInfo.UserName}.")
            .AppendLine(
                UserInfo.UserPersona is null ?
                    "Ask the user for their persona and politely decline to answer any questions until they provide it." :
                    $"The user's persona is {UserInfo.UserPersona}.");

        return new ValueTask<AIContext>(new AIContext
        {
            Instructions = instructions.ToString()
        });
    }

    public override JsonElement Serialize(JsonSerializerOptions? jsonSerializerOptions = null)
    {
        return JsonSerializer.SerializeToElement(UserInfo, jsonSerializerOptions);
    }

}

internal sealed class UserInfo
{
    public string? UserName { get; set; }
    public string? UserPersona { get; set; }
}