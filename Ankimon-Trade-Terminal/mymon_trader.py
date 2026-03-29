# === Importing Modules ===

import json
import hashlib
import uuid
from pathlib import Path
import os

# --- Modules for UnexpectedError ---
import traceback
from time import sleep
from datetime import datetime
import random

# ===============================
# Initialisations
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
addon_dir = Path(__file__).parent

mypokemon_path = addon_dir / "mypokemon.json"
mydevmon_path = addon_dir / "mydevmon.json"

pokedex_path = addon_dir / "data_files" / "pokedex.json"
moves_file_path = addon_dir / "data_files" / "moves.json"
pokeapi_db_path = addon_dir / "data_files" / "pokeapi_db.json"

trade_memory_path = addon_dir / "mymon_trades.json"

TRADE_VERSION = "02"

# ===============================
# File Helpers
# ===============================

def load_json(path, default):
    if not path.exists():
        return default
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def load_mypokemon():
    return load_json(mypokemon_path, [])

def save_mypokemon(data):
    save_json(mypokemon_path, data)

def load_mydevmon():
    return load_json(mydevmon_path, [])

def save_mydevmon(data):
    save_json(mydevmon_path, data)

def load_trade_memory():
    return load_json(trade_memory_path, [])

def save_trade_memory(data):
    save_json(trade_memory_path, data)

# ===============================
# Confirm Loop
# ===============================

def confirm_loop(prompt):
    while True:
        c = input(prompt).strip().lower()
        if c == "y":
            return True
        elif c == "n":
            return False
        else:
            print("Invalid input! Do enter 'y' to continue the trade or 'n' to cancel.")

# ===============================
# Mon Helpers
# ===============================

def find_pokemon_by_name(name, environment="mypokemon.json"):
    if environment == "mydevmon.json":
        pokemon_list = load_mydevmon()
    else:
        pokemon_list = load_mypokemon()
    return [p for p in pokemon_list if p['name'].lower() == name.lower()]

def get_pokemon_name_by_id(pid):
    pokedex = load_json(pokedex_path, {})
    for d in pokedex.values():
        if d.get("num") == pid:
            return d.get("name", str(pid))
    return str(pid)

def find_move_by_name(move_name):
    moves = load_json(moves_file_path, {})
    for m in moves.values():
        if m.get("name", "").lower() == move_name.lower():
            return m.get("num", 33)
    return 33

# ===============================
# Trade Code
# ===============================

def generate_trade_code(pokemon):
    gender = {"M": 0, "F": 1, "N": 2}.get(pokemon['gender'], 3)
    shiny = 1 if pokemon.get("shiny") else 0
    evs = ",".join(str(pokemon["ev"][s]) for s in ['hp','atk','def','spa','spd','spe'])
    ivs = ",".join(str(pokemon["iv"][s]) for s in ['hp','atk','def','spa','spd','spe'])
    attacks = ",".join(str(find_move_by_name(a)) for a in pokemon["attacks"])
    return f"{pokemon['id']},{pokemon['level']},{gender},{shiny},{evs},{ivs},{attacks}"

def parse_trade_code(code):
    parts = code.split(",")
    if len(parts) < 16:
        raise ValueError
    nums = [int(x) for x in parts]
    pid = nums[0]
    level = nums[1]
    gender_id = nums[2]
    shiny = bool(nums[3])
    ev = dict(zip(['hp','atk','def','spa','spd','spe'], nums[4:10]))
    iv = dict(zip(['hp','atk','def','spa','spd','spe'], nums[10:16]))
    attacks = nums[16:]
    return pid, level, gender_id, shiny, ev, iv, attacks

# ===============================
# Create Mon
# ===============================

