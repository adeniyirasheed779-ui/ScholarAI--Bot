import os
import telebot
from telebot import types

# Get the token from Railway's environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# Track what state a user is in and their current quiz progress
user_states = {}  # {user_id: 'STATE'}
user_quizzes = {} # {user_id: {'subject': 'English', 'current_q': 0, 'score': 0}}

# The Question Database
QUESTIONS_DB = {
    "English": [
        {"q": "Choose synonym: Big", "options": ["a", "b", "c"], "text_opts": "a) Small\nb) Large\nc) Tiny", "ans": "b", "exp": "Large has a similar meaning to Big."},
        {"q": "Choose antonym: Hot", "options": ["a", "b", "c"], "text_opts": "a) Cold\nb) Warm\nc) Spicy", "ans": "a", "exp": "Cold is the opposite of Hot."}
    ],
    "Chemistry": [
        {"q": "What is the chemical symbol for Water?", "options": ["a", "b", "c"], "text_opts": "a) CO2\nb) H2O\nc) NaCl", "ans": "b", "exp": "H2O stands for Hydrogen and Oxygen."}
    ],
    "Maths": [
        {"q": "Solve for x: 2x + 5 = 11", "options": ["a", "b", "c"], "text_opts": "a) 3\nb) 4\nc) 6", "ans": "a", "exp": "Subtract 5 from both sides: 2x = 6. Divide by 2: x = 3."}
    ],
    "Physics": [
        {"q": "What is the unit of force?", "options": ["a", "b", "c"], "text_opts": "a) Joule\nb) Watt\nc) Newton", "ans": "c", "exp": "The SI unit of force is the Newton (N)."}
    ]
}

def send_question(chat_id, user_id):
    quiz = user_quizzes[user_id]
    subject = quiz['subject']
    q_index = quiz['current_q']
    
    question_data = QUESTIONS_DB[subject][q_index]
    
    # Create buttons for options A, B, C
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row(types.KeyboardButton('A'), types.KeyboardButton('B'), types.KeyboardButton('C'))
    
    msg_text = f"Question {q_index + 1}/{len(QUESTIONS_DB[subject])}\n\n{question_data['q']}\n\n{question_data['text_opts']}"
    bot.send_message(chat_id, msg_text, reply_markup=markup)

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user_states[user_id] = 'CHOOSING_EXAM'
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row(types.KeyboardButton('JAMB'), types.KeyboardButton('WAEC'))
    
    bot.send_message(message.chat.id, "📚 Welcome to ScholarAI\n\nPractice smarter. Pass with confidence.\n\nChoose an exam:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text
    chat_id = message.chat.id

    # If user hasn't typed /start yet
    if user_id not in user_states:
        bot.send_message(chat_id, "Type /start to begin your ScholarAI quiz.")
        return

    state = user_states[user_id]

    if state == 'CHOOSING_EXAM':
        if text in ['JAMB', 'WAEC']:
            user_states[user_id] = 'CHOOSING_SUBJECT'
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.row(types.KeyboardButton('Maths'), types.KeyboardButton('English'))
            markup.row(types.KeyboardButton('Physics'), types.KeyboardButton('Chemistry'))
            bot.send_message(chat_id, f"✅ {text} Selected.\n\nChoose a subject:", reply_markup=markup)
        else:
            bot.send_message(chat_id, "Please select JAMB or WAEC using the buttons.")

    elif state == 'CHOOSING_SUBJECT':
        if text in QUESTIONS_DB:
            user_states[user_id] = 'QUIZ_ACTIVE'
            user_quizzes[user_id] = {'subject': text, 'current_q': 0, 'score': 0}
            bot.send_message(chat_id, f"📖 starting {text} Quiz...")
            send_question(chat_id, user_id)
        else:
            bot.send_message(chat_id, "❌ No questions available yet for that subject. Choose another.")

    elif state == 'QUIZ_ACTIVE':
        quiz = user_quizzes.get(user_id)
        subject = quiz['subject']
        q_index = quiz['current_q']
        question_data = QUESTIONS_DB[subject][q_index]
        
        user_ans = text.lower().strip()
        
        if user_ans in ['a', 'b', 'c']:
            if user_ans == question_data['ans']:
                bot.send_message(chat_id, "✅ Correct!")
                quiz['score'] += 1
            else:
                bot.send_message(chat_id, f"❌ Wrong.\n\n✅ Correct Answer: {question_data['ans']}")
                
            bot.send_message(chat_id, f"💡 Explanation:\n{question_data['exp']}")
            
            # Move to next question
            quiz['current_q'] += 1
            if quiz['current_q'] < len(QUESTIONS_DB[subject]):
                send_question(chat_id, user_id)
            else:
                # Quiz Completed
                score = quiz['score']
                total = len(QUESTIONS_DB[subject])
                pct = int((score / total) * 100)
                
                bot.send_message(chat_id, f"🎉 Quiz Completed!\n\n📊 Score: {score}/{total}\n📈 Percentage: {pct}%\n\nType /start to play again.", reply_markup=types.ReplyKeyboardRemove())
                # Reset states
                user_states.pop(user_id, None)
                user_quizzes.pop(user_id, None)
        else:
            bot.send_message(chat_id, "Please answer by clicking A, B, or C.")

# Start the bot polling
bot.infinity_polling()
    
