using System.ComponentModel;
using System.Text.Json;

namespace DotNetAgentFramework.Agents.Tools;

/// <summary>
/// LOCAL Weather Tool - Called directly by agents in-process.
/// 
/// This is the SAME functionality as the MCP get_weather tool (SampleMcpBridge/RestApiTools.cs)
/// but runs locally without any network calls.
/// 
/// Use this to demonstrate:
/// - LOCAL TOOL: Fast, in-process, no network latency
/// - REMOTE TOOL (MCP): Via HTTP/SSE, demonstrates MCP protocol
/// 
/// Both return similar data for the same locations.
/// </summary>
public class WeatherTool
{
    // Simulated weather data matching DemoController
    private static readonly Dictionary<string, WeatherInfo> _weatherData = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Seattle"] = new WeatherInfo("Seattle", 15, "Cloudy", 75, 12),
        ["New York"] = new WeatherInfo("New York", 22, "Sunny", 55, 8),
        ["London"] = new WeatherInfo("London", 12, "Rainy", 85, 15),
        ["Tokyo"] = new WeatherInfo("Tokyo", 28, "Partly Cloudy", 65, 6),
        ["Paris"] = new WeatherInfo("Paris", 18, "Sunny", 60, 10),
        ["Sydney"] = new WeatherInfo("Sydney", 25, "Clear", 50, 14),
        ["Berlin"] = new WeatherInfo("Berlin", 14, "Overcast", 70, 18),
        ["Mumbai"] = new WeatherInfo("Mumbai", 32, "Hot and Humid", 80, 5),
        ["San Francisco"] = new WeatherInfo("San Francisco", 17, "Foggy", 78, 11),
        ["Singapore"] = new WeatherInfo("Singapore", 30, "Tropical", 85, 7)
    };

    [Description("Get the weather for a given location. Returns temperature, conditions, humidity, and wind speed.")]
    public string GetWeather([Description("The location to get the weather for (e.g., Seattle, Tokyo, London)")] string location)
    {
        if (string.IsNullOrWhiteSpace(location))
        {
            return "Please provide a location to get weather information.";
        }

        // Try exact match first
        if (_weatherData.TryGetValue(location, out var weather))
        {
            return FormatWeatherResponse(weather);
        }

        // Try partial match
        var partialMatch = _weatherData.Keys
            .FirstOrDefault(k => k.Contains(location, StringComparison.OrdinalIgnoreCase) ||
                                 location.Contains(k, StringComparison.OrdinalIgnoreCase));
        
        if (partialMatch != null)
        {
            return FormatWeatherResponse(_weatherData[partialMatch]);
        }

        // Return simulated weather for unknown locations (same as DemoController)
        var simulated = new WeatherInfo(location, 15, "Cloudy", 70, 10);
        return FormatWeatherResponse(simulated, isSimulated: true);
    }

    private static string FormatWeatherResponse(WeatherInfo weather, bool isSimulated = false)
    {
        var response = $"The weather in {weather.Location} is {weather.Condition.ToLower()} " +
                       $"with a temperature of {weather.Temperature}°C. " +
                       $"Humidity is {weather.Humidity}% with winds at {weather.WindSpeed} km/h.";
        
        if (isSimulated)
        {
            response += " (Note: This is simulated data for an unknown location)";
        }

        return response;
    }

    private record WeatherInfo(string Location, int Temperature, string Condition, int Humidity, int WindSpeed);
}
