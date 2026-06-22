import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv('BOT_TOKEN')

# Track user states
user_states = {}
user_quizzes = {}

# Question Database
QUESTIONS_DB = {
    "English": [
        {"q": "Choose synonym: Big", "options": ["A", "B", "C"], "text_opts": ["Small", "Large", "Tiny"], "ans": "B", "exp": "Large has a similar meaning to Big."},
        {"q": "Choose antonym: Hot", "options": ["A", "B", "C"], "text_opts": ["Cold", "Warm", "Spicy"], "ans": "A", "exp": "Cold is the opposite of Hot."}
    ],
    "Chemistry": [
        {"q": "What is the chemical symbol for Water?", "options": ["A", "B", "C"], "text_opts": ["H2O", "CO2", "NaCl"], "ans": "A", "exp": "H2O stands for Hydrogen and Oxygen."}
    ],
    "Maths": [
        {"q": "Solve for x: 2x + 5 = 11", "options": ["A", "B", "C"], "text_opts": ["3", "5", "6"], "ans": "A", "exp": "Subtract 5 from both sides: 2x = 6. Divide by 2: x = 3."}
    ],
    "Physics": [
        {"q": "What is the unit of force?", "options": ["A", "B", "C"], "text_opts": ["Joule", "Watt", "Newton"], "ans": "C", "exp": "The SI unit of force is the Newton (N)."}
    ]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = 'CHOOSING_EXAM'

    keyboard = [
        [InlineKeyboardButton("JAMB", callback_data='exam_JAMB')],
        [InlineKeyboardButton("WAEC", callback_data='exam_WAEC')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📚 Welcome to ScholarAI!\nPractice smart. Pass with confidence.\n\nChoose your exam:",
        reply_markup=reply_markup
    )

async def send_question(query, user_id):
    quiz = user_quizzes[user_id]
    subject = quiz['subject']
    q_index = quiz['current_q']
    q_data = QUESTIONS_DB[subject][q_index]

    options_text = ""
    keyboard_row = []
    for i, opt in enumerate(q_data['options']):
        options_text += f"{opt}) {q_data['text_opts'][i]}\n"
        keyboard_row.append(InlineKeyboardButton(opt, callback_data=f"ans_{opt}"))

    keyboard = [keyboard_row]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg_text = f"📝 Question {q_index + 1}/{len(QUESTIONS_DB[subject])}\n\n{q_data['q']}\n\n{options_text}"
    await query.message.edit_text(msg_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith('exam_'):
        exam = data.split('_')[1]
        user_states[user_id] = 'CHOOSING_SUBJECT'
        user_quizzes[user_id] = {'exam': exam}

        keyboard = [
            [InlineKeyboardButton("English", callback_data='sub_English'), InlineKeyboardButton("Maths", callback_data='sub_Maths')],
            [InlineKeyboardButton("Physics", callback_data='sub_Physics'), InlineKeyboardButton("Chemistry", callback_data='sub_Chemistry')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"✅ {exam} Selected.\n\nChoose a subject:", reply_markup=reply_markup)

    elif data.startswith('sub_'):
        subject = data.split('_')[1]
        user_states[user_id] = 'QUIZ_ACTIVE'
        user_quizzes[user_id].update({'subject': subject, 'current_q': 0, 'score': 0})
        await send_question(query, user_id)

    elif data.startswith('ans_'):
        if user_states.get(user_id) != 'QUIZ_ACTIVE':
            return
            
        user_ans = data.split('_')[1]
        quiz = user_quizzes[user_id]
        subject = quiz['subject']
        q_index = quiz['current_q']
        q_data = QUESTIONS_DB[subject][q_index]

        if user_ans == q_data['ans']:
            feedback = "✅ Correct!\n\n"
            quiz['score'] += 1
        else:
            feedback = f"❌ Wrong.\n\n✅ Correct Answer: {q_data['ans']}\n\n"

        feedback += f"💡 Explanation:\n{q_data['exp']}"
        
        # Move to next question
        quiz['current_q'] += 1
        
        keyboard = [[InlineKeyboardButton("Next ➡️", callback_data="next_question")]]
        if quiz['current_q'] >= len(QUESTIONS_DB[subject]):
            keyboard = [[InlineKeyboardButton("Finish 🏁", callback_data="finish_quiz")]]
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(feedback, reply_markup=reply_markup)

    elif data == "next_question":
        await send_question(query, user_id)

    elif data == "finish_quiz":
        quiz = user_quizzes[user_id]
        subject = quiz['subject']
        score = quiz['score']
        total = len(QUESTIONS_DB[subject])
        pct = int((score / total) * 100)

        await query.message.edit_text(
            f"🎉 Quiz Completed!\n\n📊 Score: {score}/{total}\n📈 Percentage: {pct}%\n\nUse /start to practice again!"
        )
        user_states.pop(user_id, None)
        user_quizzes.pop(user_id, None)

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please use /start to begin your ScholarAI quiz.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_handler))

    application.run_polling()

if __name__ == '__main__':
    main()
    
    
