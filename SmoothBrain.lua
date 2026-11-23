-- Smooth Brain: stop thinking about your bags. Marks each item in them as one
-- to vendor, auction, disenchant, keep, keep for a quest, or delete.
-- Vendoring an item costs you the difference between what a vendor pays and
-- what it costs to buy again, from a vendor or the auction house. When that
-- difference, for everything you carry of it, is within your limit, it is
-- marked "vendor it". Items a RestedXP guide needs for a later quest are
-- judged more carefully (see ns.Decide in Logic.lua). Quest items whose quests
-- are all done, by RestedXP's or Questie's account, are marked as leftovers.
-- TradeSkillMaster and Auctionator supply the prices (/smooth prices says which
-- to use). The verdict shows on item tooltips, as
-- a marker on bag slots (Bagnon, Baganator, BetterBags, EllesmereUI and the
-- game's own bags), and in the /smooth list. An item you lock (middle-click it, or
-- /smooth lock) is kept without being judged, and shows a padlock. Gear in one
-- of your equipment sets, and what your class casts with, is kept as well.
--
-- The decision itself is in Logic.lua; this file gathers the facts.
local ADDON, ns = ...

local DEFAULTS = {
  limit = 500,     -- copper: vendor when buying your stack back costs at most this much more than a vendor pays
  tooltip = true,  -- add the verdict to item tooltips: one line
  explain = false, -- ...with the reason in full under it, not only while Shift is held (/smooth tooltip full)
  icons = true,    -- mark bag slots
  flash = true,    -- when a pickup fails because your bags are full, flash the stacks you'd lose least by deleting
  onboarded = false, -- the setup window (Setup.lua) has been seen
  prices = "both", -- whose prices: "tsm", "auctionator", or "both" (for each item, whichever saw it for sale last)
  ignore = {},     -- [itemID] = true: never judge it; false: judge it although it is a tool (/smooth ignore)
  locked = {},     -- [itemID] = true: yours to keep, whatever it is worth (middle-click it, or /smooth lock)
  lockclick = true, -- a middle-click on an item in your bags locks or unlocks it
  sets = true,     -- keep gear that is in one of your equipment sets, whatever it is worth (/smooth sets)
  reagents = true, -- keep what your class casts with, whatever it is worth (/smooth reagents)
  companion = true, -- take Forever Companion's price when it saw the item on the auction house last (/smooth companion)
}
local settings = DEFAULTS

local GetItemInfo = (C_Item and C_Item.GetItemInfo) or GetItemInfo
local GetItemSpell = (C_Item and C_Item.GetItemSpell) or GetItemSpell   -- the spell behind an item's "Use:", if it has one
-- The bags you carry: the backpack, four bags, and on newer clients the reagent bag after them.
local LAST_BAG = NUM_TOTAL_EQUIPPED_BAG_SLOTS or NUM_BAG_SLOTS or 4
local BIND_ON_PICKUP, BIND_QUEST = 1, 4
local CONSUMABLE, WEAPON, ARMOR, QUEST_ITEM, FISHING_POLE = 0, 2, 4, 12, 20
local UNCOMMON, DISENCHANT = 2, 13262   -- green quality; the Disenchant spell
-- Things you carry to use, not to sell: bags, ammunition, quivers and keys.
local NOT_FOR_SALE = { [1] = true, [6] = true, [11] = true, [13] = true }
local DROP_COUNT, FLASH_SECONDS = 3, 8   -- how many stacks flash when the bags are full, and for how long
-- Profession tools, left alone unless you /smooth ignore them back in. Fishing
-- poles are recognised by their kind as well.
local TOOLS = {
  [2901] = true,   -- Mining Pick
  [7005] = true,   -- Skinning Knife
  [12709] = true,  -- Finkle's Skinner
  [5956] = true,   -- Blacksmith Hammer
  [6219] = true,   -- Arclight Spanner
  [10498] = true,  -- Gyromatic Micro-Adjustor
  [9149] = true,   -- Philosopher's Stone
  [6218] = true,   -- Runed Copper Rod
  [6339] = true,   -- Runed Silver Rod
  [11130] = true,  -- Runed Golden Rod
  [11145] = true,  -- Runed Truesilver Rod
  [16207] = true,  -- Runed Arcanite Rod
  [4471] = true,   -- Flint and Tinder
  [5060] = true,   -- Thieves' Tools
  [15846] = true,  -- Salt Shaker
  [6256] = true,   -- Fishing Pole
  [6365] = true,   -- Strong Fishing Pole
  [6366] = true,   -- Darkwood Fishing Pole
  [6367] = true,   -- Big Iron Fishing Pole
  [12225] = true,  -- Blump Family Fishing Pole
  [19022] = true,  -- Nat Pagle's Extreme Angler FC-5000
  [19970] = true,  -- Arcanite Fishing Pole
  [6948] = true,   -- Hearthstone
}
-- What each class carries to cast with: spell reagents, and a rogue's powders
-- and poisons. Your own class's are kept whatever they would fetch; another
-- class's are priced like anything else. (Hunters and warriors carry none;
-- ammunition is left alone anyway.)
local REAGENTS = {
  DRUID = { 17021, 17026, 17034, 17035, 17036, 17037, 17038 },   -- Wild Berries, Wild Thornroot, and the five seeds
  MAGE = { 17020, 17031, 17032, 17056 },   -- Arcane Powder, Rune of Teleportation, Rune of Portals, Light Feather
  PALADIN = { 17033, 21177 },              -- Symbol of Divinity, Symbol of Kings
  PRIEST = { 17028, 17029, 17056 },        -- Holy Candle, Sacred Candle, Light Feather
  ROGUE = {
    5140, 5530,                            -- Flash Powder, Blinding Powder
    6947, 6949, 6950, 8926, 8927, 8928,    -- Instant Poison, every rank
    2892, 2893, 8984, 8985, 20844,         -- Deadly Poison
    3775, 3776,                            -- Crippling Poison
    5237, 6951, 9186,                      -- Mind-numbing Poison
    10918, 10920, 10921, 10922,            -- Wound Poison
  },
  SHAMAN = { 17030, 17057, 17058 },        -- Ankh, Shiny Fish Scales, Fish Oil
  WARLOCK = { 6265, 5565, 16583 },         -- Soul Shard, Infernal Stone, Demonic Figurine
}
-- One marker per verdict, in the bottom left of the slot.
local MARKS = {
  vendor = "Interface\\MoneyFrame\\UI-GoldIcon",              -- gold coin
  auction = "Interface\\AddOns\\" .. ADDON .. "\\auction",    -- gavel (our own picture)
  keep = "Interface\\RaidFrame\\ReadyCheck-Ready",            -- green tick
  quest = "Interface\\GossipFrame\\AvailableQuestIcon",       -- yellow exclamation mark
  free = "Interface\\RaidFrame\\ReadyCheck-NotReady",         -- red cross: safe to delete
  locked = "Interface\\AddOns\\" .. ADDON .. "\\lock",        -- padlock (our own picture): you locked it
  -- the Disenchant spell's own picture, or failing that Strange Dust
  disenchant = (C_Spell and C_Spell.GetSpellTexture and C_Spell.GetSpellTexture(DISENCHANT))
    or (GetSpellTexture and GetSpellTexture(DISENCHANT)) or "Interface\\Icons\\INV_Enchant_DustStrange",
}

local function IsEnchanter()
  if C_SpellBook and C_SpellBook.IsSpellKnown then
    local ok, known = pcall(C_SpellBook.IsSpellKnown, DISENCHANT)
    if ok and known then
      return true
    end
  end
  return (IsPlayerSpell ~= nil and IsPlayerSpell(DISENCHANT) == true)
    or (IsSpellKnown ~= nil and IsSpellKnown(DISENCHANT) == true)
end

-- The same, asked once and remembered: it only changes when you learn a
-- profession, and then it is asked again (SkillsChanged, further down).
local enchanter
local function Enchanter()
  if enchanter == nil then
    enchanter = IsEnchanter()
  end
  return enchanter
end

local function Say(text)
  print("|cffffd200Smooth Brain|r: " .. text)
end

local function QuestDone(questID)
  if C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted then
    return C_QuestLog.IsQuestFlaggedCompleted(questID) == true
  end
  return IsQuestFlaggedCompleted ~= nil and IsQuestFlaggedCompleted(questID) == true
end

local function OnQuest(questID)
  if C_QuestLog and C_QuestLog.IsOnQuest then
    return C_QuestLog.IsOnQuest(questID) == true
  end
  return GetQuestLogIndexByID ~= nil and (GetQuestLogIndexByID(questID) or 0) > 0
end

---------------------------------------------------------------------------
-- RestedXP: which items a guide's quest needs, and how many
---------------------------------------------------------------------------
-- RestedXP keeps its tables to itself, but it is an AceAddon, and AceAddon
-- hands out the addon's own table. questItemList is [itemID] = questID, and
-- turnInList is [questID] = { { guide, step, name }, ... }: the same two
-- tables behind RestedXP's own "Item used in guide" tooltip line.
local rxp
local function RXP()
  if not rxp then
    local ace = LibStub and LibStub("AceAddon-3.0", true)
    local found = ace and ace:GetAddon("RXPGuides", true)
    if found and type(found.questItemList) == "table" and type(found.turnInList) == "table"
      and type(found.IsGuideActive) == "function" and type(found.IsStepShown) == "function" then
      rxp = found
    end
  end
  return rxp
end

-- How many of an item a guide's own "collect" steps ask for, or nil: the
-- steps for this quest if there are any, else any step collecting the item.
local function CollectQuantity(guide, itemID, questID)
  local forQuest, any
  for _, step in pairs(type(guide.steps) == "table" and guide.steps or {}) do
    for _, element in pairs(type(step) == "table" and type(step.elements) == "table" and step.elements or {}) do
      if type(element) == "table" and element.tag == "collect" and element.id == itemID
        and type(element.qty) == "number" and element.qty > 0 and element.qty < 1000 then
        any = math.max(any or 0, element.qty)
        if element.questId == questID then
          forQuest = math.max(forQuest or 0, element.qty)
        end
      end
    end
  end
  return forQuest or any
end

local quantities = {}   -- [itemID] = quantity or false; guides are long, so each item is looked up once

