// Save the API key to local storage
function saveApiKey() {
    const apiKey = $("#apiKeyInput").val();
    if (apiKey) {
        localStorage.setItem("typhoon_apiKey", apiKey);
        // alert("API Key saved successfully!");
        $("#apiKeyContainer").hide(); // Hide the API key input and button after saving
    } else {
        alert("Please enter a valid API Key.");
    }
}

// Retrieve the API key from local storage
function getApiKey() {
    const apiKey = localStorage.getItem("typhoon_apiKey");
    if (!apiKey) {
        alert("API Key not found. Please enter and save your API Key.");
        $("#apiKeyContainer").show(); // Show the API key input and button if the key is missing
    }
    return apiKey;
}

// Show the API key input and button in case of errors
function handleApiKeyError() {
    alert("Invalid API Key or Network Error. Please enter a valid API Key.");
    $("#apiKeyContainer").show(); // Show the API key input and button
}

// Attach event listener to the Save API Key button
$(document).ready(function () {
    $("#saveApiKeyButton").click(saveApiKey);

    // Check if the API key exists in local storage
    const savedApiKey = localStorage.getItem("typhoon_apiKey");
    if (savedApiKey) {
        $("#apiKeyContainer").hide(); // Hide the API key input and button if the key exists
    } else {
        $("#apiKeyContainer").show(); // Show the API key input and button if the key doesn't exist
    }

    // Pre-fill the API key input field if it exists in local storage
    if (savedApiKey) {
        $("#apiKeyInput").val(savedApiKey);
    }
});

const apiKey = "585f5b44d354b4368bfd4ca7b24f1823"; // Replace with your actual API key

function getWeatherData(cityName, callback) {
    const apiKey = getApiKey();
    if (!apiKey) return;

    const url = `https://api.openweathermap.org/data/2.5/weather?q=${encodeURIComponent(cityName)}&units=imperial&appid=${apiKey}`;

    $.get(url, function (data) {
        console.log("API Response (Current Weather):", data); // Log the API response for debugging
        if (data) {
            $('#errorMessage').fadeOut(350); // Hide the error message if the request succeeds
            callback(data);
        } else {
            console.error("Unexpected API response:", data);
            showError('Invalid data received from the weather API.');
        }
    }).fail(function (jqXHR, textStatus, errorThrown) {
        console.error("API request failed:", textStatus, errorThrown);
        console.error("Response Text:", jqXHR.responseText); // Log the response text for debugging

        // Handle API key or network errors
        if (jqXHR.status === 401) {
            handleApiKeyError(); // Invalid API key
        } else {
            // Show the retry button and error message
            showError('network');
        }
    });
}