def create_pokemon_from_code(code):
    pid, level, gender_id, shiny, ev, iv, attacks = parse_trade_code(code)
    pokedex = load_json(pokedex_path, {})
    pokeapi = load_json(pokeapi_db_path, [])
    moves = load_json(moves_file_path, {})
    details = None
    for d in pokedex.values():
        if d.get("num") == pid:
            details = d
            break
    if not details:
        raise ValueError
    ability_pool = [v for k,v in details.get("abilities",{}).items() if k.isdigit()]
    ability = random.choice(ability_pool) if ability_pool else "No Ability"
    attack_names = []
    for aid in attacks:
        for m in moves.values():
            if m.get("num")==aid:
                attack_names.append(m["name"])
    if not attack_names:
        attack_names=["Tackle"]
    base_hp = details["baseStats"]["hp"]
    current_hp = int((((2*base_hp+iv["hp"]+ev["hp"]/4)*level)/100)+level+10)
    growth = next((p["growth_rate"] for p in pokeapi if p["id"]==pid),"medium")
    base_exp = next((p["base_experience"] for p in pokeapi if p["id"]==pid),64)
    gender = {0:"M",1:"F",2:"N"}.get(gender_id,"N")
    return {
        "name":details["name"],
        "nickname":"",
        "ability":ability,
        "id":pid,
        "gender":gender,
        "level":level,
        "type":details["types"],
        "stats":details["baseStats"],
        "ev":ev,
        "iv":iv,
        "attacks":attack_names,
        "growth_rate":growth,
        "current_hp":current_hp,
        "base_experience":base_exp,
        "friendship":0,
        "pokemon_defeated":0,
        "everstone":False,
        "shiny":shiny,
        "mega":False,
        "special_form":None,
        "captured_date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "individual_id":str(uuid.uuid4()),
        "xp":0
    }

# ===============================
# Password
# ===============================

def generate_passwords(my_code, partner_code):
    codes = sorted([my_code, partner_code])
    combo = codes[0]+"|"+codes[1]
    h = hashlib.sha256(combo.encode()).hexdigest()
    half = len(h)//2
    if my_code < partner_code:
        return h[:half]+TRADE_VERSION, h[half:]+TRADE_VERSION
    else:
        return h[half:]+TRADE_VERSION, h[:half]+TRADE_VERSION

# ===============================
# Details / Tutorial
# ===============================

def details():
    print("\n-------------------------------------")
    print("? How To Use Ankimon Trade Terminal")
    print("-------------------------------------\n")
    print("1. Trade Pokémon")
    print("- Trade Pokémon with your partner (as of trading via Anki UI).")
    print("- Unfinished trades are saved automatically.")
    print("- Resume unfinished trades anytime.\n")
    print("2. Trade Pokémon (for Dev)")
    print("- Create a pool of up to 6 Pokémon from mypokemon.json.")
    print("- Useful for testing, experimenting, or development.")
    print("- Trades performed here do NOT affect real collection.")
    print("- Unfinished trades are saved automatically.")
    print("- Resume unfinished trades anytime.\n")
    print("3. Clean Memory")
    print("- Review/Delete unfinished trades\n")
    print("General Flow:")
    print("Species Name → Choose Level → Confirmation → Trade Code → Password\n")
    print("---------------------\n")


# ===============================
# Clean Memory
# ===============================

def clean_memory():
    trades = load_trade_memory()
    if not trades:
        print("\nⓘ  No 'hanging' trades found.")
        return
    i = 0
    while i < len(trades):
        t = trades[i]
        print(f"\n(Half-Trade {i+1}/{len(trades)})")
        print(f"Trade away (you): {get_pokemon_name_by_id(t['usermon_id'])}, level {t['usermon_level']}")
        print(f"Trade for (partner): {get_pokemon_name_by_id(t['partnermon_id'])}, level {t['partnermon_level']}")
        print(f"Last Visit: {t['timestamp']}")
        print(f"Environment: {t.get('environment','mypokemon.json')}")
        choice = input("\nKeep / Delete / Cancel (k/d/c): ").lower()
        if choice == "k":
            i += 1
        elif choice == "d":
            trades.pop(i)
            save_trade_memory(trades)
        elif choice == "c":
            return
        else:
            print("Invalid input!")
    print("\n✓ Memory reviewed/cleaned.")

# ===============================
# Dev Pool Selection Helpers
# ===============================

