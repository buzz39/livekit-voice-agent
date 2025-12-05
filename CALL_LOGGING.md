# Call Logging

Your telephony agent now automatically logs all calls to the Neon database with detailed metadata.

## What Gets Logged

Every call is automatically logged to the `calls` table with:

- **contact_id** - Links to the contact in the contacts table
- **room_id** - LiveKit room identifier
- **prompt_id** - Which agent prompt was used
- **duration_seconds** - Total call length
- **interest_level** - Hot, Warm, Cold, or No Interest
- **objection** - Any objections raised by the customer
- **notes** - Additional notes captured during the call
- **email_captured** - Whether an email was collected
- **call_status** - completed, failed, etc.
- **created_at** - Timestamp of the call

## New Function Tools

The agent now has built-in tools to capture call metadata:

### 1. capture_email(email: str)
Captures the customer's email address.

**Example usage in conversation:**
```
Agent: "Can I get your email address?"
Customer: "Sure, it's john@example.com"
Agent: [calls capture_email("john@example.com")]
```

### 2. set_interest_level(level: str)
Sets the customer's interest level.

**Valid levels:** "Hot", "Warm", "Cold", "No Interest"

**Example usage:**
```
Agent: [After positive conversation, calls set_interest_level("Hot")]
```

### 3. record_objection(objection: str)
Records a customer objection or concern.

**Example usage:**
```
Customer: "This is too expensive"
Agent: [calls record_objection("Price concern")]
```

### 4. add_note(note: str)
Adds a general note about the call.

**Example usage:**
```
Agent: [calls add_note("Customer interested in premium package")]
```

## How It Works

1. **Call starts** - Contact is created/updated in database
2. **During call** - Agent uses function tools to capture metadata
3. **Call ends** - All data is automatically logged to the calls table
4. **Objections tracked** - Any objections are also logged to the objections table

## Viewing Call Logs

### Recent calls
```sql
SELECT 
    c.created_at,
    co.business_name,
    co.phone_number,
    c.duration_seconds,
    c.interest_level,
    c.email_captured,
    c.notes
FROM calls c
JOIN contacts co ON c.contact_id = co.id
ORDER BY c.created_at DESC
LIMIT 20;
```

### Calls by interest level
```sql
SELECT 
    interest_level,
    COUNT(*) as count,
    AVG(duration_seconds) as avg_duration
FROM calls
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY interest_level
ORDER BY count DESC;
```

### Hot leads
```sql
SELECT 
    co.business_name,
    co.phone_number,
    c.created_at,
    c.duration_seconds,
    c.notes
FROM calls c
JOIN contacts co ON c.contact_id = co.id
WHERE c.interest_level = 'Hot'
ORDER BY c.created_at DESC;
```

### Common objections
```sql
SELECT 
    objection_text,
    frequency,
    response_text
FROM objections
ORDER BY frequency DESC
LIMIT 10;
```

## Updating Agent Instructions

To make the agent use these tools effectively, update your prompt in the database:

```sql
UPDATE prompts 
SET content = '
You are Sam, a professional caller for Sambhav Tech AI.

IMPORTANT: Use the following tools during calls:
- capture_email(email): When customer provides their email
- set_interest_level(level): Set to "Hot", "Warm", "Cold", or "No Interest" based on conversation
- record_objection(objection): When customer raises a concern
- add_note(note): For any important details

Always try to:
1. Capture the customer''s email if possible
2. Assess their interest level by the end of the call
3. Record any objections so we can improve our approach
4. Add notes about specific needs or requests
'
WHERE name = 'default_roofing_agent';
```

## Analytics

Use the built-in `get_call_stats()` method:

```python
from neon_db import get_db
import asyncio

async def view_stats():
    db = await get_db()
    stats = await db.get_call_stats(days=7)
    print(f"Total calls: {stats['total_calls']}")
    print(f"Hot leads: {stats['hot_leads']}")
    print(f"Emails captured: {stats['emails_captured']}")
    print(f"Average duration: {stats['avg_duration']}s")

asyncio.run(view_stats())
```

## Best Practices

1. **Train the agent** - Update prompts to use the function tools appropriately
2. **Review logs daily** - Check for patterns in objections and interest levels
3. **Follow up on hot leads** - Query for Hot interest levels and reach out
4. **Improve responses** - Use objection data to refine your pitch
5. **Track conversion** - Monitor email capture rate as a KPI

## Troubleshooting

### Calls not being logged
- Check database connection in logs
- Verify `calls` table exists in Neon
- Ensure agent has proper error handling

### Metadata not captured
- Verify agent is using the function tools
- Check agent prompt includes instructions to use tools
- Review agent logs for tool execution

### Duration is 0 or incorrect
- Ensure `wait_for_completion()` is called
- Check for early disconnections
- Verify call_start_time is set correctly
