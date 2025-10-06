// Fetch current weather data from Open-Meteo
function getWeatherData(cityName, callback) {
    const geocodingUrl = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cityName)}&format=json&limit=1`;

    // First, get the latitude and longitude of the city using OpenStreetMap's Nominatim API
    $.get(geocodingUrl, function (geoData) {
        if (geoData && geoData.length > 0) {
            const { lat: latitude, lon: longitude, display_name } = geoData[0];

            // Fetch weather data using the latitude and longitude
            const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current_weather=true&temperature_unit=fahrenheit&wind_speed_unit=mph&hourly=relative_humidity_2m,apparent_temperature,precipitation_probability`;

            $.get(weatherUrl, function (weatherData) {
                console.log("API Response (Current Weather):", weatherData); // Log the API response for debugging
                console.log("Total Rain Probability Data:", weatherData.hourly.precipitation_probability); // Log rain probability data

                if (weatherData && weatherData.current_weather && weatherData.hourly) {
                    const currentWeather = weatherData.current_weather;

                    // Get the current time in GMT
                    const currentTime = new Date().toISOString(); // Current time in ISO format (GMT)

                    // Find the index of the closest time in the hourly data
                    const timeIndex = weatherData.hourly.time.findIndex(hour => hour === currentTime.slice(0, 13) + ":00");

                    // Print the timeIndex for debugging
                    console.log("Time Index:", timeIndex);

                    if (timeIndex !== -1) {
                        // Get the rain probabilities for the previous 2 hours, current hour, and the next 5 hours
                        const previousHours = timeIndex === 0 
                            ? [weatherData.hourly.precipitation_probability[timeIndex]] 
                            : weatherData.hourly.precipitation_probability.slice(Math.max(0, timeIndex - 2), timeIndex);
                        const currentHour = [weatherData.hourly.precipitation_probability[timeIndex]];
                        const nextHours = weatherData.hourly.precipitation_probability.slice(timeIndex + 1, timeIndex + 6);

                        // Combine the previous, current, and next hours into a single array
                        const combinedHours = [...previousHours, ...currentHour, ...nextHours];

                        // Find the maximum rain probability
                        const rainPercentage = combinedHours.length > 0 ? Math.max(...combinedHours) : 0;
                        console.log("Current Rain Probability Data:", combinedHours); // Log combined rain probability data
                        // console.log("Maximum Rain Probability:", rainPercentage);

                        // Add the rain percentage to the current weather object
                        currentWeather.rain_percentage = rainPercentage;

                        // Use the humidity and feels like temperature at the current time
                        currentWeather.relative_humidity_2m = weatherData.hourly.relative_humidity_2m[timeIndex];
                        currentWeather.feels_like = weatherData.hourly.apparent_temperature[timeIndex];

                        console.log("Current Humidity:", currentWeather.relative_humidity_2m);
                        console.log("Feels Like Temperature:", currentWeather.feels_like);

                    } else {
                        console.error("No matching time found in hourly data.");
                    }

                    // Use the country from the Nominatim API's address field
                    const countryName = display_name.split(',').pop().trim() || "Unknown Country";

                    console.log("Full Address:", display_name);
                    // Print is_day and weathercode values to the console
                    console.log("is_day:", currentWeather.is_day);
                    console.log("weathercode:", currentWeather.weathercode);

                    $('#errorMessage').fadeOut(350); // Hide the error message if the request succeeds
                    callback(currentWeather, geoData[0]); // Pass weather and location data
                } else {
                    console.error("Unexpected API response:", weatherData);
                    $("#locationModal .loader").attr("class", "loader").html("&#10005;");
                }
            }).fail(function (jqXHR, textStatus, errorThrown) {
                console.error("API request failed:", textStatus, errorThrown);
                console.error("Response Text:", jqXHR.responseText); // Log the response text for debugging
                showError('Network error. Please try again.');
            });
        } else {
            console.error("Geocoding failed:", geoData);
            $("#locationModal .loader").attr("class", "loader").html("&#10005;");
        }
    }).fail(function (jqXHR, textStatus, errorThrown) {
        console.error("Geocoding request failed:", textStatus, errorThrown);
        console.error("Response Text:", jqXHR.responseText); // Log the response text for debugging
        showError('Network error. Please try again.');
    });
}

