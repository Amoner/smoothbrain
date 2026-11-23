-- The nearest vendor to sell to. Questie knows every vendor and where it
-- stands; the game says where you are. The two give the vendor nearest you in
-- your zone, how far it is in a straight line, and which way. Shown under the
-- /smooth list when there is something to vendor, and by /smooth vendor.
-- Without Questie, or where the game won't say where you are (an instance),
-- there is nothing to show.
local ADDON, ns = ...

local CHUNK = 800   -- Questie NPCs looked at per frame while the list of vendors is made
local NEAR = 10     -- yards: closer than this, the vendor is "right here"
local byZone        -- [Questie's zone] = { { name, title, x, y }, ... }: the vendors there that serve you
local building

-- Whether a flag (a single bit) is set in a number of flags, without the bit library.
local function HasFlag(flags, flag)
  return type(flags) == "number" and type(flag) == "number" and flag > 0 and flags % (2 * flag) >= flag
end

local function Ask(db, id, key)
  local ok, value = pcall(db.QueryNPCSingle, id, key)
  if ok then
    return value
  end
end

-- One NPC: if it is a vendor that serves you, each of its spawns goes in `found`.
local function Look(db, id, flag, found)
  if not HasFlag(Ask(db, id, "npcFlags"), flag) then
    return
  end
  local name = Ask(db, id, "name")
  if type(name) ~= "string" or name == "" or name:sub(1, 5) == "[DND]" then
    return
  end
  if type(db.IsFriendlyToPlayer) == "function" then
    local ok, friendly = pcall(db.IsFriendlyToPlayer, Ask(db, id, "friendlyToFaction"))
    if ok and friendly == false then
      return   -- the other faction's
    end
  end
  local spawns = Ask(db, id, "spawns")
  if type(spawns) ~= "table" then
    return
  end
  local title = Ask(db, id, "subName")
  title = type(title) == "string" and title ~= "" and title or nil
  for zone, points in pairs(spawns) do
    if type(points) == "table" then
      for _, point in ipairs(points) do
        local x, y = type(point) == "table" and point[1], type(point) == "table" and point[2]
        if type(x) == "number" and type(y) == "number" and x >= 0 and y >= 0 then
          found[zone] = found[zone] or {}
          table.insert(found[zone], { name = name, title = title, x = x, y = y })
        end
      end
    end
  end
end

-- Makes the list of vendors, a few hundred NPCs a frame, once per session.
-- false when Questie isn't ready or its data isn't what this expects (then
-- it is tried again when next asked).
function ns.BuildVendors()
  if byZone or building then
    return true
  end
  local db = ns.Questie and ns.Questie()
  local flag = db and type(db.npcFlags) == "table" and db.npcFlags.VENDOR
  if not (db and type(db.NPCPointers) == "table" and type(db.QueryNPCSingle) == "function" and flag) then
    return false
  end
  building = true
  local ids = {}
  for id in pairs(db.NPCPointers) do
    ids[#ids + 1] = id
  end
  local found, done = {}, 0
  local function Step()
    local last = (C_Timer and C_Timer.After) and math.min(done + CHUNK, #ids) or #ids
    for n = done + 1, last do
      Look(db, ids[n], flag, found)
    end
    done = last
    if done < #ids then
      C_Timer.After(0, Step)
    else
      byZone, building = found, false
    end
  end
  Step()
  return true
end

-- The width and height of a map, in yards.
local function MapSize(map)
  if C_Map.GetMapWorldSize then
    local ok, width, height = pcall(C_Map.GetMapWorldSize, map)
    if ok and type(width) == "number" and width > 0 and type(height) == "number" and height > 0 then
      return width, height
    end
  end
  if C_Map.GetWorldPosFromMapPos and CreateVector2D then
    local okA, _, a = pcall(C_Map.GetWorldPosFromMapPos, map, CreateVector2D(0, 0))
    local okB, _, b = pcall(C_Map.GetWorldPosFromMapPos, map, CreateVector2D(1, 1))
    if okA and okB and type(a) == "table" and type(b) == "table" then
      -- The world's x runs north to south, its y east to west.
      local width, height = math.abs(a.y - b.y), math.abs(a.x - b.x)
      if width > 0 and height > 0 then
        return width, height
      end
    end
  end
end

-- Where you are: Questie's zone, your position on that zone's map (0 to 100,
-- like Questie's spawns) and the map's size in yards; or nil.
local function Here()
  local _, player = ns.Questie()
  local okZones, zones = pcall(QuestieLoader.ImportModule, QuestieLoader, "ZoneDB")
  if not (player and type(player.GetCurrentZoneId) == "function" and okZones and type(zones) == "table"
    and type(zones.GetUiMapIdByAreaId) == "function" and C_Map and C_Map.GetPlayerMapPosition) then
    return nil
  end
  local okZone, zone = pcall(player.GetCurrentZoneId, player)
  if not okZone or type(zone) ~= "number" then
    return nil
  end
  local okMap, map = pcall(zones.GetUiMapIdByAreaId, zones, zone)
  if not okMap or type(map) ~= "number" then
    return nil
  end
  local okPos, position = pcall(C_Map.GetPlayerMapPosition, map, "player")
  if not okPos or type(position) ~= "table" or type(position.GetXY) ~= "function" then
    return nil
  end
  local okXY, x, y = pcall(position.GetXY, position)
  local width, height = MapSize(map)
  if not okXY or type(x) ~= "number" or type(y) ~= "number" or not width then
    return nil
  end
  return zone, x * 100, y * 100, width, height
end

local COMPASS = { "E", "NE", "N", "NW", "W", "SW", "S", "SE" }

-- The vendor nearest you in your zone: { name, title, yards, direction, x, y },
-- or nil and why not: "questie" (no Questie), "building" (its vendors are still
-- being read), "nowhere" (the game won't say where you are), "none" (no
-- vendor here that serves you).
function ns.NearestVendor()
  if not (ns.Questie and ns.Questie()) then
    return nil, "questie"
  end
  if not byZone then
    if not ns.BuildVendors() then
      return nil, "questie"
    end
    if not byZone then
      return nil, "building"
    end
  end
  -- The game may hand addons values they can't do sums with; then there is no answer.
  local ok, zone, px, py, width, height = pcall(Here)
  if not ok or not zone then
    return nil, "nowhere"
  end
  local best, bestYards, bestEast, bestSouth
  local okSums = pcall(function()
    for _, vendor in ipairs(byZone[zone] or {}) do
      local east, south = (vendor.x - px) / 100 * width, (vendor.y - py) / 100 * height
      local yards = math.sqrt(east * east + south * south)
      if not bestYards or yards < bestYards then
        best, bestYards, bestEast, bestSouth = vendor, yards, east, south
      end
    end
  end)
  if not okSums then
    return nil, "nowhere"
  end
  if not best then
    return nil, "none"
  end
  local turn = math.atan2(-bestSouth, bestEast) / (math.pi / 4)   -- in eighths of a circle, east first
  return {
    name = best.name, title = best.title, x = best.x, y = best.y,
    yards = math.floor(bestYards + 0.5),
    direction = COMPASS[math.floor(turn + 0.5) % 8 + 1],
    -- Which way it is, the way the game gives your facing: 0 is north, a
    -- quarter turn (pi / 2) is west.
    bearing = math.atan2(-bestEast, -bestSouth),
  }
end

-- One line for chat, or nil when Questie isn't there to ask.
function ns.VendorLine()
  local vendor, why = ns.NearestVendor()
  if vendor then
    local who = vendor.name .. (vendor.title and (" <" .. vendor.title .. ">") or "")
    local where = vendor.yards < NEAR and "right here"
      or ("%d yd %s"):format(vendor.yards, vendor.direction)
    return ("Nearest vendor: %s, %s (%.1f, %.1f)."):format(who, where, vendor.x, vendor.y)
  elseif why == "building" then
    return "Nearest vendor: still reading Questie's vendors; ask again in a moment."
  elseif why == "nowhere" then
    return "Nearest vendor: the game won't say where you are here."
  elseif why == "none" then
    return "Nearest vendor: Questie knows of none in this zone that serves you."
  end
end

---------------------------------------------------------------------------
-- The arrow: points at the nearest vendor while you carry something to
-- vendor. Drag it where you like (beside your bags); /smooth arrow off hides it.
---------------------------------------------------------------------------
local LOOK_SECONDS = 0.5   -- how often the nearest vendor is looked for again
local BAG_LOOKS = 4        -- ...and every this many looks, whether you carry anything to vendor
local arrow                -- the frame, made the first time it is wanted
local pointing             -- the vendor it points at
local sinceLook, looks, selling = LOOK_SECONDS, 0, false

-- Where it stands: where you dragged it, or at first above the bags' usual corner.
function ns.PlaceArrow()
  if not arrow then
    return
  end
  local at = ns.Settings().arrowAt
  arrow:ClearAllPoints()
  if type(at) == "table" and type(at[1]) == "string" and type(at[3]) == "number" and type(at[4]) == "number" then
    arrow:SetPoint(at[1], UIParent, type(at[2]) == "string" and at[2] or at[1], at[3], at[4])
  else
    arrow:SetPoint("BOTTOMRIGHT", UIParent, "BOTTOMRIGHT", -330, 230)
  end
end

-- Points it: relative to which way you face, or with north up where the game won't say.
local function Turn()
  if not (arrow and pointing) then
    return
  end
  local ok = false
  if GetPlayerFacing then
    local okFacing, facing = pcall(GetPlayerFacing)
    if okFacing and type(facing) == "number" then
      ok = pcall(arrow.icon.SetRotation, arrow.icon, pointing.bearing - facing)
    end
  end
  if not ok then
    arrow.icon:SetRotation(pointing.bearing)
  end
  arrow.northUp = not ok
end

local function ShowTip(self)
  if not pointing then
    return
  end
  GameTooltip:SetOwner(self, "ANCHOR_LEFT")
  GameTooltip:AddLine("Nearest vendor")
  GameTooltip:AddLine(pointing.name .. (pointing.title and (" <" .. pointing.title .. ">") or ""), 1, 1, 1)
  GameTooltip:AddLine(("%d yd %s, at %.1f, %.1f"):format(pointing.yards, pointing.direction, pointing.x, pointing.y), 1, 1, 1)
  if self.northUp then
    GameTooltip:AddLine("The game won't say which way you face here, so the arrow has north up, like the map.", 0.7, 0.7, 0.7, true)
  end
  GameTooltip:AddLine("Drag to move it. /smooth arrow off hides it.", 0.7, 0.7, 0.7)
  GameTooltip:Show()
end

local function MakeArrow()
  arrow = CreateFrame("Frame", "SmoothBrainVendorArrow", UIParent)
  arrow:SetSize(44, 58)
  arrow:SetFrameStrata("MEDIUM")
  arrow:SetClampedToScreen(true)
  arrow:SetMovable(true)
  arrow:EnableMouse(true)
  arrow:RegisterForDrag("LeftButton")
  arrow:SetScript("OnDragStart", function(self)
    self:StartMoving()
  end)
  arrow:SetScript("OnDragStop", function(self)
    self:StopMovingOrSizing()
    local point, _, relative, x, y = self:GetPoint()
    ns.Settings().arrowAt = { point, relative, x, y }
  end)
  arrow:SetScript("OnEnter", ShowTip)
  arrow:SetScript("OnLeave", function()
    GameTooltip:Hide()
  end)
  arrow:SetScript("OnUpdate", Turn)
  arrow.icon = arrow:CreateTexture(nil, "ARTWORK")
  arrow.icon:SetSize(40, 40)
  arrow.icon:SetPoint("TOP", arrow, "TOP", 0, 0)
  arrow.icon:SetTexture("Interface\\AddOns\\" .. ADDON .. "\\arrow")
  arrow.distance = arrow:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
  arrow.distance:SetPoint("TOP", arrow.icon, "BOTTOM", 0, -1)
  ns.PlaceArrow()
end

-- Looks again for the nearest vendor, and shows or hides the arrow.
function ns.LookForVendor()
  local settings = ns.Settings()
  looks = looks + 1
  if settings.arrow and looks % BAG_LOOKS == 1 then
    local summary = ns.Summary()
    selling = (summary.vendor or 0) > 0
  end
  pointing = nil
  if settings.arrow and selling then
    pointing = ns.NearestVendor()
  end
  if not pointing then
    if arrow then
      arrow:Hide()
    end
    return
  end
  if not arrow then
    MakeArrow()
  end
  arrow.distance:SetText(pointing.yards < NEAR and "here" or (pointing.yards .. " yd"))
  Turn()
  arrow:Show()
  if type(GameTooltip.IsOwned) == "function" and GameTooltip:IsOwned(arrow) then
    ShowTip(arrow)
  end
end

local watcher = CreateFrame("Frame")
watcher:SetScript("OnUpdate", function(_, elapsed)
  if not ns.loggedIn then
    return   -- your bags and the other addons aren't there yet
  end
  sinceLook = sinceLook + (elapsed or 0)
  if sinceLook >= LOOK_SECONDS then
    sinceLook = 0
    ns.LookForVendor()
  end
end)
