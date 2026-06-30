import asyncio
import logging
import os
import random
import re
from collections import deque

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatType
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.3-70b-versatile"

BOT_USERNAME = ""  # заполнится автоматически при старте

SYSTEM_PROMPT = """ты жиросик - дерзкий токсичный участник чата, не бот и не помощник
пиши с маленькой буквы, коротко, 1 фраза, можно сленг и подколы
не пиши код и инструкции, не давай советов как ассистент, не извиняйся
не упоминай что ты ии"""

RECENT_LIMIT = 10
RANDOM_REPLY_CHANCE = 0.10

logging.basicConfig(level=logging.INFO)

groq_client = Groq(api_key=GROQ_API_KEY)
router = Router()

# chat_id -> {"recent": deque[{"role","content"}], "summary": str}
memory: dict[int, dict] = {}


def get_chat_memory(chat_id: int) -> dict:
    if chat_id not in memory:
        memory[chat_id] = {"recent": deque(maxlen=RECENT_LIMIT), "summary": ""}
    return memory[chat_id]


def compress_old_messages(old_messages: list[dict], current_summary: str) -> str:
    text_block = "\n".join(f"{m['role']}: {m['content']}" for m in old_messages)
    prompt = (
        "ниже отрывок переписки в чате. выдели только конкретные факты "
        "(имена, события, договорённости) если они есть, в 1-2 коротких предложениях. "
        "если ничего важного нет - ответь пустой строкой. "
        "не пересказывай шутки и не повторяй стиль речи участников:\n\n"
        f"предыдущая сводка: {current_summary}\n\nновые сообщения:\n{text_block}"
    )
    try:
        resp = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
        )
        result = resp.choices[0].message.content.strip()
        return result if len(result) > 5 else current_summary
    except Exception:
        return current_summary


def add_to_memory(chat_id: int, role: str, content: str):
    mem = get_chat_memory(chat_id)
    if len(mem["recent"]) == RECENT_LIMIT:
        oldest = [mem["recent"].popleft() for _ in range(min(3, len(mem["recent"])))]
        mem["summary"] = compress_old_messages(oldest, mem["summary"])
    mem["recent"].append({"role": role, "content": content})


def build_messages(chat_id: int, user_text: str) -> list[dict]:
    mem = get_chat_memory(chat_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if mem["summary"]:
        messages.append({
            "role": "system",
            "content": f"контекст прошлой переписки (кратко): {mem['summary']}"
        })
    messages.extend(mem["recent"])
    messages.append({"role": "user", "content": user_text})
    return messages


def should_respond(message: Message) -> bool:
    if message.chat.type == ChatType.PRIVATE:
        return False

    text = message.text or message.caption or ""

    if BOT_USERNAME and f"@{BOT_USERNAME.lower()}" in text.lower():
        return True

    if re.search(r"жиросик", text, re.IGNORECASE):
        return True

    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.is_bot and \
           message.reply_to_message.from_user.username == BOT_USERNAME:
            return True

    return False


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def start_private(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="добавить в группу",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
        )
    ]])
    await message.answer(
        "пр. я жиросик - умный бот помощник для группы на базе llama-3.3. "
        "добавь меня в группу по кнопке ниже и дай права админа",
        reply_markup=kb
    )


@router.message(F.chat.type == ChatType.PRIVATE)
async def handle_private(message: Message):
    if not message.text:
        return

    chat_id = message.chat.id
    user_name = message.from_user.first_name or "юзер"
    user_text = f"{user_name}: {message.text}"

    answer = await generate_reply(chat_id, user_text)

    add_to_memory(chat_id, "user", user_text)
    add_to_memory(chat_id, "assistant", answer)

    await message.answer(answer)


async def generate_reply(chat_id: int, user_text: str) -> str:
    messages = build_messages(chat_id, user_text)
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=80,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"groq error: {e}")
        return "чето сломалось не до тебя сейчас"


async def generate_spontaneous(chat_id: int) -> str:
    mem = get_chat_memory(chat_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if mem["summary"]:
        messages.append({
            "role": "system",
            "content": f"контекст прошлой переписки (кратко): {mem['summary']}"
        })
    messages.extend(mem["recent"])
    messages.append({
        "role": "user",
        "content": "напиши свою реплику в чат сам, без повода. может быть в тему переписки, "
                    "может рандомная мысль, может прикол. одна короткая фраза."
    })
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.9,
            max_tokens=60,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"groq error: {e}")
        return ""


@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group(message: Message):
    if not message.text:
        return

    chat_id = message.chat.id
    user_name = message.from_user.first_name or "юзер"
    user_text = f"{user_name}: {message.text}"

    if should_respond(message):
        answer = await generate_reply(chat_id, user_text)
        add_to_memory(chat_id, "user", user_text)
        add_to_memory(chat_id, "assistant", answer)
        await message.reply(answer)
        return

    add_to_memory(chat_id, "user", user_text)

    if random.random() < RANDOM_REPLY_CHANCE:
        answer = await generate_spontaneous(chat_id)
        if not answer:
            return
        add_to_memory(chat_id, "assistant", answer)

        if random.random() < 0.5:
            await message.reply(answer)
        else:
            await message.answer(answer)


async def main():
    global BOT_USERNAME

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    BOT_USERNAME = me.username
    logging.info(f"запущен как @{BOT_USERNAME}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
