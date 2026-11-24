"""Offline tests for Smooth Brain: loads the addon's real files into Lua 5.1
with stand-ins for the game, RestedXP, Questie, TradeSkillMaster, Auctionator,
Bagnon, Baganator, BetterBags, EllesmereUI and the game's own bag windows.
Needs Python with lupa (pip install lupa):   python SmoothBrain/dev/test.py"""
import os
import sys

from lupa import lua51

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/") + "/"

HARNESS = r"""
local results = {}
local function Check(label, ok, detail)
  results[#results + 1] = (ok and "PASS  " or "FAIL  ") .. label .. (detail ~= nil and ("  [" .. tostring(detail) .. "]") or "")
  if not ok then results.failed = true end
end
local printed = {}
function print(...)
  local parts = {}
  for i = 1, select("#", ...) do parts[#parts + 1] = tostring((select(i, ...))) end
  printed[#printed + 1] = table.concat(parts, " ")
end

---------------------------------------------------------------------------
-- The game
---------------------------------------------------------------------------
local frames = {}
local function Texture()
  return { SetSize = function() end,
    SetPoint = function(self, point)
      self.point = point
      self.points = self.points or {}
      self.points[#self.points + 1] = point
    end,
    SetTexture = function(self, path) self.texture = path end,
    SetShown = function(self, shown) self.shown = shown end, SetAllPoints = function() end,
    SetColorTexture = function(self, r, g, b, a) self.colour = { r, g, b, a } end }
end
-- A frame, font string or texture of the setup window: it remembers its text,
-- tick, scripts and whether it shows; every other method does nothing.
local Widget = {}
Widget.__index = function(_, key)
  local method = rawget(Widget, key)
  if method then return method end
  if type(key) == "string" and key:match("^%u") then return function() end end
end
local function NewWidget(name)
  local widget = setmetatable({ events = {}, scripts = {}, shown = true, enabled = true }, Widget)
  if name then _G[name] = widget end
  return widget
end
function Widget:RegisterEvent(event) self.events[event] = true end
function Widget:SetScript(name, fn)
  self.scripts[name] = fn
  if name == "OnEvent" then self.handler = fn end
end
function Widget:Show()
  if not self.shown then
    self.shown = true
    if self.scripts.OnShow then self.scripts.OnShow(self) end
  end
end
function Widget:Hide()
  if self.shown then
    self.shown = false
    if self.scripts.OnHide then self.scripts.OnHide(self) end
  end
end
function Widget:IsShown() return self.shown end
function Widget:SetShown(shown) if shown then self:Show() else self:Hide() end end
function Widget:SetText(text) self.text = text end
function Widget:GetText() return self.text end
function Widget:SetChecked(checked) self.checked = checked and true or false end
function Widget:GetChecked() return self.checked end
function Widget:SetEnabled(enabled) self.enabled = enabled and true or false end
function Widget:SetTexture(path) self.texture = path end
function Widget:SetDesaturated(gray) self.gray = gray and true or false end
function Widget:CreateFontString() return NewWidget() end
function Widget:CreateTexture() return NewWidget() end
UIParent, UISpecialFrames = NewWidget(), {}
function CreateFrame(_, name)
  local f = NewWidget(name)
  frames[#frames + 1] = f
  return f
end
local function Fire(event, ...)
  for _, f in ipairs(frames) do
    if f.events[event] and f.handler then f.handler(f, event, ...) end
  end
end
function hooksecurefunc(a, b, c)
  local tbl, name, hook = a, b, c
  if type(a) == "string" then tbl, name, hook = _G, a, b end
  local original = tbl[name]
  tbl[name] = function(...) local x, y = original(...) hook(...) return x, y end
end
SlashCmdList, NUM_BAG_SLOTS, NUM_CONTAINER_FRAMES = {}, 4, 13
NUM_TOTAL_EQUIPPED_BAG_SLOTS = 5   -- the reagent bag comes after the four bags
ERR_INV_FULL = "Inventory is full."
local timers = {}
local delays = {}   -- [timer] = after how many seconds it was asked for
C_Timer = { After = function(wait, fn) timers[#timers + 1] = fn delays[fn] = wait end }
local function RunTimers()
  local due = timers
  timers = {}
  for _, fn in ipairs(due) do fn() end
end
Enum = { TooltipDataType = { Item = 0 } }
local tooltipHook
TooltipDataProcessor = { AddTooltipPostCall = function(_, fn) tooltipHook = fn end }
-- The tooltip also says what the mouse is on: `hovered` is the item it shows, `owner` the button it belongs to.
GameTooltip = { lines = {}, AddLine = function(self, text) self.lines[#self.lines + 1] = text end,
  AddDoubleLine = function(self, left, right) self.lines[#self.lines + 1] = left .. "  >>  " .. right end,
  IsShown = function(self) return self.hovered ~= nil end,
  GetItem = function(self) return "x", self.hovered and ("|cffffffff|Hitem:" .. self.hovered .. ":::|h[x]|h|r") or nil end,
  GetOwner = function(self) return self.owner end,
  -- Like the live client: no OnTooltipAddMoney script, and hooking one it lacks is an error.
  HasScript = function(_, script) return script == "OnTooltipCleared" end,
  HookScript = function(self, script, fn)
    if script ~= "OnTooltipCleared" then error(self:GetName() .. " doesn't have a \"" .. script .. "\" script") end
    self.cleared = fn
  end,
  GetName = function() return "GameTooltip" end }
local function Hover(itemID, mouseElsewhere)
  GameTooltip.hovered = itemID
  GameTooltip.owner = itemID and { IsMouseOver = function() return not mouseElsewhere end } or nil
end
ItemRefTooltip = {}
-- The game's "Sell Price" line: a money frame with a label and three coin buttons, white.
local function Text()
  return { colour = { 1, 1, 1 }, SetTextColor = function(self, r, g, b) self.colour = { r, g, b } end,
    GetTextColor = function(self) return self.colour[1], self.colour[2], self.colour[3] end }
end
local moneyFrame = { GetName = function() return "GameTooltipMoneyFrame1" end, PrefixText = Text(),
  GoldButton = { Text = Text() }, SilverButton = { Text = Text() }, CopperButton = { Text = Text() },
  Hide = function(self) self.hidden = true end }
-- Like the game: a blank line, with the money frame shown over it. Each line's
-- left text is GameTooltipTextLeft<n>.
local ownLine = true   -- false: a tooltip whose lines can't be reached, as an older game's might be
function GameTooltip_OnTooltipAddMoney(tooltip)
  tooltip:AddLine(" ")
  local n = #tooltip.lines
  _G["GameTooltipTextLeft" .. n] = ownLine and { GetText = function() return tooltip.lines[n] end,
    SetText = function(_, text) tooltip.lines[n] = text end, SetTextColor = function() end } or nil
  moneyFrame.hidden = false
  tooltip.shownMoneyFrames = { moneyFrame }
end
GameTooltip.NumLines = function(self) return #self.lines end
local SHIFT = false
function IsShiftKeyDown() return SHIFT end

-- Items: [id] = { vendor sell price, bind type, quality (1), class (7, trade goods), subclass (0), equip slot (""),
--   whether the game marks it a crafting reagent }
local ITEMS = {
  [100] = { 12, 0 },   -- cheap meat, plenty on the auction house; a quest needs 10
  [101] = { 50, 0 },   -- pricey hide a quest needs
  [102] = { 0, 4 },    -- soulbound quest item, quest still to do
  [103] = { 5, 0 },    -- few listed
  [104] = { 25, 0 },   -- sold by a vendor
  [105] = { 8, 0 },    -- its quest is done
  [106] = { 8, 0 },    -- you are on its quest
  [107] = { 9, 0 },    -- only a low-priority (other faction) guide wants it; no price to buy it known
  [108] = { 9, 0 },    -- no price to buy it known
  [109] = { 30, 0 },   -- a quest needs it and nobody sells it
  [111] = { 16, 0 },   -- Spider Ichor: costs barely more to buy than a vendor pays
  [112] = { 100, 0 },  -- cloth worth far more on the auction house
  [113] = { 30, 0, 0 },      -- gray junk
  [114] = { 400, 2, 2, 4, 0, "INVTYPE_CHEST" },  -- armour you have worn: soulbound
  [115] = { 1, 0, 1, 6 },    -- arrows
  [116] = { 50, 0 },   -- listed below what a vendor pays
  [117] = { 100, 0 },  -- none listed, but it sells in the region
  [118] = { 40, 0 },   -- worth auctioning, but its auctions rarely sell
  [119] = { 75, 0, 1, 0 },   -- Healing Potion a later quest needs one of
  [120] = { 75, 0, 1, 0 },   -- another potion, no quest
  [2901] = { 20, 0, 1, 2, 0, "INVTYPE_2HWEAPON" },   -- Mining Pick
  [121] = { 30, 0, 1, 2, 20, "INVTYPE_2HWEAPON" },   -- some fishing pole not on the list
  [122] = { 0, 4, 1, 12 },   -- quest item left behind: its only quest is done
  [123] = { 0, 4, 1, 12 },   -- quest item with one quest done and one still open
  [124] = { 0, 4, 1, 12 },   -- its quest is done; the other faction's version never will be
  [125] = { 30, 1, 1, 12 },  -- soulbound leftover a vendor does buy
  [126] = { 0, 1, 1, 4, 0, "INVTYPE_TRINKET" },   -- a trinket from a finished quest line
  [127] = { 0, 4, 1, 12 },   -- leftover that RestedXP knows the quest of
  [130] = { 962, 2, 2, 4, 0, "INVTYPE_HAND" },    -- green gloves that sell for more than their dust
  [131] = { 500, 2, 2, 4, 0, "INVTYPE_HAND" },    -- green gloves worth more as dust than sold either way
  [132] = { 400, 2, 2, 4, 0, "INVTYPE_HAND" },    -- the same, but soulbound
  [133] = { 800, 2, 2, 2, 0, "INVTYPE_WEAPON" },  -- green sword whose dust is worth about what a vendor pays
  -- Items only Auctionator knows a price for
  [140] = { 10, 0 },   -- seen today
  [141] = { 10, 0 },   -- a quest needs it; last seen five days ago
  [142] = { 10, 0 },   -- a quest needs it; seen today
  [143] = { 10, 0 },   -- not seen for over three weeks
  [144] = { 5, 0 },    -- a vendor you visited sells it
  [145] = { 500, 2, 2, 4, 0, "INVTYPE_HAND" },   -- green gloves Auctionator has a disenchant value for
  -- Things lying in a loot window
  [150] = { 3, 0 },          -- worth 3c
  [151] = { 20, 0 },         -- worth 20c
  [152] = { 0, 4, 1, 12 },   -- a quest item, worth nothing
  [153] = { 1, 0 },          -- 1c from a vendor, 5s on the auction house
  [154] = { 1, 1 },          -- the same, but binds when picked up
  -- Quest items no RestedXP guide lists
  [160] = { 0, 4, 1, 12 },   -- a quest item Questie knows nothing about
  [161] = { 0, 1, 1, 15 },   -- not a quest item by kind, but Questie ties it to a quest still open
  [162] = { 0, 1, 1, 15 },   -- an item that starts a quest
  [170] = { 10, 0 },         -- a trade good kept in the reagent bag
  [171] = { 0, 1, 1, 15 },   -- Memories of Valor: a soulbound book, no vendor price, no quest
  [172] = { 0, 0, 1, 15 },   -- vendors don't buy it, but it sells well at auction
  [173] = { 30, 1, 1, 0 },   -- a soulbound potion
  -- Items of quests that are complete and only wait to be handed in
  [180] = { 0, 4, 1, 12 },   -- only a tool: the quest was to kill something
  [181] = { 0, 4, 1, 12 },   -- the quest's own "collect" objective: the hand-in takes it
  [182] = { 0, 4, 1, 12 },   -- the game won't say what the quest's objectives are
  [183] = { 0, 4, 1, 12 },   -- not in the game's objective list, but in Questie's
  -- The cases from the code review
  [190] = { 0, 0, 1, 15 },                        -- leftover vendors don't buy, worth a lot at auction
  [191] = { 0, 4, 1, 12 },                        -- RestedXP's quest for it is done; Questie knows another, still open
  [192] = { 300, 1, 2, 4, 0, "INVTYPE_HAND" },    -- soulbound gloves an open quest wants
  [193] = { 20, 0, 1, 12 },                       -- a tradeable quest item with a vendor price, cheap to buy
}
local LOOT = {}   -- { itemID, quantity, isQuestItem } per slot of the open loot window
function GetNumLootItems() return #LOOT end
function GetLootSlotLink(slot) return LOOT[slot] and ("|Hitem:" .. LOOT[slot][1] .. ":::|h[x]|h") or nil end
function GetLootSlotInfo(slot) return 1, "x", LOOT[slot][2] or 1, nil, 1, false, LOOT[slot][3] or false end
C_Item = { GetItemInfo = function(id)
  local item = ITEMS[id]
  if not item then return nil end
  -- As on the current client: things you can't wear have a slot name too, not an empty one.
  return "Item" .. id, "[Item" .. id .. "]", item[3] or 1, 1, 0, "", "", 20, item[6] or "INVTYPE_NON_EQUIP_IGNORE", 0, item[1], item[4] or 7,
    item[5] or 0, item[2], 0, nil, item[7] == true
end }
-- The spell behind an item's "Use:", for the items that have one: its name and number.
local USES = { [173] = 439, [120] = 439 }   -- the potions
function C_Item.GetItemSpell(id)
  if USES[id] == "broken" then error("no such item") end
  if USES[id] then return "Use" .. id, USES[id] end
end
local BAGS = { [0] = { { 100, 10 }, { 101, 4 }, { 102, 1 }, { 103, 6 }, { 104, 5 }, { 105, 3 }, { 106, 2 }, { 107, 1 },
  { 108, 20 }, { 109, 2 }, { 100, 5 }, { 111, 10 }, { 112, 4 }, { 113, 1 }, { 114, 1 }, { 115, 200 }, { 116, 2 },
  { 117, 1 }, { 118, 10 }, { 119, 24 }, { 120, 24 }, { 2901, 1 }, { 121, 1 }, { 122, 1 }, { 123, 1 }, { 124, 1 },
  { 125, 1 }, { 126, 1 }, { 127, 1 }, { 130, 1 }, { 131, 1 }, { 132, 1 }, { 133, 1 },
  { 998, 1 },      -- 998: an item the game hasn't loaded yet
  { 140, 10 }, { 141, 5 }, { 142, 5 }, { 143, 1 }, { 144, 1 }, { 145, 1 },
  { 160, 1 }, { 161, 1 }, { 162, 1 }, { 171, 1 }, { 172, 1 }, { 173, 2 }, { 180, 1 }, { 181, 1 }, { 182, 1 }, { 183, 1 },
  { 190, 1 }, { 191, 1 }, { 192, 1 }, { 193, 4 } },
  [5] = { { 170, 4 } } }   -- the reagent bag
local BOUND = { [102] = true, [114] = true, [122] = true, [123] = true, [124] = true, [125] = true, [126] = true, [127] = true,
  [132] = true, [160] = true, [161] = true, [162] = true, [171] = true, [173] = true, [180] = true, [181] = true,
  [182] = true, [183] = true, [191] = true, [192] = true }
local ENCHANTER = false
function IsPlayerSpell(spell) return ENCHANTER and spell == 13262 end
function GetSpellTexture(spell) return spell == 13262 and 136244 or nil end
local slotReads = {}   -- [bag] = how often one of its slots was read
C_Container = {
  GetContainerNumSlots = function(bag) return BAGS[bag] and #BAGS[bag] or 0 end,
  GetContainerItemInfo = function(bag, slot)
    slotReads[bag] = (slotReads[bag] or 0) + 1
    local stack = BAGS[bag] and BAGS[bag][slot]
    return stack and { itemID = stack[1], stackCount = stack[2], isBound = BOUND[stack[1]] == true } or nil
  end,
  GetContainerItemID = function(bag, slot) return BAGS[bag] and BAGS[bag][slot] and BAGS[bag][slot][1] or nil end,
  -- Free slots, and the kind of bag: 0 for an ordinary one. Bag 4 is a quiver with room in it.
  GetContainerNumFreeSlots = function(bag)
    if bag == 4 then return 6, 1 end
    return bag == 0 and FREE_SLOTS or 0, 0
  end,
  -- What the game itself says of a slot: a quest item, and the quest it starts if it starts one
  GetContainerItemQuestInfo = function(bag, slot)
    local id = BAGS[bag] and BAGS[bag][slot] and BAGS[bag][slot][1]
    return { isQuestItem = id == 160, questID = id == 162 and 936 or nil, isActive = false }
  end,
}
FREE_SLOTS = 0
local DONE = { [905] = true, [927] = true, [930] = true, [931] = true, [933] = true, [960] = true, [961] = true }
local ON = { [906] = true, [950] = true, [951] = true, [952] = true, [953] = true }
local READY = { [950] = true, [951] = true, [952] = true, [953] = true }   -- complete, not yet handed in
local OBJECTIVES = {
  [950] = { { type = "monster", text = "Carnage slain: 1/1", finished = true } },
  [951] = { { type = "monster", text = "Carnage slain: 1/1", finished = true }, { type = "item", text = "1/1 Item181", finished = true } },
  [953] = { { type = "monster", text = "Carnage slain: 1/1", finished = true } },
}
-- The quest log as the game lists it: a header, then the quests you are on. A quest under a folded
-- header is counted but not listed.
local FOLDED = {}
local function LogEntries()
  local ids = {}
  for id in pairs(ON) do
    if not FOLDED[id] then ids[#ids + 1] = id end
  end
  table.sort(ids)
  local entries = { { isHeader = true, title = "Somewhere" } }
  for _, id in ipairs(ids) do entries[#entries + 1] = { questID = id, isHeader = false, title = "Quest " .. id } end
  return entries
end
C_QuestLog = {
  IsQuestFlaggedCompleted = function(id) return DONE[id] == true end,
  IsOnQuest = function(id) return ON[id] == true end,
  IsComplete = function(id) return READY[id] == true end,
  GetQuestObjectives = function(id) return OBJECTIVES[id] end,
  GetInfo = function(index) return LogEntries()[index] end,
  GetNumQuestLogEntries = function()
    local quests = 0
    for _ in pairs(ON) do quests = quests + 1 end
    return #LogEntries(), quests
  end,
}

---------------------------------------------------------------------------
-- RestedXP, as an AceAddon with the two tables its tooltip uses
---------------------------------------------------------------------------
local function Guide(name, lowPrio, collects)
  local guide = { name = name, lowPrio = lowPrio, steps = {} }
  for itemID, qty in pairs(collects or {}) do
    guide.steps[#guide.steps + 1] = { elements = { { tag = "collect", id = itemID, qty = qty }, { tag = "goto" } } }
  end
  return guide
end
local main = Guide("23-30 Stranglethorn", nil, { [100] = 10, [101] = 4, [103] = 6, [104] = 3, [106] = 2, [109] = 2, [119] = 1,
  [141] = 5, [142] = 5 })
-- The same meat is also collected for something else (40 of them, no quest): the quest's own step counts.
main.steps[#main.steps + 1] = { elements = { { tag = "collect", id = 100, qty = 40, questId = 0 } } }
for _, step in ipairs(main.steps) do
  local element = step.elements[1]
  if element.id == 100 and element.qty == 10 then element.questId = 900 end
end
local other = Guide("Horde 20-30", "*other")
local function Entries(guide) return { { guide = guide, step = { n = 1 }, name = guide.name } } end
local RXP = {
  questItemList = { [100] = 900, [101] = 901, [102] = 902, [103] = 903, [104] = 904, [105] = 905, [106] = 906,
    [107] = 907, [109] = 909, [119] = 919, [127] = 927, [141] = 941, [142] = 942, [191] = 961 },
  turnInList = { [900] = Entries(main), [901] = Entries(main), [902] = Entries(main), [903] = Entries(main),
    [904] = Entries(main), [905] = Entries(main), [906] = Entries(main), [907] = Entries(other), [909] = Entries(main),
    [919] = Entries(main), [927] = Entries(main), [941] = Entries(main), [942] = Entries(main), [961] = Entries(main) },
  IsGuideActive = function(guide) return guide ~= nil end,
  IsStepShown = function() return true end,
}
local aceAddons = { RXPGuides = RXP }
LibStub = setmetatable({}, { __call = function(_, name)
  if name == "AceAddon-3.0" then
    return { GetAddon = function(_, addon) return aceAddons[addon] end }
  end
end })

---------------------------------------------------------------------------
-- Questie: the quests an item belongs to
---------------------------------------------------------------------------
local ITEM_QUESTS = { [190] = { 960 }, [191] = { 961, 962 }, [192] = { 963 }, [193] = { 964 }, [180] = { 950 }, [181] = { 951 }, [182] = { 952 }, [183] = { 953 }, [161] = { 935 }, [102] = { 902 }, [122] = { 930 }, [123] = { 931, 932 }, [124] = { 933, 934 }, [125] = { 930 }, [126] = { 930 } }
local OTHER_FACTION = { [934] = true }
local ITEM_STARTS = {}   -- [itemID] = the quest Questie says the item starts
local questieModules = {
  QuestieDB = {
    QueryItemSingle = function(id, key)
      if key == "relatedQuests" then return ITEM_QUESTS[id] end
      if key == "startQuest" then return ITEM_STARTS[id] end
    end,
    QueryQuestSingle = function(id, key)
      if key == "requiredRaces" then return OTHER_FACTION[id] and "theirs" or nil end
      if key == "objectives" and id == 953 then return { nil, nil, { { 183, "Item183" } } } end
    end,
  },
  QuestiePlayer = {
    HasRequiredRace = function(races) return races ~= "theirs" end,
    HasRequiredClass = function() return true end,
  },
}
QuestieLoader = { ImportModule = function(_, name) return questieModules[name] end }
Questie = { started = true }   -- the real one sets this once it has finished starting

---------------------------------------------------------------------------
-- TradeSkillMaster's price lookups
---------------------------------------------------------------------------
local PRICES = {
  dbminbuyout = { [100] = 30, [101] = 4000, [103] = 20, [104] = 90, [105] = 40, [106] = 40, [111] = 19, [112] = 2500,
    [114] = 9000, [115] = 2, [116] = 40, [118] = 900, [119] = 133, [120] = 133, [2901] = 100, [121] = 400,
    [130] = 3800, [131] = 900, [153] = 500, [154] = 500,
    [2589] = 27, [2770] = 50, [170] = 12, [172] = 4000, [190] = 50000, [193] = 22 },   -- with 118 above, three of the ten common items the setup window asks about
  dbnumauctions = { [100] = 545, [101] = 60, [103] = 7, [104] = 300, [105] = 10, [106] = 10, [111] = 112, [112] = 80,
    [114] = 3, [115] = 900, [116] = 6, [118] = 15, [119] = 199, [120] = 199, [2901] = 5, [121] = 4,
    [130] = 146, [131] = 20, [153] = 40, [154] = 40, [170] = 50, [172] = 9, [190] = 9, [193] = 400 },
  destroy = { [130] = 3590, [131] = 2500, [132] = 2000, [133] = 900, [111] = 5000 },
  dbregionsaleavg = { [111] = 16, [117] = 3000 },
  dbregionsalerate = { [111] = 0.736, [118] = 0.05 },
  vendorbuy = { [104] = 60 },
}
local priceLookups = 0   -- how often TradeSkillMaster was asked: judging an item afresh asks it again
local priceAsked = {}    -- [itemID] = the price sources it was asked for, in order
TSM_API = { GetCustomPriceValue = function(source, itemString)
  priceLookups = priceLookups + 1
  local id = tonumber(itemString:match("^i:(%d+)$"))
  if id then priceAsked[id] = (priceAsked[id] and (priceAsked[id] .. " ") or "") .. source end
  local value = PRICES[source] and PRICES[source][id]
  if value then return value end
  return nil, "no value"
end }
-- Its desktop app's data reaches it through this one global, as the game loads.
local tsmGot = {}
function TSM_APPHELPER_LOAD_DATA(tag, realm, data) tsmGot[#tsmGot + 1] = { tag, realm, data } end
local tsmLoader = TSM_APPHELPER_LOAD_DATA

---------------------------------------------------------------------------
-- Auctionator's lookups: prices from your own scans, with their age in days
---------------------------------------------------------------------------
local ATR = {
  price = { [140] = 14, [141] = 30, [142] = 30, [143] = 50, [111] = 25, [2589] = 30 },
  age = { [140] = 0, [141] = 5, [142] = 0, [111] = 0, [2589] = 1 },
  vendor = { [144] = 20 },
  dust = { [145] = 3000 },
}
local atrChanged
local function Lookup(kind)
  return function(caller, itemID)
    assert(caller == "SmoothBrain" and type(itemID) == "number", "Auctionator wants the addon's name and an item number")
    return ATR[kind][itemID]
  end
end
Auctionator = { API = { v1 = {
  GetAuctionPriceByItemID = Lookup("price"), GetAuctionAgeByItemID = Lookup("age"),
  GetVendorPriceByItemID = Lookup("vendor"), GetDisenchantPriceByItemID = Lookup("dust"),
  RegisterForDBUpdate = function(caller, callback) atrChanged = callback end,
} } }

---------------------------------------------------------------------------
-- Bagnon's item button class, and the game's own bag windows
---------------------------------------------------------------------------
Bagnon = { Item = {} }
function Bagnon.Item:Update() self.info = { itemID = self.itemID } end
local function Button(bag, itemID, slot)
  local button = setmetatable({ bag = bag, itemID = itemID, slot = slot }, { __index = Bagnon.Item })
  function button:GetBag() return self.bag end
  function button:GetID() return self.slot end
  function button:CreateTexture() return Texture() end
  return button
end
-- Baganator: addons register a "corner widget", and ask it to redraw.
local widgets, redraws = {}, 0
Baganator = {
  API = {
    RegisterCornerWidget = function(label, id, onUpdate, onInit, position, isFast)
      assert(not widgets[id], "registered twice")
      widgets[id] = { label = label, onUpdate = onUpdate, onInit = onInit, position = position }
    end,
    RequestItemButtonsRefresh = function(reasons) redraws = redraws + 1 end,
  },
  Constants = { RefreshReason = { ItemWidgets = "widgets" } },
}
-- A current client: the window redraws through its own UpdateItems, and each slot knows its bag.
local function GameSlot(bag, slot)
  return { GetBagID = function() return bag end, GetID = function() return slot end, CreateTexture = function() return Texture() end }
end
local modern = { GameSlot(0, 12), GameSlot(0, 13), GameSlot(0, 21), GameSlot(0, 2), GameSlot(0, 24), GameSlot(0, 22) }
ContainerFrame1 = { UpdateItems = function() end, GetChildren = function() return unpack(modern) end,
  GetName = function() return "ContainerFrame1" end, GetID = function() return 0 end }
-- An older client: one global function redraws a window, slots are named after it, the window's ID is the bag.
function ContainerFrame_Update() end
ContainerFrame2 = { GetName = function() return "ContainerFrame2" end, GetID = function() return 0 end }
ContainerFrame2Item1 = { GetID = function() return 12 end, CreateTexture = function() return Texture() end }
ContainerFrame2Item2 = { GetID = function() return 9 end, CreateTexture = function() return Texture() end }

---------------------------------------------------------------------------
-- BetterBags: an AceAddon whose Events module says when it draws a slot
---------------------------------------------------------------------------
local bbListeners, bbItemFrame = {}, { buttonsBySlotkey = {} }
local bbModules = {
  Events = { RegisterMessage = function(self, message, callback) bbListeners[message] = callback end },
  ItemFrame = bbItemFrame,
}
aceAddons.BetterBags = { GetModule = function(self, name) return bbModules[name] or error("no module " .. name) end }
-- A slot as BetterBags knows it, and the button it draws the item on. `merged`: it stands for every stack of the item.
local function BBSlot(bag, slot, merged)
  local stack = BAGS[bag] and BAGS[bag][slot]
  local item = { currentData = { bagid = bag, slotid = slot, isItemEmpty = stack == nil, stackedCount = merged and 2 or nil,
    itemInfo = stack and { itemID = stack[1] } or nil } }
  return item, { CreateTexture = function() return Texture() end }
end
local function BBDraw(item, button) bbListeners["item/Updated"]({}, item, button) end
-- One slot it drew before anyone could listen: 10 of item 118, worth auctioning.
local bbEarly, bbEarlyButton = BBSlot(0, 19)
bbEarly._decoration = bbEarlyButton
bbItemFrame.buttonsBySlotkey["0_19"] = bbEarly

---------------------------------------------------------------------------
-- EllesmereUI's bags: other addons register a painter, which it calls for
-- every slot it draws, with the button and { bag, slot, info, itemLink }
---------------------------------------------------------------------------
local euiRedraws = 0
EUI_Bags = { itemOverlayIcons = {}, shown = true }   -- its bags are open while the addon loads
function EUI_Bags.RegisterItemOverlayIcon(name, paint)
  assert(type(name) == "string" and type(paint) == "function", "EllesmereUI wants a name and a painter")
  EUI_Bags.itemOverlayIcons[name] = paint
end
function EUI_Bags:IsShown() return self.shown end
function EUI_Bags:RefreshInventory() euiRedraws = euiRedraws + 1 end
-- One of its slots: a protected button, so anything written onto it is noted as a mistake,
-- and its _textOverlay, the frame over the item's picture, which remembers what was drawn on it.
local function EUISlot()
  local overlay, written = { made = {} }, {}
  function overlay:CreateTexture()
    local texture = Texture()
    self.made[#self.made + 1] = texture
    return texture
  end
  local button = setmetatable({}, { __index = { _textOverlay = overlay },
    __newindex = function(_, key) written[#written + 1] = tostring(key) end })
  return button, overlay, written
end
-- What it passes for a bag slot. `merged`: a list row standing for every stack of the item.
local function EUIData(bag, slot, merged)
  local stack = BAGS[bag] and BAGS[bag][slot]
  return { bag = bag, slot = slot, info = stack and { itemID = stack[1], stackCount = stack[2] } or nil,
    _mergedCount = merged and 2 or nil }
end
local function EUIDraw(button, data)
  for _, paint in pairs(EUI_Bags.itemOverlayIcons) do paint(button, data) end
end
-- The marker showing on a slot's picture frame, and whether the slot flashes.
local function EUIMark(overlay)
  for _, texture in ipairs(overlay.made) do
    if texture.colour == nil and texture.shown and texture.texture then return texture.texture end
  end
end
local function EUIGlows(overlay)
  for _, texture in ipairs(overlay.made) do
    if texture.colour ~= nil and texture.shown == true then return true end
  end
  return false
end

---------------------------------------------------------------------------
-- Load the addon the way the game does
---------------------------------------------------------------------------
local ns = {}
for _, file in ipairs({ "Logic.lua", "SmoothBrain.lua", "Vendors.lua", "Setup.lua" }) do
  local f = assert(io.open(ADDON_DIR .. file, "rb"))
  local source = f:read("*a")
  f:close()
  assert(loadstring(source, "@SmoothBrain/" .. file))("SmoothBrain", ns)
end
Fire("ADDON_LOADED", "SmoothBrain")
local bbHeardBeforeLogin = next(bbListeners) ~= nil
Fire("PLAYER_LOGIN")
Check("BetterBags is only listened to from login on: it forgets its listeners when it starts", not bbHeardBeforeLogin
  and bbListeners["item/Updated"] ~= nil and bbListeners["item/Clearing"] ~= nil)

-- The setup window opens by itself the first time
Check("nothing opens at once at login", SmoothBrainSetup == nil and SmoothBrainDB.onboarded == false)
RunTimers()
local S = ns.Setup
Check("...but a moment later the setup window does", SmoothBrainSetup ~= nil and SmoothBrainSetup:IsShown())
Check("TradeSkillMaster: found, with how many common items it prices", S.tsm.icon.texture:find("ReadyCheck-Ready", 1, true) ~= nil
  and S.tsm.text.text == "TradeSkillMaster: prices found, for 3 of 10 common items.", S.tsm.text.text)
Check("Auctionator: found, with how fresh its scan is",
  S.auctionator.text.text == "Auctionator: prices found, for 1 of 10 common items. Last seen yesterday.", S.auctionator.text.text)
Check("it says prices are available", S.prices.text.text:find("Prices are available", 1, true) ~= nil and not S.prices.icon.gray, S.prices.text.text)
Check("the current choices are shown", S.choices.both.checked and not S.choices.tsm.checked and S.limit.text == "5s"
  and S.toggles.icons.checked and S.toggles.tooltip.checked and S.toggles.flash.checked and S.presets[3].enabled == false
  and S.presets[1].enabled == true)
Check("it names the bags it marks and the quest addons it found", S.bags.text == "Markers work in: Baganator, Bagnon, BetterBags, EllesmereUI, the game's own bags."
  and S.rxp.text.text:find("found", 1, true) ~= nil and S.questie.text.text:find("found", 1, true) ~= nil, S.bags.text)
results[#results + 1] = "INFO  setup window, summary line: " .. tostring(S.summary.text)
SmoothBrainSetup:Hide()
Check("closing it means it won't open by itself again", SmoothBrainDB.onboarded == true)

-- The decision on its own
local function V(facts, limit)
  local r = ns.Decide(facts, limit or 500)
  return r and (r.verdict .. "/" .. r.why) or "nil", r or {}
end
local text, r

-- The case reported from the game: 24 Healing Potions, a later quest needs 1, the limit set to 50c.
local potions = { count = 24, consumable = true, quest = true, needed = 1, vendorSell = 75, ahPrice = 133, ahListed = 199 }
text, r = V(potions, 50)
Check("24 potions, 75c from a vendor and 1s 33c to buy: 13s 92c apart, so keep for the quest at a 50c limit", text == "quest/costly"
  and r.diff == 1392 and r.cost == 3192 and r.gain == 1800, text .. " diff " .. tostring(r.diff))
Check("...and at 5s", V(potions, 500) == "quest/costly")
Check("...but vendor once the limit covers the whole stack", V(potions, 1392) == "vendor/cheap" and V(potions, 1391) == "quest/costly")
potions.quest, potions.needed = nil, nil
Check("...without the quest: keep, being something you use up", V(potions, 50) == "keep/costly")
potions.consumable = nil
Check("...and auction if it were not", V(potions, 50) == "auction/costly")

text, r = V({ count = 10, quality = 1, vendorSell = 16, ahPrice = 19, ahListed = 112 }, 50)
Check("10 Spider Ichor, 16c from a vendor and 19c to buy: 30c apart, so vendor at a 50c limit", text == "vendor/cheap" and r.diff == 30, r.diff)
Check("...but not at a 20c limit", V({ count = 10, vendorSell = 16, ahPrice = 19, ahListed = 112 }, 20) == "auction/costly")

Check("on the quest: keep for it", V({ count = 3, quest = true, onQuest = true, vendorSell = 8, ahPrice = 1, ahListed = 99 }) == "quest/onquest")
Check("a quest item vendors don't buy: keep for it", V({ count = 3, quest = true, vendorSell = 0, ahPrice = 1, ahListed = 99 }) == "quest/novalue")
Check("vendors don't buy it, and it is barely worth anything at auction: keep", V({ count = 3, vendorSell = 0, ahPrice = 1, ahListed = 99 }) == "keep/nosale")
text, r = V({ count = 1, vendorSell = 0, ahPrice = 4000, ahListed = 9 })
Check("vendors don't buy it, but it sells well at auction: auction", text == "auction/unsellable" and r.cost == 4000 and r.listed == 9, text)
-- The case reported from the game: Memories of Valor, a soulbound book with no vendor price.
Check("a soulbound book vendors don't buy: keep", V({ count = 1, bound = true, vendorSell = 0 }) == "keep/nosale")
Check("...and its auction price, if it had one, would not matter", V({ count = 1, bound = true, vendorSell = 0, ahPrice = 4000, ahListed = 9 }) == "keep/nosale")
Check("...unless its quest is done: safe to delete", V({ count = 3, questDone = true, vendorSell = 0 }) == "free/done")
Check("soulbound quest item: keep for it", V({ count = 1, quest = true, bound = true, vendorSell = 5 }) == "quest/bound")
Check("soulbound, no quest: it can't be auctioned, so vendor", V({ count = 1, bound = true, vendorSell = 5, ahPrice = 9, ahListed = 9 }) == "vendor/boundsell")
Check("...but a soulbound thing you use up is kept", V({ count = 1, bound = true, consumable = true, vendorSell = 5 }) == "keep/useup")
-- The case reported from the game: the Cozy Sleeping Bag, soulbound, with a Use, and a vendor would buy it.
Check("...and so is a soulbound thing with a Use of its own", V({ count = 1, bound = true, usable = true, vendorSell = 2500 }) == "keep/use")
Check("...whatever it would fetch", V({ count = 1, bound = true, usable = true, vendorSell = 2500, ahPrice = 9, ahListed = 9 }) == "keep/use")
Check("...unless it is the leftover of a finished quest", V({ count = 1, bound = true, usable = true, questDone = true, vendorSell = 5 }) == "vendor/leftover")
Check("...one a vendor won't buy was kept already", V({ count = 1, bound = true, usable = true, vendorSell = 0 }) == "keep/nosale")
Check("...and one you can trade is priced like anything else", V({ count = 1, usable = true, vendorSell = 5, ahPrice = 9, ahListed = 9 }) == "vendor/cheap"
  and V({ count = 1, usable = true, vendorSell = 5, ahPrice = 9000, ahListed = 9 }) == "auction/costly")
-- The case reported from the game: Icicle Rod, soulbound, 34s 76c from a vendor, 4s 29c as dust.
local rod = { count = 1, quality = 2, bound = true, vendorSell = 3476, destroy = 429 }
Check("Icicle Rod: soulbound, so vendor", V(rod) == "vendor/boundsell" and select(2, V(rod)).gain == 3476)
rod.enchanter = true
Check("...also for an enchanter, as its dust is worth less", V(rod) == "vendor/boundsell" and select(2, V(rod)).dust == 429)
Check("soulbound leftover of a finished quest: vendor", V({ count = 1, bound = true, questDone = true, vendorSell = 5 }) == "vendor/leftover")

local meat = { count = 10, quest = true, needed = 10, vendorSell = 12, ahPrice = 30, ahListed = 545 }
text, r = V(meat)
Check("quest item cheap to buy back: vendor", text == "vendor/cheap" and r.gain == 120 and r.cost == 300 and r.diff == 180 and r.source == "ah", text)
Check("...keep with a lower limit, vendor exactly at it", V(meat, 179) == "quest/costly" and V(meat, 180) == "vendor/cheap")
text, r = V({ count = 6, quest = true, needed = 6, vendorSell = 5, ahPrice = 20, ahListed = 7 })
Check("quest item with too few listed: keep for it", text == "quest/fewlisted" and r.listed == 7 and r.short == 6, text)
Check("...twice what the quest takes is enough", V({ count = 6, quest = true, needed = 6, vendorSell = 5, ahPrice = 20, ahListed = 12 }) == "vendor/cheap")
Check("...and other items need no such margin", V({ count = 6, vendorSell = 5, ahPrice = 20, ahListed = 1 }) == "vendor/cheap")
text, r = V({ count = 5, quest = true, needed = 3, vendorSell = 25, vendorBuy = 60, ahPrice = 90, ahListed = 300 })
Check("a vendor sells it cheaper than the auction house", text == "vendor/cheap" and r.source == "vendor" and r.cost == 300 and r.diff == 175, r.source)
text, r = V({ count = 5, quest = true, needed = 3, vendorSell = 25, vendorBuy = 60, ahPrice = 40, ahListed = 300 })
Check("the auction house is cheaper than the vendor", r.source == "ah" and r.cost == 200, r.source)
text, r = V({ count = 5, quest = true, needed = 3, vendorSell = 25, vendorBuy = 60, ahPrice = 40, ahListed = 2 })
Check("few listed, but a vendor sells it", text == "vendor/cheap" and r.source == "vendor", text)
Check("a quest needs it and nobody sells it: keep for it", V({ count = 2, quest = true, needed = 2, vendorSell = 30 }) == "quest/nosource")
Check("...sales elsewhere in the region don't count for a quest item", V({ count = 2, quest = true, vendorSell = 30, regionSale = 40 }) == "quest/nosource")
Check("no price to buy it known: nothing to say", V({ count = 2, quality = 1, vendorSell = 30 }) == "nil")
Check("gray junk: vendor", V({ count = 1, quality = 0, vendorSell = 30 }) == "vendor/junk")
text, r = V({ count = 4, quality = 1, vendorSell = 100, ahPrice = 2500, ahListed = 80 })
Check("worth far more than a vendor pays: auction", text == "auction/costly" and r.diff == 9600, r.diff)
text, r = V({ count = 2, quality = 1, vendorSell = 50, ahPrice = 40, ahListed = 6 })
Check("listed below what a vendor pays: vendor", text == "vendor/cheap" and r.diff == -20, r.diff)
text, r = V({ count = 1, quality = 1, vendorSell = 100, regionSale = 3000 })
Check("none listed, but it sells in the region: auction", text == "auction/costly" and r.source == "region" and r.diff == 2900, text)
-- Disenchanting, for green or better gear
local gloves = { count = 1, quality = 2, vendorSell = 962, ahPrice = 3800, ahListed = 146, destroy = 3590 }
Check("gloves that sell for more than their dust: auction", V(gloves) == "auction/costly")
gloves.destroy = 5200
text, r = V(gloves)
Check("...worth more as dust: disenchant", text == "disenchant/dust" and r.dust == 5200 and r.cost == 3800 and r.byOther == true, text)
gloves.enchanter = true
Check("...and an enchanter is not told to find one", select(2, V(gloves)).byOther == nil)
text, r = V({ count = 1, quality = 2, vendorSell = 800, destroy = 900 })
Check("dust worth about what a vendor pays: vendor", text == "vendor/nodust" and r.dust == 900, text)
Check("...unless the limit is lower", V({ count = 1, quality = 2, vendorSell = 800, destroy = 900 }, 50) == "disenchant/dust")
local worn = { count = 1, quality = 2, bound = true, vendorSell = 400, destroy = 2000 }
Check("soulbound gear, not an enchanter: vendor, whatever its dust is worth", V(worn) == "vendor/boundsell")
worn.enchanter = true
Check("soulbound gear, enchanter: disenchant", V(worn) == "disenchant/dust")
worn.destroy = 600
Check("...but vendor when a vendor pays about as much", V(worn) == "vendor/boundsell")
Check("soulbound gear vendors don't buy, enchanter: disenchant", V({ count = 1, bound = true, enchanter = true, vendorSell = 0, destroy = 2000 }) == "disenchant/dust")
Check("an item a quest needs is never disenchanted", V({ count = 1, quest = true, bound = true, enchanter = true, vendorSell = 5, destroy = 9000 }) == "quest/bound")
-- The case reported from the game: Sage's Boots of the Eagle. 11s 12c from a vendor, 11s 99c on the auction
-- house, 12s 34c as materials by TradeSkillMaster's estimate (10s 47c by another addon's). It said disenchant.
local boots = { count = 1, quality = 2, vendorSell = 1112, ahPrice = 1199, ahListed = 51, destroy = 1234,
  destroyBy = "TradeSkillMaster", saleRate = 0.31 }
text, r = V(boots, 100)
Check("materials worth 35c more than the auction price: not worth disenchanting; at a 1s limit, vendor", text == "vendor/cheap"
  and r.dust == 1234 and r.diff == 87, text)
Check("...and the tooltip says what disenchanting would have added, and whose estimate that is", ns.Explain(r, ns.Money)
  == "A vendor pays 11s 12c for your 1. Buying them back costs 11s 99c on the auction house (51 listed), only 87c more."
  .. " Disenchanting would yield about 12s 34c (TradeSkillMaster's estimate), only 35c more.", ns.Explain(r, ns.Money))
text, r = V(boots, 50)
Check("...at a 50c limit, auction: the materials still add less than the limit", text == "auction/costly"
  and ns.Explain(r, ns.Money):find("only 35c more.", 1, true) ~= nil, text)
Check("...disenchant only once they beat the auction price by more than the limit", V(boots, 35) == "auction/costly"
  and V(boots, 34) == "disenchant/dust")
boots.destroy = 1047
text, r = V(boots, 50)
Check("...and by the other estimate, 10s 47c, disenchanting isn't mentioned at all", text == "auction/costly"
  and ns.Explain(r, ns.Money):find("Disenchant", 1, true) == nil, ns.Explain(r, ns.Money))
text, r = V({ count = 1, quality = 2, vendorSell = 0, ahPrice = 4000, ahListed = 9, destroy = 2000 })
Check("vendors don't buy it, and it fetches more at auction than as materials: auction", text == "auction/unsellable", text)
text, r = V({ count = 1, quality = 2, vendorSell = 0, ahPrice = 1000, ahListed = 9, destroy = 2000 })
Check("...but disenchant when the materials are worth clearly more", text == "disenchant/dust" and r.cost == 1000, text)

-- A price from your own scans: no count, but how long ago it was seen
text, r = V({ count = 10, vendorSell = 10, ahPrice = 14, ahSeen = 0 })
Check("a scanned price works like any other", text == "vendor/cheap" and r.diff == 40 and r.seen == 0 and r.listed == nil, text)
local scanned = { count = 5, quest = true, needed = 5, vendorSell = 10, ahPrice = 30, ahSeen = 1 }
Check("quest item seen listed yesterday: counts as buyable", V(scanned) == "vendor/cheap")
scanned.ahSeen = 2
text, r = V(scanned)
Check("...seen two days ago: too long for a quest item", text == "quest/stale" and r.seen == 2, text)
scanned.quest = nil
Check("...but fine for any other item", V(scanned) == "vendor/cheap")

Check("Money", ns.Money(12345) == "1g 23s 45c" and ns.Money(500) == "5s" and ns.Money(0) == "0c" and ns.Money(10007) == "1g 7c",
  ns.Money(12345))
Check("ParseMoney", ns.ParseMoney("5s") == 500 and ns.ParseMoney("1g 20s") == 12000 and ns.ParseMoney("250") == 250
  and ns.ParseMoney("2g3s4c") == 20304 and ns.ParseMoney("50c") == 50 and ns.ParseMoney("cheap") == nil and ns.ParseMoney("") == nil
  and ns.ParseMoney("5x") == nil)

-- With the game around it
local function Verdict(id) local result = ns.Check(id) return result and (result.verdict .. "/" .. result.why) or "nil" end
local a = ns.Check(100)
Check("two stacks are counted together", a.count == 15 and a.gain == 180 and a.cost == 450 and a.diff == 270, a.count)
Check("the quest's own collect step gives the quantity", a.needed == 10, a.needed)
Check("guides are named", a.guides[1] == "23-30 Stranglethorn", a.guides[1])
local EXPECT = {
  [100] = "vendor/cheap", [101] = "quest/costly", [102] = "quest/novalue", [103] = "quest/fewlisted", [104] = "vendor/cheap",
  [105] = "vendor/cheap", [106] = "quest/onquest", [107] = "nil", [108] = "nil", [109] = "quest/nosource",
  [111] = "vendor/cheap", [112] = "auction/costly", [113] = "vendor/junk", [114] = "vendor/boundsell", [115] = "nil",
  [116] = "vendor/cheap", [117] = "auction/costly", [118] = "auction/costly", [119] = "quest/costly", [120] = "keep/costly",
  [2901] = "nil", [121] = "nil", [122] = "free/done", [123] = "quest/held", [124] = "free/done", [125] = "vendor/leftover",
  [126] = "keep/nosale", [127] = "free/done", [170] = "vendor/cheap", [171] = "keep/nosale", [172] = "auction/unsellable",
  [173] = "keep/useup", [180] = "free/done", [181] = "quest/held", [182] = "quest/held", [183] = "quest/held",
  [190] = "auction/unsellable", [191] = "quest/held", [192] = "quest/held", [193] = "quest/held", [130] = "auction/costly", [131] = "disenchant/dust", [132] = "vendor/boundsell", [133] = "vendor/nodust",
  [140] = "vendor/cheap", [141] = "quest/stale", [142] = "vendor/cheap", [143] = "nil", [144] = "vendor/cheap",
  [145] = "disenchant/dust", [160] = "quest/held", [161] = "quest/held", [162] = "quest/held",
}
local LABEL = {
  [100] = "cheap meat a quest needs", [101] = "pricey hide a quest needs", [102] = "soulbound quest item, quest still to do",
  [103] = "quest item with few listed", [104] = "quest item a vendor sells", [105] = "tradeable item whose quest is done",
  [106] = "item of a quest you are on", [107] = "only a guide RestedXP hides wants it", [108] = "no price to buy it known",
  [109] = "quest item nobody sells", [111] = "Spider Ichor", [112] = "valuable cloth", [113] = "gray junk",
  [114] = "soulbound armour", [115] = "arrows", [116] = "listed below the vendor price", [117] = "none listed, sells in the region",
  [118] = "valuable but rarely sells", [119] = "potions a quest needs one of", [120] = "potions no quest needs",
  [2901] = "Mining Pick", [121] = "a fishing pole not on the tool list", [122] = "leftover quest item, its quest done",
  [123] = "quest item with a quest still open", [124] = "leftover whose other quest is the other faction's",
  [125] = "soulbound leftover a vendor buys", [126] = "trinket from a finished quest", [127] = "leftover RestedXP knows the quest of",
  [130] = "green gloves that sell for more than their dust", [131] = "green gloves worth more as dust",
  [132] = "soulbound green gloves, not an enchanter", [133] = "green sword whose dust is worth what a vendor pays",
  [140] = "Auctionator only, seen today", [141] = "Auctionator only, quest item last seen five days ago",
  [142] = "Auctionator only, quest item seen today", [143] = "Auctionator only, not seen for three weeks",
  [144] = "sold by a vendor Auctionator has seen", [145] = "green gloves with only Auctionator's disenchant value",
  [160] = "the game's own quest item, unknown to RestedXP and Questie", [161] = "item Questie ties to an open quest",
  [162] = "item that starts a quest not yet done", [170] = "trade good in the reagent bag",
  [171] = "soulbound book vendors don't buy", [172] = "unsellable item worth auctioning", [173] = "soulbound potion",
  [180] = "tool of a complete quest whose hand-in doesn't take it", [181] = "collect objective of a complete quest",
  [182] = "item of a complete quest with unreadable objectives", [183] = "item only Questie lists as an objective",
  [190] = "leftover vendors don't buy that sells at auction", [191] = "item RestedXP is done with but another quest needs",
  [192] = "soulbound gear an open quest wants", [193] = "tradeable quest item that is cheap to buy",
}
for id, want in pairs(EXPECT) do
  Check(("%s: %s"):format(LABEL[id], want), Verdict(id) == want, Verdict(id))
end
Check("an item you don't carry: no verdict", (function() RXP.questItemList[110] = 900 return Verdict(110) end)() == "nil")
Check("the vendor-sold quest item is bought back from the vendor", ns.Check(104).source == "vendor")
Check("quest items say why they are kept", ns.Check(160).questNote == "It is a quest item."
  and ns.Check(161).questNote == "A quest you haven't finished needs it." and ns.Check(162).questNote == "It starts a quest you haven't done."
  and ns.Check(123).questNote == "A quest you haven't finished needs it." and ns.Check(102).questNote == nil, ns.Check(160).questNote)
Check("a valuable leftover says to auction it, and that its quest is done", ns.Explain(ns.Check(190), ns.Money)
  == "Its quest is done (says Questie). Vendors don't buy it, but buying your 1 costs 5g on the auction house (9 listed).",
  ns.Explain(ns.Check(190), ns.Money))
Check("an item another quest still needs says so, whatever RestedXP's quest", ns.Check(191).questNote
  == "A quest you haven't finished needs it." and ns.Check(191).questDone == nil and ns.Check(191).by == nil, ns.Check(191).questNote)
Check("a cheap tradeable quest item is kept, not weighed against its price", ns.Explain(ns.Check(193), ns.Money)
  == "A quest you haven't finished needs it.", ns.Explain(ns.Check(193), ns.Money))
Check("a complete quest's tool says why it can go", ns.Explain(ns.Check(180), ns.Money)
  == "A leftover: its quest is complete, and handing it in doesn't take this item (says Questie). Vendors don't buy it.",
  ns.Explain(ns.Check(180), ns.Money))
Check("...and its collect objective says to hand the quest in", ns.Check(181).questNote
  == "Its quest is complete: hand it in, and this item goes with it." and ns.Check(183).questNote == ns.Check(181).questNote
  and ns.Check(182).questNote == ns.Check(181).questNote, ns.Check(182).questNote)
Check("leftovers say who vouches for them", ns.Check(122).by == "Questie" and ns.Check(127).by == "RestedXP" and ns.Check(105).by == "RestedXP")

local function Tip(id)
  GameTooltip.lines = {}
  tooltipHook(GameTooltip, { id = id })
  return table.concat(GameTooltip.lines, "\n        ")
end
-- The same with Shift held: the reason in full.
local function Full(id)
  SHIFT = true
  local tip = Tip(id)
  SHIFT = false
  return tip
end
Check("only gear is disenchanted, whatever TradeSkillMaster says of a trade good", ns.Check(111).dust == nil)
Check("a disenchant value says whose estimate it is", ns.Check(131).dust == 2500 and ns.Check(131).dustBy == "TradeSkillMaster"
  and ns.Check(145).dustBy == "Auctionator" and ns.Explain(ns.Check(131), ns.Money):find("(TradeSkillMaster's estimate)", 1, true) ~= nil,
  ns.Explain(ns.Check(131), ns.Money))
ATR.dust[131] = 1800
Fire("QUEST_ACCEPTED", 1, 1)
Check("where TradeSkillMaster and Auctionator both have one, the lower is used", ns.Check(131).dust == 1800
  and ns.Check(131).dustBy == "Auctionator", ns.Check(131).dust)
ATR.dust[131] = 9000
Fire("QUEST_ACCEPTED", 1, 1)
Check("...whichever addon it comes from", ns.Check(131).dust == 2500 and ns.Check(131).dustBy == "TradeSkillMaster", ns.Check(131).dust)
ATR.dust[131] = nil
Fire("QUEST_ACCEPTED", 1, 1)
Check("TradeSkillMaster's price wins where both have one", ns.Check(111).price == 19 and ns.Check(111).listed == 112
  and ns.Check(111).seen == nil)
Check("Auctionator fills in the rest", ns.Check(140).price == 14 and ns.Check(140).seen == 0 and ns.Check(144).source == "vendor"
  and ns.Check(145).dust == 3000)
for _, id in ipairs({ 111, 119, 120, 112, 100, 101, 122, 125, 127, 105, 130, 131, 133, 114, 140, 141, 144, 160, 161, 162, 171, 172,
  173, 180, 181 }) do
  results[#results + 1] = ("INFO  tooltip, %s:\n        %s\n      with Shift held:\n        %s"):format(LABEL[id], Tip(id), Full(id))
end
Check("the tooltip is one line: the marker, the verdict, and the prices behind it", Tip(111)
  == "|TInterface\\MoneyFrame\\UI-GoldIcon:0|t |cff40ff40Vendor it|r  >>  vendor 1s 60c, auction 1s 90c (x10)" and #GameTooltip.lines == 1, Tip(111))
Check("...the dearer way first when it is one to auction, and no count for a single item", Tip(112):find("Auction it|r  >>  auction 1g, vendor 4s (x4)", 1, true) ~= nil
  and Tip(130):find("Auction it|r  >>  auction 38s, vendor 9s 62c", 1, true) ~= nil and Tip(130):find("(x", 1, true) == nil, Tip(130))
Check("...materials against the better of the other two for gear to disenchant", Tip(131):find("Disenchant it|r  >>  materials ~25s, auction 9s", 1, true) ~= nil,
  Tip(131))
Check("...a quest's own note in a few words, or nothing when the verdict says it all", Tip(181):find("  >>  hand its quest in", 1, true) ~= nil
  and Tip(160):find("  >>  ", 1, true) == nil and #GameTooltip.lines == 1, Tip(160))
Check("...and with Shift held, the verdict and the reason in full", Full(111):find("Smooth Brain: |cff40ff40vendor it|r", 1, true) ~= nil
  and Full(111):find("Buying them back costs", 1, true) ~= nil and #GameTooltip.lines == 2, Full(111))
Check("no tooltip lines when there is nothing to say", Tip(108) == "" and Tip(115) == "" and Tip(2901) == ""
  and Full(108) == "" and Full(2901) == "")
do
  local columns = GameTooltip.AddDoubleLine
  GameTooltip.AddDoubleLine = nil   -- a tooltip that can't write two columns
  Check("a tooltip without two columns gets the same on one line", Tip(111):find("Vendor it|r  |cffcccccc", 1, true) ~= nil
    and Tip(111):find("auction", 1, true) ~= nil and #GameTooltip.lines == 1, Tip(111))
  GameTooltip.AddDoubleLine = columns
end
tooltipHook({ AddLine = function() error("another tooltip was written to") end }, { id = 100 })
Check("other tooltips are left alone", true)

-- Under the game's "Sell Price" line: what lands there while the game builds
-- the tooltip (the lines, as written and plainly), and the whole tooltip after.
-- Plainly: colours dropped, a coin's icon as its letter, our marks as words.
local function Plain(text)
  return (text:gsub("|T[^|]*ChatFrameExpandArrow:0|t ", "> ")
    :gsub("|T[^|]*SmoothBrain.auction:0|t", "[gavel]")
    :gsub("|T136244:0|t", "[dust]")
    :gsub("|T[^|]*UI%-(%a)%a*Icon[^|]*|t", function(coin) return coin:lower() end)
    :gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", ""))
end
local function Sold(id, cost, unknown)
  Hover(not unknown and id or nil)
  GameTooltip.lines = {}
  GameTooltip_OnTooltipAddMoney(GameTooltip, cost)
  local raw, under = {}, {}
  for i, line in ipairs(GameTooltip.lines) do raw[i], under[i] = line, Plain(line) end
  tooltipHook(GameTooltip, { id = id })
  local all = {}
  for i, line in ipairs(GameTooltip.lines) do all[i] = Plain(line) end
  Hover(nil)
  return under, all, raw
end
local function Lines(lines) return table.concat(lines, " | ") end
do
  local under, all, raw = Sold(112, 400)   -- to auction
  Check("the game's own line, written like ours: the coin, the label, the amount; dimmed, as it lost",
    under[1] == "g Sell Price: 4s" and raw[1]:find("|cff808080Sell Price:|r |cff77777c4|r", 1, true) ~= nil
    and moneyFrame.hidden == true, raw[1])
  Check("the verdict's line: the pointer, the gavel, the label gold, each amount in its coin's colour",
    raw[2]:find("^|T[^|]*ChatFrameExpandArrow:0|t |T[^|]*SmoothBrain.auction:0|t |cffffd100Auction Price:|r ") ~= nil
    and raw[2]:find("|cffffd7001|r|T[^|]*UI%-GoldIcon") ~= nil, raw[2])
  Check("one block: the three prices, the verdict, a blank line; nothing more at the end", under[2] == "> [gavel] Auction Price: 1g"
    and under[3]:find("^%[gavel%] Auction it  >>  auction 1g, vendor 4s") ~= nil and under[4] == " " and #under == 4 and #all == 4,
    Lines(all))
  under, all, raw = Sold(111, 160)   -- to vendor
  Check("vendor it: the pointer on the Sell Price line, the auction price dimmed", under[1] == "> g Sell Price: 1s 60c"
    and raw[1]:find("|cffffd100Sell Price:|r |cffc7c7cf1|r", 1, true) ~= nil
    and under[2] == "[gavel] Auction Price: 1s 90c" and raw[2]:find("|cff808080Auction Price:|r |cff77777c1|r", 1, true) ~= nil
    and raw[2]:find("|cff8e633990|r", 1, true) ~= nil, Lines(raw))
  Check("...the stack's prices when the game gives the stack's, the verdict under them", under[3]:find("Vendor it  >>  vendor 1s 60c", 1, true) ~= nil
    and #all == 4, Lines(all))
  under = Sold(111, 16)
  Check("one item's prices when the game gives one item's", under[1] == "> g Sell Price: 16c" and under[2] == "[gavel] Auction Price: 19c", Lines(under))
  under = Sold(111, 16)
  Check("...and all again the next time the tooltip is built", under[2] == "[gavel] Auction Price: 19c" and #under == 4, Lines(under))
  under = Sold(131, 900)   -- to disenchant
  Check("disenchant it: the pointer on the disenchant line, the other two dimmed", under[1] == "g Sell Price: 9s"
    and under[2] == "[gavel] Auction Price: 9s" and under[3] == "> [dust] Disenchant: 25s"
    and under[4]:find("Disenchant it", 1, true) ~= nil, Lines(under))
  under, all = Sold(111, 16, true)
  Check("an item the game can't name yet: its line left alone, the rest at the end", #under == 1 and under[1] == " "
    and all[2] == "[gavel] Auction Price: 19c" and all[3]:find("Vendor it", 1, true) ~= nil and #all == 3, Lines(all))
  under, all = Sold(108, 9)
  Check("nothing to say: the Sell Price line alone, undimmed, no blank line", #all == 1 and all[1] == "g Sell Price: 9c", Lines(all))
  SHIFT = true
  under, all = Sold(111, 16)
  SHIFT = false
  Check("with Shift held, the reason in full in the block", under[3]:find("Smooth Brain:", 1, true) ~= nil
    and under[4]:find("Buying them back costs", 1, true) ~= nil and under[5] == " " and #all == 5, Lines(all))
  ownLine = false   -- a game whose tooltip lines can't be reached: its own line recoloured instead
  under, all, raw = Sold(112, 400)
  Check("where the line can't be written, the game's own is recoloured: dimmed, as it lost", under[1] == " "
    and moneyFrame.hidden == false and moneyFrame.PrefixText.colour[1] == 0.5 and moneyFrame.GoldButton.Text.colour[1] == 0.6,
    table.concat(moneyFrame.PrefixText.colour, ","))
  under = Sold(111, 160)
  Check("...or bright, as it won", moneyFrame.PrefixText.colour[2] == 0.82 and moneyFrame.GoldButton.Text.colour[2] == 0.84
    and moneyFrame.CopperButton.Text.colour[1] == 0.93, table.concat(moneyFrame.PrefixText.colour, ","))
  GameTooltip.cleared(GameTooltip)
  Check("...and gets its own colours back when the tooltip is cleared", moneyFrame.PrefixText.colour[2] == 1
    and moneyFrame.GoldButton.Text.colour[3] == 1, table.concat(moneyFrame.PrefixText.colour, ","))
  ownLine = true
  SlashCmdList.SMOOTHBRAIN("pricelines off")
  under, all = Sold(111, 16)
  Check("/smooth pricelines off: the game's line as it was, and the verdict at the end as before", #under == 1 and under[1] == " "
    and moneyFrame.hidden == false and #all == 2 and all[2]:find("Vendor it", 1, true) ~= nil and SmoothBrainDB.pricelines == false,
    Lines(all))
  SlashCmdList.SMOOTHBRAIN("pricelines on")
  Check("/smooth pricelines on: back", Sold(111, 16)[2] == "[gavel] Auction Price: 19c")
end

-- Markers
local COIN, GAVEL, TICK = "Interface\\MoneyFrame\\UI-GoldIcon", "Interface\\AddOns\\SmoothBrain\\auction", "Interface\\RaidFrame\\ReadyCheck-Ready"
local QUEST, CROSS, DUST = "Interface\\GossipFrame\\AvailableQuestIcon", "Interface\\RaidFrame\\ReadyCheck-NotReady", 136244
local function Mark(button)
  local icon = button.SmoothBrainIcon
  return icon and icon.shown and icon.texture or nil
end
local meatSlot, hide, ichor, cloth, potion, leftover, plain, pick, bank = Button(0, 100), Button(0, 101), Button(0, 111), Button(0, 112),
  Button(0, 120), Button(0, 122), Button(0, 108), Button(0, 2901), Button(-1, 100)
for _, button in ipairs({ meatSlot, hide, ichor, cloth, potion, leftover, plain, pick, bank }) do button:Update() end
Check("Bagnon: coin on slots to vendor", Mark(meatSlot) == COIN and Mark(ichor) == COIN, tostring(Mark(ichor)))
Check("Bagnon: gavel to auction, tick to keep, ! for a quest, cross to delete", Mark(cloth) == GAVEL and Mark(potion) == TICK
  and Mark(hide) == QUEST and Mark(leftover) == CROSS, tostring(Mark(cloth)))
Check("Bagnon: no marker on tools, slots with no verdict, or the bank", Mark(plain) == nil and Mark(pick) == nil and Mark(bank) == nil)
local dustGloves, wornGloves = Button(0, 131), Button(0, 132)
dustGloves:Update()
wornGloves:Update()
Check("the Disenchant spell's picture on gear to disenchant, a coin on soulbound gear", Mark(dustGloves) == DUST and Mark(wornGloves) == COIN,
  tostring(Mark(dustGloves)))
ENCHANTER = true
Fire("SKILL_LINES_CHANGED")
Check("learning Enchanting: soulbound gear is to disenchant too", Verdict(132) == "disenchant/dust" and Mark(wornGloves) == DUST
  and ns.Check(132).byOther == nil, Verdict(132))
results[#results + 1] = ("INFO  tooltip, soulbound green gloves, as an enchanter:\n        %s"):format(Tip(132))
ENCHANTER = false
Fire("SKILL_LINES_CHANGED")
ContainerFrame1:UpdateItems()
Check("the game's own bags: every marker, none on the Mining Pick", Mark(modern[1]) == COIN and Mark(modern[2]) == GAVEL
  and Mark(modern[3]) == TICK and Mark(modern[4]) == QUEST and Mark(modern[5]) == CROSS and Mark(modern[6]) == nil, tostring(Mark(modern[1])))

-- Skills go up all the time while you play. Nothing is judged again for it,
-- unless it is Disenchant that was learned or lost.
do
  local asked = priceLookups
  Fire("SKILL_LINES_CHANGED")
  Fire("SPELLS_CHANGED")
  Check("a skill going up judges nothing afresh", priceLookups == asked and Mark(wornGloves) == COIN, priceLookups - asked)
  ENCHANTER = true
  Fire("SPELLS_CHANGED")
  Check("...learning Disenchant does, however the game announces it", Verdict(132) == "disenchant/dust" and Mark(wornGloves) == DUST
    and priceLookups > asked, Verdict(132))
  ENCHANTER = false
  Fire("SKILL_LINES_CHANGED")
  Check("...and so does losing it", Verdict(132) == "vendor/boundsell" and Mark(wornGloves) == COIN, Verdict(132))
end

-- Each price is a call into another addon, so only those that can change the
-- verdict are asked for.
do
  priceAsked = {}
  Fire("QUEST_ACCEPTED", 1, 1)
  SlashCmdList.SMOOTHBRAIN("all")   -- judges everything you carry, each item once
  printed = {}
  Check("a tradeable item with a price here: its price, how many are listed, what a vendor charges",
    priceAsked[111] == "dbminbuyout dbnumauctions vendorbuy", priceAsked[111])
  Check("...one with no price here: what it sells for across the region as well", priceAsked[117] ~= nil
    and priceAsked[117]:find("^dbminbuyout dbregionsaleavg vendorbuy") ~= nil, priceAsked[117])
  Check("...one to auction: how often its auctions sell, too", priceAsked[118] == "dbminbuyout dbnumauctions vendorbuy dbregionsalerate",
    priceAsked[118])
  Check("something soulbound: nothing, as it can't be sold or bought back", priceAsked[102] == nil and priceAsked[125] == nil
    and priceAsked[173] == nil and priceAsked[171] == nil, tostring(priceAsked[125]))
  Check("...unless it is gear: what disenchanting it would yield, and no more", priceAsked[132] == "destroy", priceAsked[132])
  Check("an item kept for the quest you are on, whatever it costs: nothing", Verdict(106) == "quest/onquest" and priceAsked[106] == nil,
    tostring(priceAsked[106]))
end

-- The game says which bag changed, and only that bag is read again.
do
  ns.Check(111)
  slotReads = {}
  BAGS[5][1][2] = 9                    -- the stack in the reagent bag grows
  Fire("BAG_UPDATE", 5)
  Fire("BAG_UPDATE_DELAYED")
  Check("a change in one bag has only that bag read again", ns.Check(170).count == 9 and slotReads[5] == #BAGS[5] and slotReads[0] == nil,
    tostring(slotReads[5]) .. "/" .. tostring(slotReads[0]))
  BAGS[5][2] = { 111, 7 }              -- Spider Ichor there as well as in the backpack
  Fire("BAG_UPDATE", 5)
  Fire("BAG_UPDATE_DELAYED")
  Check("an item is counted across your bags", ns.Check(111).count == 17 and Mark(ichor) == COIN, ns.Check(111).count)
  BAGS[5][2] = nil
  BAGS[5][1][2] = 4
  Fire("BAG_UPDATE", 5)
  Fire("BAG_UPDATE_DELAYED")
  Check("...and no longer once it has left one", ns.Check(111).count == 10 and ns.Check(170).count == 4, ns.Check(111).count)
  slotReads = {}
  Fire("BAG_UPDATE", 7)                -- a bag in the bank
  Fire("BAG_UPDATE_DELAYED")
  ns.Check(111)
  Check("a change in the bank has nothing read", next(slotReads) == nil, next(slotReads))
  BAGS[5][1][2] = 6
  Fire("BAG_UPDATE")                   -- no bag named
  Fire("BAG_UPDATE_DELAYED")
  Check("a change with no bag named has every bag read", ns.Check(170).count == 6 and slotReads[0] == #BAGS[0]
    and slotReads[5] == #BAGS[5], tostring(slotReads[0]))
  BAGS[5][1][2] = 4
  Fire("PLAYER_ENTERING_WORLD")
  Check("...and so does arriving somewhere", ns.Check(170).count == 4, ns.Check(170).count)
  -- The game hasn't said a bag changed, yet a slot shows something new.
  Fire("BAG_UPDATE", 3)                -- (an empty bag: any reading-again from earlier this second is forgotten)
  BAGS[0][12] = { 153, 2 }             -- where the Spider Ichor was
  ContainerFrame1:UpdateItems()
  Check("a slot holding something the bags weren't known to hold has them read again", Verdict(153) == "auction/costly"
    and Mark(modern[1]) == GAVEL and ns.Check(111) == nil, Verdict(153))
  BAGS[0][12] = { 111, 10 }
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
  Check("...and when the game does say, that is followed", Mark(modern[1]) == COIN and Verdict(153) == "nil" and ns.Check(111).count == 10,
    Verdict(153))
  -- An item is asked about in the slot it was last read in. If something
  -- else is there by now, it isn't judged until the bags have been read.
  local where
  for slot, stack in ipairs(BAGS[0]) do
    if stack[1] == 160 then where = slot end
  end
  local stack = BAGS[0][where]
  Fire("QUEST_ACCEPTED", 1, 1)         -- everything is to be judged afresh
  BAGS[0][where] = { 108, 1 }
  local result, later = ns.Check(160)
  Check("an item whose slot holds something else by now gets no verdict yet", result == nil and later == true, tostring(later))
  BAGS[0][where] = stack
  Check("...and the game's word on it is asked for once the slot is its own again", Verdict(160) == "quest/held", Verdict(160))
end
local widget = widgets.smooth_brain
Check("Baganator: one corner widget, starting bottom left", widget ~= nil and widget.label == "Smooth Brain"
  and widget.position.corner == "bottom_left")
local corner = widget.onInit({ CreateTexture = function() return Texture() end })
local function Corner(itemID, bag)
  corner.texture = nil
  local show = widget.onUpdate(corner, { itemID = itemID, itemLocation = { bagID = bag or 0, slotIndex = 1 } })
  return show, corner.texture
end
local function Shows(itemID, texture)
  local show, drawn = Corner(itemID)
  return show == true and drawn == texture
end
Check("Baganator: coin, gavel, dust, tick, ! and cross", Shows(111, COIN) and Shows(112, GAVEL) and Shows(131, DUST)
  and Shows(120, TICK) and Shows(101, QUEST) and Shows(122, CROSS))
Check("Baganator: nothing on tools or slots with no verdict", Corner(2901) == false and Corner(108) == false)
Check("Baganator: the ! on the game's own quest items", Shows(160, QUEST) and Shows(161, QUEST) and Shows(162, QUEST) and Shows(123, QUEST))
Check("Baganator: nothing in the bank", Corner(111, 6) == false and Corner(111, -1) == false)
Check("Baganator: the reagent bag is looked at too", Corner(170, 5) == true and corner.texture == COIN)
Check("Baganator: an item still loading is asked about again", Corner(998) == nil)
Check("Baganator: an empty slot", widget.onUpdate(corner, { itemLocation = { bagID = 0, slotIndex = 3 } }) == false)
local reagentSlot = GameSlot(5, 1)
modern[#modern + 1] = reagentSlot
ContainerFrame1:UpdateItems()
Check("the game's own bags: the reagent bag is looked at too", Mark(reagentSlot) == COIN, tostring(Mark(reagentSlot)))
ContainerFrame_Update(ContainerFrame2)
Check("the game's own bags on an older client", Mark(ContainerFrame2Item1) == COIN and Mark(ContainerFrame2Item2) == nil,
  tostring(Mark(ContainerFrame2Item1)))

-- BetterBags
local function Glows(button) return button.SmoothBrainFlash ~= nil and button.SmoothBrainFlash.shown == true end
Check("BetterBags: a slot it drew before login has its marker", Mark(bbEarlyButton) == GAVEL, tostring(Mark(bbEarlyButton)))
local bbIchor, bbIchorButton = BBSlot(0, 12)
local bbCloth, bbClothButton = BBSlot(0, 13)
local bbLeftover, bbLeftoverButton = BBSlot(0, 24)
local bbPick, bbPickButton = BBSlot(0, 22)
local bbBank, bbBankButton = BBSlot(-1, 12)
bbBank.currentData.itemInfo, bbBank.currentData.isItemEmpty = { itemID = 111 }, false
local bbFree, bbFreeButton = BBSlot(0, 99)
bbFree.isFreeSlot = true
for _, pair in ipairs({ { bbIchor, bbIchorButton }, { bbCloth, bbClothButton }, { bbLeftover, bbLeftoverButton },
  { bbPick, bbPickButton }, { bbBank, bbBankButton }, { bbFree, bbFreeButton } }) do
  BBDraw(pair[1], pair[2])
end
Check("BetterBags: coin, gavel and cross on the slots it draws", Mark(bbIchorButton) == COIN and Mark(bbClothButton) == GAVEL
  and Mark(bbLeftoverButton) == CROSS, tostring(Mark(bbIchorButton)))
Check("...top right, clear of the item level it writes bottom left", bbIchorButton.SmoothBrainIcon.point == "TOPRIGHT"
  and meatSlot.SmoothBrainIcon.point == "BOTTOMLEFT", bbIchorButton.SmoothBrainIcon.point)
Check("BetterBags: nothing on tools, the bank or free slots", Mark(bbPickButton) == nil and Mark(bbBankButton) == nil
  and Mark(bbFreeButton) == nil)
SlashCmdList.SMOOTHBRAIN("limit 20c")
Check("BetterBags: a changed verdict repaints the slot, though BetterBags draws nothing", Mark(bbIchorButton) == GAVEL,
  tostring(Mark(bbIchorButton)))
SlashCmdList.SMOOTHBRAIN("limit 5s")
-- The Spider Ichor leaves slot 12 and the cloth takes its place; BetterBags has not redrawn yet.
local ichorStack = BAGS[0][12]
BAGS[0][12] = BAGS[0][13]
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
Check("BetterBags: a slot whose item changed loses its marker until BetterBags draws it again", Mark(bbIchorButton) == nil)
bbIchor.currentData.itemInfo = { itemID = 112 }
BBDraw(bbIchor, bbIchorButton)
Check("...and then shows the new item's", Mark(bbIchorButton) == GAVEL)
BAGS[0][12] = ichorStack
bbIchor.currentData.itemInfo = { itemID = 111 }
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
BBDraw(bbIchor, bbIchorButton)
Check("...and the old one's when it is back", Mark(bbIchorButton) == COIN)
-- Bags full. A second stack of the leftover sits in a new slot; only the first is among the three to flash.
BAGS[0][#BAGS[0] + 1] = { 122, 1 }
local extra = #BAGS[0]
local bbSecond, bbSecondButton = BBSlot(0, extra)
local bbMerged, bbMergedButton = BBSlot(0, extra, true)
BBDraw(bbSecond, bbSecondButton)
BBDraw(bbMerged, bbMergedButton)
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
Check("BetterBags: the stack to throw away flashes", Glows(bbLeftoverButton) and not Glows(bbIchorButton) and not Glows(bbClothButton))
Check("...another stack of that item doesn't, unless its button stands for all of them", not Glows(bbSecondButton)
  and Glows(bbMergedButton))
RunTimers()
Check("...and it stops by itself", not Glows(bbLeftoverButton) and not Glows(bbMergedButton))
bbListeners["item/Clearing"]({}, bbSecond, bbSecondButton)
bbListeners["item/Clearing"]({}, bbMerged, bbMergedButton)
BAGS[0][extra] = nil
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
bbListeners["item/Clearing"]({}, bbCloth, bbClothButton)
Check("BetterBags: a slot it takes away loses its marker", Mark(bbClothButton) == nil)
-- A slot of a shape this wasn't written for: BetterBags must be able to go on drawing.
local reported
geterrorhandler = function() return function(mistake) reported = mistake end end
local okDraw = pcall(BBDraw, setmetatable({}, { __index = function() error("changed") end }), bbClothButton)
Check("BetterBags: a mistake while it draws is reported, not thrown back at it", okDraw and reported ~= nil, tostring(reported))
geterrorhandler = nil
SlashCmdList.SMOOTHBRAIN("limit 20c")
SlashCmdList.SMOOTHBRAIN("limit 5s")
Check("...and is left alone from then on", Mark(bbClothButton) == nil and Mark(bbIchorButton) == COIN)

-- EllesmereUI
Check("EllesmereUI: its painter is registered, and bags that were already open are drawn again, once",
  type(EUI_Bags.itemOverlayIcons.SmoothBrain) == "function" and euiRedraws == 1, euiRedraws)
local euiIchor, euiIchorOverlay, euiIchorWritten = EUISlot()
local euiCloth, euiClothOverlay = EUISlot()
local euiLeftover, euiLeftoverOverlay, euiLeftoverWritten = EUISlot()
local euiPick, euiPickOverlay = EUISlot()
local euiBank, euiBankOverlay = EUISlot()
local euiPlaceholder, euiPlaceholderOverlay = EUISlot()
EUIDraw(euiIchor, EUIData(0, 12))
EUIDraw(euiCloth, EUIData(0, 13))
EUIDraw(euiLeftover, EUIData(0, 24))
EUIDraw(euiPick, EUIData(0, 22))
EUIDraw(euiBank, { bag = 6, slot = 12, info = { itemID = 111 } })
EUIDraw(euiPlaceholder, { bag = 0, slot = 0 })
Check("EllesmereUI: coin, gavel and cross on the slots it draws", EUIMark(euiIchorOverlay) == COIN and EUIMark(euiClothOverlay) == GAVEL
  and EUIMark(euiLeftoverOverlay) == CROSS, tostring(EUIMark(euiIchorOverlay)))
local euiPoints = euiIchorOverlay.made[1] and euiIchorOverlay.made[1].points or {}
Check("...on the frame over the item's picture, as its top right quarter, with nothing written onto the button",
  #euiIchorWritten == 0 and #euiIchorOverlay.made == 1 and euiPoints[1] == "TOPRIGHT" and euiPoints[2] == "BOTTOMLEFT",
  table.concat(euiIchorWritten, ",") .. " / " .. table.concat(euiPoints, ","))
Check("EllesmereUI: nothing on tools, the bank or placeholder slots", EUIMark(euiPickOverlay) == nil and EUIMark(euiBankOverlay) == nil
  and EUIMark(euiPlaceholderOverlay) == nil)
SlashCmdList.SMOOTHBRAIN("limit 20c")
Check("EllesmereUI: a changed verdict repaints the slot, though EllesmereUI draws nothing", EUIMark(euiIchorOverlay) == GAVEL,
  tostring(EUIMark(euiIchorOverlay)))
SlashCmdList.SMOOTHBRAIN("limit 5s")
-- The Spider Ichor leaves slot 12 and the cloth takes its place; EllesmereUI has not redrawn yet.
ichorStack = BAGS[0][12]
BAGS[0][12] = BAGS[0][13]
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
Check("EllesmereUI: a slot whose item changed loses its marker until EllesmereUI draws it again", EUIMark(euiIchorOverlay) == nil)
EUIDraw(euiIchor, EUIData(0, 12))
Check("...and then shows the new item's", EUIMark(euiIchorOverlay) == GAVEL)
BAGS[0][12] = ichorStack
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
EUIDraw(euiIchor, EUIData(0, 12))
Check("...and the old one's when it is back", EUIMark(euiIchorOverlay) == COIN)
-- Its buttons are reused: the one that showed the cloth now shows an empty slot, then the cloth again.
EUIDraw(euiCloth, EUIData(0, 99))
local euiEmptied = EUIMark(euiClothOverlay)
EUIDraw(euiCloth, EUIData(0, 13))
Check("EllesmereUI: a button reused for an empty slot loses its marker, and gets it back with an item", euiEmptied == nil
  and EUIMark(euiClothOverlay) == GAVEL and #euiClothOverlay.made == 1)
-- Bags full. A second stack of the leftover sits in a new slot; only the first is among the three to flash.
BAGS[0][#BAGS[0] + 1] = { 122, 1 }
extra = #BAGS[0]
local euiSecond, euiSecondOverlay = EUISlot()
local euiRow, euiRowOverlay = EUISlot()
EUIDraw(euiSecond, EUIData(0, extra))
EUIDraw(euiRow, EUIData(0, extra, true))
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
Check("EllesmereUI: the stack to throw away flashes", EUIGlows(euiLeftoverOverlay) and not EUIGlows(euiIchorOverlay)
  and not EUIGlows(euiClothOverlay) and #euiLeftoverWritten == 0)
Check("...another stack of that item doesn't, unless it is a list row standing for all of them", not EUIGlows(euiSecondOverlay)
  and EUIGlows(euiRowOverlay))
RunTimers()
Check("...and it stops by itself", not EUIGlows(euiLeftoverOverlay) and not EUIGlows(euiRowOverlay))
BAGS[0][extra] = nil
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
Check("EllesmereUI: a stack that is gone loses its marker", EUIMark(euiSecondOverlay) == nil and EUIMark(euiRowOverlay) == nil)
Check("EllesmereUI: a button with no picture frame, or a call with nothing to go on, is left alone",
  pcall(EUIDraw, {}, EUIData(0, 12)) and pcall(EUIDraw, euiPick, nil) and pcall(EUIDraw, nil, nil))
Fire("ADDON_LOADED", "EllesmereUIBags")
Check("EllesmereUI: it is asked only once", euiRedraws == 1, euiRedraws)

printed = {}
SlashCmdList.SMOOTHBRAIN("")
results[#results + 1] = "INFO  /smooth:\n        " .. table.concat(printed, "\n        ")
local listed = table.concat(printed, "\n")
Check("/smooth lists what to vendor or delete, and only that", listed:find("Item111", 1, true) ~= nil and listed:find("Item100", 1, true) ~= nil
  and listed:find("Item122", 1, true) ~= nil and listed:find("Item101", 1, true) == nil and listed:find("Item112", 1, true) == nil
  and listed:find("Item2901", 1, true) == nil and listed:find("Item131", 1, true) == nil and listed:find("Item140", 1, true) ~= nil and listed:find("Item170", 1, true) ~= nil and listed:find("Item180", 1, true) ~= nil and #printed == 21, #printed)
Check("...with what vendoring pays and how many others there are", printed[#printed - 1]:find("pays 24s 44c", 1, true) ~= nil
  and printed[#printed]:find("/smooth all also lists the 29", 1, true) ~= nil, printed[#printed - 1])
printed = {}
SlashCmdList.SMOOTHBRAIN("all")
Check("/smooth all lists every item judged", #printed == 49, #printed)

-- Whose prices
printed = {}
SlashCmdList.SMOOTHBRAIN("prices auctionator")
Check("/smooth prices auctionator: its price for Spider Ichor, and nothing for items it never saw", SmoothBrainDB.prices == "auctionator"
  and ns.Check(111).price == 25 and ns.Check(111).seen == 0 and Verdict(112) == "nil", printed[1])
SlashCmdList.SMOOTHBRAIN("prices tsm")
Check("/smooth prices tsm: nothing for items only Auctionator knows", ns.Check(111).price == 19 and Verdict(140) == "nil"
  and Verdict(145) == "nil")
printed = {}
SlashCmdList.SMOOTHBRAIN("prices mine")
Check("an unknown choice is refused", SmoothBrainDB.prices == "tsm" and printed[1]:find("tsm, auctionator or both", 1, true) ~= nil, printed[1])
SlashCmdList.SMOOTHBRAIN("prices both")
Check("/smooth prices both: back to both", Verdict(140) == "vendor/cheap" and ns.Check(111).price == 19)
ATR.price[140] = 400
Check("a scan changes Auctionator's price: nothing happens until it reports", Verdict(140) == "vendor/cheap")
atrChanged()
Check("...nor until the scan has settled", Verdict(140) == "vendor/cheap")
RunTimers()
Check("...then the verdict follows", Verdict(140) == "auction/costly" and atrChanged ~= nil, Verdict(140))
ATR.price[140] = 14
atrChanged()
RunTimers()

-- Forever Companion notes the prices the auction house shows you, to the
-- second. Whoever saw an item last is believed. Here TradeSkillMaster's
-- snapshot has no time of its own, so it counts as an hour older than the
-- login; Auctionator's days have no start, so "today" counts as a day ago.
do
  local NOTED, now = {}, os.time()
  ForeverCompanion = { GetAuctionEntry = function(self, id)
    assert(self == ForeverCompanion and type(id) == "number", "Forever Companion wants itself and an item number")
    return NOTED[id]
  end }
  local function Seen(event)
    Fire(event or "AUCTION_HOUSE_BROWSE_RESULTS_UPDATED")
    RunTimers()
  end
  NOTED[111] = { m = 30, q = 500, t = now - 60 }           -- a minute ago; TradeSkillMaster says 19, 112 listed
  NOTED[112] = { m = 9999, q = 5, t = now - 2 * 3600 }     -- two hours ago; TradeSkillMaster says 25s
  NOTED[143] = { m = 50, q = 3, t = now - 3 * 86400 }      -- three days ago; nobody else has a price with an age
  NOTED[140] = { m = 400, q = 9, t = now - 2 * 86400 }     -- two days ago; Auctionator saw it today at 14c
  Check("a price Forever Companion noted isn't used until the auction house has shown something", ns.Check(111).price == 19)
  Fire("AUCTION_HOUSE_BROWSE_RESULTS_UPDATED")
  Check("...nor until that has settled", ns.Check(111).price == 19)
  RunTimers()
  Check("Forever Companion's price from the last hour replaces TradeSkillMaster's, with its own count", ns.Check(111).price == 30
    and ns.Check(111).listed == 500 and ns.Check(111).seen == nil and ns.Check(111).seenBy == nil
    and ns.Explain(ns.Check(111), ns.Money):find("(500 listed)", 1, true) ~= nil, ns.Explain(ns.Check(111), ns.Money))
  Check("...one from before TradeSkillMaster's snapshot doesn't", ns.Check(112).price == 2500 and ns.Check(112).listed == 80, ns.Check(112).price)
  Check("...but fills in what TradeSkillMaster lacks, and says who saw it when", ns.Check(143).price == 50
    and ns.Check(143).seen == 3 and ns.Check(143).seenBy == "Forever Companion"
    and ns.Explain(ns.Check(143), ns.Money):find("(Forever Companion saw it 3 days ago)", 1, true) ~= nil,
    ns.Check(143) and ns.Explain(ns.Check(143), ns.Money))
  Check("...unless Auctionator saw the item more recently", ns.Check(140).price == 14 and ns.Check(140).seen == 0
    and ns.Check(140).seenBy == "Auctionator", ns.Check(140).price)
  NOTED[140] = { m = 400, q = 9, t = now - 60 }
  Seen("COMMODITY_SEARCH_RESULTS_UPDATED")
  Check("seen within the hour, it is taken over Auctionator's too", ns.Check(140).price == 400 and ns.Check(140).listed == 9
    and ns.Check(140).seen == nil, ns.Check(140).price)
  NOTED[140] = nil
  NOTED[111] = { m = 30, t = now - 60 }
  NOTED[143] = { m = 50, t = now - 60 }
  Seen("AUCTION_HOUSE_CLOSED")
  Check("where it took no count, TradeSkillMaster's stands in", ns.Check(111).price == 30 and ns.Check(111).listed == 112,
    ns.Check(111).listed)
  Check("...and with no count anywhere, it says it was seen today", ns.Check(143).seen == 0 and ns.Check(143).listed == nil
    and ns.Explain(ns.Check(143), ns.Money):find("(Forever Companion saw it today)", 1, true) ~= nil,
    ns.Explain(ns.Check(143), ns.Money))
  NOTED[143] = { m = 50, q = 3, t = now - 30 * 86400 }
  Seen()
  Check("a price it last saw over three weeks ago is no price", Verdict(143) == "nil", Verdict(143))
  NOTED[143] = { m = 0, t = now }
  NOTED[2589] = { m = 27, q = 40, t = now - 2 * 86400 }
  Seen()
  Check("an entry with no price is passed over", Verdict(143) == "nil", Verdict(143))
  local found = ns.Detect()
  Check("the setup window's check counts its prices", found.companion.installed and found.companion.priced == 1
    and found.companion.newest == 2, found.companion.priced)
  -- Forever Companion alone
  local tsmWas, auctionatorWas = TSM_API, Auctionator
  TSM_API, Auctionator = nil, nil
  Fire("QUEST_ACCEPTED", 1, 1)
  found = ns.Detect()
  local state = ns.Setup.Verdict(found)
  Check("with no other price addon its prices do", ns.Check(111).price == 30 and ns.Check(111).seen == 0
    and ns.Check(111).seenBy == "Forever Companion" and Verdict(100) ~= "quest/noprices" and state == true, Verdict(100))
  printed = {}
  SlashCmdList.SMOOTHBRAIN("companion off")
  Check("/smooth companion off: its prices are left alone", SmoothBrainDB.companion == false and Verdict(111) == "nil"
    and Verdict(100) == "quest/noprices" and ns.Setup.Verdict(ns.Detect()) == false
    and printed[1]:find("Forever Companion's price when it is the newest: off", 1, true) ~= nil, printed[1])
  TSM_API, Auctionator = tsmWas, auctionatorWas
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("...and TradeSkillMaster's price is back", ns.Check(111).price == 19 and ns.Check(111).listed == 112)
  Fire("AUCTION_HOUSE_BROWSE_RESULTS_UPDATED")
  Check("...and the auction house no longer has everything judged afresh", #timers == 0, #timers)
  SlashCmdList.SMOOTHBRAIN("companion on")
  Check("/smooth companion on: back at once", SmoothBrainDB.companion == true and ns.Check(111).price == 30)
  NOTED[111] = { m = "30", t = now }
  ForeverCompanion.GetAuctionEntry = function(self, id)
    if id == 112 then error("Forever Companion broke") end
    return NOTED[id]
  end
  Seen()
  Check("an entry that isn't what was expected, or an error in Forever Companion, changes nothing", ns.Check(111).price == 19
    and ns.Check(112).price == 2500)
  ForeverCompanion = nil
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("without Forever Companion everything is as before", ns.Check(111).price == 19 and ns.Check(140).price == 14
    and ns.Detect().companion.installed == false)
end

-- Whoever saw an item for sale last is believed, with each addon's own time:
-- TradeSkillMaster's from its app's data, Forever Companion's to the second,
-- Auctionator's to the day. Spider Ichor: TradeSkillMaster says 19c (112
-- listed), Auctionator saw it today at 25c.
do
  local now, DAY = os.time(), 86400
  local NOTED = {}
  ForeverCompanion = { GetAuctionEntry = function(self, id) return NOTED[id] end }
  local function Again()   -- everything is judged afresh, with the clocks as they now stand
    Fire("QUEST_ACCEPTED", 1, 1)
  end
  local function Ichor()
    local result = ns.Check(111)
    return result.price .. "/" .. tostring(result.listed) .. "/" .. tostring(result.seen) .. "/" .. tostring(result.seenBy)
  end
  local function AppData(realm, at, fields, tag)
    TSM_APPHELPER_LOAD_DATA(tag or "AUCTIONDB_NON_COMMODITY_DATA", realm, "return {downloadTime=" .. at .. ",fields={"
      .. (fields or '"itemString","minBuyout","numAuctions","marketValueRecent"') .. "},data={{111,J,34,J}}}")
  end
  Check("TradeSkillMaster's loader is listened in on, not replaced", TSM_APPHELPER_LOAD_DATA ~= tsmLoader and #tsmGot == 0)
  AppData("Somewhere-Alliance", now - 1800)   -- its snapshot is half an hour old
  Check("...what its app brings reaches it as it was sent", #tsmGot == 1 and tsmGot[1][1] == "AUCTIONDB_NON_COMMODITY_DATA"
    and tsmGot[1][2] == "Somewhere-Alliance" and tsmGot[1][3]:find("downloadTime=" .. (now - 1800), 1, true) ~= nil, #tsmGot)
  NOTED[111] = { m = 30, q = 500, t = now - 1200 }
  Again()
  Check("Forever Companion saw it twenty minutes ago, after the snapshot: its price", Ichor() == "30/500/nil/nil", Ichor())
  NOTED[111] = { m = 30, q = 500, t = now - 2400 }
  Again()
  Check("...forty minutes ago, before it: TradeSkillMaster's, though that was within the hour", Ichor() == "19/112/nil/nil", Ichor())
  AppData("Somewhere-Alliance", now - 5 * 3600)   -- a long evening with no /reload: the snapshot is five hours old
  NOTED[111] = { m = 30, q = 500, t = now - 2 * 3600 }
  Again()
  Check("an old snapshot loses to what Forever Companion saw two hours ago, which says when that was",
    Ichor() == "30/nil/0/Forever Companion", Ichor())
  NOTED[111] = nil
  Again()
  Check("Auctionator's \"today\" with no telling when its day began: TradeSkillMaster's", Ichor() == "19/112/nil/nil", Ichor())
  -- Auctionator's days start at its own midnight: here, six hours ago.
  Auctionator.Constants = { SCAN_DAY_0 = now - 6 * 3600 - 1000 * DAY }
  Again()
  Check("its day began before the snapshot was taken, so the snapshot may well be newer: TradeSkillMaster's",
    Ichor() == "19/112/nil/nil", Ichor())
  AppData("Somewhere-Alliance", now - 8 * 3600)
  Again()
  Check("a snapshot from before its day began is older for certain: Auctionator's", Ichor() == "25/nil/0/Auctionator", Ichor())
  -- Auctionator stamps a scan when it starts, whether or not it reaches the
  -- item. The case reported: Raw Winter Squid, 25s from an afternoon scan,
  -- taken over a TradeSkillMaster snapshot from that evening because another
  -- scan had been started since.
  AppData("Somewhere-Alliance", now - 5 * 3600)
  Auctionator.SavedState = { TimeOfLastBrowseScan = now - 3600, TimeOfLastGetAllScan = now - 3600, TimeOfLastReplicateScan = now - 3600 }
  Again()
  Check("a scan Auctionator started since the snapshot says nothing of when it saw this item: TradeSkillMaster's",
    Ichor() == "19/112/nil/nil", Ichor())
  ATR.age[111] = 1
  Again()
  Check("...and an item it last saw yesterday is older still", Ichor() == "19/112/nil/nil", Ichor())
  NOTED[111] = { m = 30, q = 500, t = now - 20 * 3600 }
  AppData("Somewhere-Alliance", now - 3 * DAY)
  Again()
  Check("Forever Companion saw it yesterday too, at a known hour: its price over Auctionator's", Ichor() == "30/nil/0/Forever Companion", Ichor())
  NOTED[111] = nil
  Again()
  Check("...and without it, Auctionator's from yesterday over a snapshot three days old", Ichor() == "25/nil/1/Auctionator", Ichor())
  ATR.age[111] = 0
  AppData("Somewhere-Alliance", now - 8 * 3600)   -- your realm's snapshot: from before Auctionator's day began
  -- The app may bring several realms' prices
  AppData("Elsewhere-Horde", now - 60)
  Again()
  Check("another realm's snapshot, when the game doesn't say which is yours: the newest is taken", Ichor() == "19/112/nil/nil", Ichor())
  function GetRealmName() return "Somewhere" end
  function UnitFactionGroup(unit) return unit == "player" and "Alliance" or nil end
  Again()
  Check("...when it does, your own realm's", Ichor() == "25/nil/0/Auctionator", Ichor())
  AppData("Forever-US", now, '"itemString","regionMarketValue"', "AUCTIONDB_REGION_STAT")
  AppData("Somewhere-Alliance", now, '"itemString","historical"', "AUCTIONDB_NON_COMMODITY_HISTORICAL")
  Again()
  Check("data without the lowest buyouts in it says nothing about their age", Ichor() == "25/nil/0/Auctionator", Ichor())
  local got = #tsmGot
  local ok = pcall(TSM_APPHELPER_LOAD_DATA, "APP_INFO", nil, nil)
  Check("something unexpected from the app breaks nothing, and still reaches TradeSkillMaster", ok and #tsmGot == got + 1)
  SlashCmdList.SMOOTHBRAIN("prices tsm")
  Check("/smooth prices tsm: TradeSkillMaster's, however old", Ichor() == "19/112/nil/nil", Ichor())
  SlashCmdList.SMOOTHBRAIN("prices both")
  printed = {}
  SlashCmdList.SMOOTHBRAIN("prices")
  Check("/smooth prices says how the two are chosen between", printed[1] ~= nil and printed[1]:find("whichever saw it for sale last", 1, true) ~= nil,
    printed[1])
  -- Back to how it was: TradeSkillMaster's snapshot the newest of all
  GetRealmName, UnitFactionGroup = nil, nil
  Auctionator.Constants, Auctionator.SavedState = nil, nil
  ForeverCompanion = nil
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("...and all is as before", Ichor() == "19/112/nil/nil" and ns.Check(140).price == 14, Ichor())
end

-- Prices are noted anew while you play: by Forever Companion as the auction
-- house shows them, by Auctionator as it scans. Only the items they are for
-- are judged again, and nothing else is read again for it.
do
  local NOTED, now = {}, os.time()
  ForeverCompanion = { GetAuctionEntry = function(self, id) return NOTED[id] end }
  Fire("QUEST_ACCEPTED", 1, 1)
  SlashCmdList.SMOOTHBRAIN("all")   -- everything you carry is judged
  printed = {}
  local logReads, GetInfo = 0, C_QuestLog.GetInfo
  C_QuestLog.GetInfo = function(...)
    logReads = logReads + 1
    return GetInfo(...)
  end
  local function Seen()
    Fire("AUCTION_HOUSE_BROWSE_RESULTS_UPDATED")
    RunTimers()
  end
  local function Scanned()
    atrChanged()
    RunTimers()
  end
  local function Others(itemID)   -- how many items other than this one were priced again
    local others = 0
    for id in pairs(priceAsked) do
      if id ~= itemID then others = others + 1 end
    end
    return others
  end
  priceAsked = {}
  Seen()
  Check("the auction house shows something, and Forever Companion has noted nothing new: nothing is judged again",
    next(priceAsked) == nil and logReads == 0, next(priceAsked))
  NOTED[111] = { m = 30, q = 500, t = now - 30 }   -- half a minute ago: after TradeSkillMaster's snapshot
  Seen()
  Check("it has noted one item's price: that item is judged again", ns.Check(111).price == 30 and ns.Check(111).listed == 500
    and priceAsked[111] ~= nil, ns.Check(111).price)
  Check("...and no other, nor is your quest log read again", Others(111) == 0 and logReads == 0, Others(111))
  priceAsked = {}
  Seen()
  Check("...and not a second time for the same note", next(priceAsked) == nil, next(priceAsked))
  NOTED[111] = { m = 30, q = 480, t = now - 10 }
  Seen()
  Check("a later note of the same price, with another count, is followed too", ns.Check(111).listed == 480 and Others(111) == 0,
    ns.Check(111).listed)
  NOTED[111] = nil
  Seen()
  Check("...and so is its note going", ns.Check(111).price == 19 and ns.Check(111).listed == 112, ns.Check(111).price)
  -- Auctionator
  priceAsked = {}
  Scanned()
  Check("Auctionator reports, with no price of yours changed: nothing is judged again", next(priceAsked) == nil, next(priceAsked))
  ATR.price[140] = 400
  Scanned()
  Check("its scan changed one price: that item is judged again, and no other", Verdict(140) == "auction/costly" and Others(140) == 0
    and logReads == 0, Others(140))
  ATR.price[140] = 14
  ATR.dust[145] = 100   -- what its gloves disenchant into is worth less after the scan
  priceAsked = {}
  Scanned()
  local cheap, gloves = Verdict(140), Verdict(145)   -- neither is on a slot that shows: they are judged when asked
  Check("...and when it moved what gear disenchants into, that gear", cheap == "vendor/cheap" and gloves == "vendor/nodust"
    and priceAsked[145] ~= nil and Others(145) == 1, gloves)
  ATR.dust[145] = 3000
  Scanned()
  Check("...both ways", Verdict(145) == "disenchant/dust", Verdict(145))
  -- Auctionator starting a scan moves nothing by itself: its "today" counts
  -- as seen when its day began (here six hours ago), scan or no scan.
  Auctionator.Constants = { SCAN_DAY_0 = now - 6 * 3600 - 1000 * 86400 }
  Fire("QUEST_ACCEPTED", 1, 1)
  local before = ns.Check(111).price
  Auctionator.SavedState = { TimeOfLastBrowseScan = os.time() }
  priceAsked = {}
  Scanned()
  Check("a scan Auctionator has just started doesn't make its price from earlier today the newest", before == 19
    and ns.Check(111).price == 19 and next(priceAsked) == nil, ns.Check(111).price)
  Auctionator.Constants, Auctionator.SavedState = nil, nil
  ForeverCompanion = nil
  C_QuestLog.GetInfo = GetInfo
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("...and all is as before", ns.Check(111).price == 19 and ns.Check(140).price == 14, ns.Check(111).price)
end

-- Bags full: the stacks you'd lose least by deleting flash
local function Glows(button) return button.SmoothBrainFlash ~= nil and button.SmoothBrainFlash.shown == true end
local leftoverSlot, junkSlot, ichorSlot, hideSlot = Button(0, 122, 24), Button(0, 113, 14), Button(0, 111, 12), Button(0, 101, 2)
for _, button in ipairs({ leftoverSlot, junkSlot, ichorSlot, hideSlot }) do button:Update() end
local dropWidget = widgets.smooth_brain_drop
local dropCorner = dropWidget and dropWidget.onInit({ CreateTexture = function() return Texture() end })
local function Drops(slot)
  return dropWidget.onUpdate(dropCorner, { itemID = BAGS[0][slot][1], itemLocation = { bagID = 0, slotIndex = slot } })
end
Check("nothing flashes while there is room", not Glows(leftoverSlot) and not Glows(modern[5]) and Drops(24) == false)
Fire("UI_ERROR_MESSAGE", 99, "You can't do that yet.")
Check("another error message changes nothing", not Glows(leftoverSlot))
Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
Check("bags full: the three leftovers flash, worth nothing", Glows(leftoverSlot) and Glows(modern[5]) and Drops(24) == true
  and Drops(26) == true and Drops(29) == true)
Check("...as a solid red wash, hard to miss", leftoverSlot.SmoothBrainFlash.colour[1] == 1 and leftoverSlot.SmoothBrainFlash.colour[4] >= 0.5)
Check("...and nothing else does, however cheap", not Glows(junkSlot) and not Glows(ichorSlot) and not Glows(hideSlot)
  and Drops(14) == false and Drops(12) == false)
RunTimers()
Check("...and it stops by itself after a while", not Glows(leftoverSlot) and Drops(24) == false)
Fire("UI_ERROR_MESSAGE", ERR_INV_FULL)
Check("an older client sends the message alone", Glows(leftoverSlot))
-- Someone moves things while it flashes: the stack in slot 24 swaps places with the hide in slot 2.
BAGS[0][24], BAGS[0][2] = BAGS[0][2], BAGS[0][24]
leftoverSlot.itemID, hideSlot.itemID = 101, 122
leftoverSlot:Update()
hideSlot:Update()
Check("the flash stays with the stack, not the slot, when items are moved", not Glows(leftoverSlot) and Drops(24) == false)
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
Check("...and after the bags settle it is on the stack's new slot", Glows(hideSlot) and Drops(2) == true and not Glows(leftoverSlot))
BAGS[0][24], BAGS[0][2] = BAGS[0][2], BAGS[0][24]
leftoverSlot.itemID, hideSlot.itemID = 122, 101
leftoverSlot:Update()
hideSlot:Update()
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
FREE_SLOTS = 1
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
Check("making room stops it at once", not Glows(leftoverSlot))
FREE_SLOTS = 0
Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
Check("room in the quiver is not room: it keeps flashing", Glows(leftoverSlot))
RunTimers()
FREE_SLOTS = 0
RunTimers()
-- Without the leftovers, the cheapest stacks to vendor come next: 5c, then 24c, then 30c (two of them: slot order decides).
for _, id in ipairs({ 122, 124, 127, 180 }) do SmoothBrainDB.ignore[id] = true end
printed = {}
SlashCmdList.SMOOTHBRAIN("drop")
results[#results + 1] = "INFO  /smooth drop:\n        " .. table.concat(printed, "\n        ")
Check("/smooth drop lists the three cheapest stacks to vendor", #printed == 4 and printed[2]:find("Item144", 1, true) ~= nil
  and printed[2]:find("worth 5c", 1, true) ~= nil and printed[3]:find("Item105", 1, true) ~= nil and printed[4]:find("Item113", 1, true) ~= nil,
  printed[2])
Check("...and they flash; stacks to keep for a quest never do", Glows(junkSlot) and not Glows(leftoverSlot) and not Glows(hideSlot)
  and Drops(14) == true and Drops(2) == false)
RunTimers()
-- Looting: is what lies in the loot window worth throwing something away for?
local function Loot(...)
  LOOT = { ... }
  Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
  local flashing = { Drops(39) == true, Drops(6) == true, Drops(14) == true }   -- the 5c, 24c and 30c stacks
  RunTimers()
  return (flashing[1] and "5c " or "") .. (flashing[2] and "24c " or "") .. (flashing[3] and "30c" or "")
end
Check("loot worth 3c: nothing in the bags is worth less, so nothing flashes", Loot({ 150, 1 }) == "", Loot({ 150, 1 }))
Check("loot worth 20c: only the 5c stack flashes", Loot({ 151, 1 }) == "5c ", Loot({ 151, 1 }))
Check("ten of them, 2s together: all three flash", Loot({ 151, 10 }) == "5c 24c 30c", Loot({ 151, 10 }))
Check("a quest item worth nothing: the cheapest flash anyway", Loot({ 152, 1, true }) == "5c 24c 30c")
Check("...also when the game doesn't flag it but it is one", Loot({ 152, 1 }) == "5c 24c 30c")
Check("...and when a RestedXP guide needs it for a quest", Loot({ 101, 1 }) == "5c 24c 30c")
Check("worth 1c to a vendor but 5s at auction: counts as 5s", Loot({ 153, 1 }) == "5c 24c 30c")
Check("...unless it binds when picked up: then only the vendor counts", Loot({ 154, 1 }) == "")
Check("several things lying there: the most valuable decides", Loot({ 150, 1 }, { 151, 1 }) == "5c ")
LOOT = {}
Check("no loot window (a vendor, a quest reward): the cheapest flash", Loot() == "5c 24c 30c")
SlashCmdList.SMOOTHBRAIN("flash off")
Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
Check("/smooth flash off: full bags flash nothing", not Glows(junkSlot) and SmoothBrainDB.flash == false)
SlashCmdList.SMOOTHBRAIN("flash on")
for _, id in ipairs({ 122, 124, 127, 180 }) do SmoothBrainDB.ignore[id] = nil end
Fire("QUEST_ACCEPTED", 1, 1)

printed = {}
SlashCmdList.SMOOTHBRAIN("limit 1s")
Check("/smooth limit 1s", SmoothBrainDB.limit == 100 and Verdict(100) == "quest/costly" and Verdict(111) == "vendor/cheap", printed[1])
Check("...and the coin turns into a quest mark, in every kind of bag", Mark(meatSlot) == QUEST and Mark(ichor) == COIN
  and Mark(modern[1]) == COIN, tostring(Mark(meatSlot)))
SlashCmdList.SMOOTHBRAIN("limit 20c")
Check("/smooth limit 20c: even Spider Ichor goes to auction", Verdict(111) == "auction/costly" and Mark(ichor) == GAVEL
  and Mark(modern[1]) == GAVEL and Mark(ContainerFrame2Item1) == GAVEL)
SlashCmdList.SMOOTHBRAIN("limit 5s")
Check("...and back at 5s", Mark(meatSlot) == COIN and Verdict(100) == "vendor/cheap" and Mark(ichor) == COIN)
printed = {}
SlashCmdList.SMOOTHBRAIN("limit lots")
Check("a limit that isn't money is refused", SmoothBrainDB.limit == 500 and printed[1]:find("couldn't read", 1, true) ~= nil, printed[1])
local before = redraws
SlashCmdList.SMOOTHBRAIN("icons off")
Check("/smooth icons off", Mark(meatSlot) == nil and Mark(hide) == nil and Mark(modern[1]) == nil and Corner(111) == false)
Check("...and Baganator is asked to redraw", redraws == before + 1, redraws - before)
SlashCmdList.SMOOTHBRAIN("icons on")
Check("/smooth icons on", Mark(meatSlot) == COIN and Mark(modern[1]) == COIN and Shows(111, COIN))
SlashCmdList.SMOOTHBRAIN("tooltip off")
Check("/smooth tooltip off", Tip(100) == "" and Full(100) == "")
SlashCmdList.SMOOTHBRAIN("tooltip on")
Check("/smooth tooltip on: one line again", Tip(100) ~= "" and #GameTooltip.lines == 1, Tip(100))
printed = {}
SlashCmdList.SMOOTHBRAIN("tooltip full")
Check("/smooth tooltip full: the reason in full without Shift, and it says so", Tip(100):find("Smooth Brain: ", 1, true) ~= nil
  and #GameTooltip.lines == 2 and SmoothBrainDB.explain == true and printed[1]:find("in full", 1, true) ~= nil, printed[1])
SlashCmdList.SMOOTHBRAIN("tooltip off")
SlashCmdList.SMOOTHBRAIN("tooltip short")
Check("/smooth tooltip short: one line, also after it was off", Tip(100) ~= "" and #GameTooltip.lines == 1 and SmoothBrainDB.explain == false
  and SmoothBrainDB.tooltip == true, Tip(100))
printed = {}
SlashCmdList.SMOOTHBRAIN("tooltip loud")
Check("anything else is refused, and changes nothing", printed[1]:find("short, full or off", 1, true) ~= nil and SmoothBrainDB.tooltip == true
  and SmoothBrainDB.explain == false, printed[1])
printed = {}
SlashCmdList.SMOOTHBRAIN("tooltip")
Check("/smooth tooltip alone says which it is", printed[1]:find("one line", 1, true) ~= nil and printed[1]:find("hold Shift", 1, true) ~= nil, printed[1])

printed = {}
SlashCmdList.SMOOTHBRAIN("ignore |cffffffff|Hitem:111::::::::28:::::|h[Spider Ichor]|h|r")
Check("/smooth ignore [item] leaves it alone", Verdict(111) == "nil" and Mark(ichor) == nil and SmoothBrainDB.ignore[111] == true, printed[1])
printed = {}
SlashCmdList.SMOOTHBRAIN("ignore")
Check("/smooth ignore lists them and mentions the tools", printed[1]:find("Item111", 1, true) ~= nil and printed[1]:find("mining pick", 1, true) ~= nil,
  printed[1])
SlashCmdList.SMOOTHBRAIN("ignore 111")
Check("...and the same command judges it again", Verdict(111) == "vendor/cheap" and Mark(ichor) == COIN)
SlashCmdList.SMOOTHBRAIN("ignore 2901")
Check("a tool can be judged after all", Verdict(2901) == "vendor/cheap" and Mark(pick) == COIN, Verdict(2901))
SlashCmdList.SMOOTHBRAIN("ignore 2901")
Check("...and left alone again", Verdict(2901) == "nil" and Mark(pick) == nil)

-- Locking: an item you say is yours to keep
do
  local LOCK = "Interface\\AddOns\\SmoothBrain\\lock"
  printed = {}
  SlashCmdList.SMOOTHBRAIN("lock |cffffffff|Hitem:111::::::::28:::::|h[Spider Ichor]|h|r")
  Check("/smooth lock [item]: it is kept, with a padlock, and says so", Verdict(111) == "locked/locked" and Mark(ichor) == LOCK
    and SmoothBrainDB.locked[111] == true and printed[1]:find("is locked", 1, true) ~= nil, printed[1])
  Check("...in every kind of bag", Shows(111, LOCK) and Mark(modern[1]) == LOCK and Mark(bbIchorButton) == LOCK
    and Mark(ContainerFrame2Item1) == LOCK and EUIMark(euiIchorOverlay) == LOCK, tostring(Mark(bbIchorButton)))
  local tip = Tip(111)
  results[#results + 1] = "INFO  tooltip, a locked item:\n        " .. tip
  Check("the tooltip says it is locked", tip:find("lock:0|t |cffffffffKeep it|r (you locked it)", 1, true) ~= nil
    and #GameTooltip.lines == 1, tip)
  Check("...and with Shift held, how to unlock it", Full(111):find("you locked it", 1, true) ~= nil
    and Full(111):find("to unlock", 1, true) ~= nil and #GameTooltip.lines == 2, Full(111))
  printed = {}
  SlashCmdList.SMOOTHBRAIN("")
  Check("/smooth no longer lists it to vendor", table.concat(printed, "\n"):find("Item111", 1, true) == nil)
  printed = {}
  SlashCmdList.SMOOTHBRAIN("all")
  Check("...and /smooth all lists it as kept", table.concat(printed, "\n"):find("[Item111] x10: |cffffffffkeep it|r (you locked it)", 1, true) ~= nil)
  printed = {}
  SlashCmdList.SMOOTHBRAIN("lock")
  Check("/smooth lock alone lists what is locked, and says how", printed[1]:find("locked: [Item111].", 1, true) ~= nil
    and printed[1]:find("Middle-click", 1, true) ~= nil, printed[1])
  Check("the summary counts it among the items to keep", ns.Summary().locked == 1
    and S.SummaryLine({ vendor = 0, free = 0, auction = 0, disenchant = 0, keep = 0, quest = 0, locked = 1, gain = 0 })
      == "With this limit, in your bags now: 1 to keep.")
  printed = {}
  SlashCmdList.SMOOTHBRAIN("lock 111")
  Check("...and the same command unlocks it", Verdict(111) == "vendor/cheap" and Mark(ichor) == COIN and Mark(bbIchorButton) == COIN
    and SmoothBrainDB.locked[111] == nil and printed[1]:find("unlocked", 1, true) ~= nil, printed[1])
  printed = {}
  SlashCmdList.SMOOTHBRAIN("unlock 111")
  Check("/smooth unlock on an item that isn't locked changes nothing", SmoothBrainDB.locked[111] == nil
    and printed[1]:find("isn't locked", 1, true) ~= nil, printed[1])
  SlashCmdList.SMOOTHBRAIN("lock 111")
  SlashCmdList.SMOOTHBRAIN("unlock 111")
  Check("/smooth unlock unlocks a locked one", SmoothBrainDB.locked[111] == nil and Verdict(111) == "vendor/cheap")
  printed = {}
  SlashCmdList.SMOOTHBRAIN("lock")
  Check("/smooth lock alone, with nothing locked", printed[1]:find("nothing is locked", 1, true) ~= nil, printed[1])

  -- A middle-click on an item in your bags
  Hover(111)
  Fire("GLOBAL_MOUSE_DOWN", "MiddleButton")
  Check("a middle-click on an item in your bags locks it", Verdict(111) == "locked/locked" and Mark(ichor) == LOCK)
  Fire("GLOBAL_MOUSE_DOWN", "MiddleButton")
  Check("...and another unlocks it", Verdict(111) == "vendor/cheap" and Mark(ichor) == COIN)
  local cloth112 = Verdict(112)
  local asked = priceLookups
  Fire("GLOBAL_MOUSE_DOWN", "LeftButton")
  Fire("GLOBAL_MOUSE_DOWN", "RightButton")
  Check("the other mouse buttons lock nothing, and nothing is judged afresh for them", next(SmoothBrainDB.locked) == nil
    and Verdict(111) == "vendor/cheap" and Verdict(112) == cloth112 and priceLookups == asked, priceLookups - asked)
  Hover(999)
  Fire("GLOBAL_MOUSE_DOWN", "MiddleButton")
  Check("an item you don't carry isn't locked by a middle-click", next(SmoothBrainDB.locked) == nil)
  Hover(111, true)
  Fire("GLOBAL_MOUSE_DOWN", "MiddleButton")
  Check("nor one whose tooltip was left showing by something the mouse is no longer on", next(SmoothBrainDB.locked) == nil)
  Hover(nil)
  Fire("GLOBAL_MOUSE_DOWN", "MiddleButton")
  Check("nor anything while no tooltip shows", next(SmoothBrainDB.locked) == nil)
  SlashCmdList.SMOOTHBRAIN("lockclick off")
  Hover(111)
  Fire("GLOBAL_MOUSE_DOWN", "MiddleButton")
  Check("/smooth lockclick off: a middle-click does nothing", SmoothBrainDB.lockclick == false and next(SmoothBrainDB.locked) == nil)
  SmoothBrain_ToggleLock()
  Check("...but the key you can bind still locks the item under the mouse", SmoothBrainDB.locked[111] == true
    and type(BINDING_NAME_SMOOTHBRAIN_LOCK) == "string")
  SmoothBrain_ToggleLock()
  Hover(nil)
  printed = {}
  SmoothBrain_ToggleLock()
  Check("that key with the mouse on nothing says what to do", next(SmoothBrainDB.locked) == nil
    and printed[1]:find("point at an item", 1, true) ~= nil, printed[1])
  SlashCmdList.SMOOTHBRAIN("lockclick on")
  Check("/smooth lockclick on", SmoothBrainDB.lockclick == true)

  -- Whatever the item is
  for _, id in ipairs({ 2901, 122, 101, 108 }) do SlashCmdList.SMOOTHBRAIN("lock " .. id) end
  Check("a tool, a leftover, a quest item and an item with no verdict can all be locked", Verdict(2901) == "locked/locked"
    and Verdict(122) == "locked/locked" and Verdict(101) == "locked/locked" and Verdict(108) == "locked/locked"
    and Mark(pick) == LOCK and Mark(leftover) == LOCK and Mark(hide) == LOCK and Mark(plain) == LOCK, Verdict(108))
  SlashCmdList.SMOOTHBRAIN("ignore 122")
  Check("locking counts for more than ignoring", SmoothBrainDB.ignore[122] == true and Verdict(122) == "locked/locked"
    and Mark(leftover) == LOCK)
  SmoothBrainDB.ignore[122] = nil
  -- Bags full: with every leftover locked, the cheapest stacks to vendor come next, as they do without the leftovers.
  for _, id in ipairs({ 124, 127, 180 }) do SlashCmdList.SMOOTHBRAIN("lock " .. id) end
  Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
  Check("bags full: a locked stack never flashes as one to throw away", not Glows(leftoverSlot) and Glows(junkSlot)
    and not Glows(bbLeftoverButton))
  RunTimers()
  local ids = {}
  for id in pairs(SmoothBrainDB.locked) do ids[#ids + 1] = id end
  for _, id in ipairs(ids) do SlashCmdList.SMOOTHBRAIN("unlock " .. id) end
  Check("unlocking them all brings every verdict back", next(SmoothBrainDB.locked) == nil and #ids == 7 and Verdict(2901) == "nil"
    and Verdict(122) == "free/done" and Verdict(101) == "quest/costly" and Verdict(108) == "nil" and Mark(leftover) == CROSS
    and Mark(pick) == nil and Mark(hide) == QUEST, #ids)
end

-- Kept without being priced: gear in one of your equipment sets
do
  Check("both rules are on unless you turn them off", SmoothBrainDB.sets == true and SmoothBrainDB.reagents == true)
  local glovesWas, dustWas, junkWas = Verdict(130), Verdict(131), Verdict(113)
  -- What the game says of your sets: item IDs by the slot they are worn in, with 0 and -1 for slots a set leaves out.
  local SETS = { [3] = { name = "Tank", items = { [1] = 0, [10] = 130, [16] = -1 } }, [7] = { name = "", items = { [10] = 131 } } }
  local locationsAsked = 0
  C_EquipmentSet = {
    GetEquipmentSetIDs = function()
      local ids = {}
      for id in pairs(SETS) do ids[#ids + 1] = id end
      table.sort(ids)
      return ids
    end,
    GetEquipmentSetInfo = function(id) return SETS[id].name, 132 end,
    GetItemIDs = function(id) return SETS[id].items end,
    GetItemLocations = function() locationsAsked = locationsAsked + 1 return {} end,
  }
  Check("gear is priced like anything else until the game says it is in a set", glovesWas ~= "keep/set" and dustWas == "disenchant/dust"
    and Verdict(130) == glovesWas, glovesWas)
  Fire("EQUIPMENT_SETS_CHANGED")
  Check("gear in one of your equipment sets is kept, whatever it is worth", Verdict(130) == "keep/set" and Verdict(131) == "keep/set"
    and ns.Check(130).set == "Tank" and ns.Check(131).set == nil, Verdict(130))
  Check("...with the tick, in every kind of bag", Mark(dustGloves) == TICK and Shows(130, TICK) and Shows(131, TICK), tostring(Mark(dustGloves)))
  local tip = Tip(130)
  results[#results + 1] = "INFO  tooltip, gloves in an equipment set:\n        " .. tip
  Check("the tooltip names the set", tip:find('Keep it|r  >>  in your set "Tank"', 1, true) ~= nil and #GameTooltip.lines == 1, tip)
  tip = Full(130)
  Check("...and with Shift held, says how to turn the rule off", tip:find("keep it", 1, true) ~= nil
    and tip:find('your equipment set "Tank"', 1, true) ~= nil and tip:find("/smooth sets off", 1, true) ~= nil and #GameTooltip.lines == 2, tip)
  Check("a set the game gives no name for is still a set", Tip(131):find("in an equipment set", 1, true) ~= nil
    and Full(131):find("one of your equipment sets", 1, true) ~= nil, Tip(131))
  Check("other gear is still priced", Verdict(133) ~= "keep/set" and Verdict(145) ~= "keep/set", Verdict(133))
  Check("where each piece is isn't asked: on WoW Forever that can crash the game", locationsAsked == 0, locationsAsked)
  printed = {}
  SlashCmdList.SMOOTHBRAIN("all")
  Check("/smooth all lists it as kept", table.concat(printed, "\n"):find("[Item130] x1: |cffffffffkeep it|r. It is in your equipment set", 1, true) ~= nil)
  -- Anything the game says is in a set counts, gray junk included; and what is kept never flashes.
  SETS[3].items[5] = 113
  Fire("EQUIPMENT_SETS_CHANGED")
  Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
  Check("bags full: a stack in a set never flashes as one to throw away", junkWas == "vendor/junk" and Verdict(113) == "keep/set"
    and not Glows(junkSlot), junkWas)
  RunTimers()
  SETS[3].items[5] = nil
  Fire("EQUIPMENT_SETS_CHANGED")
  Check("taking an item out of the set prices it again", Verdict(113) == junkWas and Verdict(130) == "keep/set", Verdict(113))
  SlashCmdList.SMOOTHBRAIN("lock 130")
  Check("locking counts for more than the set: the padlock", Verdict(130) == "locked/locked")
  SlashCmdList.SMOOTHBRAIN("unlock 130")
  SlashCmdList.SMOOTHBRAIN("ignore 130")
  Check("an ignored item gets no marker, set or not", Verdict(130) == "nil" and SmoothBrainDB.ignore[130] == true)
  SlashCmdList.SMOOTHBRAIN("ignore 130")
  Check("...and is kept again once it isn't ignored", Verdict(130) == "keep/set" and SmoothBrainDB.ignore[130] == false)
  SmoothBrainDB.ignore[130] = nil
  printed = {}
  SlashCmdList.SMOOTHBRAIN("sets off")
  Check("/smooth sets off: set gear is priced like the rest", SmoothBrainDB.sets == false and Verdict(130) == glovesWas
    and Verdict(131) == dustWas and Mark(dustGloves) == DUST and printed[1]:find("equipment sets: off", 1, true) ~= nil, printed[1])
  printed = {}
  SlashCmdList.SMOOTHBRAIN("sets")
  Check("/smooth sets alone says which it is", printed[1]:find("off. /smooth sets on|off", 1, true) ~= nil, printed[1])
  SlashCmdList.SMOOTHBRAIN("sets on")
  Check("/smooth sets on", SmoothBrainDB.sets == true and Verdict(130) == "keep/set" and Mark(dustGloves) == TICK)
  -- The game's answer in a shape this wasn't written for: nothing is in a set, and nothing breaks.
  local itemIDs = C_EquipmentSet.GetItemIDs
  C_EquipmentSet.GetItemIDs = function() error("changed") end
  Fire("EQUIPMENT_SETS_CHANGED")
  Check("a game that answers differently: gear is priced as before, without an error", Verdict(130) == glovesWas and Verdict(131) == dustWas)
  C_EquipmentSet.GetItemIDs = function() return "not a list" end
  Fire("EQUIPMENT_SETS_CHANGED")
  Check("...whatever it answers", Verdict(130) == glovesWas)
  C_EquipmentSet.GetItemIDs = itemIDs
  C_EquipmentSet.GetEquipmentSetIDs = function() return nil end
  Fire("EQUIPMENT_SETS_CHANGED")
  Check("a character with no sets", Verdict(130) == glovesWas and Verdict(131) == dustWas)
  C_EquipmentSet = nil
  Fire("EQUIPMENT_SETS_CHANGED")
  Check("a client without equipment sets", Verdict(130) == glovesWas and Mark(dustGloves) == DUST)
end

-- Kept without being priced: what your class casts with
do
  -- Ankh (a shaman's), Arcane Powder (a mage's), Instant Poison and Flash Powder (a rogue's): all sold by vendors
  -- and listed on the auction house for much more than a vendor pays back.
  for _, id in ipairs({ 17030, 17020, 6947, 5140 }) do
    ITEMS[id] = { 500, 0 }
    PRICES.vendorbuy[id], PRICES.dbminbuyout[id], PRICES.dbnumauctions[id] = 2000, 1500, 50
  end
  ITEMS[6947][4] = 0   -- a poison is a consumable
  local first = #BAGS[0] + 1
  BAGS[0][first], BAGS[0][first + 1], BAGS[0][first + 2], BAGS[0][first + 3] = { 17030, 5 }, { 17020, 5 }, { 6947, 5 }, { 5140, 5 }
  local ankh = Button(0, 17030, first)
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
  ankh:Update()
  Check("the case reported: Ankhs are marked to auction", Verdict(17030) == "auction/costly" and Mark(ankh) == GAVEL, Verdict(17030))
  local CLASS = "SHAMAN"
  function UnitClass(unit) return unit == "player" and "Schamane" or nil, unit == "player" and CLASS or nil end
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("your own class's reagents are kept, whatever they are worth", Verdict(17030) == "keep/reagent" and Mark(ankh) == TICK
    and Shows(17030, TICK), Verdict(17030))
  Check("another class's are priced like anything else", Verdict(17020) == "auction/costly" and Verdict(5140) == "auction/costly"
    and Verdict(6947) == "keep/costly", Verdict(17020))
  local tip = Tip(17030)
  results[#results + 1] = "INFO  tooltip, a shaman's Ankhs:\n        " .. tip
  Check("the tooltip says why", tip:find("Keep it|r  >>  your class uses it", 1, true) ~= nil and #GameTooltip.lines == 1, tip)
  tip = Full(17030)
  Check("...and with Shift held, how to turn the rule off", tip:find("keep it", 1, true) ~= nil
    and tip:find("Your class uses it", 1, true) ~= nil and tip:find("/smooth reagents off", 1, true) ~= nil and #GameTooltip.lines == 2, tip)
  Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
  Check("bags full: your reagents never flash as stacks to throw away", not Glows(ankh))
  RunTimers()
  printed = {}
  SlashCmdList.SMOOTHBRAIN("reagents off")
  Check("/smooth reagents off: they are priced like the rest", SmoothBrainDB.reagents == false and Verdict(17030) == "auction/costly"
    and Mark(ankh) == GAVEL and printed[1]:find("reagents: off", 1, true) ~= nil, printed[1])
  SlashCmdList.SMOOTHBRAIN("reagents on")
  Check("/smooth reagents on", SmoothBrainDB.reagents == true and Verdict(17030) == "keep/reagent" and Mark(ankh) == TICK)
  CLASS = "MAGE"
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("a mage keeps Arcane Powder, and prices Ankhs", Verdict(17020) == "keep/reagent" and Verdict(17030) == "auction/costly")
  CLASS = "ROGUE"
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("a rogue keeps powders and poisons", Verdict(5140) == "keep/reagent" and Verdict(6947) == "keep/reagent"
    and Verdict(17020) == "auction/costly")
  CLASS = "WARRIOR"
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("a class that casts with nothing keeps none of them for that", Verdict(17030) == "auction/costly" and Verdict(17020) == "auction/costly"
    and Verdict(5140) == "auction/costly" and Verdict(6947) == "keep/costly")
  CLASS = nil
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("while the game doesn't say what you are, nothing is kept as a reagent", Verdict(17030) == "auction/costly")
  printed = {}
  SlashCmdList.SMOOTHBRAIN("help")
  local help = table.concat(printed, "\n")
  Check("/smooth help lists both commands", help:find("/smooth sets on|off", 1, true) ~= nil
    and help:find("/smooth reagents on|off", 1, true) ~= nil)
  UnitClass = nil
  for offset = 3, 0, -1 do BAGS[0][first + offset] = nil end
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
  Fire("QUEST_ACCEPTED", 1, 1)
end

-- Soulbound things with a Use of their own are kept. The case reported from
-- the game: the Cozy Sleeping Bag, marked to vendor.
do
  ITEMS[174], BOUND[174] = { 2500, 1, 1, 15 }, true                        -- the Cozy Sleeping Bag: a vendor would pay 25s
  ITEMS[175], BOUND[175] = { 300, 1, 2, 4, 0, "INVTYPE_TRINKET" }, true    -- a soulbound trinket with a Use: gear
  ITEMS[176] = { 40, 0, 1, 15 }                                            -- something with a Use that you can trade
  ITEMS[177], BOUND[177] = { 30, 1, 1, 12 }, true                          -- a soulbound quest tool with a Use; its quest is done
  ITEMS[178], BOUND[178] = { 60, 1, 1, 15 }, true                          -- soulbound, no Use: only a vendor wants it
  USES[174], USES[175], USES[176], USES[177] = 8690, 8691, 8692, 8693
  ITEM_QUESTS[177] = { 930 }
  local first = #BAGS[0] + 1
  for offset, id in ipairs({ 174, 175, 176, 177, 178 }) do BAGS[0][first + offset - 1] = { id, 1 } end
  local bag = Button(0, 174, first)
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
  bag:Update()
  Check("the Cozy Sleeping Bag is kept, not marked to vendor", Verdict(174) == "keep/use" and Mark(bag) == TICK and Shows(174, TICK),
    Verdict(174))
  local tip = Tip(174)
  results[#results + 1] = "INFO  tooltip, the Cozy Sleeping Bag:\n        " .. tip
  Check("the tooltip says why in a few words", tip:find("Keep it|r  >>  soulbound, yours to use", 1, true) ~= nil and #GameTooltip.lines == 1, tip)
  tip = Full(174)
  results[#results + 1] = "INFO  ...with Shift held:\n        " .. tip
  Check("...and with Shift held in full, with what a vendor would pay", tip:find("has a use of its own", 1, true) ~= nil
    and tip:find("25s", 1, true) ~= nil and #GameTooltip.lines == 2, tip)
  Check("a soulbound trinket with a Use is gear like any other: vendor", Verdict(175) == "vendor/boundsell", Verdict(175))
  Check("something with a Use that you can trade is priced like anything else", Verdict(176) == "nil", Verdict(176))
  Check("a soulbound quest tool whose quest is done is still a leftover", Verdict(177) == "vendor/leftover", Verdict(177))
  Check("something soulbound with no Use still goes to a vendor", Verdict(178) == "vendor/boundsell", Verdict(178))
  printed = {}
  SlashCmdList.SMOOTHBRAIN("")
  local listed = table.concat(printed, "\n")
  Check("/smooth doesn't list the Sleeping Bag among things to vendor", listed:find("Item174", 1, true) == nil
    and listed:find("Item178", 1, true) ~= nil, listed)
  Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
  Check("bags full: it never flashes as a stack to throw away", not Glows(bag))
  RunTimers()
  USES[174] = "broken"
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("if the game can't say whether it has a Use, nothing breaks", pcall(Verdict, 174) and Verdict(174) == "vendor/boundsell", Verdict(174))
  for id = 174, 178 do ITEMS[id], BOUND[id], USES[id] = nil, nil, nil end
  ITEM_QUESTS[177] = nil
  for offset = 4, 0, -1 do BAGS[0][first + offset] = nil end
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
end

-- Food and potions the game also marks as crafting reagents are priced like
-- trade goods. The case reported from the game: Raw Winter Squid, food to the
-- game and a cooking ingredient, 7c from a vendor and 5s 95c at auction,
-- marked "keep it".
do
  ITEMS[194] = { 7, 0, 1, 0, 0, nil, true }   -- Raw Winter Squid: food, and a crafting reagent
  ITEMS[195] = { 7, 0, 1, 0 }                 -- food at the same prices that is nothing else
  USES[194], USES[195] = 433, 433
  PRICES.dbminbuyout[194], PRICES.dbnumauctions[194] = 595, 169
  PRICES.dbminbuyout[195], PRICES.dbnumauctions[195] = 595, 169
  local first = #BAGS[0] + 1
  BAGS[0][first], BAGS[0][first + 1] = { 194, 1 }, { 195, 1 }
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
  Check("food that is also a crafting reagent is priced like a trade good: auction it", Verdict(194) == "auction/costly"
    and ns.Check(194).price == 595, Verdict(194))
  Check("...and its tooltip line says so", Tip(194):find("Auction it", 1, true) ~= nil, Tip(194))
  Check("...other food as dear to buy back is still kept", Verdict(195) == "keep/costly", Verdict(195))
  PRICES.dbminbuyout[194] = 9
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("...and when it costs little more to buy back, it is one to vendor, as it was", Verdict(194) == "vendor/cheap", Verdict(194))
  BOUND[194] = true
  Fire("BAG_UPDATE", 0)
  Fire("QUEST_ACCEPTED", 1, 1)
  Check("soulbound, it still has a Use of its own, and is kept", Verdict(194) == "keep/use", Verdict(194))
  BOUND[194], ITEMS[194], ITEMS[195], USES[194], USES[195] = nil, nil, nil, nil, nil
  PRICES.dbminbuyout[194], PRICES.dbnumauctions[194], PRICES.dbminbuyout[195], PRICES.dbnumauctions[195] = nil, nil, nil, nil
  BAGS[0][first + 1] = nil
  BAGS[0][first] = nil
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
  Fire("QUEST_ACCEPTED", 1, 1)
end

-- What a verdict says can hang on the clock ("Auctionator saw it today", a
-- price seen "within the hour"). Everything is judged afresh when you leave
-- the auction house, an hour after that, and at midnight.
do
  RunTimers()
  local asked = priceLookups
  Fire("AUCTION_HOUSE_CLOSED")
  local waits = {}
  for _, fn in ipairs(timers) do waits[#waits + 1] = delays[fn] end
  table.sort(waits)
  Check("leaving the auction house asks for two rounds: a moment later, and an hour later", #waits == 2 and waits[1] <= 5
    and waits[2] >= 3600, table.concat(waits, ","))
  local first, second = timers[1], timers[2]
  timers = {}
  first()
  Verdict(111)
  Check("...the first judges everything afresh", priceLookups > asked, priceLookups - asked)
  Fire("AUCTION_HOUSE_CLOSED")   -- back again within the hour
  timers = {}
  asked = priceLookups
  second()
  Verdict(111)
  Check("...the hour's round is dropped once a later visit has its own", priceLookups == asked, priceLookups - asked)
  -- Midnight: the game's date() says how long until then.
  date = function() return { hour = 23, min = 59, sec = 0 } end
  Fire("PLAYER_LOGIN")
  local midnight
  for _, fn in ipairs(timers) do
    if delays[fn] and delays[fn] > 20 then midnight = fn end
  end
  Check("at login, a round is set for midnight", midnight ~= nil and delays[midnight] >= 60 and delays[midnight] <= 70,
    midnight and delays[midnight])
  timers = {}
  asked = priceLookups
  midnight()
  Verdict(111)
  Check("...which judges everything afresh, and sets the next", priceLookups > asked and #timers == 1, #timers)
  date, timers = nil, {}
end

-- The nearest vendor: Questie's vendors in your zone, and where you are on its map.
-- Elwynn Forest (Questie's zone 12, the game's map 1429), 3470 by 2315 yards; you stand in the middle.
do
  local db, player = questieModules.QuestieDB, questieModules.QuestiePlayer
  local NPCS = {
    [1] = { name = "Near Vendor", subName = "General Goods", npcFlags = 130, spawns = { [12] = { { 50, 40 } } } },
    [2] = { name = "Far Vendor", npcFlags = 128, spawns = { [12] = { { 80, 50 }, { -1, -1 } } } },
    [3] = { name = "Horde Vendor", npcFlags = 128, friendlyToFaction = "H", spawns = { [12] = { { 50, 50.1 } } } },
    [4] = { name = "Quest Giver", npcFlags = 2, spawns = { [12] = { { 50, 50 } } } },
    [5] = { name = "[DND] Vendor", npcFlags = 128, spawns = { [12] = { { 50, 50 } } } },
    [6] = { name = "Westfall Vendor", npcFlags = 128, spawns = { [40] = { { 50, 50 } } } },
  }
  db.npcFlags = { VENDOR = 128 }
  db.NPCPointers = {}
  for id = 1, 2000 do db.NPCPointers[id] = true end   -- most of them nobody in particular
  local queried = 0
  db.QueryNPCSingle = function(id, key)
    queried = queried + 1
    local npc = NPCS[id]
    if key == "npcFlags" then return npc and npc.npcFlags or 0 end
    return npc and npc[key]
  end
  db.IsFriendlyToPlayer = function(side) return side == nil or side == "A" or side == "AH" end
  local zone, px, py = 12, 0.5, 0.5
  player.GetCurrentZoneId = function() return zone end
  questieModules.ZoneDB = { GetUiMapIdByAreaId = function(_, area) return ({ [12] = 1429, [40] = 1436, [99] = 1999 })[area] end }
  C_Map = {
    GetPlayerMapPosition = function(map, unit)
      if px == nil then return nil end
      return { GetXY = function() return px, py end }
    end,
    GetMapWorldSize = function(map) return 3470, 2315 end,
  }
  local function Vendor()
    printed = {}
    SlashCmdList.SMOOTHBRAIN("vendor")
    return printed[1] or ""
  end
  Check("the vendors are read from Questie a little at a time, not all at once", Vendor():find("still reading", 1, true) ~= nil
    and queried < 2000, Vendor())
  RunTimers()
  RunTimers()
  RunTimers()
  local line = Vendor()
  Check("then the nearest one in your zone is named, with how far and which way",
    line:find("nearest vendor: Near Vendor <General Goods>, 232 yd N (50.0, 40.0).", 1, true) ~= nil, line)
  results[#results + 1] = "INFO  /smooth vendor:\n        " .. line
  printed = {}
  SlashCmdList.SMOOTHBRAIN("")
  local list = table.concat(printed, "\n")
  Check("/smooth names it under the things to vendor", list:find("Vendoring the", 1, true) ~= nil
    and list:find("  Nearest vendor: Near Vendor", 1, true) ~= nil, printed[#printed])
  px, py = 0.799, 0.5
  line = Vendor()
  Check("the other faction's vendors, quest givers and [DND] ones are not counted; standing by one, it is \"right here\"",
    line:find("Far Vendor, right here", 1, true) ~= nil, line)
  px, py = 0.5, 0.5
  zone = 99
  Check("a zone with no vendor Questie knows of says so", Vendor():find("none in this zone", 1, true) ~= nil, Vendor())
  zone, px = 12, nil
  Check("where the game won't say where you are, it says so", Vendor():find("won't say where you are", 1, true) ~= nil, Vendor())
  px = 0.5
  C_Map.GetPlayerMapPosition = function() error("secret") end
  Check("a position the game keeps from addons causes no error", Vendor():find("won't say where you are", 1, true) ~= nil, Vendor())
  C_Map.GetPlayerMapPosition = function() return { GetXY = function() return px, py end } end

  -- The arrow: it points at that vendor, turned by which way you face.
  function Widget:SetRotation(angle) self.rotation = angle end
  local facing = 0   -- north
  GetPlayerFacing = function() return facing end
  ns.LookForVendor()
  local arrow = SmoothBrainVendorArrow
  Check("while you carry something to vendor, the arrow shows, with the distance", arrow ~= nil and arrow:IsShown()
    and arrow.distance.text == "232 yd", arrow and arrow.distance.text)
  Check("...facing north, it points straight ahead at a vendor to the north", math.abs(arrow.icon.rotation) < 1e-6,
    arrow.icon.rotation)
  facing = math.pi / 2   -- west: the vendor is now to your right
  arrow.scripts.OnUpdate(arrow, 0.02)
  Check("...turn to face west and it turns a quarter to the right", math.abs(arrow.icon.rotation + math.pi / 2) < 1e-6,
    arrow.icon.rotation)
  GetPlayerFacing = function() error("secret") end
  arrow.scripts.OnUpdate(arrow, 0.02)
  Check("where the game won't say which way you face, north is up, like the map", math.abs(arrow.icon.rotation) < 1e-6
    and arrow.northUp == true, arrow.icon.rotation)
  GetPlayerFacing = nil
  arrow.GetPoint = function() return "TOPLEFT", UIParent, "TOPLEFT", 120, -80 end
  arrow.scripts.OnDragStop(arrow)
  local at = SmoothBrainDB.arrowAt
  Check("dragged somewhere, it stays there", at[1] == "TOPLEFT" and at[2] == "TOPLEFT" and at[3] == 120 and at[4] == -80)
  SlashCmdList.SMOOTHBRAIN("arrow reset")
  Check("/smooth arrow reset puts it back", next(SmoothBrainDB.arrowAt) == nil)
  zone = 99
  ns.LookForVendor()
  Check("with no vendor in the zone it hides", not arrow:IsShown())
  zone = 12
  ns.LookForVendor()
  Check("...and comes back with one", arrow:IsShown())
  SlashCmdList.SMOOTHBRAIN("arrow off")
  ns.LookForVendor()
  Check("/smooth arrow off hides it", not arrow:IsShown() and SmoothBrainDB.arrow == false)
  SlashCmdList.SMOOTHBRAIN("arrow on")

  Questie.started = false
  Check("without Questie ready, /smooth vendor says what it needs", Vendor():find("needs Questie", 1, true) ~= nil, Vendor())
  printed = {}
  SlashCmdList.SMOOTHBRAIN("")
  Check("...and /smooth leaves the line out", not table.concat(printed, "\n"):find("Nearest vendor", 1, true))
  Questie.started = true
  Fire("QUEST_ACCEPTED", 1, 1)
end

-- The quest log itself: an item one of your quests asks for is kept, whatever else is known about it
do
  local HAND_IN = "Its quest is complete: hand it in, and this item goes with it."
  local function Note(id) local result = ns.Check(id) return result and result.questNote or nil end
  local function Settle()
    Fire("QUEST_LOG_UPDATE")
    RunTimers()
  end
  -- The case reported from the game: the Titan Relic. It starts one quest, and once that is done the next
  -- quest, which no addon has on record, takes it at its hand-in. It was called safe to delete.
  ITEMS[200], BOUND[200] = { 0, 1, 1, 12 }, true
  ITEM_STARTS[200], ITEM_QUESTS[200], DONE[970] = 970, { 970 }, true
  -- A plain quest item: the one quest known for it is done.
  ITEMS[201], BOUND[201] = { 0, 1, 1, 12 }, true
  ITEM_QUESTS[201], DONE[972] = { 972 }, true
  local first = #BAGS[0] + 1
  BAGS[0][first], BAGS[0][first + 1] = { 200, 1 }, { 201, 1 }
  local relic = Button(0, 200, first)
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
  relic:Update()
  Check("an item that started a quest now done, still in your bags: kept, in case the next quest wants it",
    Verdict(200) == "quest/held" and Note(200) == "It started a quest you have done, and may be wanted for the next one."
    and Mark(relic) == QUEST, Verdict(200))
  ON[971], READY[971] = true, true
  OBJECTIVES[971] = { { type = "item", text = "1/1 Item200", finished = true } }
  Fire("QUEST_ACCEPTED", 1, 971)
  Check("the Titan Relic: the quest in your log that takes it keeps it, though no addon knows that quest",
    Verdict(200) == "quest/held" and Note(200) == HAND_IN and Mark(relic) == QUEST, tostring(Note(200)))
  results[#results + 1] = "INFO  tooltip, an item a complete quest in your log takes:\n        " .. Tip(200)
  Fire("UI_ERROR_MESSAGE", 20, ERR_INV_FULL)
  printed = {}
  SlashCmdList.SMOOTHBRAIN("")
  Check("...it never flashes as one to throw away, and /smooth doesn't list it", not Glows(relic)
    and table.concat(printed, "\n"):find("Item200", 1, true) == nil)
  RunTimers()

  Check("a quest item whose one known quest is done, that no quest in your log asks for: a leftover", Verdict(201) == "free/done",
    Verdict(201))
  -- You take a quest nothing has on record. What it asks for arrives a moment after the quest does.
  ON[973] = true
  OBJECTIVES[973] = { { type = "item", text = " : 0/2", finished = false } }
  Fire("QUEST_ACCEPTED", 1, 973)
  Check("a quest just taken, what it asks for still loading: nothing is called a leftover meanwhile", Verdict(201) == "quest/held"
    and Note(201):find("can't be read just now", 1, true) ~= nil and Verdict(122) == "quest/held", tostring(Note(201)))
  OBJECTIVES[973] = { { type = "item", text = "Item201: 1/2", finished = false } }
  Fire("QUEST_LOG_UPDATE")
  Check("...the quest log is read again a moment after it changed, not at once", Note(201):find("can't be read just now", 1, true) ~= nil)
  RunTimers()
  Check("...and then the quest that asks for the item keeps it", Verdict(201) == "quest/held"
    and Note(201) == "A quest in your log asks for it." and Verdict(122) == "free/done", tostring(Note(201)))
  local asked = priceLookups
  OBJECTIVES[973][1].text = "Item201: 2/2"
  Settle()
  Check("progress on a quest judges nothing afresh", priceLookups == asked, priceLookups - asked)
  READY[973] = true
  Settle()
  Check("...the quest becoming complete does: the item now says to hand it in", Note(201) == HAND_IN and priceLookups > asked,
    tostring(Note(201)))

  -- Things that aren't quest items
  ON[974] = true
  OBJECTIVES[974] = { { type = "item", text = "0/5 Bolt of Item112" }, { type = "item", text = "3/8 Item118" },
    { type = "monster", text = "Item116 slain: 0/1" } }
  Fire("QUEST_ACCEPTED", 1, 974)
  Check("a trade good a quest in your log asks for is kept too", Verdict(118) == "quest/held"
    and Note(118) == "A quest in your log asks for it.", Verdict(118))
  Check("...but not one whose name is only part of what is asked for, or that is named by another kind of objective",
    Verdict(112) == "auction/costly" and Verdict(116) == "vendor/cheap", Verdict(112))
  OBJECTIVES[974] = { { type = "item", text = "Some Item112, please" } }
  Settle()
  Check("an objective worded another way still counts, by the item's name in it", Verdict(112) == "quest/held"
    and Verdict(118) == "auction/costly", Verdict(112))
  ON[974], OBJECTIVES[974] = nil, nil
  Fire("QUEST_REMOVED", 974)
  Check("dropping the quest: judged by price again", Verdict(112) == "auction/costly")

  -- A folded header: the game counts the quests under it but won't show them
  Check("with the whole quest log readable, leftovers are called leftovers", Verdict(122) == "free/done"
    and Verdict(125) == "vendor/leftover", Verdict(125))
  FOLDED[906] = true
  Settle()
  Check("a folded header: nothing you couldn't get back is called a leftover while part of the log is hidden",
    Verdict(122) == "quest/held" and Note(122):find("folded header", 1, true) ~= nil and Verdict(125) == "quest/held"
    and Verdict(127) == "quest/held", tostring(Note(122)))
  Check("...what you could buy again is judged as before", Verdict(105) == "vendor/cheap" and Verdict(111) == "vendor/cheap"
    and Verdict(112) == "auction/costly", Verdict(105))
  FOLDED[906] = nil
  Settle()
  Check("...and unfolding it brings the leftovers back", Verdict(122) == "free/done" and Verdict(125) == "vendor/leftover"
    and Verdict(127) == "free/done", Verdict(122))
  local getInfo = C_QuestLog.GetInfo
  C_QuestLog.GetInfo = function() error("changed") end
  local okLog = pcall(Settle)
  Check("a quest log that can't be read at all: no error, and no leftover claimed", okLog and Verdict(122) == "quest/held"
    and Verdict(111) == "vendor/cheap", Verdict(122))
  C_QuestLog.GetInfo = getInfo
  Settle()

  -- The hand-in: the quest takes the Titan Relic with it
  ON[971], READY[971], DONE[971], OBJECTIVES[971] = nil, nil, true, nil
  ON[973], READY[973], OBJECTIVES[973] = nil, nil, nil
  BAGS[0][first], BAGS[0][first + 1] = nil, nil
  Fire("QUEST_TURNED_IN", 971)
  Fire("BAG_UPDATE", 0)
  Fire("BAG_UPDATE_DELAYED")
  ITEMS[200], ITEMS[201] = nil, nil
  Check("afterwards everything is as it was", Verdict(122) == "free/done" and Verdict(181) == "quest/held" and Note(181) == HAND_IN
    and Verdict(118) == "auction/costly" and Verdict(200) == "nil", Verdict(181))
end

-- Things change while you play
ON[900] = true
Fire("QUEST_ACCEPTED", 1, 900)
Check("taking the quest: keep for it, and the coin turns into a quest mark", Verdict(100) == "quest/onquest" and Mark(meatSlot) == QUEST
  and Shows(100, QUEST))
ON[900], DONE[900] = nil, true
Fire("QUEST_TURNED_IN", 900)
Check("handing it in: judged like any other item again", Verdict(100) == "vendor/cheap" and ns.Check(100).questDone and Mark(meatSlot) == COIN,
  Verdict(100))
DONE[932] = true
Fire("QUEST_TURNED_IN", 932)
Check("finishing an item's last open quest makes it a leftover", Verdict(123) == "free/done")
DONE[936] = true
Fire("QUEST_TURNED_IN", 936)
Check("...but not finishing the quest an item starts: still in your bags after that, it may be for the next quest",
  Verdict(162) == "quest/held" and ns.Check(162).questNote == "It started a quest you have done, and may be wanted for the next one.",
  Verdict(162))
DONE[936] = nil
ON[951], READY[951], DONE[951] = nil, nil, true
Fire("QUEST_TURNED_IN", 951)
Check("...and handing a quest in frees the item its hand-in should have taken", Verdict(181) == "free/done"
  and ns.Check(181).doneNote == nil, Verdict(181))
ON[951], READY[951], DONE[951] = true, true, nil
READY[950] = nil
Fire("QUEST_ACCEPTED", 1, 1)
Check("a tool is kept while its quest is still under way", Verdict(180) == "quest/held", Verdict(180))
READY[950] = true
Fire("QUEST_ACCEPTED", 1, 1)
DONE[900], DONE[932] = nil, nil
BAGS[0][1] = { 111, 30 }
Fire("BAG_UPDATE", 0)
Fire("BAG_UPDATE_DELAYED")
Check("carrying more changes the sums", ns.Check(111).count == 40 and ns.Check(111).diff == 120 and ns.Check(100).count == 5,
  ns.Check(111).diff)

-- The setup window again, this time changing things in it
Check("/smooth, /smoothbrain and the old /vok all reach it", SLASH_SMOOTHBRAIN1 == "/smooth" and SLASH_SMOOTHBRAIN2 == "/smoothbrain"
  and SLASH_SMOOTHBRAIN3 == "/vok")
SlashCmdList.SMOOTHBRAIN("setup")
Check("/smooth setup opens it, on its first page", SmoothBrainSetup:IsShown() and S.main.shown and not S.guide.shown
  and S.title.text == "Smooth Brain: setup", S.title.text)
S.guideButton.scripts.OnClick(S.guideButton)
Check("the second page says how each marker is decided", S.guide.shown and not S.main.shown
  and S.title.text == "Smooth Brain: how each marker is decided", S.title.text)
local titles = {}
for index, rule in ipairs(S.rules) do titles[index] = rule.title.text end
Check("...by ten rules, numbered in the order they are tried", table.concat(titles, " | ") == "1. No marker: left alone | 2. Keep for a quest | "
  .. "3. Disenchant | 4. Delete | 5. Keep: can't be sold | 6. Vendor: soulbound | 7. Vendor: cheap to replace | 8. Keep | 9. Auction | "
  .. "10. No marker: nothing to go on", table.concat(titles, " | "))
Check("...each with its rule spelled out, and your limit named", S.rules[2].body.text:find("RestedXP", 1, true) ~= nil
  and S.rules[7].body.text:find("at most your limit", 1, true) ~= nil and S.guideIntro.text:find("Your limit is 5s.", 1, true) ~= nil,
  S.guideIntro.text)
S.backButton.scripts.OnClick(S.backButton)
Check("Back returns to the first page", S.main.shown and not S.guide.shown)
local before = S.summary.text
S.presets[1].scripts.OnClick(S.presets[1])
Check("pressing 50c sets the limit, and the summary follows", SmoothBrainDB.limit == 50 and S.limit.text == "50c"
  and S.presets[1].enabled == false and S.summary.text ~= before, S.summary.text)
S.limit:SetText("2s 50c")
S.limit.scripts.OnEnterPressed(S.limit)
Check("typing a limit", SmoothBrainDB.limit == 250 and S.limit.text == "2s 50c")
S.limit:SetText("plenty")
S.limit.scripts.OnEnterPressed(S.limit)
Check("typing something that isn't money changes nothing", SmoothBrainDB.limit == 250 and S.limit.text == "2s 50c")
S.presets[3].scripts.OnClick(S.presets[3])
S.toggles.flash:SetChecked(false)
S.toggles.flash.scripts.OnClick(S.toggles.flash)
Check("unticking a box", SmoothBrainDB.flash == false)
S.toggles.flash:SetChecked(true)
S.toggles.flash.scripts.OnClick(S.toggles.flash)
S.choices.auctionator.scripts.OnClick(S.choices.auctionator)
Check("choosing Auctionator only", SmoothBrainDB.prices == "auctionator" and S.choices.auctionator.checked and not S.choices.both.checked
  and ns.Check(111).price == 25)
S.choices.both.scripts.OnClick(S.choices.both)
Check("...and either again", SmoothBrainDB.prices == "both" and SmoothBrainDB.limit == 500 and SmoothBrainDB.flash == true
  and ns.Check(111).price == 19)
SmoothBrainSetup:Hide()
-- What it says when things are missing
local none = { installed = false, priced = 0 }
local empty = { installed = true, priced = 0 }
local state, words = S.PriceLine("TradeSkillMaster", none, 10, "advice")
Check("not installed", state == false and words == "TradeSkillMaster: not installed, or not enabled.", words)
state, words = S.PriceLine("Auctionator", empty, 10, "Scan the auction house with it.")
Check("installed, but with nothing to offer yet", state == nil
  and words == "Auctionator: running, but it has no prices here yet. Scan the auction house with it.", words)
state, words = S.Verdict({ tsm = empty, auctionator = none })
Check("no prices anywhere", state == false and words:find("No prices yet", 1, true) ~= nil, words)
SmoothBrainDB.prices = "tsm"
state, words = S.Verdict({ tsm = empty, auctionator = { installed = true, priced = 4 } })
Check("prices, but not from the source chosen", state == false and words:find("not from the source chosen", 1, true) ~= nil, words)
SmoothBrainDB.prices = "both"
Check("the summary line when nothing is judged", S.SummaryLine({ vendor = 0, free = 0, auction = 0, disenchant = 0, keep = 0, quest = 0, gain = 0 })
  == "With this limit, nothing in your bags gets a verdict right now.")

-- Questie still starting up: it would call every restricted quest "not for you"
Questie.started = false
Fire("QUEST_ACCEPTED", 1, 1)
Check("Questie not ready: no leftover is claimed on its word, and quest items are kept", Verdict(122) == "quest/held"
  and Verdict(124) == "quest/held" and Verdict(125) == "quest/held" and Verdict(127) == "free/done", Verdict(125))
Questie.started = true
Check("...and the answer isn't remembered: once Questie is ready the leftovers show", Verdict(122) == "free/done"
  and Verdict(124) == "free/done" and Verdict(125) == "vendor/leftover", Verdict(122))
Fire("QUEST_ACCEPTED", 1, 1)

-- Neither TradeSkillMaster nor Auctionator installed
local tsmWas, auctionatorWas = TSM_API, Auctionator
TSM_API, Auctionator = nil, nil
Fire("QUEST_ACCEPTED", 1, 1)
Check("no price addon: nothing breaks, and things you could sell get no marker", Verdict(111) == "nil" and Verdict(112) == "nil"
  and Verdict(131) == "nil" and Verdict(120) == "nil", Verdict(111))
Check("...quest items, leftovers, junk, soulbound and unsellable items are still judged", Verdict(160) == "quest/held"
  and Verdict(122) == "free/done" and Verdict(113) == "vendor/junk" and Verdict(114) == "vendor/boundsell"
  and Verdict(171) == "keep/nosale" and Verdict(173) == "keep/useup", Verdict(114))
Check("...an item a guide needs is kept, with the honest reason", Verdict(100) == "quest/noprices"
  and ns.Explain(ns.Check(100), ns.Money):find("No price addon is running", 1, true) ~= nil, Verdict(100))
printed = {}
SlashCmdList.SMOOTHBRAIN("")
Check("...and /smooth says prices are missing, then lists what it can", printed[1]:find("no prices are available", 1, true) ~= nil
  and table.concat(printed, "\n"):find("Item113", 1, true) ~= nil, printed[1])
local found = ns.Detect()
local state, words = S.Verdict(found)
Check("...as does the setup window", not found.tsm.installed and not found.auctionator.installed and state == false
  and words:find("No prices yet", 1, true) ~= nil, words)
results[#results + 1] = "INFO  /smooth with no price addon:\n        " .. table.concat(printed, "\n        ")
TSM_API, Auctionator = tsmWas, auctionatorWas
Fire("QUEST_ACCEPTED", 1, 1)
Check("with the price addons back, so are the verdicts", Verdict(111) == "vendor/cheap" and Verdict(112) == "auction/costly")

-- Questie or RestedXP changes shape in an update: nothing may break
questieModules.QuestieDB.QueryItemSingle = function() error("changed") end
Fire("QUEST_ACCEPTED", 1, 1)
Check("a changed Questie: no error, no leftovers claimed on its word, and quest items are kept", Verdict(122) == "quest/held"
  and Verdict(127) == "free/done" and Verdict(161) == "keep/nosale", Verdict(161))
printed = {}
RXP.IsGuideActive = function() error("changed") end
Fire("QUEST_ACCEPTED", 1, 1)
local ok, problem = pcall(Tip, 101)
Check("a changed RestedXP causes no error", ok, problem)
Check("...quests are then left out, and it says so once", Verdict(101) == "auction/costly" and #printed == 1
  and printed[1]:find("RestedXP", 1, true) ~= nil, printed[1])
printed = {}
SlashCmdList.SMOOTHBRAIN("")
Check("...and /smooth repeats it", printed[1] ~= nil and printed[1]:find("couldn't read RestedXP", 1, true) ~= nil, printed[1])

return table.concat(results, "\n"), results.failed and true or false
"""

if __name__ == "__main__":
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.globals().ADDON_DIR = ADDON
    run = rt.eval("function(src) return assert(loadstring(src, '@test'))() end")
    try:
        text, failed = run(HARNESS)
    except Exception as exc:
        text, failed = f"ERROR {exc}", True
    print(text)
    print("\nOVERALL:", "FAILURES" if failed else "ALL PASSED")
    sys.exit(1 if failed else 0)
