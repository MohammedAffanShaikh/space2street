const API = 'https://api.open-meteo.com/v1/forecast'

export async function fetchCityWeather(city, location, signal) {
  const [latitude, longitude] = location.coordinates
  const params = new URLSearchParams({
    latitude: String(latitude), longitude: String(longitude),
    current: 'temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,wind_speed_10m,weather_code',
    hourly: 'temperature_2m,apparent_temperature,precipitation,precipitation_probability,relative_humidity_2m',
    daily: 'precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min',
    past_days: '1', forecast_days: '2', timezone: 'auto', timeformat: 'unixtime',
  })
  const response = await fetch(`${API}?${params}`, { signal })
  if (!response.ok) throw new Error(`Weather service returned ${response.status}.`)
  const raw = await response.json()
  if (!raw.current || !raw.hourly || !raw.daily) throw new Error('The weather service returned incomplete observations.')
  const now = raw.current.time
  const observed = raw.hourly.time.map((time, index) => ({
    time,
    temperature: raw.hourly.temperature_2m[index],
    apparent: raw.hourly.apparent_temperature[index],
    precipitation: raw.hourly.precipitation[index],
    probability: raw.hourly.precipitation_probability[index],
    humidity: raw.hourly.relative_humidity_2m[index],
  }))
  const past24 = observed.filter((point) => point.time <= now && point.time > now - 24 * 60 * 60)
  const next24 = observed.filter((point) => point.time > now && point.time <= now + 24 * 60 * 60)
  const recentRain = past24.reduce((sum, point) => sum + (point.precipitation ?? 0), 0)
  const forecastRain = next24.reduce((sum, point) => sum + (point.precipitation ?? 0), 0)
  const days = raw.daily.time.map((time, index) => ({
    time,
    precipitation: raw.daily.precipitation_sum[index],
    precipitationProbability: raw.daily.precipitation_probability_max[index],
    maxTemperature: raw.daily.temperature_2m_max[index],
    minTemperature: raw.daily.temperature_2m_min[index],
  }))
  return {
    city, timezone: raw.timezone, elevation: raw.elevation, fetchedAt: Date.now(),
    current: raw.current, recentRain: Math.round(recentRain * 10) / 10,
    forecastRain: Math.round(forecastRain * 10) / 10,
    forecastRainProbability: next24.length ? Math.max(...next24.map((point) => point.probability ?? 0)) : null,
    past24, next24, days,
    attribution: 'Weather model data: Open-Meteo. Current conditions reflect the selected city-centre grid cell.',
  }
}

