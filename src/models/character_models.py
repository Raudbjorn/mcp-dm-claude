from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import uuid


@dataclass
class Ability:
    """Represents an ability score or stat"""
    name: str
    value: int
    modifier: Optional[int] = None
    description: Optional[str] = None


@dataclass
class Skill:
    """Represents a character skill"""
    name: str
    ability: str  # Associated ability (e.g., "Dexterity", "Intelligence")
    proficient: bool = False
    expertise: bool = False
    modifier: Optional[int] = None
    description: Optional[str] = None


@dataclass
class Feature:
    """Represents a character feature, trait, or ability"""
    name: str
    source: str  # class, race, background, etc.
    description: str
    level_acquired: Optional[int] = None
    uses_per_day: Optional[int] = None
    recharge: Optional[str] = None  # "short rest", "long rest", etc.


@dataclass
class Spell:
    """Represents a spell a character can cast"""
    name: str
    level: int
    school: str
    casting_time: str
    range: str
    components: str
    duration: str
    description: str
    damage: Optional[str] = None
    save: Optional[str] = None
    prepared: bool = False


@dataclass
class Equipment:
    """Represents an item or piece of equipment"""
    name: str
    type: str  # weapon, armor, tool, etc.
    quantity: int = 1
    weight: Optional[float] = None
    value: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[List[str]] = None
    equipped: bool = False


@dataclass
class CharacterClass:
    """Represents a character class"""
    name: str
    level: int
    hit_die: str
    primary_abilities: List[str]
    saving_throw_proficiencies: List[str]
    features: List[Feature] = field(default_factory=list)
    spells_known: Optional[List[Spell]] = None
    spell_slots: Optional[Dict[int, int]] = None


@dataclass
class Race:
    """Represents a character race"""
    name: str
    subrace: Optional[str] = None
    ability_score_increases: Dict[str, int] = field(default_factory=dict)
    size: str = "Medium"
    speed: int = 30
    languages: List[str] = field(default_factory=list)
    proficiencies: List[str] = field(default_factory=list)
    traits: List[Feature] = field(default_factory=list)


@dataclass
class Background:
    """Represents a character background"""
    name: str
    skill_proficiencies: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    equipment: List[Equipment] = field(default_factory=list)
    features: List[Feature] = field(default_factory=list)
    ideals: List[str] = field(default_factory=list)
    bonds: List[str] = field(default_factory=list)
    flaws: List[str] = field(default_factory=list)