function getWeeklyForecast(cityName, callback) {
    // Use OpenWeatherMap's 5-day/3-hour forecast API
    const url = `https://api.openweathermap.org/data/2.5/forecast?q=${encodeURIComponent(cityName)}&units=imperial&appid=${apiKey}`;

    $.get(url, function(data) {
        console.log("API Response (5-Day Forecast):", data); // Log the API response for debugging
        if (data && data.list) {
            // Process the data to extract daily forecasts
            const dailyForecasts = processForecastData(data.list);
            callback(dailyForecasts);
        } else {
            console.error("Unexpected API response:", data);
            showError('Invalid data received from the weather API.');
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.error("API request failed:", textStatus, errorThrown);
        console.error("Response Text:", jqXHR.responseText); // Log the response text for debugging
        showError('network');
    });
}

function processForecastData(forecastList) {
    // Group forecast data by day
    const dailyData = {};

    forecastList.forEach((entry) => {
        const date = new Date(entry.dt * 1000);
        const day = date.toLocaleDateString('en-US', { weekday: 'short' });

        if (!dailyData[day]) {
            dailyData[day] = {
                day: day,
                tempMin: entry.main.temp_min,
                tempMax: entry.main.temp_max,
                icon: entry.weather[0].icon,
            };
        } else {
            dailyData[day].tempMin = Math.min(dailyData[day].tempMin, entry.main.temp_min);
            dailyData[day].tempMax = Math.max(dailyData[day].tempMax, entry.main.temp_max);
        }
    });

    // Convert the grouped data into an array and return the first 5 days
    return Object.values(dailyData).slice(0, 5);
}

function generateStats(data, callback) {
    // Weather Object
    const weather = {};

    // Location
    weather.city = data.name || "Unknown";
    weather.country = data.sys.country || "Unknown";

    // Link (OpenWeatherMap doesn't provide a direct link, so we use a placeholder)
    weather.link = "https://openweathermap.org/";

    // Temperature
    weather.temperature = data.main.temp;
    weather.temperatureUnit = "F";

    // Wind
    weather.windUnit = "mph";
    weather.windSpeed = data.wind.speed;
    weather.windDirection = data.wind.deg;

    // Humidity
    weather.humidity = data.main.humidity;

    // Current Weather
    weather.code = data.weather[0].icon;

    // Coordinates for weekly forecast
    weather.lat = data.coord.lat;
    weather.lon = data.coord.lon;

    if (callback) {
        callback(weather);
    }
}

function render(cityName) {
    $('.border .sync').addClass('busy');
    $(".border .settings").show();

    getWeatherData(cityName, function(rawdata) {
        generateStats(rawdata, function(weather) {
            $('#city span').html('<a href="' + weather.link + '">' + weather.city + '</a>');
            $("#code").text(weather_code(weather.code)).attr("class", "w" + weather.code);

            // Sets initial temp as Fahrenheit
            var temp = weather.temperature;
            if (localStorage.typhoon_measurement == "c") {
                temp = Math.round((weather.temperature - 32) * 5 / 9); // Convert to Celsius
                $("#temperature").text(temp + " °C");
            } else if (localStorage.typhoon_measurement == "k") {
                temp = Math.round((weather.temperature - 32) * 5 / 9 + 273.15); // Convert to Kelvin
                $("#temperature").text(temp + " K");
            } else {
                temp = Math.round(temp); // Round to the nearest integer for Fahrenheit
                $("#temperature").text(temp + " °F");
            }
            document.title = temp;

            var windSpeed = weather.windSpeed;
            if (localStorage.typhoon_speed != "mph") {
                // Converts to either kph or m/s
                windSpeed = (localStorage.typhoon_speed == "kph") ? Math.round(windSpeed * 1.609344) : Math.round(windSpeed * 4.4704) / 10;
            }
            $("#windSpeed").text(windSpeed);
            $("#windUnit").text((localStorage.typhoon_speed == "ms") ? "m/s" : localStorage.typhoon_speed);
            $("#humidity").text(weather.humidity + " %");

            // Background Color
            background(weather.temperature);

            // Show Icon
            $('.border .sync, .border .settings').css("opacity", "0.8");
            $('#actualWeather').fadeIn(500);
            $("#locationModal").fadeOut(500);
            setTimeout(function() { $('.border .sync').removeClass('busy'); }, 500);

            // Fetch and render weekly forecast
            getWeeklyForecast(cityName, function(weeklyData) {
                renderWeeklyForecast(weeklyData);
            });
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

        // Update the DOM with the converted temperatures and Climacons icon
        $(`#${index} .day`).text(day.day);
        $(`#${index} .code`).text(weather_code(day.icon)).attr("class", "w" + day.icon);
        $(`#${index} .temp`).text(`${tempMin}° / ${tempMax}° ${unit.toUpperCase()}`);
    });
}

function renderWeeklyForecastMock() {
    const mockData = [
        { day: "Mon", tempMin: 60, tempMax: 75, icon: "01d" },
        { day: "Tue", tempMin: 62, tempMax: 78, icon: "02d" },
        { day: "Wed", tempMin: 65, tempMax: 80, icon: "03d" },
        { day: "Thu", tempMin: 63, tempMax: 77, icon: "04d" },
        { day: "Fri", tempMin: 61, tempMax: 76, icon: "09d" },
    ];

    mockData.forEach((day, index) => {
        $(`#${index} .day`).text(day.day);
        $(`#${index} .code`).text(weather_code(day.icon)).attr("class", "w" + day.icon);
        $(`#${index} .temp`).text(`${day.tempMin}° / ${day.tempMax}°`);
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
    } else {
        $("#container").css("background", "#" + localStorage.typhoon_color)
    }
}

// Converts OpenWeatherMap weather codes to Climacons icons
function weather_code(iconCode) {
    const climaconMap = {
        "01d": "v", // Clear sky (day)
        "01n": "C", // Clear sky (night)
        "02d": "1", // Few clouds (day)
        "02n": "2", // Few clouds (night)
        "03d": "`", // Scattered clouds
        "03n": "`", // Scattered clouds
        "04d": "a", // Broken clouds
        "04n": "a", // Broken clouds
        "09d": "r", // Shower rain
        "09n": "r", // Shower rain
        "10d": "q", // Rain (day)
        "10n": "q", // Rain (night)
        "11d": "z", // Thunderstorm
        "11n": "z", // Thunderstorm
        "13d": "w", // Snow
        "13n": "w", // Snow
        "50d": "m", // Mist
        "50n": "m"  // Mist
    };

    // Return the corresponding Climacon icon or a default icon
    return climaconMap[iconCode] || "a"; // Default to a cloud icon if no match is found
}

$(document).ready(function() {
    //Filters Proprietary RSS Tags
    jQuery.fn.filterNode = function(name){
        return this.filter(function(){
            return this.nodeName === name;
        });
    };

    //APP START.
    init_settings()
    if (!localStorage.typhoon) {
        show_settings("location")
    } else {
        //Has been run before
        render(localStorage.typhoon)

        setInterval(function() {
            console.log("Updating Data...")
            $(".border .sync").click()
        }, 600000)
    }

    // Add event listener for the reset button
    $('#resetButton').click(function () {
        // if (confirm("Are you sure you want to reset all settings? This will clear all saved preferences.")) {
            localStorage.clear(); // Clear all local storage
            location.reload(); // Reload the page to apply default settings
        // }
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
            render(localStorage.typhoon);
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
            }, 600000);
        }
    });

    // Sets up localstorage
    localStorage.typhoon_measurement = localStorage.typhoon_measurement || "c";
    localStorage.typhoon_speed = localStorage.typhoon_speed || "kph";
    localStorage.typhoon_color = localStorage.typhoon_color || "gradient";
    localStorage.typhoon_launcher = localStorage.typhoon_launcher || "checked";

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
    

    if (localStorage.typhoon_launcher == "checked") {
        $('#locationModal .launcher input').attr("checked", "checked")
        document.title = "enable_launcher"
    }
    $('#locationModal .launcher input').click(function() {
        localStorage.typhoon_launcher = $('#locationModal .launcher input').attr("checked")
        if (localStorage.typhoon_launcher == "checked") {
            document.title = "enable_launcher"
        } else {
            document.title = "disable_launcher"
        }
    })

    //Control CSS.
    $("span[data-color]:not([data-color=gradient])").map(function() { $(this).css('background', '#' + $(this).attr("data-color")) })

    /* Error Message Retry Button */
    $('#errorMessage .btn').click(function() {
        render(localStorage.typhoon)
    })

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
    const errorText = message === 'network' ? 
        'Could not connect to the internet. Please try again.' : 
        message || 'An unknown error occurred.';
    
    // Show the error message and retry button
    $('#errorMessage').html(`
        <div>
            ${errorText}<br>
            <button class="btn" id="retryButton">TRY AGAIN</button>
        </div>
    `).fadeIn(350);

    // Show the API key input and button
    $('#apiKeyContainer').show();

    // Hide the actual weather display
    $('#actualWeather').fadeOut(350);

    // Attach event listener to the retry button
    $('#retryButton').click(function () {
        $('#errorMessage').fadeOut(350); // Hide the error message
        render(localStorage.typhoon); // Retry fetching the weather data
    });
}
function updateTitle(val) {
    document.title = "o" + val
    localStorage.app_opacity = val
}
function opacity() {
    //On first run, opacity would be 0.8
    if (localStorage.getItem("app_opacity") === null) {
        localStorage.app_opacity = 0.8
    }
    $('input[type=range]').val(localStorage.app_opacity)
    document.title = "o" + localStorage.app_opacity
    document.title = enable_drag
}