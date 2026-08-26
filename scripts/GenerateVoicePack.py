"""Renders the Spanish voice packs into src/Sounds/<pack>/.

The spell lists, the file naming and the rendering pipeline all belong to MiniAuras, so this
imports its generator from the sibling checkout rather than restating any of it. What lives here
is the Spanish side: which voices, what they say, and the check that the clip names still match
the packs MiniAuras ships.

Run from the repo root with the ELEVENLABS_API_KEY environment variable set:
    python scripts/GenerateVoicePack.py [--force] [--allow-english]

Existing clips are skipped unless --force is given. A spell with no Spanish name stops the run,
because a pack that announces one spell in English is worse than one that was never built;
--allow-english renders it in English anyway.
"""

import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
# MiniAuras is expected beside this repo. Nothing is copied out of it: the spell lists and the
# clip names have one owner, and a stale duplicate here would ship a pack that plays nothing.
MINIAURAS = REPO.parent / "MiniAuras"

if not MINIAURAS.is_dir():
    sys.exit(f"MiniAuras checkout not found at {MINIAURAS}")

sys.path.insert(0, str(MINIAURAS / "scripts"))

import GenerateTtsAudio as base  # noqa: E402

VOICES = {
    "Miguel": "k8cFOyAg7B9qwBlDDNTC",
    "Kate": "qWWAqFomnJ99VwQLREfT",
}
# Multilingual v2 gives the steadiest Spanish reading.
MODEL_ID = "eleven_multilingual_v2"

NAMES = pathlib.Path(__file__).resolve().parent / "SpellNamesEsES.json"
OUT_DIR = REPO / "src" / "Sounds"
# The pack every generated clip name is checked against.
REFERENCE_PACK = MINIAURAS / "src" / "Sounds" / "TTS" / "David"

PREVIEWS = {
    "PreviewImportant": "Importante",
    "PreviewDefensive": "Defensivo",
    "PreviewEnemyDebuff": "Perjuicio enemigo",
}
# Spoken when the pack is picked in the dropdown. A real announcement, long enough to judge the
# voice by.
PREVIEW_VOICE_TEXT = "Gracia del caminaespíritus"

# English spell name -> what the Spanish voices say instead of the client's name for it. Most
# entries cut a long name down to the part a player reacts to. The rest correct a name the
# client gets wrong for us, because our spell id is the aura and the aura carries another
# ability's name.
SHORT_NAMES = {
    "Ancient of Lore": "Anciano",
    "Arcane Surge": "Oleada",
    "Aspect of the Turtle": "Tortuga",
    "Avenging Crusader": "Cruzado",
    "Barkskin": "Piel",
    "Blessing of Freedom": "Libertad",
    "Blessing of Protection": "Protección",
    "Blessing of Sacrifice": "Sacrificio",
    "Blessing of Sanctuary": "Santuario",
    "Blessing of Spellwarding": "Resguardo",
    "Celestial Alignment": "Encarnación",
    "Cloak of Shadows": "Capa",
    "Colossus Smash": "Machaque",
    "Dark Simulacrum": "Simulación",
    "Emerald Communion": "Comunión",
    "Enraged Regeneration": "Regeneración",
    "Greater Invisibility": "Invisibilidad",
    # The aura is Divine Shield's, so the client name is Escudo divino.
    "Guardian of the Forgotten Queen": "Reina olvidada",
    "Ice Block": "Bloque",
    "Incarnation: Avatar of Ashamane": "Encarnación",
    "Incarnation: Chosen of Elune": "Encarnación",
    "Incarnation: Guardian of Ursoc": "Encarnación",
    # The aura drops the form, so the client name is a bare Encarnación.
    "Incarnation: Tree of Life": "Encarnación",
    "Invoke Chi-Ji, the Red Crane": "Chi-Ji",
    "Invoke Niuzao, the Black Ox": "Niuzao",
    # The aura is Yu'lon's Blessing, so the client name is Bendiciones de Yu'lon.
    "Invoke Yu'lon, the Jade Serpent": "Yu'lon",
    "Life Cocoon": "Crisálida",
    "Nullifying Shroud": "Velo",
    "Obsidian Scales": "Escamas",
    "Rallying Cry": "Berrido",
    # The aura is Amplified Refraction, so the client name is Refracción amplificada.
    "Refractive Images": "Imágenes refractivas",
    # The aura is Mortal Strike's, so the client name is Golpe mortal.
    "Sharpen Blade": "Hoja afilada",
    "Shield Wall": "Muro",
    "Spell Reflection": "Reflejo",
    # The aura belongs to the totem, so the client name is Tótem Enlace de espíritu.
    "Spirit Link": "Enlace de espíritu",
    "Survival Instincts": "Instintos",
    "Touch of Karma": "Karma",
    "Unending Resolve": "Resolución",
}


def build_texts(categories, names):
    """File stem -> the Spanish text that stem's clip speaks, and the names with no Spanish."""
    texts = {}
    untranslated = []

    for ids in categories.values():
        for name in ids.values():
            text = base.spoken_text(name)
            spoken = SHORT_NAMES.get(text) or names.get(text)

            if not spoken:
                untranslated.append(text)

            texts[base.slug(text)] = spoken or text

    texts.update(PREVIEWS)
    texts["PreviewVoice"] = PREVIEW_VOICE_TEXT

    return texts, sorted(set(untranslated))


def check_against_shipped(stems):
    """A pack whose file names drift from MiniAuras' own plays nothing for the clips that
    differ, and says so nowhere, so the mismatch is caught here instead."""
    if not REFERENCE_PACK.is_dir():
        sys.exit(f"reference pack not found at {REFERENCE_PACK}")

    shipped = {path.stem for path in REFERENCE_PACK.glob("*.ogg")}
    missing = sorted(shipped - stems)
    extra = sorted(stems - shipped)

    if missing or extra:
        sys.exit(f"clip names do not match {REFERENCE_PACK.name}: missing {missing}, extra {extra}")


def main():
    api_key = os.environ.get("ELEVENLABS_API_KEY")

    if not api_key:
        sys.exit("set ELEVENLABS_API_KEY")

    force = "--force" in sys.argv

    names = json.loads(NAMES.read_text(encoding="utf-8"))
    texts, untranslated = build_texts(base.parse_categories(), names)

    if untranslated and "--allow-english" not in sys.argv:
        listed = "\n  ".join(untranslated)
        sys.exit(
            f"no Spanish name for:\n  {listed}\n"
            "re-run scripts/FetchSpellNamesEsES.py, or pass --allow-english to speak these in English"
        )

    for name in untranslated:
        print(f"WARNING: no Spanish name for '{name}', speaking English")

    check_against_shipped(set(texts))

    rendered, reused = 0, 0

    for pack, voice_id in VOICES.items():
        pack_dir = OUT_DIR / pack
        pack_dir.mkdir(parents=True, exist_ok=True)

        for file_stem in sorted(texts):
            path = pack_dir / f"{file_stem}.ogg"

            if path.exists() and not force:
                reused += 1
                continue

            base.render(api_key, voice_id, texts[file_stem], path, 0.0, MODEL_ID)
            rendered += 1
            print(f"rendered {pack}/{path.name}")

    print(f"{rendered} clip(s) rendered, {reused} reused")


if __name__ == "__main__":
    main()
