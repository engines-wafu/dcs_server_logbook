-- merge.lua

-- Function to merge stats from multiple servers
function mergeStats(statsFilePathList)
    local mergedStats = {}

    for _, filePath in ipairs(statsFilePathList) do
        local fileContents, errorMessage = loadfile(filePath)

        if fileContents then
            local success, stats = pcall(loadfile, fileContents)

            if success and type(stats) == "table" then
                for pilotID, pilotLog in pairs(stats) do
                    if not mergedStats[pilotID] then
                        -- If pilotID is not in mergedStats, add the entry
                        mergedStats[pilotID] = pilotLog
                    else
                        -- PilotID already exists, sum hours and kills, select the smallest currency
                        mergedStats[pilotID].times.total = (mergedStats[pilotID].times.total or 0) + (pilotLog.times.total or 0)
                        mergedStats[pilotID].weapons.kills = (mergedStats[pilotID].weapons.kills or 0) + (pilotLog.weapons.kills or 0)
                        mergedStats[pilotID].lastJoin = math.min(mergedStats[pilotID].lastJoin, pilotLog.lastJoin)
                    end
                end
            else
                print("Error parsing stats from file: " .. filePath)
            end
        else
            print("Error loading stats file: " .. errorMessage)
        end
    end

    return mergedStats
end

-- Example usage
local statsFilePathList = {
    "data/SlmodStats_server1.lua",
    "data/SlmodStats_server2.lua"
}

local mergedStats = mergeStats(statsFilePathList)

-- You can now use the mergedStats table as needed.
