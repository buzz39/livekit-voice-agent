# Call Recording and Transcripts

Your telephony agent now captures full transcripts and can record audio for every call.

## What's Captured

### 1. Transcripts (Stored in Database)
- ✅ **Automatically saved** to the `transcript` column in the `calls` table
- ✅ **Turn-by-turn format** - Shows both agent and user messages
- ✅ **Stored in Neon database** - Query anytime
- ✅ **No additional cost** - Uses LiveKit's built-in conversation history

### 2. Audio Recordings (LiveKit Cloud)
- ✅ **Automatically recorded** when `record=True` in session.start()
- ✅ **Available in LiveKit Cloud** dashboard for 30 days
- ✅ **Downloadable** as audio files
- ✅ **FREE until end of 2025** (beta)

## Viewing Transcripts

### Query recent call transcripts
```sql
SELECT 
    c.id,
    c.created_at,
    co.business_name,
    co.phone_number,
    c.duration_seconds,
    c.interest_level,
    c.transcript
FROM calls c
JOIN contacts co ON c.contact_id = co.id
WHERE c.transcript IS NOT NULL
ORDER BY c.created_at DESC
LIMIT 10;
```

### Search transcripts for keywords
```sql
SELECT 
    c.id,
    co.business_name,
    c.created_at,
    c.transcript
FROM calls c
JOIN contacts co ON c.contact_id = co.id
WHERE c.transcript ILIKE '%website%'
ORDER BY c.created_at DESC;
```

### View full transcript for a specific call
```sql
SELECT transcript FROM calls WHERE id = 2;
```

## Accessing Audio Recordings

### Option 1: LiveKit Cloud Dashboard (Easiest)