// Fetch weekly forecast data from Open-Meteo
function getWeeklyForecast(cityName, callback) {
    const geocodingUrl = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cityName)}&format=json&limit=1`;

    // First, get the latitude and longitude of the city using OpenStreetMap's Nominatim API
    $.get(geocodingUrl, function (geoData) {
        if (geoData && geoData.length > 0) {
            const { lat: latitude, lon: longitude } = geoData[0];

            // Fetch forecast data using the latitude and longitude
            const forecastUrl = `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&daily=temperature_2m_min,temperature_2m_max,weathercode&temperature_unit=fahrenheit&timezone=auto`;

            $.get(forecastUrl, function (forecastData) {
                console.log("API Response (Weekly Forecast):", forecastData); // Log the API response for debugging
                if (forecastData && forecastData.daily) {
                    const dailyForecasts = processForecastData(forecastData.daily);
                    callback(dailyForecasts);
                } else {
                    console.error("Unexpected API response:", forecastData);
                    showError('Invalid data received from the weather API.');
                }
            }).fail(function (jqXHR, textStatus, errorThrown) {
                console.error("API request failed:", textStatus, errorThrown);
                console.error("Response Text:", jqXHR.responseText); // Log the response text for debugging
                showError('Network error. Please try again.');
            });
        } else {
            console.error("Geocoding failed:", geoData);
            showError('City not found. Please enter a valid city name.');
        }
    }).fail(function (jqXHR, textStatus, errorThrown) {
        console.error("Geocoding request failed:", textStatus, errorThrown);
        console.error("Response Text:", jqXHR.responseText); // Log the response text for debugging
        showError('Network error. Please try again.');
    });
}

// Process forecast data from Open-Meteo
function processForecastData(dailyData) {
    const { time, temperature_2m_min, temperature_2m_max, weathercode } = dailyData;

    const slicedTime = time.slice(0, 4); // Get the first four days of data

    // Include the first four days (indices 0 to 3)
    return slicedTime.map((date, index) => ({
        day: new Date(date + 'T00:00:00Z').toLocaleDateString('en-US', { weekday: 'short', timeZone: 'UTC' }),
        tempMin: temperature_2m_min[index],
        tempMax: temperature_2m_max[index],
        icon: weathercode[index],
    }));
}

// Update the render function to use Open-Meteo data
function render(cityName) {
    $('.border .sync').addClass('busy');
    $(".border .settings").show();

    getWeatherData(cityName, function (currentWeather, locationData) {
        if (!currentWeather || !locationData) {
            console.error("Failed to fetch weather data.");
            showError('Failed to fetch weather data. Please try again.');
            return;
        }

        // Update the city div with a hyperlink
        const mapUrl = `https://www.openstreetmap.org/?mlat=${locationData.lat}&mlon=${locationData.lon}#map=10/${locationData.lat}/${locationData.lon}`;
        const countryName = locationData.display_name.split(',').pop().trim() || "Unknown Country"; // Extract country from display_name
        
        $('#city span').html(`<a href="${mapUrl}">${locationData.name}, ${countryName}</a>`);
        const iconChar = weather_code(currentWeather.weathercode, currentWeather.is_day);
        const codeClass = "w" + currentWeather.weathercode;
        $("#code").text(iconChar).attr("class", codeClass + (iconChar === "/" ? " moon-large" : ""));
        // Sets initial temp as Fahrenheit
        let temp = currentWeather.temperature;

        if (temp < 32) {
            $("#thermometer").text("_");
        } else if (temp < 55) {
            $("#thermometer").text("+");
        } else if (temp < 85) {
            $("#thermometer").text("Q");
        } else if (temp < 100) {
            $("#thermometer").text("W");
        } else {
            $("#thermometer").text("E");
        }

        if (localStorage.typhoon_measurement == "c") {
            temp = Math.round((temp - 32) * 5 / 9); // Convert to Celsius
            $("#temperature").text(temp + " °C");
        } else if (localStorage.typhoon_measurement == "k") {
            temp = Math.round((temp - 32) * 5 / 9 + 273.15); // Convert to Kelvin
            $("#temperature").text(temp + " K");
        } else {
            temp = Math.round(temp); // Round to the nearest integer for Fahrenheit
            $("#temperature").text(temp + " °F");
        }
        document.title = temp;

        let windSpeed = currentWeather.windspeed;
        if (localStorage.typhoon_speed != "mph") {
            // Converts to either kph or m/s
            windSpeed = (localStorage.typhoon_speed == "kph") ? Math.round(windSpeed * 1.609344) : Math.round(windSpeed * 4.4704) / 10;
        }
        $("#windSpeed").text(windSpeed);
        $("#windUnit").text((localStorage.typhoon_speed == "ms") ? "m/s" : (localStorage.typhoon_speed == "kph") ? "km/h" : localStorage.typhoon_speed);
        $("#humidity").html(
            `<div title="Humidity" style="display: inline-block; position: relative; padding: 0px;">
            <img id="humidityIcon" src="humidity.svg" height="18" style="vertical-align: middle; filter: none; box-shadow: none;"> 
            ${currentWeather.relative_humidity_2m} %
            </div>`
        );

        // Update "Feels Like" and "Rain Propability"
        const feelsLike = localStorage.typhoon_measurement === "c"
            ? Math.round((currentWeather.feels_like - 32) * 5 / 9) + "°C"
            : localStorage.typhoon_measurement === "k"
            ? Math.round((currentWeather.feels_like - 32) * 5 / 9 + 273.15) + "K"
            : Math.round(currentWeather.feels_like) + "°F";

        $("#feelsLike").text(`Feels Like: ${feelsLike}`);
        const shouldShake = currentWeather.rain_percentage > 35;
        $("#rainPercentage").html(
            `<span id="umbrellaIcon" style="font-family: 'ClimaconsRegular'; font-size: 1.2em; vertical-align: top;${shouldShake ? '' : ''}"${shouldShake ? ' class="shake-umbrella"' : ''}>{</span>${currentWeather.rain_percentage}%`
        );
        // Show the additional-info div when weather data is available
        $('.additional-info').removeClass('hidden');

        // Background Color
        background(currentWeather.temperature);

        // Show Icon
        $('.border .sync, .border .settings').css("opacity", "0.8");
        $('#actualWeather').fadeIn(500);
        $("#humidityIcon").css("opacity", "1");
        $("#locationModal").fadeOut(500);
        setTimeout(function () { $('.border .sync').removeClass('busy'); }, 1000);

        // Fetch and render weekly forecast
        getWeeklyForecast(cityName, function (weeklyData) {
            renderWeeklyForecast(weeklyData);
        });
    });
}

