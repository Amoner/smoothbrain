"""How much work Smooth Brain does for each thing that happens in the game,
measured offline: the addon's real files, the stand-ins from test.py, and a
full set of bags (120 slots, 85 different items, 30 quests).

For each event it prints the time spent in the addon's own Lua, the memory it
throws away, and how often it calls into the game and the other addons. The
time inside those isn't in it: the stand-ins answer at once. So compare the
numbers with each other and from one version to the next, not with a frame.

Needs Python with lupa (pip install lupa):   python SmoothBrain/dev/perf.py"""
import os
import sys

from lupa import lua51

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/") + "/"
sys.path.insert(0, ADDON + "dev")
import test as harness  # noqa: E402  (the stand-ins only; its checks sit under __main__)

STUBS = harness.HARNESS.split("-- Load the addon the way the game does")[0]

PROFILE = r"""
---------------------------------------------------------------------------
-- A realistic character: 120 slots, 108 stacks of 85 different items, 30 quests
---------------------------------------------------------------------------
local counts = {}
if priceAsked then priceAsked = setmetatable({}, { __newindex = function() end }) end   -- the tests' own note of what was asked: not wanted here
local function Counted(tbl, key, label)
  local original = tbl[key]
  tbl[key] = function(...)
    counts[label] = (counts[label] or 0) + 1
    return original(...)
  end
end

ITEMS, BOUND = {}, {}
for bag = 0, 5 do BAGS[bag] = {} end
local ids = {}
for n = 1, 85 do
  local id = 5000 + n
  ids[n] = id
  if n <= 40 then            -- trade goods with auction prices
    ITEMS[id] = { 10 + n, 0 }
    PRICES.dbminbuyout[id], PRICES.dbnumauctions[id] = 40 + n * 7, 50 + n
    PRICES.dbregionsaleavg[id], PRICES.dbregionsalerate[id] = 35 + n * 7, 0.4
  elseif n <= 55 then        -- potions and food
    ITEMS[id] = { 25, 0, 1, 0 }
    PRICES.dbminbuyout[id], PRICES.dbnumauctions[id] = 300, 80
    USES[id] = 439
  elseif n <= 65 then        -- green gear, half of it soulbound
    ITEMS[id] = { 400, 2, 2, 4, 0, "INVTYPE_HAND" }
    PRICES.dbminbuyout[id], PRICES.destroy[id] = 2500, 900
    BOUND[id] = n % 2 == 0 or nil
  elseif n <= 75 then        -- quest items
    ITEMS[id] = { 0, 4, 1, 12 }
    BOUND[id] = true
  elseif n <= 83 then        -- gray junk
    ITEMS[id] = { 30 + n, 0, 0 }
  else                       -- arrows
    ITEMS[id] = { 1, 0, 1, 6 }
  end
end
local stack = 0
for bag = 0, 5 do
  for slot = 1, 20 do
    stack = stack + 1
    if stack <= 108 then
      BAGS[bag][slot] = { ids[(stack - 1) % 85 + 1], 5 }
    else
      BAGS[bag][slot] = false   -- an empty slot
    end
  end
end
-- empty slots answer nil
local rawInfo, rawID = C_Container.GetContainerItemInfo, C_Container.GetContainerItemID
C_Container.GetContainerItemInfo = function(bag, slot) if BAGS[bag] and BAGS[bag][slot] then return rawInfo(bag, slot) end end
C_Container.GetContainerItemID = function(bag, slot) if BAGS[bag] and BAGS[bag][slot] then return rawID(bag, slot) end end
C_Container.GetContainerItemQuestInfo = function() return { isQuestItem = false, isActive = false } end

ON, READY, DONE, OBJECTIVES = {}, {}, {}, {}
local logEntries = { { isHeader = true, title = "Somewhere" } }
for q = 1, 30 do
  local id = 7000 + q
  ON[id] = true
  OBJECTIVES[id] = { { type = "monster", text = "Things slain: 3/10" }, { type = "item", text = "2/8 Thing " .. q } }
  logEntries[#logEntries + 1] = { questID = id, isHeader = false, title = "Quest " .. id }
end
C_QuestLog.IsQuestFlaggedCompleted = function() return false end
C_QuestLog.IsOnQuest = function(id) return ON[id] == true end
C_QuestLog.IsComplete = function() return false end
C_QuestLog.GetQuestObjectives = function(id)
  local copy = {}   -- the game hands out a fresh table each time
  for i, line in ipairs(OBJECTIVES[id] or {}) do copy[i] = { type = line.type, text = line.text } end
  return copy
end
C_QuestLog.GetInfo = function(index)
  local entry = logEntries[index]
  return entry and { questID = entry.questID, isHeader = entry.isHeader, title = entry.title } or nil
end
C_QuestLog.GetNumQuestLogEntries = function() return #logEntries, 30 end
ForeverCompanion = { GetAuctionEntry = function() return nil end }
function GetRealmName() return "PvP" end
function UnitFactionGroup() return "Alliance" end
function UnitClass() return "Hunter", "HUNTER" end

-- The game's own bag window, with a button for every slot
for index = #modern, 1, -1 do modern[index] = nil end
for bag = 0, 5 do
  for slot = 1, 20 do modern[#modern + 1] = GameSlot(bag, slot) end
end

for _, name in ipairs({ "GetContainerItemInfo", "GetContainerItemID", "GetContainerItemQuestInfo", "GetContainerNumSlots" }) do
  Counted(C_Container, name, name)
end
Counted(C_Item, "GetItemInfo", "GetItemInfo")
Counted(C_Item, "GetItemSpell", "GetItemSpell")
Counted(TSM_API, "GetCustomPriceValue", "TSM price lookups")
for _, name in ipairs({ "GetAuctionPriceByItemID", "GetAuctionAgeByItemID", "GetVendorPriceByItemID", "GetDisenchantPriceByItemID" }) do
  Counted(Auctionator.API.v1, name, "Auctionator lookups")
end
Counted(ForeverCompanion, "GetAuctionEntry", "Forever Companion lookups")
Counted(questieModules.QuestieDB, "QueryItemSingle", "Questie lookups")
Counted(questieModules.QuestieDB, "QueryQuestSingle", "Questie lookups")
Counted(QuestieLoader, "ImportModule", "Questie module imports")
Counted(C_QuestLog, "GetInfo", "quest log reads")
Counted(C_QuestLog, "GetQuestObjectives", "quest objective reads")
Counted(_G, "GetRealmName", "GetRealmName")
local painted = 0
local rawTexture = Texture

local ns = {}
for _, file in ipairs({ "Logic.lua", "SmoothBrain.lua", "Setup.lua" }) do
  local f = assert(io.open(ADDON_DIR .. file, "rb"))
  local source = f:read("*a")
  f:close()
  assert(loadstring(source, "@SmoothBrain/" .. file))("SmoothBrain", ns)
end
Fire("ADDON_LOADED", "SmoothBrain")
Fire("PLAYER_LOGIN")
SmoothBrainDB.onboarded = true
RunTimers()
-- the bags are opened once, so every slot's button is known to the addon
ContainerFrame1.UpdateItems(ContainerFrame1)

local out = {}
local function Measure(label, work, rounds)
  rounds = rounds or 200
  work()                       -- once, to settle
  counts = {}
  collectgarbage("collect")
  collectgarbage("stop")
  local before = collectgarbage("count")
  work()
  local garbage = collectgarbage("count") - before
  collectgarbage("restart")
  local once = counts
  counts = {}                  -- the timed rounds below count into a table of their own
  local started = os.clock()
  for _ = 1, rounds do work() end
  local each = (os.clock() - started) / rounds * 1000
  local parts = {}
  for name, n in pairs(once) do parts[#parts + 1] = ("%s %d"):format(name, n) end
  table.sort(parts)
  out[#out + 1] = ("%s\n    %.3f ms of our own Lua, %.0f KB of garbage\n    calls into the game and other addons: %s"):format(
    label, each, garbage, #parts > 0 and table.concat(parts, "; ") or "none")
end

Measure("A skill goes up (SKILL_LINES_CHANGED)", function()
  Fire("SKILL_LINES_CHANGED")
end)
Measure("The auction house shows results: 2 s later Forever Companion's notes are compared", function()
  Fire("AUCTION_ITEM_LIST_UPDATE")
  RunTimers()
end)
Measure("A quest is accepted: everything is judged afresh (QUEST_ACCEPTED, then the log settles)", function()
  Fire("QUEST_ACCEPTED", 1, 7001)
  Fire("QUEST_LOG_UPDATE")
  RunTimers()
end)
Measure("The quest log ticks (a kill that counts): QUEST_LOG_UPDATE, nothing that matters changed", function()
  Fire("QUEST_LOG_UPDATE")
  RunTimers()
end)
Measure("One bag changes, with the same items in it (BAG_UPDATE + BAG_UPDATE_DELAYED)", function()
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
end)
local arrows, shot = BAGS[4][4], 0
Measure("An arrow is shot: one stack's count changes", function()
  shot = shot + 1
  arrows[2] = 200 - shot % 150
  Fire("BAG_UPDATE", 4)
  Fire("BAG_UPDATE_DELAYED")
end)
local goods, looted = BAGS[0][1], 0
Measure("One trade good is looted: its stack's count changes", function()
  looted = looted + 1
  goods[2] = 5 + looted % 15
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
end)
Measure("The game redraws its open bag window (UpdateItems)", function()
  ContainerFrame1.UpdateItems(ContainerFrame1)
end)
GameTooltip.lines = {}
Measure("A tooltip is shown for an item you carry", function()
  GameTooltip.lines = {}
  tooltipHook(GameTooltip, { id = 5001 })
end, 20000)
Measure("A tooltip is shown for an item you don't carry (auction house, vendor, chat link)", function()
  tooltipHook(GameTooltip, { id = 4242 })
end, 20000)
Measure("A mouse click anywhere (GLOBAL_MOUSE_DOWN, left button)", function()
  Fire("GLOBAL_MOUSE_DOWN", "LeftButton")
end, 20000)

return table.concat(out, "\n\n")
"""

if __name__ == "__main__":
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.globals().ADDON_DIR = ADDON
    run = rt.eval("function(src) return assert(loadstring(src, '@perf'))() end")
    print(run(STUBS + PROFILE))
