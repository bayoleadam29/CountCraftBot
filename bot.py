import os
import re
import io
import asyncio
from datetime import datetime
from collections import Counter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# User sessions
user_sessions = {}

# ==================== TEXT ANALYSIS FUNCTIONS ====================
def count_words(text):
    """Count total words"""
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def count_unique_words(text):
    """Count unique words"""
    words = re.findall(r'\b\w+\b', text.lower())
    return len(set(words))

def count_characters(text):
    """Count characters (with and without spaces)"""
    return {
        "with_spaces": len(text),
        "without_spaces": len(re.sub(r'\s', '', text))
    }

def count_sentences(text):
    """Count sentences"""
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])

def count_paragraphs(text):
    """Count paragraphs"""
    paragraphs = [p for p in text.split('\n') if p.strip()]
    return len(paragraphs)

def count_lines(text):
    """Count lines"""
    lines = text.split('\n')
    return len([l for l in lines if l.strip()])

def count_syllables(word):
    """Count syllables in a word (basic algorithm)"""
    word = word.lower()
    count = 0
    vowels = 'aeiouy'
    if word[0] in vowels:
        count += 1
    for index in range(1, len(word)):
        if word[index] in vowels and word[index-1] not in vowels:
            count += 1
    if word.endswith('e'):
        count -= 1
    if count == 0:
        count = 1
    return count

def count_total_syllables(text):
    """Count total syllables in text"""
    words = re.findall(r'\b\w+\b', text)
    return sum(count_syllables(word) for word in words)

def count_characters_by_type(text):
    """Count character types"""
    letters = sum(1 for c in text if c.isalpha())
    digits = sum(1 for c in text if c.isdigit())
    spaces = sum(1 for c in text if c.isspace())
    punctuation = sum(1 for c in text if c in '.,!?;:()[]{}"\'')
    special = len(text) - letters - digits - spaces - punctuation
    return {
        "letters": letters,
        "digits": digits,
        "spaces": spaces,
        "punctuation": punctuation,
        "special": special
    }

def count_vowels_consonants(text):
    """Count vowels and consonants"""
    vowels = 'aeiouAEIOU'
    consonants = 'bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ'
    vowel_count = sum(1 for c in text if c in vowels)
    consonant_count = sum(1 for c in text if c in consonants)
    return {
        "vowels": vowel_count,
        "consonants": consonant_count
    }

def word_frequency(text, limit=10):
    """Get word frequency"""
    words = re.findall(r'\b\w+\b', text.lower())
    return Counter(words).most_common(limit)

def calculate_readability(text):
    """Calculate Flesch Reading Ease"""
    words = count_words(text)
    sentences = count_sentences(text)
    syllables = count_total_syllables(text)
    
    if words == 0 or sentences == 0:
        return {"score": 0, "level": "No text to analyze"}
    
    flesch = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    
    if flesch >= 90:
        level = "Very Easy (5th grade)"
    elif flesch >= 80:
        level = "Easy (6th grade)"
    elif flesch >= 70:
        level = "Fairly Easy (7th grade)"
    elif flesch >= 60:
        level = "Plain English (8th-9th grade)"
    elif flesch >= 50:
        level = "Fairly Difficult (10th-12th grade)"
    elif flesch >= 30:
        level = "Difficult (College)"
    else:
        level = "Very Difficult (College Graduate)"
    
    return {
        "score": flesch,
        "level": level,
        "avg_words": words / sentences if sentences > 0 else 0
    }

def estimate_reading_time(text):
    """Estimate reading time"""
    words = count_words(text)
    # Average reading speed: 200-250 words per minute
    reading_speed = 225
    minutes = words / reading_speed
    return {
        "minutes": minutes,
        "seconds": minutes * 60
    }

def estimate_speaking_time(text):
    """Estimate speaking time"""
    words = count_words(text)
    # Average speaking speed: 130-150 words per minute
    speaking_speed = 140
    minutes = words / speaking_speed
    return {
        "minutes": minutes,
        "seconds": minutes * 60
    }

