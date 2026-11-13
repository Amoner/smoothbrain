-- Smooth Brain: the decision itself. Nothing here calls the game, so it can
-- be tested on its own (dev/test.py).
local _, ns = ...

-- For an item a quest needs, the auction house only counts as a way to get it
-- back when at least this many times what the quest takes are listed, so a
-- few listings selling out doesn't leave you without it.
ns.SUPPLY_FACTOR = 2

-- Prices from your own scans (Auctionator) come without a count. For an item a
-- quest needs they only count when the item was seen listed this recently:
-- today or yesterday.
ns.FRESH_DAYS = 1

-- One rule for every item: vendoring costs you the difference between what a
-- vendor pays and what the same items cost to buy again. That is what you lose
-- if you turn out to need them, and it is also about what auctioning them
-- would have added. Vendor when that difference, for everything you carry, is
-- within the limit.
--
-- facts (prices per unit, in copper):
--   count       how many you carry
--   consumable  something you use up (a potion, food, a bandage)
--   quest       a quest you haven't done needs it: a RestedXP guide says so,
--               or it is a quest item nothing says is finished with
--   questNote   for the second kind, a sentence saying which
--   hold        for the second kind: keep it whatever it costs to buy back
--               (only a guide's "collect this" is weighed against the price)
--   needed      how many that quest takes, if the guide says
--   onQuest     that quest is in your log now
--   questDone   a guide needed it, and the quest is done
--   doneNote    how it is done, when not simply handed in
--   bound       it can't be traded
--   quality     0 is gray junk
--   vendorSell  what a vendor pays
--   vendorBuy   what a vendor charges, if one sells it
--   ahPrice     lowest auction house price, if any are listed
--   ahListed    how many are listed
--   ahSeen      instead of ahListed, for a price from your own scans: how many
--               days ago the item was last seen listed
--   regionSale  what it sells for across the region, for when none are listed
--   destroy     what disenchanting it yields in materials, for gear that can be
--   enchanter   you can disenchant
--   saleRate    share of its auctions that sell (0 to 1), if known
--   noPrices    no price addon is running at all
--
-- Returns nil when there is nothing to say (something you can trade that a
-- vendor buys, with no price to buy it known), else
-- { verdict = "vendor" | "auction" | "disenchant" | "keep" | "quest" | "free", why, count,
--   quest, needed, questDone, gain, price, source ("vendor" | "ah" |
--   "region"), listed, cost, diff, saleRate }.
-- "quest", "keep" and "auction" all mean the item is worth too much more than
-- a vendor pays: "quest" when a quest needs it, "keep" for things you use up,
-- "auction" for the rest. "disenchant" is for gear whose materials are worth
-- more than either: anyone can have a tradeable item disenchanted, only an
-- enchanter a soulbound one.
function ns.Decide(facts, limit)
  local count = facts.count or 0
  local quest = facts.quest == true
  local result = { count = count, quest = quest or nil, needed = quest and facts.needed or nil,
    questDone = facts.questDone or nil, questNote = quest and facts.questNote or nil,
    doneNote = facts.questDone and facts.doneNote or nil }
  local function Is(verdict, why)
    result.verdict, result.why = verdict, why
    return result
  end

  if quest and facts.onQuest then
    return Is("quest", "onquest")
  end
  if quest and facts.hold then
    result.unsellable = (facts.vendorSell or 0) <= 0 or nil
    return Is("quest", "held")
  end
  -- What disenchanting one would yield, when someone can do it. It is an
  -- estimate, and of the three ways to be rid of an item disenchanting is the
  -- most trouble: so it has to beat both of the others, what a vendor pays and
  -- what the item would fetch, by more than the limit.
  local dust = not quest and (facts.destroy or 0) > 0 and (not facts.bound or facts.enchanter) and facts.destroy or nil
  result.dustBy = dust and facts.destroyBy or nil   -- whose estimate it is
  local function Disenchant()
    result.dust, result.byOther = dust * count, not facts.enchanter or nil
    return Is("disenchant", "dust")
  end
  local sell = facts.vendorSell or 0
  result.gain = sell * count
  if sell <= 0 then
    if quest then
      return Is("quest", "novalue")
    end
    -- A vendor won't buy it. If it can be traded and costs enough to buy, it
    -- is worth auctioning, leftover or not. Otherwise a leftover can go, and
    -- anything else is only worth what it does for you.
    local each, where = nil, nil
    if not facts.bound then
      if (facts.ahPrice or 0) > 0 then
        each, where = facts.ahPrice, "ah"
      elseif (facts.regionSale or 0) > 0 then
        each, where = facts.regionSale, "region"
      end
    end
    local function Fetches()
      result.price, result.source, result.cost = each, where, each * count
      if where == "ah" then
        result.seen = facts.ahSeen
        result.listed = not facts.ahSeen and (facts.ahListed or 0) or nil
      end
    end
    if dust and (dust - (each or 0)) * count > limit then
      if each then
        Fetches()
      end
      return Disenchant()
    end
    if each and each * count > limit then
      Fetches()
      return Is("auction", "unsellable")
    end
    if facts.questDone then
      return Is("free", "done")
    end
    result.tradeable = not facts.bound or nil
    return Is("keep", "nosale")
  end
  if facts.bound then
    if quest then
      return Is("quest", "bound")
    end
    if dust and (dust - sell) * count > limit then
      return Disenchant()
    end
    if facts.questDone then
      return Is("vendor", "leftover")
    end
    if facts.consumable then
      return Is("keep", "useup")   -- something soulbound you would use up, not sell
    end
    -- It can't be auctioned or traded, so a vendor is the only buyer.
    result.dust = dust and dust * count or nil
    return Is("vendor", "boundsell")
  end

  -- The cheapest way to buy it again.
  local price, source
  if (facts.vendorBuy or 0) > 0 then
    price, source = facts.vendorBuy, "vendor"
  end
  local ah, seen = facts.ahPrice or 0, facts.ahSeen
  local listed = not seen and (facts.ahListed or 0) or nil
  if ah > 0 then
    local need = math.min(facts.needed or count, count)
    local enough
    if seen then
      enough = seen <= ns.FRESH_DAYS
    else
      enough = listed >= need * ns.SUPPLY_FACTOR
    end
    if not quest or enough then
      if not price or ah < price then
        price, source = ah, "ah"
      end
    elseif not price then
      result.listed, result.seen, result.short = listed, seen, need
      return Is("quest", seen and "stale" or "fewlisted")
    end
  elseif not price and not quest and (facts.regionSale or 0) > 0 then
    price, source = facts.regionSale, "region"
  end
  if dust and (dust - math.max(sell, price or 0)) * count > limit then
    -- Worth clearly more as enchanting materials than sold either way.
    if price then
      result.price, result.source, result.cost = price, source, price * count
      result.listed, result.seen = source == "ah" and listed or nil, source == "ah" and seen or nil
    end
    return Disenchant()
  end
  result.dust = dust and dust * count or nil   -- not worth doing, but the tooltip says what it would yield
  if not price then
    if quest then
      return Is("quest", facts.noPrices and "noprices" or "nosource")
    end
    if dust then
      return Is("vendor", "nodust")   -- no price to buy it known, so a vendor's is what it has to beat
    end
    return facts.quality == 0 and Is("vendor", "junk") or nil
  end

  result.price, result.source = price, source
  result.listed, result.seen = source == "ah" and listed or nil, source == "ah" and seen or nil
  result.cost = price * count
  result.diff = result.cost - result.gain
  result.saleRate = facts.saleRate
  if result.diff <= limit then
    return Is("vendor", "cheap")
  end
  return Is(quest and "quest" or facts.consumable and "keep" or "auction", "costly")
end

ns.HEADLINE = {
  vendor = "|cff40ff40vendor it|r",
  auction = "|cff40a0ffauction it|r",
  disenchant = "|cffc080ffdisenchant it|r",
  keep = "|cffffffffkeep it|r",
  quest = "|cffffd100keep it for its quest|r",
  free = "|cffff6060safe to delete|r",
  -- Not one of Decide's: an item you locked yourself is never judged (ns.Check).
  locked = "|cffffffffkeep it|r (you locked it)",
}

local function Days(days)
  return days == 0 and "today" or days == 1 and "yesterday" or (days .. " days ago")
end

local function Where(result)
  if result.source == "vendor" then
    return "from a vendor"
  elseif result.source == "region" then
    return "going by sales in the region (none listed here now)"
  elseif result.seen then
    return ("on the auction house (Auctionator saw it %s)"):format(Days(result.seen))
  end
  return ("on the auction house (%d listed)"):format(result.listed or 0)
end

local function QuestNote(result)
  if result.questDone then
    local what = result.doneNote or "its quest is done"
    return what:sub(1, 1):upper() .. what:sub(2) .. (result.by and (" (says " .. result.by .. ")") or "") .. ". "
  elseif not result.quest then
    return ""
  elseif result.questNote then
    return result.questNote .. " "
  end
  return result.needed and ("A quest needs %d. "):format(result.needed) or "A quest needs it. "
end

-- " (TradeSkillMaster's estimate)": disenchant values differ from addon to addon.
local function Estimate(result)
  return result.dustBy and (" (" .. result.dustBy .. "'s estimate)") or ""
end

-- For an item that is not to be disenchanted although its materials would be
-- worth a little more than selling it: a sentence saying so.
local function DustNote(result, Money)
  local best = math.max(result.gain or 0, result.cost or 0)
  if not result.dust or result.dust <= best then
    return ""
  end
  return (" Disenchanting would yield about %s%s, only %s more."):format(Money(result.dust), Estimate(result),
    Money(result.dust - best))
end

-- One or two sentences saying why. Money turns copper into text.
function ns.Explain(result, Money)
  local why, note = result.why, QuestNote(result)
  local says = result.by and (" (says " .. result.by .. ")") or ""
  local what = result.doneNote or "its quest is done"
  if why == "locked" then
    return "Locked items are not judged. Middle-click it in your bags, or /smooth lock it, to unlock."
  elseif why == "done" then
    return "A leftover: " .. what .. says .. ". Vendors don't buy it."
  elseif why == "leftover" then
    return "A leftover: " .. what .. says .. ". It can't be traded, so a vendor is all that's left."
  elseif why == "junk" then
    return "Junk: only a vendor wants it."
  elseif why == "onquest" then
    return "You are on its quest right now."
  elseif why == "novalue" then
    return note .. "Vendors don't buy it."
  elseif why == "bound" then
    return note .. "It can't be traded, so it can't be bought back."
  elseif why == "noprices" then
    return note .. "No price addon is running, so there is no telling what buying it back would cost."
  elseif why == "nosource" then
    return note .. "Nobody is selling it: none on the auction house, and no vendor known."
  elseif why == "stale" then
    return note .. ("Auctionator last saw it on the auction house %s, too long ago to count on buying it back."):format(
      Days(result.seen))
  elseif why == "fewlisted" then
    return note .. ("Only %d on the auction house, too few to count on buying %d back."):format(result.listed, result.short)
  elseif why == "nosale" then
    if result.tradeable then
      return "Vendors don't buy it, and it isn't worth auctioning."
    end
    return "It can't be sold or traded, so it is only worth what it does for you."
  elseif why == "held" then
    return (result.questNote or "A quest needs it.") .. (result.unsellable and " Vendors don't buy it." or "")
  elseif why == "unsellable" then
    return note .. ("Vendors don't buy it, but buying your %d costs %s %s."):format(
      result.count, Money(result.cost), Where(result))
  elseif why == "useup" then
    return "It is soulbound and something you use up."
  elseif why == "boundsell" then
    local text = ("It is soulbound, so it can't be auctioned: a vendor pays %s for your %d."):format(
      Money(result.gain), result.count)
    if result.dust then
      text = text .. (" Disenchanting would yield about %s%s, %s."):format(Money(result.dust), Estimate(result),
        result.dust > result.gain and ("only " .. Money(result.dust - result.gain) .. " more") or "less")
    end
    return text
  elseif why == "dust" then
    local text = ("Disenchanting your %d should yield about %s in materials%s, against %s from a vendor"):format(
      result.count, Money(result.dust), Estimate(result), Money(result.gain))
    if result.cost then
      text = text .. (" and %s %s"):format(Money(result.cost), Where(result))
    end
    text = text .. "."
    if result.byOther then
      text = text .. " You are not an enchanter, so someone else would have to do it."
    end
    return note .. text
  elseif why == "nodust" then
    if result.dust <= result.gain then
      return note .. ("A vendor pays %s for your %d, as much as the %s disenchanting would yield."):format(
        Money(result.gain), result.count, Money(result.dust))
    end
    return note .. ("A vendor pays %s for your %d. Disenchanting would yield about %s%s, only %s more."):format(
      Money(result.gain), result.count, Money(result.dust), Estimate(result), Money(result.dust - result.gain))
  elseif why == "cheap" then
    if result.diff <= 0 then
      return note .. ("A vendor pays %s for your %d, and buying them back costs no more: %s each %s."):format(
        Money(result.gain), result.count, Money(result.price), Where(result)) .. DustNote(result, Money)
    end
    return note .. ("A vendor pays %s for your %d. Buying them back costs %s %s, only %s more."):format(
      Money(result.gain), result.count, Money(result.cost), Where(result), Money(result.diff)) .. DustNote(result, Money)
  end
  local text = note .. ("Buying your %d back costs %s %s, %s more than the %s a vendor pays."):format(
    result.count, Money(result.cost), Where(result), Money(result.diff), Money(result.gain))
  if result.verdict == "auction" and result.saleRate and result.saleRate < 0.2 then
    text = text .. (" Only about %d%% of its auctions sell."):format(math.floor(result.saleRate * 100 + 0.5))
  end
  return text .. DustNote(result, Money)
end

-- 12345 -> "1g 23s 45c"
function ns.Money(copper)
  copper = math.floor((copper or 0) + 0.5)
  local gold, silver, rest = math.floor(copper / 10000), math.floor(copper / 100) % 100, copper % 100
  local parts = {}
  if gold > 0 then
    parts[#parts + 1] = gold .. "g"
  end
  if silver > 0 then
    parts[#parts + 1] = silver .. "s"
  end
  if rest > 0 or #parts == 0 then
    parts[#parts + 1] = rest .. "c"
  end
  return table.concat(parts, " ")
end

-- "5s", "1g 20s", "250" (copper) -> copper, or nil.
function ns.ParseMoney(text)
  text = (text or ""):lower():gsub("%s+", "")
  if text:match("^%d+$") then
    return tonumber(text)
  end
  local total, rest = 0, text
  for amount, unit in text:gmatch("(%d+)([gsc])") do
    total = total + tonumber(amount) * (unit == "g" and 10000 or unit == "s" and 100 or 1)
    rest = rest:gsub("^" .. amount .. unit, "", 1)
  end
  if text == "" or rest ~= "" then
    return nil
  end
  return total
end
