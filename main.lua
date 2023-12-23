-- Debug output
print("--------------------------")
print(" Starting logbook parser")
print(" Created by Engines, 2023")
print("--------------------------")
print("")

-- Open the file
file = "data/SlmodStats.lua"
assert(loadfile(file))()

-- [[
    I want to start by creating some objects.  The first will be a object called pilot which will contain some basic information like
    - pilotID,
    - name,
    - service,
    - rank,
    - primary squadron,
    - secondary squadron,
    - last flight, and
    - total hours.
]]



-- [[
    Next I want to have an object called logbook.  This will be unique to a pilot.  It will contain the following information:
    - pilotID,
    - name,
    - typeTotal as an array of tuples:
        - type
        - total
    - endorsements as another array:
        - description
        - name
        - date
]]

-- Turn seconds into hours

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

-- Go through the file and grab the pilotIDs to associate with names.
-- Todo: create a table of only JSW IDs to cross reference

function grabPilotNames(stats)
    pilots = {} -- create and empty array of pilot names
    for pilotID, pilotLog in pairs(stats) do
        for logKey, logValue in pairs(pilotLog) do
            if logKey == "names" then
                pilotName = logValue[#logValue] -- takes the latest name used by that ID
                pilots[pilotID] = pilotName
            end
        end
    end
    return pilots
end

function parseStatsToLogbook(stats)
    for pilotID, pilotLog in pairs(stats) do
        totalSeconds = 0
        lastJoinEpoch = 0

        pilotName = grabPilotNames(stats)[pilotID]
        print("Logbook information for pilot " .. pilotName)
        print("--------------------------------------------")

        for logKey, logValue in pairs(pilotLog) do
            --print(logKey)

            if logKey == "times" then
                for timeKey, timeValue in pairs(logValue) do
                    aircraftType = timeKey
                    for typeKey, typeSeconds in pairs(timeValue) do
                        if typeKey == "inAir" then
                            if typeSeconds == 0 then
                            else
                                totalSeconds = totalSeconds + typeSeconds
                                --print("    " .. aircraftType .. ": " .. typeSeconds)
                            end
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