def choose_pokemon(environment="mypokemon.json"):
    while True:
        species = input(
            "\nPlease enter the SPECIES NAME of the Pokémon you're trading away: "
        ).strip().lower()
        matches = find_pokemon_by_name(species, environment)
        if matches:
            break
        print(f"No Pokémon with species '{species}' found in your collection. Do try again!")
    matches = sorted(matches, key=lambda x: x["level"])
    if len(matches) > 1:
        print(f"\nMultiple Pokémon of the species '{species.title()}' found:")
        for i, p in enumerate(matches):
            print(f"{i+1}. Level {p['level']}")
        while True:
            try:
                c = int(
                    input(
                        f"\nPlease choose one labelled number representing the level of {species.title()} to trade away: "
                    )
                ) - 1
                if 0 <= c < len(matches):
                    selected = matches[c]
                    break
            except:
                pass
            print(
                f"Invalid input! Please enter a number between 1 and {len(matches)} inclusive."
            )
    else:
        selected = matches[0]
        print(f"Found one {species.title()}: Level {selected['level']}")
    if not confirm_loop(
        f"\nSelect {selected['name']} (Level {selected['level']})? (y/n): "
    ):
        return choose_pokemon(environment)
    return selected

# ===============================

def choose_devmon():
    while True:
        species = input(
            "\nPlease enter the SPECIES NAME of the Dev Pokémon you're trading away: "
        ).strip().lower()
        matches = find_pokemon_by_name(species, "mydevmon.json")
        if matches:
            break
        print(f"No Dev Pokémon with species '{species}' found in your collection. Do try again!")
    matches = sorted(matches, key=lambda x: x["level"])
    trades = load_trade_memory()
    unfinished = {t['usermon_uuid'] for t in trades if t.get('environment') == 'mydevmon.json'}
    if len(matches) > 1:
        print(f"\nMultiple Dev Pokémon of the species '{species.title()}' found:")
        for i, p in enumerate(matches):
            star = '*' if p['individual_id'] in unfinished else ''
            print(f"{i+1}. Level {p['level']}{star}")
        while True:
            try:
                c = int(
                    input(
                        f"\nPlease choose one labelled number representing the level of {species.title()} to trade away: "
                    )
                ) - 1
                if 0 <= c < len(matches):
                    selected = matches[c]
                    break
            except:
                pass
            print(
                f"Invalid input! Please enter a number between 1 and {len(matches)} inclusive."
            )
    else:
        selected = matches[0]
        star = '*' if selected['individual_id'] in unfinished else ''
        print(f"Found one {species.title()}: Level {selected['level']}{star}")
    if not confirm_loop(
        f"\nSelect {selected['name']} (Level {selected['level']})? (y/n): "
    ):
        print("\n=== Dev Trade Begins ===")
        return choose_devmon()
    return selected

# ===============================

def add_devmon():
    while True:
        species = input(
            "\nPlease enter the SPECIES NAME of the Pokémon to add to Dev Pool: "
        ).strip().lower()
        matches = find_pokemon_by_name(species, "mypokemon.json")
        if matches:
            break
        print(f"No Pokémon with species '{species}' found in your collection. Do try again!")
    matches = sorted(matches, key=lambda x: x["level"])
    if len(matches) > 1:
        print(f"\nMultiple Pokémon of the species '{species.title()}' found:")
        for i, p in enumerate(matches):
            print(f"{i+1}. Level {p['level']}")
        while True:
            try:
                c = int(
                    input(
                        f"\nPlease choose one labelled number representing the level of {species.title()} to add: "
                    )
                ) - 1
                if 0 <= c < len(matches):
                    selected = matches[c]
                    break
            except:
                pass
            print(
                f"Invalid input! Please enter a number between 1 and {len(matches)} inclusive."
            )
    else:
        selected = matches[0]
        print(f"Found one {species.title()}: Level {selected['level']}")
    if not confirm_loop(
        f"\nAdd {selected['name']} (Level {selected['level']}) to Dev Pool? (y/n): "
    ):
        return add_devmon()
    return selected

# ===============================
# Dev Pool Builder
# ===============================

def list_devmons():
    devmons = load_mydevmon()
    trades = load_trade_memory()
    unfinished = {t['usermon_uuid'] for t in trades if t.get('environment') == 'mydevmon.json'}
    from collections import defaultdict
    grouped = defaultdict(list)
    for m in devmons:
        grouped[m['name']].append(m)
    for species in sorted(grouped):
        grouped[species].sort(key=lambda x: x['level'])
        for m in grouped[species]:
            star = '*' if m['individual_id'] in unfinished else ''
            print(f"{species.title()}: Level {m['level']}{star}")