function renderWeeklyForecast(weeklyData) {
    // Render the weekly forecast in the "week" div
    weeklyData.forEach((day, index) => {
        const unit = localStorage.typhoon_measurement || "f"; // Default to Fahrenheit
        let tempMin = day.tempMin;
        let tempMax = day.tempMax;

        // Convert temperatures based on the selected unit
        if (unit === "c") {
            tempMin = Math.round((tempMin - 32) * 5 / 9); // Convert to Celsius
            tempMax = Math.round((tempMax - 32) * 5 / 9);
        } else if (unit === "k") {
            tempMin = Math.round((tempMin - 32) * 5 / 9 + 273.15); // Convert to Kelvin
            tempMax = Math.round((tempMax - 32) * 5 / 9 + 273.15);
        } else {
            tempMin = Math.round(tempMin); // Round to the nearest integer for Fahrenheit
            tempMax = Math.round(tempMax);
        }

        // Adjust font size for Kelvin
        const tempElement = $(`#${index} .temp`);
        if (unit === "k") {
            tempElement.css("font-size", "0.85em"); // Smaller font size for Kelvin
        } else {
            tempElement.css("font-size", "1em"); // Default font size for other units
        }

        // Update the DOM with the converted temperatures and Climacons icon
        $(`#${index} .day`).text(day.day);
        $(`#${index} .code`)
            .text(weather_code(day.icon, 1))
            .attr("class", `code w${day.icon}`);
        tempElement.text(`${tempMin}${unit === 'k' ? '' : '°'} / ${tempMax}${unit === 'k' ? '' : '°'} ${unit.toUpperCase()}`);
    });
}

