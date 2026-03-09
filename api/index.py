from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
import asyncio
import time
import os
from datetime import datetime

app = Flask(__name__)

# Environment variables se lo (vercel.json se aayenge)
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8321486632:AAF5vfg0vnIUIlVOLvK1q9cVlK0MRuNgNRI")
API_ID = int(os.environ.get('API_ID', 25516423))
API_HASH = os.environ.get('API_HASH', 'a86a8202eeb28dd33f3c4d8b5daba3cc')

print("⏳ Bot start ho raha hai...")

class AdvancedTelegramAPI:
    def __init__(self):
        self.client = None
        self.start_time = time.time()
        self.loop = None
    
    async def start_bot(self):
        self.client = TelegramClient('bot_session', API_ID, API_HASH)
        await self.client.start(bot_token=BOT_TOKEN)
        print("✅ Bot ready!")
        return self.client
    
    def get_uptime(self):
        return time.time() - self.start_time
    
    def _get_detailed_status(self, user):
        """User ki detailed status nikalne ka function"""
        status_info = {
            'currently': 'Unknown',
            'last_seen': None,
            'exact_time': None
        }
        
        if hasattr(user, 'status') and user.status:
            status_type = type(user.status).__name__
            
            if 'UserStatusOnline' in status_type:
                status_info['currently'] = 'Online'
                if hasattr(user.status, 'expires'):
                    status_info['expires'] = datetime.fromtimestamp(user.status.expires).isoformat()
            
            elif 'UserStatusOffline' in status_type:
                status_info['currently'] = 'Offline'
                if hasattr(user.status, 'was_online'):
                    status_info['last_seen'] = datetime.fromtimestamp(user.status.was_online).isoformat()
                    time_diff = time.time() - user.status.was_online
                    if time_diff < 60:
                        status_info['last_seen_text'] = 'Just now'
                    elif time_diff < 3600:
                        status_info['last_seen_text'] = f'{int(time_diff/60)} minutes ago'
                    elif time_diff < 86400:
                        status_info['last_seen_text'] = f'{int(time_diff/3600)} hours ago'
                    else:
                        status_info['last_seen_text'] = f'{int(time_diff/86400)} days ago'
            
            elif 'UserStatusRecently' in status_type:
                status_info['currently'] = 'Recently'
                status_info['last_seen_text'] = 'Last seen recently'
            
            elif 'UserStatusLastWeek' in status_type:
                status_info['currently'] = 'Last week'
                status_info['last_seen_text'] = 'Last seen within last week'
            
            elif 'UserStatusLastMonth' in status_type:
                status_info['currently'] = 'Last month'
                status_info['last_seen_text'] = 'Last seen within last month'
        
        return status_info

    async def get_original_details(self, username):
        """Pehle wale /details/ endpoint jaisa exact data"""
        try:
            entity = await self.client.get_entity(username)
            full = await self.client(GetFullUserRequest(entity.id))
            
            result = {
                'success': True,
                'username': f"@{entity.username}" if entity.username else None,
                'user_id': entity.id,
                'access_hash': entity.access_hash,
                'first_name': getattr(entity, 'first_name', 'N/A'),
                'last_name': getattr(entity, 'last_name', 'N/A'),
                'phone': getattr(entity, 'phone', 'N/A'),
                'is_bot': entity.bot,
                'is_verified': entity.verified,
                'is_scam': entity.scam,
                'is_fake': entity.fake,
                'is_support': entity.support,
                'mutual_contact': getattr(entity, 'mutual_contact', False),
            }
            
            if full and hasattr(full, 'full_user'):
                result['bio'] = getattr(full.full_user, 'about', 'N/A')
                result['common_chats_count'] = getattr(full.full_user, 'common_chats_count', 0)
                
                if hasattr(full.full_user, 'profile_photo') and full.full_user.profile_photo:
                    result['photo_id'] = full.full_user.profile_photo.id
                    result['has_photo'] = True
                else:
                    result['has_photo'] = False
                
                if hasattr(entity, 'status'):
                    result['status'] = str(entity.status)
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_complete_user_info(self, username):
        """Sabse advanced user info lene ka function"""
        try:
            resolved = await self.client(ResolveUsernameRequest(username))
            
            if not resolved.users:
                return None
            
            user = resolved.users[0]
            chats = resolved.chats
            full_user = await self.client(GetFullUserRequest(user.id))
            
            # Recent messages
            recent_messages = []
            try:
                async for msg in self.client.iter_messages(user.id, limit=3):
                    if msg and not msg.out:
                        recent_messages.append({
                            'id': msg.id,
                            'date': msg.date.isoformat() if msg.date else None,
                            'text': msg.text[:100] if msg.text else '[Media/Other]',
                            'has_media': bool(msg.media)
                        })
            except:
                recent_messages = []
            
            # Profile photos
            profile_photos = []
            if hasattr(full_user.full_user, 'profile_photo') and full_user.full_user.profile_photo:
                photo = full_user.full_user.profile_photo
                profile_photos.append({
                    'photo_id': photo.id,
                    'has_video': photo.has_video if hasattr(photo, 'has_video') else False,
                    'dc_id': photo.dc_id if hasattr(photo, 'dc_id') else None,
                })
            
            # Restrictions
            restrictions = []
            if hasattr(user, 'restriction_reason') and user.restriction_reason:
                for r in user.restriction_reason:
                    restrictions.append({
                        'platform': r.platform,
                        'reason': r.reason,
                        'text': r.text
                    })
            
            status_info = self._get_detailed_status(user)
            
            result = {
                'success': True,
                'basic_info': {
                    'user_id': user.id,
                    'access_hash': user.access_hash,
                    'username': f"@{user.username}" if user.username else None,
                    'phone': getattr(user, 'phone', 'Hidden'),
                    'first_name': getattr(user, 'first_name', 'N/A'),
                    'last_name': getattr(user, 'last_name', 'N/A'),
                },
                
                'account_type': {
                    'is_bot': user.bot,
                    'is_verified': user.verified,
                    'is_premium': getattr(user, 'premium', False),
                    'is_scam': user.scam,
                    'is_fake': user.fake,
                    'is_support': user.support,
                },
                
                'profile_details': {
                    'bio': getattr(full_user.full_user, 'about', 'No bio'),
                    'profile_photos': profile_photos,
                    'photo_count': getattr(full_user.full_user, 'profile_photo_count', 0),
                },
                
                'status': status_info,
                
                'social_info': {
                    'common_chats_count': getattr(full_user.full_user, 'common_chats_count', 0),
                    'recent_messages': recent_messages,
                },
                
                'restrictions': restrictions,
            }
            
            # Analysis add karo
            analysis = {
                'account_score': 100,
                'warnings': [],
                'notes': []
            }
            
            if result['account_type']['is_scam']:
                analysis['account_score'] -= 50
                analysis['warnings'].append('⚠️ SCAM account')
            
            if result['account_type']['is_fake']:
                analysis['account_score'] -= 40
                analysis['warnings'].append('⚠️ Fake account')
            
            if result['account_type']['is_premium']:
                analysis['account_score'] += 15
                analysis['notes'].append('✨ Premium user')
            
            if result['account_type']['is_verified']:
                analysis['account_score'] += 25
                analysis['notes'].append('✅ Verified')
            
            if result['profile_details']['photo_count'] > 0:
                analysis['account_score'] += 10
                analysis['notes'].append('Has profile photo')
            
            analysis['account_score'] = max(0, min(100, analysis['account_score']))
            result['analysis'] = analysis
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Initialize API
api = AdvancedTelegramAPI()

