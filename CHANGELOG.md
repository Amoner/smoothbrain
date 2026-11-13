# Changelog

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
