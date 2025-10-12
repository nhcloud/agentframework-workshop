using System.ComponentModel;

namespace DotNetAgentFramework.Agents.Tools;

public class WeatherTool
{
    [Description("Get the weather for a given location.")]
    public string GetWeather([Description("The location to get the weather for.")] string location)
    => $"The weather in {location} is cloudy with a high of 15°C.";
}
