-- Smooth Brain: the setup window. It opens once by itself after installing,
-- and with /smooth setup. Its first page checks whether prices are really
-- available, and sets the limit, whose prices to use and where the verdict
-- shows. Its second page says how each marker is decided, and in what order.
local ADDON, ns = ...

local Setup = {}
ns.Setup = Setup

local TICK, CROSS = "Interface\\RaidFrame\\ReadyCheck-Ready", "Interface\\RaidFrame\\ReadyCheck-NotReady"
local WIDTH, HEIGHT, MARGIN = 540, 626, 24
local FOOTER = -(HEIGHT - 36)
local PRESETS = { 50, 100, 500, 1000, 2000, 5000 }   -- limits offered as buttons, in copper
local LEGEND = {
  { "vendor", "vendor" }, { "auction", "auction" }, { "disenchant", "disenchant" }, { "keep", "keep" },
  { "quest", "keep for a quest" }, { "free", "delete" },
}

-- How each marker is decided, in the order the rules are tried: the same order
-- as ns.Decide in Logic.lua and Judge in SmoothBrain.lua. { marker, name, rule }
Setup.RULES = {
  { nil, "No marker: left alone",
    "Items you /smooth ignore, profession tools (mining pick, skinning knife, fishing poles, rods and the like), bags, "
      .. "ammunition and keys." },
  { "quest", "Keep for a quest",
    "An item a quest in your log asks for; an item the game marks as a quest item; or one Questie ties to an open "
      .. "quest of yours. Also an item a RestedXP guide needs for a quest you haven't done, when one of these "
      .. "is true: you are on that quest now; a "
      .. "vendor won't buy it; it is soulbound; it can't be counted on to buy back (nobody sells it, fewer than twice "
      .. "what the quest takes are listed, or Auctionator last saw it over a day ago); or buying your stack back costs "
      .. "more than your limit above the vendor price. If none is true, it gets the coin." },
  { "disenchant", "Disenchant",
    "Green or better weapons and armour whose materials beat both what a vendor pays and what the item costs to "
      .. "buy, by over your limit. An item you can trade is always compared; a soulbound one only if you know "
      .. "Disenchant." },
  { "free", "Delete",
    "A quest item whose quests are all done, that vendors don't buy. Done means the quest RestedXP's guide uses it for "
      .. "is handed in or, for items you can't wear, every quest Questie lists for it that your character can take. A "
      .. "quest that is complete and only waits to be handed in counts as done for an item its hand-in doesn't take. A "
      .. "soulbound leftover a vendor does buy gets the coin; one you can trade is judged by the rules below." },
  { "keep", "Keep: can't be sold",
    "A vendor won't buy it and no quest is tied to it: a book, a toy, a soulbound trinket. It is only worth what it "
      .. "does for you. If it can be traded and costs more than your limit to buy, it gets the gavel instead." },
  { "vendor", "Vendor: soulbound",
    "Anything soulbound that a vendor buys, since it can't be auctioned. Soulbound things you use get the tick: a "
      .. "potion, and anything else with a Use of its own that you don't wear (a sleeping bag, a mount)." },
  { "vendor", "Vendor: cheap to replace",
    "Buying everything you carry of it again costs at most your limit more than a vendor pays for it. The price to buy "
      .. "is the lower of a vendor's and the lowest auction (TradeSkillMaster's, Auctionator's or Forever Companion's, "
      .. "whichever saw the item for sale last; if none are listed, the region's sale average). Gray junk always gets "
      .. "the coin." },
  { "keep", "Keep",
    "Costs more than that to replace, and is something you use up: a potion, food, a bandage." },
  { "auction", "Auction",
    "Costs more than that to replace, and is anything else." },
  { nil, "No marker: nothing to go on",
    "Something you can trade that a vendor buys, when no price to buy it is known." },
}

---------------------------------------------------------------------------
-- What the checks found, in words
---------------------------------------------------------------------------
-- state: true (working), false (missing), nil (there, but with nothing to offer yet)
function Setup.PriceLine(name, source, probes, advice)
  if not source.installed then
    return false, name .. ": not installed, or not enabled."
  elseif source.priced == 0 then
    return nil, name .. ": running, but it has no prices here yet. " .. advice
  end
  local text = ("%s: prices found, for %d of %d common items."):format(name, source.priced, probes)
  if source.newest then
    text = text .. (" Last seen %s."):format(source.newest == 0 and "today" or source.newest == 1 and "yesterday"
      or (source.newest .. " days ago"))
  end
  return true, text
