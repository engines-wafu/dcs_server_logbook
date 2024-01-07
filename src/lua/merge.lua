-- merge.lua

local json = require "dkjson"

function parseLuaFile(fileName)
    local function dofileSafe(file)
        local f, err = loadfile(file)
        if f then
            -- Executes the chunk in a protected environment
            local success, statsOrError = pcall(f)
            if success then
                -- Check if stats is correctly returned or defined globally
                if statsOrError then
                    return statsOrError
                elseif _G['stats'] then
                    return _G['stats']
                else
                    error("The 'stats' table was not found in the file.")
                end
            else
                error("Error executing file: " .. statsOrError)
            end
        else
            error("Error loading file: " .. err)
        end
    end

    -- Load and execute the Lua file
    return dofileSafe(fileName)  -- Added return statement here
end

-- Function to merge two stats tables
-- Merges the content of table2 into table1

function mergeStats(table1, table2)
    for key, playerData in pairs(table2) do
        -- Ensure the entry exists in table1
        table1[key] = table1[key] or {}
        table1[key]["times"] = table1[key]["times"] or {}

        for aircraft, stats in pairs(playerData["times"] or {}) do
            -- Ensure the aircraft entry exists in table1
            table1[key]["times"][aircraft] = table1[key]["times"][aircraft] or {}

            -- Merge 'total', 'inAir', etc. for each aircraft
            for stat, value in pairs(stats) do
                if stat ~= "kills" then
                    if type(value) == "number" then
                        table1[key]["times"][aircraft][stat] = (table1[key]["times"][aircraft][stat] or 0) + value
                    end
                end
            end

            -- Merge 'kills' for each aircraft
            if stats["kills"] then
                table1[key]["times"][aircraft]["kills"] = table1[key]["times"][aircraft]["kills"] or {}
                for killType, kills in pairs(stats["kills"]) do
                    if type(kills) == "table" then
                        table1[key]["times"][aircraft]["kills"][killType] = table1[key]["times"][aircraft]["kills"][killType] or {}
                        for k, v in pairs(kills) do
                            table1[key]["times"][aircraft]["kills"][killType][k] = (table1[key]["times"][aircraft]["kills"][killType][k] or 0) + v
                        end
                    else
                        table1[key]["times"][aircraft]["kills"][killType] = (table1[key]["times"][aircraft]["kills"][killType] or 0) + kills
                    end
                end
            end
        end

        -- Safely update 'lastJoin' to the most recent
        if playerData["lastJoin"] then
            table1[key]["lastJoin"] = math.max(table1[key]["lastJoin"] or 0, playerData["lastJoin"])
        end
    end
end

function writeStatsToJSON(stats, outputFileName)
    local json_data = json.encode(stats, { indent = true })

    local file, err = io.open(outputFileName, "w")
    if not file then
        error("Failed to open file for writing: " .. err)
    end

    file:write(json_data)
    file:close()

    -- Print the file path instead of a message
    print(outputFileName)
end

-- Main script to merge multiple files
combinedStats = {}

-- Assuming you have a list of file names
fileNames = {
    "data/stats/SlmodStats_server1.lua",
    "data/stats/SlmodStats_server2.lua"
    -- Add all file names here
}

for _, fileName in ipairs(fileNames) do
    local stats = parseLuaFile(fileName)
    mergeStats(combinedStats, stats)
end

-- Write the combined stats to a JSON file
local outputFileName = "data/stats/combinedStats.json"
writeStatsToJSON(combinedStats, outputFileName)

return {
    parseLuaFile = parseLuaFile,
    mergeStats = mergeStats,
    writeStatsToJSON = writeStatsToJSON
}