function background(temp) {
    // Convert RGB array to CSS
    var convert = function(i) {
        // Array to RGB
        if (typeof(i) == 'object') {
            return 'rgb(' + i.join(', ') + ')';

        // Hex to array
        } else if (typeof(i) == 'string') {
            var output = [];
            if (i[0] == '#') i = i.slice(1);
            if (i.length == 3)    i = i[0] + i[0] + i[1] + i[1] + i[2] + i[2];
            output.push(parseInt(i.slice(0,2), 16))
            output.push(parseInt(i.slice(2,4), 16))
            output.push(parseInt(i.slice(4,6), 16))
            return output;
        }
    };

    // Get color at position
    var blend = function(x) {
        x = Number(x)
        var gradient = [{
            pos: 0,
            color: convert('#0081d3')
        }, {
            pos: 10,
            color: convert('#007bc2')
        }, {
            pos: 20,
            color: convert('#0071b2')
        }, {
            pos: 30,
            color: convert('#2766a2')
        }, {
            pos: 40,
            color: convert('#575591')
        }, {
            pos: 50,
            color: convert('#94556b')
        }, {
            pos: 60,
            color: convert('#af4744')
        }, {
            pos: 70,
            color: convert('#bb4434')
        }, {
            pos: 80,
            color: convert('#c94126')
        }, {
            pos: 90,
            color: convert('#d6411b')
        }, {
            pos: 100,
            color: convert('#e44211')
        }];

        var left = {
            pos: -1,
            color: false,
            percent: 0
        };
        var right = {
            pos: 101,
            color:  false,
            percent: 0
        };

        // Get the 2 closest stops to the specified position
        for (var i=0, l=gradient.length; i<l; i++) {
            var stop = gradient[i];
            if (stop.pos <= x && stop.pos > left.pos) {
                left.pos = stop.pos;
                left.color = stop.color;
            } else if (stop.pos >= x && stop.pos < right.pos) {
                right.pos = stop.pos;
                right.color = stop.color;
            }
        }

        // If there is no stop to the left or right
        if (!left.color) {
            return convert(right.color);
        } else if (!right.color) {
            return convert(left.color);
        }

        // Calculate percentages
        right.percent = Math.abs(1 / ((right.pos - left.pos) / (x - left.pos)));
        left.percent = 1 - right.percent;

        // Blend colors!
        var blend = [
            Math.round((left.color[0] * left.percent) + (right.color[0] * right.percent)),
            Math.round((left.color[1] * left.percent) + (right.color[1] * right.percent)),
            Math.round((left.color[2] * left.percent) + (right.color[2] * right.percent)),
        ];
        return convert(blend);
    };

    //Sets Background Color
    if (localStorage.typhoon_color == "gradient") {
        var percentage = Math.round((temp - 45) *  2.2)
        $("#container").css("background", blend(percentage))
    } else if (localStorage.typhoon_color == "chameleonic") {
        $("#container").css("background", '#' + localStorage.typhoon_special_color)
        $('.color span[data-color=chameleonic]').css("background", '#' + localStorage.typhoon_special_color)
    } else if (localStorage.typhoon_color == "custom" && localStorage.typhoon_custom_color) {
        $("#container").css("background", localStorage.typhoon_custom_color);
    } else {
        $("#container").css("background", "#" + localStorage.typhoon_color)
    }
// Custom Color Picker logic
$(function() {
    const customColorPicker = $('#customColorPicker');
    if (localStorage.typhoon_custom_color) {
        customColorPicker.val(localStorage.typhoon_custom_color);
    }
    function applyCustomColorInstantly(color) {
        localStorage.typhoon_color = 'custom';
        localStorage.typhoon_custom_color = color;
        $("#container").css("background", color);
        $('.color span').removeClass('selected');
        customColorPicker.addClass('selected');
    }
    customColorPicker.on('input', function() {
        applyCustomColorInstantly($(this).val());
    });
    customColorPicker.on('change', function() {
        applyCustomColorInstantly($(this).val());
    });
});
}

