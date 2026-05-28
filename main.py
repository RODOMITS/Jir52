import random
import telebot
from g4f.client import Client

# ВСТАВЬ СВОЙ ТОКЕН ТЕЛЕГРАМ СЮДА
TG_TOKEN = "8676041970:AAEEjcx09T-t4VhSKOWZsTTo5rzFzkdsmjI"
bot = telebot.TeleBot(TG_TOKEN)

# Инициализируем бесплатного ИИ-клиента
ai_client = Client()

# Инструкция, как Жиросик должен себя вести
SYSTEM_PROMPT = (
    "Ты — ленивый, прожорливый, туповатый попугай по имени Жиросик. "
    "Ты сидишь в треш-чате с пацанами. Отвечай очень коротко (от 1 до 5 слов). "
    "Используй сленг, мемы, дерзи, проси пожрать, чавкай. "
    "Пиши ТОЛЬКО с маленькой буквы, забудь про точки и запятые. "
    "Твоя цель — тупо, смешно и токсично подколоть."
)

ZHIR_PHRASES = [
    "*тяжило дышыт*",
    "ыыы жирооосык",
    "*чавкаит*",
    "нада пакушаццы",
    "хрюкккк",
    "слишна сложнааа пойду поем",
    "*урчыт*",
    "жыр жыр жыыыр",
]


# === ФИЛЬТР ВСРАТОГО СТИЛЯ ЖИРОСИКА ===
def zhirosik_style(text):
    if not text:
        return ""

    # Принудительно мелкие буквы, сносим знаки препинания
    text = (
        text.lower()
        .replace(".", "")
        .replace(",", "")
        .replace("!", "")
        .replace("?", "")
    )
    text = (
        text.replace("ться", "ццы")
        .replace("тся", "ццы")
        .replace("ик", "ык")
        .replace("привет", "приветс")
    )

    words = text.split()
    styled_words = []

    for word in words:
        # Рандомно тянем гласные на конце слов
        if len(word) > 3 and word[-1] in ["а", "о", "е", "у", "я"]:
            word = word + word[-1] * random.randint(1, 2)

        # Подмешиваем букву 'i' вместо гласных (шанс 15%)
        letters = list(word)
        for i in range(len(letters)):
            if letters[i] in ["а", "о", "е", "у"] and random.random() < 0.15:
                letters[i] = "i"
        word = "".join(letters)
        styled_words.append(word)

    result = " ".join(styled_words)

    # Хвостик (шанс 30%)
    if random.random() < 0.3:
        result = f"{result} {random.choice(ZHIR_PHRASES)}"

    # Скобочки в конец (шанс 80%)
    if random.random() < 0.8:
        brackets = random.choice([")", "))", ")))", "(((", ")))0)"])
        result = f"{result} {brackets}"

    return result


# === БЕСПЛАТНЫЙ ЗАПРОС К НЕЙРОСЕТИ ===
def ask_free_ai(user_message):
    try:
        # Запрос идет через бесплатные провайдеры DuckDuckGo/Llama
        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",  # Или "llama-3-8b"
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=40,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ИИ споткнулся: {e}")
        return None


# === ЛОГИКА БОТА ===


@bot.message_handler(commands=["start"])
def send_welcome(message):
    if message.chat.type == "private":
        markup = telebot.types.InlineKeyboardMarkup()
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?startgroup=true"
        add_button = telebot.types.InlineKeyboardButton(
            text="дабавляй давай!!1!", url=link
        )
        markup.add(add_button)
        bot.send_message(
            message.chat.id,
            "пр\n\nя жирос, добавь в группу шоб было весела)))",
            reply_markup=markup,
        )


@bot.message_handler(content_types=["text"])
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    if text.startswith("/"):
        return

    # В ЛС Жиросик отвечает всегда
    if message.chat.type == "private":
        ai_response = ask_free_ai(text)
        final_reply = (
            zhirosik_style(ai_response)
            if ai_response
            else zhirosik_style(random.choice(ZHIR_PHRASES))
        )
        bot.reply_to(message, final_reply)
        return

    # В группе — если тегнули/назвали Жиросиком (100% ответ) или случайный шанс 15%
    is_summoned = "жиросик" in text.lower() or "жирный" in text.lower()

    if is_summoned or (random.random() < 0.15):
        ai_response = ask_free_ai(text)

        if ai_response:
            final_reply = zhirosik_style(ai_response)
            bot.reply_to(message, final_reply)
        else:
            # Если бесплатный ИИ на секунду отвалился, выдаем классику
            if is_summoned:
                bot.reply_to(
                    message, zhirosik_style(random.choice(ZHIR_PHRASES))
                )


if __name__ == "__main__":
    print("Жиросик на бесплатной нейронке запущен на Bothost!")
    bot.infinity_polling()