# ===============================
def setup_dev_pool():
    devmons = load_mydevmon()
    mymons = load_mypokemon()
    if len(mymons) < 2:
        print("You must have at least 2 Pokémon in mypokemon.json to use Dev Trade.")
        return None
    trades = load_trade_memory()
    unfinished = {t['usermon_uuid'] for t in trades if t.get('environment') == 'mydevmon.json'}
    if not mydevmon_path.exists():
        print("\nNo mydevmon.json detected. Creating mydevmon.json...")
        devmons = []
        while len(devmons) < 2:
            print(f"\nSelect Dev Pokémon {len(devmons)+1}/2")
            mon = add_devmon()
            devmons.append(mon)
        save_mydevmon(devmons)
    else:
        print("\nCurrent Dev Pokémon Pool:")
        list_devmons()
        if confirm_loop("\nAdd Pokémon from mypokemon.json? (y/n): "):
            while True:
                if len(devmons) < 6:
                    mon = add_devmon()
                    devmons.append(mon)
                    save_mydevmon(devmons)
                    if not confirm_loop("\nAdd more Pokémon? (y/n): "):
                        print("\nCurrent Dev Pokémon Pool:")
                        list_devmons()
                        if confirm_loop("\nTrade away a Dev Pokémon? (y/n): "):
                            selected = choose_devmon()
                            devmons.remove(selected)
                            save_mydevmon(devmons)
                        break
                else:
                    print("\nMaximum of 6 Dev Pokémon reached.")
                    devmons = sorted(devmons, key=lambda x: (x['name'], x['level']))
                    for i, m in enumerate(devmons):
                        star = '*' if m['individual_id'] in unfinished else ''
                        print(f"{i+1}. {m['name']} Level {m['level']}{star}")
                    while True:
                        try:
                            r = int(
                                input(
                                    "\nChoose which Pokémon to replace: "
                                )
                            ) - 1
                            if 0 <= r < 6:
                                break
                        except:
                            pass
                        print("Invalid input!")
                    new_mon = add_devmon()
                    if confirm_loop(
                        f"Replace {devmons[r]['name']} Level {devmons[r]['level']}? (y/n): "
                    ):
                        devmons[r] = new_mon
                        save_mydevmon(devmons)
                    if not confirm_loop("\nReplace more Pokémon? (y/n): "):
                        break
    return load_mydevmon()

# ===============================
# Trade Engine
# ===============================