// Converts Open-Meteo weather codes to Climacons icons
function weather_code(iconCode, isDay) {
    const climaconMapDay = {
        "0": "v", // Clear sky (day)
        "1": "1", // Mainly clear (day)
        "2": "d", // Partly cloudy (day)
        "3": "`", // Overcast (day)
        "45": "h", // Fog (day)
        "48": "g", // Depositing rime fog (day)
        "51": "0", // Drizzle: Light (day)
        "53": "9", // Drizzle: Moderate (day)
        "55": "9", // Drizzle: Dense intensity (day)
        "56": "r", // Freezing Drizzle: Light (day)
        "57": "y", // Freezing Drizzle: Dense intensity (day)
        "61": "0", // Rain: Slight (day)
        "63": "9", // Rain: Moderate (day)
        "65": "9", // Rain: Heavy intensity (day)
        "66": "r", // Freezing Rain: Light (day)
        "67": "e", // Freezing Rain: Heavy (day)
        "71": "=", // Snow fall: Slight (day)
        "73": "o", // Snow fall: Moderate (day)
        "75": "6", // Snow fall: Heavy (day)
        "77": "6", // Snow grains (day)
        "80": "0", // Rain showers: Slight (day)
        "81": "9", // Rain showers: Moderate (day)
        "82": "9", // Rain showers: Violent (day)
        "85": "6", // Snow showers: Slight (day)
        "86": "6", // Snow showers: Heavy (day)
        "95": "z", // Thunderstorm: Slight or moderate (day)
        "96": "z", // Thunderstorm with slight hail (day)
        "99": "z"  // Thunderstorm with heavy hail (day)
    };

    const climaconMapNight = {
        "0": "/", // Clear sky (night)
        "1": "2", // Mainly clear (night)
        "2": "f", // Partly cloudy (night)
        "3": "`", // Overcast (night)
        "45": "g", // Fog (night)
        "48": "g", // Depositing rime fog (night)
        "51": "5", // Drizzle: Light (night)
        "53": "-", // Drizzle: Moderate (night)
        "55": "9", // Drizzle: Dense intensity (night)
        "56": "i", // Freezing Drizzle: Light (night)
        "57": "y", // Freezing Drizzle: Dense intensity (night)
        "61": "5", // Rain: Slight (night)
        "63": "-", // Rain: Moderate (night)
        "65": "9", // Rain: Heavy intensity (night)
        "66": "t", // Freezing Rain: Light (night)
        "67": "e", // Freezing Rain: Heavy (night)
        "71": "[", // Snow fall: Slight (night)
        "73": "8", // Snow fall: Moderate (night)
        "75": "6", // Snow fall: Heavy (night)
        "77": "6", // Snow grains (night)
        "80": "9", // Rain showers: Slight (night)
        "81": "9", // Rain showers: Moderate (night)
        "82": "9", // Rain showers: Violent (night)
        "85": "6", // Snow showers: Slight (night)
        "86": "6", // Snow showers: Heavy (night)
        "95": "z", // Thunderstorm: Slight or moderate (night)
        "96": "z", // Thunderstorm with slight hail (night)
        "99": "z"  // Thunderstorm with heavy hail (night)
    };

    // Return the corresponding Climacon icon based on day or night
    if (isDay) {
        return climaconMapDay[iconCode] || "`"; // Default to a cloud icon if no match is found
    } else {
        return climaconMapNight[iconCode] || "`"; // Default to a cloud icon if no match is found
    }
}

function receiveMessage(message) {
    // Save the received message as a localStorage item
    localStorage.setItem("typhoon_special_color", message);
}

$(document).ready(function() {
    // Set the size
    scaleContent();

    //APP START.
    init_settings()
    if (!localStorage.typhoon) {
        show_settings("location")
    } else {
        //Has been run before
        render(localStorage.typhoon)

        setInterval(function() {
            console.log("Updating Data...")
            document.title = "refreshing data";
            $(".border .sync").click()
        }, 1200000)
    }

    // Add event listener for the reset button
    $('#resetButton').click(function () {
            localStorage.clear(); // Clear all local storage
            document.title="reset";
            location.reload(); // Reload the page to apply default settings
    });

    // Attach event listener to the city name input field
    const locationInput = $("#locationModal input");

    locationInput.keyup(function (event) {
        if (event.key === "Enter") {
            const cityName = locationInput.val().trim(); // Get the trimmed input value

            if (cityName === "") {
                // If the input is empty, do nothing
                console.log("City name is empty. No search performed.");
                return;
            }

            // Perform the search only if the input is not empty
            getWeatherData(cityName, function (data) {
                if (data) {
                    console.log("Weather data fetched successfully.");
                    $("#locationModal .loader").attr("class", "tick loader").html("&#10003;").attr("data-city", cityName);
                } else {
                    console.log("Failed to fetch weather data.");
                    $("#locationModal .loader").attr("class", "loader").html("&#10005;");
                }
            });
        }
    });

    // Guess Location button handler
    $('#guessLocationBtn').click(function() {
        guessLocation(function(locationString) {
            $("#locationModal input").val(locationString);
            // Show loading indicator
            $("#locationModal .loader").attr("class", "loading loader").html("|");
            // Set opacity slider to localStorage value
            $('input[type=range]').val(localStorage.app_opacity);
            // Fetch weather data for the guessed location
            getWeatherData(locationString, function(data) {
                if (data) {
                    $("#locationModal .loader").attr("class", "tick loader").html("&#10003;").attr("data-city", locationString);
                } else {
                    $("#locationModal .loader").attr("class", "loader").html("&#10005;");
                }
            });
        });
    });
});

