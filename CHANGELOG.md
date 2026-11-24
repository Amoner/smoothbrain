# Changelog

## 2.11

- **New: the verdict and all three prices in one block near the top of the
  tooltip.** Sell Price, Auction Price and Disenchant sit together right
  where the game shows the sell price, each with its bag-slot marker, then
  the verdict, then a blank line to set the block apart. The price the
  verdict went by gets a pointer; the others are dimmed. Labels are gold,
  amounts in their coins' colours. Prices are for one item or the stack,
  whichever the game's line is for. `/smooth pricelines off` gives the game
  its own Sell Price line back and puts the verdict at the bottom again.
- Forever Companion is listed among the addons Smooth Brain can use, so it
  loads first when both are installed.

## 2.10

- **New: an arrow to the nearest vendor.** While you carry something marked
  "vendor it", a small gold arrow points at the nearest vendor in your zone,
  turning as you turn, with the distance under it. Drag it wherever you like,
  next to your bags for instance. Hover it for the vendor's name and map
  coordinates. `/smooth arrow off` hides it, `/smooth arrow reset` puts it
  back where it started.
- `/smooth` now ends with the nearest vendor when there is something to
  vendor ("Nearest vendor: Brother Danil <General Supplies>, 232 yd N"), and
  `/smooth vendor` says it at any time.
- Both need Questie, which knows where every vendor stands. Vendors of the
  other faction are left out. The distance is a straight line within your
  zone.

## 2.9.1

- Text that depends on the clock stays right: "Auctionator saw it today"
  after midnight, and a price Forever Companion saw "within the hour" once
  the hour is up. Since 2.9 such text could linger until the next quest
  event; now everything is judged afresh when you leave the auction house,
  an hour after that, and at midnight.

## 2.9

Lighter on your game, one new rule, and one fix to which price is believed.

- **New rule: food and potions that are crafting reagents are priced like
  trade goods**, not kept. Raw fish is the usual case: Raw Winter Squid, 7c
  from a vendor and silvers at auction, was marked "keep it" and is now
  "auction it". Lock the ones you cook with.
- **Fixed: an older Auctionator price could pass for the newest.** With
  TradeSkillMaster running too, 2.8 counted Auctionator's price as seen at
  its last scan when that was the same day. But Auctionator stamps a scan
  when it starts, whether or not it gets to the item. Reported with Raw
  Winter Squid: 25s from an afternoon scan was quoted in place of
  TradeSkillMaster's newer 5s 95c. Auctionator's price now counts as seen
  when its day began, so a snapshot from the same day is preferred.
- **A skill going up no longer has every item in your bags judged again.**
  It did, on every skill gain, in combat too. Now that only happens when you
  learn Disenchant.
- **At the auction house, only items with a newly noted price are judged
  again.** Since 2.8 every item was, every two seconds while results came in.
- **A change in one bag has only that bag read again**, not all of them.
- TradeSkillMaster and Auctionator are asked less for each item, and nothing
  at all for soulbound things or for items kept for a quest: no price can
  change what those are marked as.

## 2.8

Two new rules. Both change what some of your items are marked as.

- **New rule: soulbound things you use are kept.** Anything soulbound with a
  Use of its own that you don't wear, such as the Cozy Sleeping Bag or a
  mount, was marked to vendor because a vendor buys it. It now gets the green
  tick, the tooltip says "soulbound, yours to use", and it never flashes when
  your bags are full.
- **New rule: the newest auction price wins.** For each item, the price now
  comes from whichever addon saw it for sale last. Before, TradeSkillMaster's
  came first and Auctionator's only filled in, although TradeSkillMaster's is
  a snapshot: an hour old at best, and as old as your session is long.
  Auctionator notes a price when you scan or search, but only the day, so on
  the same day a newer snapshot is preferred.
- **New price source: Forever Companion.** It notes prices as the auction
  house shows them, to the second, so with it the tooltip matches what is
  listed now. `/smooth companion off` leaves its prices out.

Also:

- The tooltip is one line now, not a paragraph: the item's marker, the
  verdict, and the prices that decided it ("Auction it" on the left, "auction
  5s 60c, vendor 4s 61c" on the right). Hold Shift over an item for the reason
  in full. `/smooth tooltip full` always shows it, as before.
- A price from your own scans now says whose it is: "Auctionator saw it
  today", "Forever Companion saw it 3 days ago".

## 2.7

- Gear in one of your equipment sets is now kept, whatever it is worth: it
  gets the green tick, the tooltip names the set, and it never flashes when
  your bags are full. `/smooth sets off` prices it like anything else.
- Your own class's reagents are now kept instead of being marked to auction
  or vendor: a shaman's Ankhs, a mage's runes, a priest's candles, a paladin's
  symbols, a druid's seeds, a warlock's shards and stones, a rogue's powders
  and poisons. Another class's reagents are still priced.
  `/smooth reagents off` prices yours as well.

Both were asked for in the comments on CurseForge.

## 2.6

- Markers and the bags-full flash now work in EllesmereUI's bags, in its grid
  and its list view. The marker sits top right there.

## 2.5

- **Fixed: an item a quest still needed could be marked "safe to delete".**
  It happened when the only quest RestedXP or Questie had on record for the
  item was done, and a later quest they didn't know wanted it (reported with
  the Titan Relic and Prehistoric Prism). Your quest log is now read directly:
  anything a quest in it asks for is kept. An item that starts a quest is no
  longer called a leftover once that quest is done. And while part of the
  quest log can't be read (a folded header, a quest still loading), nothing
  you couldn't get back is called a leftover.
- Disenchanting is now only suggested when the materials beat both the vendor
  price and the auction price by more than your limit; before, any edge over
  the auction price was enough. Where TradeSkillMaster and Auctionator both
  have a disenchant value the lower is used, and the tooltip says whose
  estimate it is.
- Lock an item to keep it whatever it is worth: middle-click it in your bags.
  It gets a padlock, is never listed to vendor or delete, and never flashes
  when your bags are full. Middle-click again to unlock. `/smooth lock` with a
  shift-clicked item does the same, and Key Bindings has a key for it.
  `/smooth lockclick off` turns the middle-click off.
- Markers and the bags-full flash now work in BetterBags.

## 2.4

First public release.

- Every item in your bags gets a marker: vendor, auction, disenchant, keep,
  keep for a quest, or safe to delete. The tooltip says why.
- Prices from TradeSkillMaster, Auctionator, or both.
- Quest items from RestedXP Guides and Questie: kept while a quest still
  needs them, marked as leftovers once it doesn't.
- Markers in Bagnon, Baganator and the game's own bags.
- When your bags are full, the stacks you would lose least by deleting flash.
- A setup window (`/smooth setup`) for the price source, your limit and what
  is shown.
