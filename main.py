import asyncio
import os
from dotenv import load_dotenv
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import RPCError
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import ChatPrivileges

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

app = Client("perm-check-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --------- Helpers ---------
def format_rights(member) -> str:
    if member.status != ChatMemberStatus.ADMINISTRATOR:
        return "❌ Bot admin nahi hai is chat me."
    a = member.privileges  # ChatPrivileges
    # Map: label -> bool
    rights = {
        "manage_chat": a.can_manage_chat,
        "delete_messages": a.can_delete_messages,
        "manage_video_chats": a.can_manage_video_chats,
        "restrict_members": a.can_restrict_members,
        "promote_members (add admins)": a.can_promote_members,
        "change_info": a.can_change_info,
        "invite_users": a.can_invite_users,
        "pin_messages (groups)": a.can_pin_messages,
        "manage_topics (forums)": a.can_manage_topics,
        "post_messages (channels)": a.can_post_messages,
        "edit_messages (channels)": a.can_edit_messages,
        # Newer story permissions (may be None on older servers)
        "post_stories": getattr(a, "can_post_stories", False),
        "edit_stories": getattr(a, "can_edit_stories", False),
        "delete_stories": getattr(a, "can_delete_stories", False),
    }
    lines = []
    for k, v in rights.items():
        lines.append(f"{'✅' if v else '❌'} {k}")
    return "\n".join(lines)

async def resolve_target_chat(m: Message, arg: str | None):
    """
    If command used inside a chat with no arg -> use current chat.
    If arg provided -> use that username/id.
    """
    if arg:
        return await app.get_chat(arg)
    else:
        return m.chat

async def get_bot_admin_member(chat_id):
    me = await app.get_me()
    return await app.get_chat_member(chat_id, me.id)

def parse_user_and_chat_args(text_parts):
    """
    /promote <user> [chat]
    Returns (user_ref, chat_ref_or_None)
    """
    if len(text_parts) < 2:
        return None, None
    user_ref = text_parts[1]
    chat_ref = text_parts[2] if len(text_parts) >= 3 else None
    return user_ref, chat_ref

# --------- Commands ---------

@app.on_message(filters.command(["start", "help"]))
async def start_cmd(_, m: Message):
    await m.reply_text(
        "👋 Permission Checker Bot ready!\n\n"
        "Commands:\n"
        "• /check_rights [chat] — Bot ke admin rights dikhaye (agar [chat] na do to current chat)\n"
        "• /promote <user> [chat] — Agar bot ke paas add-admin right hai to <user> ko admin banaye\n\n"
        "Examples:\n"
        "• /check_rights\n"
        "• /check_rights @YourChannelUsername\n"
        "• /promote @username\n"
        "• /promote 123456789 @YourSupergroupOrChannel\n"
        "\nNote: Promote tabhi chalega jab bot admin ho aur 'promote_members' enabled ho."
    )

@app.on_message(filters.command("check_rights"))
async def check_rights_cmd(_, m: Message):
    # /check_rights [chat]
    parts = m.text.split(maxsplit=1)
    chat_ref = parts[1] if len(parts) > 1 else None
    try:
        chat = await resolve_target_chat(m, chat_ref)
        member = await get_bot_admin_member(chat.id)
        title = chat.title or chat.username or str(chat.id)
        await m.reply_text(
            f"🔎 **Chat:** {title}\n👤 **Bot status:** {member.status}\n\n" + format_rights(member)
        )
    except RPCError as e:
        await m.reply_text(f"⚠️ Error: {e}")

@app.on_message(filters.command("promote"))
async def promote_cmd(_, m: Message):
    # /promote <user> [chat]
    parts = m.text.split()
    user_ref, chat_ref = parse_user_and_chat_args(parts)
    if not user_ref:
        await m.reply_text("Usage: `/promote <user> [chat]`", quote=True)
        return
    try:
        # Resolve chat
        chat = await resolve_target_chat(m, chat_ref)

        # Check bot admin + rights
        bot_member = await get_bot_admin_member(chat.id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            await m.reply_text("❌ Bot is chat me admin hi nahi hai.")
            return
        priv = bot_member.privileges
        if not priv or not priv.can_promote_members:
            await m.reply_text("❌ Bot ke paas **promote_members (add admins)** permission nahi hai.")
            return

        # Resolve target user
        try:
            if user_ref.startswith("@"):
                user = await app.get_users(user_ref)
            else:
                user = await app.get_users(int(user_ref))
        except Exception:
            # If replied-to message exists, take that user
            if m.reply_to_message:
                user = m.reply_to_message.from_user
            else:
                raise

        # Decide what privileges to grant (safe default set)
        new_privs = ChatPrivileges(
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_invite_users=True,
            # For channels, you may want to allow posting/editing:
            can_post_messages=True,
            can_edit_messages=True,
            # (Groups) optionally:
            can_pin_messages=True,
        )

        await app.promote_chat_member(chat.id, user.id, privileges=new_privs)

        await m.reply_text(
            f"✅ **Promoted:** {user.mention} \n"
            f"📍 Chat: {chat.title or chat.username or chat.id}\n"
            f"Rights diya gaya: manage_chat, delete_messages, manage_video_chats, invite_users, "
            f"post_messages, edit_messages, pin_messages."
        )

    except RPCError as e:
        await m.reply_text(f"⚠️ Promote failed: {e}")
    except Exception as e:
        await m.reply_text(f"⚠️ Error: {e}")

# --------- Run ---------
if __name__ == "__main__":
    print("Bot starting...")
    app.run()
