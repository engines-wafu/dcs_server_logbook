--------------------------------------------------
-- PILOT MANAGEMENT SYSTEM
--------------------------------------------------

local PILOTS_FILE_PATH = "data/pilots.lua"
local SQUADRONS_FILE_PATH = "data/squadrons.lua"
local HTML_OUTPUT_PATH = "html/index.html"
local STATS_FILE_PATH = "data/SlmodStats.lua"

print("\n--------------------------------------------------")
print(" Starting the pilot management system")
print(" Created by Engines, 2023")
print("--------------------------------------------------\n")

local success, slmodStatsContents = pcall(loadfile, STATS_FILE_PATH)

if not success then
    print("Error loading SlmodStats file: " .. slmodStatsContents)
    return
end

slmodStatsContents()  -- Execute the loaded file

--------------------------------------------------
-- General functions
--------------------------------------------------

-- Some general functions, starting with turning seconds into hours

function secToHours(sec)
    local hours = sec / 3600
    local roundedHours = math.floor(hours * 10 + 0.5) / 10  -- Round to one-tenth of an hour
    return roundedHours
end

-- Turn epoch date to a human-readable format

function epochToDateString(epochTime)
    local formattedDate = os.date("%Y%m%d", epochTime)
    --local formattedDate = os.date("%Y-%m-%d %H:%M:%S", epochTime)
    return formattedDate
end

-- Days since a given epoch

function daysElapsedSince(epochTime)
    local currentTime = os.time()
    local secondsElapsed = currentTime - epochTime
    local daysElapsed = secondsElapsed / (24 * 3600)  -- Convert seconds to days
    local roundedDays = math.floor(daysElapsed + 0.5)  -- Round to the nearest day
    return roundedDays
end

-- Truncate the pilotIDs into something more manageable

function truncatePilotID(pilotID)
    return pilotID:sub(1, 4)
end

-- Get the pilot names from stats

