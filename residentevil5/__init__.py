import random, json, os
from typing import List, Dict, Any, TYPE_CHECKING, TypedDict, Set
from BaseClasses import MultiWorld, Region, Location, Item, Tutorial, ItemClassification, CollectionState
from worlds.generic.Rules import set_rule
from worlds.AutoWorld import PerGameCommonOptions, World, WebWorld
from dataclasses import dataclass

import Options
from Options import Choice, OptionGroup, Toggle, OptionSet, Range, OptionError
from enum import Enum
from .Items import RE5Type, item_table, group_table, ItemDict
from .Locations import LocationDict, EventDict, location_table, event_table
from .Regions import Chapters, region_exits
from .Options import create_option_groups, RE5Options, RE5_option_groups, slot_data_options
from .Rules import set_rules, set_chapter_rules

class RE5Web(WebWorld):
    theme = "ocean"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up Resident Evil 5 Randomizer and connecting to an Archipelago Multiworld. ",
        "English",
        "setup_en.md",
        "setup/en",
        ["Garbo"]
    )]

class RE5World(World):
    """Resident Evil 5 is a survival horror game packed with hordes of fast-moving, quick-thinking enemies that represent a whole new breed of unimaginable undead evil."""

    game = "Resident Evil 5"
    web = RE5Web()

    item_name_to_id = {item["name"]: item["ap_id"] for item in item_table}
    item_name_to_type = {item["name"]: item["type"] for item in item_table}
    location_name_to_id = {loc["name"]: loc["ap_id"] for loc in location_table}

    item_name_groups = group_table
    options_dataclass = RE5Options
    options: RE5Options

    def __init__(self, multiworld: MultiWorld, player: int):
        super(RE5World, self).__init__(multiworld, player)
        self.multiworld = multiworld
        self.player = player
        self.item_table: List[ItemDict] = item_table
        self.location_table: List[LocationDict] = location_table
        self.item_classification: Dict[RE5Type, ItemClassification] = {
            RE5Type.Chapter: ItemClassification.progression,
            RE5Type.Key: ItemClassification.progression,
            RE5Type.Explosive: ItemClassification.progression,
            RE5Type.Special: ItemClassification.progression_skip_balancing, # I don't want it to rely on special weapons like the Minigun and Longbow for progression, but they are here in case you do get them.
            RE5Type.Assault: ItemClassification.progression,
            RE5Type.Magnum: ItemClassification.progression,
            RE5Type.Handgun: ItemClassification.progression,
            RE5Type.SMG: ItemClassification.progression,
            RE5Type.Shotgun: ItemClassification.progression,
            RE5Type.Rifle: ItemClassification.progression,
            RE5Type.Treasure: ItemClassification.useful,
            RE5Type.Healing: ItemClassification.filler,
            RE5Type.Ammo: ItemClassification.filler,
            RE5Type.Filler: ItemClassification.filler
        }

    def collect(self, state: "CollectionState", item: "Item") -> bool:
        return super().collect(state, item)
    
    def remove(self, state: "CollectionState", item: "Item") -> bool:
        return super().remove(state, item)

    def set_rules(re5_world: "RE5World"):
        player = re5_world.player
        multiworld = re5_world.multiworld
        world = re5_world

        set_chapter_rules(player, multiworld, world)
        if world.options.ExcludeDriving.value == 1:
            set_driving_rules(player, multiworld)

    def generate_early(self):
        choice = self.options.StartingWeapon.value
        
        if (self.options.StartingChapter.value == 1 and 
            self.options.StartingWeapon.value == 5):  # option_None
            raise OptionError("Starting Weapon cannot be 'None' when Starting Chapter is 1-1 as a weapon is required to progress past the first region.")        

        if choice == 1:  # Early weapon global
            group = "weapons"
            target_pool = self.multiworld.early_items[self.player]
        elif choice == 2:  # Early weapon local
            group = "weapons"
            target_pool = self.multiworld.local_early_items[self.player]
        elif choice == 3:  # Early pistol global
            group = "pistol"
            target_pool = self.multiworld.early_items[self.player]
        elif choice == 4:  # Early pistol local
            group = "pistol"
            target_pool = self.multiworld.local_early_items[self.player]
        else:
            return

        weapon = self.random.choice(list(group_table[group]))
        target_pool[weapon] = 1

    def create_item(self, name: str) -> "Re5Item":
        item_id: int = self.item_name_to_id[name]
        item_type: RE5Type = self.item_name_to_type[name]
        classification = self.get_item_classification(item_type)

        return Re5Item(name, classification, item_id, self.player)
        
    def get_item_classification(self, item_type: RE5Type) -> ItemClassification:
        classification = ItemClassification.filler
        if item_type in self.item_classification.keys():
            classification = self.item_classification[item_type]

        return classification
        
    def create_event(self, event: str) -> "Re5Item":
        return Re5Item(event, ItemClassification.progression_skip_balancing, None, self.player)

    def get_filler_item_name(self) -> str:
        item = self.random.choice(item_table)

        while self.get_item_classification(item["type"]) == ItemClassification.progression:
            item = self.random.choice(item_table)

        return item["name"]


    def create_junk_items(self, count: int) -> List[Item]:
        junk_pool: List[Item] = []
        junk_list: Dict[str, int] = {}

        # Identify all filler items
        for item in self.item_table:
            name = item["name"]
            item_type = item["type"]
        
            # Check if the item is classified as filler (any of RE5Type.Filler, RE5Type.Healing, or RE5Type.Ammo)
            if item_type in [RE5Type.Filler, RE5Type.Healing, RE5Type.Ammo]:
                junk_list[name] = 100  # Assign weight of 100 for each filler item
    
        # Create exactly 'count' junk items
        for i in range(count):
            if junk_list:  # Make sure we have junk items to choose from
                chosen_item = self.random.choices(list(junk_list.keys()), 
                    weights=list(junk_list.values()), 
                    k=1
                )[0]
                junk_pool.append(self.create_item(chosen_item))
    
        return junk_pool

       
    def create_items(self):
        options = self.options
        itempool = []
    
        # Create all your main items
        for item in item_table:
            # Skip Chapter 2-3 if driving is excluded
            if item["name"] == "Chapter 2-3" and options.ExcludeDriving.value == 1:
                continue
        
            itempool.append(self.create_item(item["name"]))
    
        # Add the items to the multiworld's itempool
        self.multiworld.itempool += itempool
    
        # Calculate how many locations need to be filled
        total_locations = len(self.multiworld.get_unfilled_locations(self.player))
        current_items = len([item for item in self.multiworld.itempool if item.player == self.player])
    
        # If we need more items, create junk to fill the gap
        if total_locations > current_items:
            junk_needed = total_locations - current_items
            print(f"Adding {junk_needed} junk items to fill all locations")
        
            # Call create_junk_items to add junk items to the pool
            junk_items = self.create_junk_items(junk_needed)
        
            # Add junk items to the itempool
            self.multiworld.itempool += junk_items


    def create_regions(self):
        multiworld = self.multiworld
        player = self.player

        # Helper functions
        def create_region(name: str) -> Region:
            existing = next((r for r in multiworld.regions if r.name == name and r.player == player), None)
            if existing:
                return existing
            reg = Region(name, player, multiworld)
            multiworld.regions.append(reg)
            return reg

        def connect_region(src_name: str, dest_name: str):
            src_region = create_region(src_name)
            dest_region = create_region(dest_name)
            entrance_name = f"{src_name} -> {dest_name}"
            src_region.connect(dest_region, entrance_name)

        create_region("Menu")
        for region_name in region_exits.keys():
            create_region(region_name)

        for src_name, dest_list in region_exits.items():
            for dest_name in dest_list:
                connect_region(src_name, dest_name)

        for loc in location_table:
            chapter_region = create_region(loc["chapter"])
            chapter_region.add_locations({loc["name"]: loc["ap_id"]})

        for e in event_table:
            chapter_region = create_region(e["chapter"])
            if chapter_region:
                event = Re5Location(player, e["name"], None, chapter_region)
                event.show_in_spoiler = False
                event.place_locked_item(self.create_event(e["item"]))
                chapter_region.locations.append(event)
            else:
                raise Exception(f"Event chapter '{e['chapter']}' not found! This is a bug, please report it.")

        multiworld.completion_condition[player] = lambda state: state.has("Victory", player)

        
    def fill_slot_data(self) -> Dict[str, Any]:
        options = self.options
        
        slot_data: Dict[str, Any] = {
            "locations": {loc["ap_id"]: loc["ap_id"] for loc in location_table},
            "StartingChapter": int(options.StartingChapter.value),
            "StartingWeapon": int(options.StartingWeapon.value),
            "IncludeTreasures": bool(options.IncludeTreasures.value),
            "ExcludeDriving": bool(options.ExcludeDriving.value),
            "TrapChance": options.TrapChance.value,
            "DiscardTrapWeight": options.DiscardTrapWeight.value,
            "SiphonTrapWeight": options.SiphonTrapWeight.value
        }

        return slot_data

    def generate_output(self, output_directory: str):
        if self.multiworld.players != 1:
            return

        location_data = json.dumps({location.address: location.item.code for location in self.get_locations()})
        slot_data = self.fill_slot_data()

        file_data = b"APRE5\0\0\0"
        file_data += len(location_data).to_bytes(4, "little")
        compressed = False # todo: support compression
        file_data += compressed.to_bytes(4,"little")
        
        seed_pad = 32 - len(self.multiworld.seed_name)
        file_data += self.multiworld.seed_name[0:22].encode("utf-8") + (b"\0" * seed_pad)

        name_pad = 16 - len(self.player_name)
        file_data += self.player_name[0:15].encode("utf-8") + (b"\0" * name_pad)

        file_data += slot_data["StartingChapter"].to_bytes(4, "little")
        file_data += slot_data["StartingWeapon"].to_bytes(4, "little")
        file_data += slot_data["IncludeTreasures"].to_bytes(4, "little")
        file_data += slot_data["ExcludeDriving"].to_bytes(4, "little")

        if compressed:
            pass # todo: support compression
        else:
            file_data += location_data.encode("utf-8")

        file_name = f"{self.multiworld.get_out_file_name_base(self.player)}.apre5"
        file = open(os.path.join(output_directory, file_name), "wb+")
        file.write(file_data)
        file.close()

class Re5Item(Item):
    game: str = "Resident Evil 5"
    
class Re5Location(Location):
    game: str = "Resident Evil 5"
