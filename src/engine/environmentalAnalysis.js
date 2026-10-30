const fmt = (value, digits = 1) => Number.isFinite(value) ? Number(value).toFixed(digits) : 'not available'

export function analyzeLocation(city, weather) {
  const current = weather.current
  const observations = [
    `Latest modelled air temperature is ${fmt(current.temperature_2m)}°C; apparent temperature is ${fmt(current.apparent_temperature)}°C.`,
    `Modelled precipitation totals ${fmt(weather.recentRain)} mm over the previous 24 hours and ${fmt(weather.forecastRain)} mm over the next 24 hours.`,
    `The selected ${city} coordinate uses a weather-model grid cell${Number.isFinite(weather.elevation) ? ` at approximately ${fmt(weather.elevation, 0)} m elevation` : ''}; this is not a neighbourhood average.`,
  ]
  const actions = []
  if (current.apparent_temperature >= 35) actions.push('Consider heat-safe scheduling, shade, drinking water and check-ins for people at higher risk during the warmest hours.')
  if (weather.recentRain >= 20 || weather.forecastRain >= 20) actions.push('Review local drainage readiness and follow official rainfall and municipal alerts; these model totals do not predict street flooding.')
  if (current.wind_speed_10m >= 35) actions.push('Check official weather advisories and secure loose outdoor objects if strong winds are forecast.')
  if (!actions.length) actions.push('Use local observations alongside these model values; keep checking official weather alerts as conditions change.')
  return { observations, actions, summary: `Current modelled conditions in ${city}: ${fmt(current.temperature_2m)}°C air temperature, ${fmt(weather.recentRain)} mm recent rain and ${fmt(weather.forecastRain)} mm forecast rain over 24 hours.` }
}
