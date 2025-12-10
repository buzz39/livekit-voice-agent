import { NextRequest, NextResponse } from 'next/server';
import pool from '@/utils/db';

export async function POST(request: NextRequest) {
    let client;
    try {
        client = await pool.connect();
        const data = await request.json();
        const { id, name, llm_model, stt_model, tts_voice, tts_speed, owner_id } = data;

        if (!name) {
            return NextResponse.json({ error: 'Name is required' }, { status: 400 });
        }

        if (id) {
            // Update
            await client.query(
                `UPDATE ai_configs SET llm_model = $1, stt_model = $2, tts_voice = $3, tts_speed = $4, updated_at = NOW()
                 WHERE id = $5`,
                [llm_model || '', stt_model || '', tts_voice || '', tts_speed || 1, id]
            );
            console.log('AI config updated:', id);
        } else {
            // Create
            await client.query(
                `INSERT INTO ai_configs (name, owner_id, llm_model, stt_model, tts_voice, tts_speed)
                 VALUES ($1, $2, $3, $4, $5, $6)`,
                [name, owner_id || 'dev_user', llm_model || '', stt_model || '', tts_voice || '', tts_speed || 1]
            );
            console.log('AI config created:', name);
        }

        return NextResponse.json({ success: true });
    } catch (error: any) {
        console.error('Database error:', error);
        return NextResponse.json({ error: error.message || 'Failed to save AI config' }, { status: 500 });
    } finally {
        if (client) {
            client.release();
        }
    }
}

export async function DELETE(request: NextRequest) {
    const client = await pool.connect();
    try {
        const body = await request.json();
        const { id } = body;
        await client.query(`DELETE FROM ai_configs WHERE id = $1`, [parseInt(id)]);
        return NextResponse.json({ success: true });
    } catch (error) {
        console.error('Database error:', error);
        return NextResponse.json({ error: 'Failed to delete AI config' }, { status: 500 });
    } finally {
        client.release();
    }
}