-- { questID, guides = { names }, needed = quantity or nil } when a guide that
-- applies to this character turns in a quest using the item; else nil. The
-- same test RestedXP's tooltip makes.
local function Need(itemID)
  local source = RXP()
  local questID = source and source.questItemList[itemID]
  local entries = questID and source.turnInList[questID]
  if type(entries) ~= "table" then
    return nil
  end
  local guides, seen, needed = {}, {}, quantities[itemID]
  for _, entry in ipairs(entries) do
    local guide, step = entry.guide, entry.step
    if type(guide) == "table" and source.IsGuideActive(guide) and not guide.lowPrio
      and (type(step) ~= "table" or source.IsStepShown(step, "GroupCheck")) then
      local name = entry.name or guide.name
      if name and not seen[name] then
        seen[name] = true
        guides[#guides + 1] = name
      end
      if needed == nil then
        local quantity = CollectQuantity(guide, itemID, questID)
        if quantity then
          quantities[itemID] = math.max(quantities[itemID] or 0, quantity)
        end
      end
    end
  end
  if #guides == 0 then
    return nil
  end
  if quantities[itemID] == nil then
    quantities[itemID] = false
  end
  return { questID = questID, guides = guides, needed = quantities[itemID] or nil }
end

---------------------------------------------------------------------------
-- Questie: which quests an item belongs to, for spotting leftovers
---------------------------------------------------------------------------
-- Returns Questie's database and player modules, or nil; and, as a second
-- value, true when Questie is installed but hasn't finished starting. Until
-- then it calls every race- or class-restricted quest "not for you", which
-- would make leftovers of items an open quest still needs. Once found, the
-- two modules are remembered until everything is judged afresh (Forget).
local questieFound   -- { database, player }
local function Questie()
  if type(QuestieLoader) ~= "table" or type(QuestieLoader.ImportModule) ~= "function" then
    return nil
  end
  local addon = _G.Questie
  if type(addon) ~= "table" or not (addon.started == true or (type(addon.API) == "table" and addon.API.isReady == true)) then
    return nil, true
  end
  if questieFound then
    return questieFound[1], questieFound[2]
  end
  local ok, db = pcall(QuestieLoader.ImportModule, QuestieLoader, "QuestieDB")
  if not ok or type(db) ~= "table" or type(db.QueryItemSingle) ~= "function"
    or type(db.QueryQuestSingle) ~= "function" then
    return nil
  end
  local okPlayer, player = pcall(QuestieLoader.ImportModule, QuestieLoader, "QuestiePlayer")
  questieFound = { db, okPlayer and type(player) == "table" and player or nil }
  return questieFound[1], questieFound[2]
end

-- Whether a quest in your log has all its objectives met and only waits to be handed in.
local function QuestReady(questID)
  if C_QuestLog and C_QuestLog.IsComplete then
    return C_QuestLog.IsComplete(questID) == true
  end
  return IsQuestComplete ~= nil and IsQuestComplete(questID) == true
end

-- Whether handing a quest in takes the item: it is one of the quest's "collect"
-- objectives, by the game's own list or Questie's. Deleting such an item
-- un-completes the quest, so when it can't be told, the answer is yes.
local function TakenAtHandIn(db, questID, itemID, itemName)
  local objectives = C_QuestLog and C_QuestLog.GetQuestObjectives and C_QuestLog.GetQuestObjectives(questID)
  if type(objectives) ~= "table" or type(itemName) ~= "string" or itemName == "" then
    return true
  end
  for _, objective in pairs(objectives) do
    if type(objective) == "table" and objective.type == "item" and type(objective.text) == "string"
      and objective.text:find(itemName, 1, true) then
      return true
    end
  end
  local ok, listed = pcall(db.QueryQuestSingle, questID, "objectives")
  if not ok then
    return true
  end
  local items = type(listed) == "table" and listed[3]
  for _, entry in pairs(type(items) == "table" and items or {}) do
    if type(entry) == "table" and entry[1] == itemID then
      return true
    end
  end
  return false
end

-- true when Questie lists quests for the item and every one this character
-- can take is finished with it; false when one still needs it (or can be
-- repeated); nil when Questie has nothing on it. A quest is finished with the
-- item once it is handed in, or once it is complete and the hand-in doesn't
-- take the item (second value "ready"). When a complete quest's hand-in does
-- take it, the second value is "handin". The third value is true when the
-- item is one that starts a quest.
local function QuestsAllDone(itemID, itemName)
  local db, player = Questie()
  if not db then
    return nil, player == true and "wait" or nil   -- "wait": Questie is still starting
  end
  local quests = {}
  local ok, related = pcall(db.QueryItemSingle, itemID, "relatedQuests")
  if ok and type(related) == "table" then
    for _, questID in pairs(related) do
      quests[#quests + 1] = questID
    end
  end
  local okStart, starts = pcall(db.QueryItemSingle, itemID, "startQuest")
  local starter = okStart and type(starts) == "number" and starts > 0
  if starter then
    quests[#quests + 1] = starts
  end
  local mine, ready = 0, false
  for _, questID in ipairs(quests) do
    if type(questID) == "number" then
      local forMe = true
      if player and player.HasRequiredRace and player.HasRequiredClass then
        local okRace, races = pcall(db.QueryQuestSingle, questID, "requiredRaces")
        local okClass, classes = pcall(db.QueryQuestSingle, questID, "requiredClasses")
        forMe = (not okRace or player.HasRequiredRace(races) ~= false)
          and (not okClass or player.HasRequiredClass(classes) ~= false)
      end
      if forMe then
        mine = mine + 1
        if OnQuest(questID) or not QuestDone(questID) then
          if not (OnQuest(questID) and QuestReady(questID)) then
            return false
          elseif TakenAtHandIn(db, questID, itemID, itemName) then
            return false, "handin"
          end
          ready = true   -- only a tool for a quest that is now complete
        end
      end
    end
  end
  if mine == 0 then
    return nil, nil, starter
  end
  return true, ready and "ready" or nil, starter
end

---------------------------------------------------------------------------
-- Your quest log: the items your quests ask for
---------------------------------------------------------------------------
-- The game's own word, and the only one there is for a quest no addon knows
-- about. RestedXP and Questie tie an item to the quests they have on record;
-- an item can go on to a later quest they have nothing on, and then only the
-- quest log says it is still wanted.
--
-- { names = { [item name] = questID }, loose = { { objective text, questID } },
--   unsure = true when part of the log can't be read, signature = text that
--   changes when any of this does }
local questLog
local builtSignature   -- of the quest log the verdicts now held were judged by

-- The item an objective names: "3/8 Corrupted Brain Stem" and "Corrupted Brain
-- Stem: 3/8" both give the name. "" while the game is still loading it; nil
-- for a text in neither form.
local function ObjectiveItem(text)
  local name = text:match("^%d+%s*/%s*%d+%s+(.+)$") or text:match("^(.-)%s*:%s*%d+%s*/%s*%d+$")
  return name and name:match("^%s*(.-)%s*$") or nil
end

local function ReadQuest(log, questID, index)
  local objectives = C_QuestLog and C_QuestLog.GetQuestObjectives and C_QuestLog.GetQuestObjectives(questID)
  if type(objectives) ~= "table" then
    objectives = {}   -- an older client: the lines are asked for by the quest's place in the log
    for line = 1, (GetNumQuestLeaderBoards and GetQuestLogLeaderBoard and GetNumQuestLeaderBoards(index)) or 0 do
      local text, kind = GetQuestLogLeaderBoard(line, index)
      objectives[line] = { text = text, type = kind }
    end
  end
  for _, objective in pairs(objectives) do
    if type(objective) == "table" and objective.type == "item" then
      local text = objective.text
      local name = type(text) == "string" and text ~= "" and ObjectiveItem(text)
      if name == "" or name == false then
        log.unsure = true   -- the game hasn't the item's name yet
      elseif name then
        log.names[name] = log.names[name] or questID
      else
        log.loose[#log.loose + 1] = { text, questID }
      end
    end
  end
end

local function QuestLog()
  if questLog then
    return questLog
  end
  local log = { names = {}, loose = {}, unsure = false }
  local parts = {}   -- everything a verdict can hang on, for the signature
  local ok = pcall(function()
    local GetInfo = C_QuestLog and C_QuestLog.GetInfo
    local seen = 0
    for index = 1, 200 do
      local questID, header
      if GetInfo then
        local info = GetInfo(index)
        if type(info) ~= "table" then
          break
        end
        questID, header = info.questID, info.isHeader
      elseif GetQuestLogTitle then
        local title, _, _, isHeader, _, _, _, id = GetQuestLogTitle(index)
        if not title then
          break
        end
        questID, header = id, isHeader
      else
        break
      end
      if not header and type(questID) == "number" and questID > 0 then
        seen = seen + 1
        parts[#parts + 1] = questID .. (QuestReady(questID) and "!" or "")   -- "!": complete, waiting to be handed in
        ReadQuest(log, questID, index)
      end
    end
    -- Quests under a folded header are counted by the game but can't be read.
    local Count = (C_QuestLog and C_QuestLog.GetNumQuestLogEntries) or GetNumQuestLogEntries
    local _, quests
    if Count then
      _, quests = Count()
    end
    if type(quests) == "number" and quests > seen then
      log.unsure = true
    end
  end)
  if not ok then
    log.unsure = true   -- the quest log isn't the shape this was written for
  end
  for name, questID in pairs(log.names) do
    parts[#parts + 1] = name .. "=" .. questID
  end
  for _, entry in ipairs(log.loose) do
    parts[#parts + 1] = entry[1] .. "=" .. entry[2]
  end
  table.sort(parts)
  log.signature = table.concat(parts, "|") .. (log.unsure and "|?" or "")
  questLog, builtSignature = log, log.signature
  return log
end

-- The quest in your log that asks for an item of this name, if one does.
local function LogWants(itemName)
  if type(itemName) ~= "string" or itemName == "" then
    return nil
  end
  local log = QuestLog()
  if log.names[itemName] then
    return log.names[itemName]
  end
  for _, entry in ipairs(log.loose) do
    if entry[1]:find(itemName, 1, true) then
      return entry[2]
    end
  end
  return nil
end

---------------------------------------------------------------------------
-- Prices: TradeSkillMaster's and Auctionator's
---------------------------------------------------------------------------
-- A TradeSkillMaster price source for an item (copper, or a plain number for
-- dbnumauctions and dbregionsalerate), or nil when it has none. The item is
-- given the way TradeSkillMaster writes it: "i:" and its number.
local function TSMValue(source, itemString)
  if not (TSM_API and TSM_API.GetCustomPriceValue) then
    return nil
  end
  local ok, value = pcall(TSM_API.GetCustomPriceValue, source, itemString)
  if ok and type(value) == "number" and value > 0 then
    return value
  end
  return nil
end

local function TSM(source, itemID)
  return TSMValue(source, "i:" .. itemID)
end

-- One of Auctionator's lookups (Auctionator.API.v1) for an item, or nil.
local function Atr(method, itemID)
  local api = type(Auctionator) == "table" and type(Auctionator.API) == "table" and Auctionator.API.v1
  local lookup = type(api) == "table" and api[method]
  if type(lookup) ~= "function" then
    return nil
  end
  local ok, value = pcall(lookup, ADDON, itemID)
  if ok and type(value) == "number" and value >= 0 then
    return value
  end
  return nil
end

-- Forever Companion's own note of an item: its lowest price, how many it
-- counted for sale, how many seconds ago that was, and when (its own stamp,
-- which tells one note from the next). It notes prices whenever the auction
-- house shows them to you, so its price is often the newest there is.
local Now = time or (os and os.time)
local function Companion(itemID)
  local companion = ForeverCompanion
  local lookup = type(companion) == "table" and companion.GetAuctionEntry
  if type(lookup) ~= "function" then
    return nil
  end
  local ok, entry = pcall(lookup, companion, itemID)
  if not ok or type(entry) ~= "table" or type(entry.m) ~= "number" or entry.m <= 0 or type(entry.t) ~= "number" then
    return nil
  end
  local listed = type(entry.q) == "number" and entry.q > 0 and entry.q or nil
  return entry.m, listed, math.max(0, Now() - entry.t), entry.t
end

local function UseTSM()
  return settings.prices ~= "auctionator" and TSM_API ~= nil and TSM_API.GetCustomPriceValue ~= nil
end

local function UseAuctionator()
  return settings.prices ~= "tsm" and type(Auctionator) == "table" and type(Auctionator.API) == "table"
    and type(Auctionator.API.v1) == "table"
end

local function UseCompanion()
  return settings.companion and type(ForeverCompanion) == "table" and type(ForeverCompanion.GetAuctionEntry) == "function"
end

-- A price Forever Companion saw on the auction house within this many seconds
-- is what the auction house shows now: it is given with how many are listed,
-- not with how long ago it was seen.
local LIVE_SECONDS = 3600
local DAY, STALE_DAYS = 86400, 21   -- a price of your own not seen for three weeks is no price

-- When TradeSkillMaster's auction prices were taken. It doesn't say, but its
-- desktop app's data reaches it through one global function as the game
-- loads, each set headed by the time it was downloaded. That function is
-- listened in on (TradeSkillMaster's own is called as before, with what it was
-- given) and the time of the set with the lowest buyouts noted, by realm, as
-- the app may bring several: [realm, in small letters] = time.
local loadedAt = Now()   -- when the game read this file: your login, or the last /reload
local tsmTimes = {}
local tsmSeen   -- the time worked out from them, kept until everything is judged afresh
if type(TSM_APPHELPER_LOAD_DATA) == "function" then
  local deliver = TSM_APPHELPER_LOAD_DATA
  TSM_APPHELPER_LOAD_DATA = function(tag, realm, data, ...)
    pcall(function()
      local head = type(realm) == "string" and type(data) == "string" and data:sub(1, 400)
      local at = head and head:find('"minBuyout"', 1, true) and tonumber(head:match("downloadTime=(%d+)"))
      if at then
        tsmTimes[realm:lower()] = at
        tsmSeen = nil
      end
    end)
    return deliver(tag, realm, data, ...)
  end
end

-- The time of your own realm's prices; failing that, of the newest set that
-- came. When none was caught (TradeSkillMaster loaded its data before this
-- file was read, or brings it some other way), they are taken to be an hour
-- older than your login: its app fetches them about hourly, and the game only
-- reads them when it loads. It is the same for every item, so it is worked
-- out once.
local function TSMSeen()
  if tsmSeen then
    return tsmSeen
  end
  local realm, faction = GetRealmName and GetRealmName(), UnitFactionGroup and UnitFactionGroup("player")
  local at = type(realm) == "string" and type(faction) == "string" and tsmTimes[(realm .. "-" .. faction):lower()]
  if not at then
    for _, other in pairs(tsmTimes) do
      at = math.max(at or 0, other)
    end
  end
  tsmSeen = at or (loadedAt - LIVE_SECONDS)
  return tsmSeen
end

-- Auctionator only notes the day it last saw an item for sale (its days
-- start at midnight). Its price counts as seen when that day began: on the
-- day itself it can't say it saw the item any later than that.
--
-- The time of its last scan is not taken instead, as it was in 2.8. A scan is
-- stamped when it starts, whether or not it ever reaches the item, so a price
-- from hours earlier passed for the newest and was believed over a newer
-- TradeSkillMaster snapshot (reported with Raw Winter Squid: 25s from an
-- afternoon scan, quoted in place of 5s 95c).
local function AuctionatorSeen(days)
  local now = Now()
  local constants = Auctionator.Constants
  local zero = type(constants) == "table" and constants.SCAN_DAY_0
  if type(zero) ~= "number" then
    return now - (days + 1) * DAY   -- no telling when its days begin: a full day back at the latest
  end
  return zero + (math.floor((now - zero) / DAY) - days) * DAY
end

-- What the price addons know about an item. For the lowest auction price,
-- whichever of them saw the item most recently is believed: TradeSkillMaster
-- (a snapshot from its desktop app, read when the game loads: an hour old at
-- best), Forever Companion (which notes prices as the auction house shows
-- them, to the second) or Auctionator (your scans and searches, to the day).
-- TradeSkillMaster's price comes with how many are listed, and so does one
-- Forever Companion saw within the hour; any other comes with how many days
-- ago the item was seen. Your own notes are dropped once that is over three
-- weeks.
--
-- Each lookup is a call into another addon, so only what can matter is asked
-- for. `gear`: its disenchant value as well. `dustOnly`: nothing but that
-- (something soulbound can't be auctioned or bought back, so no price for it
-- says anything). What it sells for across the region is only asked when
-- nobody has a price here.
--
-- What Forever Companion and Auctionator said is kept as it was given (noted,
-- notedCount, notedAt; scanPrice, scanAge, scanDust): they learn
-- new prices while you play, and PricesChanged compares these to tell which
-- items to judge again.
local function Market(itemID, gear, dustOnly)
  local market = { gear = gear or nil }
  local item = "i:" .. itemID
  local tsm, auctionator = UseTSM(), UseAuctionator()
  if not dustOnly then
    market.auction = true
    local now = Now()
    local price, at, by, days, count   -- the newest so far: ties go to whoever was asked first
    local buyout = tsm and TSMValue("dbminbuyout", item) or nil
    if buyout then
      price, at = buyout, TSMSeen()
    end
    if UseCompanion() then
      local noted, listed, age, stamp = Companion(itemID)
      market.noted, market.notedCount, market.notedAt = noted, listed, stamp
      if noted and age <= STALE_DAYS * DAY and (not at or now - age > at) then
        price, at, by, days, count = noted, now - age, "Forever Companion", math.floor(age / DAY), listed
      end
    end
    if auctionator then
      local noted, seen = Atr("GetAuctionPriceByItemID", itemID), Atr("GetAuctionAgeByItemID", itemID)
      market.scanPrice, market.scanAge = noted, seen
      if noted and noted > 0 and seen then
        local seenAt = AuctionatorSeen(seen)
        if not at or seenAt > at then
          price, at, by, days, count = noted, seenAt, "Auctionator", seen, nil
        end
      end
    end
    if price then
      market.ahPrice, market.ahBy = price, by
      if not by then
        market.ahListed = TSMValue("dbnumauctions", item) or 0   -- TradeSkillMaster's
      elseif by == "Forever Companion" and now - at <= LIVE_SECONDS then
        -- Seen just now: given with how many are listed, like TradeSkillMaster's
        -- (whose count stands in when Forever Companion took none).
        market.ahListed = count or (buyout and (TSMValue("dbnumauctions", item) or 0)) or nil
        market.ahSeen = not market.ahListed and 0 or nil
      else
        market.ahSeen = days
      end
    elseif tsm then
      market.regionSale = TSMValue("dbregionsaleavg", item)
    end
    market.vendorBuy = tsm and TSMValue("vendorbuy", item) or nil
    if auctionator and not market.vendorBuy then
      local vendor = Atr("GetVendorPriceByItemID", itemID)
      if vendor and vendor > 0 then
        market.vendorBuy = vendor
      end
    end
  end
  if gear then
    market.destroy = tsm and TSMValue("destroy", item) or nil
    market.destroyBy = market.destroy and "TradeSkillMaster" or nil
    if auctionator then
      -- A disenchant value is an estimate, worked out from the addon's own
      -- prices for the materials, and the two can be well apart. Where both
      -- have one, the lower is used: disenchanting has to be clearly worth it.
      local dust = Atr("GetDisenchantPriceByItemID", itemID)
      market.scanDust = dust
      if dust and dust > 0 and (not market.destroy or dust < market.destroy) then
        market.destroy, market.destroyBy = dust, "Auctionator"
      end
    end
  end
  return market
end

---------------------------------------------------------------------------
-- Your bags
---------------------------------------------------------------------------
local container = C_Container or {}
local NumSlots = container.GetContainerNumSlots or GetContainerNumSlots
local SlotInfo = container.GetContainerItemInfo or GetContainerItemInfo
local SlotItem = container.GetContainerItemID or GetContainerItemID
local QuestInfo = container.GetContainerItemQuestInfo or GetContainerItemQuestInfo

-- What you carry, all your bags together: [itemID] = { count, bound, and bag
-- and slot of one stack of it }. The game says which bag changed, so each bag
-- is kept as it was last read ([bag] = { [itemID] = { count, bound, slot } })
-- and only the ones that changed are read again, when the answer is next
-- wanted.
local carried
local bagStacks = {}
local staleBags = {}    -- [bag] = true: it changed since it was read
local allStale = true   -- every bag is to be read again
local rescuedAt         -- when they were last all read again on a slot's say-so (Paint)

-- A bag changed (BAG_UPDATE names it). With no bag named, any may have.
local function BagChanged(bag)
  rescuedAt = nil
  if type(bag) ~= "number" then
    allStale = true
  elseif bag >= 0 and bag <= LAST_BAG then
    staleBags[bag] = true
  end
end

local function ReadBag(bag)
  local stacks = {}
  for slot = 1, (NumSlots and NumSlots(bag)) or 0 do
    local info, count, _, _, _, _, _, _, _, itemID, isBound = SlotInfo(bag, slot)
    if type(info) == "table" then
      itemID, count, isBound = info.itemID, info.stackCount, info.isBound
    end
    if itemID then
      local stack = stacks[itemID]
      if not stack then
        stack = { count = 0, slot = slot }
        stacks[itemID] = stack
      end
      stack.count = stack.count + (count or 1)
      stack.bound = stack.bound or isBound or nil
    end
  end
  return stacks
end

-- Adds an item up over all the bags, as they were last read.
local function Total(itemID)
  local count, bound, bag, slot = 0, nil, nil, nil
  for index = 0, LAST_BAG do
    local stack = bagStacks[index] and bagStacks[index][itemID]
    if stack then
      count, bound = count + stack.count, bound or stack.bound
      if not bag then
        bag, slot = index, stack.slot
      end
    end
  end
  if not bag then
    carried[itemID] = nil
    return
  end
  local entry = carried[itemID]
  if not entry then
    entry = {}
    carried[itemID] = entry
  end
  entry.count, entry.bound, entry.bag, entry.slot = count, bound, bag, slot
end

local function Carried()
  if allStale or not carried then
    carried, allStale = {}, false
    for bag = 0, LAST_BAG do
      staleBags[bag] = nil
      bagStacks[bag] = ReadBag(bag)
    end
    for bag = 0, LAST_BAG do
      for itemID in pairs(bagStacks[bag]) do
        if not carried[itemID] then
          Total(itemID)
        end
      end
    end
  elseif next(staleBags) ~= nil then
    for bag in pairs(staleBags) do
      staleBags[bag] = nil
      local before = bagStacks[bag] or {}
      bagStacks[bag] = ReadBag(bag)
      for itemID in pairs(before) do
        Total(itemID)
      end
      for itemID in pairs(bagStacks[bag]) do
        if not before[itemID] then
          Total(itemID)
        end
      end
    end
  end
  return carried
end

-- A slot in one of your bags is seen to hold this item. If the bags weren't
-- known to hold it, they changed without the game saying which (or it hasn't
-- said yet): they are all read again, at most once a second.
local function Seen(itemID, bag)
  if type(bag) == "number" and bag >= 0 and bag <= LAST_BAG and not Carried()[itemID] and rescuedAt ~= Now() then
    rescuedAt, allStale = Now(), true
  end
end

-- Whether the game itself calls the item in a slot a quest item, and the quest
-- it starts if it is one of those.
local function SlotQuest(bag, slot)
  if not QuestInfo then
    return nil
  end
  local ok, isQuestItem, questID = pcall(QuestInfo, bag, slot)
  if not ok then
    return nil
  end
  if type(isQuestItem) == "table" then
    isQuestItem, questID = isQuestItem.isQuestItem, isQuestItem.questID
  end
  return isQuestItem == true, type(questID) == "number" and questID > 0 and questID or nil
end

-- The same for an item you carry. It is the item's own nature, the same for
-- every stack, so it is asked of one stack when the item is judged, and
-- remembered until everything is judged afresh. The third value is true when
-- that can't be asked just now: the slot the item was read in holds something
-- else (the bags changed a moment ago and haven't been read again).
local questFlags = {}   -- [itemID] = { whether it is a quest item, the quest it starts }
local function QuestFlags(itemID, mine)
  local known = questFlags[itemID]
  if not known then
    if not (mine.bag and mine.slot) or (SlotItem and SlotItem(mine.bag, mine.slot) ~= itemID) then
      return nil, nil, true
    end
    local questItem, startsQuest = SlotQuest(mine.bag, mine.slot)
    known = { questItem or false, startsQuest or false }
    questFlags[itemID] = known
  end
  return known[1] or nil, known[2] or nil
end

---------------------------------------------------------------------------
-- Kept without being priced: equipment sets, and what your class casts with
---------------------------------------------------------------------------
-- [itemID] = the name of the equipment set of yours it is in (true for a set
-- with no name to give); read again when the sets change. Only the sets' item
-- IDs are asked for. Where each piece is (C_EquipmentSet.GetItemLocations)
-- isn't needed here, and is left alone on purpose: on WoW Forever it is
-- reported to crash the game for some sets.
local setItems

local function SetOf(itemID)
  if not setItems then
    setItems = {}
    local sets = C_EquipmentSet
    if type(sets) == "table" and sets.GetEquipmentSetIDs and sets.GetItemIDs then
      -- If the game's answer isn't the shape this expects, no item is in a set.
      pcall(function()
        for _, setID in pairs(sets.GetEquipmentSetIDs() or {}) do
          local name = sets.GetEquipmentSetInfo and sets.GetEquipmentSetInfo(setID)
          for _, id in pairs(sets.GetItemIDs(setID) or {}) do
            if type(id) == "number" and id > 0 and not setItems[id] then
              setItems[id] = type(name) == "string" and name ~= "" and name or true
            end
          end
        end
      end)
    end
  end
  return setItems[itemID]
end

local reagents, reagentsOf   -- [itemID] = true for your class's (REAGENTS), and the class they were worked out for

local function Reagent(itemID)
  local class = UnitClass and select(2, UnitClass("player"))   -- the second answer: "SHAMAN", whatever the language
  if type(class) ~= "string" then
    return false   -- the game doesn't say what you are yet
  end
  if class ~= reagentsOf then
    reagents, reagentsOf = {}, class
    for _, id in ipairs(REAGENTS[class] or {}) do
      reagents[id] = true
    end
  end
  return reagents[itemID] == true
end

---------------------------------------------------------------------------
-- The verdict for an item you carry
---------------------------------------------------------------------------
-- [itemID] = { count, result or false, market }; emptied when quests or
-- settings change. `market` is what the price addons said when the item was
-- judged, if they were asked: see PricesChanged.
local verdicts = {}
local NO_MARKET = {}   -- stands for "no prices were asked for"

-- Tools are left alone unless /smooth ignore says otherwise; anything else is
-- judged unless /smooth ignore says otherwise.
local function Ignored(itemID, classID, subclassID)
  local choice = settings.ignore[itemID]
  if choice ~= nil then
    return choice
  end
  return TOOLS[itemID] == true or (classID == WEAPON and subclassID == FISHING_POLE)
end

local function Judge(itemID, mine)
  local name, _, quality, _, _, _, _, _, equipSlot, _, sellPrice, classID, subclassID, bindType, _, _, craftingReagent =
    GetItemInfo(itemID)
  if not name then
    return nil, true   -- the game hasn't loaded this item yet: ask again later
  end
  if Ignored(itemID, classID, subclassID) then
    return nil
  end
  local ok, need = pcall(Need, itemID)
  if not ok then
    -- RestedXP's data isn't the shape this was written for.
    if not ns.problem then
      Say("couldn't read RestedXP's item data, so quests are not taken into account. RestedXP may have changed.")
    end
    ns.problem = tostring(need)
    need = nil
  end
  local questDone = need ~= nil and QuestDone(need.questID)
  local quest = need ~= nil and not questDone   -- a guide needs it for a quest still to come
  if not need and NOT_FOR_SALE[classID] then
    return nil
  end
  local bound = mine.bound or bindType == BIND_ON_PICKUP or bindType == BIND_QUEST
  sellPrice = sellPrice or TSM("vendorsell", itemID) or 0
  local by = questDone and "RestedXP" or nil
  -- Quest items RestedXP's guides don't list: the game's own (the yellow-edged
  -- ones), and items Questie ties to a quest. Is the quest still to do, or is
  -- the item a leftover? Not asked of things you wear, which may be worth
  -- keeping whatever their quest.
  local questNote, questBrief, doneNote, hold   -- questBrief: the note in a few words, for the tooltip's one line
  -- Wearable: a weapon or armour. (The slot name alone won't do: the game gives
  -- things you can't wear a slot name of their own, not an empty one.)
  local wearable = classID == WEAPON or classID == ARMOR
    or (equipSlot ~= nil and equipSlot ~= "" and equipSlot ~= "INVTYPE_NON_EQUIP_IGNORE" and equipSlot ~= "INVTYPE_NON_EQUIP")
  -- Usable: it has a "Use:" of its own and isn't worn. A sleeping bag, a
  -- mount's reins, a salt shaker. Soulbound, such a thing is for using, not
  -- for selling (reported with the Cozy Sleeping Bag, marked to vendor). It
  -- only matters for something soulbound, so it is only asked of those.
  local usable = false
  if bound and not wearable and GetItemSpell then
    local ok, spell, spellID = pcall(GetItemSpell, itemID)
    usable = ok and (spell ~= nil or spellID ~= nil)
  end
  -- Quest items beyond a guide's "collect this": the game's own (the
  -- yellow-edged ones), and items Questie ties to a quest. This is asked even
  -- when RestedXP's quest for the item is done, because RestedXP knows one
  -- quest per item and another may still need it. An open quest keeps
  -- anything, gear included; only things you can't wear are called leftovers.
  local unsettled = false
  -- Before anything else, your quest log: an item one of your quests asks for
  -- is kept, whatever RestedXP, Questie or its price say. They only know the
  -- quests they have on record, and an item can go on to a quest they don't.
  local wanted = LogWants(name)
  if wanted then
    quest, hold, questDone, by = true, true, false, nil
    local ready = QuestReady(wanted)
    questNote = ready and "Its quest is complete: hand it in, and this item goes with it."
      or "A quest in your log asks for it."
    questBrief = ready and "hand its quest in" or "in your quest log"
  end
  if not quest then
    local flagged, starts, moved = QuestFlags(itemID, mine)   -- the game's own word: a quest item, and the quest it starts
    if moved then
      return nil, true   -- the bags changed a moment ago and aren't read yet: ask again later
    end
    local questItem = classID == QUEST_ITEM or bindType == BIND_QUEST or flagged
    if questItem or starts or sellPrice <= 0 or bound or questDone then
      local done, detail, starter = QuestsAllDone(itemID, name)   -- true, false, or nil when Questie has nothing on it
      unsettled = detail == "wait"                                 -- Questie is still starting: ask again later
      if starts and not QuestDone(starts) then
        done = false
      end
      if done == false then
        quest, hold, questDone, by = true, true, false, nil
        local opens = starts and not QuestDone(starts)
        questNote = opens and "It starts a quest you haven't done."
          or detail == "handin" and "Its quest is complete: hand it in, and this item goes with it."
          or "A quest you haven't finished needs it."
        questBrief = opens and "starts a quest" or detail == "handin" and "hand its quest in" or nil
      elseif (starts or starter) and not wearable then
        -- It starts a quest, that quest is done, and it is still in your bags:
        -- an item like that tends to be carried on to the next quest (the Titan
        -- Relic, wanted again by a quest nothing had on record). That its own
        -- quest is done says nothing about what it is for now.
        quest, hold, questDone, by = true, true, false, nil
        questNote = "It started a quest you have done, and may be wanted for the next one."
        questBrief = "the next quest may want it"
      elseif done == true and not wearable then
        if not questDone then
          questDone, by = true, "Questie"
        end
        doneNote = detail == "ready" and "its quest is complete, and handing it in doesn't take this item" or nil
      elseif done == nil and questItem and not questDone then
        quest, hold, questNote = true, true, "It is a quest item."
      end
    end
  end
  -- A leftover you couldn't get back is only called one when the whole quest
  -- log could be read: a quest under a folded header, or one still loading,
  -- may be the one that wants it.
  if questDone and not quest and (bound or sellPrice <= 0) and QuestLog().unsure then
    quest, hold, questDone, by = true, true, false, nil
    questNote = "Part of your quest log can't be read just now (a folded header, or quests still loading), so it is kept "
      .. "in case a quest there wants it."
    questBrief = "your quest log isn't read yet"
  end
  -- Disenchanting is compared for green or better weapons and armour.
  local gear = (quality or 0) >= UNCOMMON and (classID == WEAPON or classID == ARMOR)
  local onQuest = need ~= nil and quest and not hold and OnQuest(need.questID)
  -- Prices are only asked for where they can change the verdict: not for an
  -- item kept for its quest whatever it costs, and for a soulbound one only
  -- what disenchanting it would yield.
  local market = NO_MARKET
  if not (quest and (hold or onQuest)) and (not bound or gear) then
    market = Market(itemID, gear, bound)
  end
  local result = ns.Decide({
    count = mine.count,
    -- Something you use up, and would keep for that. Not food or a potion the
    -- game also marks as a crafting reagent (raw fish, say): that is a
    -- material, priced like cloth or ore (reported with Raw Winter Squid, 7c
    -- from a vendor and silvers at auction, marked "keep it").
    consumable = classID == CONSUMABLE and craftingReagent ~= true,
    usable = usable,
    quest = quest,
    questNote = questNote,
    questBrief = questBrief,
    doneNote = doneNote,
    needed = need and need.needed,
    hold = hold,
    onQuest = onQuest,
    questDone = questDone,
    bound = bound,
    quality = quality,
    vendorSell = sellPrice,
    vendorBuy = market.vendorBuy,
    ahPrice = market.ahPrice,
    ahListed = market.ahListed,
    ahSeen = market.ahSeen,
    ahBy = market.ahBy,
    regionSale = market.regionSale,
    destroy = market.destroy,
    destroyBy = market.destroyBy,
    noPrices = not (UseTSM() or UseAuctionator() or UseCompanion()),
    enchanter = Enchanter(),
  }, settings.limit)
  if result then
    result.itemID, result.by = itemID, by
    result.questID, result.guides = need and need.questID, need and need.guides
    -- How often its auctions sell is only ever said of an item to auction.
    if result.verdict == "auction" and result.why == "costly" and UseTSM() then
      result.saleRate = TSM("dbregionsalerate", itemID)
    end
  end
  return result, unsettled, market ~= NO_MARKET and market or nil
end

-- The verdict for an item in your bags, or nil when there is nothing to say:
-- tools, bags, ammunition and keys, items you /smooth ignore, and things you can
-- trade that a vendor buys but that have no price to buy them known. An item
-- you locked is not judged at all: it is kept, whatever it is (verdict
-- "locked"), and locking it counts for more than ignoring it. Gear in one of
-- your equipment sets, and what your class casts with, is kept the same way,
-- with the ordinary "keep": you carry those to use, so they aren't priced.
function ns.Check(itemID)
  local locked = settings.locked[itemID]
  if settings.ignore[itemID] and not locked then
    return nil
  end
  local mine = Carried()[itemID]
  if not mine or mine.count <= 0 then
    return nil
  end
  local known = verdicts[itemID]
  if known and known.count == mine.count then
    return known.result or nil
  end
  local result, later, market
  if locked then
    result = { verdict = "locked", why = "locked", itemID = itemID, count = mine.count }
  else
    local set = settings.sets and SetOf(itemID)
    if set then
      result = { verdict = "keep", why = "set", set = set ~= true and set or nil, itemID = itemID, count = mine.count }
    elseif settings.reagents and Reagent(itemID) then
      result = { verdict = "keep", why = "reagent", itemID = itemID, count = mine.count }
    else
      result, later, market = Judge(itemID, mine)
    end
  end
  if not later then
    verdicts[itemID] = { count = mine.count, result = result or false, market = market }
  end
  return result, later   -- later: the game hasn't loaded the item yet
end

---------------------------------------------------------------------------
-- Tooltip
---------------------------------------------------------------------------
local function OnTooltip(tooltip, data)
  if not settings.tooltip or (tooltip ~= GameTooltip and tooltip ~= ItemRefTooltip) then
    return
  end
  if tooltip.IsForbidden and tooltip:IsForbidden() then
    return
  end
  local itemID = type(data) == "table" and data.id
  if not itemID and tooltip.GetItem then
    local _, link = tooltip:GetItem()
    itemID = type(link) == "string" and tonumber(link:match("item:(%d+)"))
  end
  local result = itemID and ns.Check(itemID)
  if not result then
    return
  end
  -- The reason in full is a paragraph, and a tooltip has enough to read: it
  -- shows while Shift is held, or always with /smooth tooltip full.
  if settings.explain or (IsShiftKeyDown ~= nil and IsShiftKeyDown()) then
    tooltip:AddLine("Smooth Brain: " .. ns.HEADLINE[result.verdict], 1, 0.82, 0)
    tooltip:AddLine(ns.Explain(result, ns.Money), 0.8, 0.8, 0.8, true)
    return
  end
  -- Otherwise one line: the slot's marker, the verdict, and on the right the
  -- prices that decided it.
  local mark = MARKS[result.verdict]
  local verdict = (mark and ("|T" .. mark .. ":0|t ") or "") .. ns.TITLE[result.verdict]
  local brief = ns.Brief(result, ns.Money)
  if brief and tooltip.AddDoubleLine then
    tooltip:AddDoubleLine(verdict, brief, 1, 0.82, 0, 0.8, 0.8, 0.8)
  else
    tooltip:AddLine(verdict .. (brief and ("  |cffcccccc" .. brief .. "|r") or ""), 1, 0.82, 0)
  end
end

if TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall and Enum and Enum.TooltipDataType then
  TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, OnTooltip)
elseif GameTooltip and GameTooltip.HookScript then
  GameTooltip:HookScript("OnTooltipSetItem", OnTooltip)
end

---------------------------------------------------------------------------
-- Markers on bag slots
---------------------------------------------------------------------------
local slots = {}   -- [button] = { bag, slot } for the game's own bags, true for Bagnon's

local dropping = {}   -- [bag * 100 + slot] = the item whose stack there flashes as one to throw away

local function SlotKey(bag, slot)
  return bag * 100 + slot
end

-- Makes a texture fade in and out for as long as it is shown.
local function Pulse(texture)
  if not texture.CreateAnimationGroup then
    return
  end
  pcall(function()
    local group = texture:CreateAnimationGroup()
    local fade = group:CreateAnimation("Alpha")
    fade:SetFromAlpha(1)
    fade:SetToAlpha(0.15)
    fade:SetDuration(0.45)
    group:SetLooping("BOUNCE")
    texture.pulse = group
  end)
end

-- Whether any stack of an item is one of those flashing.
local function Dropping(itemID)
  for _, id in pairs(dropping) do
    if id == itemID then
      return true
    end
  end
  return false
end

-- Draws the marker for the item in a slot, or takes it away. The marker sits
-- bottom left unless `corner` says "TOPRIGHT", or "QUARTER": the top right
-- quarter of the button, whatever size that is. `merged`: the button stands
-- for every stack of the item, not only the one in this slot. `keep`: where
-- the marker is remembered, for a button that nothing may be written onto.
local function Paint(button, itemID, bag, slot, corner, merged, keep)
  keep = keep or button
  local mark
  if settings.icons and itemID then
    Seen(itemID, bag)
    local result = ns.Check(itemID)
    mark = result and MARKS[result.verdict]
  end
  local icon = keep.SmoothBrainIcon
  if mark and not icon then
    icon = button:CreateTexture(nil, "OVERLAY", nil, 7)   -- above the slot's own borders
    if corner == "QUARTER" then
      icon:SetPoint("TOPRIGHT", button, "TOPRIGHT", -1, -1)
      icon:SetPoint("BOTTOMLEFT", button, "CENTER")
    else
      icon:SetSize(16, 16)
      if corner == "TOPRIGHT" then
        icon:SetPoint("TOPRIGHT", -1, -1)
      else
        icon:SetPoint("BOTTOMLEFT", 1, 1)
      end
    end
    keep.SmoothBrainIcon = icon
  end
  if icon then
    if mark then
      icon:SetTexture(mark)
    end
    icon:SetShown(mark ~= nil)
  end
  -- A solid red wash over the whole slot, fading in and out, while it is one
  -- to throw away. (A faint highlight proved too easy to miss.)
  -- Only while the slot still holds the stack that was chosen: items get moved.
  local flash = itemID ~= nil and type(bag) == "number" and type(slot) == "number"
    and (dropping[SlotKey(bag, slot)] == itemID or (merged == true and Dropping(itemID)))
  local glow = keep.SmoothBrainFlash
  if flash and not glow then
    glow = button:CreateTexture(nil, "OVERLAY", nil, 6)   -- over the item, under the marker
    glow:SetAllPoints(button)
    glow:SetColorTexture(1, 0.05, 0.05, 0.65)
    Pulse(glow)
    keep.SmoothBrainFlash = glow
  end
  if glow then
    glow:SetShown(flash)
    if flash and glow.pulse then
      glow.pulse:Play()
    end
  end
end

local function InBags(bag)
  return type(bag) == "number" and bag >= 0 and bag <= LAST_BAG
end

-- Bagnon redraws a slot through Item:Update; the marker is added after it.
local function PaintBagnon(button)
  local bag = button.GetBag and button:GetBag()
  local itemID = type(button.info) == "table" and button.info.itemID
  Paint(button, InBags(bag) and itemID or nil, bag, button.GetID and button:GetID())
  slots[button] = true
end

local bagnonHooked
local function HookBagnon()
  local class = type(Bagnon) == "table" and Bagnon.Item
  if bagnonHooked or type(class) ~= "table" or type(class.Update) ~= "function" then
    return
  end
  hooksecurefunc(class, "Update", PaintBagnon)
  bagnonHooked = true
end

-- The game's own bags: each window redraws its slots through UpdateItems
-- (or, on older clients, ContainerFrame_Update).
local function PaintSlot(button, bag, slot)
  local itemID = InBags(bag) and type(slot) == "number" and SlotItem and SlotItem(bag, slot) or nil
  Paint(button, itemID, bag, slot)
  local where = slots[button]
  if type(where) == "table" then
    where[1], where[2] = bag, slot
  else
    slots[button] = { bag, slot }
  end
end

local function PaintWindow(window)
  if type(window) ~= "table" then
    return
  end
  if window.GetChildren then
    for _, child in ipairs({ window:GetChildren() }) do
      if type(child) == "table" and child.GetBagID and child.GetID then
        PaintSlot(child, child:GetBagID(), child:GetID())
      end
    end
  end
  local name = window.GetName and window:GetName()
  local index = 1
  while name and _G[name .. "Item" .. index] do
    local button = _G[name .. "Item" .. index]
    if not button.GetBagID and button.GetID and window.GetID then
      PaintSlot(button, window:GetID(), button:GetID())
    end
    index = index + 1
  end
end

local windowsHooked = {}
local function HookGameBags()
  if type(ContainerFrame_Update) == "function" and not windowsHooked.all then
    hooksecurefunc("ContainerFrame_Update", PaintWindow)
    windowsHooked.all = true
  end
  for index = 0, NUM_CONTAINER_FRAMES or 13 do
    local window = index == 0 and ContainerFrameCombinedBags or _G["ContainerFrame" .. index]
    if type(window) == "table" and type(window.UpdateItems) == "function" and not windowsHooked[window] then
      hooksecurefunc(window, "UpdateItems", PaintWindow)
      windowsHooked[window] = true
    end
  end
end

-- Baganator has its own way in: a "corner widget", which it creates, places
-- and shows for us. It starts in the bottom left corner; Baganator's own
-- settings (Customise, icon corners) move or remove it.
local function BaganatorUpdate(texture, details)
  local where = type(details) == "table" and details.itemLocation
  if not settings.icons or not details.itemID or type(where) ~= "table" or not InBags(where.bagID) then
    return false
  end
  Seen(details.itemID, where.bagID)
  local result, later = ns.Check(details.itemID)
  if later then
    return nil   -- Baganator asks again once the item has loaded
  end
  local mark = result and MARKS[result.verdict]
  if not mark then
    return false
  end
  texture:SetTexture(mark)
  return true
end

local baganatorHooked
local function HookBaganator()
  local api = type(Baganator) == "table" and Baganator.API
  if baganatorHooked or type(api) ~= "table" or type(api.RegisterCornerWidget) ~= "function" then
    return
  end
  baganatorHooked = true
  local ok, problem = pcall(api.RegisterCornerWidget, "Smooth Brain", "smooth_brain", BaganatorUpdate,
    function(itemButton)
      local texture = itemButton:CreateTexture(nil, "OVERLAY")
      texture:SetSize(16, 16)
      return texture
    end, { corner = "bottom_left", priority = 1 }, false)
  if not ok then
    Say("couldn't add the markers to Baganator (" .. tostring(problem) .. "). Baganator may have changed.")
  end
  -- A second widget for the stacks to throw away when the bags are full: a
  -- pulsing red "pass" sign, top left.
  pcall(api.RegisterCornerWidget, "Smooth Brain: throw away first", "smooth_brain_drop", function(texture, details)
    local where = type(details) == "table" and details.itemLocation
    local flash = type(where) == "table" and InBags(where.bagID) and type(where.slotIndex) == "number"
      and details.itemID ~= nil and dropping[SlotKey(where.bagID, where.slotIndex)] == details.itemID
    if flash and texture.pulse then
      texture.pulse:Play()
    end
    return flash
  end, function(itemButton)
    local texture = itemButton:CreateTexture(nil, "OVERLAY")
    texture:SetSize(28, 28)
    texture:SetTexture("Interface\\Buttons\\UI-GroupLoot-Pass-Up")
    Pulse(texture)
    return texture
  end, { corner = "top_left", priority = 1 }, true)
end

local function RefreshBaganator()
  local api = baganatorHooked and type(Baganator) == "table" and Baganator.API
  if type(api) == "table" and type(api.RequestItemButtonsRefresh) == "function" then
    local reasons = type(Baganator.Constants) == "table" and Baganator.Constants.RefreshReason
    pcall(api.RequestItemButtonsRefresh, reasons and reasons.ItemWidgets and { reasons.ItemWidgets } or nil)
  end
end

-- BetterBags says when it draws a slot (the message "item/Updated", with the
-- slot and the button its picture is on) and when it takes one away
-- ("item/Clearing"). It doesn't draw a slot again while the item in it stays
-- the same, so the slots are remembered here and repainted when a verdict
-- changes. The marker goes top right: BetterBags writes item levels bottom left.
local betterBags = {}   -- [slot] = the button BetterBags draws it on

local function PaintBetterBags(item, button)
  local data = type(item.currentData) == "table" and item.currentData or nil
  local bag, slot = data and data.bagid, data and data.slotid
  local itemID
  if data and not data.isItemEmpty and not item.isFreeSlot and InBags(bag) and type(slot) == "number" then
    -- The game is asked what the slot holds now: BetterBags redraws a moment
    -- after the bags change, and until it has, the slot gets no marker.
    itemID = SlotItem and SlotItem(bag, slot) or nil
    if itemID ~= (type(data.itemInfo) == "table" and data.itemInfo.itemID or nil) then
      itemID = nil
    end
  end
  -- With stackedCount the button stands for every stack of the item.
  Paint(button, itemID, bag, slot, "TOPRIGHT", data ~= nil and data.stackedCount ~= nil)
end

local betterBagsHooked, betterBagsTried, loggedIn
local function HookBetterBags()
  -- Not before login: BetterBags forgets who is listening when it starts up.
  if betterBagsTried or not loggedIn then
    return
  end
  local ace = LibStub and LibStub("AceAddon-3.0", true)
  local addon = ace and ace:GetAddon("BetterBags", true)
  if type(addon) ~= "table" or type(addon.GetModule) ~= "function" then
    return
  end
  betterBagsTried = true
  -- These run in the middle of BetterBags drawing its bags. A mistake here must
  -- not stop that, so it is caught, and handed to the game's error display.
  local function Guarded(work, ...)
    local fine, mistake = pcall(work, ...)
    if not fine and type(geterrorhandler) == "function" then
      geterrorhandler()(mistake)
    end
  end
  local function Drawn(item, button)
    if type(item) == "table" and type(button) == "table" and button.CreateTexture then
      betterBags[item] = nil   -- remembered only once it has been painted without a mistake
      PaintBetterBags(item, button)
      betterBags[item] = button
    end
  end
  local function Cleared(item)
    local button = item ~= nil and betterBags[item]
    if button then
      betterBags[item] = nil
      Paint(button, nil)
    end
  end
  local ok, problem = pcall(function()
    local events = addon:GetModule("Events")
    events:RegisterMessage("item/Updated", function(_, item, button)
      Guarded(Drawn, item, button)
    end)
    events:RegisterMessage("item/Clearing", function(_, item)
      Guarded(Cleared, item)
    end)
  end)
  if not ok then
    Say("couldn't add the markers to BetterBags (" .. tostring(problem) .. "). BetterBags may have changed.")
    return
  end
  betterBagsHooked = true
  -- Slots it drew before now.
  pcall(function()
    for _, item in pairs(addon:GetModule("ItemFrame").buttonsBySlotkey) do
      Guarded(Drawn, item, type(item) == "table" and item._decoration or nil)
    end
  end)
end

-- EllesmereUI's bags have a way in made for this: a painter, which they call
-- for every slot they draw (grid slots and list rows, the bags and the bank)
-- with the button and { bag, slot, info, itemLink }. Their rules for it:
-- nothing is written onto the button, which is one of the game's protected
-- ones; what is drawn goes on button._textOverlay, the frame over the item's
-- picture, and is kept track of here. The marker is the top right quarter of
-- the picture (16 pixels on a grid slot, less on a list row): they write item
-- levels top left and counts bottom right, and put their own junk coin and
-- binding text bottom left.
local ellesmere = {}   -- [button] = { host, bag, slot, itemID, merged, and the textures drawn on host }

local function PaintEllesmere(state)
  local itemID = state.itemID
  -- The game is asked what the slot holds now: this is also called when a
  -- verdict changes, and the item may have moved since EllesmereUI drew it.
  if itemID and (not SlotItem or SlotItem(state.bag, state.slot) ~= itemID) then
    itemID = nil
  end
  Paint(state.host, itemID, state.bag, state.slot, "QUARTER", state.merged, state)
end

local function EllesmereDrew(button, data)
  local host = type(button) == "table" and button._textOverlay
  if type(host) ~= "table" or not host.CreateTexture or type(data) ~= "table" then
    return
  end
  local state = ellesmere[button]
  if not state or state.host ~= host then
    if state then
      Paint(state.host, nil, nil, nil, "QUARTER", false, state)   -- its picture frame was replaced: clear the old one
    end
    state = { host = host }
    ellesmere[button] = state
  end
  local bag, slot = data.bag, data.slot
  local itemID = type(data.info) == "table" and data.info.itemID or nil
  if not (InBags(bag) and type(slot) == "number" and slot > 0) then
    itemID = nil   -- the bank, or a slot shown only as a placeholder
  end
  state.bag, state.slot, state.itemID = bag, slot, itemID
  state.merged = data._mergedCount ~= nil   -- a list row standing for every stack of the item
  PaintEllesmere(state)
end

local ellesmereTried, ellesmereMarked
local function HookEllesmere()
  local bags = type(EUI_Bags) == "table" and EUI_Bags or nil
  if ellesmereTried or not bags or type(bags.RegisterItemOverlayIcon) ~= "function" then
    return
  end
  ellesmereTried = true
  local ok, problem = pcall(bags.RegisterItemOverlayIcon, "SmoothBrain", EllesmereDrew)
  if not ok then
    Say("couldn't add the markers to EllesmereUI's bags (" .. tostring(problem) .. "). EllesmereUI may have changed.")
    return
  end
  ellesmereMarked = true
  -- Bags already open were drawn before it could ask: have them drawn again.
  if type(bags.RefreshInventory) == "function" and type(bags.IsShown) == "function" then
    pcall(function()
      if bags:IsShown() then
        bags:RefreshInventory()
      end
    end)
  end
end

local function RefreshIcons()
  for button, where in pairs(slots) do
    if where == true then
      PaintBagnon(button)
    else
      PaintSlot(button, where[1], where[2])
    end
  end
  for item, button in pairs(betterBags) do
    PaintBetterBags(item, button)
  end
  for _, state in pairs(ellesmere) do
    PaintEllesmere(state)
  end
  RefreshBaganator()
end

---------------------------------------------------------------------------
-- Bags full: flash the stacks you would lose least by deleting
---------------------------------------------------------------------------
-- Every stack marked delete, vendor or auction, cheapest first. A stack is
-- worth nothing if it is a leftover, what a vendor pays if it is one to
-- vendor, and its auction price if that is higher. Items to keep, to keep for
-- a quest or to disenchant, and items with no verdict, are never offered.
local function Cheapest()
  local stacks = {}
  for bag = 0, LAST_BAG do
    for slot = 1, (NumSlots and NumSlots(bag)) or 0 do
      local info, count, _, _, _, _, _, _, _, itemID = SlotInfo(bag, slot)
      if type(info) == "table" then
        itemID, count = info.itemID, info.stackCount
      end
      local result = itemID and ns.Check(itemID)
      local verdict = result and result.verdict
      if verdict == "free" or verdict == "vendor" or verdict == "auction" then
        local each = 0
        if verdict ~= "free" then
          each = math.max((result.gain or 0) / math.max(result.count, 1), verdict == "auction" and result.price or 0)
        end
        stacks[#stacks + 1] = { bag = bag, slot = slot, itemID = itemID, count = count or 1, value = each * (count or 1) }
      end
    end
  end
  table.sort(stacks, function(a, b)
    if a.value ~= b.value then
      return a.value < b.value
    elseif a.bag ~= b.bag then
      return a.bag < b.bag
    end
    return a.slot < b.slot
  end)
  return stacks
end

-- What is still lying in the loot window: the most any one stack there is
-- worth (what a vendor pays, or its auction price if it can be traded and
-- that is higher), and whether one of them is for a quest. nil when no loot
-- window with items is open.
local function Pending()
  local best, quest, any = 0, false, false
  for slot = 1, (GetNumLootItems and GetNumLootItems()) or 0 do
    local link = GetLootSlotLink and GetLootSlotLink(slot)
    local itemID = type(link) == "string" and tonumber(link:match("item:(%d+)"))
    if itemID then
      any = true
      local _, _, quantity, _, _, _, isQuestItem = GetLootSlotInfo(slot)
      local _, _, _, _, _, _, _, _, _, _, sellPrice, classID, _, bindType = GetItemInfo(itemID)
      local ok, need = pcall(Need, itemID)
      if isQuestItem or classID == QUEST_ITEM or bindType == BIND_QUEST
        or (ok and need ~= nil and not QuestDone(need.questID)) then
        quest = true
      end
      local each = sellPrice or 0
      if bindType ~= BIND_ON_PICKUP and bindType ~= BIND_QUEST then
        local market = Market(itemID, false)
        each = math.max(each, market.ahPrice or market.regionSale or 0)
      end
      best = math.max(best, each * (tonumber(quantity) or 1))
    end
  end
  if not any then
    return nil
  end
  return best, quest
end

local flashRound = 0

local function StopFlashing()
  if next(dropping) ~= nil then
    dropping = {}
    RefreshIcons()
  end
end

-- Picks the stacks to flash: the cheapest few, or only those worth less than
-- `below`. Returns them, cheapest first.
local flashBelow
local function ChooseStacks()
  local stacks, chosen = Cheapest(), {}
  dropping = {}
  for index = 1, math.min(DROP_COUNT, #stacks) do
    if flashBelow and stacks[index].value >= flashBelow then
      break
    end
    chosen[index] = stacks[index]
    dropping[SlotKey(stacks[index].bag, stacks[index].slot)] = stacks[index].itemID
  end
  RefreshIcons()
  return chosen
end

-- Flashes them for a few seconds.
local function FlashCheapest(below)
  flashBelow = below
  local chosen = ChooseStacks()
  flashRound = flashRound + 1
  local round = flashRound
  if C_Timer and C_Timer.After then
    C_Timer.After(FLASH_SECONDS, function()
      if round == flashRound then
        StopFlashing()
      end
    end)
  end
  return chosen
end

local function HasFreeSlot()
  local Free = container.GetContainerNumFreeSlots or GetContainerNumFreeSlots
  -- Only ordinary bags count: room in a quiver or the reagent bag doesn't help.
  for bag = 0, LAST_BAG do
    local free, kind = 0, 0
    if Free then
      free, kind = Free(bag)
    end
    if (free or 0) > 0 and (kind or 0) == 0 then
      return true
    end
  end
  return false
end

-- "Inventory is full": the message arrives alone on older clients, after its number on newer ones.
local function IsBagsFull(first, second)
  return (ERR_INV_FULL ~= nil and (first == ERR_INV_FULL or second == ERR_INV_FULL))
    or (LE_GAME_ERR_INV_FULL ~= nil and first == LE_GAME_ERR_INV_FULL)
end

---------------------------------------------------------------------------
-- /smooth
---------------------------------------------------------------------------
-- Verdicts depend on quests and settings as well as on what you carry. This
-- drops everything that was worked out, so all of it is asked again.
local function Forget()
  verdicts = {}
  quantities = {}
  questLog = nil
  setItems = nil
  questFlags = {}
  questieFound, tsmSeen, enchanter = nil, nil, nil
end

local ORDER = { vendor = 1, free = 2, disenchant = 3, auction = 4, keep = 5, quest = 6, locked = 7 }

-- The items to vendor or delete; with everything, the rest as well.
local function List(everything)
  if not (UseTSM() or UseAuctionator() or UseCompanion()) then
    -- Without prices there is still something to say: see "Without a price addon" in the README.
    Say("no prices are available (" .. (settings.prices == "both"
      and "neither TradeSkillMaster nor Auctionator is running"
      or ("prices are set to " .. settings.prices .. " only, and it isn't running; /smooth prices both uses either"))
      .. "), so only quest items, leftovers, gray junk and soulbound items are judged.")
  end
  local rows, others = {}, 0
  for itemID in pairs(Carried()) do
    local result = ns.Check(itemID)
    if result and (everything or result.verdict == "vendor" or result.verdict == "free") then
      rows[#rows + 1] = result
    elseif result then
      others = others + 1
    end
  end
  if not RXP() then
    Say("RestedXP's item data isn't available, so its guides are not taken into account. Is RestedXP Guides enabled?")
  elseif ns.problem then
    Say("couldn't read RestedXP's item data (" .. ns.problem .. "), so quests are not taken into account.")
  end
  if #rows == 0 then
    if everything or others == 0 then
      Say("nothing in your bags to judge.")
    else
      Say(("nothing in your bags to vendor or delete. /smooth all lists the %d to auction, disenchant or keep."):format(others))
    end
    return
  end
  table.sort(rows, function(a, b)
    if ORDER[a.verdict] ~= ORDER[b.verdict] then
      return ORDER[a.verdict] < ORDER[b.verdict]
    end
    return a.itemID < b.itemID
  end)
  Say(everything and "everything judged in your bags:"
    or ("to vendor (buying each stack back costs at most %s more than a vendor pays) or delete:"):format(
      ns.Money(settings.limit)))
  local gain, selling = 0, 0
  for _, row in ipairs(rows) do
    local _, link = GetItemInfo(row.itemID)
    print(("  %s x%d: %s. %s"):format(link or ("item " .. row.itemID), row.count, ns.HEADLINE[row.verdict],
      ns.Explain(row, ns.Money)))
    if row.verdict == "vendor" then
      gain, selling = gain + row.gain, selling + 1
    end
  end
  if selling > 0 then
    print(("  Vendoring the %d marked \"vendor it\" pays %s."):format(selling, ns.Money(gain)))
  end
  if not everything and others > 0 then
    print(("  /smooth all also lists the %d to auction, disenchant or keep."):format(others))
  end
end

-- rejudge: the setting changes verdicts, not only how they are shown.
local function Toggle(name, label, value, rejudge)
  value = (value or ""):lower()
  if value ~= "on" and value ~= "off" then
    Say(("%s: %s. /smooth %s on|off"):format(label, settings[name] and "on" or "off", name))
    return
  end
  settings[name] = value == "on"
  Say(("%s: %s."):format(label, value))
  if rejudge then
    Forget()
  end
  RefreshIcons()
end

-- /smooth ignore [item]: never judge it (your pet's food, materials you are
-- saving), or judge a tool after all. The same command undoes it.
local function Ignore(rest)
  local itemID = tonumber(rest:match("item:(%d+)")) or tonumber(rest)
  if not itemID then
    local names = {}
    for id, ignored in pairs(settings.ignore) do
      if ignored then
        local _, link = GetItemInfo(id)
        names[#names + 1] = link or ("item " .. id)
      end
    end
    Say((#names > 0 and ("ignored: " .. table.concat(names, ", ") .. ". ") or "")
      .. "Profession tools (mining pick, skinning knife, fishing poles, rods, ...) are always left alone. "
      .. "Type /smooth ignore and shift-click an item to leave it out, or to bring it back.")
    return
  end
  local _, link, _, _, _, _, _, _, _, _, _, classID, subclassID = GetItemInfo(itemID)
  local label = link or ("item " .. itemID)
  local now = not Ignored(itemID, classID, subclassID)
  settings.ignore[itemID] = now
  if now then
    Say(label .. " will be left alone. The same command judges it again.")
  else
    Say(label .. " is judged again.")
  end
  Forget()
  RefreshIcons()
end

---------------------------------------------------------------------------
-- Locking: an item you say is yours to keep
---------------------------------------------------------------------------
local function SetLocked(itemID, locked)
  settings.locked[itemID] = locked and true or nil
  local _, link = GetItemInfo(itemID)
  local label = link or ("item " .. itemID)
  if locked then
    Say(label .. " is locked: it is marked to keep, whatever it is worth. Do the same again to unlock it.")
  else
    Say(label .. " is unlocked, and judged again.")
  end
  verdicts[itemID] = nil
  RefreshIcons()
end

-- The item whose tooltip shows under the mouse, if you carry it. This works
-- the same in every bag addon, known here or not.
local function HoveredItem()
  local tip = GameTooltip
  if type(tip) ~= "table" or not tip.GetItem or not tip.IsShown or not tip:IsShown()
    or (tip.IsForbidden and tip:IsForbidden()) then
    return nil
  end
  local owner = tip.GetOwner and tip:GetOwner()
  if type(owner) == "table" and owner.IsMouseOver and not owner:IsMouseOver() then
    return nil   -- a tooltip left showing by something the mouse is no longer on
  end
  local ok, _, link, id = pcall(tip.GetItem, tip)
  if not ok then
    return nil
  end
  local itemID = type(id) == "number" and id or (type(link) == "string" and tonumber(link:match("item:(%d+)"))) or nil
  if itemID and Carried()[itemID] then
    return itemID
  end
  return nil
end

-- Locks the item under the mouse, or unlocks it. false when there is none.
local function ToggleHovered()
  local itemID = HoveredItem()
  if not itemID then
    return false
  end
  SetLocked(itemID, not settings.locked[itemID])
  return true
end

-- For a key of your choosing (Key Bindings, under Smooth Brain; see Bindings.xml).
BINDING_NAME_SMOOTHBRAIN_LOCK = "Lock or unlock the item under the mouse"
function SmoothBrain_ToggleLock()
  if not ToggleHovered() then
    Say("point at an item in your bags, then press the key, to lock or unlock it.")
  end
end

-- /smooth lock [item]: lock it, or unlock it if it is locked. /smooth unlock
-- [item] only ever unlocks. Without an item, the locked ones are listed.
local function Lock(rest, unlockOnly)
  local itemID = tonumber(rest:match("item:(%d+)")) or tonumber(rest)
  if not itemID then
    local names = {}
    for id in pairs(settings.locked) do
      local _, link = GetItemInfo(id)
      names[#names + 1] = link or ("item " .. id)
    end
    table.sort(names)
    Say((#names > 0 and ("locked: " .. table.concat(names, ", ") .. ". ") or "nothing is locked. ")
      .. (settings.lockclick and "Middle-click an item in your bags to lock or unlock it, or type " or "Type ")
      .. "/smooth lock and shift-click it.")
    return
  end
  if unlockOnly and not settings.locked[itemID] then
    local _, link = GetItemInfo(itemID)
    Say((link or ("item " .. itemID)) .. " isn't locked.")
    return
  end
  SetLocked(itemID, not settings.locked[itemID])
end

SLASH_SMOOTHBRAIN1 = "/smooth"
SLASH_SMOOTHBRAIN2 = "/smoothbrain"
SLASH_SMOOTHBRAIN3 = "/vok"   -- from when this was called Vendor or Keep
SlashCmdList.SMOOTHBRAIN = function(message)
  local command, rest = (message or ""):match("^%s*(%S*)%s*(.-)%s*$")
  command = command:lower()
  if command == "" or command == "list" then
    List(false)
  elseif command == "all" then
    List(true)
  elseif command == "limit" then
    local copper = ns.ParseMoney(rest)
    if copper then
      settings.limit = copper
      Forget()
      RefreshIcons()
    elseif rest ~= "" then
      Say("couldn't read \"" .. rest .. "\" as money. Try /smooth limit 5s, or 1g 20s.")
      return
    end
    Say(("an item is marked \"vendor it\" when buying back everything you carry of it costs at most %s more "
      .. "than a vendor pays for it."):format(ns.Money(settings.limit)))
  elseif command == "setup" or command == "config" or command == "options" then
    ns.Setup:Open()
  elseif command == "prices" then
    local choice = rest:lower()
    if choice == "tsm" or choice == "auctionator" or choice == "both" then
      settings.prices = choice
      Forget()
      RefreshIcons()
    elseif choice ~= "" then
      Say("choose /smooth prices tsm, auctionator or both.")
      return
    end
    local using = settings.prices == "tsm" and "TradeSkillMaster's prices only"
      or settings.prices == "auctionator" and "Auctionator's prices only"
      or "TradeSkillMaster's and Auctionator's prices: for each item, whichever saw it for sale last"
    Say("using " .. using .. ((UseTSM() or UseAuctionator()) and "." or ", but that isn't running."))
  elseif command == "ignore" then
    Ignore(rest)
  elseif command == "lock" or command == "unlock" then
    Lock(rest, command == "unlock")
  elseif command == "lockclick" then
    Toggle("lockclick", "Middle-click to lock or unlock an item", rest)
  elseif command == "sets" then
    Toggle("sets", "Keeping gear that is in one of your equipment sets", rest, true)
  elseif command == "reagents" then
    Toggle("reagents", "Keeping your class's reagents", rest, true)
  elseif command == "companion" then
    Toggle("companion", "Taking Forever Companion's price when it is the newest", rest, true)
  elseif command == "drop" then
    local stacks = FlashCheapest()
    if #stacks == 0 then
      Say("nothing in your bags is marked to delete, vendor or auction, so there is nothing to suggest.")
      return
    end
    Say("least to lose by throwing away (flashing in your bags now):")
    for _, stack in ipairs(stacks) do
      local _, link = GetItemInfo(stack.itemID)
      print(("  %s x%d, worth %s"):format(link or ("item " .. stack.itemID), stack.count, ns.Money(stack.value)))
    end
  elseif command == "flash" then
    Toggle("flash", "Flashing the cheapest stacks when your bags are full", rest)
  elseif command == "icons" then
    Toggle("icons", "Markers on bag slots", rest)
  elseif command == "tooltip" then
    local choice = rest:lower()
    if choice == "short" or choice == "full" then
      settings.tooltip, settings.explain = true, choice == "full"
    elseif choice == "on" or choice == "off" then
      settings.tooltip = choice == "on"
    elseif choice ~= "" then
      Say("choose /smooth tooltip short, full or off.")
      return
    end
    Say("the tooltip " .. (not settings.tooltip and "says nothing. /smooth tooltip short or full brings it back."
      or settings.explain and "gives the verdict and the reason in full. /smooth tooltip short keeps it to one line."
      or "gives the verdict in one line; hold Shift over an item for the reason in full. /smooth tooltip full always shows it."))
  else
    Say("commands:")
    print("  /smooth - list the items in your bags to vendor or delete; /smooth all lists every item judged")
    print("  /smooth limit 5s - vendor an item when buying your stack back costs at most this much more than a vendor pays; now "
      .. ns.Money(settings.limit))
    print("  /smooth setup - the setup window: checks that prices are available, and sets everything below")
    print("  /smooth prices tsm|auctionator|both - whose auction prices to use (both: whichever saw the item last); now "
      .. settings.prices)
    print("  /smooth companion on|off - take Forever Companion's price as well, when it saw the item on the auction house "
      .. "last; now " .. (settings.companion and "on" or "off"))
    print("  /smooth lock [item] - keep this item whatever it is worth (shift-click it); again to unlock; alone, lists them. "
      .. "A middle-click on an item in your bags does the same")
    print("  /smooth lockclick on|off - whether a middle-click locks and unlocks; now " .. (settings.lockclick and "on" or "off"))
    print("  /smooth sets on|off - keep gear that is in one of your equipment sets, whatever it is worth; now "
      .. (settings.sets and "on" or "off"))
    print("  /smooth reagents on|off - keep your own class's spell reagents (and a rogue's poisons), whatever they are worth; now "
      .. (settings.reagents and "on" or "off"))
    print("  /smooth ignore [item] - never judge this item (shift-click it); again to undo; alone, lists them")
    print("  /smooth icons on|off - the markers on bag slots: coin = vendor, gavel = auction, dust = disenchant, green tick = keep, "
      .. "yellow ! = keep for a quest, red cross = leftover quest item, safe to delete, padlock = locked by you")
    print("  /smooth flash on|off - when a pickup fails because your bags are full, flash the "
      .. DROP_COUNT .. " stacks you'd lose least by deleting")
    print("  /smooth drop - flash them now, and list them")
    print("  /smooth tooltip short|full|off - the tooltip: one line (hold Shift for the reason in full), or always in full; now "
      .. (not settings.tooltip and "off" or settings.explain and "full" or "short"))
  end
end

---------------------------------------------------------------------------
-- For the setup window (Setup.lua)
---------------------------------------------------------------------------
ns.MARKS = MARKS

function ns.Settings()
  return settings
end

-- A setting was changed: judge everything afresh and redraw.
function ns.Changed()
  Forget()
  RefreshIcons()
end

-- Common trade goods (cloth, ore and bars, leather, herbs, a potion). A price
-- addon that knows none of them here has no prices to offer.
local PROBES = { 2589, 2592, 4306, 2770, 2840, 2318, 2319, 2447, 765, 118 }

-- What is installed and working: how many of the common items each price
-- addon has a price for (and, for Auctionator, how many days ago the newest
-- was seen), whether the quest addons are there, and which bags get markers.
function ns.Detect()
  local found = {
    probes = #PROBES,
    tsm = { installed = TSM_API ~= nil and TSM_API.GetCustomPriceValue ~= nil, priced = 0 },
    auctionator = { installed = type(Auctionator) == "table" and type(Auctionator.API) == "table"
      and type(Auctionator.API.v1) == "table", priced = 0 },
    companion = { installed = type(ForeverCompanion) == "table" and type(ForeverCompanion.GetAuctionEntry) == "function",
      priced = 0 },
    rxp = RXP() ~= nil,
    questie = Questie() ~= nil,
    bags = {},
  }
  for _, itemID in ipairs(PROBES) do
    if TSM("dbminbuyout", itemID) or TSM("dbmarket", itemID) then
      found.tsm.priced = found.tsm.priced + 1
    end
    local price, seen = Atr("GetAuctionPriceByItemID", itemID), Atr("GetAuctionAgeByItemID", itemID)
    if price and price > 0 and seen then
      found.auctionator.priced = found.auctionator.priced + 1
      found.auctionator.newest = math.min(found.auctionator.newest or seen, seen)
    end
    local noted, _, age = Companion(itemID)
    if noted and age <= STALE_DAYS * DAY then
      found.companion.priced = found.companion.priced + 1
      found.companion.newest = math.min(found.companion.newest or math.floor(age / DAY), math.floor(age / DAY))
    end
  end
  if baganatorHooked then
    found.bags[#found.bags + 1] = "Baganator"
  end
  if bagnonHooked then
    found.bags[#found.bags + 1] = "Bagnon"
  end
  if betterBagsHooked then
    found.bags[#found.bags + 1] = "BetterBags"
  end
  if ellesmereMarked then
    found.bags[#found.bags + 1] = "EllesmereUI"
  end
  found.bags[#found.bags + 1] = "the game's own bags"
  return found
end

-- How many kinds of item in your bags get each verdict, and what a vendor
-- pays for the ones to vendor.
function ns.Summary()
  local summary = { vendor = 0, free = 0, auction = 0, disenchant = 0, keep = 0, quest = 0, locked = 0, gain = 0 }
  for itemID in pairs(Carried()) do
    local result = ns.Check(itemID)
    if result then
      summary[result.verdict] = (summary[result.verdict] or 0) + 1
      if result.verdict == "vendor" then
        summary.gain = summary.gain + (result.gain or 0)
      end
    end
  end
  return summary
end

-- Auction prices change while you play: Forever Companion notes them as the
-- auction house shows them, Auctionator when you scan or search. Nothing else
-- a verdict hangs on changes with them, and most items' prices don't either.
-- So only the items one of the two has noted anew are judged again: each
-- verdict remembers what they said of its item (its `market`), and that is
-- compared with what they say now. `companion`, `auctionator`: which of them
-- may have learned something.
local function PricesChanged(companion, auctionator)
  companion, auctionator = companion and UseCompanion(), auctionator and UseAuctionator()
  local changed = false
  for itemID, known in pairs(verdicts) do
    local market, anew = known.market, false
    if market and market.auction then
      if companion then
        local noted, listed, _, stamp = Companion(itemID)
        anew = noted ~= market.noted or listed ~= market.notedCount or stamp ~= market.notedAt
      end
      if auctionator and not anew then
        anew = Atr("GetAuctionPriceByItemID", itemID) ~= market.scanPrice
          or Atr("GetAuctionAgeByItemID", itemID) ~= market.scanAge
      end
    end
    -- A scan also moves the prices of the materials gear is disenchanted into.
    if market and market.gear and auctionator and not anew then
      anew = Atr("GetDisenchantPriceByItemID", itemID) ~= market.scanDust
    end
    if anew then
      verdicts[itemID] = nil
      changed = true
    end
  end
  if changed then
    RefreshIcons()
  end
end

-- Auctionator says when a scan has changed its prices; a scan reports in
-- bursts, so wait for it to settle.
local auctionatorHooked, scanSettling
local function HookAuctionator()
  local api = type(Auctionator) == "table" and type(Auctionator.API) == "table" and Auctionator.API.v1
  if auctionatorHooked or type(api) ~= "table" or type(api.RegisterForDBUpdate) ~= "function" then
    return
  end
  auctionatorHooked = true
  local function Settled()
    scanSettling = nil
    PricesChanged(false, true)
  end
  pcall(api.RegisterForDBUpdate, ADDON, function()
    if not (C_Timer and C_Timer.After) then
      Settled()
    elseif not scanSettling then
      scanSettling = true
      C_Timer.After(2, Settled)
    end
  end)
end

-- Forever Companion notes prices as the auction house shows them, and doesn't
-- say when it has. So a moment after the auction house has shown something,
-- and when it closes, its notes are looked at again.
local AUCTION_EVENTS = { AUCTION_HOUSE_BROWSE_RESULTS_UPDATED = true, AUCTION_HOUSE_BROWSE_RESULTS_ADDED = true,
  COMMODITY_SEARCH_RESULTS_UPDATED = true, AUCTION_ITEM_LIST_UPDATE = true, REPLICATE_ITEM_LIST_UPDATE = true,
  AUCTION_HOUSE_CLOSED = true }
local pricesSettling
local function PricesSeen()
  if not UseCompanion() then
    return
  end
  local function Settled()
    pricesSettling = nil
    PricesChanged(true, false)
  end
  if not (C_Timer and C_Timer.After) then
    Settled()
  elseif not pricesSettling then
    pricesSettling = true
    C_Timer.After(2, Settled)
  end
end

-- Some of what a verdict says hangs on the clock: "Auctionator saw it today",
-- a quest item's "seen today or yesterday", and a price Forever Companion
-- saw "within the hour", which comes with how many are listed. Nothing
-- else tells when those have moved on, so everything is judged afresh at
-- these times: when you leave the auction house (once its last results have
-- settled), an hour after that, and at midnight.
local clockRound = 0
local function Afresh()
  Forget()
  RefreshIcons()
end

local function AfterAuctionHouse()
  if not (C_Timer and C_Timer.After) then
    return
  end
  clockRound = clockRound + 1
  local round = clockRound
  C_Timer.After(3, Afresh)
  C_Timer.After(LIVE_SECONDS + 5, function()
    if round == clockRound then
      Afresh()
    end
  end)
end

local function AtMidnight()
  if not (C_Timer and C_Timer.After and date) then
    return
  end
  local now = date("*t")
  local left = (24 - now.hour) * 3600 - now.min * 60 - now.sec
  C_Timer.After(math.max(left, 60) + 5, function()
    Afresh()
    AtMidnight()
  end)
end

-- A skill went up, or a spell was learned. Of all that, only one thing
-- matters here: whether you can disenchant. Skills go up all the time while
-- you play, so nothing is judged again unless that has changed.
local function SkillsChanged()
  local was = enchanter
  enchanter = nil
  if was ~= nil and Enchanter() ~= was then
    verdicts = {}
    RefreshIcons()
  end
end

-- The quest log changes far more often than it matters here (every kill that
-- counts for a quest). It is read again a moment after it last changed, and
-- items are only judged afresh when what the verdicts hang on is different:
-- which quests you have, which are complete, and which items they ask for. A
-- quest you have just taken tells its objectives a moment after it arrives,
-- so this is also what catches those.
local logSettling
local function QuestLogChanged()
  local function Settled()
    logSettling = nil
    local before = builtSignature
    questLog = nil
    if QuestLog().signature ~= before then
      Forget()
      RefreshIcons()
    end
  end
  if not (C_Timer and C_Timer.After) then
    Settled()
  elseif not logSettling then
    logSettling = true
    C_Timer.After(1, Settled)
  end
end

---------------------------------------------------------------------------
-- Events
---------------------------------------------------------------------------
local frame = CreateFrame("Frame")
for _, event in ipairs({ "ADDON_LOADED", "PLAYER_LOGIN", "BAG_UPDATE", "BAG_UPDATE_DELAYED", "QUEST_ACCEPTED",
  "QUEST_REMOVED", "QUEST_TURNED_IN", "SKILL_LINES_CHANGED", "SPELLS_CHANGED", "UI_ERROR_MESSAGE", "GLOBAL_MOUSE_DOWN",
  "QUEST_LOG_UPDATE", "EQUIPMENT_SETS_CHANGED", "PLAYER_ENTERING_WORLD", "BAG_CONTAINER_UPDATE" }) do
  pcall(frame.RegisterEvent, frame, event)
end
for event in pairs(AUCTION_EVENTS) do
  pcall(frame.RegisterEvent, frame, event)   -- which of them exist depends on the client
end
frame:SetScript("OnEvent", function(_, event, name, extra)
  if AUCTION_EVENTS[event] then
    if event == "AUCTION_HOUSE_CLOSED" then
      AfterAuctionHouse()
    else
      PricesSeen()
    end
  elseif event == "GLOBAL_MOUSE_DOWN" then
    -- Any mouse button, anywhere. The middle one, on an item in your bags, locks or unlocks it.
    if name == "MiddleButton" and settings.lockclick then
      ToggleHovered()
    end
  elseif event == "QUEST_LOG_UPDATE" then
    QuestLogChanged()
  elseif event == "SKILL_LINES_CHANGED" or event == "SPELLS_CHANGED" then
    SkillsChanged()
  elseif event == "PLAYER_ENTERING_WORLD" or event == "BAG_CONTAINER_UPDATE" then
    BagChanged(nil)   -- a new place, or a bag put on or taken off: read every bag again when next asked
  elseif event == "ADDON_LOADED" then
    if name == ADDON then
      SmoothBrainDB = type(SmoothBrainDB) == "table" and SmoothBrainDB or {}
      for key, value in pairs(DEFAULTS) do
        if type(SmoothBrainDB[key]) ~= type(value) then
          SmoothBrainDB[key] = type(value) == "table" and {} or value
        end
      end
      settings = SmoothBrainDB
    end
    HookBagnon()
    HookBaganator()
    HookBetterBags()
    HookEllesmere()
    HookGameBags()
    HookAuctionator()
  elseif event == "PLAYER_LOGIN" then
    loggedIn = true
    HookBagnon()
    HookBaganator()
    HookBetterBags()
    HookEllesmere()
    HookGameBags()
    HookAuctionator()
    -- Questie, RestedXP and the price addons finish starting after login: judge afresh once they have.
    if C_Timer and C_Timer.After then
      for _, wait in ipairs({ 6, 20 }) do
        C_Timer.After(wait, Afresh)
      end
    end
    AtMidnight()
    -- The first time, show the setup window, once the other addons have settled.
    if not settings.onboarded and ns.Setup then
      if C_Timer and C_Timer.After then
        C_Timer.After(4, function()
          ns.Setup:Open()
        end)
      else
        ns.Setup:Open()
      end
    end
  elseif event == "UI_ERROR_MESSAGE" then
    if settings.flash and IsBagsFull(name, extra) then
      -- Looting: only stacks worth less than what is lying there are worth
      -- throwing away for it, unless it is a quest item. Otherwise (a vendor,
      -- a quest reward, the mail) what you were taking isn't known.
      local worth, quest = Pending()
      FlashCheapest(worth ~= nil and not quest and worth or nil)
    end
  elseif event == "BAG_UPDATE" then
    BagChanged(name)   -- the bag that changed
  elseif event == "BAG_UPDATE_DELAYED" then
    if next(dropping) == nil then
      RefreshIcons()
    elseif HasFreeSlot() then
      StopFlashing()   -- room was made
    else
      ChooseStacks()   -- the bags changed but are still full: choose again, as stacks may have moved
    end
  else
    -- A quest was taken, dropped or handed in, or an equipment set changed.
    Forget()
    RefreshIcons()
  end
end)
