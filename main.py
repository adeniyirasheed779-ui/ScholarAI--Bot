import os
import json
import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 6975323735  # Your Telegram ID
DB_FILE = "users.json"

ACCOUNT_DETAILS = """🏦 <b>Account Number:</b> 5266508825
🏦 <b>Bank:</b> Moniepoint MFB
🏦 <b>Account Name:</b> RASHEED ADENIYI

<b>Amount:</b> ₦500 one-time for JAMB 2027/2028

After transfer, send payment screenshot here as a photo.
Need help? DM me on Telegram for support @Hardee01
"""

QUESTIONS_DB = {
    "English": [
        {"q": "Choose the correct spelling: 2027/2028 JAMB SAMPLE", "a": "Accommodate", "opts": ["Accomodate", "Accommodate", "Acommodate", "Accomodatte"]},
        {"q": "Select the synonym of 'Huge'", "a": "Massive", "opts": ["Small", "Tiny", "Massive", "Short"]},
        {"q": "The boy ___ to school every day", "a": "goes", "opts": ["go", "goes", "going", "went"]},
    ] + [{"q": f"English SAMPLE Q{i+4} 2027/2028", "a": "Option C", "opts": ["Option A", "Option B", "Option C", "Option D"]} for i in range(37)],

    "Mathematics": [
        {"q": "If x + 5 = 12, x = ?", "a": "7", "opts": ["5", "6", "7", "17"]},
        {"q": "Solve: 2x + 3 = 11", "a": "4", "opts": ["3", "4", "5", "8"]},
        {"q": "Area of rectangle 5cm x 3cm?", "a": "15cm²", "opts": ["8cm²", "15cm²", "10cm²", "20cm²"]},
    ] + [{"q": f"Maths SAMPLE Q{i+4} 2027/2028", "a": "10", "opts": ["5", "8", "10", "12"]} for i in range(37)],

    "Biology": [
        {"q": "The powerhouse of the cell is?", "a": "Mitochondria", "opts": ["Nucleus", "Ribosome", "Mitochondria", "Chloroplast"]},
        {"q": "Which is NOT a mammal?", "a": "Shark", "opts": ["Whale", "Bat", "Shark", "Dolphin"]},
        {"q": "Photosynthesis occurs in?", "a": "Chloroplast", "opts": ["Root", "Stem", "Chloroplast", "Flower"]},
    ] + [{"q": f"Biology SAMPLE Q{i+4} 2027/2028", "a": "Blood", "opts": ["Bone", "Muscle", "Blood", "Skin"]} for i in range(37)],

    "Chemistry": [
        {"q": "Chemical symbol for Sodium?", "a": "Na", "opts": ["S", "So", "Na", "Sd"]},
        {"q": "pH of pure water?", "a": "7", "opts": ["0", "7", "14", "10"]},
        {"q": "H2O is formula for?", "a": "Water", "opts": ["Salt", "Water", "Oxygen", "Hydrogen"]},
    ] + [{"q": f"Chemistry SAMPLE Q{i+4} 2027/2028", "a": "Acid", "opts": ["Base", "Salt", "Acid", "Metal"]} for i in range(37)],
}

def load_data():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
    except Exception as e:
        print(f"Database read error: {e}")
    return {}