@dataclass
class Character:
    """Represents a complete character"""
    id: str
    name: str
    system: str  # D&D 5e, Pathfinder, etc.
    
    # Core attributes
    race: Race
    character_class: CharacterClass
    background: Background
    level: int
    
    # Ability scores
    abilities: Dict[str, Ability]
    
    # Skills and proficiencies
    skills: Dict[str, Skill]
    proficiencies: List[str] = field(default_factory=list)
    
    # Combat stats
    armor_class: int = 10
    hit_points: int = 1
    max_hit_points: int = 1
    hit_dice: str = "1d8"
    
    # Equipment
    equipment: List[Equipment] = field(default_factory=list)
    
    # Spells (if applicable)
    spells: List[Spell] = field(default_factory=list)
    spell_slots: Dict[int, int] = field(default_factory=dict)
    
    # Features and traits
    features: List[Feature] = field(default_factory=list)
    
    # Personality
    personality_traits: List[str] = field(default_factory=list)
    ideals: List[str] = field(default_factory=list)
    bonds: List[str] = field(default_factory=list)
    flaws: List[str] = field(default_factory=list)
    
    # Meta information
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    campaign_id: Optional[str] = None
    player_name: Optional[str] = None
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary for storage"""
        return {
            "id": self.id,
            "name": self.name,
            "system": self.system,
            "race": {
                "name": self.race.name,
                "subrace": self.race.subrace,
                "ability_score_increases": self.race.ability_score_increases,
                "size": self.race.size,
                "speed": self.race.speed,
                "languages": self.race.languages,
                "proficiencies": self.race.proficiencies,
                "traits": [
                    {
                        "name": trait.name,
                        "source": trait.source,
                        "description": trait.description,
                        "level_acquired": trait.level_acquired,
                        "uses_per_day": trait.uses_per_day,
                        "recharge": trait.recharge
                    } for trait in self.race.traits
                ]
            },
            "character_class": {
                "name": self.character_class.name,
                "level": self.character_class.level,
                "hit_die": self.character_class.hit_die,
                "primary_abilities": self.character_class.primary_abilities,
                "saving_throw_proficiencies": self.character_class.saving_throw_proficiencies,
                "features": [
                    {
                        "name": feature.name,
                        "source": feature.source,
                        "description": feature.description,
                        "level_acquired": feature.level_acquired,
                        "uses_per_day": feature.uses_per_day,
                        "recharge": feature.recharge
                    } for feature in self.character_class.features
                ],
                "spells_known": [
                    {
                        "name": spell.name,
                        "level": spell.level,
                        "school": spell.school,
                        "casting_time": spell.casting_time,
                        "range": spell.range,
                        "components": spell.components,
                        "duration": spell.duration,
                        "description": spell.description,
                        "damage": spell.damage,
                        "save": spell.save,
                        "prepared": spell.prepared
                    } for spell in (self.character_class.spells_known or [])
                ],
                "spell_slots": self.character_class.spell_slots
            },
            "background": {
                "name": self.background.name,
                "skill_proficiencies": self.background.skill_proficiencies,
                "languages": self.background.languages,
                "equipment": [
                    {
                        "name": eq.name,
                        "type": eq.type,
                        "quantity": eq.quantity,
                        "weight": eq.weight,
                        "value": eq.value,
                        "description": eq.description,
                        "properties": eq.properties,
                        "equipped": eq.equipped
                    } for eq in self.background.equipment
                ],
                "features": [
                    {
                        "name": feature.name,
                        "source": feature.source,
                        "description": feature.description,
                        "level_acquired": feature.level_acquired,
                        "uses_per_day": feature.uses_per_day,
                        "recharge": feature.recharge
                    } for feature in self.background.features
                ],
                "ideals": self.background.ideals,
                "bonds": self.background.bonds,
                "flaws": self.background.flaws
            },
            "level": self.level,
            "abilities": {
                name: {
                    "name": ability.name,
                    "value": ability.value,
                    "modifier": ability.modifier,
                    "description": ability.description
                } for name, ability in self.abilities.items()
            },
            "skills": {
                name: {
                    "name": skill.name,
                    "ability": skill.ability,
                    "proficient": skill.proficient,
                    "expertise": skill.expertise,
                    "modifier": skill.modifier,
                    "description": skill.description
                } for name, skill in self.skills.items()
            },
            "proficiencies": self.proficiencies,
            "armor_class": self.armor_class,
            "hit_points": self.hit_points,
            "max_hit_points": self.max_hit_points,
            "hit_dice": self.hit_dice,
            "equipment": [
                {
                    "name": eq.name,
                    "type": eq.type,
                    "quantity": eq.quantity,
                    "weight": eq.weight,
                    "value": eq.value,
                    "description": eq.description,
                    "properties": eq.properties,
                    "equipped": eq.equipped
                } for eq in self.equipment
            ],
            "spells": [
                {
                    "name": spell.name,
                    "level": spell.level,
                    "school": spell.school,
                    "casting_time": spell.casting_time,
                    "range": spell.range,
                    "components": spell.components,
                    "duration": spell.duration,
                    "description": spell.description,
                    "damage": spell.damage,
                    "save": spell.save,
                    "prepared": spell.prepared
                } for spell in self.spells
            ],
            "spell_slots": self.spell_slots,
            "features": [
                {
                    "name": feature.name,
                    "source": feature.source,
                    "description": feature.description,
                    "level_acquired": feature.level_acquired,
                    "uses_per_day": feature.uses_per_day,
                    "recharge": feature.recharge
                } for feature in self.features
            ],
            "personality_traits": self.personality_traits,
            "ideals": self.ideals,
            "bonds": self.bonds,
            "flaws": self.flaws,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "campaign_id": self.campaign_id,
            "player_name": self.player_name,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """Create character from dictionary"""
        # Helper function to create features from dict
        def create_feature(feature_data):
            return Feature(
                name=feature_data["name"],
                source=feature_data["source"],
                description=feature_data["description"],
                level_acquired=feature_data.get("level_acquired"),
                uses_per_day=feature_data.get("uses_per_day"),
                recharge=feature_data.get("recharge")
            )
        
        # Helper function to create equipment from dict
        def create_equipment(eq_data):
            return Equipment(
                name=eq_data["name"],
                type=eq_data["type"],
                quantity=eq_data.get("quantity", 1),
                weight=eq_data.get("weight"),
                value=eq_data.get("value"),
                description=eq_data.get("description"),
                properties=eq_data.get("properties"),
                equipped=eq_data.get("equipped", False)
            )
        
        # Helper function to create spells from dict
        def create_spell(spell_data):
            return Spell(
                name=spell_data["name"],
                level=spell_data["level"],
                school=spell_data["school"],
                casting_time=spell_data["casting_time"],
                range=spell_data["range"],
                components=spell_data["components"],
                duration=spell_data["duration"],
                description=spell_data["description"],
                damage=spell_data.get("damage"),
                save=spell_data.get("save"),
                prepared=spell_data.get("prepared", False)
            )
        
        # Create race
        race_data = data["race"]
        race = Race(
            name=race_data["name"],
            subrace=race_data.get("subrace"),
            ability_score_increases=race_data.get("ability_score_increases", {}),
            size=race_data.get("size", "Medium"),
            speed=race_data.get("speed", 30),
            languages=race_data.get("languages", []),
            proficiencies=race_data.get("proficiencies", []),
            traits=[create_feature(trait_data) for trait_data in race_data.get("traits", [])]
        )
        
        # Create character class
        class_data = data["character_class"]
        character_class = CharacterClass(
            name=class_data["name"],
            level=class_data["level"],
            hit_die=class_data["hit_die"],
            primary_abilities=class_data["primary_abilities"],
            saving_throw_proficiencies=class_data["saving_throw_proficiencies"],
            features=[create_feature(feature_data) for feature_data in class_data.get("features", [])],
            spells_known=[create_spell(spell_data) for spell_data in class_data.get("spells_known", [])],
            spell_slots=class_data.get("spell_slots")
        )
        
        # Create background
        background_data = data["background"]
        background = Background(
            name=background_data["name"],
            skill_proficiencies=background_data.get("skill_proficiencies", []),
            languages=background_data.get("languages", []),
            equipment=[create_equipment(eq_data) for eq_data in background_data.get("equipment", [])],
            features=[create_feature(feature_data) for feature_data in background_data.get("features", [])],
            ideals=background_data.get("ideals", []),
            bonds=background_data.get("bonds", []),
            flaws=background_data.get("flaws", [])
        )
        
        # Create abilities
        abilities = {}
        for name, ability_data in data["abilities"].items():
            abilities[name] = Ability(
                name=ability_data["name"],
                value=ability_data["value"],
                modifier=ability_data.get("modifier"),
                description=ability_data.get("description")
            )
        
        # Create skills
        skills = {}
        for name, skill_data in data["skills"].items():
            skills[name] = Skill(
                name=skill_data["name"],
                ability=skill_data["ability"],
                proficient=skill_data.get("proficient", False),
                expertise=skill_data.get("expertise", False),
                modifier=skill_data.get("modifier"),
                description=skill_data.get("description")
            )
        
        return cls(
            id=data["id"],
            name=data["name"],
            system=data["system"],
            race=race,
            character_class=character_class,
            background=background,
            level=data["level"],
            abilities=abilities,
            skills=skills,
            proficiencies=data.get("proficiencies", []),
            armor_class=data.get("armor_class", 10),
            hit_points=data.get("hit_points", 1),
            max_hit_points=data.get("max_hit_points", 1),
            hit_dice=data.get("hit_dice", "1d8"),
            equipment=[create_equipment(eq_data) for eq_data in data.get("equipment", [])],
            spells=[create_spell(spell_data) for spell_data in data.get("spells", [])],
            spell_slots=data.get("spell_slots", {}),
            features=[create_feature(feature_data) for feature_data in data.get("features", [])],
            personality_traits=data.get("personality_traits", []),
            ideals=data.get("ideals", []),
            bonds=data.get("bonds", []),
            flaws=data.get("flaws", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            campaign_id=data.get("campaign_id"),
            player_name=data.get("player_name"),
            notes=data.get("notes", "")
        )


@dataclass
class NPC:
    """Represents a non-player character"""
    id: str
    name: str
    system: str
    
    # Basic info
    race: Optional[str] = None
    character_class: Optional[str] = None
    level: Optional[int] = None
    
    # Role and purpose
    role: str = "civilian"  # civilian, merchant, guard, noble, etc.
    occupation: Optional[str] = None
    location: Optional[str] = None
    
    # Personality
    personality_traits: List[str] = field(default_factory=list)
    ideals: List[str] = field(default_factory=list)
    bonds: List[str] = field(default_factory=list)
    flaws: List[str] = field(default_factory=list)
    
    # Appearance and mannerisms
    appearance: Optional[str] = None
    mannerisms: List[str] = field(default_factory=list)
    
    # Relationships
    relationships: Dict[str, str] = field(default_factory=dict)  # name -> relationship type
    
    # Combat stats (if needed)
    armor_class: Optional[int] = None
    hit_points: Optional[int] = None
    abilities: Optional[Dict[str, int]] = None
    
    # Equipment and possessions
    equipment: List[Equipment] = field(default_factory=list)
    wealth: Optional[str] = None
    
    # Story hooks
    secrets: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)
    plot_hooks: List[str] = field(default_factory=list)
    
    # Meta information
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    campaign_id: Optional[str] = None
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert NPC to dictionary for storage"""
        return {
            "id": self.id,
            "name": self.name,
            "system": self.system,
            "race": self.race,
            "character_class": self.character_class,
            "level": self.level,
            "role": self.role,
            "occupation": self.occupation,
            "location": self.location,
            "personality_traits": self.personality_traits,
            "ideals": self.ideals,
            "bonds": self.bonds,
            "flaws": self.flaws,
            "appearance": self.appearance,
            "mannerisms": self.mannerisms,
            "relationships": self.relationships,
            "armor_class": self.armor_class,
            "hit_points": self.hit_points,
            "abilities": self.abilities,
            "equipment": [
                {
                    "name": eq.name,
                    "type": eq.type,
                    "quantity": eq.quantity,
                    "weight": eq.weight,
                    "value": eq.value,
                    "description": eq.description,
                    "properties": eq.properties,
                    "equipped": eq.equipped
                } for eq in self.equipment
            ],
            "wealth": self.wealth,
            "secrets": self.secrets,
            "motivations": self.motivations,
            "plot_hooks": self.plot_hooks,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "campaign_id": self.campaign_id,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NPC':
        """Create NPC from dictionary"""
        equipment = []
        for eq_data in data.get("equipment", []):
            equipment.append(Equipment(
                name=eq_data["name"],
                type=eq_data["type"],
                quantity=eq_data.get("quantity", 1),
                weight=eq_data.get("weight"),
                value=eq_data.get("value"),
                description=eq_data.get("description"),
                properties=eq_data.get("properties"),
                equipped=eq_data.get("equipped", False)
            ))
        
        return cls(
            id=data["id"],
            name=data["name"],
            system=data["system"],
            race=data.get("race"),
            character_class=data.get("character_class"),
            level=data.get("level"),
            role=data.get("role", "civilian"),
            occupation=data.get("occupation"),
            location=data.get("location"),
            personality_traits=data.get("personality_traits", []),
            ideals=data.get("ideals", []),
            bonds=data.get("bonds", []),
            flaws=data.get("flaws", []),
            appearance=data.get("appearance"),
            mannerisms=data.get("mannerisms", []),
            relationships=data.get("relationships", {}),
            armor_class=data.get("armor_class"),
            hit_points=data.get("hit_points"),
            abilities=data.get("abilities"),
            equipment=equipment,
            wealth=data.get("wealth"),
            secrets=data.get("secrets", []),
            motivations=data.get("motivations", []),
            plot_hooks=data.get("plot_hooks", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            campaign_id=data.get("campaign_id"),
            notes=data.get("notes", "")
        )


@dataclass
class CharacterTemplate:
    """Template for character creation for a specific system"""
    system: str
    races: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    backgrounds: List[Dict[str, Any]]
    ability_names: List[str]
    skill_list: List[Dict[str, Any]]
    equipment_packs: List[Dict[str, Any]]
    creation_rules: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            "system": self.system,
            "races": self.races,
            "classes": self.classes,
            "backgrounds": self.backgrounds,
            "ability_names": self.ability_names,
            "skill_list": self.skill_list,
            "equipment_packs": self.equipment_packs,
            "creation_rules": self.creation_rules
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterTemplate':
        """Create template from dictionary"""
        return cls(
            system=data["system"],
            races=data["races"],
            classes=data["classes"],
            backgrounds=data["backgrounds"],
            ability_names=data["ability_names"],
            skill_list=data["skill_list"],
            equipment_packs=data["equipment_packs"],
            creation_rules=data["creation_rules"]
        )