-- src/utils.lua

local utils = {}

-- Turning seconds into hours

function utils.secToHours(sec)
    local hours = sec / 3600
    local roundedHours = math.floor(hours * 10 + 0.5) / 10  -- Round to one-tenth of an hour
    return roundedHours
end

-- Turn epoch date to a human-readable format

function utils.epochToDateString(epochTime)
    local formattedDate = os.date("%Y%m%d", epochTime)
    --local formattedDate = os.date("%Y-%m-%d %H:%M:%S", epochTime)
    return formattedDate
end

-- Days since a given epoch

function utils.daysElapsedSince(epochTime)
    local currentTime = os.time()
    local secondsElapsed = currentTime - epochTime
    local daysElapsed = secondsElapsed / (24 * 3600)  -- Convert seconds to days
    local roundedDays = math.floor(daysElapsed + 0.5)  -- Round to the nearest day
    return roundedDays
end

-- Truncate the pilotIDs into something more manageable

function utils.truncatePilotID(pilotID)
    return pilotID:sub(1, 4)
end

-- Check a string starts with another string

function utils.starts_with(str, start)
   return str:sub(1, #start) == start
end

-- Get the pilot names from stats
function utils.grabPilotNames(stats)
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

-- Function to get pilot information by ID

function utils.getPilotInfoByID(pilotList, pilotID)
    for _, pilot in ipairs(pilotList) do
        if pilot.id == pilotID then
            return pilot
        end
    end
    return nil  -- Pilot not found
end

-- Function to read HTML snippet from a file
function utils.readHtmlSnippet(filename)
    local file = io.open(filename, "r")  -- Open the file for reading
    if not file then return nil end       -- If the file doesn't exist, return nil
    local content = file:read("*a")      -- Read the entire contents of the file
    file:close()                         -- Close the file
    return content                       -- Return the contents
end

return utils