# ==================== KEYBOARD FUNCTIONS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Full Analysis", callback_data="full")],
        [InlineKeyboardButton("📝 Word Frequency", callback_data="frequency")],
        [InlineKeyboardButton("📖 Readability", callback_data="readability")],
        [InlineKeyboardButton("⏱️ Time Estimates", callback_data="time")],
        [InlineKeyboardButton("📋 Character Analysis", callback_data="chars")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_result_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Full Analysis", callback_data="full")],
        [InlineKeyboardButton("📝 Word Frequency", callback_data="frequency")],
        [InlineKeyboardButton("📖 Readability", callback_data="readability")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Initialize user session
    user_id = str(user.id)
    user_sessions[user_id] = {}
    
    welcome_message = (
        f"📊 Welcome {user.first_name} to **CountCraftBot**!\n\n"
        "Your precision text counting companion!\n\n"
        "**✨ Features:**\n"
        "• 📊 Count words, characters, sentences, paragraphs\n"
        "• 📝 Analyze word frequency\n"
        "• 📖 Calculate readability scores\n"
        "• ⏱️ Estimate reading and speaking time\n"
        "• 📋 Analyze character types\n"
        "• 🎯 Count vowels and consonants\n\n"
        "**🎯 How to use:**\n"
        "• Send me any text\n"
        "• Click the buttons for detailed analysis\n"
        "• Get instant statistics!\n\n"
        "⬇️ Send me text or use the buttons below!"
    )
    
    await update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📖 **CountCraftBot User Guide**\n\n"
        "**📊 Full Analysis**\n"
        "• Shows all statistics at once\n"
        "• Words, characters, sentences, paragraphs\n\n"
        "**📝 Word Frequency**\n"
        "• Shows most common words\n"
        "• Top 10 words with counts\n\n"
        "**📖 Readability**\n"
        "• Flesch Reading Ease score\n"
        "• Reading level\n"
        "• Average words per sentence\n\n"
        "**⏱️ Time Estimates**\n"
        "• Reading time\n"
        "• Speaking time\n\n"
        "**📋 Character Analysis**\n"
        "• Character types (letters, digits, etc.)\n"
        "• Vowels and consonants count\n\n"
        "**Commands**\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/stats - Get quick stats\n"
        "/frequency - Get word frequency"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    text = " ".join(context.args) if context.args else None
    
    if not text:
        await update.message.reply_text(
            "📝 **Please send text to analyze**\n\n"
            "Example: `/stats The quick brown fox jumps over the lazy dog`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    result = analyze_summary(text)
    await update.message.reply_text(
        result,
        parse_mode="Markdown",
        reply_markup=get_result_keyboard()
    )

async def frequency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /frequency command"""
    text = " ".join(context.args) if context.args else None
    
    if not text:
        await update.message.reply_text(
            "📝 **Please send text to analyze**\n\n"
            "Example: `/frequency The quick brown fox jumps over the lazy dog`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    result = analyze_frequency(text)
    await update.message.reply_text(
        result,
        parse_mode="Markdown",
        reply_markup=get_result_keyboard()
    )

# ==================== ANALYSIS FUNCTIONS ====================
def analyze_full(text):
    """Perform full text analysis"""
    word_count = count_words(text)
    unique_words = count_unique_words(text)
    char_counts = count_characters(text)
    sentence_count = count_sentences(text)
    paragraph_count = count_paragraphs(text)
    line_count = count_lines(text)
    reading_time = estimate_reading_time(text)
    speaking_time = estimate_speaking_time(text)
    readability = calculate_readability(text)
    char_types = count_characters_by_type(text)
    vowel_consonant = count_vowels_consonants(text)
    
    result = (
        f"📊 **Full Text Analysis**\n\n"
        f"📝 **Words:** {word_count}\n"
        f"🔄 **Unique Words:** {unique_words}\n"
        f"🔤 **Characters:**\n"
        f"  • With spaces: {char_counts['with_spaces']}\n"
        f"  • Without spaces: {char_counts['without_spaces']}\n"
        f"📖 **Sentences:** {sentence_count}\n"
        f"📄 **Paragraphs:** {paragraph_count}\n"
        f"📏 **Lines:** {line_count}\n\n"
        f"📊 **Character Types:**\n"
        f"  • Letters: {char_types['letters']}\n"
        f"  • Digits: {char_types['digits']}\n"
        f"  • Spaces: {char_types['spaces']}\n"
        f"  • Punctuation: {char_types['punctuation']}\n"
        f"  • Special: {char_types['special']}\n\n"
        f"🔊 **Vowels:** {vowel_consonant['vowels']}\n"
        f"🔇 **Consonants:** {vowel_consonant['consonants']}\n\n"
        f"⏱️ **Reading Time:** {reading_time['minutes']:.1f} min ({reading_time['seconds']:.0f} sec)\n"
        f"🎤 **Speaking Time:** {speaking_time['minutes']:.1f} min ({speaking_time['seconds']:.0f} sec)\n"
        f"📖 **Readability:** {readability['score']:.1f} ({readability['level']})"
    )
    
    return result

def analyze_frequency(text):
    """Analyze word frequency"""
    frequency = word_frequency(text, 10)
    
    if not frequency:
        return "📝 **No words found to analyze**"
    
    result = "📝 **Word Frequency (Top 10)**\n\n"
    for i, (word, count) in enumerate(frequency, 1):
        result += f"{i}. **{word}** - {count} time{'s' if count > 1 else ''}\n"
    
    return result

def analyze_summary(text):
    """Quick summary analysis"""
    word_count = count_words(text)
    char_counts = count_characters(text)
    sentence_count = count_sentences(text)
    reading_time = estimate_reading_time(text)
    
    result = (
        f"📋 **Quick Summary**\n\n"
        f"📝 Words: {word_count}\n"
        f"🔤 Characters: {char_counts['without_spaces']}\n"
        f"📖 Sentences: {sentence_count}\n"
        f"⏱️ Reading Time: {reading_time['minutes']:.1f} min\n\n"
        f"💡 For full analysis, click 'Full Analysis' below."
    )
    
    return result

def analyze_readability(text):
    """Detailed readability analysis"""
    readability = calculate_readability(text)
    word_count = count_words(text)
    sentence_count = count_sentences(text)
    syllables = count_total_syllables(text)
    
    if word_count == 0:
        return "📖 **No text to analyze for readability**"
    
    result = (
        f"📖 **Readability Analysis**\n\n"
        f"📊 **Flesch Reading Ease:** {readability['score']:.1f}\n"
        f"📚 **Reading Level:** {readability['level']}\n"
        f"📝 **Avg Words/Sentence:** {readability['avg_words']:.1f}\n\n"
        f"📊 **Metrics:**\n"
        f"  • Total Words: {word_count}\n"
        f"  • Total Sentences: {sentence_count}\n"
        f"  • Total Syllables: {syllables}\n\n"
        f"💡 **Flesch Score Guide:**\n"
        f"  • 90-100: Very Easy (5th grade)\n"
        f"  • 60-70: Plain English (8th-9th grade)\n"
        f"  • 30-50: Difficult (College)\n"
        f"  • 0-30: Very Difficult (Graduate)"
    )
    
    return result

def analyze_time(text):
    """Analyze time estimates"""
    reading_time = estimate_reading_time(text)
    speaking_time = estimate_speaking_time(text)
    word_count = count_words(text)
    
    result = (
        f"⏱️ **Time Estimates**\n\n"
        f"📝 **Text Length:** {word_count} words\n\n"
        f"📖 **Reading Time:**\n"
        f"  • {reading_time['minutes']:.1f} minutes\n"
        f"  • {reading_time['seconds']:.0f} seconds\n\n"
        f"🎤 **Speaking Time:**\n"
        f"  • {speaking_time['minutes']:.1f} minutes\n"
        f"  • {speaking_time['seconds']:.0f} seconds\n\n"
        f"💡 **Assumptions:**\n"
        f"  • Reading speed: 225 words/min\n"
        f"  • Speaking speed: 140 words/min"
    )
    
    return result

def analyze_chars(text):
    """Analyze characters in detail"""
    char_types = count_characters_by_type(text)
    vowel_consonant = count_vowels_consonants(text)
    char_counts = count_characters(text)
    
    result = (
        f"📋 **Character Analysis**\n\n"
        f"🔤 **Total Characters:** {char_counts['with_spaces']}\n"
        f"  • With spaces: {char_counts['with_spaces']}\n"
        f"  • Without spaces: {char_counts['without_spaces']}\n\n"
        f"📊 **Character Types:**\n"
        f"  • Letters: {char_types['letters']}\n"
        f"  • Digits: {char_types['digits']}\n"
        f"  • Spaces: {char_types['spaces']}\n"
        f"  • Punctuation: {char_types['punctuation']}\n"
        f"  • Special: {char_types['special']}\n\n"
        f"🔊 **Vowels:** {vowel_consonant['vowels']}\n"
        f"🔇 **Consonants:** {vowel_consonant['consonants']}"
    )
    
    return result

# ==================== CALLBACK HANDLERS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    
    # Get the last analyzed text
    last_text = user_sessions.get(user_id, {}).get("last_text", "")
    
    if data == "full":
        if not last_text:
            await query.edit_message_text(
                "📝 **Send me text to analyze first!**\n\n"
                "Please send any text and then use the buttons.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        result = analyze_full(last_text)
        await query.edit_message_text(
            result,
            parse_mode="Markdown",
            reply_markup=get_result_keyboard()
        )
    
    elif data == "frequency":
        if not last_text:
            await query.edit_message_text(
                "📝 **Send me text to analyze first!**\n\n"
                "Please send any text and then use the buttons.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        result = analyze_frequency(last_text)
        await query.edit_message_text(
            result,
            parse_mode="Markdown",
            reply_markup=get_result_keyboard()
        )
    
    elif data == "readability":
        if not last_text:
            await query.edit_message_text(
                "📝 **Send me text to analyze first!**\n\n"
                "Please send any text and then use the buttons.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        result = analyze_readability(last_text)
        await query.edit_message_text(
            result,
            parse_mode="Markdown",
            reply_markup=get_result_keyboard()
        )
    
    elif data == "time":
        if not last_text:
            await query.edit_message_text(
                "📝 **Send me text to analyze first!**\n\n"
                "Please send any text and then use the buttons.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        result = analyze_time(last_text)
        await query.edit_message_text(
            result,
            parse_mode="Markdown",
            reply_markup=get_result_keyboard()
        )
    
    elif data == "chars":
        if not last_text:
            await query.edit_message_text(
                "📝 **Send me text to analyze first!**\n\n"
                "Please send any text and then use the buttons.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        result = analyze_chars(last_text)
        await query.edit_message_text(
            result,
            parse_mode="Markdown",
            reply_markup=get_result_keyboard()
        )
    
    elif data == "help":
        await help_command(update, context)
    
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "Send me text to analyze or use the buttons above!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MESSAGE HANDLERS ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    # Store the text for later analysis
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["last_text"] = text
    
    # Perform automatic quick analysis
    word_count = count_words(text)
    char_counts = count_characters(text)
    sentence_count = count_sentences(text)
    reading_time = estimate_reading_time(text)
    
    # Send quick summary
    await update.message.reply_text(
        f"📝 **Text Received!**\n\n"
        f"📊 Quick Stats:\n"
        f"• Words: {word_count}\n"
        f"• Characters: {char_counts['without_spaces']}\n"
        f"• Sentences: {sentence_count}\n"
        f"• Reading Time: {reading_time['minutes']:.1f} min\n\n"
        f"💡 Click below for detailed analysis!",
        parse_mode="Markdown",
        reply_markup=get_result_keyboard()
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages (text files)"""
    document = update.message.document
    
    # Check if it's a text file
    if document.mime_type and document.mime_type.startswith("text/"):
        try:
            file = await document.get_file()
            content = await file.download_as_bytearray()
            text = content.decode('utf-8')
            
            user_id = str(update.effective_user.id)
            if user_id not in user_sessions:
                user_sessions[user_id] = {}
            user_sessions[user_id]["last_text"] = text
            
            # Perform quick analysis
            word_count = count_words(text)
            char_counts = count_characters(text)
            sentence_count = count_sentences(text)
            reading_time = estimate_reading_time(text)
            
            await update.message.reply_text(
                f"📄 **Document Received!**\n\n"
                f"📊 Quick Stats:\n"
                f"• Words: {word_count}\n"
                f"• Characters: {char_counts['without_spaces']}\n"
                f"• Sentences: {sentence_count}\n"
                f"• Reading Time: {reading_time['minutes']:.1f} min\n\n"
                f"💡 Click below for detailed analysis!",
                parse_mode="Markdown",
                reply_markup=get_result_keyboard()
            )
        except Exception as e:
            print(f"Document error: {e}")
            await update.message.reply_text(
                "❌ **Error reading document**\n\n"
                "Please make sure it's a valid text file.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    else:
        await update.message.reply_text(
            "📄 **Unsupported document type**\n\n"
            "Please send a .txt file for analysis.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    print("📊 Starting CountCraftBot...")
    print("📝 Ready to count and analyze text!")
    
    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("frequency", frequency_command))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Start the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
