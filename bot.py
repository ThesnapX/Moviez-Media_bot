import telebot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
import datetime
import time
from config import BOT_TOKEN, ADMIN_IDS
from database import Database

# Initialize bot and database
bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

# Remove any existing webhook
try:
    webhook_info = bot.get_webhook_info()
    if webhook_info.url:
        print(f"⚠️ Found active webhook: {webhook_info.url}")
        bot.remove_webhook()
        print("✅ Webhook removed successfully")
        time.sleep(2)
    else:
        print("✅ No active webhook found")
except Exception as e:
    print(f"⚠️ Error removing webhook: {e}")

# Store temporary upload sessions
upload_sessions = {}

@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user_id = message.chat.id
    params = message.text.split()[1] if len(message.text.split()) > 1 else None
    
    # Handle shared links
    if params:
        files = db.get_files(params)
        if not files:
            bot.reply_to(message, "❌ No media found for this link.")
            return
        
        for f in files:
            try:
                if f['type'] == 'photo':
                    bot.send_photo(user_id, f['file_id'], caption=f.get('caption', ''))
                elif f['type'] == 'video':
                    bot.send_video(user_id, f['file_id'], caption=f.get('caption', ''))
                elif f['type'] == 'document':
                    bot.send_document(user_id, f['file_id'])
                elif f['type'] == 'audio':
                    bot.send_audio(user_id, f['file_id'])
                elif f['type'] == 'voice':
                    bot.send_voice(user_id, f['file_id'])
                elif f['type'] == 'sticker':
                    bot.send_sticker(user_id, f['file_id'])
            except Exception as e:
                print(f"Error sending file: {e}")
        
        # Increment access count
        db.increment_access(params)
        bot.reply_to(message, "⚠️ Files will be auto-deleted after 30 minutes.")
        return
    
    # Regular start menu - Different for Admin vs Users
    if user_id in ADMIN_IDS:
        # ADMIN VIEW - Only Upload Button
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📤 Upload Files")
        bot.send_message(
            user_id,
            "👑 *Admin Panel*\n\nWelcome back! Use the button below to share files.",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        # USER VIEW - Channel and Website Links
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📢 Join Our Channel", url="https://t.me/officialmoviezmedia"),
            InlineKeyboardButton("🌐 Visit Our Website", url="https://moviez-media.vercel.app")
        )
        bot.send_message(
            user_id,
            "📢 *Welcome to File Sharing Bot!*\n\n"
            "This bot allows you to access shared files from admins.\n\n"
            "👇 Please check out our channel and website:",
            parse_mode="Markdown",
            reply_markup=markup
        )

@bot.message_handler(func=lambda message: message.text == "📤 Upload Files")
def upload_button(message):
    """Handle upload button click (Admin only)"""
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Unauthorized")
        return
    
    start_upload(message)

@bot.message_handler(commands=['upload'])
def upload_command(message):
    """Handle /upload command (Admin only)"""
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ This command is for admins only.")
        return
    
    start_upload(message)

def start_upload(message):
    """Initialize upload session"""
    media_id = f"file_{int(time.time())}_{message.chat.id}"
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("✅ Done")
    
    upload_sessions[message.chat.id] = {
        'media_id': media_id,
        'files': []
    }
    
    bot.send_message(
        message.chat.id,
        "📤 *Upload Mode Activated*\n\n"
        "Send me files (one by one or multiple at once).\n"
        "When finished, click ✅ Done",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(content_types=[
    'photo', 'video', 'document', 'audio', 'voice', 'animation', 'sticker'
])
def handle_media(message):
    """Handle all media types"""
    user_id = message.chat.id
    
    if user_id not in upload_sessions:
        return
    
    session = upload_sessions[user_id]
    file_entry = None
    
    # Process different media types
    if message.photo:
        file_entry = {
            'type': 'photo',
            'file_id': message.photo[-1].file_id,
            'caption': message.caption or ''
        }
    elif message.video:
        file_entry = {
            'type': 'video',
            'file_id': message.video.file_id,
            'caption': message.caption or ''
        }
    elif message.document:
        file_entry = {
            'type': 'document',
            'file_id': message.document.file_id
        }
    elif message.audio:
        file_entry = {
            'type': 'audio',
            'file_id': message.audio.file_id
        }
    elif message.voice:
        file_entry = {
            'type': 'voice',
            'file_id': message.voice.file_id
        }
    elif message.animation:
        file_entry = {
            'type': 'animation',
            'file_id': message.animation.file_id
        }
    elif message.sticker:
        file_entry = {
            'type': 'sticker',
            'file_id': message.sticker.file_id
        }
    
    if file_entry:
        session['files'].append(file_entry)
        current_count = len(session['files'])
        
        # Show progress for 1st, 3rd, 5th, etc.
        if current_count == 1 or current_count % 2 == 0:
            bot.reply_to(
                message,
                f"✅ *{current_count} files* saved so far. Send more or click ✅ Done.",
                parse_mode="Markdown"
            )

@bot.message_handler(func=lambda message: message.text == "✅ Done")
def finish_upload(message):
    """Finish upload and generate link"""
    user_id = message.chat.id
    
    if user_id not in upload_sessions:
        bot.reply_to(message, "❌ No active upload session. Use /upload to start.")
        return
    
    session = upload_sessions[user_id]
    files = session['files']
    media_id = session['media_id']
    
    if files:
        # Save to MongoDB
        db.save_files(media_id, files, user_id)
        
        shareable_link = f"https://t.me/{bot.get_me().username}?start={media_id}"
        
        # Generate summary
        summary = {}
        for f in files:
            f_type = f['type']
            summary[f_type] = summary.get(f_type, 0) + 1
        
        summary_text = ""
        for file_type, count in summary.items():
            summary_text += f"📁 {file_type}: {count}\n"
        
        bot.send_message(
            user_id,
            f"✅ *Upload Complete!*\n\n"
            f"📦 Total files: {len(files)}\n"
            f"{summary_text}\n"
            f"🔗 *Shareable Link:*\n{shareable_link}",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Clear session
        del upload_sessions[user_id]
    else:
        bot.send_message(
            user_id,
            "❌ No files uploaded.",
            reply_markup=ReplyKeyboardRemove()
        )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Handle text messages"""
    user_id = message.chat.id
    
    if user_id in upload_sessions:
        bot.reply_to(
            message,
            "❌ Please send media files only, or click ✅ Done to finish."
        )

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Get bot statistics (admin only)"""
    if message.chat.id not in ADMIN_IDS:
        return
    
    total_files = db.collection.count_documents({})
    total_accesses = 0
    for doc in db.collection.find({}, {'access_count': 1}):
        total_accesses += doc.get('access_count', 0)
    
    bot.send_message(
        message.chat.id,
        f"📊 *Bot Statistics*\n\n"
        f"📦 Total shared files: {total_files}\n"
        f"👁️ Total link accesses: {total_accesses}",
        parse_mode="Markdown"
    )

if __name__ == '__main__':
    print("🤖 Bot is running...")
    print(f"👑 Admin IDs: {ADMIN_IDS}")
    print(f"🤖 Bot username: @{bot.get_me().username}")
    
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=30)
    except Exception as e:
        print(f"❌ Polling error: {e}")
        time.sleep(5)
        bot.infinity_polling()