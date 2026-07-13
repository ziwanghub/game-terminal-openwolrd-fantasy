#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pixel Fantasy: Open Skill World (เอลิเรีย: โลกสกิลเปิดพิกเซลแฟนตาซี)
เกมต้นแบบข้อความล้วน - ไม่มีกราฟิก ไม่มีเอฟเฟกต์
แนว: Open World, Open Skill, สกิลอิสระคอมโบเอง, Multiplay PvP แย่งพื้นที่, อาจารย์เทพ, ความกดดัน, เงิน 3 ชนิด
"""

import random
import time

# ==================== ข้อมูลเกม ====================
AREAS = ["ป่ามืด", "ภูเขาหิน", "เมืองโบราณ", "ถ้ำเงา", "ทะเลทรายร้อน"]

OCCUPATIONS = {
    "นักรบ": {"hp": 130, "atk": 6, "pressure": 8, "skill": "basic_strike", "desc": "แข็งแกร่ง ดาเมจสูง"},
    "นักเวทย์": {"hp": 85, "mana": 90, "atk": 2, "skill": "magic_missile", "desc": "เวทย์มนต์ มานาสูง"},
    "นักธนู": {"hp": 95, "atk": 9, "pressure": 5, "skill": "arrow_shot", "desc": "โจมตีระยะไกล แม่นยำ"},
    "โจรเงา": {"hp": 90, "atk": 5, "pressure": 18, "skill": "shadow_strike", "desc": "กดดันสูง หลอกลวง"},
    "นักบวช": {"hp": 110, "mana": 70, "atk": 3, "skill": "heal", "desc": "ฟื้นฟู พรคุ้มครอง"}
}

ZODIAC_BONUSES = {
    "เมษ": {"atk": 5, "desc": "พลังโจมตี +5"},
    "พฤษภ": {"hp": 12, "desc": "พลังชีวิต +12"},
    "เมถุน": {"mana": 12, "desc": "มานา +12"},
    "กรกฎ": {"pressure": 8, "desc": "ความกดดันเริ่มต้น +8"},
    "สิงห์": {"atk": 4, "desc": "โบนัสความกล้า +4"},
    "กันย์": {"mastery_gain": 2, "desc": "ชำนาญพื้นที่เร็ว +2"},
    "ตุลย์": {"balance": True, "desc": "สมดุล HP/Mana ดี"},
    "พิจิก": {"deceive": 12, "desc": "โอกาสหลอกลวง +12%"},
    "ธนู": {"explore": 3, "desc": "สำรวจได้ดี +3"},
    "มังกร": {"money_world": 50, "desc": "เริ่มด้วยเงินโลก +50"},
    "กุมภ์": {"skill_chance": 8, "desc": "โอกาสได้สกิล +8%"},
    "มีน": {"blessing_duration": 3, "desc": "พรเทพยาวนาน +3"}
}

POPULAR_SKILLS = {
    "fire_ball": 38,
    "counter_strike": 27,
    "last_stand": 18,
    "nature_heal": 22,
    "shadow_step": 31
}

SKILL_LIST = {
    "basic_strike": {"name": "การโจมตีพื้นฐาน", "dmg": 10, "type": "attack"},
    "magic_missile": {"name": "กระสุนเวทย์", "dmg": 12, "type": "magic"},
    "arrow_shot": {"name": "ยิงธนู", "dmg": 14, "type": "ranged"},
    "shadow_strike": {"name": "โจมตีเงา", "dmg": 11, "type": "stealth"},
    "heal": {"name": "รักษา", "heal": 20, "type": "support"},
    "fire_ball": {"name": "ลูกไฟ", "dmg": 28, "type": "fire"},
    "counter_strike": {"name": "การโต้กลับ", "dmg": 18, "type": "counter"},
    "last_stand": {"name": "ยืนหยัดสุดท้าย", "dmg": 22, "type": "desperate"},
    "nature_heal": {"name": "รักษาธรรมชาติ", "heal": 25, "type": "nature"},
    "shadow_step": {"name": "ก้าวเงา", "dmg": 15, "type": "stealth"}
}

def get_zodiac(day, month):
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "เมษ"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "พฤษภ"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "เมถุน"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "กรกฎ"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "สิงห์"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "กันย์"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "ตุลย์"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "พิจิก"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "ธนู"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "มังกร"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "กุมภ์"
    elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
        return "มีน"
    return "ไม่ทราบ"

def create_character():
    print("=" * 50)
    print("🌟 สร้างตัวละคร - Pixel Fantasy: Open Skill World")
    print("=" * 50)
    name = input("ชื่อตัวละคร: ").strip()
    if not name:
        name = "นักผจญภัยนิรนาม"
    gender = input("เพศ (ชาย/หญิง/อื่นๆ): ").strip() or "ไม่ระบุ"
    birth_input = input("วันเกิด (วัน/เดือน/ปี เช่น 15/6/2000): ").strip()
    try:
        day, month, year = map(int, birth_input.split('/'))
        zodiac = get_zodiac(day, month)
    except:
        day, month, year = 1, 1, 2000
        zodiac = "เมษ"
    print(f"\nราศีของคุณคือ: {zodiac} ({ZODIAC_BONUSES[zodiac]['desc']})")

    print("\nเลือกอาชีพเริ่มต้น:")
    occ_list = list(OCCUPATIONS.keys())
    for i, occ in enumerate(occ_list, 1):
        info = OCCUPATIONS[occ]
        print(f"  {i}. {occ} - {info['desc']} (HP+{info.get('hp',90)} ATK+{info.get('atk',5)})")
    try:
        occ_idx = int(input("เลือก (1-5): ")) - 1
        occupation = occ_list[max(0, min(4, occ_idx))]
    except:
        occupation = "นักรบ"

    occ_data = OCCUPATIONS[occupation]
    z_bonus = ZODIAC_BONUSES[zodiac]

    player = {
        "name": name,
        "gender": gender,
        "birth": f"{day}/{month}/{year}",
        "zodiac": zodiac,
        "occupation": occupation,
        "level": 1,
        "exp": 0,
        "hp": occ_data.get("hp", 100),
        "max_hp": occ_data.get("hp", 100),
        "mana": occ_data.get("mana", 50),
        "max_mana": occ_data.get("mana", 50),
        "pressure": occ_data.get("pressure", 10) + z_bonus.get("pressure", 0),
        "bonus_atk": occ_data.get("atk", 5) + z_bonus.get("atk", 0),
        "mastery_gain_bonus": z_bonus.get("mastery_gain", 0),
        "deceive_bonus": z_bonus.get("deceive", 0),
        "money_world": 150 + z_bonus.get("money_world", 0),
        "money_heaven": 8,
        "money_hell": 3,
        "inventory": ["ยา HP ขนาดเล็ก"],
        "equip": {"weapon": None, "armor": None},
        "cards": [],
        "skills": [occ_data["skill"]],
        "area_mastery": {area: 15 for area in AREAS},
        "action_counts": {"attack": 0, "defend": 0, "explore": 0, "rest": 0, "low_hp": 0},
        "time_units": 0,
        "other_players": 0,
        "blessings": [],
        "disciple_of": None,
        "blessing_turns": 0
    }
    if z_bonus.get("balance"):
        player["max_hp"] += 5
        player["hp"] += 5
        player["max_mana"] += 5
        player["mana"] += 5

    print(f"\n✅ สร้างตัวละครสำเร็จ! {name} ({occupation}) - ราศี {zodiac}")
    print(f"HP: {player['hp']} | Mana: {player['mana']} | กดดัน: {player['pressure']} | ATK โบนัส: {player['bonus_atk']}")
    print(f"เงิน: โลก {player['money_world']} | สวรรค์ {player['money_heaven']} | นรก {player['money_hell']}")
    input("\nกด Enter เพื่อเริ่มเกม...")
    return player

def show_status(player, current_area):
    print("\n" + "=" * 50)
    print(f"📊 สถานะ: {player['name']} | Lv.{player['level']} | {player['occupation']} | {player['zodiac']}")
    print(f"❤️ HP: {player['hp']}/{player['max_hp']}   💧 Mana: {player['mana']}/{player['max_mana']}   🔥 กดดัน: {player['pressure']}")
    print(f"💰 เงินโลก: {player['money_world']} | สวรรค์: {player['money_heaven']} | นรก: {player['money_hell']}")
    print(f"📍 พื้นที่: {current_area} (ชำนาญ {player['area_mastery'][current_area]}%)")
    print(f"🎒 สกิล: {', '.join(player['skills'])}")
    if player['equip']['weapon']:
        print(f"⚔️ สวมใส่: {player['equip']['weapon']}")
    if player['equip']['armor']:
        print(f"🛡️ สวมใส่: {player['equip']['armor']}")
    if player['cards']:
        print(f"🃏 การ์ด: {', '.join(player['cards'])}")
    if player['blessings']:
        print(f"✨ พรเทพ: {', '.join(player['blessings'])} (เหลือ ~{player['blessing_turns']} เทิร์น)")
    if player['disciple_of']:
        print(f"👨‍🏫 ศิษย์ของ: {player['disciple_of']}")
    print(f"👥 ผู้เล่นอื่นในพื้นที่: {player['other_players']} คน")
    print("=" * 50)

def check_area_event(player, current_area):
    player['time_units'] += 1
    if player['time_units'] % 5 == 0:
        print("\n🌟 *** พื้นที่เปิดแล้ว! (เหมือน 3 นาทีผ่านไป) โอกาสแย่งชิงพื้นที่สูง ***")
        player['other_players'] = random.randint(2, 5)
    else:
        player['other_players'] = random.randint(0, 3)
    if player['other_players'] > 0:
        print(f"👥 แจ้งเตือน: มีผู้เล่นอื่น {player['other_players']} คนใน {current_area} ! สามารถท้าประลองได้")

def rest(player):
    print("\n😴 คุณพักผ่อนในพื้นที่...")
    heal = 25 + (player['mana'] // 5)
    player['hp'] = min(player['max_hp'], player['hp'] + heal)
    player['mana'] = min(player['max_mana'], player['mana'] + 18)
    player['pressure'] = max(0, player['pressure'] - 8)
    player['action_counts']['rest'] += 1
    player['time_units'] += 1
    print(f"ฟื้นฟู HP +{heal} | Mana +18 | ความกดดันลดลง")
    if player['blessing_turns'] > 0:
        player['blessing_turns'] -= 1
        if player['blessing_turns'] <= 0:
            player['blessings'] = []
            print("พรเทพหมดอายุแล้ว...")

def get_effective_dmg(base_dmg, player, current_area):
    mastery = player['area_mastery'][current_area]
    multiplier = 0.6 + (mastery / 100) * 0.8  # 0.6 ~ 1.4
    if player['blessing_turns'] > 0:
        multiplier += 0.15
    return int(base_dmg * multiplier)

def combat(player, current_area):
    monsters = {
        "ป่ามืด": ["Goblin นักล่า", "Wolf ป่า", "Ent ไม้ยักษ์"],
        "ภูเขาหิน": ["Rock Golem", "Mountain Troll", "Stone Drake"],
        "เมืองโบราณ": ["Ancient Guardian", "Ruins Specter", "Cursed Knight"],
        "ถ้ำเงา": ["Shadow Wraith", "Cave Bat Swarm", "Dark Slime"],
        "ทะเลทรายร้อน": ["Sand Scorpion", "Desert Raider", "Fire Salamander"]
    }
    monster_name = random.choice(monsters.get(current_area, ["Unknown Beast"]))
    monster_hp = random.randint(45, 95)
    monster_pressure = random.randint(5, 25)
    print(f"\n⚔️ การต่อสู้! เจอ {monster_name} (HP: {monster_hp} | กดดัน: {monster_pressure})")

    turn = 0
    while monster_hp > 0 and player['hp'] > 0:
        turn += 1
        print(f"\n--- เทิร์น {turn} ---")
        print(f"🐉 {monster_name} HP: {max(0, monster_hp)} | กดดัน: {monster_pressure}")
        print(f"คุณ HP: {player['hp']} | Mana: {player['mana']} | กดดัน: {player['pressure']}")
        print("1. โจมตีปกติ")
        print("2. ใช้ความกดดัน (หลอก/กดดันศัตรู)")
        print("3. ป้องกัน")
        print("4. ใช้สกิล (คอมโบเองได้)")
        print("5. หนี (โอกาสขึ้นกับกดดัน)")
        choice = input("เลือกการกระทำ: ").strip()

        player_dmg = 0
        defended = False

        if choice == "1":
            player_dmg = 8 + player['bonus_atk'] + random.randint(0, 6)
            player['action_counts']['attack'] += 1
            print(f"คุณโจมตี! สร้าง {player_dmg} ความเสียหาย")
        elif choice == "2":
            if player['pressure'] >= 8:
                deceive_chance = 40 + player['deceive_bonus']
                if random.randint(1, 100) < deceive_chance:
                    print("คุณหลอกมอนสเตอร์สำเร็จ! มันสับสนและลดการโจมตี")
                    monster_pressure = max(0, monster_pressure - 12)
                    player['pressure'] -= 6
                else:
                    player_dmg = player['pressure'] // 2
                    print(f"กดดันมอนสเตอร์! สร้าง {player_dmg} dmg")
                    player['pressure'] = max(0, player['pressure'] - 10)
            else:
                print("ความกดดันไม่พอ! (ต้องการอย่างน้อย 8)")
                continue
        elif choice == "3":
            print("คุณตั้งรับ... ความเสียหายจากมอนสเตอร์จะลดลงครึ่งหนึ่ง")
            defended = True
            player['action_counts']['defend'] += 1
        elif choice == "4":
            print("สกิลที่คุณมี:", ", ".join(player['skills']))
            sk_name = input("พิมพ์ชื่อสกิลที่ใช้ (หรือเว้นว่างเพื่อยกเลิก): ").strip()
            found = False
            for sk_key in player['skills']:
                if sk_key in SKILL_LIST and SKILL_LIST[sk_key]['name'] == sk_name:
                    sk = SKILL_LIST[sk_key]
                    if sk.get("dmg"):
                        player_dmg = sk["dmg"] + player['bonus_atk'] // 2
                    elif sk.get("heal"):
                        heal_amt = sk["heal"]
                        player['hp'] = min(player['max_hp'], player['hp'] + heal_amt)
                        print(f"ใช้ {sk_name} ฟื้นฟู {heal_amt} HP!")
                    player['action_counts']['attack'] += 1
                    found = True
                    break
            if not found:
                print("ใช้สกิลพื้นฐานแทน")
                player_dmg = 10 + player['bonus_atk']
                player['action_counts']['attack'] += 1
        elif choice == "5":
            flee_chance = 35 + (player['pressure'] // 2) + player['deceive_bonus']
            if random.randint(1, 100) < flee_chance:
                print("คุณหนีสำเร็จ!")
                return
            else:
                print("หนีไม่สำเร็จ! มอนสเตอร์โจมตีคุณ")
                player['hp'] -= random.randint(8, 15)
                continue
        else:
            print("เลือกไม่ถูกต้อง ใช้โจมตีปกติแทน")
            player_dmg = 8 + player['bonus_atk']

        # Apply area mastery & blessing
        if player_dmg > 0:
            player_dmg = get_effective_dmg(player_dmg, player, current_area)
            monster_hp -= player_dmg
            print(f"→ ความเสียหายสุทธิ (ปรับตามชำนาญพื้นที่): {player_dmg}")

        if monster_hp <= 0:
            break

        # Monster turn
        mon_dmg = random.randint(6, 16)
        if defended:
            mon_dmg = mon_dmg // 2
            print("ป้องกันสำเร็จ! ความเสียหายลดลง")
        if monster_pressure > 15:
            mon_dmg += 4  # monster uses its pressure
        player['hp'] -= mon_dmg
        print(f"มอนสเตอร์โจมตีคุณ {mon_dmg} ความเสียหาย")

        if player['hp'] < player['max_hp'] * 0.35:
            player['action_counts']['low_hp'] += 1

    if player['hp'] > 0:
        print("\n🎉 ชนะการต่อสู้!")
        exp_gain = random.randint(12, 28)
        player['exp'] += exp_gain
        if player['exp'] >= 100:
            player['level'] += 1
            player['exp'] = 0
            player['max_hp'] += 8
            player['hp'] += 8
            player['bonus_atk'] += 1
            print(f"LEVEL UP! ตอนนี้ Lv.{player['level']}")

        # Loot money (random type - ไม่รู้ที่มา)
        money_type = random.choice(["world", "heaven", "hell"])
        amount = random.randint(15, 55)
        if money_type == "world":
            player['money_world'] += amount
        elif money_type == "heaven":
            player['money_heaven'] += max(1, amount // 6)
        else:
            player['money_hell'] += max(1, amount // 4)
        print(f"ได้รับเงิน {money_type} {amount} (จากแหล่งลึกลับ)")

        # Item / Card loot
        if random.random() > 0.55:
            loot = random.choice(["ดาบเหล็ก", "เกราะหนัง", "การ์ดไฟ", "การ์ดน้ำแข็ง", "วัสดุอัพเกรด", "ยา HP"])
            player['inventory'].append(loot)
            print(f"พบ {loot} ในซากมอนสเตอร์!")

        # Mastery & pressure
        gain = 4 + player['mastery_gain_bonus']
        player['area_mastery'][current_area] = min(100, player['area_mastery'][current_area] + gain)
        player['pressure'] = min(100, player['pressure'] + random.randint(6, 14))

        check_unlock_skills(player, current_area)
    else:
        print("\n💀 คุณแพ้... ถูกส่งกลับไปพักฟื้น")
        player['hp'] = max(10, player['max_hp'] // 2)
        player['pressure'] = max(0, player['pressure'] - 10)

def open_chest(player):
    print("\n📦 เปิดหีบสมบัติ...")
    loot_roll = random.random()
    if loot_roll < 0.35:
        mtype = random.choice(["world", "heaven", "hell"])
        amt = random.randint(25, 80)
        player[f"money_{mtype}"] += amt
        print(f"พบเงิน {mtype} {amt}!")
    elif loot_roll < 0.65:
        item = random.choice(["ดาบเวทย์", "เกราะเหล็ก", "แหวนพลัง", "วัสดุหายาก", "การ์ดสายฟ้า"])
        player['inventory'].append(item)
        print(f"พบ {item}!")
    elif loot_roll < 0.85:
        card = random.choice(["การ์ดไฟ", "การ์ดน้ำแข็ง", "การ์ดสายฟ้า", "การ์ดเงา"])
        player['cards'].append(card)
        print(f"พบ {card}! (สวมใส่เพื่อโบนัสเสริม)")
    else:
        print("พบเบาะแสสกิลลึกลับ... เงื่อนไขสกิลบางอย่างอาจใกล้ครบแล้ว!")
        player['action_counts']['explore'] += 4

def check_unlock_skills(player, current_area):
    # Fire ball - จากการโจมตีบ่อย
    if (player['action_counts']['attack'] >= 9 and "fire_ball" not in player['skills'] and
            random.random() < 0.32 * (1 - POPULAR_SKILLS.get("fire_ball", 30)/100)):
        player['skills'].append("fire_ball")
        print("🔥 ได้รับสกิลใหม่: ลูกไฟ (Fire Ball) - เงื่อนไข: โจมตีต่อเนื่องหลายครั้ง")

    # Counter strike - จากการป้องกัน
    if (player['action_counts']['defend'] >= 6 and "counter_strike" not in player['skills'] and
            random.random() < 0.38):
        player['skills'].append("counter_strike")
        print("⚔️ ได้รับสกิล: การโต้กลับ (Counter Strike) - คอมโบป้องกัน + โจมตี")

    # Last stand - จากการรอด HP ต่ำ
    if (player['action_counts'].get('low_hp', 0) >= 3 and "last_stand" not in player['skills'] and
            random.random() < 0.45):
        player['skills'].append("last_stand")
        print("💪 ได้รับสกิล: ยืนหยัดสุดท้าย (Last Stand) - โบนัสเมื่อใกล้ตาย")

    # Area specific skill
    if current_area == "ป่ามืด" and player['action_counts']['explore'] >= 8 and "nature_heal" not in player['skills']:
        if random.random() < 0.35:
            player['skills'].append("nature_heal")
            print("🌿 ได้รับสกิลพื้นที่: รักษาธรรมชาติ (Nature Heal) - เก่งเฉพาะป่า")

    if current_area == "ถ้ำเงา" and player['pressure'] >= 35 and "shadow_step" not in player['skills']:
        if random.random() < 0.4:
            player['skills'].append("shadow_step")
            print("🌑 ได้รับสกิล: ก้าวเงา (Shadow Step) - เก่งเฉพาะถ้ำเงา")

    # Popular skill limit message (ถ้าพยายามได้สกิลที่นิยม)
    # (ใน prototype แสดงเมื่อพยายามแต่ไม่สำเร็จ)

def encounter_god_master(player):
    print("\n" + "=" * 50)
    print("✨ อาจารย์เทพปรากฏตัวในพื้นที่!")
    masters = [
        {"name": "อาเธอร์ ไฟศักดิ์สิทธิ์", "expertise": "ไฟ", "nickname": "ผู้พิชิตเปลวไฟ"},
        {"name": "ลูน่า เงาจันทรา", "expertise": "เงา", "nickname": "เงาแห่งความลับ"},
        {"name": "โกร ภูผาหิน", "expertise": "ดิน", "nickname": "ปรมาจารย์หินผา"},
        {"name": "เซเลน่า เวทย์โบราณ", "expertise": "เวทย์", "nickname": "ผู้ทรงเวทย์โบราณ"}
    ]
    master = random.choice(masters)
    print(f"ชื่อ: {master['name']}")
    print(f"ฉายา: {master['nickname']} | ความเชี่ยวชาญ: {master['expertise']}")
    print("ข้อมูลอาจารย์: เก่งเฉพาะพื้นที่ตนเอง ชำนาญสูง สามารถสอนสกิลได้จำกัด")
    print("\nคุณจะทำอย่างไร?")
    print("1. เข้าหาแบบนอบน้อม (เสี่ยงถูกปฏิเสธ)")
    print("2. ให้ของขวัญ (เสียเงินโลก 60)")
    print("3. แสดงความแข็งแกร่ง / ท้าทาย (เสี่ยงถูกไล่ล่า)")
    print("4. ขอเรียนสกิลตรงๆ (อาจได้อย่างเสียอย่าง)")
    print("5. ถอยหนี (ปลอดภัย)")

    ch = input("เลือก: ").strip()
    success = False
    trade_off = ""

    if ch == "1":
        if random.random() > 0.55:
            success = True
        else:
            print("อาจารย์ไม่ประทับใจในตัวคุณ...")
    elif ch == "2":
        if player['money_world'] >= 60:
            player['money_world'] -= 60
            if random.random() > 0.25:
                success = True
            else:
                print("รับของขวัญแต่ปฏิเสธคุณ...")
        else:
            print("เงินโลกไม่พอ!")
    elif ch == "3":
        print("คุณแสดงพลังและความกดดัน!")
        if player['pressure'] > 25 or random.random() > 0.45:
            success = True
            print("อาจารย์ยอมรับความกล้าของคุณ!")
        else:
            print("อาจารย์โกรธ! คุณถูกไล่ล่าและได้รับบาดเจ็บ")
            player['hp'] -= random.randint(15, 30)
            player['pressure'] += 8
            trade_off = "ถูกไล่ล่า"
    elif ch == "4":
        print("คุณขอเรียนสกิล...")
        if random.random() > 0.35:
            success = True
            trade_off = "ได้อย่างเสียอย่าง"
            if player['inventory']:
                lost = player['inventory'].pop(0)
                print(f"คุณยอมเสีย {lost} เพื่อแลกกับการสอน")
            else:
                player['money_world'] = max(0, player['money_world'] - 30)
                print("คุณยอมเสียเงินบางส่วน...")
        else:
            print("อาจารย์ปฏิเสธคำขอของคุณ")
    else:
        print("คุณถอยหนีจากอาจารย์เทพ...")
        return

    if success:
        print("\n🎉 สำเร็จ! อาจารย์ยอมรับคุณเป็นศิษย์ชั่วคราว (จำนวนศิษย์จำกัด)")
        player['disciple_of'] = master['name']
        new_skill_key = f"{master['expertise'].lower()}_mastery"
        if new_skill_key not in player['skills']:
            # Create a temp blessing skill
            skill_name = f"พร{ master['expertise'] }จากอาจารย์"
            player['skills'].append(new_skill_key)
            player['blessings'].append(skill_name)
            player['blessing_turns'] = 12 + ZODIAC_BONUSES.get(player['zodiac'], {}).get('blessing_duration', 0)
            print(f"ได้รับสกิล/พรพิเศษ: {skill_name} (จำกัดเวลา ~{player['blessing_turns']} เทิร์น)")
            print("สกิลนี้จะลดลงเมื่อไปพื้นที่อื่น (ตามความชำนาญ)")
    else:
        print(f"\nโอกาสนี้พลาด... {trade_off}")

def pvp_contest(player, current_area):
    print("\n" + "=" * 50)
    print("⚔️ โหมดแย่งชิงพื้นที่! (ผู้เล่นทุกคนเลเวลเท่ากัน สถานะปรับสมดุล)")
    print(f"มี {player['other_players']} ผู้เล่นอื่นในพื้นที่")
    player_power = (player['level'] * 12) + player['bonus_atk'] + (player['pressure'] // 2) + random.randint(5, 25)
    ai_power = 65 + random.randint(10, 45)
    print(f"พลังคุณ (ปรับสมดุล): {player_power}")
    print(f"พลังคู่แข่งโดยประมาณ: {ai_power}")
    time.sleep(1)

    if player_power > ai_power:
        print("\n🏆 คุณชนะการแย่งชิงพื้นที่!")
        reward = random.randint(80, 150)
        player['money_world'] += reward
        player['area_mastery'][current_area] = min(100, player['area_mastery'][current_area] + 18)
        print(f"ได้รับรางวัล: เงินโลก {reward} + ชำนาญพื้นที่ +18%")
        if random.random() > 0.6:
            player['blessings'].append("พรแห่งผู้พิชิต")
            player['blessing_turns'] = 6
            print("ได้รับพรแห่งผู้พิชิต (จำกัดเวลา)")
    else:
        print("\n😞 คุณแพ้การแย่งชิง...")
        loss = random.randint(20, 45)
        player['hp'] = max(5, player['hp'] - loss)
        player['pressure'] = max(0, player['pressure'] - 8)
        print(f"เสีย HP {loss} และความกดดันลดลง")
    print("=" * 50)

def manage_inventory(player):
    print("\n=== 🎒 คลังไอเทม & การจัดการ ===")
    print("ไอเทม:", player['inventory'] if player['inventory'] else "ว่างเปล่า")
    print("การ์ด:", player['cards'] if player['cards'] else "ไม่มี")
    print("\n1. สวมใส่อุปกรณ์ (weapon/armor)")
    print("2. สวมใส่การ์ด (เพิ่มโบนัสเสริม)")
    print("3. อัพเกรดอุปกรณ์ (ต้องมีวัสดุอัพเกรด)")
    print("0. กลับเมนูหลัก")
    ch = input("เลือก: ").strip()

    if ch == "1":
        if not player['inventory']:
            print("ไม่มีไอเทมให้สวมใส่")
            return
        for i, it in enumerate(player['inventory'], 1):
            print(f"  {i}. {it}")
        try:
            idx = int(input("เลือกหมายเลข: ")) - 1
            item = player['inventory'].pop(idx)
            if any(x in item for x in ["ดาบ", "weapon", "เวทย์"]):
                if player['equip']['weapon']:
                    player['inventory'].append(player['equip']['weapon'])
                player['equip']['weapon'] = item
                player['bonus_atk'] += 6
            elif any(x in item for x in ["เกราะ", "armor", "หนัง", "เหล็ก"]):
                if player['equip']['armor']:
                    player['inventory'].append(player['equip']['armor'])
                player['equip']['armor'] = item
                player['max_hp'] += 12
                player['hp'] += 8
            print(f"สวมใส่ {item} สำเร็จ! โบนัสสถานะอัพเดท")
        except:
            print("ยกเลิก")
    elif ch == "2":
        if not player['cards']:
            print("ไม่มีการ์ด")
            return
        card = player['cards'].pop(0)
        player['bonus_atk'] += 4
        print(f"สวมใส่ {card} +4 ATK โบนัสเสริมจากอุปกรณ์/การ์ด")
    elif ch == "3":
        has_material = any("วัสดุ" in x for x in player['inventory'])
        if has_material:
            for mat in ["วัสดุอัพเกรด", "วัสดุหายาก"]:
                if mat in player['inventory']:
                    player['inventory'].remove(mat)
                    break
            player['bonus_atk'] += 5
            player['max_hp'] += 5
            print("อัพเกรดอุปกรณ์สำเร็จ! +5 ATK +5 Max HP (ใช้เงิน/วัสดุลึกลับ)")
        else:
            print("ต้องการวัสดุอัพเกรด (หาได้จากมอนสเตอร์หรือหีบ)")

def main_game():
    print("\n" + "=" * 60)
    print("🌍 Pixel Fantasy: Open Skill World")
    print("   โลกเปิดกว้าง | สกิลอิสระ | คอมโบเอง | อาจารย์เทพ | แย่งพื้นที่")
    print("   สกิลถูกสร้างเมื่อเงื่อนไขครบ (บางอย่างคุณอาจไม่รู้) | พื้นที่เฉพาะ")
    print("   Multiplay: แจ้งเตือนผู้เล่นอื่น | ท้าประลองแย่งชิงทุก 3 นาที (sim)")
    print("=" * 60)

    player = create_character()
    current_area = random.choice(AREAS)
    print(f"\nคุณเริ่มต้นการผจญภัยที่: {current_area}")

    while True:
        check_area_event(player, current_area)
        show_status(player, current_area)

        print("\n=== การกระทำหลัก ===")
        print("1. พักผ่อน (ฟื้นฟู HP/Mana ลดกดดัน)")
        print("2. สำรวจพื้นที่ (เจอมอนสเตอร์ / หีบ / อาจารย์ / เหตุการณ์)")
        print("3. เดินทางไปพื้นที่อื่น")
        print("4. จัดการไอเทม / สวมใส่ / อัพเกรดอุปกรณ์")
        print("5. ตรวจสอบข่าวสารระบบ / หาอาจารย์เทพ")
        if player['other_players'] > 0:
            print("6. ⚔️ ท้าประลองแย่งชิงพื้นที่ (PvP - ผู้ชนะได้รางวัล)")
        print("7. ออกจากเกม (บันทึกความคืบหน้าในใจ)")

        choice = input("\nเลือกหมายเลข: ").strip()

        if choice == "1":
            rest(player)
        elif choice == "2":
            explore_event = random.random()
            if explore_event < 0.45:
                print("\nคุณสำรวจและเจอมอนสเตอร์!")
                combat(player, current_area)
            elif explore_event < 0.65:
                print("\nคุณพบหีบสมบัติเก่า!")
                open_chest(player)
            elif explore_event < 0.78:
                print("\nคุณพบร่องรอยอาจารย์เทพ...")
                if random.random() > 0.4:
                    encounter_god_master(player)
                else:
                    print("แต่หาไม่เจอ... ลองสำรวจต่อ")
            else:
                print("\nสำรวจพื้นที่... ได้รับประสบการณ์และชำนาญ +1-3%")
                player['area_mastery'][current_area] = min(100, player['area_mastery'][current_area] + random.randint(1, 3))
                player['action_counts']['explore'] += 2
                check_unlock_skills(player, current_area)
        elif choice == "3":
            print("\nพื้นที่ที่สามารถไปได้:")
            for i, area in enumerate(AREAS, 1):
                print(f"  {i}. {area} (ชำนาญ {player['area_mastery'][area]}%)")
            try:
                idx = int(input("เลือกพื้นที่ (1-5): ")) - 1
                current_area = AREAS[max(0, min(4, idx))]
                print(f"เดินทางไป {current_area}...")
                player['time_units'] += 3
                if random.random() < 0.35:
                    print("ระหว่างทางถูกมอนสเตอร์ซุ่มโจมตี!")
                    combat(player, current_area)
            except:
                print("ยกเลิกการเดินทาง")
        elif choice == "4":
            manage_inventory(player)
        elif choice == "5":
            print("\n📡 ตรวจสอบข่าวสารจากระบบ...")
            if random.random() > 0.65 or player['disciple_of'] is None:
                encounter_god_master(player)
            else:
                print("ไม่มีอาจารย์เทพใหม่... ลองสำรวจพื้นที่เพื่อโอกาส")
                if random.random() > 0.75:
                    encounter_god_master(player)
        elif choice == "6" and player['other_players'] > 0:
            pvp_contest(player, current_area)
        elif choice == "7":
            print("\nขอบคุณที่เล่น Pixel Fantasy: Open Skill World!")
            print("ตัวละครของคุณถูกบันทึกในความทรงจำของเกม (prototype)")
            print("สกิลที่คุณปลดล็อคและความชำนาญพื้นที่จะคงอยู่เมื่อเล่นต่อ")
            break
        else:
            print("เลือกไม่ถูกต้อง ลองใหม่")

        # Passive blessing countdown
        if player['blessing_turns'] > 0:
            player['blessing_turns'] -= 1
            if player['blessing_turns'] <= 0 and player['blessings']:
                print("⚠️ พรเทพหมดอายุแล้ว")
                player['blessings'] = []

        if player['hp'] <= 0:
            print("\n💀 คุณตาย... เกมจบ (prototype - คุณสามารถเริ่มใหม่ได้)")
            break

if __name__ == "__main__":
    main_game()
