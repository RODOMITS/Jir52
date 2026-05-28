import os
import random
import sqlite3
import telebot

# ВСТАВЬ СВОЙ ТОКЕН СЮДА
TOKEN = "8676041970:AAEEjcx09T-t4VhSKOWZsTTo5rzFzkdsmjI"
bot = telebot.TeleBot(TOKEN)

DB_NAME = "zhirosik_memory.db"

# Базовые фразы Жиросика (уже отформатированные под новый стиль)
ZHIR_PHRASES = [
    "*тяжило дышыт*",
    "ыыы жирооосык",
    "*чавкаит*",
    "нада пакушаццы",
    "хрюкккк",
    "слишна сложнааа пойду поем",
    "*урчыт*",
    "жыр жыр жыыыр",
    "ъеъ дай пирикусить",
]


# === РАБОТА С БАЗОЙ ДАННЫХ ===
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS markov_chains (
            chat_id TEXT,
            w1 TEXT,
            w2 TEXT,
            UNIQUE(chat_id, w1, w2) ON CONFLICT REPLACE
        )
    """
    )
    conn.commit()
    conn.close()


def learn_sentence(chat_id, text):
    # Очищаем текст от лишнего и переводим в нижний регистр для базы
    words = [w.strip().lower() for w in text.split() if w.strip()]
    if len(words) < 2:
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        cursor.execute(
            "INSERT OR IGNORE INTO markov_chains (chat_id, w1, w2) VALUES (?, ?, ?)",
            (str(chat_id), w1, w2),
        )
    conn.commit()
    conn.close()


def generate_t9_text(chat_id, seed_word=None, max_words=12):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    chat_id_str = str(chat_id)

    if not seed_word:
        cursor.execute(
            "SELECT w1 FROM markov_chains WHERE chat_id = ? ORDER BY RANDOM() LIMIT 1",
            (chat_id_str,),
        )
        res = cursor.fetchone()
        if not res:
            conn.close()
            return None
        seed_word = res[0]

    current_word = seed_word.lower()
    sentence = [current_word]

    for _ in range(max_words - 1):
        cursor.execute(
            "SELECT w2 FROM markov_chains WHERE chat_id = ? AND w1 = ? ORDER BY RANDOM() LIMIT 1",
            (chat_id_str, current_word),
        )
        res = cursor.fetchone()
        if res:
            current_word = res[0]
            sentence.append(current_word)
        else:
            break

    conn.close()
    return " ".join(sentence)


# === ФУНКЦИЯ ДЕГРАДАЦИИ ТЕКСТА (СТИЛЬ ЖИРОСИКА) ===
def zhirosik_style(text):
    if not text:
        return ""

    # 1. Строго маленький шрифт
    text = text.lower()

    # 2. Ломаем грамотность (заменяем окончания, удваиваем буквы)
    text = (
        text.replace("ться", "ццы")
        .replace("тся", "ццы")
        .replace("ешь", "ишь")
        .replace("ик", "ык")
    )

    words = text.split()
    styled_words = []

    for word in words:
        # Тянем гласные на конце слов для тупости
        if len(word) > 3 and word[-1] in ["а", "о", "е", "у", "я"]:
            word = word + word[-1] * random.randint(1, 3)

        # Рандомно заменяем некоторые гласные на английскую 'i' (шанс 35%)
        letters = list(word)
        for i in range(len(letters)):
            if letters[i] in ["а", "о", "е", "у"] and random.random() < 0.35:
                letters[i] = "i"
        word = "".join(letters)

        styled_words.append(word)

    result = " ".join(styled_words)

    # 3. Добавляем жирный хвостик (с шансом 40%)
    if random.random() < 0.4:
        result = f"{result} {random.choice(ZHIR_PHRASES)}"

    # 4. Ставим скобочки в самый конец (шанс 70%)
    if random.random() < 0.7:
        brackets = random.choice([")", "))", ")))", "((", ")))0)"])
        result = f"{result} {brackets}"

    return result


# === ЛОГИКА БОТА ===


@bot.message_handler(commands=["start"])
def send_welcome(message):
    if message.chat.type == "private":
        markup = telebot.types.InlineKeyboardMarkup()
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?startgroup=true"

        add_button = telebot.types.InlineKeyboardButton(
            text="дабавляй давай!! 1!! 1111", url=link
        )
        markup.add(add_button)

        welcome_text = "пр\n\nя жирос, добавь в группу шоб было весела)))"
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


@bot.message_handler(content_types=["text"])
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    if text.startswith("/"):
        return

    # Жиросик учится на оригинальном тексте, чтобы запоминать слова нормальными
    learn_sentence(chat_id, text)

    # Триггеры на имя
    is_summoned = "жиросик" in text.lower() or "жирный" in text.lower()

    # Шанс ответа (20% на любое сообщение или 100% если позвали)
    if is_summoned or random.random() < 0.20:
        user_words = [w.lower() for w in text.split() if len(w) > 2]
        seed = random.choice(user_words) if user_words else None

        # Генерируем фразу по Т9
        raw_reply = generate_t9_text(chat_id, seed_word=seed)

        if raw_reply:
            # Стилизуем её под Жиросика
            final_reply = zhirosik_style(raw_reply)
        else:
            # Если база пустая, коверкаем дефолтную фразу + скобки
            final_reply = zhirosik_style(random.choice(ZHIR_PHRASES))

        bot.reply_to(message, final_reply)


if __name__ == "__main__":
    init_db()
    print("жиросик включился и дико тупит...")
    bot.infinity_polling()
