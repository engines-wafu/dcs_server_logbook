-- src/squadrons.lua

local utils = require("src.utils")

--print(type(utils.getPilotInfoByID))

local squadronsModule = {}

function squadronsModule.parseStatsForPilotHTML(stats, pilotList, pilotID, includeTableTags, sqnType)

    local pilotInfo = utils.getPilotInfoByID(pilotsList, pilotID)
    local pilotID = pilotID
    local PILOT_URL = "usr/" .. utils.truncatePilotID(pilotID) .. ".html"
    local HTML_OUTPUT_PATH = "html/" .. PILOT_URL

    pilots.generatePilotHTML(stats, pilotsList, pilotID, HTML_OUTPUT_PATH, THRESHOLD_SECONDS)

    if not pilotInfo then
        return "<tr><td>" .. pilotID .. "</td><td colspan='3'>Pilot not found in the list</td></tr>\n"
    end

    local pilotLog = stats[pilotID]
    if not pilotLog then
        return "<tr><td>" .. pilotInfo.rank .. " " .. pilotInfo.name .. "</td><td colspan='4'>No logbook information found for " .. pilotInfo.name .. "</td></tr>\n"
    end

    local totalSeconds = 0
    local primarySeconds = 0
    local lastJoinEpoch = 0
    local noKills = 0

    for logKey, logValue in pairs(pilotLog) do
        if logKey == "times" then
            for aircraftType, timeValue in pairs(logValue) do
                -- Summing up total time
                totalSeconds = totalSeconds + (timeValue["total"] or 0)

                -- Summing up kills across all types
                if timeValue["kills"] then
                    for killType, killDetails in pairs(timeValue["kills"]) do
                        if type(killDetails) == "table" then
                            for killCategory, killCount in pairs(killDetails) do
                                if type(killCount) == "number" then
                                    noKills = noKills + killCount
                                end
                            end
                        elseif type(killDetails) == "number" then
                            noKills = noKills + killDetails
                        end
                    end
                end
                if sqnType then
                    -- Here we are trying to find any time logged specifically to the squadron aircraft type.
                    -- If success, then primarySeconds are added.
                    local prefix = (sqnType)
                    --print("P: " .. pilotInfo.name .. "... Looking for type starting with: " .. prefix .. ". Logged type is: " .. aircraftType)
                    if utils.starts_with(aircraftType, prefix) then
                        for key, val in pairs(timeValue) do
                            if key == "total" and val >= 600 then
                                primarySeconds = primarySeconds + val
                            end
                        end
                        --print("MATCH!  Primary time: " .. utils.secToHours(primarySeconds))
                    else
                        --print("No good match")
                    end
                end
            end
        elseif logKey == "lastJoin" then
            lastJoinEpoch = logValue
        end
    end

    local hours = utils.secToHours(totalSeconds)
    local primary_hours = utils.secToHours(primarySeconds)
    local currency = utils.daysElapsedSince(lastJoinEpoch)
    local backgroundColor = ""

    -- Determine background color based on currency value
    if currency > 90 then
        backgroundColor = "gray"
    elseif currency > 30 then
        backgroundColor = "red"
    elseif currency > 14 then
        backgroundColor = "orange"  -- Amber color needs to be defined in your CSS or use "orange"
    end

    -- Combine all columns into the table row
    local tableRow = "<tr><td><a href='" .. PILOT_URL .. "'>" .. pilotInfo.rank .. " " .. pilotInfo.name .. "</a></td><td>" .. primary_hours .. "</td><td>" .. hours .. "</td><td>" .. noKills .. "</td><td style='background-color:" .. backgroundColor .. "'>" .. currency .. " days</td></tr>\n"

    if includeTableTags then
        return tableRow
    else
        return "<ul>\n" .. tableRow .. "</ul>\n"
    end
end

function squadronsModule.outputSquadronDataHTML(stats)
    local htmlContent = ""

    for _, squadron in ipairs(squadronsList) do

        htmlContent = htmlContent .. "<h2>Squadron: " .. squadron.name .. "</h2>\n"
        htmlContent = htmlContent .. "<p>Motto: " .. squadron.motto .. "</p>\n"
        if squadron.pseudoType then
            htmlContent = htmlContent .. "<p>Aircraft Type: " .. squadron.pseudoType .. "</p>\n"
        end
        htmlContent = htmlContent .. "<h3>Commanding Officer:</h3>\n"

        -- Get and display commanding officer information
        local coInfo = utils.getPilotInfoByID(pilotsList, squadron.co)
        if coInfo then
            htmlContent = htmlContent .. "<p>&nbsp;&nbsp;" .. coInfo.rank .. " " .. coInfo.name .. " " .. coInfo.service .. " [" .. utils.truncatePilotID(coInfo.id) .. "]</p>\n"
        else
            htmlContent = htmlContent .. "<p>&nbsp;&nbsp;None</p>\n"
        end

        htmlContent = htmlContent .. "<h3>Pilots:</h3>\n"
        htmlContent = htmlContent .. "<table style=border='1'>\n"
        htmlContent = htmlContent .. "<tr><th style='width:30%'>Name</th><th style='width:10%'>Type hours</th><th style='width:10%'>Total hours</th><th style='width:10%'>Kills</th><th style='width:10%'>Currency</th></tr>\n"

        for _, pilotID in ipairs(squadron.pilots) do
            local pilotInfo = utils.getPilotInfoByID(pilotsList, pilotID)
            if pilotInfo then
                htmlContent = htmlContent .. squadronsModule.parseStatsForPilotHTML(stats, utils.grabPilotNames(stats), pilotInfo.id, true, squadron.type)
            end
        end

        htmlContent = htmlContent .. "</table>\n"
        htmlContent = htmlContent .. "<hr>\n"
    end

    return htmlContent
end

-- Function to generate HTML content
function generateHTMLContent(stats, pilotList, pilotID)
    local htmlContent = "<h1>Joint Strike Wing Squadron Dashboard</h1>\n"
    --htmlContent = htmlContent .. "<h2>Server log: " .. STATS_FILE_PATH .. "</h2>\n"


    -- Add squadron data
    htmlContent = htmlContent .. outputSquadronDataHTML(stats)

    return htmlContent
end

-- Function to generate HTML file
function generateHTMLFile(stats, pilotList, pilotID, outputFilePath)
    local htmlContent = generateHTMLContent(stats, pilotList, pilotID)

    -- Open the HTML file for writing
    local file = io.open(outputFilePath, "w")

    -- Check if the file was opened successfully
    if not file then
        print("Error opening file for writing: " .. outputFilePath)
        return
    end

    -- Write HTML content to the file
    file:write("<html>\n<head>\n<title>Pilot Logbook</title>\n<meta name='viewport' content='width=device-width, initial-scale=1'>\n<link rel='stylesheet' type='text/css' href='styles.css'>\n</head>\n<body>\n")
    local navbarHtml = utils.readHtmlSnippet("html/navbar.html")
    if navbarHtml then
        file:write(navbarHtml)
    end
    file:write("<div class='container'>")
    file:write(htmlContent)
    file:write("</div>")
    file:write("\n</body>\n</html>")

    -- Close the file
    file:close()

    --print("HTML file created successfully: " .. outputFilePath .. "\n")
end

return squadronsModule