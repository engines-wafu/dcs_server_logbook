local utils = require("src.utils")

local mayfly = {}

function mayfly.generateMayflyHtml(squadronsData, MAYFLY_OUTPUT_PATH)
    local function randomMaintenanceHours()
        return math.random(3, 18)  -- Generates a random number between 3 and 18
    end

    local htmlContent = "<html>\n<head>\n<title>Mayfly</title>\n<meta name='viewport' content='width=device-width, initial-scale=1'>\n<link rel='stylesheet' type='text/css' href='styles.css'>\n</head>\n<body>\n"
    local navbarHtml = utils.readHtmlSnippet("html/navbar.html")
    if navbarHtml then
        htmlContent = htmlContent .. navbarHtml
    end
    htmlContent = htmlContent .. "<table>\n<tr><th>Tail Number</th><th>Type</th><th>Squadron</th><th>Status</th><th>Maintenance</th><th>Remarks</th></tr>\n"

    for _, squadron in ipairs(squadronsData) do
        local squadronName = squadron.name or "Unknown"  -- Default to "Unknown" if the name is not provided
        for _, aircraft in ipairs(squadron.aircraft) do
            local maintenanceHours = randomMaintenanceHours()
            local statusColor = "orange"  -- Default color
            if aircraft.status == "Serviceable" then
                statusColor = "green"
            elseif aircraft.status == "Unserviceable" then
                statusColor = "red"
            end

            htmlContent = htmlContent .. string.format("<tr><td>%s</td><td>%s</td><td>%s</td><td style='background-color:%s;'>%s</td><td>%d hrs</td><td>%s</td></tr>\n",
                aircraft.tailNumber, aircraft.type, squadronName, statusColor, aircraft.status, maintenanceHours, aircraft.remarks or "")
        end
    end

    htmlContent = htmlContent .. "</table>\n</body>\n</html>"

    -- Writing the HTML content to mayfly.html
    local file = io.open(MAYFLY_OUTPUT_PATH, "w")
    if file then
        file:write(htmlContent)
        file:close()
    else
        print("Error: Unable to open file for writing at path:", MAYFLY_OUTPUT_PATH)
    end

    return htmlContent
end

return mayfly