function init_settings() {
    // Prevents Dragging on certain elements
    $('.border .settings, .border .sync, .border .close, .border .minimize, #locationModal input, #locationModal .measurement span, #locationModal .speed span, #locationModal .loader, #locationModal a, #locationModal .color, #locationModal .btn, #errorMessage .btn, #city span, #locationModal img').mouseover(function() {
        document.title = "disabledrag";
    }).mouseout(function() {
        document.title = "enabledrag";
    }).click(function() {
        if ($(this).hasClass("close")) {
            document.title = 'close';
        } else if ($(this).hasClass("minimize")) {
            document.title = 'minimize';
        } else if ($(this).hasClass("settings")) {
            show_settings("all");
        } else if ($(this).hasClass("sync")) {
            if (localStorage.typhoon_color === "chameleonic") {
                location.reload();
                document.title = "enabledrag"
            } else {
                render(localStorage.typhoon);
            }
        }
    });

    // First Run
    var locationInput = $("#locationModal input");
    var typingTimer;
    var doneTypingInterval = 1500;

    // On keyup, start the countdown
    locationInput.keyup(function() {
        typingTimer = setTimeout(doneTyping, doneTypingInterval);
    }).keydown(function() {
        // On keydown, clear the countdown
        clearTimeout(typingTimer);
    });

    function doneTyping() {
        $("#locationModal .loader").attr("class", "loading loader").html("|");
        const cityName = locationInput.val();
        getWeatherData(cityName, function(data) {
            if (data) {
                $("#locationModal .loader").attr("class", "tick loader").html("&#10003;").attr("data-city", cityName);
            } else {
                $("#locationModal .loader").attr("class", "loader").html("&#10005;");
            }
        });
    }

    // This can only be run if there is a tick.
    $("#locationModal .loader").click(function() {
        if ($(this).hasClass("tick")) {
            const cityName = $("#locationModal .loader").attr("data-city");
            localStorage.typhoon = cityName;
            render(cityName);
            show_settings("noweather");
            setInterval(function() {
                console.log("Updating Data...");
                $(".border .sync").click();
            }, 1200000);
        }
    });

    // Sets up localstorage
    localStorage.typhoon_measurement = localStorage.typhoon_measurement || "c";
    localStorage.typhoon_speed = localStorage.typhoon_speed || "kph";
    localStorage.typhoon_color = localStorage.typhoon_color || "gradient";
    localStorage.typhoon_launcher = localStorage.typhoon_launcher || "checked";
    document.title = "enable_launcher"

    $('#locationModal .measurement [data-type=' + localStorage.typhoon_measurement + ']').addClass('selected');
    $('#locationModal .speed [data-type=' + localStorage.typhoon_speed + ']').addClass('selected');

    //Sets up the Toggle Switches
    $('#locationModal .toggleswitch span').click(function() {
        $(this).parent().children().removeClass('selected')
        localStorage.setItem("typhoon_" + $(this).parent().attr("class").replace("toggleswitch ", ""), $(this).addClass('selected').attr("data-type"))
        $(".border .settings").hide()
    })

    //Color thing
    $('.color span').click(function() {
        localStorage.typhoon_color = $(this).attr("data-color")
        background(null)
    })
    $('.color span[data-color=gradient]').click(function() {
        $(".border .settings").hide()
    })
    $('.color span[data-color=chameleonic]').click(function() {
        $(".border .settings").hide()
        localStorage.typhoon_color = "chameleonic"
        location.reload()
        document.title = "enabledrag"
        $(this).css('background', '#' + localStorage.typhoon_special_color)
    })
    

    if (localStorage.typhoon_launcher == "checked") {
        $('#locationModal .launcher input').attr("checked", "checked")
        document.title = "enable_launcher"
    }
    $('#locationModal .launcher input').click(function() {
        localStorage.typhoon_launcher = $('#locationModal .launcher input').prop("checked") ? "checked" : "unchecked";
        if (localStorage.typhoon_launcher === "checked") {
            document.title = "enable_launcher";
        } else {
            document.title = "disable_launcher";
        }
    });

    if (localStorage.typhoon_launcher === "checked") {
        $('#locationModal .launcher input').prop("checked", true);
        document.title = "enable_launcher";
    } else {
        $('#locationModal .launcher input').prop("checked", false);
        document.title = "disable_launcher";
    }

    //Control CSS.
    $("span[data-color]:not([data-color=gradient])").map(function() { $(this).css('background', '#' + $(this).attr("data-color")) })

    /* Error Message Retry Button */
    $('#errorMessage .btn').click(function() {
    if (!localStorage.typhoon) {
        location.reload();
    } else {
        //Has been run before
        render(localStorage.typhoon)
    }
    })

}

