# Changelog

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