def save_data(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Database write error: {e}")

USER_DATA = load_data()

def is_premium(user_id):
    return str(user_id) in USER_DATA and USER_DATA[str(user_id)].get("premium", False)

def get_questions(subject, user_id):
    questions = QUESTIONS_DB.get(subject, [])
    return questions[:40] if is_premium(user_id) else questions[:20]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uid = str(user_id)
    
    # Initialize profile state if missing entirely
    if uid not in USER_DATA:
        USER_DATA[uid] = {"premium": False}
    else:
        # Clear out current testing metrics safely on refresh
        for key in ["subject", "q_index", "score"]:
            USER_DATA[uid].pop(key, None)
    save_data(USER_DATA)

    keyboard = [
        [InlineKeyboardButton("📚 English", callback_data="subj_English")],
        [InlineKeyboardButton("➗ Mathematics", callback_data="subj_Mathematics")],
        [InlineKeyboardButton("🧬 Biology", callback_data="subj_Biology")],
        [InlineKeyboardButton("⚗️ Chemistry", callback_data="subj_Chemistry")],
        [InlineKeyboardButton("💎 Upgrade to Premium ₦500", callback_data="upgrade")]
    ]
    status = "<b>PREMIUM ✅</b>" if is_premium(user_id) else "<b>FREE - 20 Qs only</b>"
    text = f"""Welcome to JAMB 2027/2028 CBT Prep Bot! 🚀

Status: {status}
Choose a subject to start practice.

Free users get first 20 questions.
Premium ₦500 unlocks all 40 questions per subject.

Need help? DM me on Telegram for support @Hardee01"""
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    uid = str(user_id)

    if data == "upgrade":
        await query.message.reply_text(ACCOUNT_DETAILS, parse_mode="HTML")
        USER_DATA[uid] = USER_DATA.get(uid, {"premium": False})
        USER_DATA[uid]["awaiting_payment"] = True
        save_data(USER_DATA)
        return

    if data.startswith("subj_"):
        subject = data.split("_", 1)[1]
        questions = get_questions(subject, user_id)
        if not questions:
            await query.message.reply_text("No questions for this subject yet.")
            return

        USER_DATA[uid] = USER_DATA.get(uid, {"premium": False})
        USER_DATA[uid]["subject"] = subject
        USER_DATA[uid]["q_index"] = 0
        USER_DATA[uid]["score"] = 0
        save_data(USER_DATA)
        
        await send_question(query, user_id, questions[0], feedback="")

async def send_question(query, user_id, q_data, feedback=""):
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"ans_{i}")] for i, opt in enumerate(q_data["opts"])]
    uid = str(user_id)
    
    prefix = f"{feedback}\n\n" if feedback else ""
    safe_q = html.escape(q_data["q"])
    text = f"{prefix}📝 <b>Question {USER_DATA[uid]['q_index'] + 1}</b>:\n\n{safe_q}"
    
    try:
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception:
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    uid = str(user_id)

    if uid not in USER_DATA or "subject" not in USER_DATA[uid]:
        return

    choice_idx = int(query.data.split("_", 1)[1])
    subject = USER_DATA[uid]["subject"]
    q_index = USER_DATA[uid]["q_index"]
    questions = get_questions(subject, user_id)
    
    if q_index >= len(questions):
        return

    q_data = questions[q_index]
    chosen = q_data["opts"][choice_idx]
    correct = q_data["a"]

    if chosen == correct:
        USER_DATA[uid]["score"] += 1
        result = "✅ <b>Correct!</b>"
    else:
        result = f"❌ <b>Wrong!</b> Correct answer: <code>{html.escape(correct)}</code>"

    USER_DATA[uid]["q_index"] += 1
    save_data(USER_DATA)

    if USER_DATA[uid]["q_index"] >= len(questions):
        score = USER_DATA[uid]["score"]
        total = len(questions)
        await query.message.edit_text(
            f"{result}\n\n🏁 <b>Quiz complete!</b>\nFinal Score: <code>{score}/{total}</code>\n\nRun /start to launch a new session.", 
            parse_mode="HTML"
        )
        for key in ["subject", "q_index", "score"]:
            USER_DATA[uid].pop(key, None)
        save_data(USER_DATA)
    else:
        await send_question(query, user_id, questions[USER_DATA[uid]["q_index"]], feedback=result)

async def payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uid = str(user_id)
    
    if uid in USER_DATA and USER_DATA[uid].get("awaiting_payment"):
        await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=update.message.message_id)
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=f"💳 <b>Premium Upgrading Request</b>\nUser System ID: <code>{user_id}</code>\n\nTo grant authorization, copy and send:\n<code>/approve {user_id}</code>", 
            parse_mode="HTML"
        )
        
        await update.message.reply_text("Screenshot forwarded to admin for verification. You will be upgraded once confirmed! ⌛")
        USER_DATA[uid]["awaiting_payment"] = False
        save_data(USER_DATA)

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        target_id = str(context.args[0])
        USER_DATA[target_id] = USER_DATA.get(target_id, {})
        USER_DATA[target_id]["premium"] = True
        save_data(USER_DATA)
        
        try:
            await context.bot.send_message(chat_id=int(target_id), text="🎉 Payment confirmed! You now have PREMIUM access to all 40 questions per subject for JAMB 2027/2028!")
            await update.message.reply_text(f"User {target_id} successfully upgraded to Premium ✅")
        except Exception as e:
            await update.message.reply_text(f"Database adjusted successfully, but direct notification to chat could not deliver: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^subj_|^upgrade"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern="^ans_\\d+$"))
    app.add_handler(MessageHandler(filters.PHOTO, payment_screenshot))
    
    print("Bot running safely for JAMB 2027/2028...")
    app.run_polling()

if __name__ == "__main__":
    main()
