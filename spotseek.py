#!/usr/bin/python3

from queue_functions import *
from my_imports import *
from csv_functions import *
from telebot.types import InlineQueryResultCachedAudio

import traceback

# todo: isn't best practice and can be optimized later.
# to keep track of last query and deboune fast changes while user is still typing
last_queries = {}

# initialize and get ready
bot = telebot.TeleBot(bot_api)

# defined commands
@bot.message_handler(commands = ['start'])
def start_message_handler(message):
    bot.send_message(message.chat.id, welcome_message, disable_web_page_preview=True)
    log(bot_name + " log:\n📥 /start command sent from user: " + str(message.chat.id))

@bot.message_handler(commands = ['info'])
def info_message_handler(message):
    bot.send_message(message.chat.id, info_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n📥 /info command sent from user: " + str(message.chat.id))

@bot.message_handler(commands = ['privacy'])
def privacy_message_handler(message):
    bot.send_message(message.chat.id, privacy_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n📥 /privacy command sent from user: " + str(message.chat.id))

# wrong defined patterns such as deezer, youtube, ...
@bot.message_handler(regexp = deezer_link_pattern)
def deezer_link_handler(message):
    bot.send_message(message.chat.id, deezer_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ deezer link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = soundcloud_link_pattern)
def soundcloud_link_handler(message):
    bot.send_message(message.chat.id, soundcloud_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ soundcloud link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = youtube_link_pattern)
def youtube_link_handler(message):
    bot.send_message(message.chat.id, youtube_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ youtube link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = spotify_episode_link_pattern)
def spotify_episode_link_handler(message):
    bot.send_message(message.chat.id, spotify_episode_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ episode link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = spotify_artist_link_pattern)
def spotify_artist_link_handler(message):
    bot.send_message(message.chat.id, spotify_artist_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ artist link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = spotify_user_link_pattern)
def spotify_user_link_handler(message):
    bot.send_message(message.chat.id, spotify_user_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ user link sent from user: " + str(message.chat.id))

@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    # check that query is not empty
    if not inline_query.query:
        return
    
    # Store the current query
    last_queries[inline_query.from_user.id] = inline_query.query
    # Wait briefly to see if the user keeps typing
    time.sleep(0.6)
    # If user typed something new during the wait, skip this request
    if last_queries.get(inline_query.from_user.id) != inline_query.query:
        return

    # search and find tracks from spotify. then check our local db
    tracks = search_track_ids(inline_query.query)

    results = [
        InlineQueryResultCachedAudio(
            id=track["id"],
            audio_file_id=track['telegram_audio_id'],
            caption="@SpotSeekBot"
        )
        for track in tracks
    ]
    
    # Send the results back to Telegram
    bot.answer_inline_query(inline_query.id, results)

# correct pattern
@bot.message_handler(regexp = spotify_correct_link_pattern)
def handle_correct_spotify_link(message):       
    guide_message_1 = bot.send_message(message.chat.id, "Ok🙂👍\nPlease be patient and wait till I download all of your link.\n\nYou will get a message in the end.")
    log(bot_name + " log:\n🔗✅ correct link pattern from user: " + str(message.chat.id) + " with contents of:\n" + message.text)
    try:
        # Check the membership status and stop continuing if user is not a member
        is_member = check_membership(promote_channel_username, message.chat.id)

        if is_member:
            log(bot_name + " log:\n👥✅ user " + str(message.chat.id) + " is member of channel.")
        else:
            log(bot_name + " log:\n👥❌ user " + str(message.chat.id) + " is not member of channel.")
            
            # Send message with join button to user
            keyboard = types.InlineKeyboardMarkup()
            channel_button = types.InlineKeyboardButton(text='Join', url=promote_channel_link)
            keyboard.add(channel_button)
            bot.send_message(message.chat.id,
                            not_subscribed_to_channel_message,
                            parse_mode="Markdown",
                            disable_web_page_preview=True,
                            reply_markup=keyboard)

            try_to_delete_message(message.chat.id, guide_message_1.message_id)
            return

        valid_spotify_links_in_user_text = get_valid_spotify_links(message.text)

        # if user sends multiple links combined with normal text we only extract and
        # analyze first one so the bot won't be spammed
        first_link = valid_spotify_links_in_user_text[0]

        # if the link is shortened convert "spotify.link" to "open.spotify.com"
        if get_link_type(first_link) == "shortened":
            log(bot_name + " log:\n🔗🩳 shortened link sent from user: " + str(message.chat.id))
            first_link = get_redirect_link(first_link)

        link_type = get_link_type(first_link)
        if link_type not in ["track", "album", "playlist"]:
            try_to_delete_message(message.chat.id, guide_message_1.message_id)
            bot.send_message(message.chat.id, "Looks like this link is wrong, expired or not supported. Try another.")
            log(bot_name + " log:\n🛑 error in handling short link.")
            return
        
        # # fixme
        # if link_type == "playlist" or link_type == "album":
        #     try_to_delete_message(message.chat.id, guide_message_1.message_id)
        #     bot.send_message(message.chat.id, "Sorry 😢\n\nAlbums & Playlists are temporarily disabled due to spotify policies. Please send a track link.")
        #     log(bot_name + " log:\n🛑 figue out a solution for spotify playlist limit")
        #     return
        
        matches = get_track_ids(first_link)
        
        # more than 1000 tracks
        if len(matches) > 1000:
            try_to_delete_message(message.chat.id, guide_message_1.message_id)
            bot.send_message(message.chat.id, more_than_1000_tracks_message)
            log(bot_name + " log:\n1️⃣0️⃣0️⃣0️⃣ Playlist more than 1000 tracks from user: " + str(message.chat.id))
            return

        # no tracks
        if not matches:
            try_to_delete_message(message.chat.id, guide_message_1.message_id)
            bot.send_message(message.chat.id, "sorry I couldn't extract tracks from link.")
            log(bot_name + " log:\n0️⃣ Zero tracks error from user: " + str(message.chat.id))
            return

        # check if user already has sth for download in queue
        for folder in ["track", "album", "playlist"]:
            folder_path = received_links_folder_path + "/" + folder
            files = list_of_files_in_a_folder(folder_path)
            if str(message.chat.id) in files:
                try_to_delete_message(message.chat.id, guide_message_1.message_id)
                bot.send_message(message.chat.id, sth_to_download_message, parse_mode="Markdown", disable_web_page_preview=True)
                log(bot_name + " log:\n🚦 already sth to download\nuser: " + str(message.chat.id))
                return

        try:
            # if files are already in database bypass the queue handler system (can be optimized later. currently there are duplicate codes in handler and here)
            consecutive_download = 0
            while matches and (consecutive_download < 200):
                consecutive_download += 1
                track_id = matches[0]
                # new method based on sqlite3 db
                telegram_audio_id = get_telegram_audio_id(track_id)
                if telegram_audio_id is not None:
                    matches.pop(0) # remove the track from list
                    bot.send_audio(message.chat.id, telegram_audio_id, caption=bot_username)
                    time.sleep(1)
                else:
                    break # reached track that is not in database. break and proceed to queue handler

            # no tracks left for queue handler
            if not matches:
                bot.send_message(message.chat.id, end_message, parse_mode="Markdown", disable_web_page_preview=True)
                try_to_delete_message(message.chat.id, guide_message_1.message_id)
                return
        except Exception as e:
            log(bot_name + " log:\n🛑 An error in queue bypass: " + str(e) + "\nfor user: " + str(message.chat.id))

        # everything is fine. add user tracks to queue
        write_list_to_file(matches, received_links_folder_path + "/" + link_type + "/" + str(message.chat.id))
        return


    except Exception as e:
        log(bot_name + " log:\n🛑 A general error occurred: " + str(e))
        print(traceback.format_exc())
        try_to_delete_message(message.chat.id, guide_message_1.message_id)
        try: # I added this try & except block to check if I can solve the unclosed spotseek.py processes
            bot.send_message(message.chat.id, unsuccessful_process_message, parse_mode="Markdown")
        except:
            return

# any other thing received by bot
@bot.message_handler(func=lambda message: True)
def all_other_forms_of_messages(message):
    bot.reply_to(message, wrong_link_message, disable_web_page_preview=True)
    log(bot_name + " log:\n❌wrong link pattern from user: " + str(message.chat.id) + " with contents of:\n" + message.text)

def main():
    bot.infinity_polling()

if __name__ == '__main__':
    main()