function guessLocation(callback) {
    $.get("https://ipapi.co/json/", function(data) {
        if (data && data.city && data.region && data.country) {
            const locationString = `${data.city}, ${data.region}, ${data.country}`;
            callback(locationString);
        } else {
            showError("Could not guess your location.");
        }
    }).fail(function() {
        showError("Could not guess your location.");
    });
}

function show_settings(amount) {

    if (amount == 'all') {
        $("#locationModal .full").show()
        $("#locationModal .credits").hide()
    } else if (amount == 'location') {
        $("#locationModal .full").hide()
        $("#locationModal .credits").hide()
    }
    $('.btn[tag="credits"]').click(function() {
        $("#locationModal .input, #locationModal .full, .settings, .sync").hide()
        $("#locationModal .credits").fadeIn(500)
    })
    $('#locationModal .credits img').click(function() {
        $("#locationModal .credits").fadeOut(350)
        $("#locationModal .input, #locationModal .full, .settings, .sync").fadeIn(350)
    })
    //Show the Modal
    $("#locationModal").fadeToggle(350)
    if (amount != "noweather") {
        $("#actualWeather").fadeToggle(350)
    }
}
function showError(message) {
    // Show the error message and retry button
    $('#errorMessage').fadeIn(350);
    // Hide the actual weather display
    $('#actualWeather').fadeOut(350);
}

function opacity() {
    // On first run, opacity would be 0.8
    if (localStorage.getItem("app_opacity") === null) {
        localStorage.app_opacity = 0.8;
        document.title = "o" + localStorage.app_opacity;
    }

    const slider = $('input[type=range]');
    slider.val(localStorage.app_opacity);
    document.title = "o" + localStorage.app_opacity;

    // Update opacity dynamically as the slider value changes
    slider.on('input', function () {
        const newOpacity = $(this).val();
        console.log("Opacity value:", newOpacity); // Print the value to the console
        document.title = "o" + newOpacity; // Update the title dynamically
        localStorage.app_opacity = newOpacity; // Save the new value to localStorage
    });
}

$(window).on('resize', function () {
    scaleContent();
});

function scaleContent() {
    const originalWidth = 300; // Original width
    const originalHeight = 500; // Original height
    const aspectRatio = originalWidth / originalHeight;

    // Get the current window size
    const windowWidth = $(window).width();
    const windowHeight = $(window).height();

    // Calculate the scale factor while maintaining the aspect ratio
    const scaleFactor = Math.min(windowWidth / originalWidth, windowHeight / originalHeight);

    // Apply the scale to the app wrapper
    $('#appWrapper').css({
        transform: `scale(${scaleFactor})`,
        transformOrigin: 'top left', // Scale from the top-left corner
        width: `${originalWidth}px`, // Maintain original width
        height: `${originalHeight}px`, // Maintain original height
    });
}