function grabPilotNames(stats)
    local pilots = {}
    for pilotID, pilotLog in pairs(stats) do
        for logKey, logValue in pairs(pilotLog) do
            if logKey == "names" then
                local pilotName = logValue[#logValue]  -- Corrected: declare pilotName as local
                pilots[pilotID] = pilotName
            end
        end
    end
    return pilots
end

--------------------------------------------------
-- Pilot objects
--------------------------------------------------

-- Define the pilot object
local Pilot = {
    pilotID = "",
    name = "",
    rank = "",
    service = "",
    hours = 0
}

-- Constructor function for creating a new pilot object
function Pilot.new(pilotID, name, rank, service, time, last_flight, kills)
    local self = setmetatable({}, { __index = Pilot })
    self.pilotID = pilotID or ""
    self.name = name or ""
    self.rank = rank or ""
    self.service = service or ""
    self.time = time or 0
    self.last_flight = last_flight or 0
    self.kills = kills or 0
    return self
end

-- Method to promote the pilot to a new rank
function Pilot:promote(new_rank)
    print("Promoting " .. self.name .. " to " .. new_rank)
    self.rank = new_rank
end

-- Method to set the pilot's total hours
function Pilot:loghours(new_seconds)
    print("Updating logbook total for " .. self.name .. " to " .. secToHours(new_seconds))
    self.time = new_seconds
end

-- Method to set the pilot's last flight
function Pilot:lastflight(last_flight)
    print("Updating last flight for " .. self.name .. " to " .. last_flight)
    self.last_flight = last_flight
end

--------------------------------------------------
-- Aircraft objects
--------------------------------------------------

-- Define the Aircraft object
local Aircraft = {
    tailNumber = "",
    type = "",
    status = ""
}

-- Constructor function for creating a new Aircraft object
function Aircraft.new(tailNumber, type, status)
    local self = setmetatable({}, { __index = Aircraft })
    self.tailNumber = tailNumber or ""
    self.type = type or ""
    self.status = status or "Unserviceable"
    return self
end

--------------------------------------------------
-- Squadron objects
--------------------------------------------------

-- Define the Squadron object
local Squadron = {
    name = "",
    motto = "",
    aircraft = {},
    co = nil,  -- Commanding Officer (initially nil)
    pilots = {}
}

-- Constructor function for creating a new Squadron object
function Squadron.new(name, motto)
    local self = setmetatable({}, { __index = Squadron })
    self.name = name or ""
    self.motto = motto or ""
    self.aircraft = {}
    self.co = nil
    self.pilots = {}
    return self
end

-- Method to draft a pilot to the squadron
function Squadron:draft(pilot)
    if not pilot then
        print("Error: Cannot draft a nil pilot.")
        return
    end

    print("Drafting " .. pilot.name .. " to " .. self.name)
    
    -- Assign the drafted pilot as the Commanding Officer if none is assigned
    if not self.co then
        print(pilot.name .. " is now the Commanding Officer.")
        self.co = pilot
    end

    -- Add the drafted pilot to the list of pilots in the squadron
    table.insert(self.pilots, pilot)
end

--------------------------------------------------
-- Read static information from files
--------------------------------------------------

-- Load the pilots file
local pilotsFileContents, pilotsErrorMessage = loadfile(PILOTS_FILE_PATH)

-- Check if the file was loaded successfully
if not pilotsFileContents then
    print("Error loading pilots file: " .. pilotsErrorMessage)
    return
end

-- Execute the loaded file to get the pilots table
local pilotsList = pilotsFileContents()

-- Load the squadrons file
local squadronsFileContents, squadronsErrorMessage = loadfile(SQUADRONS_FILE_PATH)

-- Check if the file was loaded successfully
if not squadronsFileContents then
    print("Error loading squadrons file: " .. squadronsErrorMessage)
    return
end

-- Execute the loaded file to get the squadrons table
local squadronsList = squadronsFileContents()

-- Function to get pilot information by ID
function getPilotInfoByID(pilotID)
    for _, pilot in ipairs(pilotsList) do
        if pilot.id == pilotID then
            return pilot
        end
    end
    return nil  -- Pilot not found
end

function parseStatsForPilot(stats, pilotList, pilotID)
    local pilotName = pilotList[pilotID]
    if not pilotName then
        print("Pilot with ID " .. pilotID .. " not found in the pilot list.")
        return
    end

    local pilotLog = stats[pilotID]
    if not pilotLog then
        print("No logbook information found for pilot " .. pilotName)
        return
    end

    local totalSeconds = 0
    local lastJoinEpoch = 0
    local noKills = 0

    for logKey, logValue in pairs(pilotLog) do
        if logKey == "times" then
            for aircraftType, timeValue in pairs(logValue) do
                for key, val in pairs(timeValue) do
                    if key == "total" and val >= 600 then
                        totalSeconds = totalSeconds + val
                        --print("    " .. aircraftType .. ": " .. secToHours(seconds))
                    end
                    if key == "weapons" then -- val will be each aircraft type
                        for weaponType, weaponStat in pairs(val) do
                            --print("Type: " .. weaponType)
                            if type(weaponStat) == "table" then
                                for killType, killCount in pairs(weaponStat) do
                                    --print (killType .. ": " .. killCount)
                                    if killType == "kills" then
                                        noKills = noKills + killCount
                                    end
                                end
                            end
                        end
                    end
                end
            end
        elseif logKey == "lastJoin" then
            lastJoinEpoch = logValue
        end
    end
    print("    Total time: " .. secToHours(totalSeconds) .. ". Kills: " .. noKills .. ". Currency: " .. daysElapsedSince(lastJoinEpoch) .. " days")
end

function getListOfPilots(stats, outputFile)
    local pilots = grabPilotNames(stats)

    -- Open the CSV file for writing
    local file = io.open(outputFile, "w")

    -- Check if the file was opened successfully
    if not file then
        print("Error opening file for writing: " .. outputFile)
        return
    end

    -- Write the header to the CSV file
    file:write("PilotID, PilotName\n")

    -- Write each pilot to the CSV file
    for id, pilot in pairs(pilots) do
        -- Check if the pilot name starts with "=" and omit it
        if pilot:sub(1, 1) == "=" then
            pilot = pilot:sub(2)  -- Remove the "="
        end

        file:write(id .. "," .. pilot .. "\n")
    end

    -- Close the file
    file:close()

    print("CSV file created successfully: " .. outputFile)
end

function printPilotInfo(stats, pilotList, pilotID)
    local pilotName = pilotList[pilotID]
    if not pilotName then
        print("Pilot with ID " .. pilotID .. " not found in the pilot list.")
        return
    end

    local pilotLog = stats[pilotID]
    if not pilotLog then
        print("No logbook information found for pilot " .. pilotName)
        return
    end

    print("Logbook information for pilot " .. pilotName)
    print("--------------------------------------------------")

    for logKey, logValue in pairs(pilotLog) do
        --print(logKey)
        if logKey == "times" then
            print("Total Flight Times:")
            for aircraftType, timeValue in pairs(logValue) do
                for state, seconds in pairs(timeValue) do
                    print(state)
                    if state == "total" then
                        print("  " .. aircraftType .. ": " .. secToHours(seconds))
                    end
                end
            end
        elseif logKey == "lastJoin" then
            print("Last Joined: " .. epochToDateString(logValue))
        end
    end

    print("--------------------------------------------------")
end

-- Display information about each squadron

function outputSquadronData()
    for _, squadron in ipairs(squadronsList) do
        print("Squadron Name: " .. squadron.name)
        print("Motto: " .. squadron.motto)
        print("Commanding Officer:")

        -- Get and display commanding officer information
        local coInfo = getPilotInfoByID(squadron.co)
        if coInfo then
            print("  " .. coInfo.rank .. " " .. coInfo.name .. " " .. coInfo.service .. " [" .. truncatePilotID(coInfo.id) .. "]")
        else
            print("- None")
        end

        print("Pilots:")
        for _, pilotID in ipairs(squadron.pilots) do
            local pilotInfo = getPilotInfoByID(pilotID)
            if pilotInfo then
                print("  " .. pilotInfo.rank .. " " .. pilotInfo.name .. " " .. pilotInfo.service .. " [" .. truncatePilotID(pilotInfo.id) .. "]")
                parseStatsForPilot(stats, grabPilotNames(stats), pilotInfo.id)
            else
                print("  Pilot ID: " .. pilotID .. " (Pilot not found)")
            end        
        end
        print("--------------------------------------------------\n")
    end
end

--------------------------------------------------
-- HTML Output Functions
--------------------------------------------------

function parseStatsForPilotHTML(stats, pilotList, pilotID, includeTableTags)
    local pilotInfo = getPilotInfoByID(pilotID)
    if not pilotInfo then
        return "<tr><td>" .. pilotID .. "</td><td colspan='3'>Pilot not found in the list</td></tr>\n"
    end

    local pilotLog = stats[pilotID]
    if not pilotLog then
        return "<tr><td>" .. pilotID .. "</td><td colspan='3'>No logbook information found for " .. pilotInfo.name .. "</td></tr>\n"
    end

    local totalSeconds = 0
    local lastJoinEpoch = 0
    local noKills = 0

    for logKey, logValue in pairs(pilotLog) do
        if logKey == "times" then
            for aircraftType, timeValue in pairs(logValue) do
                for key, val in pairs(timeValue) do
                    if key == "total" and val >= 600 then
                        totalSeconds = totalSeconds + val
                    end
                    if key == "weapons" then -- val will be each aircraft type
                        for weaponType, weaponStat in pairs(val) do
                            --print("Type: " .. weaponType)
                            if type(weaponStat) == "table" then
                                for killType, killCount in pairs(weaponStat) do
                                    --print (killType .. ": " .. killCount)
                                    if killType == "kills" then
                                        noKills = noKills + killCount
                                    end
                                end
                            end
                        end
                    end
                end
            end
        elseif logKey == "lastJoin" then
            lastJoinEpoch = logValue
        end
    end

    local hours = secToHours(totalSeconds)
    local currency = daysElapsedSince(lastJoinEpoch)
    local backgroundColor = ""

    -- Determine background color based on currency value
    if currency > 30 then
        backgroundColor = "red"
    elseif currency > 14 then
        backgroundColor = "orange"  -- Amber color needs to be defined in your CSS or use "orange"
    end

    -- Return a table row with columns for pilot name, hours, kills, and currency
    local tableRow = "<tr><td>" .. pilotInfo.rank .. " " .. pilotInfo.name .. "</td><td>" .. hours .. "</td><td>" .. noKills .. "</td><td style='background-color:" .. backgroundColor .. "'>" .. currency .. " days</td></tr>\n"

    if includeTableTags then
        return tableRow
    else
        return "<ul>\n" .. tableRow .. "</ul>\n"
    end
end

function outputSquadronDataHTML(stats)
    local htmlContent = ""

    for _, squadron in ipairs(squadronsList) do
        htmlContent = htmlContent .. "<h2>Squadron: " .. squadron.name .. "</h2>\n"
        htmlContent = htmlContent .. "<p>Motto: " .. squadron.motto .. "</p>\n"
        htmlContent = htmlContent .. "<h3>Commanding Officer:</h3>\n"

        -- Get and display commanding officer information
        local coInfo = getPilotInfoByID(squadron.co)
        if coInfo then
            htmlContent = htmlContent .. "<p>&nbsp;&nbsp;" .. coInfo.rank .. " " .. coInfo.name .. " " .. coInfo.service .. " [" .. truncatePilotID(coInfo.id) .. "]</p>\n"
        else
            htmlContent = htmlContent .. "<p>&nbsp;&nbsp;None</p>\n"
        end

        htmlContent = htmlContent .. "<h3>Pilots:</h3>\n"
        htmlContent = htmlContent .. "<table style='width:60%' border='1'>\n"
        htmlContent = htmlContent .. "<tr><th>Name</th><th>Hours</th><th>Kills</th><th>Currency</th></tr>\n"

        for _, pilotID in ipairs(squadron.pilots) do
            local pilotInfo = getPilotInfoByID(pilotID)
            if pilotInfo then
                htmlContent = htmlContent .. parseStatsForPilotHTML(stats, grabPilotNames(stats), pilotInfo.id, true)
            end
        end

        htmlContent = htmlContent .. "</table>\n"
        htmlContent = htmlContent .. "<hr>\n"
    end

    return htmlContent
end

-- Function to generate HTML content
function generateHTMLContent(stats, pilotList, pilotID)
    local pilotName = "TEST PILOT"
    local htmlContent = "<h1>Logbook information for JSW Pilots</h1>\n"

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
    file:write("<html>\n<head>\n<title>Pilot Logbook</title>\n</head>\n<body>\n")
    file:write(htmlContent)
    file:write("\n</body>\n</html>")

    -- Close the file
    file:close()

    print("HTML file created successfully: " .. outputFilePath)
end

-- Example usage:
--local stats = { -- your stats data here }
--local pilotList = { -- your pilot list data here }
local pilotID = "ea2dca05dc204673da916448f77f00f1" -- replace with the desired pilot ID
generateHTMLFile(stats, pilotsList, pilotID, HTML_OUTPUT_PATH)


-- Example usage:
--getListOfPilots(stats, "data/pilots_list.csv")
--parseStatsToLogbook(stats, pilotsList)
--parseStatsForPilot(stats, grabPilotNames(stats), "ea2dca05dc204673da916448f77f00f1")
--printPilotInfo(stats, grabPilotNames(stats), "1a1cba06dd0066c82910007ab36a3c1f")