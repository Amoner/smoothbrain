# Smooth Brain

Stop thinking about your bags. Every item in them gets a marker: vendor,
auction, disenchant, keep, keep for a quest, or delete. WoW Forever only.

(Called Vendor or Keep before version 2.0. `/vok` still works.)

Needs prices from **TradeSkillMaster** (with the TSM desktop app), from
**Auctionator** (your own scans), or both. With **RestedXP Guides** it knows which items a later quest needs,
and with **Questie** which quest items are leftovers. Works on Bagnon,
Baganator, BetterBags, EllesmereUI's bags and the game's own bags.

## Install

From [CurseForge](https://www.curseforge.com/wow/addons/smooth-brain), or
with the CurseForge app.

By hand: put this folder in `Interface/AddOns` and name it `SmoothBrain`.
(GitHub's "Download ZIP" names it `smoothbrain-main`; rename it.)

## Setup

A setup window opens by itself the first time, and with `/smooth setup`:

1. **Prices.** It asks TradeSkillMaster and Auctionator for ten common trade
   goods and says, for each, whether it is installed and whether it has
   prices here. You choose which to use.
2. **Your limit.** Type it or press one of the buttons; the line below says
   what that does to the items in your bags right now.
3. **Where it shows.** Markers, tooltip lines, flashing when your bags are
   full, with the bag addons it found and what each marker means.
4. **Quests.** Whether RestedXP and Questie are there.

Everything in it can also be set with the commands below.

## What you see

A marker in the bottom left of the bag slot, and two lines on the tooltip.
In Baganator the marker is one of its corner widgets, named "Smooth Brain":
its settings (Customise, then the icon corners) move it to another corner or
take it off. In BetterBags the marker sits top right, because BetterBags
writes item levels bottom left. In EllesmereUI's bags it is the top right
quarter of the item's picture, the one corner EllesmereUI leaves free: on a
grid slot that is the usual size, on a row of its list view it is smaller, and
a list without the icon column shows no markers.

| Marker | Verdict | Meaning |
|---|---|---|
| gold coin | vendor it | costs little more to buy again than a vendor pays |
| gavel | auction it | worth clearly more than a vendor pays |
| Disenchant icon | disenchant it | green or better gear worth more as enchanting materials |
| green tick | keep it | the same, for things you use up (potions, food, bandages); things a vendor won't buy; gear in one of your equipment sets; your class's reagents |
| yellow ! | keep it for its quest | a quest item whose quest isn't done, or an item a RestedXP guide needs that isn't cheap to get back |
| red cross | safe to delete | a quest item whose quests are all done, that vendors don't buy |
| padlock | keep it (you locked it) | an item you locked yourself; see below |

`/smooth` lists the items to vendor or delete in chat, with what a vendor pays
for them. `/smooth all` lists every item judged.

## Locking an item

**Middle-click an item in your bags to lock it.** A locked item is not judged
at all: it shows a padlock, counts as one to keep, is never listed to vendor
or delete, and never flashes when your bags are full. Middle-click it again to
unlock it. Use it for what the rule can't know: your pet's food, cloth you are
saving for First Aid, gear you still wear.

A lock is on the kind of item, not the stack, and is shared by all your
characters. Any item you carry can be locked, tools and quest items included.

Other ways to do the same:

- `/smooth lock` and a shift-clicked item. `/smooth lock` alone lists what is
  locked; `/smooth unlock` with an item only ever unlocks.
- A key of your own: Key Bindings has "Lock or unlock the item under the
  mouse" under Smooth Brain. Point at the item and press it.

`/smooth lockclick off` turns the middle-click off, for when that button does
something else for you (push-to-talk, say). The command and the key still work.

The middle-click and the key go by the item whose tooltip is showing, so they
work in any bag addon, including ones Smooth Brain puts no markers in.

## Equipment sets and your class's reagents

Two kinds of item are kept without being priced, because you carry them to
use. Both show the green tick, and the tooltip says which it is.

- **Gear in one of your equipment sets** (the game's Equipment Manager).
  Whatever a set holds is kept; the tooltip names the set. Take a piece out of
  the set and it is priced again. `/smooth sets off` prices all of it.
- **Your own class's reagents:** a shaman's Ankhs, a mage's runes and Arcane
  Powder, a priest's candles, a paladin's symbols, a druid's seeds, a
  warlock's Soul Shards, a rogue's powders and poisons, and the like. Another
  class's reagents are priced like anything else: a warrior's Light Feathers
  are still ones to sell. `/smooth reagents off` prices yours as well.

Both go by the kind of item, not the copy: a second pair of the gloves that
are in your set is kept too. A lock counts for more than either (the padlock
shows), and an item you `/smooth ignore` gets no marker at all.

## The rule

Vendoring an item costs you the difference between what a vendor pays and
what the same items cost to buy again. That is what you lose if you turn out
to need them, and about what auctioning them would have added.

    difference = (cheapest price to buy it - vendor price) x how many you carry

**vendor it** when the difference is within your limit (5 silver unless you
change it with `/smooth limit`); otherwise auction, keep, or keep for its quest.

The price to buy is the lower of a vendor that sells it and the lowest auction
house listing. When none are listed, the region's sale average stands in.

Two examples at a 50 copper limit: 10 Spider Ichor, 16c from a vendor and 19c
on the auction house, differ by 30c, so vendor. 24 Healing Potions, 75c and
1s 33c, differ by 13s 92c, so keep.

Anything a quest in your log asks for is kept, whatever it is and whatever it
costs. The quest log is read directly for this, so it also holds for quests
that neither RestedXP nor Questie knows.

Quest items are kept as long as their quest isn't done, whatever they would
cost to buy back: the ones the game itself marks as quest items, and items
Questie ties to a quest of yours that is still open. That holds even when the
quest RestedXP's guide uses the item for is already done.

Items a RestedXP guide needs for a quest you haven't done are judged more
strictly. They are always kept when you are on the quest now, when they can't
be traded, when a vendor won't buy them, or when nobody sells them. The
auction house only counts for them when at least twice what the quest takes is
listed.

## When your bags are full

When picking something up fails because your bags are full, the stacks you
would lose least by deleting flash for eight seconds, three at most: the
whole slot pulses red in Bagnon, BetterBags, EllesmereUI and the game's own
bags, and a pulsing red "pass" sign in the top left of the slot in Baganator.
It stops as soon as there is room. Where BetterBags or EllesmereUI's list
shows several stacks of an item as one slot, that slot flashes when any of
them is one to go.

When you are looting, only stacks worth less than what is lying in the loot
window flash, so nothing flashes if the loot isn't worth the swap. If the
loot is a quest item, the cheapest stacks flash whatever it is worth. Away
from a loot window (a vendor, a quest reward, the mail) the addon can't see
what you were taking, and the cheapest stacks flash.

Only stacks marked delete, vendor or auction are offered. A leftover counts
as worth nothing, a stack to vendor as what a vendor pays for it, a stack to
auction as its auction price. Items to keep, to keep for a quest or to
disenchant never flash, and neither do items you locked. `/smooth drop` flashes and lists them at any time, and
`/smooth flash off` turns the automatic flashing off. Nothing is ever deleted
for you.

## Whose prices

`/smooth prices both` (the default) asks TradeSkillMaster first and uses
Auctionator for whatever it has nothing on. `/smooth prices tsm` and
`/smooth prices auctionator` use one only.

Auctionator's prices come from your own scans, so they are as fresh as your
last scan, and they come without a count of how many are listed. The tooltip
then says when Auctionator last saw the item. A price not seen for over three
weeks is ignored. For an item a quest needs, the "twice what the quest takes"
test is replaced by "seen today or yesterday". Region sale figures are
TradeSkillMaster's only.

## Without a price addon

The addon loads and works without TradeSkillMaster and Auctionator, with less
to say. It still marks quest items (keep, or delete once their quest is
done), gray junk and soulbound items a vendor buys (vendor), and things a
vendor won't buy (keep). Anything else you could sell gets no marker, because
there is nothing to compare the vendor price with, and nothing is ever marked
auction or disenchant. An item a RestedXP guide needs is kept, since what
buying it back would cost can't be known. The setup window and `/smooth` both
say that prices are missing.

## Soulbound items

A soulbound item can't be auctioned or traded, so a vendor is the only buyer:
it is **vendor it**, unless an enchanter would get clearly more from
disenchanting it. That includes gear you carry to wear, which the addon can't
tell from gear you have replaced; lock the pieces you wear. Soulbound
things you use up are **keep it**.

An item a vendor won't buy, with no quest tied to it (a book, a toy, a
soulbound trinket), is **keep it**: it is only worth what it does for you. If
it can be traded and costs more than your limit to buy, it is **auction it**.

## Disenchanting

For green or better weapons and armour, the disenchant value is compared as
well. It is **disenchant it** only when the materials are worth more than both
what a vendor pays and what the item costs to buy, by over your limit.
Disenchanting is the most trouble of the three and its yield is an estimate,
so a small edge doesn't count: boots worth 11s 12c to a vendor, 11s 99c at
auction and an estimated 12s 34c as materials are not marked for disenchanting
unless your limit is under 35c. The tooltip still says what the materials
would have added.

- An item you can still trade is compared whether or not you are an
  enchanter; the tooltip then says someone else would have to do it.
- A soulbound item is only compared when your character knows Disenchant.
  Otherwise it is **vendor it**.
- Items a quest needs are never marked for disenchanting.

The value comes from TradeSkillMaster (its Disenchant Value, which follows
the price source set there for destroy values) or from Auctionator. Each works
it out from its own prices for the materials, so the two can be well apart;
where both have one, the lower is used, and the tooltip says whose estimate it
is. Other addons that show a disenchant value on the tooltip (Disenchantry,
for one) reckon their own, which can differ again.

## Leftover quest items

A quest item is called a leftover when its quest is done: the quest RestedXP's
guide uses it for, or, for items vendors don't buy and soulbound ones, every
quest Questie lists for it that your character can take. One open or
repeatable quest is enough to keep it.

A quest that is complete and only waits to be handed in counts as done for an
item its hand-in doesn't take: something you only used along the way. An item
the hand-in does take (one of the quest's "collect" objectives) is kept, and
the tooltip says to hand the quest in; deleting it would un-complete the
quest. When the game's objective list can't be read, the item is kept. Things you can wear are never
called leftovers, though an open quest keeps them like anything else. The
tooltip says whose word it is. A leftover that vendors don't buy but that
sells at auction is **auction it**, not delete. Questie is only believed once
it has finished starting up after login.

RestedXP and Questie only know the quests they have on record, and an item
can go on to a quest they have nothing on. So three things stop an item being
called a leftover, whatever they say:

- **A quest in your log asks for it.** It is kept, and once that quest is
  complete the tooltip says to hand it in.
- **It is an item that starts a quest.** When that quest is done and the item
  is still in your bags, it is usually wanted for the next quest in the chain,
  so it is kept.
- **Part of your quest log can't be read**: a header is folded shut in the
  quest log, or a quest has only just arrived. Until it can, nothing you
  couldn't get back (soulbound, or not bought by vendors) is called a
  leftover. Unfold the header and the leftovers show again.

One gap remains: between handing in one quest of a chain and accepting the
next, nothing can know the next quest wants the item, unless the item is one
that started a quest. Lock an item you know you need.

## What is left alone

Profession tools (mining pick, skinning knife, fishing poles, blacksmith
hammer, spanner, enchanting rods and the like), bags, ammunition, keys, and
items you can trade that a vendor buys but that have no price to buy them
known. The reagent bag is looked at like any other. Gray junk is always **vendor it**.

`/smooth ignore` with a shift-clicked item leaves any other item alone, or brings
a tool back in. An ignored item gets no marker at all; a locked one (above)
gets the padlock.

## Commands

    /smooth setup           the setup window
    /smooth                 the items to vendor or delete
    /smooth all             every item judged, including what to auction or disenchant
    /smooth limit 50c       the largest difference you'd vendor at (50c, 5s, 1g 20s)
    /smooth prices both     whose prices: tsm, auctionator or both
    /smooth lock [item]     keep this item whatever it is worth; again to unlock; alone, lists them
    /smooth lockclick on|off  whether a middle-click on an item locks and unlocks it
    /smooth sets on|off     keep gear that is in one of your equipment sets
    /smooth reagents on|off  keep your own class's reagents
    /smooth ignore [item]   never judge this item; again to undo; alone, lists them
    /smooth drop            flash and list the stacks you'd lose least by deleting
    /smooth flash on|off    do that by itself when your bags are full
    /smooth icons on|off    the markers on bag slots
    /smooth tooltip on|off  the tooltip lines

## Limits

- It judges money and quests only. It can't know that the meat is your pet's
  food or the cloth is for First Aid; lock those (middle-click them).
- TradeSkillMaster's prices are as fresh as your last login or `/reload`,
  Auctionator's as your last scan.
- "A vendor sells it" comes from TradeSkillMaster, or from vendors you have
  visited with Auctionator running, and does not say where.
- It reads RestedXP's and Questie's own tables. If an update changes them,
  that part goes quiet; for RestedXP it says so.

## Tests

`python dev/test.py` runs the addon's real files against stand-ins for the
game and the other addons. Needs Python with `lupa`
(`python -m pip install lupa`).

`python dev/release.py build` runs the tests and then makes the zip that
goes to CurseForge, in `dev/dist/`.

## License

MIT; see [LICENSE](LICENSE).
