--------------------------------------------------
-- PILOT MANAGEMENT SYSTEM
--------------------------------------------------

print("\n--------------------------------------------------")
print(" Starting the pilot management system")
print(" Created by Engines, 2023")
print("--------------------------------------------------\n")

-- Open the file
file = "data/SlmodStatsSimple.lua"
assert(loadfile(file))()

--------------------------------------------------
-- General functions
--------------------------------------------------

-- Some general functions, starting with turn seconds into hours

function secToHours(sec)
    hours = sec / 3600
    local roundedHours = math.floor(hours * 10 + 0.5) / 10  -- Round to one-tenth of an hour
    return roundedHours
end

-- Turn epoch date to human readable format

function epochToDateString(epochTime)
    local formattedDate = os.date("%Y-%m-%d %H:%M:%S", epochTime)
    return formattedDate
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
function Pilot.new(pilotID, name, rank, service, time, last_flight)
    local self = setmetatable({}, { __index = Pilot })
    self.pilotID = pilotID or ""
    self.name = name or ""
    self.rank = rank or ""
    self.service = service or ""
    self.time = time or 0
    self.last_flight = last_flight or 0
    return self
end

-- Method to promote the pilot to a new rank
function Pilot:promote(new_rank)
    print("Promoting " .. self.name .. " to " .. new_rank)
    self.rank = new_rank
end

-- Method to set pilot's total hours
function Pilot:loghours(new_seconds)
    print("Updating logbook total for " .. self.name .. " to " .. secToHours(new_seconds))
    self.time = new_seconds
end

-- Method to set pilot's last flight
function Pilot:lastflight(last_flight)
    print("Updating last flight for " .. self.name .. " to " .. last_flight)
    self.last_flight = last_flight
end

-- We also need a squadron.  A squadron has a name, motto, aircraft, CO, and pilots

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

-- Specify the path to the pilots file
local pilotsFilePath = "data/pilots.lua"

-- Load the pilots file
local pilotsFileContents, pilotsErrorMessage = loadfile(pilotsFilePath)

-- Check if the file was loaded successfully
if not pilotsFileContents then
    print("Error loading pilots file: " .. pilotsErrorMessage)
    return
end

-- Execute the loaded file to get the pilots table
local pilotsList = pilotsFileContents()

-- Specify the path to the squadrons file
local squadronsFilePath = "data/squadrons.lua"

-- Load the squadrons file
local squadronsFileContents, squadronsErrorMessage = loadfile(squadronsFilePath)

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

-- Display information about each squadron
for _, squadron in ipairs(squadronsList) do
    print("Squadron Name: " .. squadron.name)
    print("Motto: " .. squadron.motto)
    print("Commanding Officer:")
    
    -- Get and display commanding officer information
    local coInfo = getPilotInfoByID(squadron.co)
    if coInfo then
        print("- Pilot ID: " .. coInfo.id .. ", Name: " .. coInfo.name .. ", Rank: " .. coInfo.rank .. ", Service: " .. coInfo.service)
    else
        print("- None")
    end

    print("Pilots in Squadron:")
    for _, pilotID in ipairs(squadron.pilots) do
        local pilotInfo = getPilotInfoByID(pilotID)
        if pilotInfo then
            print("- Pilot ID: " .. pilotInfo.id .. ", Name: " .. pilotInfo.name .. ", Rank: " .. pilotInfo.rank .. ", Service: " .. pilotInfo.service)
        else
            print("- Pilot ID: " .. pilotID .. " (Pilot not found)")
        end
    end

    print("----------------------")
end

--------------------------------------------------
-- Test cases
--------------------------------------------------

-- Display information about each pilot
-- for _, pilot in ipairs(pilotsList) do
--     print("Pilot ID: " .. pilot.id)
--     print("Name: " .. pilot.name)
--     print("Rank: " .. pilot.rank)
--     print("----------------------")
-- end

-- Example usage creating a Squadron:
-- local s_800NAS = Squadron.new("800 NAS", "Nunquam non-paratus")

-- Example usage creating a Pilot:
-- local p_Engines = Pilot.new("ea2dca05dc204673da916448f77f00f1", "Gavin Edwards", "Lt Cdr", "RN")

-- Example usage drafting a Pilot to the Squadron:
-- s_800NAS:draft(p_Engines)

-- Display the Squadron information
-- print("Squadron Name: " .. s_800NAS.name)
-- print("Motto: " .. s_800NAS.motto)
-- print("Commanding Officer: " .. (s_800NAS.co and s_800NAS.co.name or "None"))
-- print("Pilots in Squadron:")
-- for _, pilot in ipairs(s_800NAS.pilots) do
--     print("- " .. pilot.name)
-- end

-- Go through the file and grab the pilotIDs to associate with names.
-- Todo: create a table of only JSW IDs to cross reference

function grabPilotNames(stats)
    local pilots = {}
    for pilotID, pilotLog in pairs(stats) do
        for logKey, logValue in pairs(pilotLog) do
            if logKey == "names" then
                pilotName = logValue[#logValue]
                pilots[pilotID] = pilotName
            end
        end
    end
    return pilots
end

function parseStatsToLogbook(stats)
    for pilotID, pilotLog in pairs(stats) do
        local totalSeconds = 0
        local lastJoinEpoch = 0

        local pilotName = grabPilotNames(stats)[pilotID]
        print("Logbook information for pilot " .. pilotName)
        print("--------------------------------------------------")
        print("  PilotID: " .. pilotID)

        for logKey, logValue in pairs(pilotLog) do
            -- print(logKey) -- use this line to check what values are available.
            if logKey == "times" then
                for aircraftType, timeValue in pairs(logValue) do
                    for state, seconds in pairs(timeValue) do
                        -- print(state)
                        if state == "total" and seconds >= 600 then
                            totalSeconds = totalSeconds + seconds
                            print("    " .. aircraftType .. ": " .. secToHours(seconds))
                        end
                    end
                end
            elseif logKey == "lastJoin" then
                lastJoinEpoch = logValue
            end
        end

        print("  Total time: " .. secToHours(totalSeconds))
        print("  Last joined: " .. epochToDateString(lastJoinEpoch))
        print("")
    end
end



parseStatsToLogbook(stats)