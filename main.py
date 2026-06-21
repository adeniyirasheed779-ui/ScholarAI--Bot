import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_data = {}

QUESTIONS = {
    "JAMB": {
        "Maths": [
            {
                "q": "If 2x + 5 = 15, what is x?",
                "a": "5",
                "exp": "Subtract 5 from both sides to get 2x = 10. Then divide both sides by 2 to get x = 5."
            },
            {
                "q": "What is 25% of 200?",
                "a": "50",
                "exp": "25% means 25/100. So 25/100 × 200 = 50."
            },
            {
                "q": "Solve: 7² - 5²",
                "a": "24",
                "exp": "7² = 49 and 5² = 25. Therefore 49 - 25 = 24."
            }
        ],
        "English": [
            {
                "q": "Choose synonym: 'Big'  a) Small  b) Large  c) Tiny",
                "a": "b",
                "exp": "Large has a similar meaning to Big, while Small and Tiny are opposites."
            }
        ]
    },
    "WAEC": {
        "Maths": [
            {
                "q": "Find area of a circle with radius 7 cm. Use π = 22/7.",
                "a": "154",
                "exp": "Area = πr² = (22/7) × 7 × 7 = 154."
            },
            {
                "q": "If y = 3x + 2 and x = 4, find y.",
                "a": "14",
                "exp": "Substitute x = 4 into y = 3(4) + 2 = 14."
            }
        ]
    }
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["JAMB", "WAEC"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "📚 Welcome to ScholarAI\n\n"
        "Practice smarter. Pass with confidence.\n\n"
        "Choose an exam:",
        reply_markup=reply_markup
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    # Exam Selection
    if text in ["JAMB", "WAEC"]:
        user_data[user_id] = {
            "exam": text,
            "q_index": 0,
            "score": 0
        }

        keyboard = [["Maths", "English", "Physics"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"📚 {text} Selected\n\nChoose a subject:",
            reply_markup=reply_markup
        )
        return

    # Subject Selection
    if text in ["Maths", "English", "Physics"] and user_id in user_data:
        exam = user_data[user_id]["exam"]

        if exam in QUESTIONS and text in QUESTIONS[exam]:
            user_data[user_id]["subject"] = text
            user_data[user_id]["q_index"] = 0

            q = QUESTIONS[exam][text][0]

            await update.message.reply_text(
                f"Question 1/{len(QUESTIONS[exam][text])}\n\n"
                f"{q['q']}\n\n"
                f"Reply with your answer."
            )
        else:
            await update.message.reply_text(
                f"❌ No questions available yet for {text} in {exam}.\n"
                f"Choose another subject."
            )
        return

    # Answer Questions
    if user_id in user_data and "subject" in user_data[user_id]:
        exam = user_data[user_id]["exam"]
        subject = user_data[user_id]["subject"]
        idx = user_data[user_id]["q_index"]

        question = QUESTIONS[exam][subject][idx]
        correct_answer = question["a"]
        explanation = question.get("exp", "No explanation available.")

        if text.lower() == correct_answer.lower():
            user_data[user_id]["score"] += 1

            await update.message.reply_text(
                f"✅ Correct!\n\n"
                f"💡 Explanation:\n{explanation}"
            )
        else:
            await update.message.reply_text(
                f"❌ Wrong.\n\n"
                f"✅ Correct Answer: {correct_answer}\n\n"
                f"💡 Explanation:\n{explanation}"
            )

        idx += 1
        total_questions = len(QUESTIONS[exam][subject])

        if idx < total_questions:
            user_data[user_id]["q_index"] = idx

            next_q = QUESTIONS[exam][subject][idx]

            await update.message.reply_text(
                f"Question {idx + 1}/{total_questions}\n\n"
                f"{next_q['q']}"
            )
        else:
            score = user_data[user_id]["score"]
            percentage = round((score / total_questions) * 100)

            await update.message.reply_text(
                f"🎉 Quiz Completed!\n\n"
                f"📊 Score: {score}/{total_questions}\n"
                f"📈 Percentage: {percentage}%\n\n"
                f"Type /start to play again."
            )

            del user_data[user_id]

        return

    await update.message.reply_text(
        "Type /start to begin your ScholarAI quiz."
    )


app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    print("ScholarAI Bot is running...")
    app.run_polling()