end

function Setup.Verdict(found)
  local settings = ns.Settings()
  local tsm = found.tsm.priced > 0 and settings.prices ~= "auctionator"
  local auctionator = found.auctionator.priced > 0 and settings.prices ~= "tsm"
  local companion = found.companion ~= nil and found.companion.priced > 0 and settings.companion
  if tsm or auctionator or companion then
    return true, "Prices are available. Items in your bags are being judged."
  elseif found.tsm.priced > 0 or found.auctionator.priced > 0 then
    return false, "Prices exist, but not from the source chosen below. Choose \"Either\"."
  end
  return false, "No prices yet. Quest items, leftovers, gray junk and soulbound items are still marked; other things "
    .. "you could sell are not."
end

function Setup.SummaryLine(summary)
  local parts = {}
  local function Add(count, text)
    if count > 0 then
      parts[#parts + 1] = count .. " " .. text
    end
  end
  Add(summary.vendor, ("to vendor (%s)"):format(ns.Money(summary.gain)))
  Add(summary.free, "to delete")
  Add(summary.auction, "to auction")
  Add(summary.disenchant, "to disenchant")
  Add(summary.keep + summary.quest + (summary.locked or 0), "to keep")
  if #parts == 0 then
    return "With this limit, nothing in your bags gets a verdict right now."
  end
  return "With this limit, in your bags now: " .. table.concat(parts, ", ") .. "."
end

---------------------------------------------------------------------------
-- Building blocks
---------------------------------------------------------------------------
local function Text(parent, font, x, y, width)
  local text = parent:CreateFontString(nil, "OVERLAY", font)
  text:SetPoint("TOPLEFT", x, y)
  text:SetWidth(width or (WIDTH - x - MARGIN))
  text:SetJustifyH("LEFT")
  return text
end

-- A line with a tick or a cross in front of it.
local function StatusLine(parent, y)
  local line = { icon = parent:CreateTexture(nil, "ARTWORK"), text = Text(parent, "GameFontHighlight", MARGIN + 22, y) }
  line.icon:SetSize(16, 16)
  line.icon:SetPoint("TOPLEFT", MARGIN, y + 2)
  function line:Set(state, words)
    self.icon:SetTexture(state and TICK or CROSS)
    self.icon:SetDesaturated(state == nil)   -- gray cross: there, but nothing to offer yet
    self.text:SetText(words)
  end
  return line
end

local function Check(parent, x, y, label, width)
  local check = CreateFrame("CheckButton", nil, parent, "UICheckButtonTemplate")
  check:SetSize(24, 24)
  check:SetPoint("TOPLEFT", x, y)
  check.label = Text(parent, "GameFontHighlight", x + 26, y - 5, width)
  check.label:SetText(label)
  return check
end

local function Button(parent, x, y, width, label)
  local button = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
  button:SetSize(width, 22)
  button:SetPoint("TOPLEFT", x, y)
  button:SetText(label)
  return button
end

-- One of the window's two pages: a frame filling it.
local function Page(window)
  local page = CreateFrame("Frame", nil, window)
  page:SetAllPoints(window)
  return page
end

---------------------------------------------------------------------------
-- The first page: checks and settings
---------------------------------------------------------------------------
function Setup:CreateMain(window)
  local page = Page(window)
  local intro = Text(page, "GameFontHighlightSmall", MARGIN, -44)
  intro:SetText("Stop thinking about your bags. Each item gets a marker: vendor, auction, disenchant, keep, keep for a "
    .. "quest, or delete.")

  -- 1. Prices
  local y = -70
  Text(page, "GameFontNormal", MARGIN, y):SetText("1. Prices")
  self.tsm = StatusLine(page, y - 20)
  self.auctionator = StatusLine(page, y - 54)
  self.prices = StatusLine(page, y - 88)
  Text(page, "GameFontHighlight", MARGIN, y - 114, 40):SetText("Use:")
  self.choices = {}
  local x = MARGIN + 44
  for _, choice in ipairs({ { "both", "Either (the newest)", 150 }, { "tsm", "TradeSkillMaster only", 160 },
    { "auctionator", "Auctionator only", 130 } }) do
    local check = Check(page, x, y - 108, choice[2], choice[3] - 30)
    check:SetScript("OnClick", function()
      ns.Settings().prices = choice[1]
      ns.Changed()
      self:Refresh()
    end)
    self.choices[choice[1]] = check
    x = x + choice[3]
  end

  -- 2. The limit
  y = -214
  Text(page, "GameFontNormal", MARGIN, y):SetText("2. Your limit")
  Text(page, "GameFontHighlight", MARGIN, y - 20):SetText(
    "Vendor an item when buying your whole stack back would cost at most this much more than a vendor pays for it:")
  local box = CreateFrame("EditBox", nil, page, "InputBoxTemplate")
  self.limit = box
  box:SetSize(70, 20)
  box:SetPoint("TOPLEFT", MARGIN + 6, y - 56)
  box:SetAutoFocus(false)
  box:SetScript("OnEnterPressed", function()
    local copper = ns.ParseMoney(box:GetText())
    if copper then
      ns.Settings().limit = copper
      ns.Changed()
    end
    box:ClearFocus()
    self:Refresh()   -- shows the limit as it now stands, typed well or not
  end)
  box:SetScript("OnEscapePressed", function()
    box:ClearFocus()
    self:Refresh()
  end)
  self.presets = {}
  x = MARGIN + 90
  for index, copper in ipairs(PRESETS) do
    local button = Button(page, x, y - 55, 56, ns.Money(copper))
    button:SetScript("OnClick", function()
      ns.Settings().limit = copper
      ns.Changed()
      self:Refresh()
    end)
    self.presets[index] = button
    x = x + 60
  end
  self.summary = Text(page, "GameFontHighlightSmall", MARGIN, y - 86)

  -- 3. Where it shows
  y = -330
  Text(page, "GameFontNormal", MARGIN, y):SetText("3. Where it shows")
  self.toggles = {}
  for index, toggle in ipairs({ { "icons", "Markers on bag slots" }, { "tooltip", "The verdict on item tooltips" },
    { "flash", "Flash the cheapest stacks when a pickup fails because your bags are full" } }) do
    local check = Check(page, MARGIN, y - 18 - (index - 1) * 24, toggle[2])
    check:SetScript("OnClick", function(button)
      ns.Settings()[toggle[1]] = button:GetChecked() and true or false
      ns.Changed()
      self:Refresh()
    end)
    self.toggles[toggle[1]] = check
  end
  self.bags = Text(page, "GameFontHighlightSmall", MARGIN + 26, y - 96)
  -- What the markers mean, in a word each; the second page has the rules.
  x = MARGIN
  for _, entry in ipairs(LEGEND) do
    local icon = page:CreateTexture(nil, "ARTWORK")
    icon:SetSize(16, 16)
    icon:SetPoint("TOPLEFT", x, y - 116)
    icon:SetTexture(ns.MARKS[entry[1]])
    local word = Text(page, "GameFontHighlightSmall", x + 19, y - 118, 90)
    word:SetText(entry[2])
    x = x + (entry[1] == "quest" and 112 or entry[1] == "disenchant" and 88 or 72)
  end

  -- 4. Quests
  y = -476
  Text(page, "GameFontNormal", MARGIN, y):SetText("4. Quests")
  self.rxp = StatusLine(page, y - 20)
  self.questie = StatusLine(page, y - 40)

  local hint = Text(page, "GameFontDisableSmall", MARGIN, -546)
  hint:SetText("/smooth setup opens this again. To keep an item whatever its marker says, middle-click it in your bags: "
    .. "it gets a padlock.")
  self.guideButton = Button(page, MARGIN, FOOTER, 210, "How each marker is decided")
  self.guideButton:SetScript("OnClick", function()
    self:ShowPage("guide")
  end)
  return page
end

---------------------------------------------------------------------------
-- The second page: how each marker is decided, and in what order
---------------------------------------------------------------------------
function Setup:CreateGuide(window)
  local page = Page(window)
  self.guideIntro = Text(page, "GameFontHighlightSmall", MARGIN, -44)
  local y = -76
  self.rules = {}
  for index, rule in ipairs(Setup.RULES) do
    local marker, name, how = rule[1], rule[2], rule[3]
    if marker then
      local icon = page:CreateTexture(nil, "ARTWORK")
      icon:SetSize(16, 16)
      icon:SetPoint("TOPLEFT", MARGIN, y + 2)
      icon:SetTexture(ns.MARKS[marker])
    end
    local title = Text(page, "GameFontNormal", MARGIN + 22, y)
    title:SetText(("%d. %s"):format(index, name))
    local body = Text(page, "GameFontHighlightSmall", MARGIN + 22, y - 15)
    body:SetText(how)
    self.rules[index] = { title = title, body = body }
    y = y - 15 - math.max(body:GetStringHeight() or 0, 11) - 9
  end
  self.backButton = Button(page, MARGIN, FOOTER, 96, "Back")
  self.backButton:SetScript("OnClick", function()
    self:ShowPage("main")
  end)
  return page
end

---------------------------------------------------------------------------
-- The window
---------------------------------------------------------------------------
function Setup:Create()
  if self.frame then
    return self.frame
  end
  local f = CreateFrame("Frame", "SmoothBrainSetup", UIParent, "BackdropTemplate")
  self.frame = f
  f:SetSize(WIDTH, HEIGHT)
  f:SetPoint("CENTER")
  f:SetFrameStrata("DIALOG")
  f:SetToplevel(true)
  f:SetBackdrop({ edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border", edgeSize = 32,
    insets = { left = 11, right = 12, top = 12, bottom = 11 } })
  -- A solid background: nothing behind the window shows through the text.
  local background = f:CreateTexture(nil, "BACKGROUND")
  background:SetPoint("TOPLEFT", 10, -10)
  background:SetPoint("BOTTOMRIGHT", -10, 10)
  background:SetColorTexture(0.05, 0.05, 0.07, 1)
  f:EnableMouse(true)
  f:SetMovable(true)
  f:RegisterForDrag("LeftButton")
  f:SetScript("OnDragStart", f.StartMoving)
  f:SetScript("OnDragStop", f.StopMovingOrSizing)
  if type(UISpecialFrames) == "table" then
    table.insert(UISpecialFrames, "SmoothBrainSetup")   -- Escape closes it
  end
  local close = CreateFrame("Button", nil, f, "UIPanelCloseButton")
  close:SetPoint("TOPRIGHT", -6, -6)
  self.title = Text(f, "GameFontNormalLarge", MARGIN, -22)

  self.main = self:CreateMain(f)
  self.guide = self:CreateGuide(f)
  local done = Button(f, WIDTH - MARGIN - 96, FOOTER, 96, "Done")
  done:SetScript("OnClick", function()
    f:Hide()
  end)

  f:SetScript("OnShow", function()
    self:ShowPage("main")
  end)
  f:SetScript("OnHide", function()
    ns.Settings().onboarded = true
  end)
  f:Hide()
  return f
end

function Setup:ShowPage(name)
  self.page = name
  self.main:SetShown(name == "main")
  self.guide:SetShown(name == "guide")
  self.title:SetText(name == "guide" and "Smooth Brain: how each marker is decided" or "Smooth Brain: setup")
  self:Refresh()
end

-- Brings every line and control in step with what is installed and chosen.
function Setup:Refresh()
  if not self.frame then
    return
  end
  local settings, found = ns.Settings(), ns.Detect()
  self.found = found
  self.tsm:Set(Setup.PriceLine("TradeSkillMaster", found.tsm, found.probes,
    "Add this auction house in the TSM desktop app, then /reload."))
  self.auctionator:Set(Setup.PriceLine("Auctionator", found.auctionator, found.probes,
    "Scan the auction house with it."))
  self.prices:Set(Setup.Verdict(found))
  for choice, check in pairs(self.choices) do
    check:SetChecked(settings.prices == choice)
  end
  self.limit:SetText(ns.Money(settings.limit))
  for index, button in ipairs(self.presets) do
    button:SetEnabled(settings.limit ~= PRESETS[index])
  end
  self.summary:SetText(Setup.SummaryLine(ns.Summary()))
  for name, check in pairs(self.toggles) do
    check:SetChecked(settings[name] and true or false)
  end
  self.bags:SetText("Markers work in: " .. table.concat(found.bags, ", ") .. ".")
  -- Kept to one line each: the two sit close together.
  self.rxp:Set(found.rxp, found.rxp and "RestedXP Guides: found. Items a later quest needs are kept."
    or "RestedXP Guides: not running. No item is treated as needed for a quest.")
  self.questie:Set(found.questie, found.questie and "Questie: found. Leftover quest items are marked."
    or "Questie: not running. Leftovers are only spotted through RestedXP.")
  self.guideIntro:SetText(("Everything you carry of one item is judged together, by these rules in this order. The first "
    .. "that fits decides. Your limit is %s."):format(ns.Money(settings.limit)))
end

function Setup:Open()
  self:Create():Show()
end
