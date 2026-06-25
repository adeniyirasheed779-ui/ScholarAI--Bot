import os
import csv
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== CONFIG - CHANGE THESE ==========
TOKEN = os.getenv("BOT_TOKEN") # Get from @BotFather
ADMIN_ID = 6975323735 # Your Telegram ID from @userinfobot

QUESTION_FILE = "questions.csv"
DB_FILE = "users.db"
FREE_LIMIT = 10
PREMIUM_LIMIT = 40
BANK_ACC = "5266508825"
BANK_NAME = "Moniepoint MFB"
BANK_OWNER = "RASHEED ADENIYI"

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_premium INTEGER DEFAULT 0,
            tests_done INTEGER DEFAULT 0,
            total_correct INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def ensure_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES(?)', (user_id,))
    conn.commit()
    conn.close()

def check_premium(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_premium FROM users WHERE user_id =?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return True if row and row[0] == 1 else False

def upgrade_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (user_id, is_premium) VALUES(?, 1) ON CONFLICT(user_id) DO UPDATE SET is_premium = 1', (user_id,))
    conn.commit()
    conn.close()

def update_stats(user_id, correct, total):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET tests_done = tests_done + 1, total_correct = total_correct +?, total_questions = total_questions +? WHERE user_id =?', (correct, total, user_id))
    conn.commit()
    conn.close()

def get_profile(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT tests_done, total_correct, total_questions FROM users WHERE user_id =?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# ========== LOAD QUESTIONS ==========
def load_questions():
    question_bank = {}
    if not os.path.exists(QUESTION_FILE):
        with open(QUESTION_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['subject','question','option_a','option_b','option_c','option_d','answer','explanation'])
            writer.writerow(['English','Select nearest meaning to Diligent','Lazy','Hardworking','Careless','Idle','Hardworking','Diligent means showing careful persistent work.'])
            writer.writerow(['Maths','What is 2+2?','3','4','5','6','4','Basic addition'])
            writer.writerow(['Biology','Which organ purifies blood?','Heart','Kidney','Liver','Lungs','Kidney','Kidney filters waste from blood'])

    with open(QUESTION_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sub = row.get('subject', 'General').strip()
            if not row.get('question'): continue
            if sub not in question_bank: question_bank[sub] = []
            question_bank[sub].append(row)
    return question_bank

QUESTION_BANK = load_questions()
user_sessions = {}

# ========== /START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    is_premium = check_premium(user_id)

    tier_tag = "👑 PREMIUM" if is_premium else "🆓 FREE"
    text = f"🚀 *ScholarAI JAMB/UTME Bot* [{tier_tag}]\n\n"
    text += f"Free: {FREE_LIMIT} questions per subject\nPremium: {PREMIUM_LIMIT} questions\n"
    text += "📚 Tap subject for CBT test\n📊 /profile for stats"

    keyboard = []
    for subject in QUESTION_BANK.keys():
        keyboard.append([InlineKeyboardButton(f"📚 {subject}", callback_data=f"subject_{subject}")])
    if not is_premium:
        keyboard.append([InlineKeyboardButton("🔑 Upgrade Premium ₦500", callback_data="upgrade")])
    keyboard.append([InlineKeyboardButton("📊 My Profile", callback_data="profile")])

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ========== /PROFILE ==========
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = get_profile(user_id)

    if not row or row[2] == 0:
        text = "📊 *No tests yet*\nStart practicing with /start"
    else:
        acc = round(row[1]/row[2]*100, 1) if row[2] > 0 else 0
        text = f"📊 *Your ScholarAI Stats*\n\nTests done: {row[0]}\nQuestions: {row[2]}\nCorrect: {row[1]}\nAccuracy: {acc}%\n\nKeep grinding! 💪"

    if update.message:
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')

# ========== CBT LOGIC ==========
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    subject = query.data.replace("subject_", "")
    user_id = update.effective_user.id
    is_premium = check_premium(user_id)

    qs = QUESTION_BANK.get(subject, [])
    if not qs:
        await query.answer("No questions for this subject yet!", show_alert=True)
        return

    limit = PREMIUM_LIMIT if is_premium else FREE_LIMIT
    limit = min(len(qs), limit)
    selected = random.sample(qs, limit)

    user_sessions[user_id] = {'subject': subject, 'questions': selected, 'limit': limit, 'current': 0, 'score': 0}
    await show_question(update, context)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    test = user_sessions[user_id]
    q = test['questions'][test['current']]

    options = [('A', q.get('option_a','')), ('B', q.get('option_b','')), ('C', q.get('option_c','')), ('D', q.get('option_d',''))]
    random.shuffle(options)

    try:
        correct = next(l for l, t in options if t.strip() == q.get('answer','').strip())
    except:
        correct = 'A'

    test['correct'] = correct
    test['exp'] = q.get('explanation', 'No explanation provided')

    text = f"*Q{test['current']+1}/{test['limit']} - {test['subject']}*\n\n{q.get('question')}\n\n"
    keyboard = [[InlineKeyboardButton(f"{l}. {t[:50]}", callback_data=f"ans_{l}")] for l, t in options]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if user_id not in user_sessions: return

    test = user_sessions[user_id]
    chosen = query.data.replace("ans_", "")

    if chosen == test['correct']:
        test['score'] += 1
        fb = "✅ Correct!"
    else:
        fb = f"❌ Wrong! Answer: {test['correct']}"

    await query.edit_message_text(f"{fb}\n\n💡 {test['exp']}", parse_mode='Markdown')
    test['current'] += 1
    await asyncio.sleep(2)

    if test['current'] < test['limit']:
        await show_question(update, context)
    else:
        update_stats(user_id, test['score'], test['limit'])
        perc = round(test['score']/test['limit']*100, 1)
        text = f"🎉 *Test Complete!*\n\nSubject: {test['subject']}\nScore: {test['score']}/{test['limit']} = {perc}%\n\n"
        if perc >= 70: text += "🔥 JAMB Ready!"
        elif perc >= 50: text += "💪 Good! Keep practicing"
        else: text += "📚 Study explanations and retry"

        if not check_premium(user_id):
            text += "\n\n🔑 Upgrade to Premium for 40 questions!"

        keyboard = [
            [InlineKeyboardButton("🔄 Retake", callback_data=f"subject_{test['subject']}")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")],
            [InlineKeyboardButton("📊 Profile", callback_data="profile")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        del user_sessions[user_id]

# ========== BUTTON ROUTER ==========
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith("subject_"):
        await start_test(update, context)
    elif data == "home":
        await start(update, context)
    elif data == "profile":
        await profile(update, context)
    elif data == "upgrade":
        text = f"🏦 *Premium Activation - ₦500*\n\nAccount: `{BANK_ACC}`\nBank: {BANK_NAME}\nName: {BANK_OWNER}\n\n1. Transfer ₦500\n2. Send receipt photo to admin\n3. Admin go approve you manually"
        await query.edit_message_text(text, parse_mode='Markdown')
    elif data.startswith("ans_"):
        await handle_answer(update, context)
    elif data.startswith("approve_") and user_id == ADMIN_ID:
        target = int(data.replace("approve_", ""))
        upgrade_user(target)
        await query.edit_message_text("✅ Approved!")
        await context.bot.send_message(target, "🎉 Premium activated! Send /start to begin 40 questions")

# ========== MAIN ==========
def main():
    init_db()
    if not TOKEN:
        print("CRITICAL: Set BOT_TOKEN environment variable")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CallbackQueryHandler(buttons))

    print("ScholarAI CBT Bot is LIVE! No OpenAI needed")
    app.run_polling()

if __name__ == '__main__':
    import asyncio
    main()