def trade_engine(environment="mypokemon.json"):
    if environment == "mydevmon.json":
        mons = load_mydevmon()
    else:
        mons = load_mypokemon()
    if not mons:
        print("No Pokémon available.")
        return
    if environment == "mydevmon.json":
        selected = choose_devmon()
    else:
        selected = choose_pokemon(environment)
    trades = load_trade_memory()
    for t in trades:
        if (
            t["usermon_uuid"] == selected["individual_id"]
            and t.get("environment", "mypokemon.json") == environment
        ):
            partner_name = get_pokemon_name_by_id(t["partnermon_id"])
            if confirm_loop(
                f"\nContinue unfinished trade with {partner_name} level {t['partnermon_level']}? (y/n): "
            ):
                partner_code = t["partner_code"]
                my_trade_code = generate_trade_code(selected)
                break
            else:
                trades.remove(t)
                save_trade_memory(trades)
    else:
        if not confirm_loop(
            f"\nTrade away {selected['name']} (Level {selected['level']})? (y/n): "
        ):
            print("🗑 Trade cancelled.")
            return
        print("\n=== Trade Begins ===")
        my_trade_code = generate_trade_code(selected)
        print(f"\nYour Trade Code (to send to partner): {my_trade_code}")
        while True:
            partner_code = input(
                "Enter trade partner's Trade Code: "
            ).strip()
            try:
                pid = int(partner_code.split(",")[0])
                if pid == selected["id"]:
                    print(
                        "✘ Error! You cannot trade Pokémon of the same species.\n"
                    )
                    continue
                partner = create_pokemon_from_code(partner_code)
                break
            except:
                print(
                    "✘ Error! Incorrect partner Trade Code. Please check with your partner.\n"
                )
        print(
            f"\nOngoing trade between:\n"
            f"-{selected['name']} of level {selected['level']} (you)\n"
            f"-{partner['name']} of level {partner['level']} (partner)"
        )
        if not confirm_loop("\nConfirm and continue trade? (y/n): "):
            print("🗑 Trade cancelled.")
            return
        trades.append(
            {
                "usermon_uuid": selected["individual_id"],
                "usermon_id": selected["id"],
                "usermon_level": selected["level"],
                "partnermon_id": partner["id"],
                "partnermon_level": partner["level"],
                "partner_code": partner_code,
                "environment": environment,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        save_trade_memory(trades)

    # --- Password ---

    my_pass, expected = generate_passwords(
        my_trade_code, partner_code
    )
    print(f"\nYour Trade Password (to send to partner): {my_pass}")
    while True:
        p = input("Enter trade partner's Trade Password: ").strip()
        if p == expected:
            break
        print(
            "✘ Error! Incorrect partner's Trade Password. Please check with your partner.\n"
        )
    partner = create_pokemon_from_code(partner_code)
    if not confirm_loop(
        f"\n(Final Confirmation)\nTrade away {selected['name']} level {selected['level']}, "
        f"for {partner['name']} level {partner['level']}? (y/n): "
    ):
        print("🗑 Trade cancelled.")
        return
    if environment == "mydevmon.json":
        mons = load_mydevmon()
    else:
        mons = load_mypokemon()
    for i, p in enumerate(mons):
        if p["individual_id"] == selected["individual_id"]:
            mons[i] = partner
            break
    if environment == "mydevmon.json":
        save_mydevmon(mons)
    else:
        save_mypokemon(mons)
    trades = load_trade_memory()
    trades = [
        t
        for t in trades
        if not (
            t["usermon_uuid"] == selected["individual_id"]
            and t.get("environment", "mypokemon.json")
            == environment
        )
    ]
    save_trade_memory(trades)
    print("\n✓ Trade completed successfully!")

# ===============================
# Main
# ===============================

def main():
    print("\n==================================")
    print("Ankimon Trade Terminal")
    print("(press Ctrl+C to quit/force quit)")
    print("==================================\n")
    print("1. Trade Pokémon")
    print("2. Trade Pokémon (for Dev)")
    print("3. Clean Memory")
    print("4. How to Use Ankimon Trade Terminal?")
    while True:
        start = input(
            "\nPlease select one option (input 1 or 2 or 3 or 4): "
        ).strip()
        if start == "1":
            print("⌕ Selected: Trade Pokémon")
            trade_engine("mypokemon.json")
            break
        elif start == "2":
            print("⌕ Selected: Trade Pokémon (for Dev)")
            setup_dev_pool()
            trade_engine("mydevmon.json")
            break
        elif start == "3":
            print("⌕ Selected: Clean Memory")
            clean_memory()
            main()
        elif start == "4":
            print("⌕ Selected: How to Use Ankimon Trade Terminal?")
            details()
            main()
        else:
            print("Invalid input! Do enter '1', '2', '3', or '4'.")

# ===============================
# Outro
# ===============================

def outro():
    print("\n==================================")
    print("Thank you for using")
    print("Ankimon Trade Terminal.")
    print("Feel free to report any bugs or suggest improvements in")
    print("https://github.com/Nut2026/My-Ankimon-Contributions/issues")
    print("Even more thanks to the Ankimon Devs for designing the trade logic!")
    print("Have a nice day!")
    print("==================================\n")

# ===============================
# Error Handler
# ===============================

def sanitise_traceback(exc):
    tb = traceback.extract_tb(exc.__traceback__)
    lines = []
    for f in tb:
        filename = f.filename
        if filename.startswith(BASE_DIR):
            filename = filename.replace(BASE_DIR, "<PROJECT_DIR>")
        else:
            filename = "<ABS_PATH>"
        lines.append(
            f'File "{filename}", line {f.lineno}, in {f.name}'
        )
    return "\n".join(lines)

def run_program():
    try:
        main()
        outro()
    except KeyboardInterrupt:
        print("\n♺ Keyboard Interrupt detected. Exiting safely...")
        outro()

    except Exception as e:
        print("\n🚨🚨 A fatal error has occurred. 🚨🚨\n")
        print("Error Type:", type(e).__name__)
        print("Error Message:", str(e))
        print("\nSanitised Traceback (for debugging):")
        print(sanitise_traceback(e))
        print("\n🚨🚨 Ankimon Trade Terminal -- crashed. 🚨🚨\n")

# ===============================
# Start
# ===============================

if __name__ == "__main__":
    run_program()
