@echo off
set PATH=C:\dcs_server_logbook\bin;%PATH%
set LUA_PATH=C:\dcs_server_logbook\?.lua

copy /y "C:\Users\JointStrikeWing\Saved Games\DCS.openbeta_server\Slmod\SlmodStats.lua" "C:\dcs_server_logbook\data\SlmodStats_server1.lua"
copy /y "C:\Users\JointStrikeWing\Saved Games\DCS.openbeta_server2\Slmod\SlmodStats.lua" "C:\dcs_server_logbook\data\SlmodStats_server2.lua"

lua54.exe main.lua