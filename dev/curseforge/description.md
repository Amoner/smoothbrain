**Stop thinking about your bags.** Every item in them gets a marker that says what to do with it, and the tooltip says why.

For World of Warcraft: Forever.

## New in 2.10

- **An arrow to the nearest vendor.** While you carry something to vendor, a small gold arrow points at the nearest vendor in your zone, turning as you turn, with the distance under it. Drag it next to your bags. `/smooth vendor` names the vendor in chat. Needs Questie.

## New in 2.9

- **Raw fish is no longer "keep it".** Food and potions that are crafting reagents are priced like trade goods: Raw Winter Squid is "auction it".
- **Much lighter on your game.** A skill going up no longer has every item judged again, the auction house only has the items with a new price judged again, and a bag change only has that bag read again.

## The seven markers

| Marker | Verdict | Meaning |
|---|---|---|
| Gold coin | **Vendor it** | It costs little more to buy again than a vendor pays. |
| Gavel | **Auction it** | It is worth clearly more than a vendor pays. |
| Disenchant icon | **Disenchant it** | Green or better gear worth more as enchanting materials. |
| Green tick | **Keep it** | Things you use up (potions, food, bandages) that are dear to replace, soulbound things you use (a sleeping bag, a mount), things a vendor won't buy, gear in your equipment sets, and your class's reagents. Raw fish and other crafting reagents are priced, not kept. |
| Yellow ! | **Keep it for its quest** | A quest still needs it. |
| Red cross | **Safe to delete** | A quest item whose quests are all done, that vendors don't buy. |
| Padlock | **Keep it (you locked it)** | An item you locked yourself. It is kept whatever it is worth. |

## Lock what you want to keep

**Middle-click an item in your bags to lock it.** It gets a padlock, counts as one to keep whatever it is worth, and never flashes when your bags are full. Middle-click again to unlock. Use it for your pet's food, cloth you are saving, gear you still wear.

`/smooth lock` with a shift-clicked item does the same, and Key Bindings has a key for it.

## Kept for you

Three kinds of item are kept without you locking them:

- **Soulbound things you use:** anything soulbound with a Use of its own that you don't wear, such as the Cozy Sleeping Bag or a mount.
- **Gear in one of your equipment sets.** The tooltip names the set.
- **Your own class's reagents:** a shaman's Ankhs, a mage's runes, a priest's candles, a paladin's symbols, a druid's seeds, a warlock's shards, a rogue's powders and poisons. Another class's reagents are still priced.

`/smooth sets off` and `/smooth reagents off` turn the last two rules off.

## The rule

Vendoring an item costs you the difference between what a vendor pays and what the same items cost to buy again.

    difference = (cheapest price to buy it - vendor price) x how many you carry

If the difference is within your limit (5 silver unless you change it), the item is **vendor it**. Otherwise it is auction, keep, or keep for its quest. Hover any item and one tooltip line shows the verdict and the two prices; hold Shift for the reason in full.

## What it reads

- **Prices:** TradeSkillMaster (with the TSM desktop app), Auctionator (your own scans), Forever Companion (what the auction house showed you), or all of them: for each item, the price of whichever saw it for sale last is used, so the tooltip matches what is listed now. Without any of them, it still marks quest items, gray junk and soulbound items, but can't judge anything else.
- **Quests:** your quest log, first of all: anything a quest in it asks for is kept. RestedXP Guides, for items a later quest needs. Questie, for which quest items are leftovers, and where the vendors stand. The game's own quest flags.
- **Bags:** Bagnon, Baganator, BetterBags, EllesmereUI and the game's own bags.

All of these are optional. Smooth Brain uses whichever you have.

## When your bags are full

When a pickup fails because your bags are full, the stacks you would lose least by deleting flash red, three at most. While looting, only stacks worth less than the loot flash. Nothing is ever deleted or sold for you.

## Setup

A setup window opens the first time, and with `/smooth setup`. It checks your price addons, asks for your limit, and shows what each marker means.

## Commands

    /smooth setup           the setup window
    /smooth                 the items to vendor or delete
    /smooth all             every item judged
    /smooth limit 50c       the largest difference you'd vendor at (50c, 5s, 1g 20s)
    /smooth prices both     whose prices: tsm, auctionator or both (the newest)
    /smooth lock [item]     keep this item whatever it is worth; again to unlock
    /smooth sets on|off     keep gear that is in one of your equipment sets
    /smooth reagents on|off keep your own class's reagents
    /smooth ignore [item]   never judge this item; again to undo
    /smooth drop            flash and list the stacks you'd lose least by deleting
    /smooth flash on|off    do that by itself when your bags are full
    /smooth vendor          the nearest vendor in your zone, how far and which way
    /smooth arrow on|off    the arrow to the nearest vendor (reset puts it back)
    /smooth icons on|off    the markers on bag slots
    /smooth tooltip short|full|off  the tooltip: one line, or the reason in full

## Limits

- It judges money and quests only. It can't know the meat is your pet's food or the cloth is for First Aid. Lock those.
- It can't tell soulbound gear you wear from gear you have replaced; both are **vendor it** until you lock the pieces you wear or put them in an equipment set.
- TradeSkillMaster's prices are as fresh as your last login or `/reload`, Auctionator's as your last scan, Forever Companion's as your last look at the auction house. The newest is used, but Auctionator only notes the day it saw a price.
- It reads RestedXP's and Questie's own tables. If an update to either changes them, that part goes quiet until Smooth Brain is updated.
