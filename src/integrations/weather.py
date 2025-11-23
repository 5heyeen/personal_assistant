"""Weather integration using Open-Meteo API (free, no API key required)."""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..utils.config import get_config
from ..utils.logger import get_logger


class WeatherIntegration:
    """Handles weather data retrieval and analysis."""

    def __init__(self, latitude: float = 59.9139, longitude: float = 10.7522):
        """Initialize Weather integration.

        Args:
            latitude: Location latitude (default: Oslo)
            longitude: Location longitude (default: Oslo)
        """
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.latitude = latitude
        self.longitude = longitude
        self.api_base = "https://api.open-meteo.com/v1/forecast"

    def get_today_forecast(self) -> Optional[Dict[str, Any]]:
        """Get today's weather forecast.

        Returns:
            Dictionary with weather data
        """
        try:
            params = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'hourly': 'temperature_2m,precipitation,precipitation_probability,weathercode',
                'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode',
                'timezone': 'auto',
                'forecast_days': 1
            }

            response = requests.get(self.api_base, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse response
            daily = data.get('daily', {})
            hourly = data.get('hourly', {})

            forecast = {
                'temp_min': daily.get('temperature_2m_min', [0])[0],
                'temp_max': daily.get('temperature_2m_max', [0])[0],
                'precipitation_total': daily.get('precipitation_sum', [0])[0],
                'hourly_temps': hourly.get('temperature_2m', []),
                'hourly_precipitation': hourly.get('precipitation', []),
                'hourly_times': hourly.get('time', []),
                'weathercode': daily.get('weathercode', [0])[0]
            }

            self.logger.info(f"Retrieved weather: {forecast['temp_min']}-{forecast['temp_max']}°C")
            return forecast

        except Exception as e:
            self.logger.error(f"Error getting weather: {e}")
            return None

    def get_rain_periods(self, forecast: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract rain periods from hourly forecast.

        Args:
            forecast: Forecast data from get_today_forecast()

        Returns:
            List of rain period dictionaries
        """
        rain_periods = []

        if not forecast:
            return rain_periods

        hourly_precip = forecast.get('hourly_precipitation', [])
        hourly_times = forecast.get('hourly_times', [])

        current_period = None

        for i, precip in enumerate(hourly_precip):
            if precip > 0.1:  # Threshold for rain (mm)
                time_str = hourly_times[i]
                hour = datetime.fromisoformat(time_str).hour

                if current_period is None:
                    current_period = {'start': hour, 'end': hour}
                else:
                    current_period['end'] = hour
            else:
                if current_period:
                    rain_periods.append(current_period)
                    current_period = None

        if current_period:
            rain_periods.append(current_period)

        return rain_periods

    def get_temperature_advice(self, forecast: Dict[str, Any]) -> List[str]:
        """Generate contextual temperature advice with personality.

        Args:
            forecast: Forecast data from get_today_forecast()

        Returns:
            List of advice strings
        """
        advice = []

        if not forecast:
            return advice

        temp_min = forecast.get('temp_min', 0)
        temp_max = forecast.get('temp_max', 0)
        hourly_temps = forecast.get('hourly_temps', [])
        hourly_times = forecast.get('hourly_times', [])

        # Temperature descriptions with personality
        if temp_min < 0:
            morning_desc = f"Brr! It's a freezing {int(temp_min)}°C this morning"
        elif temp_min < 5:
            morning_desc = f"Bundle up! It's a chilly {int(temp_min)}°C to start"
        elif temp_min < 10:
            morning_desc = f"It's a cool {int(temp_min)}°C this morning"
        elif temp_min < 15:
            morning_desc = f"Mild start at {int(temp_min)}°C"
        else:
            morning_desc = None

        if morning_desc:
            # Add warming advice
            if temp_max - temp_min > 10:
                advice.append(f"{morning_desc}, but warming up to {int(temp_max)}°C - layers are your friend!")
            else:
                advice.append(f"{morning_desc}. Dress warmly!")

        # Find evening temperature (18:00-22:00)
        evening_temp = None
        for i, time_str in enumerate(hourly_times):
            hour = datetime.fromisoformat(time_str).hour
            if 18 <= hour <= 22:
                if evening_temp is None or i < len(hourly_temps):
                    evening_temp = hourly_temps[i] if i < len(hourly_temps) else None

        if evening_temp and evening_temp < 10:
            advice.append(f"Evening gets chilly at {int(evening_temp)}°C - grab a jacket if you're heading out!")
        elif evening_temp and 10 <= evening_temp < 15:
            advice.append(f"Cool evening at {int(evening_temp)}°C - might want a light layer")

        if temp_max > 25:
            advice.append(f"Warm day peaking at {int(temp_max)}°C - stay hydrated! 💧")

        return advice

    def format_rain_summary(self, forecast: Dict[str, Any]) -> Optional[str]:
        """Format rain timing summary.

        Args:
            forecast: Forecast data from get_today_forecast()

        Returns:
            Formatted rain summary string
        """
        rain_periods = self.get_rain_periods(forecast)

        if not rain_periods:
            return None

        summaries = []
        for period in rain_periods:
            start = period['start']
            end = period['end']
            if start == end:
                summaries.append(f"{start:02d}:00")
            else:
                summaries.append(f"{start:02d}:00-{end:02d}:00")

        return ", ".join(summaries)

    def format_weather_summary(self, forecast: Dict[str, Any]) -> str:
        """Format complete weather summary.

        Args:
            forecast: Forecast data from get_today_forecast()

        Returns:
            Formatted weather string
        """
        if not forecast:
            return "☀️ Weather unavailable"

        temp_min = int(forecast.get('temp_min', 0))
        temp_max = int(forecast.get('temp_max', 0))

        summary = f"☀️ {temp_min}-{temp_max}°C"

        rain_summary = self.format_rain_summary(forecast)
        if rain_summary:
            summary += f", 💧 {rain_summary}"

        return summary

    def get_rain_warnings_for_events(
        self,
        forecast: Dict[str, Any],
        events: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Check which events might have rain.

        Args:
            forecast: Forecast data
            events: List of calendar events

        Returns:
            Dictionary mapping event summaries to rain warnings
        """
        warnings = {}

        if not forecast:
            return warnings

        rain_periods = self.get_rain_periods(forecast)

        for event in events:
            start_time = event.get('start')
            if not start_time:
                continue

            event_hour = start_time.hour
            event_summary = event.get('summary', 'Event')

            # Check if event time overlaps with rain
            for period in rain_periods:
                if period['start'] <= event_hour <= period['end']:
                    warnings[event_summary] = "☂️"
                    break

        return warnings