# Global event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Start bot on module load
try:
    bot = loop.run_until_complete(api.start_bot())
except Exception as e:
    print(f"Error starting bot: {e}")
    bot = None

@app.route('/')
def home():
    status = "running" if bot else "degraded"
    return jsonify({
        'status': status,
        'uptime': f"{api.get_uptime():.2f} seconds",
        'version': '2.0 Advanced (Vercel)',
        'endpoints': {
            '/id/<username>': 'Basic ID only',
            '/details/<username>': 'ORIGINAL - Basic details with phone',
            '/full/<username>': 'Everything available (original)',
            '/complete/<username>': 'Complete user details (advanced)',
            '/status/<username>': 'Only online/offline status',
            '/analyze/<username>': 'Complete analysis with score',
        }
    })

@app.route('/id/<path:username>')
def get_id(username):
    """Sirf ID ke liye"""
    if not bot:
        return jsonify({'success': False, 'error': 'Bot not initialized'}), 500
    
    try:
        if not username.startswith('@'):
            username = '@' + username
        
        async def get_entity():
            return await bot.get_entity(username)
        
        entity = loop.run_until_complete(get_entity())
        
        return jsonify({
            'success': True,
            'username': f"@{entity.username}" if entity.username else None,
            'chat_id': entity.id,
            'type': type(entity).__name__
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/details/<path:username>')
def get_details(username):
    """DETAILS KE SAATH - EXACTLY PEHLE JAISA"""
    if not bot:
        return jsonify({'success': False, 'error': 'Bot not initialized'}), 500
    
    try:
        if not username.startswith('@'):
            username = '@' + username
        
        result = loop.run_until_complete(api.get_original_details(username))
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/full/<path:username>')
def get_full(username):
    """SAB KUCH - RAW DATA"""
    if not bot:
        return jsonify({'success': False, 'error': 'Bot not initialized'}), 500
    
    try:
        if not username.startswith('@'):
            username = '@' + username
        
        async def get_raw():
            entity = await bot.get_entity(username)
            full = await bot(GetFullUserRequest(entity.id))
            return {
                'entity': entity.to_dict(),
                'full_user': full.to_dict() if full else None
            }
        
        data = loop.run_until_complete(get_raw())
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/complete/<path:username>')
def complete_info(username):
    """Complete advanced user details"""
    if not bot:
        return jsonify({'success': False, 'error': 'Bot not initialized'}), 500
    
    try:
        if not username.startswith('@'):
            username = '@' + username
        
        result = loop.run_until_complete(api.get_complete_user_info(username.replace('@', '')))
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/status/<path:username>')
def get_status(username):
    """Sirf status check"""
    if not bot:
        return jsonify({'success': False, 'error': 'Bot not initialized'}), 500
    
    try:
        if not username.startswith('@'):
            username = '@' + username
        
        async def check_status():
            user = await bot.get_entity(username)
            if hasattr(user, 'status'):
                status_type = type(user.status).__name__
                return {
                    'success': True,
                    'username': username,
                    'status_type': status_type,
                    'details': api._get_detailed_status(user)
                }
            return {'success': True, 'status': 'No status info'}
        
        return jsonify(loop.run_until_complete(check_status()))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/analyze/<path:username>')
def analyze_user(username):
    """Full analysis with extra insights"""
    if not bot:
        return jsonify({'success': False, 'error': 'Bot not initialized'}), 500
    
    try:
        if not username.startswith('@'):
            username = '@' + username
        
        result = loop.run_until_complete(api.get_complete_user_info(username.replace('@', '')))
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

# Vercel handler
def handler(request):
    return app(request)

# For local testing
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 ADVANCED TELEGRAM API STARTED (LOCAL)")
    print("📍 Port: 8000")
    print("="*60)
    app.run(host='0.0.0.0', port=8000, debug=False)