1. Go to [LiveKit Cloud Console](https://cloud.livekit.io)
2. Navigate to your project
3. Click on "Agent insights" tab
4. Find your call by room ID or timestamp
5. Play audio directly in browser or download

**Enable this feature:**
1. Go to [Project Settings](https://cloud.livekit.io/projects/p_/settings/project)
2. Enable "Agent observability" under Data and privacy
3. Recordings will appear automatically for all future calls

### Option 2: Custom Recording to S3/Storage

For long-term storage or custom workflows, you can record directly to your storage:

```python
from livekit import api
import os

async def entrypoint(ctx: JobContext):
    # Start recording to S3
    req = api.RoomCompositeEgressRequest(
        room_name=ctx.room.name,
        audio_only=True,
        file_outputs=[
            api.EncodedFileOutput(
                file_type=api.EncodedFileType.MP3,
                filepath=f"recordings/{ctx.room.name}.mp3",
                s3=api.S3Upload(
                    bucket=os.getenv("AWS_BUCKET_NAME"),
                    region=os.getenv("AWS_REGION"),
                    access_key=os.getenv("AWS_ACCESS_KEY_ID"),
                    secret=os.getenv("AWS_SECRET_ACCESS_KEY"),
                ),
            )
        ],
    )
    
    lkapi = api.LiveKitAPI()
    egress_info = await lkapi.egress.start_room_composite_egress(req)
    recording_url = f"https://{os.getenv('AWS_BUCKET_NAME')}.s3.amazonaws.com/recordings/{ctx.room.name}.mp3"
    
    # Store URL in database for later retrieval
    # ... continue with agent logic
```

Then update the database call logging to include the recording URL.

## Transcript Format

Transcripts are saved in a simple, readable format:

```
Agent: Hey... uh, hey there - this is Sam from Sambhav Tech. Umm, I know this is kind of out of the blue... do you have, like, a quick minute?
User: Sure, what's this about?
Agent: Cool, cool - yeah, I'll keep it super short. So... I was looking at your roofing business online earlier today...
User: Okay, I'm listening.
Agent: We've been helping a bunch of roofers kinda clean that up and get more homeowners actually calling in. Would it be cool if I sent you a quick demo?
User: Yeah, send it to john@example.com
Agent: Oh, perfect - yeah. Okay, so that's john@example.com... yeah? that looks right?
User: Yes, that's correct.
Agent: Alright, awesome. I'll uh... send it over today. Thanks for picking up - talk soon.
```

## Analytics with Transcripts

### Find calls mentioning specific topics
```sql
-- Calls where price was discussed
SELECT 
    co.business_name,
    c.created_at,
    c.interest_level
FROM calls c
JOIN contacts co ON c.contact_id = co.id
WHERE c.transcript ILIKE '%price%' OR c.transcript ILIKE '%cost%'
ORDER BY c.created_at DESC;
```

### Analyze successful calls
```sql
-- Get transcripts from Hot leads
SELECT 
    co.business_name,
    c.transcript,
    c.notes
FROM calls c
JOIN contacts co ON c.contact_id = co.id
WHERE c.interest_level = 'Hot'
ORDER BY c.created_at DESC
LIMIT 5;
```

### Track common phrases
```sql
-- Count how often "already have a website" appears
SELECT 
    COUNT(*) as frequency
FROM calls
WHERE transcript ILIKE '%already have a website%';
```

## Data Retention

### Database Transcripts
- **Stored indefinitely** in your Neon database
- **Your control** - delete or archive as needed
- **No additional cost** beyond Neon storage

### LiveKit Cloud Recordings
- **30-day retention** - automatically deleted after 30 days
- **Download before expiry** if you need long-term storage
- **FREE until end of 2025** (beta)

## Privacy and Compliance

### Disabling Recording for Specific Calls

If you need to disable recording for privacy reasons:

```python
# In telephony_agent.py
await session.start(agent=agent, room=ctx.room, record=False)
```

This disables:
- Audio recording upload to LiveKit Cloud
- Transcript upload to LiveKit Cloud
- Traces and logs upload

**Note:** Local transcript capture in your database still works.

### GDPR/Privacy Considerations

1. **Inform callers** - Add a message at the start: "This call may be recorded for quality purposes"
2. **Data retention** - Set up automatic deletion of old transcripts
3. **Access control** - Restrict who can view transcripts in your database
4. **Anonymization** - Consider removing PII from transcripts after a period

```sql
-- Delete transcripts older than 90 days
DELETE FROM calls 
WHERE created_at < NOW() - INTERVAL '90 days' 
AND transcript IS NOT NULL;

-- Or anonymize instead of delete
UPDATE calls 
SET transcript = '[REDACTED]'
WHERE created_at < NOW() - INTERVAL '90 days';
```

## Troubleshooting

### Transcript is NULL in database
**Causes:**
- Session ended before transcript could be captured
- Very short call (< 2 seconds)
- Error in transcript capture code

**Solution:**
- Check agent logs for errors
- Verify session.history is populated
- Ensure call lasted long enough for conversation

### Audio recording not available in LiveKit Cloud
**Causes:**
- Agent observability not enabled in project settings
- Using `record=False` in session.start()
- Call happened before feature was enabled

**Solution:**
1. Enable "Agent observability" in [project settings](https://cloud.livekit.io/projects/p_/settings/project)
2. Ensure `record=True` in session.start() (default)
3. Wait a few minutes after call ends for upload to complete

### Transcript is incomplete
**Causes:**
- Call ended abruptly
- Network issues during call
- Agent crashed before transcript was saved

**Solution:**
- Implement better error handling
- Add retry logic for database saves
- Consider saving transcript incrementally during call

## Best Practices

1. **Review transcripts regularly** - Identify patterns in successful calls
2. **Train your agent** - Use real transcripts to improve prompts
3. **Monitor quality** - Check for misunderstandings or errors
4. **Backup recordings** - Download important calls from LiveKit Cloud before 30-day expiry
5. **Respect privacy** - Only store what you need, delete old data
6. **Use for training** - Analyze transcripts to improve your sales pitch
7. **Track keywords** - Build queries to find specific topics or objections

## Example: Export Transcripts to CSV

```python
import asyncio
import csv
from neon_db import get_db

async def export_transcripts():
    db = await get_db()
    
    async with db.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                c.id,
                c.created_at,
                co.business_name,
                co.phone_number,
                c.duration_seconds,
                c.interest_level,
                c.transcript
            FROM calls c
            JOIN contacts co ON c.contact_id = co.id
            WHERE c.transcript IS NOT NULL
            ORDER BY c.created_at DESC
        """)
    
    with open('transcripts.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Call ID', 'Date', 'Business', 'Phone', 'Duration', 'Interest', 'Transcript'])
        
        for row in rows:
            writer.writerow([
                row['id'],
                row['created_at'],
                row['business_name'],
                row['phone_number'],
                row['duration_seconds'],
                row['interest_level'],
                row['transcript']
            ])
    
    print(f"Exported {len(rows)} transcripts to transcripts.csv")

asyncio.run(export_transcripts())
```

## Next Steps

1. **Enable LiveKit Cloud observability** - Get audio recordings automatically
2. **Test a call** - Make a test call and check the transcript in the database
3. **Review recordings** - Listen to calls in LiveKit Cloud dashboard
4. **Build analytics** - Create queries to analyze conversation patterns
5. **Improve prompts** - Use real transcripts to refine your agent's behavior
